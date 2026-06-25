/**
 * Category enum and utilities for auction listings.
 */

export const CATEGORIES = {
  HANDBAG: "Handbag",
  WATCHES: "Watches",
  PERFUMES: "Perfumes",
  FASHION_APPAREL: "Fashion & Apparel",
  ACCESSORIES: "Accessories",
  FINE_ART: "Fine Art & Collectibles",
  WINES_SPIRITS: "Wines & Spirits",
  HOME_DECOR: "Home Decor & Furniture",
  OTHERS: "Others",
};

/**
 * Get all category values as a sorted array.
 */
export const getCategoryOptions = () => {
  return Object.values(CATEGORIES).sort();
};

/**
 * Get display label for a category (same as value in this case).
 */
export const getCategoryLabel = (categoryKey) => {
  return CATEGORIES[categoryKey] || categoryKey;
};
