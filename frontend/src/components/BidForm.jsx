import { useState } from "react";

// Bid amount input and submit control for an active auction.
export default function BidForm({ listingId, onSubmit }) {
  const [amount, setAmount] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: call submitBid(listingId, amount); handle validation errors.
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* TODO: amount input + submit button */}
    </form>
  );
}
