# UI iş akışları

Sürüm: 0.1  
Tarih: 28 Ekim 2026

Bu belge, Minimal kabuktaki ekranlara göre operasyon senaryolarını çizer. Sayfa ve rol sınırı [arayüz planındadır](arayuz.md). Kurallar [iş kurallarındadır](is-kurallari.md).

Diyagramlar Mermaid UML’dir (use case, activity, sequence, state).

## 1. Aktörler ve ekranlar

| Aktör | Giriş sonrası kabuk | Ana menü |
| --- | --- | --- |
| Platform yöneticisi | Sicil | Firmalar |
| Firma yöneticisi | Sefer | Özet, Gidiş, Dönüş, Takip, Araçlar, Şoförler, Ayarlar, Kullanıcılar (+ üst çubuk bildirimler) |
| Operasyoncu | Sefer | Özet, Gidiş, Dönüş, Takip, Araçlar, Şoförler (+ üst çubuk bildirimler) |
| İzleyici | Sefer | Aynı menü; yazma düğmeleri yok |

```mermaid
flowchart LR
  subgraph Auth["Giriş"]
    L[Giriş formu]
  end
  subgraph Platform["Sicil kabuğu"]
    F[Firmalar]
  end
  subgraph Firma["Sefer kabuğu"]
    O[Özet]
    G[Gidiş kuyruğu]
    D[Dönüş havuzu]
    T[Takip]
    A[Araçlar]
    S[Şoförler]
    Y[Ayarlar]
    K[Kullanıcılar]
  end
  L -->|platform_admin| F
  L -->|tenant_admin| O
  L -->|dispatcher| O
  L -->|viewer| O
  O --> G
  O --> D
  O --> T
  tenant_admin -.-> Y
  tenant_admin -.-> K
```

```mermaid
usecaseDiagram
  actor Platform as "Platform yöneticisi"
  actor Admin as "Firma yöneticisi"
  actor Ops as "Operasyoncu"
  actor View as "İzleyici"

  package Sicil {
    usecase UC1 as "Firma aç / listele"
    usecase UC2 as "Firma kullanıcısı ekle"
  }

  package Sefer {
    usecase UC3 as "Özet ve grafikleri oku"
    usecase UC4 as "Gidiş kuyruğunu yönet"
    usecase UC5 as "Gidiş ata"
    usecase UC6 as "Dönüş havuzunu yönet"
    usecase UC7 as "Dönüş hesapla / onayla"
    usecase UC8 as "Canlı takip izle"
    usecase UC9 as "Bildirimleri oku / görüldü"
    usecase UC10 as "Araç ve şoför sicili"
    usecase UC11 as "Arvento çek / Netgsm ayarla"
  }

  Platform --> UC1
  Platform --> UC2
  Admin --> UC3
  Admin --> UC4
  Admin --> UC5
  Admin --> UC6
  Admin --> UC7
  Admin --> UC8
  Admin --> UC9
  Admin --> UC10
  Admin --> UC11
  Ops --> UC3
  Ops --> UC4
  Ops --> UC5
  Ops --> UC6
  Ops --> UC7
  Ops --> UC8
  Ops --> UC9
  Ops --> UC10
  View --> UC3
  View --> UC4
  View --> UC6
  View --> UC8
  View --> UC9
  View --> UC10
```

## 2. Günlük operasyon (özetten kuyruğa)

Operasyoncu veya firma yöneticisi güne **Özet** ile başlar; kuyruk işi **Gidiş** / **Dönüş** sayfalarındadır.

```mermaid
flowchart TD
  Start([Giriş]) --> Ozet[Özet: KPI + grafikler + harita]
  Ozet --> Pull{Konumları çek?}
  Pull -->|Evet| Arvento[POST /integrations/arvento/pull]
  Arvento --> Ozet
  Pull -->|Hayır| Branch{Ne yapılacak?}
  Branch --> Gidis[Gidiş kuyruğu]
  Branch --> Donus[Dönüş havuzu]
  Branch --> Takip[Takip haritası]
  Branch --> Uyari[Bildirimler]
  Gidis --> GidisIs[Ekle / Excel / Ata / Çıkar]
  Donus --> DonusIs[Ekle / Excel / Hesapla / Onayla]
  GidisIs --> Dosya[Yük dosya paneli]
  DonusIs --> Dosya
```

## 3. Senaryo: Gidiş yükü ekle ve ata

**Ekran:** `#gidis` → Ekle veya Excel içe aktar → satır → dosya paneli → Ata.

