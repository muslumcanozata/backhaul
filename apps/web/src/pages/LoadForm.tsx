import { FormEvent, useState } from "react";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
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
    <Drawer anchor="right" open onClose={onClose} slotProps={{ paper: { sx: { width: { xs: "100%", sm: 440 }, p: 3 } } }}>
      <Stack component="form" spacing={2} onSubmit={submit}>
        <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between" }}>
          <Typography variant="h5">{direction === "gidis" ? "Gidiş ekle" : "Dönüş ekle"}</Typography>
          <Button onClick={onClose}>Kapat</Button>
        </Stack>
        <TextField label="Referans" value={reference} onChange={(event) => setReference(event.target.value)} required />
        <TextField label="Müşteri" value={customer} onChange={(event) => setCustomer(event.target.value)} />
        {direction === "donus" ? (
          <TextField label="Aracı firma" value={brokerFirm} onChange={(event) => setBrokerFirm(event.target.value)} />
        ) : null}
        <Stack direction="row" spacing={1}>
          <TextField label="Yükleme ili" value={pickupIl} onChange={(event) => setPickupIl(event.target.value)} required fullWidth />
          <TextField label="İlçe" value={pickupIlce} onChange={(event) => setPickupIlce(event.target.value)} required fullWidth />
        </Stack>
        <Stack direction="row" spacing={1}>
          <TextField label="Boşaltma ili" value={dropIl} onChange={(event) => setDropIl(event.target.value)} required fullWidth />
          <TextField label="İlçe" value={dropIlce} onChange={(event) => setDropIlce(event.target.value)} required fullWidth />
        </Stack>
        <Stack direction="row" spacing={1}>
          <TextField label="Tonaj" value={tonnage} onChange={(event) => setTonnage(event.target.value)} required fullWidth />
          <TextField select label="Dorse" value={trailer} onChange={(event) => setTrailer(event.target.value)} required fullWidth>
            {CATALOG.map((item) => (
              <MenuItem key={item} value={item}>
                {TRAILER_LABEL[item]}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
        <TextField label="Hazır" type="datetime-local" value={readyAt} onChange={(event) => setReadyAt(event.target.value)} required slotProps={{ inputLabel: { shrink: true } }} />
        <TextField label="Teslim başlangıç" type="datetime-local" value={deliverStart} onChange={(event) => setDeliverStart(event.target.value)} required slotProps={{ inputLabel: { shrink: true } }} />
        <TextField label="Teslim bitiş" type="datetime-local" value={deliverEnd} onChange={(event) => setDeliverEnd(event.target.value)} required slotProps={{ inputLabel: { shrink: true } }} />
        {direction === "donus" || freight ? (
          <TextField label="Navlun (TL)" value={freight} onChange={(event) => setFreight(event.target.value)} required={direction === "donus"} />
        ) : (
          <TextField label="Navlun (opsiyonel)" value={freight} onChange={(event) => setFreight(event.target.value)} />
        )}
        <Button type="submit" variant="contained" size="large">
          Kaydet
        </Button>
      </Stack>
    </Drawer>
  );
}

function toIso(value: string): string {
  return new Date(value).toISOString();
}
