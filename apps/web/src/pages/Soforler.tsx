import { FormEvent, useState } from "react";
import { CButton, CCard, CCardBody, CCardHeader, CFormInput, CFormLabel } from "@coreui/react";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { canWriteMaster } from "../labels";
import { LoadingNote } from "../loading";
import { useSession } from "../session";

export function Soforler() {
  const { token, user, notice } = useSession();
  const { vehicles, drivers, loading, reload } = useFleet();
  const [selected, setSelected] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [card, setCard] = useState("");
  const driver = drivers.find((item) => item.id === selected);
  const vehicle = vehicles.find((item) => item.driver_id === driver?.id);

  async function create(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      const created = await api<{ id: string }>("/drivers", token, {
        method: "POST",
        body: JSON.stringify({ name, phone, card_id: card || null }),
      });
      setName("");
      setPhone("");
      setCard("");
      setSelected(created.id);
      await reload();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Şoför eklenemedi");
    }
  }

  return (
    <div className="row g-3">
      <div className="col-12 col-lg-6 d-flex flex-column gap-3">
        <CCard>
          <CCardHeader>
            <strong>Şoförler</strong>
          </CCardHeader>
          <div className="list-group list-group-flush">
            {drivers.map((item) => {
              const bound = vehicles.find((row) => row.driver_id === item.id);
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`list-group-item list-group-item-action text-start ${item.id === selected ? "active" : ""}`}
                  onClick={() => setSelected(item.id)}
                >
                  <div className="fw-semibold">{item.name}</div>
                  <div className={`small ${item.id === selected ? "text-white-50" : "text-body-secondary"}`}>
                    {item.phone} · {bound ? bound.plate : "Araç yok"}
                  </div>
                </button>
              );
            })}
          </div>
          {loading ? (
            <LoadingNote label="Şoförler yükleniyor…" />
          ) : drivers.length === 0 ? (
            <CCardBody>
              <div className="text-body-secondary">Kayıtlı şoför yok.</div>
            </CCardBody>
          ) : null}
        </CCard>
        {canWriteMaster(user.role) ? (
          <CCard>
            <CCardHeader>
              <strong>Şoför ekle</strong>
            </CCardHeader>
            <CCardBody>
              <form className="d-flex flex-column gap-3" onSubmit={create}>
                <div>
                  <CFormLabel>Ad</CFormLabel>
                  <CFormInput value={name} onChange={(event) => setName(event.target.value)} required />
                </div>
                <div>
                  <CFormLabel>Telefon</CFormLabel>
                  <CFormInput value={phone} onChange={(event) => setPhone(event.target.value)} required />
                </div>
                <div>
                  <CFormLabel>Kart</CFormLabel>
                  <CFormInput value={card} onChange={(event) => setCard(event.target.value)} />
                </div>
                <CButton type="submit" color="primary">
                  Ekle
                </CButton>
              </form>
            </CCardBody>
          </CCard>
        ) : null}
      </div>
      <div className="col-12 col-lg-6">
        <CCard>
          <CCardHeader>
            <strong>{driver?.name ?? "Şoför dosyası"}</strong>
            <div className="small text-body-secondary">
              {driver ? "SMS geçmişi rota bildirimleri açılınca bu dosyada durur." : "Dosya için bir şoför seçin."}
            </div>
          </CCardHeader>
          {driver ? (
            <CCardBody className="d-flex flex-column gap-3">
              <div>
                <div className="small text-body-secondary">Telefon</div>
                <div>{driver.phone}</div>
              </div>
              <div>
                <div className="small text-body-secondary">Kart</div>
                <div>{driver.card_id ?? "Yok"}</div>
              </div>
              <div>
                <div className="small text-body-secondary">Araç</div>
                <div>{vehicle ? vehicle.plate : "Bağlı araç yok"}</div>
              </div>
            </CCardBody>
          ) : null}
        </CCard>
      </div>
    </div>
  );
}
