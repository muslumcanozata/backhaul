import { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { LOAD_STATUS_LABEL, VEHICLE_STATE_COLOR, VEHICLE_STATE_LABEL, availability, canOperate, clock, type VehicleState } from "../labels";
import { useSession } from "../session";
import type { AlertItem, Load } from "../types";
import { useLiveVehicles } from "../live-data";
import { FleetMap } from "./FleetMap";

const PIE = ["#1877F2", "#22C55E", "#FFAB00", "#FF5630", "#8E33FF", "#00B8D9"];

export function Masa() {
  const { token, user, notice } = useSession();
  const { vehicles, settings, reload } = useFleet();
  const live = useLiveVehicles(settings?.gps_stale_minutes ?? 15);
  const [loads, setLoads] = useState<Load[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [pullNote, setPullNote] = useState("");
  const operate = canOperate(user.role);

  useEffect(() => {
    Promise.all([api<Load[]>("/loads", token), api<AlertItem[]>("/alerts", token)])
      .then(([nextLoads, nextAlerts]) => {
        setLoads(nextLoads);
        setAlerts(nextAlerts);
      })
      .catch((err: Error) => notice(err.message));
  }, [token]);

  const outbound = loads.filter((item) => item.direction === "gidis" && ["planlanabilir", "atandi", "yolda"].includes(item.status));
  const pool = loads.filter((item) => item.direction === "donus" && ["havuz", "onerildi", "atandi"].includes(item.status));
  const assigned = loads.filter((item) => item.status === "atandi" || item.status === "yolda");
  const openAlerts = alerts.filter((item) => !item.seen_at);

  const counts = [
    ["Boş araç", vehicles.filter((item) => availability(item, settings) === "Boş").length],
    ["Gidiş Planlama", outbound.length],
    ["Dönüş Planlama", pool.length],
    ["Açık uyarı", openAlerts.length],
  ] as const;

  const statusChart = useMemo(() => {
    const bag = new Map<string, number>();
    for (const item of loads.filter((row) => row.status !== "iptal")) {
      bag.set(item.status, (bag.get(item.status) ?? 0) + 1);
    }
    return [...bag.entries()].map(([name, value]) => ({ name: LOAD_STATUS_LABEL[name] ?? name, value }));
  }, [loads]);

  const benefitChart = useMemo(
    () =>
      loads
        .filter((item) => item.direction === "donus" && item.benefit_try)
        .slice(0, 8)
        .map((item) => ({ name: item.reference, fayda: Number(item.benefit_try) })),
    [loads],
  );

  const fleetChart = useMemo(() => {
    const bag = new Map<string, number>();
    for (const item of vehicles) {
      const label = availability(item, settings);
      bag.set(label, (bag.get(label) ?? 0) + 1);
    }
    return [...bag.entries()].map(([name, value]) => ({ name, value }));
  }, [vehicles, settings]);

  const canPull =
    Boolean(settings?.arvento_enabled && settings.arvento_configured) || Boolean(settings?.seyir_enabled && settings.seyir_configured);

  async function pull() {
    notice("");
    setPullNote("");
    try {
      const pulled = await api<{ updated: number; unmatched: string[] }>("/integrations/telematics/pull", token, { method: "POST" });
      const missed = pulled.unmatched.filter(Boolean);
      setPullNote(missed.length ? `${pulled.updated} araç güncellendi. Eşleşmeyen plaka: ${missed.join(", ")}` : `${pulled.updated} araç güncellendi`);
      await reload();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Konum çekilemedi");
    }
  }

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} sx={{ alignItems: { sm: "center" }, justifyContent: "space-between", gap: 1 }}>
        <Box>
          <Typography variant="h4">Operasyon özeti</Typography>
          <Typography color="text.secondary" variant="body2">
            Filo durumu, kuyruk yükü ve dönüş faydası
          </Typography>
        </Box>
        {operate ? (
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" onClick={() => void pull()} disabled={!canPull}>
              Konumları çek
            </Button>
            <Button component="a" href="#gidis" variant="contained">
              Gidiş Planlama
            </Button>
            <Button component="a" href="#donus" variant="contained" color="inherit">
              Dönüş Planlama
            </Button>
          </Stack>
        ) : null}
      </Stack>
      {pullNote ? <Alert severity="info">{pullNote}</Alert> : null}
      {settings?.routes_needs_approval ? (
        <Alert
          severity="warning"
          action={
            operate ? (
              <Button
                color="inherit"
                size="small"
                onClick={() => {
                  notice("");
                  api("/settings/routes/approve", token, { method: "POST" })
                    .then(() => reload())
                    .catch((err: Error) => notice(err.message));
                }}
              >
                {settings.routes_limit} daha onayla
              </Button>
            ) : undefined
          }
        >
          Günlük Routes tavanı doldu ({settings.routes_today}/{settings.routes_allowed}). Yeni rota için onay gerekir.
        </Alert>
      ) : null}

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(4, 1fr)" } }}>
        {counts.map(([label, value]) => (
          <Card key={label}>
            <CardContent>
              <Typography color="text.secondary" variant="overline">
                {label}
              </Typography>
              <Typography variant="h3">{value}</Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "1.2fr 1fr 1fr" } }}>
        <Card>
          <CardHeader title="Filo müsaitliği" subheader="Anlık araç durumu. Çubuğa tıklayınca araç listesi açılır." />
          <CardContent sx={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={fleetChart}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} width={28} />
                <Tooltip />
                <Bar
                  dataKey="value"
                  name="Araç"
                  radius={[8, 8, 0, 0]}
                  fill="#1877F2"
                  cursor="pointer"
                  onClick={(data: { name?: string }) => {
                    if (data.name) window.location.hash = `araclar/${encodeURIComponent(data.name)}`;
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader title="Yük durumu" subheader="Açık ve tamamlanan seferler" />
          <CardContent sx={{ height: 280 }}>
            {statusChart.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={statusChart} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                    {statusChart.map((item, index) => (
                      <Cell key={item.name} fill={PIE[index % PIE.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Typography color="text.secondary">Grafik için yük yok.</Typography>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader title="Dönüş faydası" subheader="Hesaplanmış fırsatlar (TL)" />
          <CardContent sx={{ height: 280 }}>
            {benefitChart.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={benefitChart} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis type="category" dataKey="name" width={70} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="fayda" name="Fayda" radius={[0, 8, 8, 0]} fill="#22C55E" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Typography color="text.secondary">Henüz fayda hesabı yok. Dönüş Planlamandan Hesapla’yı çalıştırın.</Typography>
            )}
          </CardContent>
        </Card>
      </Box>

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "1.4fr 1fr" } }}>
        <Card>
          <CardHeader title="Canlı harita" subheader={`${live.link} · ${live.vehicles.length} araç. Araca tıklayınca detay açılır.`} />
          <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1.5, px: 2, pb: 1 }}>
            {(Object.keys(VEHICLE_STATE_LABEL) as VehicleState[]).map((state) => (
              <Stack key={state} direction="row" spacing={0.5} sx={{ alignItems: "center", opacity: live.counts.get(state) ? 1 : 0.45 }}>
                <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: VEHICLE_STATE_COLOR[state] }} />
                <Typography variant="caption">
                  {VEHICLE_STATE_LABEL[state]} {live.counts.get(state) ?? 0}
                </Typography>
              </Stack>
            ))}
          </Stack>
          <Box sx={{ display: "flex", flexDirection: "column", height: { xs: 340, lg: 420 } }}>
            <FleetMap
              vehicles={live.vehicles}
              selectedId={null}
              states={live.states}
              tick={live.tick}
              onSelect={(id) => {
                window.location.hash = `takip/${id}`;
              }}
            />
          </Box>
        </Card>
        <Stack spacing={2}>
          <Card>
            <CardHeader title="Yaklaşan gidişler" action={<Button component="a" href="#gidis">Tümü</Button>} />
            <CardContent>
              <Stack spacing={1.5}>
                {outbound.slice(0, 5).map((item) => (
                  <Box key={item.id}>
                    <Typography variant="subtitle2">{item.reference}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {item.pickup_il} → {item.drop_il} · {clock(item.ready_at)} · {LOAD_STATUS_LABEL[item.status] ?? item.status}
                    </Typography>
                  </Box>
                ))}
                {outbound.length === 0 ? <Typography color="text.secondary">Açık gidiş yok.</Typography> : null}
              </Stack>
            </CardContent>
          </Card>
          <Card>
            <CardHeader title="Dönüş fırsatları" action={<Button component="a" href="#donus">Tümü</Button>} />
            <CardContent>
              <Stack spacing={1.5}>
                {pool.slice(0, 5).map((item) => (
                  <Box key={item.id}>
                    <Typography variant="subtitle2">{item.reference}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {item.freight_try} TL · {item.benefit_try ? `${item.benefit_try} TL fayda · ` : ""}
                      {item.pickup_il}/{item.drop_il}
                    </Typography>
                  </Box>
                ))}
                {pool.length === 0 ? <Typography color="text.secondary">Havuz boş.</Typography> : null}
              </Stack>
            </CardContent>
          </Card>
          <Card>
            <CardHeader title="Atanan seferler" subheader={`${assigned.length} açık atama`} />
            <CardContent>
              <Stack spacing={1}>
                {assigned.slice(0, 4).map((item) => (
                  <Typography key={item.id} variant="body2">
                    {item.reference} · {item.direction === "gidis" ? "Gidiş" : "Dönüş"} · {LOAD_STATUS_LABEL[item.status]}
                  </Typography>
                ))}
                {assigned.length === 0 ? <Typography color="text.secondary">Atama yok.</Typography> : null}
              </Stack>
            </CardContent>
          </Card>
        </Stack>
      </Box>
    </Stack>
  );
}
