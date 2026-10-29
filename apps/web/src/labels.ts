import type { Driver, Page, Role, Settings, Vehicle } from "./types";

export const ROLE_LABEL: Record<Role, string> = {
  platform_admin: "Platform yöneticisi",
  tenant_admin: "Firma yöneticisi",
  dispatcher: "Operasyoncu",
  viewer: "İzleyici",
};

export const PAGE_LABEL: Record<Page, string> = {
  firmalar: "Firmalar",
  masa: "Özet",
  gidis: "Gidiş kuyruğu",
  donus: "Dönüş havuzu",
  takip: "Takip",
  araclar: "Araçlar",
  soforler: "Şoförler",
  ayarlar: "Ayarlar",
  kullanicilar: "Kullanıcılar",
};

export const LOAD_STATUS_LABEL: Record<string, string> = {
  planlanabilir: "Planlanabilir",
  havuz: "Havuz",
  onerildi: "Önerildi",
  atandi: "Atandı",
  yolda: "Yolda",
  teslim: "Teslim",
  iptal: "İptal",
};

export const TRAILER_LABEL: Record<string, string> = {
  tenteli: "Tenteli",
  frigolu: "Frigolu",
  sal: "Sal",
  lowbed: "Lowbed",
  tanker: "Tanker",
};

export const STATUS_LABEL: Record<string, string> = {
  serviste: "Serviste",
  bakimda: "Bakımda",
  ariza: "Arıza",
};

export const CATALOG = ["tenteli", "frigolu", "sal", "lowbed", "tanker"];

export function pagesFor(role: Role): Page[] {
  if (role === "platform_admin") return ["firmalar"];
  const pages: Page[] = ["masa", "gidis", "donus", "takip", "araclar", "soforler"];
  if (role === "tenant_admin") pages.push("ayarlar", "kullanicilar");
  return pages;
}

export function canWriteMaster(role: Role): boolean {
  return role === "tenant_admin";
}

export function canOperate(role: Role): boolean {
  return role === "tenant_admin" || role === "dispatcher";
}

export function driverName(drivers: Driver[], driverId: string | null): string {
  if (!driverId) return "Şoför yok";
  return drivers.find((driver) => driver.id === driverId)?.name ?? "Şoför yok";
}

export function signalLabel(recordedAt: string | null): string {
  if (!recordedAt) return "Sinyal yok";
  const minutes = Math.max(0, Math.round((Date.now() - new Date(recordedAt).getTime()) / 60000));
  if (minutes < 1) return "Az önce";
  if (minutes < 60) return `${minutes} dk`;
  return `${Math.round(minutes / 60)} sa`;
}

export function availability(vehicle: Vehicle, settings: Settings | null): string {
  if (vehicle.status === "bakimda") return "Bakım";
  if (vehicle.status === "ariza") return "Arıza";
  if (!vehicle.recorded_at || !settings) return "Sinyal yok";
  const age = Date.now() - new Date(vehicle.recorded_at).getTime();
  if (age > settings.gps_stale_minutes * 60_000) return "Bayat sinyal";
  if (!vehicle.driver_id) return "Şoför yok";
  if (vehicle.duty === "yuklu") return "Yüklü";
  return "Boş";
}

export const REJECT_LABEL: Record<string, string> = {
  VEHICLE_NOT_IN_SERVICE: "Serviste değil",
  STALE_POSITION: "Bayat sinyal",
  NO_DRIVER: "Şoför yok",
  CAPACITY: "Tonaj sığmıyor",
  TRAILER: "Kasa uymuyor",
  OVERLAP: "Saat çakışıyor",
  ROW_REQUIRED: "Zorunlu alan boş",
  ROW_TONNAGE: "Tonaj geçersiz",
  ROW_WINDOW: "Teslim penceresi hatalı",
  ROW_PLACE: "İl veya ilçe sözlükte yok",
  ROW_TRAILER: "Kasa tipi kapalı",
  ROW_FREIGHT: "Dönüş navlunu yok",
  ROW_DIRECTION: "Yön geçersiz",
  ROW_LOCKED: "Atanmış referans",
  ROW_GEOCODE: "Koordinat çözülemedi",
  FILE_TOO_LARGE: "Dosya 2000 satırı aşıyor",
  FILE_COLUMNS: "Kolonlar eksik",
  LOAD_NOT_READY: "Yük atanamaz",
  TACHO_UNKNOWN: "Takograf sayacı yok",
  TACHO_DAILY: "Günlük sürüş dolu",
  TACHO_WEEKLY: "Haftalık sürüş dolu",
  TACHO_FORTNIGHT: "İki haftalık sürüş dolu",
  DUSUK_FAYDA: "Daha düşük fayda",
};

export const ALERT_LABEL: Record<string, string> = {
  BREAK_WARNING: "Mola yaklaşıyor",
  BREAK_OVERDUE: "Mola zamanı geçti",
  DAILY_DRIVING_WARNING: "Günlük sürüş dolmak üzere",
  DAILY_DRIVING_LIMIT: "Günlük sürüş doldu",
  WEEKLY_DRIVING_WARNING: "Haftalık sürüş dolmak üzere",
  WEEKLY_DRIVING_LIMIT: "Haftalık sürüş doldu",
  FORTNIGHT_DRIVING_WARNING: "İki haftalık sürüş dolmak üzere",
  FORTNIGHT_DRIVING_LIMIT: "İki haftalık sürüş doldu",
  TACHO_ESTIMATED: "Sayaç tahmini",
  PLAN_INFEASIBLE: "Açık sefer süreye sığmıyor",
  SMS_UNDELIVERED: "SMS telefona ulaşmadı",
  SMS_NO_PHONE: "Şoförün telefonu yok",
  SMS_REJECTED: "SMS kabul edilmedi",
};

export function clock(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    timeZone: "Europe/Istanbul",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
