# Seyir Mobil entegrasyon planı

Sürüm: 0.1  
Tarih: 31 Ekim 2026  
Kaynak sözleşme: LocationService Web Servisi Metotları ve Kullanımları TR V2.5 (Seyir Mobil)

Bu belge Seyir canlı bağlantısını ve telematics sağlayıcı switch’lerini tanımlar. İş kuralları [iş kurallarında](is-kurallari.md), adaptör çerçevesi [mimari planda](mimari-ve-teslimat.md), ekranlar [arayüz planındadır](arayuz.md).

## 1. Amaç

- Konum/takograf kaynağı **tenant bazlı** seçilir. Her firmanın kendi switch’leri vardır.
- **Arvento** ve **Seyir** birbirinden bağımsız açılıp kapanır; **ikisi birden açık olabilir**.
- Kapalı sağlayıcıya (sırlar dolu olsa bile) istek atılmaz. Kod silinmez.

## 2. Sağlayıcı switch’leri (tenant)

Alanlar `tenant_settings` üzerindedir; firma A Seyir açık / Arvento kapalı iken firma B ikisini de açık tutabilir.

| Alan | Tip | Anlam |
| --- | --- | --- |
| `arvento_enabled` | bool | Kapalıysa bu tenant için Arvento pull/canlı çağrı yok |
| `seyir_enabled` | bool | Kapalıysa bu tenant için Seyir pull/canlı çağrı yok |

Kurallar:

1. Switch’ler **bağımsızdır**. İkisi açık, ikisi kapalı veya biri açık olabilir.
2. Sırlar saklı kalsa bile kapalı sağlayıcıya istek gitmez.
3. Yeni firma varsayılanı: ikisi de kapalı.
4. `PATCH /settings` yalnızca ilgili tenant’ın switch alanlarını yazar.

İkisi birden açıkken davranış:

- `telematics/pull` **her iki** açık ve yapılandırılmış sağlayıcıyı sırayla çeker.
- Aynı araca iki kaynaktan konum gelirse **daha yeni `recorded_at`** kazanır; eşitlikte son yazılan korunur.
- Takograf: Seyir ölçülmüş paket (`olculmus`) varsa o yazılır; yoksa Arvento yolu (ölçülmüş veya tahmini) olduğu gibi kalır. İki ölçülmüş çakışırsa yine daha yeni sinyal zamanı esas alınır.
- Eşleşmeyen plakalar sağlayıcı bazında `unmatched` listesinde toplanır.

`SettingsOut` alanları:

- `arvento_enabled`, `seyir_enabled`
- `arvento_configured`, `seyir_configured`
- `enabled_telematics`: `("arvento" | "seyir")[]` — açık olanlar; ikisi de kapalıysa `[]`

## 3. Ortak çekim yüzeyi

Planlama ve takip, sağlayıcı bilmez. Adaptör çıktısı ortak pakete düşer; `VehiclePosition` ve `TachoState` güncellenir. Pull her zaman **oturumdaki tenant** için çalışır.

| Uç | Davranış |
| --- | --- |
| `POST /integrations/telematics/pull` | Tenant’ta açık + yapılandırılmış tüm sağlayıcıları çeker. Hiçbiri yoksa 409 |
| `POST /integrations/arvento/pull` | Yalnız bu tenant’ta `arvento_enabled` iken; aksi halde 409 |
| `POST /integrations/seyir/pull` | Yalnız bu tenant’ta `seyir_enabled` iken; aksi halde 409 |
| `PUT /settings/arvento` | Arvento sırları (tenant secret); pull switch’e bağlı |
| `PUT /settings/seyir` | Seyir `user_name` + `password` (tenant secret) |

Özet ekranındaki “Konumları çek” `telematics/pull` çağırır. Buton, tenant’ta en az bir açık ve yapılandırılmış sağlayıcı yoksa pasiftir.

## 4. Seyir adaptörü (MVP)

### 4.1 Bağlantı

