import { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import type { Load, Vehicle } from "../types";

type LatLng = { lat: number; lng: number };

type GoogleMap = { fitBounds: (bounds: unknown) => void };

type BackhaulGoogle = {
  maps: {
    Map: new (element: HTMLElement, options: Record<string, unknown>) => GoogleMap;
    Marker: new (options: Record<string, unknown>) => unknown;
    LatLngBounds: new () => { extend: (point: LatLng) => void; isEmpty: () => boolean };
  };
};

declare global {
  interface Window {
    google?: BackhaulGoogle;
  }
}

const key = import.meta.env.VITE_GOOGLE_MAPS_BROWSER_KEY as string | undefined;

function point(lat: string | null, lng: string | null): LatLng | null {
  if (!lat || !lng) return null;
  const parsed = { lat: Number(lat), lng: Number(lng) };
  return Number.isFinite(parsed.lat) && Number.isFinite(parsed.lng) ? parsed : null;
}

function project(item: LatLng): { x: number; y: number } {
  return {
    x: ((item.lng - 26) / 19) * 100,
    y: ((42.2 - item.lat) / 6.4) * 64,
  };
}

export function DeskMap({ vehicles, load }: { vehicles: Vehicle[]; load: Load | null }) {
  const host = useRef<HTMLDivElement>(null);
  const marks = vehicles.map((vehicle) => point(vehicle.latitude, vehicle.longitude)).filter((item): item is LatLng => item !== null);
  const pickup = load ? point(load.pickup_lat, load.pickup_lng) : null;
  const drop = load ? point(load.drop_lat, load.drop_lng) : null;

  const markKey = marks.map((item) => `${item.lat.toFixed(5)},${item.lng.toFixed(5)}`).join(";");
  const focusKey = `${pickup?.lat ?? ""},${pickup?.lng ?? ""};${drop?.lat ?? ""},${drop?.lng ?? ""}`;

  useEffect(() => {
    if (!key || !host.current) return;
    let cancelled = false;
    loadMaps(key).then((google) => {
      if (cancelled || !host.current) return;
      const map = new google.maps.Map(host.current, {
        center: { lat: 39.1, lng: 35.2 },
        zoom: 6,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
      });
      const bounds = new google.maps.LatLngBounds();
      marks.forEach((item) => {
        new google.maps.Marker({ map, position: item, title: "Araç" });
        bounds.extend(item);
      });
      if (pickup) {
        new google.maps.Marker({ map, position: pickup, title: "Yükleme" });
        bounds.extend(pickup);
      }
      if (drop) {
        new google.maps.Marker({ map, position: drop, title: "Boşaltma" });
        bounds.extend(drop);
      }
      if (!bounds.isEmpty()) map.fitBounds(bounds);
    }).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [markKey, focusKey]);

  if (key) return <Box ref={host} sx={{ height: 320, borderRadius: 2, overflow: "hidden" }} />;

  return (
    <Box component="svg" viewBox="0 0 100 64" sx={{ width: "100%", height: 280, bgcolor: "#f4f6f8", borderRadius: 2 }}>
      {marks.map((item, index) => {
        const spot = project(item);
        return <circle key={index} cx={spot.x} cy={spot.y} r="1.4" fill="#121621" />;
      })}
      {pickup ? <circle cx={project(pickup).x} cy={project(pickup).y} r="1.6" fill="#15b79e" /> : null}
      {drop ? <circle cx={project(drop).x} cy={project(drop).y} r="1.6" fill="#635bff" /> : null}
    </Box>
  );
}

function loadMaps(token: string): Promise<BackhaulGoogle> {
  if (window.google?.maps) return Promise.resolve(window.google);
  const existing = document.querySelector<HTMLScriptElement>("script[data-backhaul-maps]");
  const wait = (script: HTMLScriptElement) =>
    new Promise<BackhaulGoogle>((resolve, reject) => {
      script.addEventListener("load", () => (window.google ? resolve(window.google) : reject()));
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
