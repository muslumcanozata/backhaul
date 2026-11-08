import { useEffect, useState } from "react";
import { CButton, CFormInput, CFormLabel, COffcanvas, COffcanvasBody, COffcanvasHeader, COffcanvasTitle } from "@coreui/react";
import { api } from "../api";
import { REJECT_LABEL, TRAILER_LABEL, canOperate, clock } from "../labels";
import { useSession } from "../session";
import type { Candidate, Load } from "../types";

export function LoadFile({ load, onChanged, onClose }: { load: Load; onChanged: () => Promise<void>; onClose: () => void }) {
  const { token, user, notice } = useSession();
  const [detail, setDetail] = useState(load);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [dropIl, setDropIl] = useState("");
  const [dropIlce, setDropIlce] = useState("");

  useEffect(() => {
    setDetail(load);
    api<typeof load>(`/loads/${load.id}`, token)
      .then(setDetail)
      .catch((err: Error) => notice(err.message));
    api<Candidate[]>(`/loads/${load.id}/candidates`, token)
      .then(setCandidates)
      .catch((err: Error) => notice(err.message));
  }, [load.id, token]);

  async function assign(vehicleId: string) {
    notice("");
    try {
      await api(`/loads/${detail.id}/assign`, token, { method: "POST", body: JSON.stringify({ vehicle_id: vehicleId }) });
      await onChanged();
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Atama yapılamadı";
      notice(REJECT_LABEL[message] ?? message);
    }
  }

  async function cancel() {
    notice("");
    try {
      await api(`/loads/${detail.id}/cancel`, token, { method: "POST" });
      await onChanged();
      onClose();
    } catch (err) {
      notice(err instanceof Error ? err.message : "İptal edilemedi");
    }
  }

  async function revise() {
    notice("");
    try {
      await api(`/loads/${detail.id}/revise`, token, { method: "POST", body: JSON.stringify({ drop_il: dropIl, drop_ilce: dropIlce }) });
      await onChanged();
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Yer güncellenemedi";
      notice(REJECT_LABEL[message] ?? message);
    }
  }

  async function lock() {
    notice("");
    try {
      await api(`/loads/${detail.id}/lock`, token, { method: "POST" });
      await onChanged();
      onClose();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Kilit yazılamadı");
    }
  }

  async function approve() {
    notice("");
    try {
      await api(`/loads/${detail.id}/approve`, token, { method: "POST" });
      await onChanged();
      onClose();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Onay yazılamadı");
    }
  }

  async function deliver() {
    notice("");
    try {
      await api(`/loads/${detail.id}/deliver`, token, { method: "POST" });
      await onChanged();
      onClose();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Teslim kapanamadı");
    }
  }

  async function resend() {
    notice("");
    try {
      await api(`/loads/${detail.id}/sms/resend`, token, { method: "POST" });
      await onChanged();
      onClose();
    } catch (err) {
      notice(err instanceof Error ? err.message : "SMS yeniden gönderilemedi");
    }
  }

  const operate = canOperate(user.role) && detail.status === "planlanabilir";
  const rejected = (detail.alternatives ?? []).slice(0, 3);
  const shown = rejected.length ? rejected : candidates.filter((item) => !item.eligible).slice(0, 3).map((item) => ({ reference: item.plate, code: item.code ?? "" }));
  const tacho = detail.tacho_source
    ? `kalan ${detail.tacho_continuous_remain ?? 0} dk kesintisiz · ${detail.tacho_daily_remain ?? 0} dk günlük · ${detail.tacho_weekly_remain ?? 0} dk haftalık · ${detail.tacho_fortnight_remain ?? 0} dk iki haftalık · ${detail.tacho_source === "tahmini" ? "tahmini" : "ölçülmüş"}`
    : "Sayaç yok";
  const costs = detail.empty_km_cost || detail.loaded_km_cost ? `${detail.empty_km_cost ?? "—"} TL boş · ${detail.loaded_km_cost ?? "—"} TL dolu` : "Maliyet yok";

  return (
    <COffcanvas placement="end" visible onHide={onClose} style={{ width: "min(100%, 420px)" }}>
      <COffcanvasHeader>
        <COffcanvasTitle>{detail.reference}</COffcanvasTitle>
        <CButton color="secondary" variant="ghost" onClick={onClose}>
          Kapat
        </CButton>
      </COffcanvasHeader>
      <COffcanvasBody>
        <div className="text-body-secondary mb-3">
          {TRAILER_LABEL[detail.trailer_type] ?? detail.trailer_type} · {detail.tonnage} ton · {clock(detail.ready_at)}
        </div>
        <div className="d-flex flex-column gap-3 mb-4">
          <Fact
            label="Paket"
            value={detail.calculated_at ? `${detail.rule_pack || "TR-AETR-2026"} · ${clock(detail.calculated_at)}` : detail.rule_pack || "TR-AETR-2026"}
          />
          <Fact label="Yükleme" value={`${detail.pickup_il} / ${detail.pickup_ilce}`} />
          <Fact label="Boşaltma" value={`${detail.drop_il} / ${detail.drop_ilce}`} />
          <Fact label="Teslim" value={`${clock(detail.deliver_start)} – ${clock(detail.deliver_end)}`} />
          <Fact label="Navlun" value={detail.freight_try ? `${detail.freight_try} TL` : "Yok"} />
          {detail.direction === "donus" ? <Fact label="Aracı firma" value={detail.broker_firm || "Yok"} /> : null}
          {detail.customer ? <Fact label="Müşteri" value={detail.customer} /> : null}
          <Fact
            label="Fayda"
            value={detail.benefit_try ? `${detail.benefit_try} TL · ${detail.empty_km ?? "—"} boş km · ${detail.loaded_km ?? "—"} dolu km` : "Hesap yok"}
          />
          <Fact label="Maliyet" value={costs} />
          {detail.toll_try ? <Fact label="Geçiş ücreti" value={`${detail.toll_try} TL`} /> : null}
          {detail.base_km ? <Fact label="Üse dönüş" value={`${detail.base_km} km`} /> : null}
          {detail.chain_note ? <Fact label="Zincir" value={detail.chain_note} /> : null}
          <Fact label="Süre" value={detail.planned_break_min == null ? "Mola yok" : `${detail.planned_break_min} dk mola`} />
          {detail.driver_advice ? <Fact label="Sürücü tavsiyesi" value={detail.driver_advice} /> : null}
          <Fact label="SMS" value={detail.sms_job_id ? `${detail.sms_status} · ${detail.sms_job_id}` : (detail.sms_status ?? "Yok")} />
          <Fact label="Takograf" value={tacho} />
          <Fact label="Koordinat" value={detail.geocode_quality === "google" ? "Google" : "Yaklaşık"} />
        </div>
        {canOperate(user.role) && detail.sms_status === "iletilemedi" ? (
          <CButton className="mb-3" color="secondary" variant="outline" onClick={resend}>
            SMS’i yeniden gönder
          </CButton>
        ) : null}
        {shown.length ? (
          <div className="d-flex flex-column gap-2 mb-3">
            <h2 className="h5 mb-0">Diğer yükler</h2>
            {shown.map((item) => (
              <div key={item.reference} className="small text-body-secondary">
                {item.reference} · {REJECT_LABEL[item.code] ?? item.code}
              </div>
            ))}
          </div>
        ) : null}
        {canOperate(user.role) && (detail.status === "atandi" || detail.status === "onerildi") ? (
          <div className="d-flex flex-column flex-sm-row gap-2 mb-3">
            <div className="flex-grow-1">
              <CFormLabel>Boşaltma ili</CFormLabel>
              <CFormInput value={dropIl} onChange={(event) => setDropIl(event.target.value)} />
            </div>
            <div className="flex-grow-1">
              <CFormLabel>Boşaltma ilçesi</CFormLabel>
              <CFormInput value={dropIlce} onChange={(event) => setDropIlce(event.target.value)} />
            </div>
            <div className="d-flex align-items-end">
              <CButton color="secondary" onClick={revise} disabled={!dropIl || !dropIlce}>
                Yeri güncelle
              </CButton>
            </div>
          </div>
        ) : null}
        <h2 className="h5 mb-2">Araçlar</h2>
        <div className="d-flex flex-column gap-3">
          {candidates.map((item) => (
            <div key={item.vehicle_id} className="d-flex align-items-center justify-content-between gap-2">
              <div>
                <div className="fw-semibold">{item.plate}</div>
                <div className="small text-body-secondary">
                  {item.eligible ? `${item.empty_km} boş km · ${item.loaded_km} dolu km` : (REJECT_LABEL[item.code ?? ""] ?? item.code)}
                </div>
              </div>
              {operate && item.eligible ? (
                <CButton color="primary" onClick={() => assign(item.vehicle_id)}>
                  Ata
                </CButton>
              ) : null}
            </div>
          ))}
        </div>
        {canOperate(user.role) && detail.status === "onerildi" ? (
          <CButton className="mt-3" color="primary" onClick={approve}>
            Onayla ve kilitle
          </CButton>
        ) : null}
        {canOperate(user.role) && detail.status === "atandi" && !detail.locked ? (
          <CButton className="mt-3" color="primary" onClick={lock}>
            Kilitle
          </CButton>
        ) : null}
        {canOperate(user.role) && detail.status === "atandi" ? (
          <div className="d-flex gap-2 mt-4">
            <CButton color="secondary" variant="outline" onClick={cancel}>
              Atamayı iptal et
            </CButton>
            <CButton color="primary" onClick={deliver}>
              Teslim edildi
            </CButton>
          </div>
        ) : null}
      </COffcanvasBody>
    </COffcanvas>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="small text-body-secondary">{label}</div>
      <div>{value}</div>
    </div>
  );
}
