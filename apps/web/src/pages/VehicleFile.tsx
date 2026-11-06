import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Divider from "@mui/material/Divider";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
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
    <Card>
      <CardHeader
        title={vehicle.plate}
        subheader={`${TRAILER_LABEL[vehicle.trailer_type] ?? vehicle.trailer_type} · ${vehicle.capacity_tons} ton · ${availability(vehicle, settings)}`}
        action={
          <Button onClick={onClose} size="small">
            Listeye dön
          </Button>
        }
      />
      <CardContent>
      <Tabs value={tab} onChange={(_, next) => setTab(next)} variant="scrollable" allowScrollButtonsMobile sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}>
        <Tab label="Özet" />
        <Tab label="Bakım" />
        <Tab label="Lastik" />
        <Tab label="Yakıt" />
        <Tab label="Kullanım" />
      </Tabs>

      {tab === 0 ? (
        <Stack spacing={2}>
          <Stack spacing={1.5}>
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
            <Stack component="form" spacing={2} onSubmit={saveMaster}>
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
        </Stack>
      ) : null}

      {tab === 1 ? (
        <HistoryTab
          title="Bakım geçmişi"
          canWrite={canOperate(user.role)}
          rows={(dossier?.maintenances ?? []).map((row) => `${stamp(row.happened_at)} · ${row.kind} · ${row.odometer_km ?? "—"} km · ${row.workshop ?? ""} ${row.cost_try ? `· ${row.cost_try} TL` : ""}`)}
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
          rows={(dossier?.tire_events ?? []).map((row) => `${stamp(row.happened_at)} · ${row.position} · ${row.event} · ${row.brand_size ?? ""} · ${row.odometer_km ?? "—"} km`)}
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
        <Stack spacing={2}>
          <HistoryTab
            title="Yakıt alma"
            canWrite={canOperate(user.role)}
            rows={(dossier?.fuel_fills ?? []).map((row) => `${stamp(row.happened_at)} · ${row.liters ?? "—"} L · ${row.amount_try ?? "—"} TL · ${row.station ?? row.source} · ${row.odometer_km ?? "—"} km`)}
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
            <Stack spacing={1}>
              <Typography variant="subtitle2">Seyir depo örnekleri</Typography>
              {(dossier?.fuel_samples ?? []).slice(0, 12).map((row) => (
                <Typography key={row.id} variant="body2" color="text.secondary">
                  {stamp(row.recorded_at)} · {row.level_pct != null ? `%${row.level_pct}` : `${row.level_liters} L`} · {row.odometer_km ?? "—"} km
                </Typography>
              ))}
            </Stack>
          ) : null}
        </Stack>
      ) : null}

      {tab === 4 ? (
        <Stack spacing={2}>
          <Typography variant="h6">Şoför kullanım</Typography>
          {(dossier?.driver_stints ?? []).length === 0 ? <Typography color="text.secondary">Stint yok</Typography> : null}
          {(dossier?.driver_stints ?? []).map((row) => (
            <Box key={row.id}>
              <Typography
                sx={{ cursor: "pointer", color: "primary.main" }}
                onClick={() => {
                  window.location.hash = `takograf/${row.driver_id}`;
                }}
              >
                {row.driver_name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {stamp(row.started_at)} → {row.ended_at ? stamp(row.ended_at) : "açık"} · {row.source}
              </Typography>
            </Box>
          ))}
          <Divider />
          <Typography variant="h6">Yükler</Typography>
          {(dossier?.usage_loads ?? []).length === 0 ? <Typography color="text.secondary">Yük yok</Typography> : null}
          {(dossier?.usage_loads ?? []).map((row) => (
            <Typography key={row.id} variant="body2">
              {row.reference} · {row.direction} · {row.status} · {stamp(row.ready_at)}
            </Typography>
          ))}
        </Stack>
      ) : null}
      </CardContent>
    </Card>
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
    <Stack spacing={2}>
      <Typography variant="h6">{title}</Typography>
      {rows.length === 0 ? <Typography color="text.secondary">Kayıt yok</Typography> : null}
      {rows.map((row) => (
        <Typography key={row} variant="body2">
          {row}
        </Typography>
      ))}
      {canWrite ? form : null}
    </Stack>
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
    <Stack component="form" spacing={1.5} onSubmit={submit}>
      <Typography variant="subtitle2">Yeni bakım</Typography>
      <TextField select label="Tür" value={kind} onChange={(event) => setKind(event.target.value)}>
        {MAINT_KIND.map(([value, label]) => (
          <MenuItem key={value} value={value}>
            {label}
          </MenuItem>
        ))}
      </TextField>
      <TextField label="Tarih" type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} required />
      <TextField label="Km" value={odometer} onChange={(event) => setOdometer(event.target.value)} />
      <TextField label="Tutar (TL)" value={cost} onChange={(event) => setCost(event.target.value)} />
      <TextField label="Servis" value={workshop} onChange={(event) => setWorkshop(event.target.value)} />
      <TextField label="Not" value={note} onChange={(event) => setNote(event.target.value)} />
      <Button type="submit" variant="contained">
        Ekle
      </Button>
    </Stack>
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
    <Stack component="form" spacing={1.5} onSubmit={submit}>
      <Typography variant="subtitle2">Yeni lastik olayı</Typography>
      <TextField select label="Konum" value={position} onChange={(event) => setPosition(event.target.value)}>
        {TIRE_POS.map(([value, label]) => (
          <MenuItem key={value} value={value}>
            {label}
          </MenuItem>
        ))}
      </TextField>
      <TextField select label="Olay" value={eventKind} onChange={(event) => setEventKind(event.target.value)}>
        {TIRE_EVENT.map(([value, label]) => (
          <MenuItem key={value} value={value}>
            {label}
          </MenuItem>
        ))}
      </TextField>
      <TextField label="Marka / ebat" value={brand} onChange={(event) => setBrand(event.target.value)} />
      <TextField label="Tarih" type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} required />
      <TextField label="Km" value={odometer} onChange={(event) => setOdometer(event.target.value)} />
      <TextField label="Not" value={note} onChange={(event) => setNote(event.target.value)} />
      <Button type="submit" variant="contained">
        Ekle
      </Button>
    </Stack>
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
    <Stack component="form" spacing={1.5} onSubmit={submit}>
      <Typography variant="subtitle2">Yeni dolum</Typography>
      <TextField label="Tarih" type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} required />
      <TextField label="Litre" value={liters} onChange={(event) => setLiters(event.target.value)} />
      <TextField label="Tutar (TL)" value={amount} onChange={(event) => setAmount(event.target.value)} />
      <TextField label="Km" value={odometer} onChange={(event) => setOdometer(event.target.value)} />
      <TextField label="İstasyon" value={station} onChange={(event) => setStation(event.target.value)} />
      <TextField label="Not" value={note} onChange={(event) => setNote(event.target.value)} />
      <Button type="submit" variant="contained">
        Ekle
      </Button>
    </Stack>
  );
}

function localInputNow() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}
