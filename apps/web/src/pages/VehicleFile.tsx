import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";
import {
  CButton,
  CCard,
  CCardBody,
  CCardHeader,
  CFormInput,
  CFormLabel,
  CFormSelect,
  CNav,
  CNavItem,
  CNavLink,
} from "@coreui/react";
import { api } from "../api";
import { STATUS_LABEL, TRAILER_LABEL, availability, canOperate, canWriteMaster, driverName, signalLabel } from "../labels";
import { useSession } from "../session";
import type { Driver, Settings, Vehicle, VehicleDossier } from "../types";

const MAINT_KIND = [
  ["periyodik", "Periyodik"],
  ["ariza", "Arıza"],
  ["muayene", "Muayene"],
  ["diger", "Diğer"],
] as const;

const TIRE_POS = [
  ["FL", "Ön sol"],
  ["FR", "Ön sağ"],
  ["RL", "Arka sol"],
  ["RR", "Arka sağ"],
  ["RLO", "Arka sol dış"],
  ["RRO", "Arka sağ dış"],
  ["stepne", "Stepne"],
  ["diger", "Diğer"],
] as const;

const TIRE_EVENT = [
  ["takildi", "Takıldı"],
  ["sokuldu", "Söküldü"],
  ["degisti", "Değişti"],
  ["basinc", "Basınç"],
] as const;

const TABS = ["Özet", "Bakım", "Lastik", "Yakıt", "Kullanım"] as const;

function stamp(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
}

