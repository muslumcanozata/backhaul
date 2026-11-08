import { FormEvent, useEffect, useState } from "react";
import { CAlert, CButton, CCard, CCardBody, CCardHeader, CFormCheck, CFormInput, CFormLabel, CFormSwitch } from "@coreui/react";
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
  const [arventoEnabled, setArventoEnabled] = useState(false);
  const [seyirEnabled, setSeyirEnabled] = useState(false);
  const [baseIl, setBaseIl] = useState("");
  const [baseIlce, setBaseIlce] = useState("");
  const [tollEnabled, setTollEnabled] = useState(false);
  const [saved, setSaved] = useState("");
  const [username, setUsername] = useState("");
  const [pin1, setPin1] = useState("");
  const [pin2, setPin2] = useState("");
  const [seyirUser, setSeyirUser] = useState("");
  const [seyirPassword, setSeyirPassword] = useState("");
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
    setArventoEnabled(settings.arvento_enabled);
    setSeyirEnabled(settings.seyir_enabled);
    setBaseIl(settings.home_base_il ?? "");
    setBaseIlce(settings.home_base_ilce ?? "");
    setTollEnabled(settings.toll_enabled);
  }, [settings]);

  function toggle(type: string) {
    setTypes((current) => (current.includes(type) ? current.filter((item) => item !== type) : [...current, type]));
  }

  async function approveRoutes() {
    notice("");
    setSaved("");
    try {
      await api("/settings/routes/approve", token, { method: "POST" });
      setSaved("Routes tavanı yükseltildi. Dönüş hesabı yeniden çalıştı.");
      await reload();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Onay yazılamadı");
    }
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
          ...(emptyCost !== "" ? { empty_km_cost: emptyCost } : {}),
          ...(loadedCost !== "" ? { loaded_km_cost: loadedCost } : {}),
          ...(dailyLimit ? { tacho_daily_min: Number(dailyLimit) } : {}),
          ...(warningLead ? { tacho_warning_min: Number(warningLead) } : {}),
          return_approval: approval,
          auto_assign_estimated: estimatedAuto,
          arvento_enabled: arventoEnabled,
          seyir_enabled: seyirEnabled,
          home_base_il: baseIl,
          home_base_ilce: baseIlce,
          toll_enabled: tollEnabled,
        }),
      });
      setSaved(
        emptyCost !== "" && loadedCost !== ""
          ? "Ayarlar kaydedildi. Dönüş hesabı yeni maliyetlerle yeniden çalıştı."
          : "Ayarlar kaydedildi",
      );
      await reload();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Ayar kaydedilemedi");
    }
  }

  return (
    <CCard style={{ maxWidth: 640 }}>
      <CCardHeader>
        <strong>Ayarlar</strong>
        <div className="small text-body-secondary">
          Sinyal tazeliği {settings?.gps_stale_minutes ?? 15} dakika. Dönüş hesabı iki kilometre maliyeti de dolunca çalışır.
        </div>
      </CCardHeader>
      <CCardBody>
        <form className="d-flex flex-column gap-3" onSubmit={save}>
          <div className="d-flex flex-column gap-2">
            {CATALOG.map((type) => (
              <CFormCheck key={type} id={`trailer-${type}`} label={TRAILER_LABEL[type]} checked={types.includes(type)} onChange={() => toggle(type)} />
            ))}
          </div>
          <div>
            <CFormLabel>Boş kilometre maliyeti (TL)</CFormLabel>
            <CFormInput value={emptyCost} onChange={(event) => setEmptyCost(event.target.value)} inputMode="decimal" />
          </div>
          <div>
            <CFormLabel>Dolu kilometre maliyeti (TL)</CFormLabel>
            <CFormInput value={loadedCost} onChange={(event) => setLoadedCost(event.target.value)} inputMode="decimal" />
          </div>
          <div>
            <CFormLabel>Günlük sürüş limiti (dakika)</CFormLabel>
            <CFormInput value={dailyLimit} onChange={(event) => setDailyLimit(event.target.value)} inputMode="numeric" />
          </div>
          <div>
            <CFormLabel>Ön uyarı payı (dakika)</CFormLabel>
            <CFormInput value={warningLead} onChange={(event) => setWarningLead(event.target.value)} inputMode="numeric" />
            <div className="form-text">Yasal paket 540 dakika ve 30 dakika pay. Firma bu değerleri küçültebilir.</div>
          </div>
          <CFormCheck id="return-approval" label="Dönüş atamasında onay iste" checked={approval} onChange={() => setApproval((value) => !value)} />
          <CFormCheck
            id="estimated-auto"
            label="Tahmini takografla otomatik dönüş"
            checked={estimatedAuto}
            onChange={() => setEstimatedAuto((value) => !value)}
          />
          <div>
            <CFormLabel>Üs noktası: il</CFormLabel>
            <CFormInput value={baseIl} onChange={(event) => setBaseIl(event.target.value)} />
            <div className="form-text">Dönüş zinciri buraya dönüşle biter. Boş bırakılırsa son boşaltmada biter.</div>
          </div>
          <div>
            <CFormLabel>Üs noktası: ilçe</CFormLabel>
            <CFormInput value={baseIlce} onChange={(event) => setBaseIlce(event.target.value)} />
            <div className="form-text">Boşsa Merkez kabul edilir.</div>
          </div>
          <CFormSwitch
            id="toll-enabled"
            label="Köprü ve otoyol ücretini Routes API'den hesapla"
            checked={tollEnabled}
            onChange={(event) => setTollEnabled(event.target.checked)}
          />
          <div className="small text-body-secondary">
            Açıkken Routes istekleri daha pahalı SKU'ya geçer. Ücret gelmeyen yük otomatik atanmaz. Binek araç fiyatı döner, ağır vasıta
            farklı olabilir.
          </div>
          <div>
            Bugün {settings?.routes_today ?? 0} / {settings?.routes_allowed ?? 333} Routes isteği · {settings?.routes_cache_hits ?? 0} cache
            isabeti
          </div>
          <div className="small text-body-secondary">
            İlk {settings?.routes_limit ?? 333} istek otomatik (aylık ücretsiz Essentials ≈ 10.000). Üstü için onay gerekir. Canlı konum 5 km
            hücrede tutulur, aynı rota tekrar sorulmaz.
          </div>
          {settings?.routes_needs_approval ? (
            <CAlert color="warning" className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-0">
              <span>
                Günlük Routes tavanı doldu{settings.routes_blocked ? ` · ${settings.routes_blocked} rota bekliyor` : ""}. Onaylayınca plan
                yeniden çalışır.
              </span>
              <CButton color="warning" size="sm" onClick={() => void approveRoutes()}>
                {settings.routes_limit} daha onayla
              </CButton>
            </CAlert>
          ) : null}
          <CButton type="submit" color="primary">
            Kaydet
          </CButton>
          {saved ? <CAlert color="success" className="mb-0">{saved}</CAlert> : null}

          <h2 className="h5 mb-0">Konum sağlayıcıları</h2>
          <div className="text-body-secondary">
            Her sağlayıcı bu firmaya özeldir; ikisi birden açık olabilir. Kapalıyken sırlar saklı kalsa bile istek atılmaz.
          </div>
          <CFormSwitch
            id="arvento-enabled"
            label={settings?.arvento_configured ? "Arvento açık (kayıt var)" : "Arvento açık (kayıt eksik)"}
            checked={arventoEnabled}
            onChange={(event) => setArventoEnabled(event.target.checked)}
          />
          {arventoEnabled ? (
            <div className="d-flex flex-column gap-3">
              <div>
                <CFormLabel>Arvento kullanıcı</CFormLabel>
                <CFormInput value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="off" />
              </div>
              <div>
                <CFormLabel>PIN1</CFormLabel>
                <CFormInput type="password" value={pin1} onChange={(event) => setPin1(event.target.value)} autoComplete="new-password" />
              </div>
              <div>
                <CFormLabel>PIN2</CFormLabel>
                <CFormInput type="password" value={pin2} onChange={(event) => setPin2(event.target.value)} autoComplete="new-password" />
              </div>
              <CButton
                type="button"
                color="secondary"
                variant="outline"
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
              </CButton>
            </div>
          ) : null}

          <CFormSwitch
            id="seyir-enabled"
            label={settings?.seyir_configured ? "Seyir açık (kayıt var)" : "Seyir açık (kayıt eksik)"}
            checked={seyirEnabled}
            onChange={(event) => setSeyirEnabled(event.target.checked)}
          />
          {seyirEnabled ? (
            <div className="d-flex flex-column gap-3">
              <div>
                <CFormLabel>Seyir kullanıcı adı</CFormLabel>
                <CFormInput value={seyirUser} onChange={(event) => setSeyirUser(event.target.value)} autoComplete="off" />
              </div>
              <div>
                <CFormLabel>Seyir şifre</CFormLabel>
                <CFormInput
                  type="password"
                  value={seyirPassword}
                  onChange={(event) => setSeyirPassword(event.target.value)}
                  autoComplete="new-password"
                />
              </div>
              <CButton
                type="button"
                color="secondary"
                variant="outline"
                onClick={async () => {
                  notice("");
                  setSaved("");
                  try {
                    await api("/settings/seyir", token, {
                      method: "PUT",
                      body: JSON.stringify({ username: seyirUser, password: seyirPassword }),
                    });
                    setSeyirUser("");
                    setSeyirPassword("");
                    setSaved("Seyir kaydı yazıldı");
                    await reload();
                  } catch (err) {
                    notice(err instanceof Error ? err.message : "Seyir kaydı yazılamadı");
                  }
                }}
              >
                Seyir kaydet
              </CButton>
            </div>
          ) : null}

          <h2 className="h5 mb-0">{settings?.netgsm_configured ? "Netgsm kaydı var" : "Netgsm kaydı eksik"}</h2>
          <div>
            <CFormLabel>Netgsm kullanıcı kodu</CFormLabel>
            <CFormInput value={usercode} onChange={(event) => setUsercode(event.target.value)} autoComplete="off" />
          </div>
          <div>
            <CFormLabel>Netgsm şifre</CFormLabel>
            <CFormInput type="password" value={smsPassword} onChange={(event) => setSmsPassword(event.target.value)} autoComplete="new-password" />
          </div>
          <div>
            <CFormLabel>Mesaj başlığı</CFormLabel>
            <CFormInput value={smsHeader} onChange={(event) => setSmsHeader(event.target.value)} autoComplete="off" />
          </div>
          <CButton
            type="button"
            color="secondary"
            variant="outline"
            onClick={async () => {
              notice("");
              setSaved("");
              try {
                await api("/settings/netgsm", token, {
                  method: "PUT",
                  body: JSON.stringify({ usercode, password: smsPassword, header: smsHeader }),
                });
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
          </CButton>
        </form>
      </CCardBody>
    </CCard>
  );
}
