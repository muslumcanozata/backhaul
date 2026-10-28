import { useEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { api, download, upload } from "../api";
import { LOAD_STATUS_LABEL, REJECT_LABEL, TRAILER_LABEL, canOperate, clock } from "../labels";
import { useSession } from "../session";
import type { ImportResult, Load } from "../types";
import { LoadFile } from "./LoadFile";
import { LoadForm } from "./LoadForm";

const OPEN_GIDIS = new Set(["planlanabilir", "atandi", "yolda"]);
const OPEN_DONUS = new Set(["havuz", "onerildi", "atandi", "yolda"]);

export function QueuePage({ direction }: { direction: "gidis" | "donus" }) {
  const { token, user, notice } = useSession();
  const fileRef = useRef<HTMLInputElement>(null);
  const [loads, setLoads] = useState<Load[]>([]);
  const [loadId, setLoadId] = useState("");
  const [adding, setAdding] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const operate = canOperate(user.role);
  const open = useMemo(
    () => loads.filter((item) => (direction === "gidis" ? OPEN_GIDIS : OPEN_DONUS).has(item.status)),
    [loads, direction],
  );
  const selected = loads.find((item) => item.id === loadId) ?? null;

  async function refresh() {
    setLoads(await api<Load[]>(`/loads?direction=${direction}`, token));
  }

  useEffect(() => {
    refresh().catch((err: Error) => notice(err.message));
  }, [token, direction]);

  async function onFile(file: File) {
    notice("");
    setResult(null);
    try {
      const imported = await upload<ImportResult>("/loads/import", token, file);
      setResult(imported);
      await refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Dosya alınamadı";
      notice(REJECT_LABEL[message] ?? message);
    }
  }

  async function exportSheet() {
    notice("");
    try {
      await download(`/loads/export?direction=${direction}`, token, `yukler-${direction}.xlsx`);
    } catch (err) {
      notice(err instanceof Error ? err.message : "Dışa aktarma başarısız");
    }
  }

  async function remove(id: string) {
    notice("");
    try {
      await api(`/loads/${id}`, token, { method: "DELETE" });
      if (loadId === id) setLoadId("");
      await refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kuyruktan çıkarılamadı";
      notice(REJECT_LABEL[message] ?? message);
    }
  }

  return (
    <Stack spacing={2}>
      <Card>
        <CardHeader
          title={direction === "gidis" ? "Gidiş kuyruğu" : "Dönüş havuzu"}
          subheader={direction === "gidis" ? "Planlanabilir ve atanmış gidişler" : "Navlunlu fırsatlar ve öneriler"}
          action={
            operate ? (
              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
                <input
                  ref={fileRef}
                  hidden
                  type="file"
                  accept=".csv,.xlsx,text/csv"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    event.target.value = "";
                    if (file) void onFile(file);
                  }}
                />
                <Button variant="contained" onClick={() => setAdding(true)}>
                  Ekle
                </Button>
                <Button variant="outlined" onClick={() => fileRef.current?.click()}>
                  Excel içe aktar
                </Button>
                <Button variant="outlined" onClick={() => void exportSheet()}>
                  Excel dışa aktar
                </Button>
                <Button component="a" href="/yuk-sablonu.xlsx" download="yuk-sablonu.xlsx" variant="text">
                  Şablon
                </Button>
                {direction === "donus" ? (
                  <Button
                    onClick={async () => {
                      notice("");
                      try {
                        await api("/returns/solve", token, { method: "POST" });
                        await refresh();
                      } catch (err) {
                        notice(err instanceof Error ? err.message : "Dönüş hesabı çalışmadı");
                      }
                    }}
                  >
                    Hesapla
                  </Button>
                ) : null}
              </Stack>
            ) : (
              <Button variant="outlined" onClick={() => void exportSheet()}>
                Excel dışa aktar
              </Button>
            )
          }
        />
        <CardContent sx={{ pt: 0 }}>
          {result ? (
            <Alert severity={result.rejected.length ? "warning" : "success"} sx={{ mb: 2 }}>
              {result.accepted} kabul, {result.updated} güncelleme, {result.rejected.length} ret
            </Alert>
          ) : null}
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Referans</TableCell>
                <TableCell>Rota</TableCell>
                <TableCell>Tonaj</TableCell>
                <TableCell>Hazır</TableCell>
                <TableCell>{direction === "donus" ? "Navlun / Fayda" : "Durum"}</TableCell>
                {direction === "donus" ? <TableCell>Aracı firma</TableCell> : null}
                <TableCell align="right">İşlem</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {open.map((item) => (
                <TableRow key={item.id} hover selected={item.id === loadId} onClick={() => setLoadId(item.id)} sx={{ cursor: "pointer" }}>
                  <TableCell>
                    <Typography variant="subtitle2">{item.reference}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {TRAILER_LABEL[item.trailer_type] ?? item.trailer_type}
                      {item.locked ? " · Kilitli" : ""}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {item.pickup_il}/{item.pickup_ilce} → {item.drop_il}/{item.drop_ilce}
                  </TableCell>
                  <TableCell>{item.tonnage}</TableCell>
                  <TableCell>{clock(item.ready_at)}</TableCell>
                  <TableCell>
                    {direction === "donus" ? (
                      <>
                        {item.freight_try ?? "—"} TL
                        {item.benefit_try ? ` · ${item.benefit_try} TL fayda` : ""}
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          {LOAD_STATUS_LABEL[item.status] ?? item.status}
                        </Typography>
                      </>
                    ) : (
                      LOAD_STATUS_LABEL[item.status] ?? item.status
                    )}
                  </TableCell>
                  {direction === "donus" ? <TableCell>{item.broker_firm || "—"}</TableCell> : null}
                  <TableCell align="right" onClick={(event) => event.stopPropagation()}>
                    {operate && item.status !== "yolda" ? (
                      <Button color="inherit" size="small" onClick={() => void remove(item.id)}>
                        Çıkar
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {open.length === 0 ? (
            <Typography color="text.secondary" sx={{ mt: 2 }}>
              Bu kuyrukta açık satır yok.
            </Typography>
          ) : null}
        </CardContent>
      </Card>
      {adding ? <LoadForm direction={direction} onSaved={refresh} onClose={() => setAdding(false)} /> : null}
      {selected ? <LoadFile load={selected} onChanged={refresh} onClose={() => setLoadId("")} /> : null}
    </Stack>
  );
}
