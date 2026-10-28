# MVP planı

Sürüm: 0.2  
Tarih: 25 Ekim 2026

Bu belge ilk yayının sınırıdır. İşin tamamı [iş gereksinimlerinde](brd.md), kurallar [iş kurallarında](is-kurallari.md), kurulum [mimari planda](mimari-ve-teslimat.md) durur. MVP o belgeleri daraltır. Kuralları gevşetmez.

## 1. MVP nedir

Operasyoncu, Arvento’dan gelen konuma bakarak gidiş yükünü elle atar. Dönüş fırsatı navlunuyla havuza girer. Sistem, boş veya boşalacak tırı takograf sınırının içinde en yüksek faydayla otomatik eşleştirir ve rotayı o firmanın Netgsm hesabından şoföre yazar.

Ürün tek firmaya özel değildir. Aynı imaj paylaşılan podda birden fazla firmayı, ayrı podda tek firmayı çalıştırır. İki firmanın verisi ve hesabı birbirine karışmaz.

İlk müşterinin filosu bu yayının deneme verisidir: tenteli tırlar, araç başına 24 veya 25 ton. Ürün başka firmanın kasa tipini ve tonajını da kaydeder.

## 2. Yayında olan

- Firma, kullanıcı, rol. Kullanıcı tek firmaya bağlıdır.
- `shared` ve `dedicated` açılış kuralları. Paylaşılan podda firma sırları şifreli kayıttadır. Ayrı pod `TENANT_ID` ve o firmanın ortam değişkenleriyle açılır. Paylaşılan pod, Netgsm veya Arvento sırrı ortamda doluysa açılmaz.
- Araç, şoför, cep telefonu, kasa tipi, kapasite, boş ve dolu kilometre maliyeti.
- Kasa kataloğu: tenteli, frigolu, sal, lowbed, tanker. Firma kullandığı tipleri açar.
- Arvento SOAP `GetVehicleStatusV4` ile son konum, hız, yön, plaka ve sinyal zamanı. Kontak bu pakette yoktur. Sürücü alanı geliyorsa eşleşme güncellenir.
- Tonaj, açık seferin tonajıdır. Operasyoncu düzeltebilir. Sensör tonajı bu yayında yoktur.
- Planlanabilir araç: serviste, konumu taze, şoförü belli, yeni yüklemeden önce boşalıyor.
- Gidiş yükünün Excel veya CSV ile toplu girişi. Atamayı operasyoncu yapar.
- Dönüş fırsatı, navlun zorunlu. Navlunsuz satır havuza girmez.
- Google Geocoding ve trafiksiz Routes API rota matrisi. Mesafe yaklaşık kalırsa otomatik atama kesinleşmez.
- `TR-AETR-2026` kural paketi. Firma sınırı yalnızca daraltabilir.
- Takograf sayacı, `TachographActiveFleetReport` veya `CANBUSTachographLastStatus` örnek cevabında eşlenirse ölçülmüş kullanılır. Eşlenmezse tahmin `dSpeed` üzerinden üretilir. Tahmini sayaçla otomatik dönüş, firmanın bayrağı kapalıyken yapılmaz. Bayrağın başlangıç değeri kapalıdır.
- Dönüşte tam eşleştirme, açıklama kartı ve yüzde 15 kararlılık eşiği.
- Atama, güncelleme ve iptal SMS’i. Netgsm kabulü atamayı kilitler.
- Uygulama içi uyarılar: mola ve sürüş sınırları, bayat sinyal, eksik telefon, SMS reddi, iletilemeyen SMS, yasal olarak bozulan plan, eksik kilometre maliyeti.
- Operasyon ekranı sefer masasıdır: gidiş kuyruğu, harita, dönüş havuzu ve dosya paneli. Görsel kabuk ücretsiz Minimal’dır. Menü ve yetki değişmez. Platform yöneticisi bu masayı açamaz. Sayfa ve rol dökümü [arayüz planındadır](arayuz.md).

## 3. Yayında olmayan

Bunlar sonraki sürümdedir. MVP şeması onları sonradan eklemeye izin verir. Ekranları ve canlı çağrıları ilk yayına girmez.

- Seyir canlı bağlantısı. Adaptör arayüzü durur, istek atılmaz.
- Aks ağırlığı, `WEIGHT_CONFLICT`, `EMPTY_BUT_HEAVY`, `LOADED_WITHOUT_ORDER`.
- Kart okunamadı uyarısı. Arvento bu alanı örnek cevapta göstermeden üretilmez.
- Rota sapması ve mola noktası seçimi.
- Firmanın paylaşılan poddan kendi poduna taşınması için ekran. Taşıma, veri kopyalama işlemidir.
- Şoför uygulaması, e-posta, U-ETDS, muhasebe, yakıt ve ERP.
- Parsiyel yük, çift şoför, uluslararası sefer.
- Platform yöneticisinin bir firmanın operasyonunu açması.