| Öğe | Değer |
| --- | --- |
| Adres | `https://ws.seyirmobil.com/LocationService.asmx` |
| Kimlik | `user_name`, `password` (yönetici seviyesinde web servis kullanıcısı) |
| Ad alanı | `http://tempuri.org/` |
| İstemci | Yalnızca kullanılan metotlar; WSDL’den tam istemci üretilmez |

Sırlar: paylaşılan podda `TenantSecret` içinde şifreli; ayrı podda ortam değişkeni (`SEYIR_USERNAME`, `SEYIR_PASSWORD`). Shared pod, müşteri sırrı ortamda doluysa açılmaz (mevcut Netgsm/Arvento kuralı).

### 4.2 Kullanılan metotlar

Dokümandaki 39 metottan yalnızca ikisi ilk sürüme girer.

| Metot | Amaç | Önerilen aralık |
| --- | --- | --- |
| `GetActualLocations` | Filo son konum paketi | ~60 sn |
| `GetDriversLastTaviState` | Sürücü takograf özeti | ~5 dk |

Sonraki faz: raporlar, bölge, navigasyon mesajı, Pvt_* sürücü CRUD, paylaşımlı cihaz, sıcaklık.

### 4.3 Konum eşlemesi (`GetActualLocations`)

| Seyir alanı | Backhaul |
| --- | --- |
| `vehicle` | Plaka; boşluksuz büyük harf normalize; önce plaka, yoksa cihaz |
| `device_id` | `Vehicle.device_id` yedek eşleşme |
| `latitude`, `longitude` | Konum |
| `speed` | `speed_kmh` |
| `angle` | `course` |
| `data_time` | `recorded_at` (ofsetli ISO → UTC) |
| `total_km` | `odometer_km` (`VehiclePosition`) |
| `driver_key` | `Driver.card_id` eşlemesi; değişince `vehicle_driver_stints` |
| `driver` | Ad ile tekil eşleşme yedek |
| `fuel_level` / `tank_level` / `fuel` (opsiyonel) | `vehicle_fuel_samples`; ≥8 puan ani yükselişte `vehicle_fuel_fills` `source=seyir` |
| `is_vehicle_running` | Kontak (saklanırsa; plan kuralı şimdilik konum tazeliğine bakar) |
| `is_gps_active` | 0 olsa da lat/lng yazılır (doküman: son aktif konum); tazelik `data_time` ile |

Depo alanı pakette yoksa yakıt örneği yazılmaz; bakım ve lastik yalnız elle girilir. Ayrı SOAP yakıt/lastik raporu bu sürümde yok.

Eşleşmeyen plaka/cihaz `unmatched` listesine düşer; sessizce atılmaz.

### 4.4 Takograf eşlemesi (`GetDriversLastTaviState`)

Seyir alanları çoğunlukla **kalan / kullanılmamış** dilindedir. Ürün modeli **kullanılmış dakika** tutar. Dönüşüm clamp ≥ 0 ile yapılır. Canlıya çıkmadan önce örnek DataSet fixture’ı ile birim (dk) doğrulanır.

| Seyir | Backhaul (yaklaşık) |
| --- | --- |
| `not_used_daily_drive` | `daily_min = tacho_daily_min − değer` |
| `not_used_weekly_drive` | `weekly_min = tacho_weekly_min − değer` |
| `total_double_weekly_drive` | `fortnight_min` (doğrudan kullanılmış iki haftalık) |
| `remaining_drive_period` / `not_used_drive_period` | `continuous_min` (fixture ile kesin alan seçilir) |
| `remaining_long_drive_count` | `extensions_used = tacho_extensions − değer` |
| — | `source = olculmus` |

Eşleşme sırası: `driver_code` → `card_id`; yoksa `current_plate` → araç → `driver_id`.

`alert_type` Seyir uyarı kodları ürün uyarı listesine bire bir kopyalanmaz. Ürün kendi `TR-AETR-2026` eşikleriyle `sync_alerts` üretir.

## 5. Arvento (tenant switch)

