import { useState } from "react";

import AdminLayout from "../../components/admin/AdminLayout.jsx";
import { createListing, uploadListingImage } from "../../api/auctions.js";
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

export default function AdminCreate() {
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
  const [message, setMessage] = useState(null);
  const { user, loading } = useAuth();

  const handleChange = (field) => async (event) => {
    if (field === "images" && event.target.files.length) {
      // Upload file immediately
      const files = Array.from(event.target.files);
      setUploading(true);
      setMessage(null);

      try {
        const formData = new FormData();
        formData.append("file", files[0]);
        const { key, url } = await uploadListingImage(formData);
        let previewUrl = url;
        if (typeof url === "string" && /^https?:\/\//i.test(url)) {
          try {
            previewUrl = new URL(url).pathname;
          } catch {
            previewUrl = url;
          }
        }
        setForm((prev) => ({
          ...prev,
          images: files,
          imageKey: key,
          imageUrl: previewUrl,
        }));
        setMessage({ type: "success", text: "Image uploaded successfully." });
      } catch (err) {
        const errText = err?.response?.data?.detail || "Could not upload image.";
        setMessage({ type: "error", text: errText });
      } finally {
        setUploading(false);
      }
      return;
    }

    const value = event.target.type === "file"
      ? Array.from(event.target.files)
      : event.target.value;

    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);

    try {
      const payload = {
        title: form.title,
        description: form.description,
        category: form.category,
        image_key: form.imageKey,
        starting_price: form.startingPrice.replace(/,/g, ""),
        minimum_increment: form.minimumIncrement.replace(/,/g, ""),
        starts_at: form.startTime,
        ends_at: form.endTime,
      };

      // Debug: log payload so we can confirm image_key is being sent
      // (remove console.log in production)
      console.log("Create payload:", payload);

      await createListing(payload);

      setMessage({ type: "success", text: "Item saved successfully." });
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
        let errText = "Could not save item. Please try again.";
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
        setMessage({ type: "error", text: "Could not save item. Please try again." });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AdminLayout>
      <p className="admin-eyebrow">SecureBid Admin Panel</p>
      <h1 className="admin-page-title">Create a new item listing</h1>

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

      {loading ? (
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
              <div style={{ padding: ".85rem 1rem", borderRadius: 6, background: "rgba(27,26,23,.04)", fontSize: ".84rem", color: "var(--ink)" }}>New</div>
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
                required
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
                type="file"
                accept="image/*"
                multiple
                onChange={handleChange("images")}
                disabled={uploading}
              />
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
                  required
                />
              </div>
            </div>

            <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
              <div className="field">
                <label htmlFor="startTime">Auction Start</label>
                <input
                  id="startTime"
                  type="datetime-local"
                  value={form.startTime}
                  onChange={handleChange("startTime")}
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="endTime">Auction End</label>
                <input
                  id="endTime"
                  type="datetime-local"
                  value={form.endTime}
                  onChange={handleChange("endTime")}
                  required
                />
              </div>
            </div>
          </div>
        </section>

        <button type="submit" className="btn-gold" disabled={submitting || uploading || !user?.is_staff}>
          {submitting ? "Saving…" : uploading ? "Uploading…" : "Save item"}
        </button>
      </form>
      )}
    </AdminLayout>
  );
}
