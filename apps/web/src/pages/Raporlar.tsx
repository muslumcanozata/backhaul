import { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { download, api } from "../api";
import { useSession } from "../session";
import type { Report } from "../types";

const REPORTS = [
  { slug: "operasyon", title: "Operasyon özeti" },
  { slug: "donus-faydasi", title: "Dönüş faydası" },
  { slug: "takograf", title: "Takograf uyum" },
  { slug: "sms", title: "SMS iletişim" },
  { slug: "filo", title: "Filo kullanım" },
  { slug: "routes", title: "Routes maliyeti" },
] as const;

type Slug = (typeof REPORTS)[number]["slug"];

function todayIso() {
  const now = new Date();
  const off = now.getTimezoneOffset();
  return new Date(now.getTime() - off * 60_000).toISOString().slice(0, 10);
}

function daysAgo(n: number) {
  const now = new Date();
  now.setDate(now.getDate() - n);
  const off = now.getTimezoneOffset();
  return new Date(now.getTime() - off * 60_000).toISOString().slice(0, 10);
}

export function Raporlar({ initialReport = "" }: { initialReport?: string }) {
  const { token, notice } = useSession();
  const [slug, setSlug] = useState<Slug>(REPORTS.some((item) => item.slug === initialReport) ? (initialReport as Slug) : "operasyon");
  const [preset, setPreset] = useState("30");
  const [fromDay, setFromDay] = useState(daysAgo(29));
  const [toDay, setToDay] = useState(todayIso());
  const [direction, setDirection] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (REPORTS.some((item) => item.slug === initialReport)) setSlug(initialReport as Slug);
  }, [initialReport]);

  useEffect(() => {
    if (preset === "1") {
      setFromDay(todayIso());
      setToDay(todayIso());
    } else if (preset === "7") {
      setFromDay(daysAgo(6));
      setToDay(todayIso());
    } else if (preset === "30") {
      setFromDay(daysAgo(29));
      setToDay(todayIso());
    }
  }, [preset]);

  const query = useMemo(() => {
    const params = new URLSearchParams({ from: fromDay, to: toDay });
    if (direction) params.set("direction", direction);
    return params.toString();
  }, [fromDay, toDay, direction]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api<Report>(`/reports/${slug}?${query}`, token)
      .then((next) => {
        if (alive) setReport(next);
      })
      .catch((err: Error) => notice(err.message))
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [slug, query, token, notice]);

  function choose(next: Slug) {
    setSlug(next);
    window.location.hash = `raporlar/${next}`;
  }

  const showDirection = slug === "operasyon" || slug === "filo";

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} sx={{ justifyContent: "space-between", gap: 2, alignItems: { md: "center" } }}>
        <Box>
          <Typography variant="h4">Raporlar</Typography>
          <Typography color="text.secondary" variant="body2">
            Dönemsel özet. Masa anlık kalır; burası geçmişe bakar.
          </Typography>
        </Box>
        <Button
          variant="outlined"
          onClick={() => {
            notice("");
            download(`/reports/${slug}/export?${query}`, token ?? "", `${slug}-${fromDay}-${toDay}.xlsx`).catch((err: Error) => notice(err.message));
          }}
        >
          Excel indir
        </Button>
      </Stack>

      <Card>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ flexWrap: "wrap" }}>
            <TextField select label="Dönem" value={preset} onChange={(event) => setPreset(event.target.value)} sx={{ minWidth: 140 }}>
              <MenuItem value="1">Bugün</MenuItem>
              <MenuItem value="7">7 gün</MenuItem>
              <MenuItem value="30">30 gün</MenuItem>
              <MenuItem value="ozel">Özel</MenuItem>
            </TextField>
            <TextField
              label="Başlangıç"
              type="date"
              value={fromDay}
              onChange={(event) => {
                setPreset("ozel");
                setFromDay(event.target.value);
              }}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              label="Bitiş"
              type="date"
              value={toDay}
              onChange={(event) => {
                setPreset("ozel");
                setToDay(event.target.value);
              }}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            {showDirection ? (
              <TextField select label="Yön" value={direction} onChange={(event) => setDirection(event.target.value)} sx={{ minWidth: 140 }}>
                <MenuItem value="">Hepsi</MenuItem>
                <MenuItem value="gidis">Gidiş</MenuItem>
                <MenuItem value="donus">Dönüş</MenuItem>
              </TextField>
            ) : null}
          </Stack>
        </CardContent>
      </Card>

      <Tabs
        value={slug}
        onChange={(_, next) => choose(next)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        {REPORTS.map((item) => (
          <Tab key={item.slug} value={item.slug} label={item.title} />
        ))}
      </Tabs>

      {loading && !report ? <Alert severity="info">Rapor yükleniyor</Alert> : null}
      {report ? (
        <>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(4, 1fr)" } }}>
            {report.kpis.map((item) => (
              <Card key={item.key}>
                <CardContent>
                  <Typography color="text.secondary" variant="overline">
                    {item.label}
                  </Typography>
                  <Typography variant="h4">{item.value}</Typography>
                  {item.hint ? (
                    <Typography variant="caption" color="text.secondary">
                      {item.hint}
                    </Typography>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </Box>

          {report.series.length ? (
            <Card>
              <CardHeader title="Trend" subheader={`${report.from_day} – ${report.to_day}`} />
              <CardContent sx={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={report.series}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis width={40} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#1877F2" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          ) : null}

          {report.columns.length ? (
            <Card>
              <CardHeader title="Detay" />
              <Table size="small">
                <TableHead>
                  <TableRow>
                    {report.columns
                      .filter((column) => column !== "driver_id")
                      .map((column) => (
                        <TableCell key={column}>{column}</TableCell>
                      ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {report.rows.map((row, index) => (
                    <TableRow
                      key={index}
                      hover={slug === "takograf" && Boolean(row.driver_id)}
                      sx={slug === "takograf" && row.driver_id ? { cursor: "pointer" } : undefined}
                      onClick={() => {
                        if (slug === "takograf" && row.driver_id) window.location.hash = `takograf/${row.driver_id}`;
                      }}
                    >
                      {report.columns
                        .filter((column) => column !== "driver_id")
                        .map((column) => (
                          <TableCell key={column}>{row[column] ?? ""}</TableCell>
                        ))}
                    </TableRow>
                  ))}
                  {report.rows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={report.columns.length}>
                        <Typography color="text.secondary">Bu dönemde satır yok.</Typography>
                      </TableCell>
                    </TableRow>
                  ) : null}
                </TableBody>
              </Table>
            </Card>
          ) : null}
        </>
      ) : null}
    </Stack>
  );
}
