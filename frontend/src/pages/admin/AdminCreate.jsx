import { useState } from "react";

import AdminLayout from "../../components/admin/AdminLayout.jsx";
import { createListing } from "../../api/auctions.js";
import { useAuth } from "../../context/AuthContext.jsx";

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
    startingPrice: "",
    minimumIncrement: "",
    startTime: "",
    endTime: "",
    images: [],
  });
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);
  const { user, loading } = useAuth();

  const handleChange = (field) => (event) => {
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
        image_key: form.images.length > 0 ? form.images[0].name : "",
        starting_price: form.startingPrice.replace(/,/g, ""),
        minimum_increment: form.minimumIncrement.replace(/,/g, ""),
        starts_at: form.startTime,
        ends_at: form.endTime,
      };

      await createListing(payload);

      setMessage({ type: "success", text: "Item saved successfully." });
      setForm({
        title: "",
        description: "",
        startingPrice: "",
        minimumIncrement: "",
        startTime: "",
        endTime: "",
        images: [],
      });
    } catch (error) {
      if (error?.response?.status === 403) {
        setMessage({ type: "error", text: "Admin access required." });
      } else {
        const errText = error?.response?.data?.detail ||
          error?.response?.data?.ends_at ||
          "Could not save item. Please try again.";
        setMessage({ type: "error", text: errText });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AdminLayout>
      <p className="admin-eyebrow">SecureBid Admin Panel</p>
      <h1 className="admin-page-title">Create a new item listing</h1>

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
              <label htmlFor="images">Images</label>
              <input
                id="images"
                type="file"
                accept="image/*"
                multiple
                onChange={handleChange("images")}
              />
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

        <button type="submit" className="btn-gold" disabled={submitting || !user?.is_staff}>
          {submitting ? "Saving…" : "Save item"}
        </button>
      </form>
      )}
    </AdminLayout>
  );
}
