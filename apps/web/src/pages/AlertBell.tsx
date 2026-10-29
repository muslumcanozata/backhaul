import { useCallback, useEffect, useState } from "react";
import { BellIcon } from "@phosphor-icons/react";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Popover from "@mui/material/Popover";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { ALERT_LABEL, canOperate } from "../labels";
import { useSession } from "../session";
import type { AlertItem, Vehicle } from "../types";

export function AlertBell() {
  const { token, user, notice } = useSession();
  const [rows, setRows] = useState<AlertItem[]>([]);
  const [plates, setPlates] = useState<Map<string, string>>(new Map());
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const unseen = rows.filter((row) => !row.seen_at).length;

  const reload = useCallback(async () => {
    const [alerts, vehicles] = await Promise.all([api<AlertItem[]>("/alerts", token), api<Vehicle[]>("/vehicles", token)]);
    setRows(alerts);
    setPlates(new Map(vehicles.map((vehicle) => [vehicle.id, vehicle.plate])));
  }, [token]);

  useEffect(() => {
    reload().catch(() => undefined);
    const timer = window.setInterval(() => {
      reload().catch(() => undefined);
    }, 60_000);
    return () => window.clearInterval(timer);
  }, [reload]);

  async function markSeen(id: string) {
    notice("");
    try {
      await api(`/alerts/${id}/seen`, token, { method: "POST" });
      await reload();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Uyarı kapatılamadı");
    }
  }

  return (
    <>
      <IconButton
        aria-label="Uyarılar"
        onClick={(event) => {
          setAnchor(event.currentTarget);
          reload().catch(() => undefined);
        }}
        sx={{ color: "text.secondary" }}
      >
        <Badge badgeContent={unseen} color="error" max={99}>
          <BellIcon size={22} weight={unseen ? "fill" : "regular"} />
        </Badge>
      </IconButton>
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{ paper: { sx: { width: 360, maxWidth: "92vw", mt: 1 } } }}
      >
        <Stack direction="row" sx={{ px: 2, py: 1.5, alignItems: "center", justifyContent: "space-between" }}>
          <Typography variant="subtitle1">Bildirimler</Typography>
          <Typography variant="caption" color="text.secondary">
            {unseen ? `${unseen} okunmamış` : "Hepsi görüldü"}
          </Typography>
        </Stack>
        <Divider />
        {rows.length === 0 ? (
          <Box sx={{ px: 2, py: 3 }}>
            <Typography color="text.secondary" variant="body2">
              Açık uyarı yok
            </Typography>
          </Box>
        ) : (
          <List dense sx={{ maxHeight: 420, overflow: "auto", py: 0 }}>
            {rows.map((row) => (
              <ListItem
                key={row.id}
                alignItems="flex-start"
                secondaryAction={
                  canOperate(user.role) && !row.seen_at ? (
                    <Button size="small" onClick={() => void markSeen(row.id)}>
                      Görüldü
                    </Button>
                  ) : null
                }
                sx={{
                  bgcolor: row.seen_at ? "transparent" : row.level === "kritik" ? "rgba(255, 86, 48, 0.06)" : "rgba(24, 119, 242, 0.04)",
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  pr: canOperate(user.role) && !row.seen_at ? 11 : 2,
                }}
              >
                <ListItemText
                  primary={`${row.level === "kritik" ? "Kritik" : "Uyarı"} · ${ALERT_LABEL[row.code] ?? row.code}`}
                  secondary={`${plates.get(row.vehicle_id ?? "") ?? "Araç"} · ${row.measured} / ${row.limit_value} dk${row.seen_at ? " · görüldü" : ""}`}
                  slotProps={{
                    primary: { variant: "body2", sx: { fontWeight: row.seen_at ? 400 : 600 } },
                    secondary: { variant: "caption" },
                  }}
                />
              </ListItem>
            ))}
          </List>
        )}
      </Popover>
    </>
  );
}
