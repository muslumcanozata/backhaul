import { FormEvent, useEffect, useMemo, useState } from "react";
import { CBadge, CButton, CCard, CCardBody, CCardHeader, CFormInput, CFormLabel, CFormSelect } from "@coreui/react";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { STATUS_LABEL, TRAILER_LABEL, availability, canWriteMaster, driverName } from "../labels";
import { LoadingNote } from "../loading";
import { useSession } from "../session";
import { VehicleFile } from "./VehicleFile";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isVehicleId(value: string) {
  return UUID_RE.test(value);
}

export function Araclar({ initialFilter = "" }: { initialFilter?: string }) {
  const { token, user, notice } = useSession();
  const { vehicles, drivers, settings, loading, reload } = useFleet();
  const [selected, setSelected] = useState(() => (isVehicleId(initialFilter) ? initialFilter : ""));
  const [filter, setFilter] = useState(() => (isVehicleId(initialFilter) ? "" : initialFilter));
  const [plate, setPlate] = useState("");
  const [capacity, setCapacity] = useState("24");
  const [trailer, setTrailer] = useState(settings?.enabled_trailer_types[0] ?? "tenteli");
  const vehicle = vehicles.find((item) => item.id === selected);
  const types = settings?.enabled_trailer_types ?? ["tenteli"];

  useEffect(() => {
    if (isVehicleId(initialFilter)) {
      setSelected(initialFilter);
      setFilter("");
    } else {
      setFilter(initialFilter);
      if (initialFilter) setSelected("");
    }
  }, [initialFilter]);

  const groups = useMemo(() => {
    const map = new Map<string, number>();
    vehicles.forEach((item) => {
      const label = availability(item, settings);
      map.set(label, (map.get(label) ?? 0) + 1);
    });
    return map;
  }, [vehicles, settings]);

  const shown = filter ? vehicles.filter((item) => availability(item, settings) === filter) : vehicles;

  function chooseFilter(next: string) {
    setFilter(next);
    setSelected("");
    window.location.hash = next ? `araclar/${encodeURIComponent(next)}` : "araclar";
  }

  function openVehicle(id: string) {
    setSelected(id);
    window.location.hash = `araclar/${id}`;
  }

  function closeVehicle() {
    setSelected("");
    window.location.hash = filter ? `araclar/${encodeURIComponent(filter)}` : "araclar";
  }

  useEffect(() => {
    if (!types.includes(trailer)) setTrailer(types[0]);
  }, [types, trailer]);

  async function create(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      const created = await api<{ id: string }>("/vehicles", token, {
        method: "POST",
        body: JSON.stringify({ plate, capacity_tons: capacity, trailer_type: trailer }),
      });
      setPlate("");
      await reload();
      openVehicle(created.id);
    } catch (err) {
      notice(err instanceof Error ? err.message : "Araç eklenemedi");
    }
  }

  if (selected && vehicle) {
    return (
      <div className="d-flex flex-column gap-3">
        <VehicleFile vehicle={vehicle} drivers={drivers} settings={settings} onChanged={reload} onClose={closeVehicle} />
      </div>
    );
  }

  if (selected && !vehicle) {
    return (
      <CCard>
        <CCardBody className="d-flex flex-column gap-3">
          <div className="text-body-secondary">Araç bulunamadı.</div>
          <CButton color="secondary" variant="outline" onClick={closeVehicle}>
            Listeye dön
          </CButton>
        </CCardBody>
      </CCard>
    );
  }

  return (
    <div className="row g-3">
      <div className={canWriteMaster(user.role) ? "col-12 col-lg-8" : "col-12"}>
        <CCard>
          <CCardHeader>
            <strong>Araçlar</strong>
            <div className="small text-body-secondary">Özlük dosyası için bir araç seçin.</div>
          </CCardHeader>
          <div className="d-flex flex-wrap gap-2 px-3 pb-2">
            <CBadge
              as="button"
              type="button"
              color={filter ? "secondary" : "primary"}
              className="border-0"
              onClick={() => chooseFilter("")}
            >
              Tümü {vehicles.length}
            </CBadge>
            {[...groups.entries()].map(([label, count]) => (
              <CBadge
                key={label}
                as="button"
                type="button"
                color={filter === label ? "primary" : "secondary"}
                className="border-0"
                onClick={() => chooseFilter(label)}
              >
                {label} {count}
              </CBadge>
            ))}
            {filter && !groups.has(filter) ? (
              <CBadge as="button" type="button" color="primary" className="border-0" onClick={() => chooseFilter("")}>
                {filter} 0
              </CBadge>
            ) : null}
          </div>
          <div className="list-group list-group-flush">
            {shown.map((item) => (
              <button key={item.id} type="button" className="list-group-item list-group-item-action text-start" onClick={() => openVehicle(item.id)}>
                <div className="fw-semibold">{item.plate}</div>
                <div className="small text-body-secondary">
                  {TRAILER_LABEL[item.trailer_type] ?? item.trailer_type} · {item.capacity_tons} ton · {STATUS_LABEL[item.status] ?? item.status} ·{" "}
                  {driverName(drivers, item.driver_id)} · {availability(item, settings)}
                </div>
              </button>
            ))}
          </div>
          {loading ? (
            <LoadingNote label="Araçlar yükleniyor…" />
          ) : shown.length === 0 ? (
            <CCardBody>
              <div className="text-body-secondary">{vehicles.length === 0 ? "Kayıtlı araç yok." : "Bu durumda araç yok."}</div>
            </CCardBody>
          ) : null}
        </CCard>
      </div>
      {canWriteMaster(user.role) ? (
        <div className="col-12 col-lg-4">
          <CCard>
            <CCardHeader>
              <strong>Araç ekle</strong>
            </CCardHeader>
            <CCardBody>
              <form className="d-flex flex-column gap-3" onSubmit={create}>
                <div>
                  <CFormLabel>Plaka</CFormLabel>
                  <CFormInput value={plate} onChange={(event) => setPlate(event.target.value)} required />
                </div>
                <div>
                  <CFormLabel>Kapasite (ton)</CFormLabel>
                  <CFormInput value={capacity} onChange={(event) => setCapacity(event.target.value)} required />
                </div>
                <div>
                  <CFormLabel>Kasa</CFormLabel>
                  <CFormSelect value={types.includes(trailer) ? trailer : types[0]} onChange={(event) => setTrailer(event.target.value)}>
                    {types.map((type) => (
                      <option key={type} value={type}>
                        {TRAILER_LABEL[type] ?? type}
                      </option>
                    ))}
                  </CFormSelect>
                </div>
                <CButton type="submit" color="primary">
                  Ekle
                </CButton>
              </form>
            </CCardBody>
          </CCard>
        </div>
      ) : null}
    </div>
  );
}