export function VehicleFile({
  vehicle,
  drivers,
  settings,
  onChanged,
  onClose,
}: {
  vehicle: Vehicle;
  drivers: Driver[];
  settings: Settings | null;
  onChanged: () => Promise<void>;
  onClose: () => void;
}) {
  const { token, user, notice } = useSession();
  const [tab, setTab] = useState(0);
  const [dossier, setDossier] = useState<VehicleDossier | null>(null);
  const [status, setStatus] = useState(vehicle.status);
  const [driverId, setDriverId] = useState(vehicle.driver_id ?? "");
  const [latitude, setLatitude] = useState(vehicle.latitude ?? "");
  const [longitude, setLongitude] = useState(vehicle.longitude ?? "");
  const [speed, setSpeed] = useState(vehicle.speed_kmh ?? "0");

  const loadDossier = useCallback(async () => {
    try {
      setDossier(await api<VehicleDossier>(`/vehicles/${vehicle.id}/dossier`, token));
    } catch (err) {
      notice(err instanceof Error ? err.message : "Özlük dosyası açılamadı");
    }
  }, [notice, token, vehicle.id]);

  useEffect(() => {
    setStatus(vehicle.status);
    setDriverId(vehicle.driver_id ?? "");
    setLatitude(vehicle.latitude ?? "");
    setLongitude(vehicle.longitude ?? "");
    setSpeed(vehicle.speed_kmh ?? "0");
  }, [vehicle]);

  useEffect(() => {
    void loadDossier();
  }, [loadDossier]);

  async function saveMaster(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      await api(`/vehicles/${vehicle.id}`, token, {
        method: "PATCH",
        body: JSON.stringify({ status, driver_id: driverId || null }),
      });
      await onChanged();
      await loadDossier();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Araç kaydı güncellenemedi");
    }
  }

  async function savePosition(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      await api(`/vehicles/${vehicle.id}/position`, token, {
        method: "POST",
        body: JSON.stringify({
          latitude,
          longitude,
          speed_kmh: speed || "0",
          recorded_at: new Date().toISOString(),
        }),
      });
      await onChanged();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Konum yazılamadı");
    }
  }

  const facts = [
    ["Durum", STATUS_LABEL[vehicle.status] ?? vehicle.status],
    ["Şoför", dossier?.driver_name ?? driverName(drivers, vehicle.driver_id)],
    ["Km", dossier?.odometer_km ? `${dossier.odometer_km} km` : "—"],
    ["Depo", dossier?.last_fuel_level_pct != null ? `%${dossier.last_fuel_level_pct}` : "—"],
    ["Son dolum", stamp(dossier?.last_fuel_fill_at)],
    ["Son bakım", stamp(dossier?.last_maintenance_at)],
    ["Sinyal", signalLabel(vehicle.recorded_at)],
    ["Konum", vehicle.latitude && vehicle.longitude ? `${vehicle.latitude}, ${vehicle.longitude} · ${vehicle.speed_kmh ?? "0"} km/s` : "Konum yok"],
    ["Cihaz", vehicle.device_id ?? "Yok"],
    [
      "Takograf",
      vehicle.tacho_source
        ? `${vehicle.tacho_daily_min ?? 0} dk günlük · ${vehicle.tacho_weekly_min ?? 0} dk haftalık · ${vehicle.tacho_source === "tahmini" ? "tahmini" : "ölçülmüş"}`
        : "Sayaç yok",
    ],
  ];

  return (
    <CCard>
      <CCardHeader className="d-flex flex-column flex-sm-row justify-content-between gap-2 align-items-sm-start">
        <div>
          <strong>{vehicle.plate}</strong>
          <div className="small text-body-secondary">
            {TRAILER_LABEL[vehicle.trailer_type] ?? vehicle.trailer_type} · {vehicle.capacity_tons} ton · {availability(vehicle, settings)}
          </div>
        </div>
        <CButton color="secondary" variant="outline" size="sm" onClick={onClose}>
          Listeye dön
        </CButton>
      </CCardHeader>
      <CCardBody>
        <CNav variant="tabs" role="tablist" className="mb-3 flex-nowrap overflow-auto">
          {TABS.map((label, index) => (
            <CNavItem key={label}>
              <CNavLink
                href="#"
                active={tab === index}
                onClick={(event) => {
                  event.preventDefault();
                  setTab(index);
                }}
                style={{ whiteSpace: "nowrap" }}
              >
                {label}
              </CNavLink>
            </CNavItem>
          ))}
        </CNav>

        {tab === 0 ? (
          <div className="d-flex flex-column gap-3">
            <div className="d-flex flex-column gap-3">
              {facts.map(([label, value]) => (
                <div key={label}>
                  <div className="small text-body-secondary">{label}</div>
                  <div>{value}</div>
                </div>
              ))}
            </div>
            {canWriteMaster(user.role) ? (
              <form className="d-flex flex-column gap-3" onSubmit={saveMaster}>
                <h2 className="h5 mb-0">Kayıt</h2>
                <div>
                  <CFormLabel>Durum</CFormLabel>
                  <CFormSelect value={status} onChange={(event) => setStatus(event.target.value)}>
                    {Object.entries(STATUS_LABEL).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </CFormSelect>
                </div>
                <div>
                  <CFormLabel>Bağlı şoför</CFormLabel>
                  <CFormSelect value={driverId} onChange={(event) => setDriverId(event.target.value)}>
                    <option value="">Şoför yok</option>
                    {drivers.map((driver) => (
                      <option key={driver.id} value={driver.id}>
                        {driver.name}
                      </option>
                    ))}
                  </CFormSelect>
                </div>
                <CButton type="submit" color="primary">
                  Kaydet
                </CButton>
              </form>
            ) : null}
            {canOperate(user.role) ? (
              <form className="d-flex flex-column gap-3" onSubmit={savePosition}>
                <h2 className="h5 mb-0">Elle konum</h2>
                <div>
                  <CFormLabel>Enlem</CFormLabel>
                  <CFormInput value={latitude} onChange={(event) => setLatitude(event.target.value)} required />
                </div>
                <div>
                  <CFormLabel>Boylam</CFormLabel>
                  <CFormInput value={longitude} onChange={(event) => setLongitude(event.target.value)} required />
                </div>
                <div>
                  <CFormLabel>Hız (km/s)</CFormLabel>
                  <CFormInput value={speed} onChange={(event) => setSpeed(event.target.value)} />
                </div>
                <CButton type="submit" color="primary">
                  Konumu yaz
                </CButton>
              </form>
            ) : null}
          </div>
        ) : null}

        {tab === 1 ? (
          <HistoryTab
            title="Bakım geçmişi"
            canWrite={canOperate(user.role)}
            rows={(dossier?.maintenances ?? []).map(
              (row) =>
                `${stamp(row.happened_at)} · ${row.kind} · ${row.odometer_km ?? "—"} km · ${row.workshop ?? ""} ${row.cost_try ? `· ${row.cost_try} TL` : ""}`,
            )}
            form={
              <MaintenanceForm
                defaultKm={dossier?.odometer_km ?? ""}
                onSaved={async () => {
                  await loadDossier();
                }}
                vehicleId={vehicle.id}
              />
            }
          />
        ) : null}

        {tab === 2 ? (
          <HistoryTab
            title="Lastik geçmişi"
            canWrite={canOperate(user.role)}
            rows={(dossier?.tire_events ?? []).map(
              (row) =>
                `${stamp(row.happened_at)} · ${row.position} · ${row.event} · ${row.brand_size ?? ""} · ${row.odometer_km ?? "—"} km`,
            )}
            form={
              <TireForm
                defaultKm={dossier?.odometer_km ?? ""}
                onSaved={async () => {
                  await loadDossier();
                }}
                vehicleId={vehicle.id}
              />
            }
          />
        ) : null}

        {tab === 3 ? (
          <div className="d-flex flex-column gap-3">
            <HistoryTab
              title="Yakıt alma"
              canWrite={canOperate(user.role)}
              rows={(dossier?.fuel_fills ?? []).map(
                (row) =>
                  `${stamp(row.happened_at)} · ${row.liters ?? "—"} L · ${row.amount_try ?? "—"} TL · ${row.station ?? row.source} · ${row.odometer_km ?? "—"} km`,
              )}
              form={
                <FuelForm
                  defaultKm={dossier?.odometer_km ?? ""}
                  onSaved={async () => {
                    await loadDossier();
                  }}
                  vehicleId={vehicle.id}
                />
              }
            />
            {(dossier?.fuel_samples.length ?? 0) > 0 ? (
              <div className="d-flex flex-column gap-2">
                <div className="fw-semibold">Seyir depo örnekleri</div>
                {(dossier?.fuel_samples ?? []).slice(0, 12).map((row) => (
                  <div key={row.id} className="small text-body-secondary">
                    {stamp(row.recorded_at)} · {row.level_pct != null ? `%${row.level_pct}` : `${row.level_liters} L`} · {row.odometer_km ?? "—"}{" "}
                    km
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {tab === 4 ? (
          <div className="d-flex flex-column gap-3">
            <h2 className="h5 mb-0">Şoför kullanım</h2>
            {(dossier?.driver_stints ?? []).length === 0 ? <div className="text-body-secondary">Stint yok</div> : null}
            {(dossier?.driver_stints ?? []).map((row) => (
              <div key={row.id}>
                <button
                  type="button"
                  className="btn btn-link p-0 text-decoration-none"
                  onClick={() => {
                    window.location.hash = `takograf/${row.driver_id}`;
                  }}
                >
                  {row.driver_name}
                </button>
                <div className="small text-body-secondary">
                  {stamp(row.started_at)} → {row.ended_at ? stamp(row.ended_at) : "açık"} · {row.source}
                </div>
              </div>
            ))}
            <hr />
            <h2 className="h5 mb-0">Yükler</h2>
            {(dossier?.usage_loads ?? []).length === 0 ? <div className="text-body-secondary">Yük yok</div> : null}
            {(dossier?.usage_loads ?? []).map((row) => (
              <div key={row.id} className="small">
                {row.reference} · {row.direction} · {row.status} · {stamp(row.ready_at)}
              </div>
            ))}
          </div>
        ) : null}
      </CCardBody>
    </CCard>
  );
}

function HistoryTab({
  title,
  rows,
  form,
  canWrite,
}: {
  title: string;
  rows: string[];
  form: ReactNode;
  canWrite: boolean;
}) {
  return (
    <div className="d-flex flex-column gap-3">
      <h2 className="h5 mb-0">{title}</h2>
      {rows.length === 0 ? <div className="text-body-secondary">Kayıt yok</div> : null}
      {rows.map((row) => (
        <div key={row} className="small">
          {row}
        </div>
      ))}
      {canWrite ? form : null}
    </div>
  );
}

function MaintenanceForm({ vehicleId, defaultKm, onSaved }: { vehicleId: string; defaultKm: string; onSaved: () => Promise<void> }) {
  const { token, notice } = useSession();
  const [kind, setKind] = useState("periyodik");
  const [happenedAt, setHappenedAt] = useState(() => localInputNow());
  const [odometer, setOdometer] = useState(defaultKm);
  const [cost, setCost] = useState("");
  const [workshop, setWorkshop] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => setOdometer(defaultKm), [defaultKm]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      await api(`/vehicles/${vehicleId}/maintenances`, token, {
        method: "POST",
        body: JSON.stringify({
          kind,
          happened_at: new Date(happenedAt).toISOString(),
          odometer_km: odometer || null,
          cost_try: cost || null,
          workshop: workshop || null,
          note: note || null,
        }),
      });
      setNote("");
      setCost("");
      await onSaved();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Bakım kaydı yazılamadı");
    }
  }

  return (
    <form className="d-flex flex-column gap-3" onSubmit={submit}>
      <div className="fw-semibold">Yeni bakım</div>
      <div>
        <CFormLabel>Tür</CFormLabel>
        <CFormSelect value={kind} onChange={(event) => setKind(event.target.value)}>
          {MAINT_KIND.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </CFormSelect>
      </div>
      <div>
        <CFormLabel>Tarih</CFormLabel>
        <CFormInput type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} required />
      </div>
      <div>
        <CFormLabel>Km</CFormLabel>
        <CFormInput value={odometer} onChange={(event) => setOdometer(event.target.value)} />
      </div>
      <div>
        <CFormLabel>Tutar (TL)</CFormLabel>
        <CFormInput value={cost} onChange={(event) => setCost(event.target.value)} />
      </div>
      <div>
        <CFormLabel>Servis</CFormLabel>
        <CFormInput value={workshop} onChange={(event) => setWorkshop(event.target.value)} />
      </div>
      <div>
        <CFormLabel>Not</CFormLabel>
        <CFormInput value={note} onChange={(event) => setNote(event.target.value)} />
      </div>
      <CButton type="submit" color="primary">
        Ekle
      </CButton>
    </form>
  );
}

function TireForm({ vehicleId, defaultKm, onSaved }: { vehicleId: string; defaultKm: string; onSaved: () => Promise<void> }) {
  const { token, notice } = useSession();
  const [position, setPosition] = useState("FL");
  const [eventKind, setEventKind] = useState("degisti");
  const [brand, setBrand] = useState("");
  const [happenedAt, setHappenedAt] = useState(() => localInputNow());
  const [odometer, setOdometer] = useState(defaultKm);
  const [note, setNote] = useState("");

  useEffect(() => setOdometer(defaultKm), [defaultKm]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      await api(`/vehicles/${vehicleId}/tire-events`, token, {
        method: "POST",
        body: JSON.stringify({
          position,
          event: eventKind,
          brand_size: brand || null,
          happened_at: new Date(happenedAt).toISOString(),
          odometer_km: odometer || null,
          note: note || null,
        }),
      });
      setBrand("");
      setNote("");
      await onSaved();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Lastik kaydı yazılamadı");
    }
  }

  return (
    <form className="d-flex flex-column gap-3" onSubmit={submit}>
      <div className="fw-semibold">Yeni lastik olayı</div>
      <div>
        <CFormLabel>Konum</CFormLabel>
        <CFormSelect value={position} onChange={(event) => setPosition(event.target.value)}>
          {TIRE_POS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </CFormSelect>
      </div>
      <div>
        <CFormLabel>Olay</CFormLabel>
        <CFormSelect value={eventKind} onChange={(event) => setEventKind(event.target.value)}>
          {TIRE_EVENT.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </CFormSelect>
      </div>
      <div>
        <CFormLabel>Marka / ebat</CFormLabel>
        <CFormInput value={brand} onChange={(event) => setBrand(event.target.value)} />
      </div>
      <div>
        <CFormLabel>Tarih</CFormLabel>
        <CFormInput type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} required />
      </div>
      <div>
        <CFormLabel>Km</CFormLabel>
        <CFormInput value={odometer} onChange={(event) => setOdometer(event.target.value)} />
      </div>
      <div>
        <CFormLabel>Not</CFormLabel>
        <CFormInput value={note} onChange={(event) => setNote(event.target.value)} />
      </div>
      <CButton type="submit" color="primary">
        Ekle
      </CButton>
    </form>
  );
}

function FuelForm({ vehicleId, defaultKm, onSaved }: { vehicleId: string; defaultKm: string; onSaved: () => Promise<void> }) {
  const { token, notice } = useSession();
  const [happenedAt, setHappenedAt] = useState(() => localInputNow());
  const [liters, setLiters] = useState("");
  const [amount, setAmount] = useState("");
  const [odometer, setOdometer] = useState(defaultKm);
  const [station, setStation] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => setOdometer(defaultKm), [defaultKm]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      await api(`/vehicles/${vehicleId}/fuel-fills`, token, {
        method: "POST",
        body: JSON.stringify({
          happened_at: new Date(happenedAt).toISOString(),
          liters: liters || null,
          amount_try: amount || null,
          odometer_km: odometer || null,
          station: station || null,
          note: note || null,
        }),
      });
      setLiters("");
      setAmount("");
      setStation("");
      setNote("");
      await onSaved();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Yakıt kaydı yazılamadı");
    }
  }

  return (
    <form className="d-flex flex-column gap-3" onSubmit={submit}>
      <div className="fw-semibold">Yeni dolum</div>
      <div>
        <CFormLabel>Tarih</CFormLabel>
        <CFormInput type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} required />
      </div>
      <div>
        <CFormLabel>Litre</CFormLabel>
        <CFormInput value={liters} onChange={(event) => setLiters(event.target.value)} />
      </div>
      <div>
        <CFormLabel>Tutar (TL)</CFormLabel>
        <CFormInput value={amount} onChange={(event) => setAmount(event.target.value)} />
      </div>
      <div>
        <CFormLabel>Km</CFormLabel>
        <CFormInput value={odometer} onChange={(event) => setOdometer(event.target.value)} />
      </div>
      <div>
        <CFormLabel>İstasyon</CFormLabel>
        <CFormInput value={station} onChange={(event) => setStation(event.target.value)} />
      </div>
      <div>
        <CFormLabel>Not</CFormLabel>
        <CFormInput value={note} onChange={(event) => setNote(event.target.value)} />
      </div>
      <CButton type="submit" color="primary">
        Ekle
      </CButton>
    </form>
  );
}

function localInputNow() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}
