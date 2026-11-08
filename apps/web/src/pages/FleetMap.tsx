import { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { VEHICLE_STATE_COLOR, VEHICLE_STATE_LABEL, signalLabel, type VehicleState } from "../labels";
import type { LiveVehicle } from "../types";

declare global {
  interface Window {
    google?: unknown;
  }
}

type LatLng = { lat: number; lng: number };

type GoogleMarker = {
  addListener: (event: string, handler: () => void) => unknown;
  setPosition: (position: LatLng) => void;
  setIcon: (icon: unknown) => void;
  setMap: (map: null) => void;
};

type GoogleInfo = {
  setContent: (content: string) => void;
  open: (options: { map: GoogleMap; anchor: GoogleMarker; shouldFocus?: boolean }) => void;
  close: () => void;
};

type GoogleMap = {
  panTo: (position: LatLng) => void;
  fitBounds: (bounds: unknown) => void;
};

type LiveGoogle = {
  maps: {
    Map: new (element: HTMLElement, options: Record<string, unknown>) => GoogleMap;
    Marker: new (options: Record<string, unknown>) => GoogleMarker;
    InfoWindow: new (options: Record<string, unknown>) => GoogleInfo;
    LatLngBounds: new () => { extend: (point: LatLng) => void; isEmpty: () => boolean };
    SymbolPath: { FORWARD_CLOSED_ARROW: number };
  };
};

const browserKey = import.meta.env.VITE_GOOGLE_MAPS_BROWSER_KEY as string | undefined;

export function FleetMap({ vehicles, selectedId, states, tick, onSelect }: { vehicles: LiveVehicle[]; selectedId: string | null; states: Map<string, VehicleState>; tick: number; onSelect: (id: string) => void }) {
  const pick = useRef(onSelect);
  pick.current = onSelect;
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<GoogleMap | null>(null);
  const markers = useRef(new Map<string, GoogleMarker>());
  const markerKey = useRef(new Map<string, string>());
  const fitted = useRef(false);
  const info = useRef<GoogleInfo | null>(null);
  const rows = useRef(vehicles);
  rows.current = vehicles;
  // Durum (states) tick ile yeniden hesaplanır; konum değişmeyince marker API çağrılmaz.
  const signature = vehicles.map((vehicle) => `${vehicle.id}:${vehicle.latitude}:${vehicle.longitude}:${vehicle.course}:${states.get(vehicle.id)}`).join("|");
  const colors = useRef(states);
  colors.current = states;

  useEffect(() => {
    if (!browserKey || !host.current || mapRef.current) return;
    let cancelled = false;
    loadMaps(browserKey).then((google) => {
      if (cancelled || !host.current || mapRef.current) return;
      info.current = new google.maps.InfoWindow({ disableAutoPan: true });
      mapRef.current = new google.maps.Map(host.current, {
        center: { lat: 39.1, lng: 35.2 },
        zoom: 6,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
      });
      paint(google);
    }).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const google = window.google as LiveGoogle | undefined;
    if (!browserKey || !google?.maps?.SymbolPath || !mapRef.current) return;
    paint(google);
  }, [signature, selectedId]);

  function paint(google: LiveGoogle) {
    const map = mapRef.current;
    if (!map) return;
    const bounds = new google.maps.LatLngBounds();
    const seen = new Set<string>();
    rows.current.forEach((vehicle) => {
      const spot = point(vehicle.latitude, vehicle.longitude);
      if (!spot) return;
      seen.add(vehicle.id);
      const icon = {
        path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
        scale: vehicle.id === selectedId ? 7 : 5,
        rotation: Number(vehicle.course ?? 0),
        fillColor: VEHICLE_STATE_COLOR[colors.current.get(vehicle.id) ?? "bayat"],
        fillOpacity: 1,
        strokeColor: "#ffffff",
        strokeWeight: 1,
      };
      const stamp = `${spot.lat},${spot.lng},${icon.rotation},${icon.fillColor},${icon.scale}`;
      const marker = markers.current.get(vehicle.id);
      if (marker) {
        if (markerKey.current.get(vehicle.id) !== stamp) {
          marker.setPosition(spot);
          marker.setIcon(icon);
          markerKey.current.set(vehicle.id, stamp);
        }
      } else {
        const created = new google.maps.Marker({ map, position: spot, icon });
        created.addListener("click", () => pick.current(vehicle.id));
        created.addListener("mouseover", () => {
          const current = rows.current.find((item) => item.id === vehicle.id);
          if (!current || !info.current) return;
          info.current.setContent(hoverCard(current, colors.current.get(current.id) ?? "bayat"));
          info.current.open({ map, anchor: created, shouldFocus: false });
        });
        created.addListener("mouseout", () => info.current?.close());
        markers.current.set(vehicle.id, created);
        markerKey.current.set(vehicle.id, stamp);
      }
      bounds.extend(spot);
      if (vehicle.id === selectedId) map.panTo(spot);
    });
    markers.current.forEach((marker, id) => {
      if (!seen.has(id)) {
        marker.setMap(null);
        info.current?.close();
        markers.current.delete(id);
        markerKey.current.delete(id);
      }
    });
    if (!fitted.current && !bounds.isEmpty()) {
      map.fitBounds(bounds);
      fitted.current = true;
    }
  }

  if (browserKey) return <Box ref={host} sx={{ flex: 1, minHeight: 0, width: "100%" }} />;

  const marks = vehicles
    .map((vehicle) => ({ vehicle, spot: point(vehicle.latitude, vehicle.longitude) }))
    .filter((item): item is { vehicle: LiveVehicle; spot: LatLng } => item.spot !== null);

  return (
    <Stack sx={{ flex: 1, minHeight: 0 }}>
      <Typography variant="caption" color="text.secondary" sx={{ px: 2, pt: 2 }}>
        Google harita anahtarı yok. Konumlar Türkiye taslağında canlı durur.
      </Typography>
      <Box component="svg" viewBox="0 0 100 64" sx={{ width: "100%", flex: 1, minHeight: 0, bgcolor: "#f4f6f8" }}>
        {marks.map(({ vehicle, spot }) => {
          const place = project(spot);
          const chosen = vehicle.id === selectedId;
          return (
            <circle
              key={vehicle.id}
              onClick={() => onSelect(vehicle.id)}
              style={{ cursor: "pointer" }}
              cx={place.x}
              cy={place.y}
              r={chosen ? 2.2 : 1.5}
              fill={VEHICLE_STATE_COLOR[states.get(vehicle.id) ?? "bayat"]}
            >
              <title>{hoverText(vehicle, states.get(vehicle.id) ?? "bayat")}</title>
            </circle>
          );
        })}
      </Box>
    </Stack>
  );
}

function hoverText(vehicle: LiveVehicle, state: VehicleState): string {
  const speed = vehicle.speed_kmh ? `${Math.round(Number(vehicle.speed_kmh))} km/sa` : "-";
  return `${vehicle.plate} · ${VEHICLE_STATE_LABEL[state]} · ${vehicle.driver_name ?? "Şoför yok"} · ${speed} · ${signalLabel(vehicle.recorded_at)}`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
}

function hoverCard(vehicle: LiveVehicle, state: VehicleState): string {
  const speed = vehicle.speed_kmh ? `${Math.round(Number(vehicle.speed_kmh))} km/sa` : "-";
  const row = (name: string, value: string) =>
    `<div style="display:flex;justify-content:space-between;gap:16px"><span style="color:#637381">${name}</span><span>${escapeHtml(value)}</span></div>`;
  return `<div style="font:12px/1.5 system-ui,sans-serif;min-width:170px;color:#1c252e">
    <div style="display:flex;align-items:center;gap:6px;font-weight:600;font-size:13px;margin-bottom:2px">
      <span style="width:9px;height:9px;border-radius:50%;background:${VEHICLE_STATE_COLOR[state]}"></span>${escapeHtml(vehicle.plate)}
      <span style="font-weight:400;color:#637381">${VEHICLE_STATE_LABEL[state]}</span>
    </div>
    ${row("Şoför", vehicle.driver_name ?? "Yok")}
    ${row("Hız", speed)}
    ${row("Son sinyal", signalLabel(vehicle.recorded_at))}
  </div>`;
}

function point(lat: string | null, lng: string | null): LatLng | null {
  if (!lat || !lng) return null;
  const parsed = { lat: Number(lat), lng: Number(lng) };
  return Number.isFinite(parsed.lat) && Number.isFinite(parsed.lng) ? parsed : null;
}

function project(item: LatLng): { x: number; y: number } {
  return { x: ((item.lng - 26) / 19) * 100, y: ((42.2 - item.lat) / 6.4) * 64 };
}

function loadMaps(token: string): Promise<LiveGoogle> {
  const ready = window.google as LiveGoogle | undefined;
  if (ready?.maps) return Promise.resolve(ready);
  const existing = document.querySelector<HTMLScriptElement>("script[data-backhaul-maps]");
  const wait = (script: HTMLScriptElement) =>
    new Promise<LiveGoogle>((resolve, reject) => {
      script.addEventListener("load", () => {
        const google = window.google as LiveGoogle | undefined;
        if (google) resolve(google);
        else reject();
      });
      script.addEventListener("error", () => reject());
    });
  if (existing) return wait(existing);
  const script = document.createElement("script");
  script.dataset.backhaulMaps = "1";
  script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(token)}&language=tr&region=TR`;
  script.async = true;
  document.head.appendChild(script);
  return wait(script);
}

