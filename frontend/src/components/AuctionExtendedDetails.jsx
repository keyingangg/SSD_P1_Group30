import { useState } from "react";

function buildImageList(listing) {
  if (!listing || typeof listing !== "object") return [];
  if (Array.isArray(listing.image_urls) && listing.image_urls.length) return listing.image_urls.filter(Boolean);
  if (Array.isArray(listing.images) && listing.images.length) return listing.images.filter(Boolean);
  if (listing.image_url) return [listing.image_url];
  if (listing.image_key) {
    if (/^https?:\/\//i.test(listing.image_key)) return [listing.image_key];
    return [`/images/${listing.image_key}`];
  }
  return [];
}

export default function AuctionExtendedDetails({ listing }) {
  const [activeImage, setActiveImage] = useState(0);

  if (!listing) return <p style={{ opacity: 0.65 }}>No listing details available.</p>;

  const imageUrls = buildImageList(listing);
  const description = listing.description || "";

  return (
    <div className="ld-left">
      {/* Main image */}
      <div className="ld-image-main">
        {listing.provenance_verified && (
          <div className="ld-provenance-tag">Provenance Verified</div>
        )}
        {imageUrls.length ? (
          <img src={imageUrls[activeImage]} alt={listing.title || "Item"} />
        ) : (
          <div className="ld-no-image">No images uploaded.</div>
        )}
      </div>

      {/* Thumbnails */}
      {imageUrls.length > 1 && (
        <div className="ld-thumbnails">
          {imageUrls.map((url, i) => (
            <button
              key={`${url}-${i}`}
              type="button"
              className={`ld-thumb${i === activeImage ? " active" : ""}`}
              onClick={() => setActiveImage(i)}
            >
              <img src={url} alt={`View ${i + 1}`} />
            </button>
          ))}
        </div>
      )}

      {/* Description */}
      <div className="ld-description-section">
        <div style={{ padding: "1.5rem" }}>
          {listing.category && (
            <p className="ld-description-eyebrow">{listing.category}</p>
          )}
          <h3 className="ld-description-heading">{listing.title || "Untitled Item"}</h3>
          <hr className="ld-description-divider" />
          <div className="ld-description">
            {description ? (
              <p>{description}</p>
            ) : (
              <p style={{ opacity: 0.55 }}>No description provided.</p>
            )}
            {(listing.reference || listing.year || listing.condition || listing.movement || listing.case_material || listing.box_papers) && (
              <>
                <hr className="ld-specs-divider" />
                <div className="ld-specs-grid">
                  {listing.reference && <><span className="ld-spec-label">Reference</span><span className="ld-spec-value">{listing.reference}</span></>}
                  {listing.year && <><span className="ld-spec-label">Year</span><span className="ld-spec-value">{listing.year}</span></>}
                  {listing.condition && <><span className="ld-spec-label">Condition</span><span className="ld-spec-value">{listing.condition}</span></>}
                  {listing.movement && <><span className="ld-spec-label">Movement</span><span className="ld-spec-value">{listing.movement}</span></>}
                  {listing.case_material && <><span className="ld-spec-label">Case</span><span className="ld-spec-value">{listing.case_material}</span></>}
                  {listing.box_papers && <><span className="ld-spec-label">Box & Papers</span><span className="ld-spec-value">{listing.box_papers}</span></>}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
