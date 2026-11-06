import { useEffect, useState } from "react";
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
import { api } from "../api";
import { clock, hours } from "../labels";
import { useSession } from "../session";
import type { TachoDriver, TachoDriverDetail } from "../types";

export function Takograf({ initialDriver = "" }: { initialDriver?: string }) {
  const { token, notice } = useSession();
  const [rows, setRows] = useState<TachoDriver[]>([]);
  const [selected, setSelected] = useState(initialDriver);
  const [detail, setDetail] = useState<TachoDriverDetail | null>(null);

  useEffect(() => {
    if (initialDriver) setSelected(initialDriver);
  }, [initialDriver]);

  useEffect(() => {
    api<TachoDriver[]>("/tacho", token)
      .then(setRows)
      .catch((err: Error) => notice(err.message));
  }, [token, notice]);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    api<TachoDriverDetail>(`/tacho/${selected}`, token)
      .then(setDetail)
      .catch((err: Error) => notice(err.message));
  }, [selected, token, notice]);

  function choose(id: string) {
    setSelected(id);
    window.location.hash = `takograf/${id}`;
  }

  const current = detail ?? rows.find((item) => item.driver_id === selected) ?? null;

  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "340px 1fr" }, alignItems: "start" }}>
      <Card>
        <CardHeader title="Dijital takograf" subheader={`${rows.length} sürücü · AETR limitleri`} />
        <Stack>
          {rows.map((item) => (
            <ListItemButton key={item.driver_id} selected={item.driver_id === selected} onClick={() => choose(item.driver_id)}>
              <Stack spacing={0.75} sx={{ width: "100%" }}>
                <Stack direction="row" sx={{ justifyContent: "space-between", gap: 1 }}>
                  <Typography variant="subtitle2">{item.name}</Typography>
                  {item.warning ? <Chip size="small" color="warning" label="Sınır yakın" /> : null}
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {item.plate ?? "Araç yok"} · {item.source === "olculmus" ? "Ölçülmüş" : item.source === "tahmini" ? "Tahmini" : "Kayıt yok"}
                </Typography>
                <Meter label="Gün" used={item.daily_used} limit={item.daily_limit} remain={item.daily_remain} compact />
              </Stack>
            </ListItemButton>
          ))}
          {rows.length === 0 ? (
            <CardContent>
              <Typography color="text.secondary">Kayıtlı sürücü yok.</Typography>
            </CardContent>
          ) : null}
        </Stack>
      </Card>

      <Stack spacing={2}>
        <Card>
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

        <Card>
          <CardHeader title="Takograf geçmişi" subheader="Seyir ölçümleri ve tahmini sayaç örnekleri, yeniden eskiye" />
          {detail?.samples.length ? (
            <Table size="small">
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
