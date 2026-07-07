import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import AdminLayout from "../admin-layout/AdminLayout.jsx";
import { createListing, getListingDetail, updateListing, uploadListingImage } from "../../api/auctions.js";
import { getCategoryOptions } from "../../config/categories.js";

const SGT_TZ = "Asia/Singapore";

function toSGTInput(value) {
  if (value === null || value === undefined || value === "") return "";
  const d = value instanceof Date ? value : new Date(value);
  if (isNaN(d.getTime())) return "";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: SGT_TZ, year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(d);
  const g = (t) => parts.find(p => p.type === t)?.value || "00";
  return `${g("year")}-${g("month")}-${g("day")}T${g("hour")}:${g("minute")}`;
}

const EMPTY = {
  title: "", description: "", category: "Others",
  startingPrice: "", minimumIncrement: "",
  startTime: "", endTime: "",
  images: [], imageKey: "", imageUrl: "",
};

export default function AdminCreate() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const fileRef = useRef(null);
  const editingId = searchParams.get("edit");
  const isEdit = Boolean(editingId);

  const [form, setForm] = useState(EMPTY);
  const [listingStatus, setListingStatus] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(isEdit);
  const [message, setMessage] = useState(null);
  const showError = (text) => {
    setMessage({ type: "error", text });
    setTimeout(() => setMessage(m => m?.text === text ? null : m), 4000);
  };
  const [dragging, setDragging] = useState(false);

  const nowSGT = toSGTInput(new Date());
  const minEnd = form.startTime && form.startTime > nowSGT ? form.startTime : nowSGT;

  useEffect(() => {
    if (!isEdit || !editingId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const l = await getListingDetail(editingId);
        if (cancelled) return;
        setListingStatus(l.status || null);
        setForm({
          title: l.title || "", description: l.description || "",
          category: l.category || "Others",
          startingPrice: l.starting_price ? String(l.starting_price) : "",
          minimumIncrement: l.minimum_increment ? String(l.minimum_increment) : "",
          startTime: toSGTInput(l.starts_at), endTime: toSGTInput(l.ends_at),
          images: [], imageKey: l.image_key || "", imageUrl: l.image_url || "",
        });
      } catch {
        if (!cancelled) showError("Could not load listing for editing.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [editingId, isEdit]);

  const setFile = (file) => {
    if (!file) return;
    setForm(p => ({ ...p, images: [file], imageKey: "", imageUrl: URL.createObjectURL(file) }));
  };

  const clearImage = () => {
    if (fileRef.current) fileRef.current.value = "";
    setForm(p => ({ ...p, images: [], imageKey: "", imageUrl: "" }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const action = e.nativeEvent?.submitter?.dataset?.action || "publish";
    const isDraft = action === "draft";

    if (isDraft) {
      if (!form.title.trim()) { showError("Item Name is required to save a draft."); return; }
    } else {
      const missing = [];
      if (!form.title.trim()) missing.push("Item Name");
      if (!form.description.trim()) missing.push("Item Description");
      if (!form.startingPrice.trim()) missing.push("Starting Price");
      if (!form.minimumIncrement.trim()) missing.push("Minimum Bid Increment");
      if (!form.startTime) missing.push("Auction Opens");
      if (!form.endTime) missing.push("Auction Closes");
      if (!form.images?.length && !form.imageKey) missing.push("Item Image");
      if (missing.length) {
        showError(`Please complete: ${missing.join(", ")}.`);
        return;
      }
    }

    setSubmitting(true);
    setMessage(null);
    try {
      let imageKey = form.imageKey;
      if (form.images?.length) {
        setUploading(true);
        const fd = new FormData();
        fd.append("file", form.images[0]);
        const res = await uploadListingImage(fd);
        imageKey = res.key;
      }
      const payload = {
        title: form.title,
        description: form.description,
        category: form.category,
        image_key: imageKey,
        save_as_draft: isDraft,
      };
      const startingPrice = form.startingPrice.replace(/,/g, "").trim();
      if (startingPrice) payload.starting_price = startingPrice;

      const minimumIncrement = form.minimumIncrement.trim();
      if (minimumIncrement) {
        payload.minimum_increment = minimumIncrement.replace(/,/g, "");
      }
      if (isDraft) {
        payload.starts_at = form.startTime || null;
        payload.ends_at = form.endTime || null;
      } else {
        if (form.startTime) {
          payload.starts_at = form.startTime;
        }
        if (form.endTime) {
          payload.ends_at = form.endTime;
        }
      }
      if (isEdit) {
        await updateListing(editingId, payload);
        navigate("/admin/listings");
      } else {
        await createListing(payload);
        navigate("/admin/listings");
      }
    } catch (err) {
      const resp = err?.response?.data;
      let text = "Something went wrong. Please try again.";
      if (resp?.detail) text = resp.detail;
      else if (typeof resp === "object") {
        text = Object.entries(resp).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(" ") : v}`).join(" · ");
      }
      showError(text);
    } finally {
      setUploading(false);
      setSubmitting(false);
    }
  };

  return (
    <AdminLayout>
      <nav className="acf-breadcrumb">
        <Link to="/admin/overview">Admin</Link>
        <span>›</span>
        <Link to="/admin/listings">Listings</Link>
        <span>›</span>
        <span>{isEdit ? "Edit Lot" : "New Lot"}</span>
      </nav>

      <h1 className="acf-title">
        {isEdit ? "Edit Auction Listing" : "Create Auction Listing"}
        {isEdit && listingStatus === "draft" && (
          <span style={{ marginLeft: ".65rem", fontSize: ".55em", fontWeight: 700, letterSpacing: ".08em", verticalAlign: "middle", padding: ".2em .55em", border: "1px solid rgba(0,0,0,.15)", color: "#888", background: "#f5f5f3" }}>DRAFT</span>
        )}
      </h1>
      <div className="acf-title-rule" />

      {message && message.type === "error" && (
        <div className={`acf-toast acf-toast--error`}>{message.text}</div>
      )}
      {message && message.type === "success" && (
        <div className="acf-msg acf-msg--success">{message.text}</div>
      )}

      {loading ? <p style={{ opacity: .6 }}>Loading…</p> : (
        <form onSubmit={handleSubmit}>
          <div className="acf-card">

            <p className="acf-section-label">Item Details</p>
            <div className="acf-section-rule" />

            <div className="acf-field">
              <label htmlFor="title">Item Name / Title</label>
              <input id="title" type="text" placeholder="e.g. Rolex Submariner Date Ref. 126610LN"
                value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))} />
            </div>

            <div className="acf-field">
              <label htmlFor="category">Category</label>
              <select id="category" value={form.category}
                onChange={e => setForm(p => ({ ...p, category: e.target.value }))}>
                {getCategoryOptions().map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div className="acf-field">
              <label htmlFor="description">Item Description</label>
              <textarea id="description"
                placeholder="Provenance, condition notes, authentication details."
                value={form.description}
                onChange={e => setForm(p => ({ ...p, description: e.target.value }))} />
            </div>

            <div className="acf-field">
              <label>Item Image &mdash; <span className="acf-field-note">JPEG · PNG · Max 5MB</span></label>
              <input ref={fileRef} id="images" type="file" accept="image/*"
                style={{ display: "none" }}
                onChange={e => setFile(e.target.files?.[0])}
                disabled={uploading} />
              {form.imageUrl ? (
                <div className="acf-img-preview">
                  <img src={form.imageUrl} alt="Preview" />
                  <button type="button" className="acf-img-remove" onClick={clearImage}>Remove</button>
                </div>
              ) : (
                <label htmlFor="images"
                  className={`acf-dropzone${dragging ? " dragging" : ""}`}
                  onDragOver={e => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={e => { e.preventDefault(); setDragging(false); setFile(e.dataTransfer.files?.[0]); }}>
                  <span>Drag &amp; drop or click to upload an image</span>
                </label>
              )}
            </div>

            <div className="acf-section-rule" style={{ marginTop: ".5rem" }} />

            <p className="acf-section-label" style={{ marginTop: "1.25rem" }}>Auction Settings</p>

            <div className="acf-two-col">
              <div className="acf-field">
                <label htmlFor="startingPrice">Starting Price (SGD)</label>
                <input id="startingPrice" type="text" placeholder="0.00"
                  value={form.startingPrice}
                  onChange={e => setForm(p => ({ ...p, startingPrice: e.target.value }))} />
              </div>
              <div className="acf-field">
                <label htmlFor="minimumIncrement">Minimum Bid Increment (SGD)</label>
                <input id="minimumIncrement" type="text" placeholder="500.00"
                  value={form.minimumIncrement}
                  onChange={e => setForm(p => ({ ...p, minimumIncrement: e.target.value }))} />
              </div>
            </div>

            <div className="acf-two-col">
              <div className="acf-field">
                <label htmlFor="startTime">Auction Opens (Date &amp; Time SGT)</label>
                <input id="startTime" type="datetime-local"
                  value={form.startTime} min={nowSGT}
                  onChange={e => {
                    const v = e.target.value;
                    setForm(p => ({ ...p, startTime: v, endTime: p.endTime && p.endTime < v ? v : p.endTime }));
                  }} />
              </div>
              <div className="acf-field">
                <label htmlFor="endTime">Auction Closes (Date &amp; Time SGT)</label>
                <input id="endTime" type="datetime-local"
                  value={form.endTime} min={minEnd}
                  onChange={e => setForm(p => ({ ...p, endTime: e.target.value }))} />
              </div>
            </div>

            <div className="acf-section-rule" />

            <div className="acf-actions">
              <button type="submit" data-action="publish" className="acf-btn-publish"
                disabled={submitting || uploading}>
                {uploading ? "Uploading…" : submitting ? "Publishing…" : (isEdit && listingStatus !== "draft" ? "Update Listing" : "Publish Listing")}
              </button>
              {(!isEdit || listingStatus === "draft") && (
                <button type="submit" data-action="draft" className="acf-btn-outline"
                  disabled={submitting || uploading}>
                  Save Draft
                </button>
              )}
              <button type="button" className="acf-btn-outline"
                onClick={() => navigate("/admin/listings")}>
                Cancel
              </button>
            </div>
            <p className="acf-publish-note">Publishing makes this listing visible to users when the auction window opens.</p>

          </div>
        </form>
      )}
    </AdminLayout>
  );
}
