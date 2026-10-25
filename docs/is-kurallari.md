# İş kuralları

Bu belge [iş gereksinimlerinin](brd.md) uygulanırken değişmeyecek kararlarını sabitler. Ekran ve servis bu kurallara uymazsa gereksinim karşılanmış sayılmaz.

## 1. Araç durumları

Operasyon durumu:

| Durum | Planlama |
| --- | --- |
| `serviste` | Diğer koşullar sağlanırsa açık |
| `bakimda` | Kapalı |
| `ariza` | Kapalı |

Yük durumu, açık seferden türetilir:

| Durum | Anlam |
| --- | --- |
| `bos` | Açık sefer yok ve etkin tonaj boş eşiğinin altında |
| `yuklu` | Açık sefer var |
| `bosalacak` | Açık sefer var ve tahmini teslim zamanı belli |

Etkin tonaj sırası:

1. Operasyoncunun son düzeltmesi, düzeltme açık sefer için yapıldıysa
2. Açık seferin tonajı
3. Sağlayıcıdan gelen brüt ağırlık eksi dara, ikisi de varsa
4. Hiçbiri yoksa ve açık sefer de yoksa araç `bos` kabul edilir

Boş eşiği, firmanın belirlediği toleranstır. Başlangıç değeri daranın yüzde 5’i veya 1 ton, hangisi büyükse odur. Sensör tonajı ile sefer tonajı bu eşiğin üzerinde ayrışırsa `WEIGHT_CONFLICT` açılır ve planlama sefer tonajını esas alır.

`yuklu` araç, teslim zamanı yeni yükün hazır zamanından önceyse `bosalacak` gibi planlanabilir. Yeni yükün bindirme noktası, mevcut boşaltma noktasıdır. Çakışan saat aralığına ikinci yük yazılmaz.

## 2. Yük durumları

```text
taslak → planlanabilir → atandi → yolda → teslim
            ↘ iptal         ↘ iptal
taslak → havuz → onerildi → atandi → yolda → teslim
            ↘ iptal
```

- Gidiş, koordinatı çözülünce `planlanabilir` olur.
- Dönüş, koordinatı çözülünce `havuz` olur.
- Onay modu açıksa otomatik çözüm yükü `onerildi` yapar. Operasyoncu onaylayınca `atandi` olur.
- Otomatik modda çözüm doğrudan `atandi` yazar.
- `yolda`, araç yükleme noktasına vardığında veya operasyoncu yola çıktı dediğinde başlar.
- `teslim`, boşaltma tamamlanınca aracın yük durumunu `bos` yapar ve dönüş hesabını tetikler.
- `atandi` ve sonrası dosyayla güncellenemez. İptal, ancak henüz `yolda` değilse operasyoncu tarafından yapılır. İptal, aracı yeniden planlamaya sokar.

## 3. Aday eleme

Bir araç–yük çifti, aşağıdaki kodlardan biri oluşursa skora girmez:

| Kod | Koşul |
| --- | --- |
| `VEHICLE_NOT_IN_SERVICE` | Araç bakımda veya arızada |
| `STALE_POSITION` | Son sinyal, tazelik eşiğinden eski |
| `NO_DRIVER` | Eşleşmiş sürücü yok |
| `CAPACITY` | Yük tonajı, araç kapasitesinden büyük |
| `TRAILER` | Yükün dorse tipi, aracın dorse tipiyle aynı değil |
| `OVERLAP` | Aracın boşalma zamanı, yükün hazır zamanından sonra |
| `WINDOW` | Yasal molalar eklenmiş varış, teslim penceresinin dışında |
| `TACHO_DAILY` | Kalan günlük sürüş, gerekli sürüşü karşılamıyor |
| `TACHO_WEEKLY` | Kalan haftalık sürüş yetmiyor |
| `TACHO_FORTNIGHT` | Kalan iki haftalık sürüş yetmiyor |
| `TACHO_REST` | Sefer, günlük veya haftalık dinlenme başlamadan bitirilemiyor |
| `TACHO_UNKNOWN` | Ölçülmüş sayaç yok ve firma tahmini takografla otomatik atamayı kapattı |
| `APPROX_DISTANCE` | Mesafe yaklaşık ve atama otomatik kesinleşecek |

Gidiş listesinde bu çiftler gizlenmez. Reddedildi olarak ve kodla gösterilir. Dönüş çözümüne girmezler.

