import { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardHeader from "@mui/material/CardHeader";
import ListItemButton from "@mui/material/ListItemButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { API } from "../api";
import { signalLabel } from "../labels";
import { useSession } from "../session";
import type { LiveVehicle } from "../types";

type LatLng = { lat: number; lng: number };

type GoogleMarker = {
  setPosition: (position: LatLng) => void;
  setIcon: (icon: unknown) => void;
  setMap: (map: null) => void;
};

type GoogleMap = {
  panTo: (position: LatLng) => void;
  fitBounds: (bounds: unknown) => void;
};

type LiveGoogle = {
  maps: {
    Map: new (element: HTMLElement, options: Record<string, unknown>) => GoogleMap;
    Marker: new (options: Record<string, unknown>) => GoogleMarker;
    LatLngBounds: new () => { extend: (point: LatLng) => void; isEmpty: () => boolean };
    SymbolPath: { FORWARD_CLOSED_ARROW: number };
  };
};

const browserKey = import.meta.env.VITE_GOOGLE_MAPS_BROWSER_KEY as string | undefined;

export function Takip() {
  const { token } = useSession();
  const [vehicles, setVehicles] = useState<LiveVehicle[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [link, setLink] = useState("Bağlantı kuruluyor");

  useEffect(() => {
    let socket: WebSocket | null = null;
    let stopped = false;
    let retry = 0;

    function connect() {
      const url = `${API.replace(/^http/, "ws")}/live?token=${encodeURIComponent(token)}`;
      socket = new WebSocket(url);
      socket.onopen = () => setLink("Canlı");
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as { type: string; vehicles?: LiveVehicle[]; vehicle?: LiveVehicle };
        if (message.type === "snapshot" && message.vehicles) setVehicles(message.vehicles);
        if (message.type === "position" && message.vehicle) {
          const next = message.vehicle;
          setVehicles((current) => {
            const index = current.findIndex((item) => item.id === next.id);
            if (index < 0) return [...current, next];
            return current.map((item) => (item.id === next.id ? next : item));
          });
        }
      };
      socket.onclose = () => {
        if (stopped) return;
        setLink("Bağlantı yenileniyor");
        retry = window.setTimeout(connect, 2000);
      };
    }

    connect();
    return () => {
      stopped = true;
      window.clearTimeout(retry);
      socket?.close();
    };
  }, [token]);

  return (
    <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ alignItems: "stretch", minHeight: { lg: "calc(100vh - 148px)" } }}>
      <Card sx={{ width: { lg: 320 }, flexShrink: 0, overflow: "auto" }}>
        <CardHeader title="Araçlar" subheader={link} />
        <Stack>
          {vehicles.length === 0 ? (
            <Typography color="text.secondary" sx={{ px: 2, pb: 2 }}>
              Kayıtlı araç yok
            </Typography>
          ) : null}
          {vehicles.map((vehicle) => (
            <ListItemButton key={vehicle.id} selected={vehicle.id === selected} onClick={() => setSelected(vehicle.id)}>
              <Stack>
                <Typography>
                  {vehicle.plate} · {vehicle.duty === "yuklu" ? "Yüklü" : "Boş"}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {vehicle.driver_name ?? "Şoför yok"} · {vehicle.speed_kmh ?? "0.0"} km/s · {signalLabel(vehicle.recorded_at)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {vehicle.latitude && vehicle.longitude ? `${vehicle.latitude}, ${vehicle.longitude}` : "Konum yok"}
                </Typography>
              </Stack>
            </ListItemButton>
          ))}
        </Stack>
      </Card>
      <Card sx={{ flex: 1, minHeight: 520, overflow: "hidden" }}>
        <FleetMap vehicles={vehicles} selectedId={selected} />
      </Card>
    </Stack>
  );
}

function FleetMap({ vehicles, selectedId }: { vehicles: LiveVehicle[]; selectedId: string | null }) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<GoogleMap | null>(null);
  const markers = useRef(new Map<string, GoogleMarker>());
  const fitted = useRef(false);
  const rows = useRef(vehicles);
  rows.current = vehicles;
  const signature = vehicles.map((vehicle) => `${vehicle.id}:${vehicle.latitude}:${vehicle.longitude}:${vehicle.course}:${vehicle.duty}`).join("|");

  useEffect(() => {
    if (!browserKey || !host.current || mapRef.current) return;
    let cancelled = false;
    loadMaps(browserKey).then((google) => {
      if (cancelled || !host.current || mapRef.current) return;
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
        scale: 5,
        rotation: Number(vehicle.course ?? 0),
        fillColor: vehicle.duty === "yuklu" ? "#1677ff" : "#121621",
        fillOpacity: 1,
        strokeColor: "#ffffff",
        strokeWeight: 1,
      };
      const marker = markers.current.get(vehicle.id);
      if (marker) {
        marker.setPosition(spot);
        marker.setIcon(icon);
      } else {
        markers.current.set(vehicle.id, new google.maps.Marker({ map, position: spot, title: vehicle.plate, icon }));
      }
      bounds.extend(spot);
      if (vehicle.id === selectedId) map.panTo(spot);
    });
    markers.current.forEach((marker, id) => {
      if (!seen.has(id)) {
        marker.setMap(null);
        markers.current.delete(id);
      }
    });
    if (!fitted.current && !bounds.isEmpty()) {
      map.fitBounds(bounds);
      fitted.current = true;
    }
  }

  if (browserKey) return <Box ref={host} sx={{ height: "100%", minHeight: 520 }} />;

  const marks = vehicles
    .map((vehicle) => ({ vehicle, spot: point(vehicle.latitude, vehicle.longitude) }))
    .filter((item): item is { vehicle: LiveVehicle; spot: LatLng } => item.spot !== null);

  return (
    <Stack sx={{ height: "100%", minHeight: 520 }}>
      <Typography variant="caption" color="text.secondary" sx={{ px: 2, pt: 2 }}>
        Google harita anahtarı yok. Konumlar Türkiye taslağında canlı durur.
      </Typography>
      <Box component="svg" viewBox="0 0 100 64" sx={{ width: "100%", flex: 1, bgcolor: "#f4f6f8" }}>
        {marks.map(({ vehicle, spot }) => {
          const place = project(spot);
          const chosen = vehicle.id === selectedId;
          return (
            <circle
              key={vehicle.id}
              cx={place.x}
              cy={place.y}
              r={chosen ? 2.2 : 1.5}
              fill={vehicle.duty === "yuklu" ? "#1677ff" : "#121621"}
            />
          );
        })}
      </Box>
    </Stack>
  );
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
