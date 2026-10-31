import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import { XIcon } from "@phosphor-icons/react";
import Card from "@mui/material/Card";
import CardHeader from "@mui/material/CardHeader";
import ListItemButton from "@mui/material/ListItemButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { useLiveVehicles } from "../live-data";
import { FleetMap } from "./FleetMap";
import { TRAILER_LABEL, VEHICLE_STATE_COLOR, VEHICLE_STATE_LABEL, clock, signalLabel, type VehicleState } from "../labels";
import { useSession } from "../session";
import type { Driver, LiveVehicle, Load, Settings, Vehicle } from "../types";

export function Takip({ initialVehicle = "" }: { initialVehicle?: string }) {
  const { token } = useSession();
  const { settings, vehicles: fleet, drivers, reload } = useFleet();
  const [loads, setLoads] = useState<Load[]>([]);
  const staleMinutes = settings?.gps_stale_minutes ?? 15;
  const { vehicles, link, tick, states, counts } = useLiveVehicles(staleMinutes);
  const [selected, setSelected] = useState<string | null>(initialVehicle || null);

  useEffect(() => {
    if (initialVehicle) setSelected(initialVehicle);
  }, [initialVehicle]);

  useEffect(() => {
    if (!selected) return;
    reload().catch(() => undefined);
    api<Load[]>("/loads", token)
      .then(setLoads)
      .catch(() => setLoads([]));
  }, [selected, token, reload]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: { xs: "column", lg: "row" },
        gap: 2,
        height: { xs: "auto", lg: "calc(100dvh - 160px)" },
        minHeight: { lg: 480 },
      }}
    >
      <Card
        sx={{
          order: { xs: 2, lg: 1 },
          width: { lg: 340 },
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          height: { xs: "min(420px, 50dvh)", lg: "auto" },
          minHeight: 0,
        }}
      >
        <CardHeader title="Araçlar" subheader={`${link} · ${vehicles.length} araç`} />
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1, px: 2, pb: 1.5 }}>
          {(Object.keys(VEHICLE_STATE_LABEL) as VehicleState[]).map((state) => (
            <Stack key={state} direction="row" spacing={0.5} sx={{ alignItems: "center", opacity: counts.get(state) ? 1 : 0.45 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: VEHICLE_STATE_COLOR[state] }} />
              <Typography variant="caption">
                {VEHICLE_STATE_LABEL[state]} {counts.get(state) ?? 0}
              </Typography>
            </Stack>
          ))}
        </Stack>
        <Stack sx={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
          {vehicles.length === 0 ? (
            <Typography color="text.secondary" sx={{ px: 2, pb: 2 }}>
              Kayıtlı araç yok
            </Typography>
          ) : null}
          {vehicles.map((vehicle) => (
            <ListItemButton key={vehicle.id} selected={vehicle.id === selected} onClick={() => setSelected(vehicle.id)} sx={{ flexShrink: 0 }}>
              <Box sx={{ width: 10, height: 10, mr: 1.5, flexShrink: 0, borderRadius: "50%", bgcolor: VEHICLE_STATE_COLOR[states.get(vehicle.id) ?? "bayat"] }} />
              <Stack sx={{ minWidth: 0 }}>
                <Typography noWrap>
                  {vehicle.plate} · {VEHICLE_STATE_LABEL[states.get(vehicle.id) ?? "bayat"]}
                </Typography>
                <Typography variant="body2" color="text.secondary" noWrap>
                  {vehicle.driver_name ?? "Şoför yok"} · {vehicle.speed_kmh ?? "0.0"} km/s · {signalLabel(vehicle.recorded_at)}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {vehicle.latitude && vehicle.longitude ? `${vehicle.latitude}, ${vehicle.longitude}` : "Konum yok"}
                </Typography>
              </Stack>
            </ListItemButton>
          ))}
        </Stack>
      </Card>
      <Card
        sx={{
          order: { xs: 1, lg: 2 },
          flex: { lg: 1 },
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          height: { xs: "50dvh", lg: "auto" },
          minHeight: { xs: 320, lg: 0 },
          position: "relative",
        }}
      >
        <FleetMap vehicles={vehicles} selectedId={selected} states={states} tick={tick} onSelect={setSelected} />
        {(() => {
          const live = vehicles.find((item) => item.id === selected);
          if (!live) return null;
          return (
            <VehiclePopup
              live={live}
              state={states.get(live.id) ?? "bayat"}
              vehicle={fleet.find((item) => item.id === live.id) ?? null}
              driver={drivers.find((item) => item.id === fleet.find((row) => row.id === live.id)?.driver_id) ?? null}
              load={loads.find((item) => item.vehicle_id === live.id && (item.status === "atandi" || item.status === "yolda")) ?? null}
              settings={settings}
              onClose={() => setSelected(null)}
            />
          );
        })()}
      </Card>
    </Box>
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
    <Stack direction="row" sx={{ justifyContent: "space-between", gap: 2 }}>
      <Typography variant="body2" color="text.secondary" sx={{ flexShrink: 0 }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ textAlign: "right", minWidth: 0, overflowWrap: "anywhere" }}>
        {value}
      </Typography>
    </Stack>
  );
}