## 4. Takograf kural paketi `TR-AETR-2026`

Değerler, Karayolu Taşıma Yönetmeliği madde 35’in işaret ettiği güncel AETR uygulamasından alınmıştır. Üretim öncesi konsolide resmi metinle birebir kontrol edilir. Firma kaydı bu değerleri büyütmez; şirket limiti daha küçükse o kullanılır.

| Parametre | Değer |
| --- | --- |
| Kesintisiz sürüş | 4,5 saat |
| Mola | 45 dakika |
| Bölünmüş mola | Önce en az 15 dakika, ardından en az 30 dakika |
| Günlük sürüş | 9 saat |
| Uzatılmış günlük sürüş | 10 saat, takvim haftasında en fazla 2 kez |
| Haftalık sürüş | 56 saat |
| Ardışık iki takvim haftası | 90 saat |
| Normal günlük dinlenme | 11 saat kesintisiz |
| Azaltılmış günlük dinlenme | En az 9 saat, iki haftalık dinlenme arasında en fazla 3 kez |
| Bölünmüş günlük dinlenme | En az 3 saat ve ardından en az 9 saat |
| Günlük pencere | Önceki dinlenmenin bitiminden itibaren 24 saat içinde günlük dinlenme tamamlanır |
| Normal haftalık dinlenme | 45 saat |
| Azaltılmış haftalık dinlenme | En az 24 saat |
| İki ardışık hafta | İki normal dinlenme, ya da bir normal ve bir azaltılmış |
| Haftalık dinlenmenin son başlama anı | Önceki haftalık dinlenmenin bitiminden 6 kez 24 saat sonra |
| Azaltmanın telafisi | Eksik süre, ilgili haftayı izleyen üçüncü haftanın sonuna kadar, en az 9 saatlik bir dinlenmeye eklenmiş tek parça halinde |

Sayılar sürüş süresine aittir. Diğer iş, bekleme ve mola bu sayaçlara eklenmez.

Uzun süreli dinlenme hem günlük hem haftalık şarta uyuyorsa haftalık dinlenme olarak yazılır. Azaltılmış haftalık dinlenme kullanıldıysa telafi borcu sürücünün kartında durur ve vadesi yaklaşınca `REDUCED_REST_COMPENSATION` açılır. Telafi borcu kapanmadan, borcun vadesini aşan bir plan üretilmez.

Günlük 10 saatlik uzatma, ancak o hafta ikiden az uzatma kullanıldıysa ve şirket limiti de 10 saate izin veriyorsa açılır. Plan bir uzatma harcıyorsa bu harcama atamanın üzerine yazılır. Atama iptal olursa harcama geri alınır. Gerçekleşmiş sürüşten doğan uzatma geri alınmaz.

### Sayaç kaynağı

`ölçülmüş`: sağlayıcının takograf raporundaki sürüş, mola ve dinlenme sayaçları. Plan bunu kullanır.

`tahmini`: rapor yokken hız 5 km/sa üzerinde süren hareket sürüş sayılır. Hız bu eşiğin altında ve bu durum mola süresi boyunca kesintisiz sürerse mola sayılır. Kontak kapalı uzun duruş, dinlenme adayıdır. Tahmini sayaçla gidiş önerisi üretilebilir. Otomatik dönüş ataması, firma `tahmini_ile_otomatik_atama` bayrağını açmadıkça yapılmaz. Bayrağın başlangıç değeri kapalıdır.

İki kaynak da yoksa çift `TACHO_UNKNOWN` ile elenir.

### Planın süre hesabı

1. Çıkış zamanı, yükün hazır zamanı ile aracın boşalma zamanının geç olanıdır.
2. Boş kilometre ve dolu kilometre yol ağından süreye çevrilir.
3. Sürüş 4,5 saati dolduruyorsa süreye 45 dakika mola eklenir. Yarım kalmış 15 dakikalık ilk parça varsa yalnızca kalan 30 dakika eklenir.
4. Eklenen sürüş, günlük, haftalık ve iki haftalık kalan hakları aşarsa çift elenir. Günlük 9 saat dolmuş ve uzatma hakkı varsa 10 saate kadar devam edilir.
5. Varış, teslim penceresinin içindeyse çift skorlanır. Değilse `WINDOW` ile elenir.
6. Sefer sırasında 24 saatlik pencere veya 6 kez 24 saatlik haftalık dinlenme borcu doluyorsa, gereken dinlenme süreye eklenir ve pencere yeniden denenir. Dinlenme eklenince pencere kaçıyorsa çift elenir.

