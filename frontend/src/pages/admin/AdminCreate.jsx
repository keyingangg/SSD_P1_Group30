import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import AdminLayout from "../../components/admin/AdminLayout.jsx";
import { createListing, getListingDetail, updateListing, uploadListingImage } from "../../api/auctions.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { CATEGORIES, getCategoryOptions } from "../../config/categories.js";

const FIELD_STYLE = {
  display: "grid",
  gap: ".75rem",
  marginBottom: "1.4rem",
};

const SECTION_STYLE = {
  background: "#fff",
  border: "1px solid rgba(27,26,23,.08)",
  borderRadius: 8,
  padding: "1.25rem 1.5rem",
  marginBottom: "1.5rem",
};

const DATE_TIME_STYLE = {
  background: "rgba(194,161,90,.08)",
  borderColor: "rgba(194,161,90,.4)",
};

const SGT_TIME_ZONE = "Asia/Singapore";

function toSingaporeDateTimeInputValue(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: SGT_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);

  const get = (type) => parts.find((part) => part.type === type)?.value || "00";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

export default function AdminCreate() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const imageInputRef = useRef(null);
  const editingId = searchParams.get("edit");
  const isEditMode = Boolean(editingId);
  const [form, setForm] = useState({
    title: "",
    description: "",
    category: "Others",
    startingPrice: "",
    minimumIncrement: "",
    startTime: "",
    endTime: "",
    images: [],
    imageKey: "",
    imageUrl: "",
  });
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loadingEditData, setLoadingEditData] = useState(false);
  const [message, setMessage] = useState(null);
  const { user, loading } = useAuth();
  const nowLocal = toSingaporeDateTimeInputValue(new Date());
  const minEndLocal = form.startTime && form.startTime > nowLocal ? form.startTime : nowLocal;

  function formatLocalDateTime(value) {
    return toSingaporeDateTimeInputValue(value);
  }

  const hasImage = Boolean(form.imageUrl || form.imageKey || form.images?.length);

  const clearImageSelection = () => {
    if (imageInputRef.current) {
      imageInputRef.current.value = "";
    }

    setForm((prev) => ({
      ...prev,
      images: [],
      imageKey: "",
      imageUrl: "",
    }));
  };

  useEffect(() => {
    if (!isEditMode || !editingId) return;

    let cancelled = false;
    const loadListing = async () => {
      setLoadingEditData(true);
      setMessage(null);
      try {
        const listing = await getListingDetail(editingId);
        if (cancelled) return;

        setForm({
          title: listing.title || "",
          description: listing.description || "",
          category: listing.category || "Others",
          startingPrice: listing.starting_price ? String(listing.starting_price) : "",
          minimumIncrement: listing.minimum_increment ? String(listing.minimum_increment) : "",
          startTime: formatLocalDateTime(listing.starts_at),
          endTime: formatLocalDateTime(listing.ends_at),
          images: [],
          imageKey: listing.image_key || "",
          imageUrl: listing.image_key || "",
        });
      } catch (error) {
        if (!cancelled) {
          setMessage({ type: "error", text: "Could not load listing details for editing." });
        }
      } finally {
        if (!cancelled) setLoadingEditData(false);
      }
    };

    loadListing();
    return () => {
      cancelled = true;
    };
  }, [editingId, isEditMode]);

  const handleChange = (field) => async (event) => {
    if (field === "images") {
      const files = Array.from(event.target.files || []);
      const selectedFile = files[0] || null;
      const previewUrl = selectedFile ? URL.createObjectURL(selectedFile) : "";

      setForm((prev) => ({
        ...prev,
        images: files,
        imageKey: "",
        imageUrl: previewUrl,
      }));
      return;
    }

    const value = event.target.type === "file"
      ? Array.from(event.target.files)
      : event.target.value;

    if (field === "startTime") {
      setForm((prev) => {
        const next = { ...prev, startTime: value };
        if (next.endTime && value && next.endTime < value) {
          next.endTime = value;
        }
        return next;
      });
      return;
    }

    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const action = event.nativeEvent?.submitter?.dataset?.action || "create";
    const saveAsDraft = action === "draft";

    const title = (form.title || "").trim();
    const startingPrice = (form.startingPrice || "").trim();
    if (!title || !startingPrice) {
      setMessage({ type: "error", text: "Name and Starting Price are required to save a draft." });
      return;
    }

    if (!saveAsDraft) {
      const missing = [];
      if (!(form.description || "").trim()) missing.push("Description");
      if (!(form.minimumIncrement || "").trim()) missing.push("Minimum Increment");
      if (!(form.startTime || "").trim()) missing.push("Auction Start");
      if (!(form.endTime || "").trim()) missing.push("Auction End");

      if (missing.length) {
        setMessage({ type: "error", text: `Please complete: ${missing.join(", ")}.` });
        return;
      }
    }

    setSubmitting(true);
    setMessage(null);

    try {
      let imageKey = form.imageKey;
      if (form.images?.length) {
        setUploading(true);
        const formData = new FormData();
        formData.append("file", form.images[0]);
        const uploadedImage = await uploadListingImage(formData);
        imageKey = uploadedImage.key;
      }

      const payload = {
        title: form.title,
        description: form.description,
        category: form.category,
        image_key: imageKey,
        starting_price: form.startingPrice.replace(/,/g, ""),
        minimum_increment: form.minimumIncrement.replace(/,/g, ""),
        starts_at: form.startTime,
        ends_at: form.endTime,
        save_as_draft: saveAsDraft,
      };

      // Debug: log payload so we can confirm image_key is being sent
      // (remove console.log in production)
      console.log("Create payload:", payload);

      if (isEditMode) {
        await updateListing(editingId, payload);
      } else {
        await createListing(payload);
      }

      setMessage({ type: "success", text: isEditMode ? "Item updated successfully." : (saveAsDraft ? "Draft saved successfully." : "Item created successfully.") });

      if (isEditMode) {
        navigate("/admin/listings");
        return;
      }

      setForm({
        title: "",
        description: "",
        category: "Others",
        startingPrice: "",
        minimumIncrement: "",
        startTime: "",
        endTime: "",
        images: [],
        imageKey: "",
        imageUrl: "",
      });
    } catch (error) {
      // Friendly error formatting for validation and server errors.
      const resp = error?.response?.data;
      if (error?.response?.status === 403) {
        setMessage({ type: "error", text: "Admin access required." });
      } else if (resp) {
        let errText = saveAsDraft ? "Could not save draft. Please try again." : "Could not create item. Please try again.";
        if (typeof resp === "string") {
          errText = resp;
        } else if (resp.detail) {
          errText = resp.detail;
        } else if (typeof resp === "object") {
          // Flatten field errors to a single message
          errText = Object.entries(resp)
            .map(([k, v]) => {
              if (Array.isArray(v)) return `${k}: ${v.join(" ")}`;
              if (typeof v === "object") return `${k}: ${JSON.stringify(v)}`;
              return `${k}: ${v}`;
            })
            .join(" ");
        }

        setMessage({ type: "error", text: errText });
      } else {
        setMessage({ type: "error", text: saveAsDraft ? "Could not save draft. Please try again." : "Could not create item. Please try again." });
      }
    } finally {
      setUploading(false);
      setSubmitting(false);
    }
  };

  return (
    <AdminLayout>
      <p className="admin-eyebrow">SecureBid Admin Panel</p>
      <h1 className="admin-page-title">{isEditMode ? "Edit item listing" : "Create a new item listing"}</h1>

      {/* User feedback banner */}
      {message && (
        <div
          role="alert"
          style={{
            marginBottom: "1rem",
            padding: "0.75rem 1rem",
            borderRadius: 6,
            border: message.type === "success" ? "1px solid rgba(20,120,20,.15)" : "1px solid rgba(180,20,20,.12)",
            background: message.type === "success" ? "rgba(220,255,220,.4)" : "rgba(255,230,230,.6)",
            color: message.type === "success" ? "#0b5920" : "#7a0000",
          }}
        >
          {message.text}
        </div>
      )}

      {loading || loadingEditData ? (
        <p>Loading…</p>
      ) : (!user || !user.is_staff) ? (
        <p className="admin-error-text">Admin access required to create listings.</p>
      ) : (
      <form onSubmit={handleSubmit}>
        <section style={SECTION_STYLE}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
            <div style={{ flex: "1 1 300px" }}>
              <p className="admin-panel-title">Item details</p>

            </div>
            <div style={{ flex: "0 0 220px", minWidth: 220 }}>
              <label className="eyebrow" style={{ marginBottom: ".45rem", display: "block" }}>Status</label>
              <div style={{ padding: ".85rem 1rem", borderRadius: 6, background: "rgba(27,26,23,.04)", fontSize: ".84rem", color: "var(--ink)" }}>{isEditMode ? "Editing" : "New"}</div>
            </div>
          </div>

          <div style={FIELD_STYLE}>
            <div className="field">
              <label htmlFor="title">Name</label>
              <input
                id="title"
                type="text"
                placeholder="e.g. Patek Philippe Nautilus"
                value={form.title}
                onChange={handleChange("title")}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                placeholder="Detailed description, provenance and condition notes"
                value={form.description}
                onChange={handleChange("description")}
              />
            </div>

            <div className="field">
              <label htmlFor="category">Category</label>
              <select
                id="category"
                value={form.category}
                onChange={handleChange("category")}
                required
              >
                {getCategoryOptions().map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="images">Images</label>
              <input
                id="images"
                ref={imageInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleChange("images")}
                disabled={uploading}
                style={{ display: "none" }}
              />
              {!hasImage ? (
                <label
                  htmlFor="images"
                  className="btn-gold"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "fit-content",
                    cursor: uploading ? "not-allowed" : "pointer",
                    opacity: uploading ? 0.6 : 1,
                    pointerEvents: uploading ? "none" : "auto",
                  }}
                >
                  {uploading ? "Uploading..." : "Choose files"}
                </label>
              ) : (
                <button
                  type="button"
                  className="btn-gold"
                  onClick={clearImageSelection}
                  disabled={uploading}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "fit-content",
                    cursor: uploading ? "not-allowed" : "pointer",
                    opacity: uploading ? 0.6 : 1,
                    pointerEvents: uploading ? "none" : "auto",
                  }}
                >
                  Remove image
                </button>
              )}
              {form.imageUrl && (
                <div style={{ marginTop: ".5rem" }}>
                  <img src={form.imageUrl} alt="Preview" style={{ maxWidth: "200px", maxHeight: "200px", borderRadius: 6 }} />
                </div>
              )}
              {/* Debug: show returned image key and URL */}
              {form.imageKey && (
                <div style={{ marginTop: ".5rem", fontSize: ".9rem", color: "var(--ink)" }}>
                  <div><strong>Uploaded key:</strong> {form.imageKey}</div>
                  <div style={{ marginTop: ".25rem" }}><a href={form.imageUrl} target="_blank" rel="noreferrer">Open uploaded image</a></div>
                </div>
              )}
            </div>

            <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
              <div className="field">
                <label htmlFor="startingPrice">Starting Price</label>
                <input
                  id="startingPrice"
                  type="text"
                  placeholder="e.g. 12,000"
                  value={form.startingPrice}
                  onChange={handleChange("startingPrice")}
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="minimumIncrement">Minimum Increment</label>
                <input
                  id="minimumIncrement"
                  type="text"
                  placeholder="e.g. 500"
                  value={form.minimumIncrement}
                  onChange={handleChange("minimumIncrement")}
                />
              </div>
            </div>

            <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
              <div className="field">
                <label htmlFor="startTime">Auction Start</label>
                <p style={{ margin: 0, fontSize: ".78rem", opacity: 0.7 }}>Timezone: Singapore (SGT)</p>
                <input
                  id="startTime"
                  type="datetime-local"
                  value={form.startTime}
                  onChange={handleChange("startTime")}
                  min={isEditMode ? undefined : nowLocal}
                  style={DATE_TIME_STYLE}
                />
              </div>

              <div className="field">
                <label htmlFor="endTime">Auction End</label>
                <p style={{ margin: 0, fontSize: ".78rem", opacity: 0.7 }}>Timezone: Singapore (SGT)</p>
                <input
                  id="endTime"
                  type="datetime-local"
                  value={form.endTime}
                  onChange={handleChange("endTime")}
                  min={isEditMode ? undefined : minEndLocal}
                  style={DATE_TIME_STYLE}
                />
              </div>
            </div>
          </div>
        </section>

        <div style={{ display: "flex", gap: ".75rem", flexWrap: "wrap" }}>
          {!isEditMode && (
            <button
              type="submit"
              data-action="draft"
              className="btn-gold"
              disabled={submitting || uploading || !user?.is_staff}
              style={{ opacity: 0.85, width: "auto", minWidth: 180, flex: "1 1 220px" }}
            >
              {submitting ? "Saving..." : uploading ? "Uploading..." : "Save as draft"}
            </button>
          )}
          {isEditMode && (
            <button
              type="button"
              className="btn-gold"
              onClick={() => navigate("/admin/listings")}
              disabled={submitting || uploading}
              style={{ width: "auto", minWidth: 180, flex: "1 1 220px", background: "transparent", color: "var(--ink)", border: "1px solid rgba(27,26,23,.18)" }}
            >
              Cancel update
            </button>
          )}
          <button
            type="submit"
            data-action="create"
            className="btn-gold"
            disabled={submitting || uploading || !user?.is_staff}
            style={{ width: "auto", minWidth: 180, flex: "1 1 220px" }}
          >
            {submitting ? (isEditMode ? "Updating..." : "Creating...") : uploading ? "Uploading..." : (isEditMode ? "Update item" : "Create item")}
          </button>
        </div>
      </form>
      )}
    </AdminLayout>
  );
}
