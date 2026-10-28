export type Role = "platform_admin" | "tenant_admin" | "dispatcher" | "viewer";

export type User = {
  id: string;
  email: string;
  role: Role;
  tenant_id: string | null;
  active: boolean;
};

export type Tenant = {
  id: string;
  name: string;
  code: string;
  status: string;
};

export type Vehicle = {
  id: string;
  plate: string;
  capacity_tons: string;
  trailer_type: string;
  tare_tons: string | null;
  status: string;
  device_id: string | null;
  driver_id: string | null;
  latitude: string | null;
  longitude: string | null;
  speed_kmh: string | null;
  recorded_at: string | null;
  duty: string;
  tacho_source: string | null;
  tacho_continuous_min: number | null;
  tacho_daily_min: number | null;
  tacho_weekly_min: number | null;
  tacho_fortnight_min: number | null;
};

export type Driver = {
  id: string;
  name: string;
  phone: string;
  card_id: string | null;
};

export type Settings = {
  enabled_trailer_types: string[];
  empty_km_cost: string | null;
  loaded_km_cost: string | null;
  gps_stale_minutes: number;
  arvento_configured: boolean;
  tacho_continuous_min: number;
  tacho_daily_min: number;
  tacho_extended_min: number;
  tacho_extensions: number;
  tacho_weekly_min: number;
  tacho_fortnight_min: number;
  tacho_warning_min: number;
  return_approval: boolean;
  auto_assign_estimated: boolean;
  netgsm_configured: boolean;
};

export type Page = "firmalar" | "masa" | "gidis" | "donus" | "takip" | "uyarilar" | "araclar" | "soforler" | "ayarlar" | "kullanicilar";

export type LiveVehicle = {
  id: string;
  plate: string;
  status: string;
  duty: string;
  driver_name: string | null;
  latitude: string | null;
  longitude: string | null;
  speed_kmh: string | null;
  course: string | null;
  recorded_at: string | null;
};

export type AlertItem = {
  id: string;
  vehicle_id: string | null;
  code: string;
  level: string;
  measured: number;
  limit_value: number;
  seen_at: string | null;
};

export type Load = {
  id: string;
  reference: string;
  direction: "gidis" | "donus";
  pickup_il: string;
  pickup_ilce: string;
  drop_il: string;
  drop_ilce: string;
  pickup_lat: string | null;
  pickup_lng: string | null;
  drop_lat: string | null;
  drop_lng: string | null;
  geocode_quality: string;
  tonnage: string;
  trailer_type: string;
  ready_at: string;
  deliver_start: string;
  deliver_end: string;
  freight_try: string | null;
  customer: string | null;
  broker_firm: string | null;
  status: string;
  vehicle_id: string | null;
  empty_km: string | null;
  loaded_km: string | null;
  distance_quality: string | null;
  benefit_try: string | null;
  locked: boolean;
  sms_status: string | null;
  sms_job_id: string | null;
  tacho_source: string | null;
  tacho_continuous_min: number | null;
  tacho_daily_min: number | null;
  tacho_weekly_min: number | null;
  tacho_continuous_remain: number | null;
  tacho_daily_remain: number | null;
  tacho_weekly_remain: number | null;
  tacho_fortnight_remain: number | null;
  planned_break_min: number | null;
  calculated_at: string | null;
  rule_pack: string;
  empty_km_cost: string | null;
  loaded_km_cost: string | null;
  alternatives: { reference: string; code: string }[];
};

export type Candidate = {
  vehicle_id: string;
  plate: string;
  eligible: boolean;
  code: string | null;
  empty_km: string | null;
  loaded_km: string | null;
  rank: string | null;
  distance_quality: string | null;
};

export type ImportResult = {
  accepted: number;
  updated: number;
  rejected: { row: number; reference: string; code: string }[];
};