İlk sürüm molayı bir otopark koordinatına koymaz. Molayı sürenin içine yazar. Operasyoncu tahmini varışta mola payını görür.

## 5. Uyarılar

Seviye `uyari` operasyoncuyu öne çeker. Seviye `kritik` planı bozar: araç, koşullar düzelene kadar yeni atama almaz. Süregelen sefer iptal edilmez; `PLAN_INFEASIBLE` ile yeniden plan istenir.

Başlangıç ön-uyarı payı 30 dakikadır. Firma bu payı büyütebilir, sıfıra indiremez. Küçük pay, uyarıyı sınıra daha çok yaklaştırır; yasal sınırı değiştirmez.

| Kod | Seviye | Koşul |
| --- | --- | --- |
| `BREAK_WARNING` | uyarı | Kesintisiz sürüş, 4,5 saate ön-uyarı payı kadar yaklaştı |
| `BREAK_OVERDUE` | kritik | Kesintisiz sürüş 4,5 saati geçti, nitelikli mola yok |
| `DAILY_DRIVING_WARNING` | uyarı | Günlük sürüş, kullanılabilir limite pay kadar yaklaştı |
| `DAILY_DRIVING_LIMIT` | kritik | 9 saat doldu ve uzatma hakkı yok, ya da 10 saat doldu |
| `WEEKLY_DRIVING_WARNING` | uyarı | Haftalık 56 saate pay kadar yaklaşıldı |
| `WEEKLY_DRIVING_LIMIT` | kritik | Haftalık sürüş 56 saati geçti |
| `FORTNIGHT_DRIVING_WARNING` | uyarı | İki haftalık 90 saate pay kadar yaklaşıldı |
| `FORTNIGHT_DRIVING_LIMIT` | kritik | İki haftalık sürüş 90 saati geçti |
| `DAILY_REST_DUE` | kritik | 24 saatlik pencerede günlük dinlenme tamamlanamıyor |
| `WEEKLY_REST_DUE` | kritik | Haftalık dinlenme, 6 kez 24 saat dolmadan başlamıyor |
| `REDUCED_REST_COMPENSATION` | uyarı | Telafi borcunun vadesine 3 günden az kaldı |
| `STALE_GPS` | uyarı | Servisteki aracın sinyali tazelik eşiğini geçti |
| `WEIGHT_CONFLICT` | uyarı | Sensör tonajı ile sefer tonajı boş eşiğinden fazla ayrıştı |
| `EMPTY_BUT_HEAVY` | uyarı | Açık sefer yok, sensör boş eşiğinin üstünde |
| `LOADED_WITHOUT_ORDER` | uyarı | Araç hareket halinde, etkin tonaj boş eşiğinin üstünde, açık sefer yok |
| `NO_DRIVER_CARD` | kritik | Araç hareket halinde, kart okuması yok |
| `TACHO_ESTIMATED` | uyarı | Planlamada kullanılan sayaç tahmini |
| `ROUTE_DEVIATION` | uyarı | Araç, planlanan koridordan firma eşiğinden fazla saptı. Başlangıç 15 km |
| `PLAN_INFEASIBLE` | kritik | Bağlı sefer, güncel sayaçla artık yasal değil |
| `SMS_NO_PHONE` | uyarı | Atanan şoförün geçerli cep telefonu yok. Atama kilitlenmez |
| `SMS_REJECTED` | uyarı | Netgsm gönderimi kabul etmedi |
| `SMS_UNDELIVERED` | uyarı | Netgsm kabul etti, iletim raporu telefona ulaşmadı dedi |

`NO_DRIVER_CARD`, sağlayıcı bu bilgiyi gönderdiğinde çalışır. Göndermiyorsa bu kod üretilmez ve `TACHO_ESTIMATED` açık kalır.

## 6. Fayda

Amaç, firmanın o hesaptaki tüm çiftlerinin fayda toplamını en büyük yapmaktır. Tek yükün kendi en iyi aracını kapması, başka bir yükü aracsız bırakıp toplamı düşürüyorsa seçilmez.

Navlun girilmişse, Türk lirası:

