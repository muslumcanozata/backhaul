import { useEffect, useState } from "react";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { ALERT_LABEL, canOperate } from "../labels";
import { useSession } from "../session";
import type { AlertItem } from "../types";

export function Uyarilar() {
  const { token, user, notice } = useSession();
  const { vehicles } = useFleet();
  const [rows, setRows] = useState<AlertItem[]>([]);

  async function reload() {
    setRows(await api<AlertItem[]>("/alerts", token));
  }

  useEffect(() => {
    reload().catch((err: unknown) => notice(err instanceof Error ? err.message : "Uyarılar alınamadı"));
  }, [token]);

  const plates = new Map(vehicles.map((vehicle) => [vehicle.id, vehicle.plate]));

  return (
    <Card>
      <CardHeader title="Uyarılar" subheader="Takograf ve açık sefer. Tahmini sayaç ölçülmüş sayacın yerini tutmaz." />
      <CardContent>
        <Stack spacing={1.5}>
          {rows.length === 0 ? <Typography color="text.secondary">Açık uyarı yok</Typography> : null}
          {rows.map((row) => (
            <Stack key={row.id} direction="row" sx={{ alignItems: "center", justifyContent: "space-between", gap: 2 }}>
              <BoxLine
                title={`${row.level === "kritik" ? "Kritik" : "Uyarı"} · ${ALERT_LABEL[row.code] ?? row.code}`}
                detail={`${plates.get(row.vehicle_id ?? "") ?? "Araç"} · ${row.measured} / ${row.limit_value} dk${row.seen_at ? " · görüldü" : ""}`}
              />
              {canOperate(user.role) && !row.seen_at ? (
                <Button
                  size="small"
                  onClick={async () => {
                    notice("");
                    try {
                      await api(`/alerts/${row.id}/seen`, token, { method: "POST" });
                      await reload();
                    } catch (err) {
                      notice(err instanceof Error ? err.message : "Uyarı kapatılamadı");
                    }
                  }}
                >
                  Görüldü
                </Button>
              ) : null}
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}

function BoxLine({ title, detail }: { title: string; detail: string }) {
  return (
    <Stack>
      <Typography>{title}</Typography>
      <Typography variant="body2" color="text.secondary">
        {detail}
      </Typography>
    </Stack>
  );
}
