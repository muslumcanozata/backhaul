import { useEffect, useMemo, useState } from "react";
import { CBadge, CCard, CCardBody, CCardHeader, CProgress, CTable, CTableBody, CTableDataCell, CTableHead, CTableHeaderCell, CTableRow } from "@coreui/react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { clock, hours } from "../labels";
import { LoadingNote } from "../loading";
import { useSession } from "../session";
import type { TachoDriver, TachoDriverDetail } from "../types";

const ACTIVITY_LABEL: Record<string, string> = {
  DRIVE: "Sürüş",
  REST: "Dinlenme",
  WORK: "İş",
  AVAILABLE: "Müsait",
  AVAIL: "Müsait",
  BREAK: "Mola",
  UNKNOWN: "Bilinmiyor",
};

export function Takograf({ initialDriver = "" }: { initialDriver?: string }) {
  const { token, notice } = useSession();
  const [rows, setRows] = useState<TachoDriver[]>([]);
  const [selected, setSelected] = useState(initialDriver);
  const [detail, setDetail] = useState<TachoDriverDetail | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    if (initialDriver) setSelected(initialDriver);
  }, [initialDriver]);

  useEffect(() => {
    let alive = true;
    setListLoading(true);
    api<TachoDriver[]>("/tacho", token)
      .then((next) => {
        if (alive) setRows(next);
      })
      .catch((err: Error) => notice(err.message))
      .finally(() => {
        if (alive) setListLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [token, notice]);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      setDetailLoading(false);
      return;
    }
    let alive = true;
    setDetailLoading(true);
    api<TachoDriverDetail>(`/tacho/${selected}`, token)
      .then((next) => {
        if (alive) setDetail(next);
      })
      .catch((err: Error) => notice(err.message))
      .finally(() => {
        if (alive) setDetailLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [selected, token, notice]);

  function choose(id: string) {
    setSelected(id);
    window.location.hash = `takograf/${id}`;
  }

  const ordered = useMemo(
    () =>
      [...rows].sort((a, b) => {
        if (a.warning !== b.warning) return a.warning ? -1 : 1;
        if (a.daily_remain !== b.daily_remain) return a.daily_remain - b.daily_remain;
        return a.name.localeCompare(b.name, "tr");
      }),
    [rows],
  );

  const summary = useMemo(
    () => ({
      warning: rows.filter((item) => item.warning).length,
      estimated: rows.filter((item) => item.source === "tahmini").length,
      noVehicle: rows.filter((item) => !item.plate).length,
    }),
    [rows],
  );

  const current = detail ?? ordered.find((item) => item.driver_id === selected) ?? null;

  const dailySeries = useMemo(() => {
    if (!detail?.samples.length) return [];
    return [...detail.samples]
      .sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime())
      .map((item) => ({
        at: clock(item.recorded_at),
        daily: item.daily_min,
        source: item.source,
      }));
  }, [detail]);

  return (
    <div className="d-flex flex-column flex-lg-row gap-3" style={{ minHeight: 480 }}>
      <CCard
        className="d-flex flex-column flex-shrink-0"
        style={{ width: 340, maxWidth: "100%", minHeight: 0, height: "min(420px, 50dvh)" }}
      >
        <CCardHeader>
          <strong>Dijital takograf</strong>
          <div className="small text-body-secondary">
            {rows.length} sürücü · kalan güne göre
          </div>
        </CCardHeader>
        <div className="d-flex flex-wrap gap-2 px-3 pb-2">
          <CBadge color={summary.warning ? "warning" : "secondary"}>Sınır yakın {summary.warning}</CBadge>
          <CBadge color="secondary">Tahmini {summary.estimated}</CBadge>
          <CBadge color="secondary">Araçsız {summary.noVehicle}</CBadge>
        </div>
        <div className="flex-grow-1 overflow-auto" style={{ minHeight: 0 }}>
          {ordered.map((item) => {
            const active = item.driver_id === selected;
            return (
              <button
                key={item.driver_id}
                type="button"
                className={`w-100 border-0 border-bottom text-start px-3 py-2 ${active ? "bg-body-secondary" : "bg-transparent"}`}
                onClick={() => choose(item.driver_id)}
              >
                <div className="d-flex flex-column gap-1">
                  <div className="d-flex justify-content-between gap-2">
                    <span className="fw-semibold">{item.name}</span>
                    {item.warning ? <CBadge color="warning">Sınır yakın</CBadge> : null}
                  </div>
                  <div className="small text-body-secondary">
                    {item.plate ?? "Araç yok"} · {sourceLabel(item.source)}
                    {item.activity_status ? ` · ${activityLabel(item.activity_status)}` : ""}
                  </div>
                  <Meter label="Gün" used={item.daily_used} limit={item.daily_limit} remain={item.daily_remain} compact />
                </div>
              </button>
            );
          })}
          {listLoading ? (
            <LoadingNote label="Takograf yükleniyor…" />
          ) : rows.length === 0 ? (
            <div className="px-3 pb-3 text-body-secondary">Kayıtlı sürücü yok.</div>
          ) : null}
        </div>
      </CCard>

      <div className="d-flex flex-column gap-3 flex-grow-1" style={{ minWidth: 0, minHeight: 0 }}>
        <CCard className="flex-shrink-0">
          <CCardHeader>
            <strong>{current?.name ?? "Sürücü seçin"}</strong>
            <div className="small text-body-secondary">
              {current
                ? `${current.plate ?? "Araç yok"} · ${current.card_id ?? "Kart yok"} · ${current.recorded_at ? clock(current.recorded_at) : "Ölçüm yok"}`
                : "Günlük, haftalık ve iki haftalık kullanım bu ekranda durur."}
            </div>
          </CCardHeader>
          {current ? (
            <CCardBody>
              <div className="d-flex flex-wrap gap-2 mb-3">
                <CBadge color={current.source === "olculmus" ? "success" : "secondary"}>{sourceLabel(current.source)}</CBadge>
                {current.activity_status ? <CBadge color="secondary">{activityLabel(current.activity_status)}</CBadge> : null}
                {current.daily_rest_remain_min != null ? (
                  <CBadge color="secondary">Günlük dinlenme kalan {hours(current.daily_rest_remain_min)}</CBadge>
                ) : null}
                {current.weekly_rest_remain_min != null ? (
                  <CBadge color="secondary">Haftalık dinlenme kalan {hours(current.weekly_rest_remain_min)}</CBadge>
                ) : null}
              </div>
              <div className="row g-3">
                <div className="col-12 col-sm-6">
                  <Meter label="Kesintisiz sürüş" used={current.continuous_used} limit={current.continuous_limit} remain={current.continuous_remain} />
                </div>
                <div className="col-12 col-sm-6">
                  <Meter label="Günlük sürüş" used={current.daily_used} limit={current.daily_limit} remain={current.daily_remain} />
                </div>
                <div className="col-12 col-sm-6">
                  <Meter label="Haftalık sürüş" used={current.weekly_used} limit={current.weekly_limit} remain={current.weekly_remain} />
                </div>
                <div className="col-12 col-sm-6">
                  <Meter label="İki haftalık sürüş" used={current.fortnight_used} limit={current.fortnight_limit} remain={current.fortnight_remain} />
                </div>
              </div>
              <div className="small text-body-secondary mt-3">
                Uzatma hakkı {current.extensions_used} / {current.extensions_limit} kullanıldı.
                {current.source === "tahmini" ? " Sayaç tahmini; Seyir ölçümü gelince kesinleşir." : ""}
              </div>
            </CCardBody>
          ) : null}
        </CCard>

        <CCard className="flex-shrink-0">
          <CCardHeader>
            <strong>Günlük kullanım</strong>
            <div className="small text-body-secondary">Seçili sürücünün örneklenen günlük sürüş dakikası</div>
          </CCardHeader>
          <CCardBody style={{ height: 220 }}>
            {detailLoading ? (
              <LoadingNote label="Grafik yükleniyor…" />
            ) : dailySeries.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dailySeries} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="at" tick={{ fontSize: 11 }} minTickGap={24} />
                  <YAxis width={36} tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip formatter={(value) => [`${value} dk`, "Günlük"]} />
                  <Line type="monotone" dataKey="daily" name="Günlük" stroke="#1877F2" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-body-secondary">{current ? "Çizgi için en az iki örnek gerekir." : "Çizgi için bir sürücü seçin."}</div>
            )}
          </CCardBody>
        </CCard>

        <CCard className="d-flex flex-column overflow-hidden" style={{ minHeight: 0, height: "min(420px, 50dvh)" }}>
          <CCardHeader>
            <strong>Takograf geçmişi</strong>
            <div className="small text-body-secondary">Seyir ölçümleri ve tahmini sayaç örnekleri, yeniden eskiye</div>
          </CCardHeader>
          {detailLoading ? (
            <LoadingNote label="Geçmiş yükleniyor…" />
          ) : detail?.samples.length ? (
            <div className="flex-grow-1 overflow-auto" style={{ minHeight: 0 }}>
              <CTable small hover striped className="mb-0">
                <CTableHead>
                  <CTableRow>
                    <CTableHeaderCell>Zaman</CTableHeaderCell>
                    <CTableHeaderCell>Kaynak</CTableHeaderCell>
                    <CTableHeaderCell className="text-end">Kesintisiz</CTableHeaderCell>
                    <CTableHeaderCell className="text-end">Günlük</CTableHeaderCell>
                    <CTableHeaderCell className="text-end">Haftalık</CTableHeaderCell>
                    <CTableHeaderCell className="text-end">İki haftalık</CTableHeaderCell>
                  </CTableRow>
                </CTableHead>
                <CTableBody>
                  {detail.samples.map((item) => (
                    <CTableRow key={item.recorded_at}>
                      <CTableDataCell>{clock(item.recorded_at)}</CTableDataCell>
                      <CTableDataCell>{item.source === "olculmus" ? "Ölçülmüş" : "Tahmini"}</CTableDataCell>
                      <CTableDataCell className="text-end">{hours(item.continuous_min)}</CTableDataCell>
                      <CTableDataCell className="text-end">{hours(item.daily_min)}</CTableDataCell>
                      <CTableDataCell className="text-end">{hours(item.weekly_min)}</CTableDataCell>
                      <CTableDataCell className="text-end">{hours(item.fortnight_min)}</CTableDataCell>
                    </CTableRow>
                  ))}
                </CTableBody>
              </CTable>
            </div>
          ) : (
            <CCardBody>
              <div className="text-body-secondary">{current ? "Bu sürücüde henüz geçmiş yok." : "Geçmiş için bir sürücü seçin."}</div>
            </CCardBody>
          )}
        </CCard>
      </div>
    </div>
  );
}

function sourceLabel(source: string | null | undefined) {
  if (source === "olculmus") return "Ölçülmüş";
  if (source === "tahmini") return "Tahmini";
  return "Kayıt yok";
}

function activityLabel(value: string) {
  const key = value.trim().toUpperCase();
  return ACTIVITY_LABEL[key] ?? value;
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
  const color = remain <= 30 || ratio >= 90 ? "danger" : ratio >= 70 ? "warning" : "success";
  return (
    <div className="d-flex flex-column gap-1">
      <div className="d-flex justify-content-between gap-2">
        <span className={compact ? "small" : "fw-semibold"}>{label}</span>
        <span className="small text-body-secondary">
          {hours(used)} / {hours(limit)}
        </span>
      </div>
      <CProgress thin={!compact} height={compact ? 6 : 8} value={ratio} color={color} />
      {compact ? null : <div className="small text-body-secondary">Kalan {hours(remain)}</div>}
    </div>
  );
}