```text
fayda = navlun
      - bos_km × bos_km_maliyeti
      - dolu_km × dolu_km_maliyeti
```

Navlun boşsa:

```text
fayda = dolu_km - bos_km × bos_km_ceza_katsayisi
```

Başlangıç katsayısı 1,5’tir. Bir boş kilometre, 1,5 dolu kilometreden pahalı sayılır. İki formül aynı havuz hesabında karıştırılmaz. Havuzda navlunu olan ve olmayan yük bir arada ise, navlunu olmayan yük yedek formülle skorlanır ve açıklamada birimi `km` olarak yazılır. Toplam, yalnızca aynı birimdeki çiftler arasında maksimize edilir. Birimli gruplar ayrı ayrı eşleştirilir.

`bos_km`, aracın boşalma konumu ile yükleme noktası arasındaki yol mesafesidir. `dolu_km`, yükleme ile boşaltma arasındaki yol mesafesidir. Maliyet katsayıları firma ayarıdır, başlangıçta boş bırakılır. Boş bırakılan katsayı, navlun formülünü kullanılamaz hale getirir ve sistem o firma için yedek formüle düşer. Böylece uydurma bir liraya kilometre fiyatı atanmaz.

Gecikme formüle katılmaz. Pencere kaçıran çift zaten `WINDOW` ile elenmiştir.

### Eşleştirme

1. Firma için planlanabilir araçlar ve `havuz` durumundaki dönüş yükleri alınır.
2. Çiftler 3. bölümdeki kurallarla elenir.
3. Kalan çiftlerin faydası hesaplanır. Negatif fayda da aday kalır; başka yasal seçenek yoksa boş kilometre, aracı boşta tutmaktan iyi olabilir. Firma `negatif_fayda_atanmasin` açarsa negatif çiftler düşer. Başlangıç değeri kapalıdır.
4. Her araca en fazla bir yük, her yüke en fazla bir araç veren ve fayda toplamı en yüksek eşleşme seçilir. Çözüm tam eşleştirme algoritmasıyla bulunur. Araç veya yük sayısı diğerinden az ise açıkta kalanlar havuzda veya boşta durur.
5. Kilitli atamalar 7. bölümdeki kurala göre çözümün dışında tutulur, kalan serbest araç ve yüklerle hesap tekrarlanır.

Hesap şu olaylarda çalışır: havuza yük girmesi, yükün iptali, aracın teslimle boşalması, aracın planlanabilir hale gelmesi, operasyoncunun yeniden hesap istemesi. Konum her sinyalde hesabı tetiklemez.

### Kararlılık

- `onerildi` atama, daha iyi bir çözüm çıkınca değişir. Bu durumda SMS kuyruğa yazılmaz.
- `atandi` olup Netgsm henüz kabul etmemiş atama, yeni toplam fayda mevcut toplamın yüzde 15 üzerindeyse değişir. Eşik firma ayarıdır. Değişen atamanın bekleyen SMS’i gönderilmeden düşer.
- Netgsm’in iş kimliği döndürdüğü atama yalnızca `PLAN_INFEASIBLE`, araç arızası, bakım veya yük iptalinde bozulur. Telefona ulaşmama raporu kilidi açmaz.
- Değişen atamanın eski hali denetim kaydında kalır. Yeni kart, neyin değiştiğini gösterir.

## 7. Toplu giriş kuralları

Zorunlu kolonlar: `referans_no`, `yukleme_il`, `yukleme_ilce`, `bosaltma_il`, `bosaltma_ilce`, `tonaj`, `dorse_tipi`, `hazir_zamani`, `teslim_baslangic`, `teslim_bitis`.

Opsiyonel kolonlar: `musteri`, `yukleme_adres`, `bosaltma_adres`, `navlun_try`, `yon`.

Satır reddi:

| Kod | Koşul |
| --- | --- |
| `ROW_REQUIRED` | Zorunlu kolon boş |
| `ROW_TONNAGE` | Tonaj sayı değil veya sıfırdan büyük değil |
| `ROW_WINDOW` | Teslim bitişi, hazır zamanından önce |
| `ROW_PLACE` | İl veya ilçe sözlükte yok |
| `ROW_TRAILER` | Dorse tipi firma listesinde yok |
| `ROW_DIRECTION` | Yön dolu ama `gidis` veya `donus` değil |
| `ROW_LOCKED` | Referans atanmış bir yüke ait |
| `ROW_GEOCODE` | Adres koordinata çözülemedi |