```mermaid
sequenceDiagram
  actor Ops as Operasyoncu
  participant UI as Gidiş kuyruğu
  participant API as API
  participant DB as Veri
  participant SMS as Netgsm

  Ops->>UI: Ekle formu veya Excel yükle
  UI->>API: POST /loads veya POST /loads/import
  API->>DB: planlanabilir satır
  API-->>UI: tablo yenilenir

  Ops->>UI: Satırı aç
  UI->>API: GET /loads/{id}/candidates
  API-->>UI: Uygun / elenen araçlar
  Ops->>UI: Ata
  UI->>API: POST /loads/{id}/assign
  API->>DB: status=atandi, km ve süre
  API->>SMS: atama kuyruğu + gönder
  alt Netgsm 00 + job id
    SMS-->>API: kabul
    API->>DB: locked=true
  else Hesap yok / red
    API->>DB: SMS bekliyor veya uyarı
  end
  API-->>UI: Dosya paneli SMS durumu
```

```mermaid
stateDiagram-v2
  [*] --> planlanabilir: Ekle / Excel
  planlanabilir --> atandi: Ata
  planlanabilir --> iptal: Çıkar
  atandi --> yolda: (sonraki sürüm / elle)
  atandi --> teslim: Teslim edildi
  atandi --> iptal: Atamayı iptal et / Çıkar
  atandi --> planlanabilir: PLAN_INFEASIBLE veya arıza/bakım kilidi bozar
  yolda --> teslim: Teslim edildi
  teslim --> [*]
  iptal --> [*]
```

## 4. Senaryo: Dönüş fırsatı ve otomatik eşleşme

**Ekran:** `#donus` → Ekle / Excel (navlun zorunlu) → Hesapla → öneri veya atama → dosya paneli.

```mermaid
sequenceDiagram
  actor Ops as Operasyoncu
  participant UI as Dönüş havuzu
  participant API as API
  participant Solver as OR-Tools
  participant SMS as Netgsm

  Ops->>UI: Dönüş satırı ekle (navlun)
  UI->>API: POST /loads direction=donus
  API-->>UI: havuz

  Ops->>UI: Hesapla (veya Ayarlar’da km maliyeti kaydet)
  UI->>API: POST /returns/solve veya PATCH /settings
  Note over API: Maliyet değişince API hesabı kendisi yeniden çalıştırır
  alt km maliyeti eksik
    API-->>UI: COST_RATES_MISSING uyarısı
  else maliyetler dolu
    API->>Solver: fayda matrisi (yalnız google mesafe)
    Solver-->>API: çiftler
    alt return_approval açık
      API-->>UI: onerildi (SMS yok)
      Ops->>UI: Onayla
      UI->>API: POST /loads/{id}/approve
      API->>SMS: atama
    else onay kapalı
      API->>SMS: atama
      API-->>UI: atandi + kilit (kabulde)
    end
  end
```

```mermaid
stateDiagram-v2
  [*] --> havuz: Ekle / Excel (navlun)
  havuz --> onerildi: Hesapla + onay modu
  havuz --> atandi: Hesapla + otomatik
  onerildi --> havuz: Daha iyi çözüm / Çıkar
  onerildi --> atandi: Onayla
  atandi --> havuz: Kararsızlık eşiği aşıldı ve kilit yok
  atandi --> teslim: Teslim edildi
  atandi --> iptal: İptal / kilit bozulması
  teslim --> [*]: Araç boş + yeniden Hesapla tetiklenebilir
```

## 5. Senaryo: Excel içe / dışa aktarma

**Ekran:** Gidiş veya Dönüş üst düğmeleri.

```mermaid
flowchart LR
  subgraph Ice["İçe aktarma"]
    T[Şablon indir]
    F[Excel / CSV seç]
    I[POST /loads/import]
    R[Kabul / güncelleme / ret özeti]
  end
  subgraph Disa["Dışa aktarma"]
    E[Excel dışa aktar]
    X[GET /loads/export?direction=...]
    D[yukler-*.xlsx indir]
  end
  T --> F --> I --> R
  E --> X --> D
```

Kurallar:

- İlk satır başlıktır. Zorunlu kolonlar şablondaki gibidir.
- Dönüş satırında `yon=donus` ve `navlun_try` dolu olmalıdır.
- Kilitli / yolda / teslim referans güncellenmez (`ROW_LOCKED`).
- Dışa aktarma `iptal` satırlarını çıkarır.

## 6. Senaryo: Yer güncelleme ve SMS

**Ekran:** Atanmış yük dosya paneli → boşaltma ili/ilçesi → Yeri güncelle.

```mermaid
sequenceDiagram
  actor Ops as Operasyoncu
  participant UI as Yük dosyası
  participant API as API
  participant SMS as Netgsm

  Ops->>UI: Boşaltma yerini değiştir
  UI->>API: POST /loads/{id}/revise
  API->>API: Değişiklik var mı?
  alt Değişti ve status=atandi
    API->>SMS: guncelleme (aynı olay ikinci kez açılmaz)
  end
  API-->>UI: Güncel rota metni
```

