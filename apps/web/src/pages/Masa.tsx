import { useEffect, useMemo, useState } from "react";
import { CAlert, CButton, CCard, CCardBody, CCardHeader, CCol, CRow } from "@coreui/react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { LOAD_STATUS_LABEL, availability, canOperate, clock } from "../labels";
import { LoadingNote } from "../loading";
import { useSession } from "../session";
import type { AlertItem, Load } from "../types";
import { useLiveVehicles } from "../live-data";
import { FleetMap } from "./FleetMap";
import { LiveLegend } from "./LiveLegend";

const PIE = ["#1877F2", "#22C55E", "#FFAB00", "#FF5630", "#8E33FF", "#00B8D9"];

export function Masa() {
  const { token, user, notice } = useSession();
  const { vehicles, settings, reload } = useFleet();
  const live = useLiveVehicles(settings?.gps_stale_minutes ?? 15);
  const [loads, setLoads] = useState<Load[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [pullNote, setPullNote] = useState("");
  const operate = canOperate(user.role);

  useEffect(() => {
    Promise.all([api<Load[]>("/loads", token), api<AlertItem[]>("/alerts", token)])
      .then(([nextLoads, nextAlerts]) => {
        setLoads(nextLoads);
        setAlerts(nextAlerts);
      })
      .catch((err: Error) => notice(err.message));
  }, [token]);

  const outbound = loads.filter((item) => item.direction === "gidis" && ["planlanabilir", "atandi", "yolda"].includes(item.status));
  const pool = loads.filter((item) => item.direction === "donus" && ["havuz", "onerildi", "atandi"].includes(item.status));
  const assigned = loads.filter((item) => item.status === "atandi" || item.status === "yolda");
  const openAlerts = alerts.filter((item) => !item.seen_at);

  const counts = [
    ["Boş araç", vehicles.filter((item) => availability(item, settings) === "Boş").length],
    ["Gidiş Planlama", outbound.length],
    ["Dönüş Planlama", pool.length],
    ["Açık uyarı", openAlerts.length],
  ] as const;

  const statusChart = useMemo(() => {
    const bag = new Map<string, number>();
    for (const item of loads.filter((row) => row.status !== "iptal")) {
      bag.set(item.status, (bag.get(item.status) ?? 0) + 1);
    }
    return [...bag.entries()].map(([name, value]) => ({ name: LOAD_STATUS_LABEL[name] ?? name, value }));
  }, [loads]);

  const benefitChart = useMemo(
    () =>
      loads
        .filter((item) => item.direction === "donus" && item.benefit_try)
        .slice(0, 8)
        .map((item) => ({ name: item.reference, fayda: Number(item.benefit_try) })),
    [loads],
  );

  const fleetChart = useMemo(() => {
    const bag = new Map<string, number>();
    for (const item of vehicles) {
      const label = availability(item, settings);
      bag.set(label, (bag.get(label) ?? 0) + 1);
    }
    return [...bag.entries()].map(([name, value]) => ({ name, value }));
  }, [vehicles, settings]);

  const canPull =
    Boolean(settings?.arvento_enabled && settings.arvento_configured) || Boolean(settings?.seyir_enabled && settings.seyir_configured);

  async function pull() {
    notice("");
    setPullNote("");
    try {
      const pulled = await api<{ updated: number; unmatched: string[] }>("/integrations/telematics/pull", token, { method: "POST" });
      const missed = pulled.unmatched.filter(Boolean);
      setPullNote(missed.length ? `${pulled.updated} araç güncellendi. Eşleşmeyen plaka: ${missed.join(", ")}` : `${pulled.updated} araç güncellendi`);
      await reload();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Konum çekilemedi");
    }
  }

  return (
    <div className="d-flex flex-column gap-3">
      <div className="d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-2">
        <div>
          <h1 className="h3 mb-1">Operasyon özeti</h1>
          <div className="text-body-secondary small">Filo durumu, kuyruk yükü ve dönüş faydası</div>
        </div>
        {operate ? (
          <div className="d-flex flex-wrap gap-2">
            <CButton color="secondary" variant="outline" onClick={() => void pull()} disabled={!canPull}>
              Konumları çek
            </CButton>
            <CButton color="primary" href="#gidis">
              Gidiş Planlama
            </CButton>
            <CButton color="secondary" href="#donus">
              Dönüş Planlama
            </CButton>
          </div>
        ) : null}
      </div>
      {pullNote ? <CAlert color="info">{pullNote}</CAlert> : null}
      {settings?.routes_needs_approval ? (
        <CAlert color="warning" className="d-flex justify-content-between align-items-center flex-wrap gap-2">
          <span>
            Günlük Routes tavanı doldu ({settings.routes_today}/{settings.routes_allowed}). Yeni rota için onay gerekir.
          </span>
          {operate ? (
            <CButton
              color="warning"
              size="sm"
              onClick={() => {
                notice("");
                api("/settings/routes/approve", token, { method: "POST" })
                  .then(() => reload())
                  .catch((err: Error) => notice(err.message));
              }}
            >
              {settings.routes_limit} daha onayla
            </CButton>
          ) : null}
        </CAlert>
      ) : null}

      <CRow className="g-3">
        {counts.map(([label, value]) => (
          <CCol key={label} xs={6} lg={3}>
            <CCard>
              <CCardBody>
                <div className="text-body-secondary text-uppercase small">{label}</div>
                <div className="display-6">{value}</div>
              </CCardBody>
            </CCard>
          </CCol>
        ))}
      </CRow>

      <CRow className="g-3">
        <CCol lg={5}>
          <CCard className="h-100">
            <CCardHeader>
              <strong>Filo müsaitliği</strong>
              <div className="small text-body-secondary">Anlık araç durumu. Çubuğa tıklayınca araç listesi açılır.</div>
            </CCardHeader>
            <CCardBody style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={fleetChart}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} width={28} />
                  <Tooltip />
                  <Bar
                    dataKey="value"
                    name="Araç"
                    radius={[8, 8, 0, 0]}
                    fill="#1877F2"
                    cursor="pointer"
                    onClick={(data: { name?: string }) => {
                      if (data.name) window.location.hash = `araclar/${encodeURIComponent(data.name)}`;
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </CCardBody>
          </CCard>
        </CCol>
        <CCol lg={3}>
          <CCard className="h-100">
            <CCardHeader>
              <strong>Yük durumu</strong>
              <div className="small text-body-secondary">Açık ve tamamlanan seferler</div>
            </CCardHeader>
            <CCardBody style={{ height: 280 }}>
              {statusChart.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={statusChart} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                      {statusChart.map((item, index) => (
                        <Cell key={item.name} fill={PIE[index % PIE.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-body-secondary">Grafik için yük yok.</div>
              )}
            </CCardBody>
          </CCard>
        </CCol>
        <CCol lg={4}>
          <CCard className="h-100">
            <CCardHeader>
              <strong>Dönüş faydası</strong>
              <div className="small text-body-secondary">Hesaplanmış fırsatlar (TL)</div>
            </CCardHeader>
            <CCardBody style={{ height: 280 }}>
              {benefitChart.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={benefitChart} layout="vertical" margin={{ left: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 12 }} />
                    <YAxis type="category" dataKey="name" width={70} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="fayda" name="Fayda" radius={[0, 8, 8, 0]} fill="#22C55E" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-body-secondary">Henüz fayda hesabı yok. Dönüş Planlamandan Hesapla’yı çalıştırın.</div>
              )}
            </CCardBody>
          </CCard>
        </CCol>
      </CRow>

      <CRow className="g-3">
        <CCol lg={7}>
          <CCard>
            <CCardHeader>
              <strong>Canlı harita</strong>
              <div className="small text-body-secondary">
                {live.link} · {live.vehicles.length} araç. Araca tıklayınca detay açılır.
              </div>
            </CCardHeader>
            <LiveLegend dutyCounts={live.counts} motionCounts={live.motionCounts} />
            <div className="live-map-panel">
              {live.loading ? (
                <div
                  className="position-absolute top-0 start-0 end-0 bottom-0 d-flex align-items-center justify-content-center"
                  style={{ zIndex: 1, background: "rgba(255,255,255,0.72)" }}
                >
                  <LoadingNote label="Harita yükleniyor…" />
                </div>
              ) : null}
              <FleetMap
                vehicles={live.vehicles}
                selectedId={null}
                states={live.states}
                motions={live.motions}
                tick={live.tick}
                onSelect={(id) => {
                  window.location.hash = `takip/${id}`;
                }}
              />
            </div>
          </CCard>
        </CCol>
        <CCol lg={5}>
          <div className="d-flex flex-column gap-3">
            <CCard>
              <CCardHeader className="d-flex justify-content-between align-items-center">
                <strong>Yaklaşan gidişler</strong>
                <CButton color="link" href="#gidis" className="p-0">
                  Tümü
                </CButton>
              </CCardHeader>
              <CCardBody className="d-flex flex-column gap-3">
                {outbound.slice(0, 5).map((item) => (
                  <div key={item.id}>
                    <div className="fw-semibold">{item.reference}</div>
                    <div className="small text-body-secondary">
                      {item.pickup_il} → {item.drop_il} · {clock(item.ready_at)} · {LOAD_STATUS_LABEL[item.status] ?? item.status}
                    </div>
                  </div>
                ))}
                {outbound.length === 0 ? <div className="text-body-secondary">Açık gidiş yok.</div> : null}
              </CCardBody>
            </CCard>
            <CCard>
              <CCardHeader className="d-flex justify-content-between align-items-center">
                <strong>Dönüş fırsatları</strong>
                <CButton color="link" href="#donus" className="p-0">
                  Tümü
                </CButton>
              </CCardHeader>
              <CCardBody className="d-flex flex-column gap-3">
                {pool.slice(0, 5).map((item) => (
                  <div key={item.id}>
                    <div className="fw-semibold">{item.reference}</div>
                    <div className="small text-body-secondary">
                      {item.freight_try} TL · {item.benefit_try ? `${item.benefit_try} TL fayda · ` : ""}
                      {item.pickup_il}/{item.drop_il}
                    </div>
                  </div>
                ))}
                {pool.length === 0 ? <div className="text-body-secondary">Havuz boş.</div> : null}
              </CCardBody>
            </CCard>
            <CCard>
              <CCardHeader>
                <strong>Atanan seferler</strong>
                <div className="small text-body-secondary">{assigned.length} açık atama</div>
              </CCardHeader>
              <CCardBody className="d-flex flex-column gap-2">
                {assigned.slice(0, 4).map((item) => (
                  <div key={item.id} className="small">
                    {item.reference} · {item.direction === "gidis" ? "Gidiş" : "Dönüş"} · {LOAD_STATUS_LABEL[item.status]}
                  </div>
                ))}
                {assigned.length === 0 ? <div className="text-body-secondary">Atama yok.</div> : null}
              </CCardBody>
            </CCard>
          </div>
        </CCol>
      </CRow>
    </div>
  );
}
