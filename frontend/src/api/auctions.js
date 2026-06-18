import axiosClient from "./axiosClient.js";

export async function getListings() {
  const { data } = await axiosClient.get("/auctions/");
  return data;
}

export async function getListingDetail(listingId) {
  const { data } = await axiosClient.get(`/auctions/${listingId}/`);
  return data;
}

export async function createListing(payload) {
  const { data } = await axiosClient.post("/auctions/create/", payload);
  return data;
}

export async function updateListing(listingId, payload) {
  const { data } = await axiosClient.patch(`/auctions/${listingId}/update/`, payload);
  return data;
}

export async function deleteListing(listingId) {
  const { data } = await axiosClient.delete(`/auctions/${listingId}/delete/`);
  return data;
}

// TODO: POST /auctions/:id/bid/
export async function submitBid(listingId, amount) {}

// TODO: GET /auctions/bids/history/
export async function getUserBidHistory() {}