İptal (kilitli atama):

```mermaid
sequenceDiagram
  actor Ops as Operasyoncu
  participant UI as Yük dosyası
  participant API as API
  participant SMS as Netgsm

  Ops->>UI: Atamayı iptal et / Çıkar
  UI->>API: POST /loads/{id}/cancel veya DELETE
  alt locked
    API->>SMS: iptal
  else kilit yok
    API->>API: bekleyen SMS düşer
  end
  API-->>UI: iptal veya gidişte planlanabilir / dönüşte havuz
```

## 7. Senaryo: Canlı takip

**Ekran:** `#takip` (okuma). Konum kaynağı Özet’teki Arvento çekimi veya elle konum.

```mermaid
sequenceDiagram
  participant Ops as Operasyoncu
  participant UI as Takip
  participant WS as WebSocket /live
  participant API as API
  participant Arvento as Arvento SOAP

  Ops->>UI: #takip aç
  UI->>WS: token ile bağlan
  WS-->>UI: snapshot araçlar
  Ops->>API: Konumları çek (Özet)
  API->>Arvento: GetVehicleStatusV4
  Arvento-->>API: paketler
  API->>WS: position olayları
  WS-->>UI: noktalar güncellenir
```

## 8. Senaryo: Uyarı ve takograf

**Ekran:** üst çubuk zil / bildirimler, araç dosyası takograf satırı, yük dosyası kalan süreler.

```mermaid
flowchart TD
  Pos[Yeni konum örneği] --> Tacho[Tahmini sayaç güncelle]
  Tacho --> Fit{Açık sefer sığar mı?}
  Fit -->|Hayır ve kilitli| Break[PLAN_INFEASIBLE: iptal SMS + yük düşer]
  Fit -->|Uyarı eşiği| Alert[Bildirimler zili]
  Fit -->|Tamam| Ok[Sayaç devam]
  Alert --> Seen[Görüldü işaretle]
```

## 9. Senaryo: Ayarlar (firma yöneticisi)

**Ekran:** `#ayarlar`

```mermaid
flowchart LR
  A[Ayarlar] --> C[Kasa tipleri + km maliyeti]
  A --> T[Günlük limit / ön uyarı]
  A --> F[Dönüş onay / tahmini otomatik]
  A --> R[Arvento PIN]
  A --> N[Netgsm üçlüsü]
  C --> Patch[PATCH /settings]
  T --> Patch
  F --> Patch
  R --> PutA[PUT /settings/arvento]
  N --> PutN[PUT /settings/netgsm]
```

Dönüş hesabı yalnızca iki km maliyeti dolunca çalışır. Netgsm kaydı yoksa atama yine yazılır; SMS bekler, kilit oluşmaz.

## 10. Senaryo: Platform sicili

**Ekran:** `#firmalar`

```mermaid
sequenceDiagram
  actor PA as Platform yöneticisi
  participant UI as Firmalar
  participant API as API

  PA->>UI: Firma aç
  UI->>API: POST /tenants
  PA->>UI: Kullanıcı ekle
  UI->>API: POST /tenants/{id}/users
  Note over PA,API: Operasyon menüsü yok; /loads 403
```

## 11. Sayfa × senaryo matrisi

| Senaryo | Özet | Gidiş | Dönüş | Takip | Bildirim | Araçlar | Ayarlar |
| --- | --- | --- | --- | --- | --- | --- | --- |
| KPI / grafik okuma | ● | | | | | | |
| Arvento çek | ● | | | ○ | | | |
| Gidiş ekle / Excel / ata | | ● | | | | | |
| Dönüş ekle / Hesapla / onay | | | ● | | | | |
| Canlı konum izle | ○ | | | ● | | | |
| Uyarı görüldü | ○ | | | | ● | | |
| Araç durum / şoför | | | | | | ● | |
| Maliyet / Netgsm / bayraklar | | | | | | | ● |

● birincil ekran · ○ yardımcı tetikleyici

## 12. Yük yaşam döngüsü (özet)

```mermaid
stateDiagram-v2
  direction LR
  [*] --> GidisPlan: gidis ekle
  [*] --> DonusHavuz: donus + navlun
  GidisPlan --> Atandi: operasyon ata
  DonusHavuz --> Onerildi: hesapla + onay
  DonusHavuz --> Atandi: hesapla otomatik
  Onerildi --> Atandi: onayla
  Atandi --> Teslim: teslim edildi
  Atandi --> Iptal: iptal / kilit kırılması
  Teslim --> [*]: araç boş → dönüş hesabı
  Iptal --> [*]
```
