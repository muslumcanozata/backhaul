import { useEffect, useState } from "react";
import { API } from "./api";
import { VEHICLE_STATE_LABEL, liveState, type VehicleState } from "./labels";
import { useSession } from "./session";
import type { LiveVehicle } from "./types";

export function useLiveVehicles(staleMinutes: number) {
  const { token } = useSession();
  const [vehicles, setVehicles] = useState<LiveVehicle[]>([]);
  const [link, setLink] = useState("Bağlantı kuruluyor");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((value) => value + 1), 60_000);
    return () => window.clearInterval(timer);
  }, []);

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

  const states = new Map(vehicles.map((vehicle) => [vehicle.id, liveState(vehicle, staleMinutes)]));
  const counts = new Map<VehicleState, number>();
  states.forEach((state) => counts.set(state, (counts.get(state) ?? 0) + 1));

  return { vehicles, link, tick, states, counts, labels: VEHICLE_STATE_LABEL };
}
