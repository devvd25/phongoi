export type Role = "student" | "landlord" | "admin";

export interface User {
  id: number;
  email: string;
  full_name: string;
  initials: string;
  role: Role;
  phone?: string | null;
  school_id?: number | null;
  bio?: string | null;
  email_verified: boolean;
  phone_verified: boolean;
  address_verified: boolean;
  id_verification: string;
  personalize: boolean;
  created_at: string;
}

export interface ListingCard {
  id: number;
  title: string;
  price: number;
  area?: number | null;
  district: string;
  street?: string | null;
  address: string;
  short_address: string;
  lat?: number | null;
  lng?: number | null;
  image?: string | null;
  images: string[];
  room_type: string;
  room_type_label: string;
  amenities: string[];
  amenity_labels: string[];
  max_people?: number | null;
  risk_level: "low" | "medium" | "high";
  risk_score: number;
  quality_score: number;
  source_count: number;
  status: string;
  posted_at: string;
  meta: string;
  price_tag?: string | null;
  match?: number | null;
  match_breakdown?: Record<string, number> | null;
  reasons: string[];
  distance_km?: number | null;
}

export interface Filters {
  budget_min?: number | null;
  budget_max?: number | null;
  area_min?: number | null;
  districts: string[];
  school_id?: number | null;
  max_distance_km?: number | null;
  amenities: string[];
  room_types: string[];
  max_people?: number | null;
  keywords?: string | null;
  hide_high_risk: boolean;
  sort: "match" | "price_asc" | "price_desc" | "newest" | "distance";
}

export interface SearchResult {
  engine: string;
  total: number;
  page: number;
  pages: number;
  hidden_risky: number;
  merged_duplicates: number;
  source_count: number;
  items: ListingCard[];
  pins: { id: number; lat: number; lng: number; price: number }[];
  school?: { id: number; name: string; lat: number; lng: number } | null;
  filters: Filters;
  chips: string[];
  parse_engine: string;
}

export interface Catalog {
  amenities: { key: string; label: string }[];
  districts: string[];
  schools: { id: number; name: string; short_name: string; district: string }[];
  room_types: { key: string; label: string }[];
  report_reasons: { key: string; label: string }[];
}
