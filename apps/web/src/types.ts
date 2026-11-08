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

export type VehicleDossier = {
  vehicle_id: string;
  plate: string;
  odometer_km: string | null;
  driver_id: string | null;
  driver_name: string | null;
  open_stint_started_at: string | null;
  last_fuel_fill_at: string | null;
  last_maintenance_at: string | null;
  last_fuel_level_pct: string | null;
  maintenances: {
    id: string;
    kind: string;
    happened_at: string;
    odometer_km: string | null;
    cost_try: string | null;
    workshop: string | null;
    note: string | null;
    source: string;
  }[];
  tire_events: {
    id: string;
    position: string;
    event: string;
    brand_size: string | null;
    odometer_km: string | null;
    happened_at: string;
    note: string | null;
    source: string;
  }[];
  fuel_fills: {
    id: string;
    happened_at: string;
    liters: string | null;
    amount_try: string | null;
    odometer_km: string | null;
    station: string | null;
    source: string;
    note: string | null;
  }[];
  fuel_samples: {
    id: string;
    recorded_at: string;
    level_pct: string | null;
    level_liters: string | null;
    odometer_km: string | null;
  }[];
  driver_stints: {
    id: string;
    driver_id: string;
    driver_name: string;
    started_at: string;
    ended_at: string | null;
    source: string;
  }[];
  usage_loads: {
    id: string;
    reference: string;
    direction: string;
    status: string;
    ready_at: string;
    delivered_at: string | null;
  }[];
};

export type Settings = {
  enabled_trailer_types: string[];
  empty_km_cost: string | null;
  loaded_km_cost: string | null;
  gps_stale_minutes: number;
  arvento_enabled: boolean;
  seyir_enabled: boolean;
  home_base_il: string | null;
  home_base_ilce: string | null;
  toll_enabled: boolean;
  arvento_configured: boolean;
  seyir_configured: boolean;
  enabled_telematics: string[];
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
  routes_today: number;
  routes_limit: number;
  routes_allowed: number;
  routes_cache_hits: number;
  routes_blocked: number;
  routes_needs_approval: boolean;
};

export type Page = "firmalar" | "masa" | "gidis" | "donus" | "takip" | "araclar" | "soforler" | "takograf" | "raporlar" | "ayarlar" | "kullanicilar";

export type ReportKpi = { key: string; label: string; value: string; hint?: string | null };
export type ReportSeriesPoint = { name: string; value: number };
export type Report = {
  slug: string;
  title: string;
  from_day: string;
  to_day: string;
  kpis: ReportKpi[];
  series: ReportSeriesPoint[];
  columns: string[];
  rows: Record<string, string | number>[];
};

export type TachoDriver = {
  driver_id: string;
  name: string;
  phone: string;
  card_id: string | null;
  plate: string | null;
  source: string | null;
  continuous_used: number;
  continuous_limit: number;
  continuous_remain: number;
  daily_used: number;
  daily_limit: number;
  daily_remain: number;
  weekly_used: number;
  weekly_limit: number;
  weekly_remain: number;
  fortnight_used: number;
  fortnight_limit: number;
  fortnight_remain: number;
  extensions_used: number;
  extensions_limit: number;
  warning: boolean;
  recorded_at: string | null;
  activity_status: string | null;
  daily_rest_remain_min: number | null;
  weekly_rest_remain_min: number | null;
};

export type TachoSample = {
  recorded_at: string;
  source: string;
  continuous_min: number;
  daily_min: number;
  weekly_min: number;
  fortnight_min: number;
  extensions_used: number;
};

export type TachoDriverDetail = TachoDriver & { samples: TachoSample[] };

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
  toll_try: string | null;
  base_km: string | null;
  chain_value_try: string | null;
  chain_note: string | null;
  driver_advice: string | null;
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
