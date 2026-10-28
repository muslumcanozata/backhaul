import { FormEvent, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { CATALOG, TRAILER_LABEL } from "../labels";
import { useSession } from "../session";

export function Ayarlar() {
  const { token, notice } = useSession();
  const { settings, reload } = useFleet();
  const [types, setTypes] = useState<string[]>(["tenteli"]);
  const [emptyCost, setEmptyCost] = useState("");
  const [loadedCost, setLoadedCost] = useState("");
  const [dailyLimit, setDailyLimit] = useState("540");
  const [warningLead, setWarningLead] = useState("30");
  const [approval, setApproval] = useState(false);
  const [estimatedAuto, setEstimatedAuto] = useState(false);
  const [saved, setSaved] = useState("");
  const [username, setUsername] = useState("");
  const [pin1, setPin1] = useState("");
  const [pin2, setPin2] = useState("");
  const [usercode, setUsercode] = useState("");
  const [smsPassword, setSmsPassword] = useState("");
  const [smsHeader, setSmsHeader] = useState("");

  useEffect(() => {
    if (!settings) return;
    setTypes(settings.enabled_trailer_types);
    setEmptyCost(settings.empty_km_cost ?? "");
    setLoadedCost(settings.loaded_km_cost ?? "");
    setDailyLimit(String(settings.tacho_daily_min ?? 540));
    setWarningLead(String(settings.tacho_warning_min ?? 30));
    setApproval(settings.return_approval);
    setEstimatedAuto(settings.auto_assign_estimated);
  }, [settings]);

  function toggle(type: string) {
    setTypes((current) => (current.includes(type) ? current.filter((item) => item !== type) : [...current, type]));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    notice("");
    setSaved("");
    try {
      await api("/settings", token, {
        method: "PATCH",
        body: JSON.stringify({
          enabled_trailer_types: types,
          ...(emptyCost ? { empty_km_cost: emptyCost } : {}),
          ...(loadedCost ? { loaded_km_cost: loadedCost } : {}),
          ...(dailyLimit ? { tacho_daily_min: Number(dailyLimit) } : {}),
          ...(warningLead ? { tacho_warning_min: Number(warningLead) } : {}),
          return_approval: approval,
          auto_assign_estimated: estimatedAuto,
        }),
      });
      setSaved("Ayarlar kaydedildi");
      await reload();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Ayar kaydedilemedi");
    }
  }

  return (
    <Card component="form" onSubmit={save} sx={{ maxWidth: 640 }}>
      <CardHeader
        title="Ayarlar"
        subheader={`Sinyal tazeliği ${settings?.gps_stale_minutes ?? 15} dakika. Dönüş hesabı iki kilometre maliyeti de dolunca çalışır.`}
      />
      <CardContent>
        <Stack spacing={2}>
          <Stack>
            {CATALOG.map((type) => (
              <FormControlLabel
                key={type}
                control={<Checkbox checked={types.includes(type)} onChange={() => toggle(type)} />}
                label={TRAILER_LABEL[type]}
              />
            ))}
          </Stack>
          <TextField label="Boş kilometre maliyeti (TL)" value={emptyCost} onChange={(event) => setEmptyCost(event.target.value)} slotProps={{ htmlInput: { inputMode: "decimal" } }} />
          <TextField label="Dolu kilometre maliyeti (TL)" value={loadedCost} onChange={(event) => setLoadedCost(event.target.value)} slotProps={{ htmlInput: { inputMode: "decimal" } }} />
          <TextField label="Günlük sürüş limiti (dakika)" value={dailyLimit} onChange={(event) => setDailyLimit(event.target.value)} slotProps={{ htmlInput: { inputMode: "numeric" } }} />
          <TextField label="Ön uyarı payı (dakika)" value={warningLead} onChange={(event) => setWarningLead(event.target.value)} helperText="Yasal paket 540 dakika ve 30 dakika pay. Firma bu değerleri küçültebilir." slotProps={{ htmlInput: { inputMode: "numeric" } }} />
          <FormControlLabel control={<Checkbox checked={approval} onChange={() => setApproval((value) => !value)} />} label="Dönüş atamasında onay iste" />
          <FormControlLabel control={<Checkbox checked={estimatedAuto} onChange={() => setEstimatedAuto((value) => !value)} />} label="Tahmini takografla otomatik dönüş" />
          <Button type="submit" variant="contained">
            Kaydet
          </Button>
          {saved ? <Alert severity="success">{saved}</Alert> : null}
          <Typography variant="h6">{settings?.arvento_configured ? "Arvento kaydı var" : "Arvento kaydı eksik"}</Typography>
          <TextField label="Arvento kullanıcı" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="off" />
          <TextField label="PIN1" type="password" value={pin1} onChange={(event) => setPin1(event.target.value)} autoComplete="new-password" />
          <TextField label="PIN2" type="password" value={pin2} onChange={(event) => setPin2(event.target.value)} autoComplete="new-password" />
          <Button
            type="button"
            variant="outlined"
            onClick={async () => {
              notice("");
              setSaved("");
              try {
                await api("/settings/arvento", token, { method: "PUT", body: JSON.stringify({ username, pin1, pin2 }) });
                setUsername("");
                setPin1("");
                setPin2("");
                setSaved("Arvento kaydı yazıldı");
                await reload();
              } catch (err) {
                notice(err instanceof Error ? err.message : "Arvento kaydı yazılamadı");
              }
            }}
          >
            Arvento kaydet
          </Button>
          <Typography variant="h6">{settings?.netgsm_configured ? "Netgsm kaydı var" : "Netgsm kaydı eksik"}</Typography>
          <TextField label="Netgsm kullanıcı kodu" value={usercode} onChange={(event) => setUsercode(event.target.value)} autoComplete="off" />
          <TextField label="Netgsm şifre" type="password" value={smsPassword} onChange={(event) => setSmsPassword(event.target.value)} autoComplete="new-password" />
          <TextField label="Mesaj başlığı" value={smsHeader} onChange={(event) => setSmsHeader(event.target.value)} autoComplete="off" />
          <Button
            type="button"
            variant="outlined"
            onClick={async () => {
              notice("");
              setSaved("");
              try {
                await api("/settings/netgsm", token, { method: "PUT", body: JSON.stringify({ usercode, password: smsPassword, header: smsHeader }) });
                setUsercode("");
                setSmsPassword("");
                setSmsHeader("");
                setSaved("Netgsm kaydı yazıldı");
                await reload();
              } catch (err) {
                notice(err instanceof Error ? err.message : "Netgsm kaydı yazılamadı");
              }
            }}
          >
            Netgsm kaydet
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
