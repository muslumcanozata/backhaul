import { useEffect, useState } from "react";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
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
    <Drawer anchor="right" open onClose={onClose} slotProps={{ paper: { sx: { width: { xs: "100%", sm: 420 }, p: 3 } } }}>
      <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="h5">{detail.reference}</Typography>
        <Button onClick={onClose}>Kapat</Button>
      </Stack>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        {TRAILER_LABEL[detail.trailer_type] ?? detail.trailer_type} · {detail.tonnage} ton · {clock(detail.ready_at)}
      </Typography>
      <Stack spacing={1.5} sx={{ mb: 3 }}>
        <Fact label="Paket" value={detail.calculated_at ? `${detail.rule_pack || "TR-AETR-2026"} · ${clock(detail.calculated_at)}` : (detail.rule_pack || "TR-AETR-2026")} />
        <Fact label="Yükleme" value={`${detail.pickup_il} / ${detail.pickup_ilce}`} />
        <Fact label="Boşaltma" value={`${detail.drop_il} / ${detail.drop_ilce}`} />
        <Fact label="Teslim" value={`${clock(detail.deliver_start)} – ${clock(detail.deliver_end)}`} />
        <Fact label="Navlun" value={detail.freight_try ? `${detail.freight_try} TL` : "Yok"} />
        {detail.direction === "donus" ? <Fact label="Aracı firma" value={detail.broker_firm || "Yok"} /> : null}
        {detail.customer ? <Fact label="Müşteri" value={detail.customer} /> : null}
        <Fact label="Fayda" value={detail.benefit_try ? `${detail.benefit_try} TL · ${detail.empty_km ?? "—"} boş km · ${detail.loaded_km ?? "—"} dolu km` : "Hesap yok"} />
        <Fact label="Maliyet" value={costs} />
        <Fact label="Süre" value={detail.planned_break_min == null ? "Mola yok" : `${detail.planned_break_min} dk mola`} />
        <Fact label="SMS" value={detail.sms_job_id ? `${detail.sms_status} · ${detail.sms_job_id}` : (detail.sms_status ?? "Yok")} />
        <Fact label="Takograf" value={tacho} />
        <Fact label="Koordinat" value={detail.geocode_quality === "google" ? "Google" : "Yaklaşık"} />
      </Stack>
      {canOperate(user.role) && detail.sms_status === "iletilemedi" ? (
        <Button sx={{ mb: 2 }} onClick={resend}>
          SMS’i yeniden gönder
        </Button>
      ) : null}
      {shown.length ? (
        <Stack spacing={1} sx={{ mb: 2 }}>
          <Typography variant="h6">Diğer yükler</Typography>
          {shown.map((item) => (
            <Typography key={item.reference} variant="body2" color="text.secondary">
              {item.reference} · {REJECT_LABEL[item.code] ?? item.code}
            </Typography>
          ))}
        </Stack>
      ) : null}
      {canOperate(user.role) && (detail.status === "atandi" || detail.status === "onerildi") ? (
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <TextField label="Boşaltma ili" value={dropIl} onChange={(event) => setDropIl(event.target.value)} />
          <TextField label="Boşaltma ilçesi" value={dropIlce} onChange={(event) => setDropIlce(event.target.value)} />
          <Button onClick={revise} disabled={!dropIl || !dropIlce}>
            Yeri güncelle
          </Button>
        </Stack>
      ) : null}
      <Typography variant="h6" sx={{ mb: 1 }}>
        Araçlar
      </Typography>
      <Stack spacing={1.5}>
        {candidates.map((item) => (
          <Stack key={item.vehicle_id} direction="row" sx={{ alignItems: "center", justifyContent: "space-between", gap: 1 }}>
            <div>
              <Typography variant="subtitle2">{item.plate}</Typography>
              <Typography variant="body2" color="text.secondary">
                {item.eligible
                  ? `${item.empty_km} boş km · ${item.loaded_km} dolu km`
                  : (REJECT_LABEL[item.code ?? ""] ?? item.code)}
              </Typography>
            </div>
            {operate && item.eligible ? (
              <Button variant="contained" onClick={() => assign(item.vehicle_id)}>
                Ata
              </Button>
            ) : null}
          </Stack>
        ))}
      </Stack>
      {canOperate(user.role) && detail.status === "onerildi" ? (
        <Button sx={{ mt: 2 }} variant="contained" onClick={approve}>
          Onayla
        </Button>
      ) : null}
      {canOperate(user.role) && detail.status === "atandi" ? (
        <Stack direction="row" spacing={1} sx={{ mt: 3 }}>
          <Button color="inherit" onClick={cancel}>
            Atamayı iptal et
          </Button>
          <Button onClick={deliver}>Teslim edildi</Button>
        </Stack>
      ) : null}
    </Drawer>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography>{value}</Typography>
    </div>
  );
}
