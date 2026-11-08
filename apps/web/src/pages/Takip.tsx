import { useEffect, useState } from "react";
import { CBadge, CButton, CCard, CCardHeader } from "@coreui/react";
import CIcon from "@coreui/icons-react";
import { cilX } from "@coreui/icons";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { useLiveVehicles } from "../live-data";
import { LoadingNote } from "../loading";
import { FleetMap } from "./FleetMap";
import { LiveLegend } from "./LiveLegend";
import {
  MOTION_STATE_COLOR,
  MOTION_STATE_LABEL,
  TRAILER_LABEL,
  VEHICLE_STATE_COLOR,
  VEHICLE_STATE_LABEL,
  clock,
  signalLabel,
  type MotionState,
  type VehicleState,
} from "../labels";
import { useSession } from "../session";
import type { Driver, LiveVehicle, Load, Settings, Vehicle } from "../types";

export function Takip({ initialVehicle = "" }: { initialVehicle?: string }) {
  const { token } = useSession();
  const { settings, vehicles: fleet, drivers } = useFleet();
  const [loads, setLoads] = useState<Load[]>([]);
  const staleMinutes = settings?.gps_stale_minutes ?? 15;
  const { vehicles, link, loading, tick, states, motions, counts, motionCounts } = useLiveVehicles(staleMinutes);
  const [selected, setSelected] = useState<string | null>(initialVehicle || null);

  useEffect(() => {
    if (initialVehicle) setSelected(initialVehicle);
  }, [initialVehicle]);

  useEffect(() => {
    if (!selected) return;
    api<Load[]>("/loads", token)
      .then(setLoads)
      .catch(() => setLoads([]));
  }, [selected, token]);

  return (
    <div className="d-flex flex-column flex-lg-row gap-3" style={{ height: undefined, minHeight: 480 }}>
      <CCard className="d-flex flex-column order-2 order-lg-1" style={{ width: 340, maxWidth: "100%", minHeight: 0, height: "min(420px, 50dvh)" }}>
        <CCardHeader>
          <strong>Araçlar</strong>
          <div className="small text-body-secondary">
            {link} · {vehicles.length} araç
          </div>
        </CCardHeader>
        <LiveLegend dutyCounts={counts} motionCounts={motionCounts} />
        <div className="list-scroll">
          {loading ? (
            <LoadingNote label="Harita yükleniyor…" />
          ) : vehicles.length === 0 ? (
            <div className="text-body-secondary px-3 pb-3">Kayıtlı araç yok</div>
          ) : null}
          {vehicles.map((vehicle) => {
            const duty = states.get(vehicle.id) ?? "bayat";
            const motion = motions.get(vehicle.id);
            const active = vehicle.id === selected;
            return (
              <button
                key={vehicle.id}
                type="button"
                className={`w-100 border-0 border-bottom text-start px-3 py-2 d-flex align-items-start ${active ? "bg-body-secondary" : "bg-transparent"}`}
                onClick={() => setSelected(vehicle.id)}
              >
                <span className="legend-dot me-2 mt-1" style={{ backgroundColor: VEHICLE_STATE_COLOR[duty] }} />
                <span className="min-w-0">
                  <span className="d-block text-truncate">
                    {vehicle.plate} · {VEHICLE_STATE_LABEL[duty]}
                    {motion ? ` · ${MOTION_STATE_LABEL[motion]}` : ""}
                  </span>
                  <span className="d-block small text-body-secondary text-truncate">
                    {vehicle.driver_name ?? "Şoför yok"} · {vehicle.speed_kmh ?? "0.0"} km/s · {signalLabel(vehicle.recorded_at)}
                  </span>
                  <span className="d-block small text-body-secondary text-truncate">
                    {vehicle.latitude && vehicle.longitude ? `${vehicle.latitude}, ${vehicle.longitude}` : "Konum yok"}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </CCard>
      <CCard className="flex-grow-1 order-1 order-lg-2 position-relative d-flex flex-column" style={{ minWidth: 0, minHeight: 320, height: "50dvh" }}>
        {loading ? (
          <div
            className="position-absolute top-0 start-0 end-0 bottom-0 d-flex align-items-center justify-content-center"
            style={{ zIndex: 2, background: "rgba(255,255,255,0.72)" }}
          >
            <LoadingNote label="Harita yükleniyor…" />
          </div>
        ) : null}
        <FleetMap vehicles={vehicles} selectedId={selected} states={states} motions={motions} tick={tick} onSelect={setSelected} />
        {(() => {
          const live = vehicles.find((item) => item.id === selected);
          if (!live) return null;
          return (
            <VehiclePopup
              live={live}
              state={states.get(live.id) ?? "bayat"}
              motion={motions.get(live.id) ?? null}
              vehicle={fleet.find((item) => item.id === live.id) ?? null}
              driver={drivers.find((item) => item.id === fleet.find((row) => row.id === live.id)?.driver_id) ?? null}
              load={loads.find((item) => item.vehicle_id === live.id && (item.status === "atandi" || item.status === "yolda")) ?? null}
              settings={settings}
              onClose={() => setSelected(null)}
            />
          );
        })()}
      </CCard>
    </div>
  );
}

function minutes(value: number | null): string {
  if (value === null || value === undefined) return "—";
  const rest = Math.max(0, value);
  const hours = Math.floor(rest / 60);
  const mins = rest % 60;
  return hours ? `${hours} sa ${mins} dk` : `${mins} dk`;
}

function remain(limit: number | undefined, used: number | null): string {
  if (limit === undefined || used === null || used === undefined) return "—";
  return minutes(limit - used);
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="d-flex justify-content-between gap-3">
      <span className="small text-body-secondary flex-shrink-0">{label}</span>
      <span className="small text-end" style={{ minWidth: 0, overflowWrap: "anywhere" }}>
        {value}
      </span>
    </div>
  );
}

function VehiclePopup({
  live,
  state,
  motion,
  vehicle,
  driver,
  load,
  settings,
  onClose,
}: {
  live: LiveVehicle;
  state: VehicleState;
  motion: MotionState | null;
  vehicle: Vehicle | null;
  driver: Driver | null;
  load: Load | null;
  settings: Settings | null;
  onClose: () => void;
}) {
  const hasPoint = live.latitude && live.longitude;
  const source = vehicle?.tacho_source;
  return (
    <CCard className="vehicle-popup shadow p-3" style={{ top: 12, right: 12, bottom: "auto", left: "auto" }}>
      <div className="d-flex align-items-start justify-content-between mb-2 gap-2">
        <div className="d-flex align-items-center flex-wrap gap-2">
          <h2 className="h5 mb-0">{live.plate}</h2>
          <CBadge style={{ backgroundColor: VEHICLE_STATE_COLOR[state] }}>{VEHICLE_STATE_LABEL[state]}</CBadge>
          {motion ? <CBadge style={{ backgroundColor: MOTION_STATE_COLOR[motion] }}>{MOTION_STATE_LABEL[motion]}</CBadge> : null}
        </div>
        <CButton color="secondary" variant="ghost" size="sm" onClick={onClose} aria-label="Kapat">
          <CIcon icon={cilX} />
        </CButton>
      </div>
      <div className="d-flex flex-column gap-1">
        <Row label="Şoför" value={live.driver_name ?? "Şoför yok"} />
        {driver ? <Row label="Telefon" value={driver.phone || "Yok"} /> : null}
        <Row label="Hız" value={`${live.speed_kmh ?? "0.0"} km/s`} />
        <Row label="Son sinyal" value={live.recorded_at ? `${clock(live.recorded_at)} (${signalLabel(live.recorded_at)})` : "Yok"} />
        <Row label="Konum" value={hasPoint ? `${live.latitude}, ${live.longitude}` : "Konum yok"} />
        {hasPoint ? (
          <a href={`https://www.google.com/maps?q=${live.latitude},${live.longitude}`} target="_blank" rel="noreferrer" className="small">
            Google Haritalar'da aç
          </a>
        ) : null}
      </div>
      <hr />
      <div className="d-flex flex-column gap-1">
        <Row label="Kasa" value={vehicle ? TRAILER_LABEL[vehicle.trailer_type] ?? vehicle.trailer_type : "—"} />
        <Row label="Kapasite" value={vehicle ? `${vehicle.capacity_tons} ton` : "—"} />
        <Row label="Cihaz no" value={vehicle?.device_id ?? "—"} />
      </div>
      <hr />
      <div className="fw-semibold small mb-1">Takograf {source ? `· ${source === "olculmus" ? "ölçülmüş" : "tahmini"}` : ""}</div>
      {source ? (
        <div className="d-flex flex-column gap-1">
          <Row label="Kesintisiz sürüş kalan" value={remain(settings?.tacho_continuous_min, vehicle?.tacho_continuous_min ?? null)} />
          <Row label="Günlük kalan" value={remain(settings?.tacho_daily_min, vehicle?.tacho_daily_min ?? null)} />
          <Row label="Haftalık kalan" value={remain(settings?.tacho_weekly_min, vehicle?.tacho_weekly_min ?? null)} />
        </div>
      ) : (
        <div className="small text-body-secondary">Sayaç yok</div>
      )}
      <hr />
      <div className="fw-semibold small mb-1">Açık sefer</div>
      {load ? (
        <div className="d-flex flex-column gap-1">
          <Row label="Referans" value={load.reference} />
          <Row label="Güzergâh" value={`${load.pickup_il} → ${load.drop_il}`} />
          <Row label="Teslim" value={`${clock(load.deliver_start)} – ${clock(load.deliver_end)}`} />
        </div>
      ) : (
        <div className="small text-body-secondary">Yok</div>
      )}
    </CCard>
  );
}