- `app/arvento.py` ve mevcut test fixture’ları kalır.
- Bu tenant’ta `arvento_enabled=false` iken Arvento pull 409; periyodik işleyici (varsa) o tenant için atlar.
- Ayarlar’da Arvento formu switch kapalıyken salt okunur veya gizli; sır yazımı isteğe bağlı açık kalabilir.
- Yoğun kullanım örneği: ilgili tenant’ta `seyir_enabled=true`, `arvento_enabled=false`. Başka tenant Arvento’yu açık tutabilir.

## 6. Veri modeli ve migrasyon

`tenant_settings`:

- `arvento_enabled BOOLEAN DEFAULT 0`
- `seyir_enabled BOOLEAN DEFAULT 0`

`tenant_secrets`:

- `seyir_username`, `seyir_password` (şifreli, nullable)

Dedicated env (örnek adlar, değer yok):

- `SEYIR_USERNAME`, `SEYIR_PASSWORD`

Mevcut Arvento sır kolonları değişmez.

## 7. Arayüz

**Ayarlar — Telematics kartı (tenant)**

1. Arvento switch + (açıkken) kullanıcı / PIN1 / PIN2 + kaydet.
2. Seyir switch + (açıkken) kullanıcı adı / şifre + kaydet.
3. Switch’ler bağımsız; ikisi birden açılabilir. Bilgi metni: “Her sağlayıcı bu firmaya özeldir; ikisi birden açık olabilir.”
4. Yapılandırma durumu rozeti: kayıt var / eksik / kapalı.

**Özet**

- “Konumları çek” → `telematics/pull` (açık tüm sağlayıcılar).
- Tenant’ta açık ve yapılandırılmış sağlayıcı yoksa buton disabled + kısa açıklama.

## 8. Uygulama sırası

| Adım | Çıktı |
| --- | --- |
| 1 | Tenant switch alanları (bağımsız), settings API/UI, Arvento pull kilidi |
| 2 | `seyir.py`: credentials, `GetActualLocations`, `telematics/pull` (çoklu sağlayıcı), konum fixture testi |
| 3 | `GetDriversLastTaviState` → ölçülmüş takograf, eşleme + fixture |
| 4 | Çakışma kuralı (daha yeni `recorded_at`), özet butonu, docs, migrasyon |

## 9. Test

- Offline SOAP/DataSet fixture ile Seyir konum parse (canlı ağ yok).
- Plaka normalize: `41 AZ 473` ↔ `41AZ473`.
- `data_time` +03:00 → UTC.
- Switch kapalıyken ilgili sağlayıcı pull 409.
- İki switch birden açıkken `telematics/pull` ikisini de çağırır; aynı araçta daha yeni `recorded_at` kalır.
- Tenant izolasyonu: A’nın Seyir ayarı B’nin Arvento pull’unu etkilemez.
- Takograf: kalan → kullanılmış dönüşümü; `source=olculmus`.
- Dedicated env sırları shared pod’da boot’u bozar (mevcut kurala ek).

## 10. Bilinçli dışarıda

- Seyir rapor / performans / bölge / sıcaklık / navigasyon metotları.
- Seyir `alert_type` kodlarının ürün uyarı tablosuna bire bir aktarımı.
- Arvento kodunun silinmesi.
- Sağlayıcılar arası otomatik failover (biri hata verince diğerine düşme) — ilk sürümde her açık sağlayıcı bağımsız denenir, hata kendi sonucuna yazılır.

## 11. Kabul

1. Firma yöneticisi kendi tenant’ında Seyir ve Arvento switch’lerini bağımsız açıp kapatabiliyor; ikisi birden açık kalabiliyor.
2. Seyir sırları yazılı ve switch açıkken pull, plakası eşleşen araçlara konum yazıyor.
3. Takograf metodu yetkili ve fixture doğrulanmışsa sayaç `olculmus` oluyor.
4. Bir sağlayıcı kapalıyken o sağlayıcıya istek gitmiyor; diğeri açıksa çalışmaya devam ediyor.
5. İki tenant’ın switch/sırları birbirine karışmıyor.
6. Planlama / dönüş hesabı sağlayıcı adından bağımsız çalışmaya devam ediyor.