function VehiclePopup({
  live,
  state,
  vehicle,
  driver,
  load,
  settings,
  onClose,
}: {
  live: LiveVehicle;
  state: VehicleState;
  vehicle: Vehicle | null;
  driver: Driver | null;
  load: Load | null;
  settings: Settings | null;
  onClose: () => void;
}) {
  const hasPoint = live.latitude && live.longitude;
  const source = vehicle?.tacho_source;
  return (
    <Card
      elevation={8}
      sx={{
        position: "absolute",
        zIndex: 2,
        top: { xs: "auto", lg: 12 },
        bottom: { xs: 8, lg: "auto" },
        left: { xs: 8, lg: "auto" },
        right: { xs: 8, lg: 12 },
        width: { lg: 320 },
        maxHeight: { xs: "70%", lg: "calc(100% - 24px)" },
        overflowY: "auto",
        p: 2,
      }}
    >
      <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Typography variant="h6">{live.plate}</Typography>
          <Chip size="small" label={VEHICLE_STATE_LABEL[state]} sx={{ bgcolor: VEHICLE_STATE_COLOR[state], color: "#fff" }} />
        </Stack>
        <IconButton size="small" onClick={onClose} aria-label="Kapat">
          <XIcon />
        </IconButton>
      </Stack>
      <Stack spacing={0.75}>
        <Row label="Şoför" value={live.driver_name ?? "Şoför yok"} />
        {driver ? <Row label="Telefon" value={driver.phone || "Yok"} /> : null}
        <Row label="Hız" value={`${live.speed_kmh ?? "0.0"} km/s`} />
        <Row label="Son sinyal" value={live.recorded_at ? `${clock(live.recorded_at)} (${signalLabel(live.recorded_at)})` : "Yok"} />
        <Row label="Konum" value={hasPoint ? `${live.latitude}, ${live.longitude}` : "Konum yok"} />
        {hasPoint ? (
          <Link href={`https://www.google.com/maps?q=${live.latitude},${live.longitude}`} target="_blank" rel="noreferrer" variant="body2">
            Google Haritalar'da aç
          </Link>
        ) : null}
      </Stack>
      <Divider sx={{ my: 1.5 }} />
      <Stack spacing={0.75}>
        <Row label="Kasa" value={vehicle ? TRAILER_LABEL[vehicle.trailer_type] ?? vehicle.trailer_type : "—"} />
        <Row label="Kapasite" value={vehicle ? `${vehicle.capacity_tons} ton` : "—"} />
        <Row label="Cihaz no" value={vehicle?.device_id ?? "—"} />
      </Stack>
      <Divider sx={{ my: 1.5 }} />
      <Typography variant="subtitle2" sx={{ mb: 0.75 }}>
        Takograf {source ? `· ${source === "olculmus" ? "ölçülmüş" : "tahmini"}` : ""}
      </Typography>
      {source ? (
        <Stack spacing={0.75}>
          <Row label="Kesintisiz sürüş kalan" value={remain(settings?.tacho_continuous_min, vehicle?.tacho_continuous_min ?? null)} />
          <Row label="Günlük kalan" value={remain(settings?.tacho_daily_min, vehicle?.tacho_daily_min ?? null)} />
          <Row label="Haftalık kalan" value={remain(settings?.tacho_weekly_min, vehicle?.tacho_weekly_min ?? null)} />
        </Stack>
      ) : (
        <Typography variant="body2" color="text.secondary">
          Sayaç yok
        </Typography>
      )}
      <Divider sx={{ my: 1.5 }} />
      <Typography variant="subtitle2" sx={{ mb: 0.75 }}>
        Açık sefer
      </Typography>
      {load ? (
        <Stack spacing={0.75}>
          <Row label="Referans" value={load.reference} />
          <Row label="Güzergâh" value={`${load.pickup_il} → ${load.drop_il}`} />
          <Row label="Teslim" value={`${clock(load.deliver_start)} – ${clock(load.deliver_end)}`} />
        </Stack>
      ) : (
        <Typography variant="body2" color="text.secondary">
          Yok
        </Typography>
      )}
    </Card>
  );
}
