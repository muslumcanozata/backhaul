import { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import ListItemButton from "@mui/material/ListItemButton";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { clock, hours } from "../labels";
import { LoadingNote } from "../loading";
import { useSession } from "../session";
import type { TachoDriver, TachoDriverDetail } from "../types";

const ACTIVITY_LABEL: Record<string, string> = {
  DRIVE: "Sürüş",
  REST: "Dinlenme",
  WORK: "İş",
  AVAILABLE: "Müsait",
  AVAIL: "Müsait",
  BREAK: "Mola",
  UNKNOWN: "Bilinmiyor",
};

export function Takograf({ initialDriver = "" }: { initialDriver?: string }) {
  const { token, notice } = useSession();
  const [rows, setRows] = useState<TachoDriver[]>([]);
  const [selected, setSelected] = useState(initialDriver);
  const [detail, setDetail] = useState<TachoDriverDetail | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    if (initialDriver) setSelected(initialDriver);
  }, [initialDriver]);

  useEffect(() => {
    let alive = true;
    setListLoading(true);
    api<TachoDriver[]>("/tacho", token)
      .then((next) => {
        if (alive) setRows(next);
      })
      .catch((err: Error) => notice(err.message))
      .finally(() => {
        if (alive) setListLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [token, notice]);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      setDetailLoading(false);
      return;
    }
    let alive = true;
    setDetailLoading(true);
    api<TachoDriverDetail>(`/tacho/${selected}`, token)
      .then((next) => {
        if (alive) setDetail(next);
      })
      .catch((err: Error) => notice(err.message))
      .finally(() => {
        if (alive) setDetailLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [selected, token, notice]);

  function choose(id: string) {
    setSelected(id);
    window.location.hash = `takograf/${id}`;
  }

  const ordered = useMemo(
    () =>
      [...rows].sort((a, b) => {
        if (a.warning !== b.warning) return a.warning ? -1 : 1;
        if (a.daily_remain !== b.daily_remain) return a.daily_remain - b.daily_remain;
        return a.name.localeCompare(b.name, "tr");
      }),
    [rows],
  );

  const summary = useMemo(
    () => ({
      warning: rows.filter((item) => item.warning).length,
      estimated: rows.filter((item) => item.source === "tahmini").length,
      noVehicle: rows.filter((item) => !item.plate).length,
    }),
    [rows],
  );

  const current = detail ?? ordered.find((item) => item.driver_id === selected) ?? null;

  const dailySeries = useMemo(() => {
    if (!detail?.samples.length) return [];
    return [...detail.samples]
      .sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime())
      .map((item) => ({
        at: clock(item.recorded_at),
        daily: item.daily_min,
        source: item.source,
      }));
  }, [detail]);

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
          width: { lg: 340 },
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          height: { xs: "min(420px, 50dvh)", lg: "auto" },
          minHeight: 0,
        }}
      >
        <CardHeader title="Dijital takograf" subheader={`${rows.length} sürücü · kalan güne göre`} />
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1, px: 2, pb: 1.5 }}>
          <Chip size="small" color={summary.warning ? "warning" : "default"} label={`Sınır yakın ${summary.warning}`} />
          <Chip size="small" label={`Tahmini ${summary.estimated}`} />
          <Chip size="small" label={`Araçsız ${summary.noVehicle}`} />
        </Stack>
        <Stack sx={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
          {ordered.map((item) => (
            <ListItemButton key={item.driver_id} selected={item.driver_id === selected} onClick={() => choose(item.driver_id)} sx={{ flexShrink: 0 }}>
              <Stack spacing={0.75} sx={{ width: "100%" }}>
                <Stack direction="row" sx={{ justifyContent: "space-between", gap: 1 }}>
                  <Typography variant="subtitle2">{item.name}</Typography>
                  {item.warning ? <Chip size="small" color="warning" label="Sınır yakın" /> : null}
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {item.plate ?? "Araç yok"} · {sourceLabel(item.source)}
                  {item.activity_status ? ` · ${activityLabel(item.activity_status)}` : ""}
                </Typography>
                <Meter label="Gün" used={item.daily_used} limit={item.daily_limit} remain={item.daily_remain} compact />
              </Stack>
            </ListItemButton>
          ))}
          {listLoading ? (
            <LoadingNote label="Takograf yükleniyor…" />
          ) : rows.length === 0 ? (
            <CardContent>
              <Typography color="text.secondary">Kayıtlı sürücü yok.</Typography>
            </CardContent>
          ) : null}
        </Stack>
      </Card>

      <Stack spacing={2} sx={{ flex: 1, minWidth: 0, minHeight: 0, overflow: { lg: "hidden" } }}>
        <Card sx={{ flexShrink: 0 }}>
          <CardHeader
            title={current?.name ?? "Sürücü seçin"}
            subheader={
              current
                ? `${current.plate ?? "Araç yok"} · ${current.card_id ?? "Kart yok"} · ${current.recorded_at ? clock(current.recorded_at) : "Ölçüm yok"}`
                : "Günlük, haftalık ve iki haftalık kullanım bu ekranda durur."
            }
          />
          {current ? (
            <CardContent>
              <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1, mb: 2 }}>
                <Chip size="small" label={sourceLabel(current.source)} color={current.source === "olculmus" ? "success" : "default"} />
                {current.activity_status ? <Chip size="small" label={activityLabel(current.activity_status)} /> : null}
                {current.daily_rest_remain_min != null ? <Chip size="small" label={`Günlük dinlenme kalan ${hours(current.daily_rest_remain_min)}`} /> : null}
                {current.weekly_rest_remain_min != null ? <Chip size="small" label={`Haftalık dinlenme kalan ${hours(current.weekly_rest_remain_min)}`} /> : null}
              </Stack>
              <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
                <Meter label="Kesintisiz sürüş" used={current.continuous_used} limit={current.continuous_limit} remain={current.continuous_remain} />
                <Meter label="Günlük sürüş" used={current.daily_used} limit={current.daily_limit} remain={current.daily_remain} />
                <Meter label="Haftalık sürüş" used={current.weekly_used} limit={current.weekly_limit} remain={current.weekly_remain} />
                <Meter label="İki haftalık sürüş" used={current.fortnight_used} limit={current.fortnight_limit} remain={current.fortnight_remain} />
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Uzatma hakkı {current.extensions_used} / {current.extensions_limit} kullanıldı.
                {current.source === "tahmini" ? " Sayaç tahmini; Seyir ölçümü gelince kesinleşir." : ""}
              </Typography>
            </CardContent>
          ) : null}
        </Card>

        <Card sx={{ flexShrink: 0 }}>
          <CardHeader title="Günlük kullanım" subheader="Seçili sürücünün örneklenen günlük sürüş dakikası" />
          <CardContent sx={{ height: 220 }}>
            {detailLoading ? (
              <LoadingNote label="Grafik yükleniyor…" />
            ) : dailySeries.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dailySeries} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="at" tick={{ fontSize: 11 }} minTickGap={24} />
                  <YAxis width={36} tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip formatter={(value) => [`${value} dk`, "Günlük"]} />
                  <Line type="monotone" dataKey="daily" name="Günlük" stroke="#1877F2" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <Typography color="text.secondary">{current ? "Çizgi için en az iki örnek gerekir." : "Çizgi için bir sürücü seçin."}</Typography>
            )}
          </CardContent>
        </Card>

        <Card
          sx={{
            flex: { lg: 1 },
            minHeight: 0,
            height: { xs: "min(420px, 50dvh)", lg: "auto" },
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <CardHeader title="Takograf geçmişi" subheader="Seyir ölçümleri ve tahmini sayaç örnekleri, yeniden eskiye" />
          {detailLoading ? (
            <LoadingNote label="Geçmiş yükleniyor…" />
          ) : detail?.samples.length ? (
            <Box sx={{ flex: 1, minHeight: 0, overflow: "auto" }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Zaman</TableCell>
                    <TableCell>Kaynak</TableCell>
                    <TableCell align="right">Kesintisiz</TableCell>
                    <TableCell align="right">Günlük</TableCell>
                    <TableCell align="right">Haftalık</TableCell>
                    <TableCell align="right">İki haftalık</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {detail.samples.map((item) => (
                    <TableRow key={item.recorded_at}>
                      <TableCell>{clock(item.recorded_at)}</TableCell>
                      <TableCell>{item.source === "olculmus" ? "Ölçülmüş" : "Tahmini"}</TableCell>
                      <TableCell align="right">{hours(item.continuous_min)}</TableCell>
                      <TableCell align="right">{hours(item.daily_min)}</TableCell>
                      <TableCell align="right">{hours(item.weekly_min)}</TableCell>
                      <TableCell align="right">{hours(item.fortnight_min)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          ) : (
            <CardContent>
              <Typography color="text.secondary">{current ? "Bu sürücüde henüz geçmiş yok." : "Geçmiş için bir sürücü seçin."}</Typography>
            </CardContent>
          )}
        </Card>
      </Stack>
    </Box>
  );
}

function sourceLabel(source: string | null | undefined) {
  if (source === "olculmus") return "Ölçülmüş";
  if (source === "tahmini") return "Tahmini";
  return "Kayıt yok";
}

function activityLabel(value: string) {
  const key = value.trim().toUpperCase();
  return ACTIVITY_LABEL[key] ?? value;
}

function Meter({
  label,
  used,
  limit,
  remain,
  compact = false,
}: {
  label: string;
  used: number;
  limit: number;
  remain: number;
  compact?: boolean;
}) {
  const ratio = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const color = remain <= 30 || ratio >= 90 ? "error" : ratio >= 70 ? "warning" : "success";
  return (
    <Stack spacing={0.5}>
      <Stack direction="row" sx={{ justifyContent: "space-between", gap: 1 }}>
        <Typography variant={compact ? "caption" : "subtitle2"}>{label}</Typography>
        <Typography variant="caption" color="text.secondary">
          {hours(used)} / {hours(limit)}
        </Typography>
      </Stack>
      <LinearProgress variant="determinate" value={ratio} color={color} sx={{ height: compact ? 6 : 8, borderRadius: 99 }} />
      {compact ? null : (
        <Typography variant="caption" color="text.secondary">
          Kalan {hours(remain)}
        </Typography>
      )}
    </Stack>
  );
}
