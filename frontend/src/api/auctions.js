import axiosClient from "./axiosClient.js";

// TODO: GET /auctions/ (supports search/filter params)
export async function getListings(params) {}

// TODO: GET /auctions/:id/
export async function getListingDetail(listingId) {}

// TODO: POST /auctions/:id/bid/
export async function submitBid(listingId, amount) {}

// TODO: GET /auctions/bids/history/
export async function getUserBidHistory() {}
