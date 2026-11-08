import { useEffect, useMemo, useRef, useState } from "react";
import {
  CAlert,
  CButton,
  CCard,
  CCardBody,
  CCardHeader,
  CTable,
  CTableBody,
  CTableDataCell,
  CTableHead,
  CTableHeaderCell,
  CTableRow,
} from "@coreui/react";
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
    <div className="d-flex flex-column gap-3">
      <CCard>
        <CCardHeader className="d-flex flex-column flex-lg-row justify-content-between gap-2 align-items-lg-start">
          <div>
            <strong>{direction === "gidis" ? "Gidiş Planlama" : "Dönüş Planlama"}</strong>
            <div className="small text-body-secondary">
              {direction === "gidis" ? "Planlanabilir ve atanmış gidişler" : "Navlunlu fırsatlar ve öneriler"}
            </div>
          </div>
          {operate ? (
            <div className="d-flex flex-wrap gap-2 justify-content-lg-end">
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
              <CButton color="primary" onClick={() => setAdding(true)}>
                Ekle
              </CButton>
              <CButton color="secondary" variant="outline" onClick={() => fileRef.current?.click()}>
                Excel içe aktar
              </CButton>
              <CButton color="secondary" variant="outline" onClick={() => void exportSheet()}>
                Excel dışa aktar
              </CButton>
              <CButton color="link" href="/yuk-sablonu.xlsx" download="yuk-sablonu.xlsx">
                Şablon
              </CButton>
              {direction === "donus" ? (
                <CButton
                  color="secondary"
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
                </CButton>
              ) : null}
            </div>
          ) : (
            <CButton color="secondary" variant="outline" onClick={() => void exportSheet()}>
              Excel dışa aktar
            </CButton>
          )}
        </CCardHeader>
        <CCardBody>
          {result ? (
            <CAlert color={result.rejected.length ? "warning" : "success"}>
              {result.accepted} kabul, {result.updated} güncelleme, {result.rejected.length} ret
            </CAlert>
          ) : null}
          <CTable small hover responsive className="mb-0">
            <CTableHead>
              <CTableRow>
                <CTableHeaderCell>Referans</CTableHeaderCell>
                <CTableHeaderCell>Rota</CTableHeaderCell>
                <CTableHeaderCell>Tonaj</CTableHeaderCell>
                <CTableHeaderCell>Hazır</CTableHeaderCell>
                <CTableHeaderCell>{direction === "donus" ? "Navlun / Fayda" : "Durum"}</CTableHeaderCell>
                {direction === "donus" ? <CTableHeaderCell>Aracı firma</CTableHeaderCell> : null}
                <CTableHeaderCell className="text-end">İşlem</CTableHeaderCell>
              </CTableRow>
            </CTableHead>
            <CTableBody>
              {open.map((item) => (
                <CTableRow
                  key={item.id}
                  active={item.id === loadId}
                  style={{ cursor: "pointer" }}
                  onClick={() => setLoadId(item.id)}
                >
                  <CTableDataCell>
                    <div className="fw-semibold">{item.reference}</div>
                    <div className="small text-body-secondary">
                      {TRAILER_LABEL[item.trailer_type] ?? item.trailer_type}
                      {item.locked ? " · Kilitli" : ""}
                    </div>
                  </CTableDataCell>
                  <CTableDataCell>
                    {item.pickup_il}/{item.pickup_ilce} → {item.drop_il}/{item.drop_ilce}
                  </CTableDataCell>
                  <CTableDataCell>{item.tonnage}</CTableDataCell>
                  <CTableDataCell>{clock(item.ready_at)}</CTableDataCell>
                  <CTableDataCell>
                    {direction === "donus" ? (
                      <>
                        {item.freight_try ?? "—"} TL
                        {item.benefit_try ? ` · ${item.benefit_try} TL fayda` : ""}
                        <div className="small text-body-secondary">{LOAD_STATUS_LABEL[item.status] ?? item.status}</div>
                      </>
                    ) : (
                      LOAD_STATUS_LABEL[item.status] ?? item.status
                    )}
                  </CTableDataCell>
                  {direction === "donus" ? <CTableDataCell>{item.broker_firm || "—"}</CTableDataCell> : null}
                  <CTableDataCell className="text-end" onClick={(event) => event.stopPropagation()}>
                    {operate && item.status !== "yolda" ? (
                      <CButton color="secondary" variant="ghost" size="sm" onClick={() => void remove(item.id)}>
                        Çıkar
                      </CButton>
                    ) : null}
                  </CTableDataCell>
                </CTableRow>
              ))}
            </CTableBody>
          </CTable>
          {open.length === 0 ? <div className="text-body-secondary mt-3">Bu kuyrukta açık satır yok.</div> : null}
        </CCardBody>
      </CCard>
      {adding ? <LoadForm direction={direction} onSaved={refresh} onClose={() => setAdding(false)} /> : null}
      {selected ? <LoadFile load={selected} onChanged={refresh} onClose={() => setLoadId("")} /> : null}
    </div>
  );
}