Dosyada 2.000 satır sınırı vardır. Üstü tek dosya olarak kabul edilmez. Geçerli satırlar tek işlemde kaydolur. Hatalı satır atlanır. Sonuçta kabul, güncelleme ve ret sayıları ile ret gerekçeleri döner.

## 8. Açıklama kartı

Her öneri ve atama şu alanları saklar:

- Kural paketi kimliği ve hesap zamanı
- Takograf güveni: `olculmus` veya `tahmini`
- Sayaç özeti: kesintisiz sürüş, günlük, haftalık, iki haftalık kalan
- Boş kilometre, dolu kilometre, süre, eklenen mola dakikası
- Navlun, kilometre maliyetleri, fayda ve birim
- Bu aracın elendiği veya daha düşük kaldığı en fazla üç diğer yük, kodlarıyla
- SMS durumu: bekliyor, kabul edildi, iletildi, iletilemedi, düştü. Varsa Netgsm iş kimliği

Operasyoncu bu kart olmadan otomatik atamayı kabul etmek zorunda kalmaz. Onay modunda onay düğmesi kartla aynı ekrandadır. İletilemeyen SMS için yeniden gönder düğmesi de bu karttadır.

## 9. Rota SMS’i

SMS yalnızca şu üç olayda yazılır:

| Olay | Ne zaman | Kod |
| --- | --- | --- |
| Atama | Yük `atandi` olunca. Gidiş ve dönüş aynı kuraldadır | `atama` |
| Güncelleme | Aynı atamada yükleme yeri, boşaltma yeri, hazır zamanı veya teslim penceresi değişince | `guncelleme` |
| İptal | Kabul edilmiş atama iptal olunca veya `PLAN_INFEASIBLE` ile bozulunca | `iptal` |

Tahmini varışın kayması, mola dakikasının yeniden hesaplanması ve fayda kartının yenilenmesi SMS üretmez.

Şoförün telefonu 10 haneli `5` ile başlayan numaraya çözülemiyorsa kuyruğa satır yazılmaz, `SMS_NO_PHONE` açılır, atama `atandi` kalır ve kilitlenmez.

Kuyruk durumları: `bekliyor`, `kabul`, `iletildi`, `iletilemedi`, `dustu`.

Netgsm `00` ve bir iş kimliği dönerse satır `kabul` olur ve atama kilitlenir. Zaman aşımı ve 5xx üç kez, artan aralıkla yeniden denenir. Kimlik hatası, onaysız başlık ve hatalı numara yeniden denenmez. Satır `iletilemedi`ye ancak iletim raporu ulaşmayınca geçer. Rapor gecikmesi kilidi bekletmez.

Aynı atama kimliği ve aynı olay kodu ikinci satır açmaz. Atama, satır `bekliyor` iken değişirse satır `dustu` olur ve Netgsm’e gitmez.

Metin Türkçe karakter taşır. `encoding` değeri `TR` olur. Şablonlar:

```text
{firma} ATAMA {yon} {plaka} Ref {referans} Yukleme {yukleme_il}/{yukleme_ilce} {hazir} Bosaltma {bosaltma_il}/{bosaltma_ilce} Teslim {teslim_bas}-{teslim_bit}

{firma} GUNCELLEME {yon} {plaka} Ref {referans} Yukleme {yukleme_il}/{yukleme_ilce} {hazir} Bosaltma {bosaltma_il}/{bosaltma_ilce} Teslim {teslim_bas}-{teslim_bit}

{firma} IPTAL {plaka} Ref {referans} Bu sefer iptal edildi.
```

Saatler `GG.AA SS:dd` ve Türkiye saatidir. Açık adres ve koordinat mesaja girmez. Bir mesaj birden fazla SMS parçasına bölünebilir. Parça sayısı gönderim kaydında durur.

Gönderen, platformun tek Netgsm hesabıdır. `msgheader` o hesapta onaylı başlıktır. Firma kendi başlığını ilk sürümde getirmez. Şoför firmayı metnin ilk kelimesinden ayırır. `iysfilter` kapalıdır. Bu kuyruk pazarlama listesi değildir. Her firmanın kendi başlığını kullanması sonraki sürüme kalır.