## 4. Operasyoncunun günü

1. Gidiş dosyasını yükler. Hatalı satırlar neden koduyla döner.
2. Kuyruktan bir yük seçer. Sistem kapasitesi, kasa tipi, konumu ve takografı uyan araçları sıralar. Uymayanı gerekçesiyle gösterir ve seçtirmez.
3. Aracı bağlar. Firmanın Netgsm hesabı kabul edince şoföre atama SMS’i gider ve atama kilitlenir.
4. Dönüş fırsatlarını navlunlarıyla havuza yazar.
5. Araç teslimle boşalınca sistem havuzu yeniden çözer. Açıklama kartında boş kilometre, dolu kilometre, navlun ve net fayda görünür.
6. İptal veya yer değişikliğinde şoföre ayrı SMS gider.
7. Sınır yaklaşınca uyarı kutusunda görür. Uyarı şoföre SMS olarak gitmez.

## 5. Dilimler

Her dilim bir öncekinin üstüne çıkar. Dilim bitmeden sonraki dilimin entegrasyonu tamamlanmış sayılmaz.

### M1 — Firma ve izolasyon

Firma, kullanıcı, araç, şoför, kasa, kapasite, kilometre maliyeti. `shared` ve `dedicated` açılış kuralları. Elle konum. Sicil kabuğu ve sefer masası: araç, şoför, ayar ve kullanıcı sayfaları rolüne göre açılır.

Bitti sayılması: iki firma aynı podda birbirinin aracını okuyamaz. Ayrı pod başka firma kimliğini reddeder. Paylaşılan pod, Netgsm ortam değişkeni doluyken açılmaz.

### M2 — Konum, gidiş, harita

Arvento SOAP `GetVehicleStatusV4`, tazelik uyarısı, planlanabilir liste. Toplu gidiş dosyası, Google koordinat ve mesafe, operasyoncunun ataması. Haritada son konum.

Bitti sayılması: geçerli satırlar kuyruğa iner. 25 tonluk yük, 24 tonluk tenteli araca yazılamaz. Frigolu yük tenteli araca yazılamaz. Bayat konumlu araç listede planlanabilir görünmez.

### M3 — Takograf

`TR-AETR-2026`, tahmini ve ölçülmüş sayaç, şirket limiti, sürüş ve mola uyarıları, `PLAN_INFEASIBLE`.

Bitti sayılması: 4,5 saat, 9 ve 10 saat, haftada iki uzatma, 56 saat ve 90 saat testleri geçer. Yasal sınırın üstüne şirket limiti yazılamaz. Gidiş ataması sayaçsız araçla kapanmaz.

### M4 — Dönüş ve SMS

Navlunlu fırsat, TL fayda, tam eşleştirme, kararlılık, açıklama kartı, Netgsm kuyruğu ve kilit.

Bitti sayılması: iki araç ve iki fırsatta çözücü, tek tek en iyi seçimin toplamı düşürdüğü örnekte yüksek toplamı seçer. Navlunsuz dönüş satırı havuza girmez. Netgsm kabulü atamayı kilitler. Aynı olay ikinci SMS üretmez. Bir firmanın SMS’i diğer firmanın başlığıyla gitmez. Kilometre maliyeti boşsa o firmanın dönüş hesabı çalışmaz.

M4 kapanınca MVP yayınlanır.

## 6. Yayın kapısı

MVP, mimari plandaki üretim kapılarının 3, 4, 5, 6 ve 7 numaralı maddeleri geçmeden pilot firmaya açılmaz. `TR-AETR-2026` değerlerinin resmi metinle kontrolü bu kapının parçasıdır. Seyir dokümanı ve aks ağırlığı bu kapıyı beklemez.

Pilotun ilk haftasında bakılacaklar:

- İki firmanın verisi çapraz sorguda karışmaz.
- Gidiş dosyası ve dönüş fırsatı, kurala uymayan çiftleri atamaz.
- Operasyoncu fayda kartını ek hesap yapmadan okur.
- Şoför, kabul edilen SMS’te yükleme ve boşaltma ilini, ilçesini ve saatini görür.
- 100 araç ve 100 fırsatta, elemeden sonra önbellekli Google çağrılarıyla eşleşme 10 saniyenin altında biter.

## 7. MVP sonrası

Sıradaki iş, pilotun gerçek verisine göre seçilir.

1. Arvento örnek cevabında takograf sayacı veya aks ağırlığı varsa ölçülmüş sayaç ve sensör tonajı.
2. Seyir sözleşmesi gelirse ikinci adaptör.
3. Rota sapması ve uyarıların e-posta ile gitmesi.
4. Firmayı paylaşılan poddan ayrı poda taşıyan operasyon adımı.
