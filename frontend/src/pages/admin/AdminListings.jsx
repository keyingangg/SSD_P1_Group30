import { useEffect, useState } from "react";

import AdminLayout from "../../components/admin/AdminLayout.jsx";
import { deleteListing, getListings, updateListing } from "../../api/auctions.js";

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  minWidth: 900,
};

const cellStyle = {
  padding: "1rem",
  borderBottom: "1px solid rgba(27,26,23,.08)",
  textAlign: "left",
  verticalAlign: "top",
};

const inputStyle = {
  width: "100%",
  minWidth: "180px",
  padding: "12px 14px",
  border: "1px solid rgba(27,26,23,.12)",
  borderRadius: 6,
  background: "var(--input-bg)",
  color: "var(--ink)",
  fontSize: "14px",
};

function formatLocalDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

const actionButtonStyle = {
  fontSize: ".82rem",
  padding: ".5rem .8rem",
  borderRadius: 5,
  border: "1px solid rgba(27,26,23,.2)",
  background: "transparent",
  cursor: "pointer",
};

export default function AdminListings() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [savingId, setSavingId] = useState(null);

  const fetchListings = async () => {
    setLoading(true);
    setError(null);

    try {
      setListings(await getListings());
    } catch (err) {
      setError("Could not load listings. Please refresh.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchListings();
  }, []);

  const startEditing = (listing) => {
    setEditingId(listing.id);
    setEditForm({
      title: listing.title,
      description: listing.description,
      starting_price: listing.starting_price,
      minimum_increment: listing.minimum_increment,
      starts_at: formatLocalDateTime(listing.starts_at),
      ends_at: formatLocalDateTime(listing.ends_at),
      image_key: listing.image_key || "",
    });
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditForm({});
  };

  const handleFieldChange = (field) => (event) => {
    setEditForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const handleSave = async (listingId) => {
    setSavingId(listingId);
    try {
      await updateListing(listingId, editForm);
      await fetchListings();
      cancelEditing();
    } catch (err) {
      alert(err?.response?.data?.detail || "Could not update listing.");
    } finally {
      setSavingId(null);
    }
  };

  const handleDelete = async (listingId) => {
    if (!window.confirm("Delete this listing? This cannot be undone.")) {
      return;
    }

    try {
      await deleteListing(listingId);
      setListings((prev) => prev.filter((listing) => listing.id !== listingId));
    } catch (err) {
      alert(err?.response?.data?.detail || "Could not delete listing.");
    }
  };

  return (
    <AdminLayout>
      <p className="admin-eyebrow">SecureBid Admin Panel</p>
      <h1 className="admin-page-title">Manage Listings</h1>

      <div className="admin-panel" style={{ padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <div>
            <p className="admin-panel-title">View of All items listed on our auction platform</p>
           
          </div>
          <button
            className="btn-gold"
            style={{ width: "auto", minWidth: 170 }}
            onClick={() => window.location.assign("/admin/add-item")}
          >
            Add new item
          </button>
        </div>

        {loading && <p style={{ marginTop: "1rem" }}>Loading listings…</p>}
        {error && <p style={{ marginTop: "1rem", color: "var(--danger)" }}>{error}</p>}

        {!loading && !error && (
          <div style={{ overflowX: "auto", marginTop: "1rem" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={cellStyle}>Name</th>
                  <th style={cellStyle}>Start</th>
                  <th style={cellStyle}>End</th>
                  <th style={cellStyle}>Start Price</th>
                  <th style={cellStyle}>Min Increment</th>
                  <th style={cellStyle}>Status</th>
                  <th style={cellStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((listing) => (
                  <tr key={listing.id}>
                    <td style={cellStyle}>
                      {editingId === listing.id ? (
                        <input
                          value={editForm.title}
                          onChange={handleFieldChange("title")}
                          style={inputStyle}
                        />
                      ) : listing.title}
                    </td>
                    <td style={cellStyle}>
                      {editingId === listing.id ? (
                        <input
                          type="datetime-local"
                          value={editForm.starts_at}
                          onChange={handleFieldChange("starts_at")}
                          style={inputStyle}
                        />
                      ) : new Date(listing.starts_at).toLocaleString()}
                    </td>
                    <td style={cellStyle}>
                      {editingId === listing.id ? (
                        <input
                          type="datetime-local"
                          value={editForm.ends_at}
                          onChange={handleFieldChange("ends_at")}
                          style={inputStyle}
                        />
                      ) : new Date(listing.ends_at).toLocaleString()}
                    </td>
                    <td style={cellStyle}>
                      {editingId === listing.id ? (
                        <input
                          type="text"
                          inputMode="decimal"
                          value={editForm.starting_price}
                          onChange={handleFieldChange("starting_price")}
                          style={inputStyle}
                        />
                      ) : listing.starting_price}
                    </td>
                    <td style={cellStyle}>
                      {editingId === listing.id ? (
                        <input
                          value={editForm.minimum_increment}
                          onChange={handleFieldChange("minimum_increment")}
                          style={inputStyle}
                        />
                      ) : listing.minimum_increment}
                    </td>
                    <td style={cellStyle}>{listing.display_status || listing.status}</td>
                    <td style={cellStyle}>
                      {editingId === listing.id ? (
                        <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
                          <button
                            type="button"
                            style={actionButtonStyle}
                            onClick={() => handleSave(listing.id)}
                            disabled={savingId === listing.id}
                          >
                            {savingId === listing.id ? "Saving…" : "Save"}
                          </button>
                          <button
                            type="button"
                            style={actionButtonStyle}
                            onClick={cancelEditing}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
                          <button
                            type="button"
                            style={actionButtonStyle}
                            onClick={() => startEditing(listing)}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            style={actionButtonStyle}
                            onClick={() => handleDelete(listing.id)}
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
