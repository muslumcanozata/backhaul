import { useEffect, useMemo, useState } from "react";
import {
  CAlert,
  CButton,
  CCard,
  CCardBody,
  CCardHeader,
  CFormInput,
  CFormLabel,
  CFormSelect,
  CNav,
  CNavItem,
  CNavLink,
  CTable,
  CTableBody,
  CTableDataCell,
  CTableHead,
  CTableHeaderCell,
  CTableRow,
} from "@coreui/react";
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
    <div className="d-flex flex-column gap-3">
      <div className="d-flex flex-column flex-md-row justify-content-between gap-3 align-items-md-center">
        <div>
          <h1 className="h3 mb-1">Raporlar</h1>
          <div className="text-body-secondary small">Dönemsel özet. Masa anlık kalır; burası geçmişe bakar.</div>
        </div>
        <CButton
          color="secondary"
          variant="outline"
          onClick={() => {
            notice("");
            download(`/reports/${slug}/export?${query}`, token ?? "", `${slug}-${fromDay}-${toDay}.xlsx`).catch((err: Error) =>
              notice(err.message),
            );
          }}
        >
          Excel indir
        </CButton>
      </div>

      <CCard>
        <CCardBody>
          <div className="row g-3">
            <div className="col-12 col-md-auto" style={{ minWidth: 140 }}>
              <CFormLabel>Dönem</CFormLabel>
              <CFormSelect value={preset} onChange={(event) => setPreset(event.target.value)}>
                <option value="1">Bugün</option>
                <option value="7">7 gün</option>
                <option value="30">30 gün</option>
                <option value="ozel">Özel</option>
              </CFormSelect>
            </div>
            <div className="col-12 col-md-auto">
              <CFormLabel>Başlangıç</CFormLabel>
              <CFormInput
                type="date"
                value={fromDay}
                onChange={(event) => {
                  setPreset("ozel");
                  setFromDay(event.target.value);
                }}
              />
            </div>
            <div className="col-12 col-md-auto">
              <CFormLabel>Bitiş</CFormLabel>
              <CFormInput
                type="date"
                value={toDay}
                onChange={(event) => {
                  setPreset("ozel");
                  setToDay(event.target.value);
                }}
              />
            </div>
            {showDirection ? (
              <div className="col-12 col-md-auto" style={{ minWidth: 140 }}>
                <CFormLabel>Yön</CFormLabel>
                <CFormSelect value={direction} onChange={(event) => setDirection(event.target.value)}>
                  <option value="">Hepsi</option>
                  <option value="gidis">Gidiş</option>
                  <option value="donus">Dönüş</option>
                </CFormSelect>
              </div>
            ) : null}
          </div>
        </CCardBody>
      </CCard>

      <CNav variant="tabs" role="tablist" className="flex-nowrap overflow-auto">
        {REPORTS.map((item) => (
          <CNavItem key={item.slug}>
            <CNavLink
              href={`#raporlar/${item.slug}`}
              active={slug === item.slug}
              onClick={(event) => {
                event.preventDefault();
                choose(item.slug);
              }}
              style={{ whiteSpace: "nowrap" }}
            >
              {item.title}
            </CNavLink>
          </CNavItem>
        ))}
      </CNav>

      {loading && !report ? <CAlert color="info">Rapor yükleniyor</CAlert> : null}
      {report ? (
        <>
          <div className="row g-3">
            {report.kpis.map((item) => (
              <div key={item.key} className="col-6 col-lg-3">
                <CCard className="h-100">
                  <CCardBody>
                    <div className="text-uppercase small text-body-secondary">{item.label}</div>
                    <div className="h3 mb-0">{item.value}</div>
                    {item.hint ? <div className="small text-body-secondary">{item.hint}</div> : null}
                  </CCardBody>
                </CCard>
              </div>
            ))}
          </div>

          {report.series.length ? (
            <CCard>
              <CCardHeader>
                <strong>Trend</strong>
                <div className="small text-body-secondary">
                  {report.from_day} – {report.to_day}
                </div>
              </CCardHeader>
              <CCardBody style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={report.series}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis width={40} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#1877F2" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CCardBody>
            </CCard>
          ) : null}

          {report.columns.length ? (
            <CCard>
              <CCardHeader>
                <strong>Detay</strong>
              </CCardHeader>
              <CTable small hover responsive className="mb-0">
                <CTableHead>
                  <CTableRow>
                    {report.columns
                      .filter((column) => column !== "driver_id")
                      .map((column) => (
                        <CTableHeaderCell key={column}>{column}</CTableHeaderCell>
                      ))}
                  </CTableRow>
                </CTableHead>
                <CTableBody>
                  {report.rows.map((row, index) => (
                    <CTableRow
                      key={index}
                      style={slug === "takograf" && row.driver_id ? { cursor: "pointer" } : undefined}
                      onClick={() => {
                        if (slug === "takograf" && row.driver_id) window.location.hash = `takograf/${row.driver_id}`;
                      }}
                    >
                      {report.columns
                        .filter((column) => column !== "driver_id")
                        .map((column) => (
                          <CTableDataCell key={column}>{row[column] ?? ""}</CTableDataCell>
                        ))}
                    </CTableRow>
                  ))}
                  {report.rows.length === 0 ? (
                    <CTableRow>
                      <CTableDataCell colSpan={report.columns.length}>
                        <span className="text-body-secondary">Bu dönemde satır yok.</span>
                      </CTableDataCell>
                    </CTableRow>
                  ) : null}
                </CTableBody>
              </CTable>
            </CCard>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
