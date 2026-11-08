import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { useSession } from "./session";
import type { Driver, Settings, Vehicle } from "./types";

export function useFleet() {
  const { token, notice } = useSession();
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextVehicles, nextDrivers, nextSettings] = await Promise.all([
        api<Vehicle[]>("/vehicles", token),
        api<Driver[]>("/drivers", token),
        api<Settings>("/settings", token),
      ]);
      setVehicles(nextVehicles);
      setDrivers(nextDrivers);
      setSettings(nextSettings);
      notice("");
    } finally {
      setLoading(false);
    }
  }, [token, notice]);

  useEffect(() => {
    reload().catch((err: Error) => {
      setLoading(false);
      notice(err.message);
    });
  }, [reload, notice]);

  return { vehicles, drivers, settings, loading, reload };
}
