import { createClient, type RealtimeChannel, type SupabaseClient } from "@supabase/supabase-js";
import { useEffect, useMemo, useState } from "react";
import { API, api } from "./api";
import { VEHICLE_STATE_LABEL, liveState, type VehicleState } from "./labels";
import { useSession } from "./session";
import type { LiveVehicle } from "./types";

type LiveConfig = {
  supabase: boolean;
  supabase_url: string | null;
  channel: string | null;
  anon_key: string | null;
};

type LiveMessage = { type: string; vehicles?: LiveVehicle[]; vehicle?: LiveVehicle };

function liveSocketUrl(token: string): string {
  const query = `/live?token=${encodeURIComponent(token)}`;
  if (API) return `${API.replace(/^http/, "ws")}${query}`;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${query}`;
}

function applyMessage(
  message: LiveMessage,
  setVehicles: (updater: (current: LiveVehicle[]) => LiveVehicle[]) => void,
) {
  if (message.type === "snapshot" && message.vehicles) {
    setVehicles(() => message.vehicles ?? []);
  }
  if (message.type === "position" && message.vehicle) {
    const next = message.vehicle;
    setVehicles((current) => {
      const index = current.findIndex((item) => item.id === next.id);
      if (index < 0) return [...current, next];
      return current.map((item) => (item.id === next.id ? next : item));
    });
  }
}

export function useLiveVehicles(staleMinutes: number) {
  const { token } = useSession();
  const [vehicles, setVehicles] = useState<LiveVehicle[]>([]);
  const [link, setLink] = useState("Bağlantı kuruluyor");
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((value) => value + 1), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | null = null;
    let retry = 0;
    let channel: RealtimeChannel | null = null;
    let client: SupabaseClient | null = null;
    setLoading(true);
    setLink("Bağlantı kuruluyor");

    async function start() {
      // Snapshot'ı config ile paralel çek; harita ilk boyamada boş beklemesin.
      const snapPromise = api<LiveMessage>("/live/snapshot", token)
        .then((snap) => {
          if (stopped) return;
          applyMessage(snap, setVehicles);
          setLoading(false);
        })
        .catch(() => undefined);

      try {
        const config = await api<LiveConfig>("/live/config", token);
        if (stopped) return;
        await snapPromise;
        if (stopped) return;
        if (config.supabase && config.supabase_url && config.anon_key && config.channel) {
          client = createClient(config.supabase_url, config.anon_key, {
            global: { headers: { Authorization: `Bearer ${token}` } },
            auth: { persistSession: false, autoRefreshToken: false },
          });
          await client.realtime.setAuth(token);
          channel = client
            .channel(config.channel)
            .on("broadcast", { event: "position" }, ({ payload }) => {
              applyMessage(payload as LiveMessage, setVehicles);
            })
            .subscribe((status) => {
              if (status === "SUBSCRIBED") setLink("Canlı");
              if (status === "CHANNEL_ERROR" || status === "TIMED_OUT") setLink("Bağlantı yenileniyor");
            });
          return;
        }
      } catch {
        // Yerel WebSocket yedek yolu
      }
      if (stopped) return;
      await snapPromise;
      if (stopped) return;
      connectSocket();
    }

    function connectSocket() {
      const url = liveSocketUrl(token);
      socket = new WebSocket(url);
      socket.onopen = () => {
        setLink("Canlı");
      };
      socket.onmessage = (event) => {
        applyMessage(JSON.parse(event.data) as LiveMessage, setVehicles);
        setLoading(false);
      };
      socket.onclose = () => {
        if (stopped) return;
        setLink("Bağlantı yenileniyor");
        retry = window.setTimeout(connectSocket, 2000);
      };
    }

    void start().catch(() => {
      if (!stopped) setLoading(false);
    });
    return () => {
      stopped = true;
      window.clearTimeout(retry);
      socket?.close();
      if (channel && client) void client.removeChannel(channel);
    };
  }, [token]);

  const states = useMemo(() => {
    const next = new Map(vehicles.map((vehicle) => [vehicle.id, liveState(vehicle, staleMinutes)]));
    return next;
  }, [vehicles, staleMinutes, tick]);

  const counts = useMemo(() => {
    const next = new Map<VehicleState, number>();
    states.forEach((state) => next.set(state, (next.get(state) ?? 0) + 1));
    return next;
  }, [states]);

  return { vehicles, link, loading, tick, states, counts, labels: VEHICLE_STATE_LABEL };
}
