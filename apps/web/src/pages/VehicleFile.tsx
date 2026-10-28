import { FormEvent, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { STATUS_LABEL, TRAILER_LABEL, availability, canOperate, canWriteMaster, driverName, signalLabel } from "../labels";
import { useSession } from "../session";
import type { Driver, Settings, Vehicle } from "../types";

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
  const [status, setStatus] = useState(vehicle.status);
  const [driverId, setDriverId] = useState(vehicle.driver_id ?? "");
  const [latitude, setLatitude] = useState(vehicle.latitude ?? "");
  const [longitude, setLongitude] = useState(vehicle.longitude ?? "");
  const [speed, setSpeed] = useState(vehicle.speed_kmh ?? "0");

  useEffect(() => {
    setStatus(vehicle.status);
    setDriverId(vehicle.driver_id ?? "");
    setLatitude(vehicle.latitude ?? "");
    setLongitude(vehicle.longitude ?? "");
    setSpeed(vehicle.speed_kmh ?? "0");
  }, [vehicle]);

  async function saveMaster(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      await api(`/vehicles/${vehicle.id}`, token, {
        method: "PATCH",
        body: JSON.stringify({ status, driver_id: driverId || null }),
      });
      await onChanged();
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
    ["Şoför", driverName(drivers, vehicle.driver_id)],
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
    <Drawer anchor="right" open onClose={onClose} slotProps={{ paper: { sx: { width: { xs: "100%", sm: 420 }, p: 3 } } }}>
      <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="h5">{vehicle.plate}</Typography>
        <Button onClick={onClose}>Kapat</Button>
      </Stack>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        {TRAILER_LABEL[vehicle.trailer_type] ?? vehicle.trailer_type} · {vehicle.capacity_tons} ton · {availability(vehicle, settings)}
      </Typography>
      <Stack spacing={1.5} sx={{ mb: 3 }}>
        {facts.map(([label, value]) => (
          <Box key={label}>
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
            <Typography>{value}</Typography>
          </Box>
        ))}
      </Stack>
      {canWriteMaster(user.role) ? (
        <Stack component="form" spacing={2} onSubmit={saveMaster} sx={{ mb: 3 }}>
          <Typography variant="h6">Kayıt</Typography>
          <TextField select label="Durum" value={status} onChange={(event) => setStatus(event.target.value)}>
            {Object.entries(STATUS_LABEL).map(([value, label]) => (
              <MenuItem key={value} value={value}>
                {label}
              </MenuItem>
            ))}
          </TextField>
          <TextField select label="Bağlı şoför" value={driverId} onChange={(event) => setDriverId(event.target.value)}>
            <MenuItem value="">Şoför yok</MenuItem>
            {drivers.map((driver) => (
              <MenuItem key={driver.id} value={driver.id}>
                {driver.name}
              </MenuItem>
            ))}
          </TextField>
          <Button type="submit" variant="contained">
            Kaydet
          </Button>
        </Stack>
      ) : null}
      {canOperate(user.role) ? (
        <Stack component="form" spacing={2} onSubmit={savePosition}>
          <Typography variant="h6">Elle konum</Typography>
          <TextField label="Enlem" value={latitude} onChange={(event) => setLatitude(event.target.value)} required />
          <TextField label="Boylam" value={longitude} onChange={(event) => setLongitude(event.target.value)} required />
          <TextField label="Hız (km/s)" value={speed} onChange={(event) => setSpeed(event.target.value)} />
          <Button type="submit" variant="contained">
            Konumu yaz
          </Button>
        </Stack>
      ) : null}
    </Drawer>
  );
}
