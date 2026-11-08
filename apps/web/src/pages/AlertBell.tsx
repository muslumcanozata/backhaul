import { useCallback, useEffect, useState } from "react";
import {
  CBadge,
  CButton,
  CDropdown,
  CDropdownHeader,
  CDropdownItem,
  CDropdownMenu,
  CDropdownToggle,
} from "@coreui/react";
import CIcon from "@coreui/icons-react";
import { cilBell } from "@coreui/icons";
import { api } from "../api";
import { ALERT_LABEL, canOperate } from "../labels";
import { useSession } from "../session";
import type { AlertItem, Vehicle } from "../types";

export function AlertBell() {
  const { token, user, notice } = useSession();
  const [rows, setRows] = useState<AlertItem[]>([]);
  const [plates, setPlates] = useState<Map<string, string>>(new Map());
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
    <CDropdown variant="nav-item" alignment="end" onShow={() => void reload().catch(() => undefined)}>
      <CDropdownToggle caret={false} className="py-0 px-1">
        <CIcon icon={cilBell} size="lg" />
        {unseen ? (
          <CBadge color="danger" position="top-end" shape="rounded-pill" className="ms-n2">
            {unseen > 99 ? "99+" : unseen}
          </CBadge>
        ) : null}
      </CDropdownToggle>
      <CDropdownMenu className="pt-0" style={{ minWidth: 320, maxWidth: "92vw" }}>
        <CDropdownHeader className="bg-body-tertiary fw-semibold d-flex justify-content-between">
          <span>Bildirimler</span>
          <span className="text-body-secondary small">{unseen ? `${unseen} okunmamış` : "Hepsi görüldü"}</span>
        </CDropdownHeader>
        {rows.length === 0 ? (
          <div className="px-3 py-3 text-body-secondary small">Açık uyarı yok</div>
        ) : (
          <div style={{ maxHeight: 420, overflow: "auto" }}>
            {rows.map((row) => (
              <CDropdownItem
                key={row.id}
                className="d-flex flex-column align-items-stretch gap-1 py-2"
                style={{
                  whiteSpace: "normal",
                  backgroundColor: row.seen_at
                    ? undefined
                    : row.level === "kritik"
                      ? "rgba(255, 86, 48, 0.06)"
                      : "rgba(24, 119, 242, 0.04)",
                }}
                as="div"
              >
                <div className={row.seen_at ? "fw-normal" : "fw-semibold"}>
                  {row.level === "kritik" ? "Kritik" : "Uyarı"} · {ALERT_LABEL[row.code] ?? row.code}
                </div>
                <div className="small text-body-secondary">
                  {plates.get(row.vehicle_id ?? "") ?? "Araç"} · {row.measured} / {row.limit_value} dk
                  {row.seen_at ? " · görüldü" : ""}
                </div>
                {canOperate(user.role) && !row.seen_at ? (
                  <CButton size="sm" color="primary" variant="ghost" className="align-self-start px-0" onClick={() => void markSeen(row.id)}>
                    Görüldü
                  </CButton>
                ) : null}
              </CDropdownItem>
            ))}
          </div>
        )}
      </CDropdownMenu>
    </CDropdown>
  );
}
