import { FormEvent, useState } from "react";
import { CButton, CFormInput, CFormLabel, CFormSelect, COffcanvas, COffcanvasBody, COffcanvasHeader, COffcanvasTitle } from "@coreui/react";
import { api } from "../api";
import { CATALOG, REJECT_LABEL, TRAILER_LABEL } from "../labels";
import { useSession } from "../session";
import type { Load } from "../types";

export function LoadForm({
  direction,
  onSaved,
  onClose,
}: {
  direction: "gidis" | "donus";
  onSaved: () => Promise<void>;
  onClose: () => void;
}) {
  const { token, notice } = useSession();
  const [reference, setReference] = useState("");
  const [pickupIl, setPickupIl] = useState("");
  const [pickupIlce, setPickupIlce] = useState("");
  const [dropIl, setDropIl] = useState("");
  const [dropIlce, setDropIlce] = useState("");
  const [tonnage, setTonnage] = useState("20");
  const [trailer, setTrailer] = useState("tenteli");
  const [readyAt, setReadyAt] = useState("");
  const [deliverStart, setDeliverStart] = useState("");
  const [deliverEnd, setDeliverEnd] = useState("");
  const [freight, setFreight] = useState("");
  const [customer, setCustomer] = useState("");
  const [brokerFirm, setBrokerFirm] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      await api<Load>("/loads", token, {
        method: "POST",
        body: JSON.stringify({
          reference,
          direction,
          pickup_il: pickupIl,
          pickup_ilce: pickupIlce,
          drop_il: dropIl,
          drop_ilce: dropIlce,
          tonnage,
          trailer_type: trailer,
          ready_at: toIso(readyAt),
          deliver_start: toIso(deliverStart),
          deliver_end: toIso(deliverEnd),
          freight_try: direction === "donus" || freight ? freight || null : null,
          customer: customer || null,
          broker_firm: direction === "donus" ? brokerFirm || null : null,
        }),
      });
      await onSaved();
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kayıt yazılamadı";
      notice(REJECT_LABEL[message] ?? message);
    }
  }

  return (
    <COffcanvas placement="end" visible onHide={onClose} style={{ width: "min(100%, 440px)" }}>
      <COffcanvasHeader>
        <COffcanvasTitle>{direction === "gidis" ? "Gidiş ekle" : "Dönüş ekle"}</COffcanvasTitle>
        <CButton color="secondary" variant="ghost" onClick={onClose}>
          Kapat
        </CButton>
      </COffcanvasHeader>
      <COffcanvasBody>
        <form className="d-flex flex-column gap-3" onSubmit={submit}>
          <div>
            <CFormLabel>Referans</CFormLabel>
            <CFormInput value={reference} onChange={(event) => setReference(event.target.value)} required />
          </div>
          <div>
            <CFormLabel>Müşteri</CFormLabel>
            <CFormInput value={customer} onChange={(event) => setCustomer(event.target.value)} />
          </div>
          {direction === "donus" ? (
            <div>
              <CFormLabel>Aracı firma</CFormLabel>
              <CFormInput value={brokerFirm} onChange={(event) => setBrokerFirm(event.target.value)} />
            </div>
          ) : null}
          <div className="row g-2">
            <div className="col-6">
              <CFormLabel>Yükleme ili</CFormLabel>
              <CFormInput value={pickupIl} onChange={(event) => setPickupIl(event.target.value)} required />
            </div>
            <div className="col-6">
              <CFormLabel>İlçe</CFormLabel>
              <CFormInput value={pickupIlce} onChange={(event) => setPickupIlce(event.target.value)} required />
            </div>
          </div>
          <div className="row g-2">
            <div className="col-6">
              <CFormLabel>Boşaltma ili</CFormLabel>
              <CFormInput value={dropIl} onChange={(event) => setDropIl(event.target.value)} required />
            </div>
            <div className="col-6">
              <CFormLabel>İlçe</CFormLabel>
              <CFormInput value={dropIlce} onChange={(event) => setDropIlce(event.target.value)} required />
            </div>
          </div>
          <div className="row g-2">
            <div className="col-6">
              <CFormLabel>Tonaj</CFormLabel>
              <CFormInput value={tonnage} onChange={(event) => setTonnage(event.target.value)} required />
            </div>
            <div className="col-6">
              <CFormLabel>Dorse</CFormLabel>
              <CFormSelect value={trailer} onChange={(event) => setTrailer(event.target.value)} required>
                {CATALOG.map((item) => (
                  <option key={item} value={item}>
                    {TRAILER_LABEL[item]}
                  </option>
                ))}
              </CFormSelect>
            </div>
          </div>
          <div>
            <CFormLabel>Hazır</CFormLabel>
            <CFormInput type="datetime-local" value={readyAt} onChange={(event) => setReadyAt(event.target.value)} required />
          </div>
          <div>
            <CFormLabel>Teslim başlangıç</CFormLabel>
            <CFormInput type="datetime-local" value={deliverStart} onChange={(event) => setDeliverStart(event.target.value)} required />
          </div>
          <div>
            <CFormLabel>Teslim bitiş</CFormLabel>
            <CFormInput type="datetime-local" value={deliverEnd} onChange={(event) => setDeliverEnd(event.target.value)} required />
          </div>
          {direction === "donus" || freight ? (
            <div>
              <CFormLabel>Navlun (TL)</CFormLabel>
              <CFormInput value={freight} onChange={(event) => setFreight(event.target.value)} required={direction === "donus"} />
            </div>
          ) : (
            <div>
              <CFormLabel>Navlun (opsiyonel)</CFormLabel>
              <CFormInput value={freight} onChange={(event) => setFreight(event.target.value)} />
            </div>
          )}
          <CButton type="submit" color="primary" size="lg">
            Kaydet
          </CButton>
        </form>
      </COffcanvasBody>
    </COffcanvas>
  );
}

function toIso(value: string): string {
  return new Date(value).toISOString();
}
