# Backhaul — İş Gereksinimleri Belgesi

Sürüm: 0.6  
Tarih: 25 Ekim 2026  
Durum: Taslak, uygulama öncesi inceleme

Bu belge ürünün ne işe yaradığını ve ilk sürümün neyi başarmış sayılacağını tanımlar. Sürüş süreleri, fayda formülü ve durum geçişleri [iş kuralları](is-kurallari.md) belgesindedir. Sistemin nasıl kurulacağı [mimari ve teslimat](mimari-ve-teslimat.md) belgesindedir.

Belgedeki takograf sınırları operasyonel kural paketine girdi olsun diye özetlenmiştir. Üretim öncesi, yürürlükteki konsolide AETR metniyle hukuk kontrolünden geçirilir. Bu belge hukuk görüşü değildir.

## 1. Amaç

Nakliye firması, boşalan tırına dönüş yükünü geç bulduğunda boş kilometre yapar. Yükü bulunca da sürücünün kalan sürüş süresi yetmezse sefer yolda kalır veya takograf sınırı aşılır.

Backhaul bu iki kararı aynı anda verir:

1. Araç şu an nerede, kaç ton yüklü ve yeni bir iş alabilir mi?
2. Alabiliyorsa, havuzdaki dönüş yüklerinden hangisi yasal süreler içinde en yüksek faydayı üretir?

Gidiş yükleri firmanın elindedir ve toplu girilir. Dönüş yükü ise havuzdan sistem tarafından atanır.

## 2. Ürün kapsamı

İlk sürüm, Türkiye içinde komple tır taşıması yapan firmalara satılan bir üründür. Tek bir firmanın özel yazılımı değildir. Aynı imaj iki biçimde çalışır: her firmanın kendi podunda, ya da birçok firmanın paylaştığı podda. İki biçimde de firmalar birbirinin aracını, yükünü, şoförünü, planını ve entegrasyon hesabını görmez. Paylaşılan podda firmalar aynı veritabanında, satırdaki firma kimliğiyle ayrılır. Ayrı podda firmanın kendi veritabanı olur. Şema iki kurulumda da aynıdır.

İlk sürümde olanlar:

- Firma, kullanıcı ve rol yönetimi
- Araç, dorse tipi, sürücü ve takograf kartı kimliği
- Arvento ve Seyir’den konum ile sürücü verisinin alınması
- Yüklü tonajın yük kaydından, sensör varsa sensörden okunması
- Boş ve boşalması belli araçlara planlama
- Gidiş yüklerinin Excel veya CSV ile toplu girilmesi
- Dönüş yüklerinin navlunu belli fırsat olarak havuza alınması ve uygun tıra otomatik atanması
- AETR sürüş, mola ve dinlenme sınırlarına göre planın elenmesi
- Sınır aşımı ve aşım riski için uyarı kaydı
- Atamanın neden seçildiğinin operasyoncuya gösterilmesi
- Kesinleşen yük ve rotanın, o firmanın kendi Netgsm hesabıyla şoföre iletilmesi

İlk sürümde olmayanlar:

- Uluslararası sefer, gümrük, CMR ve geçiş belgesi
- Parsiyel yük ve bir araçta birden fazla yük
- Çift sürücü
- Sürücüye özel mobil uygulama. Rota, SMS ile gider.
- U-ETDS bildirimi (firmalar bunu Seyir veya kendi süreçleriyle yapmaya devam eder)
- Muhasebe, fatura, yakıt kartı ve ERP aktarımı
- Ücretli yol ve köprü ücretinin canlı sorgusu
- Mola verilecek otoparkın harita üzerinde seçilmesi

## 3. Roller

| Rol | İş |
| --- | --- |
| Platform yöneticisi | Firma açar, firmayı askıya alır, sistem sağlığını görür. Firma operasyon verisini günlük iş için kullanmaz. |
| Firma yöneticisi | Kullanıcı, araç, sürücü, dorse tipi, maliyet katsayısı ve entegrasyon hesabını yönetir. Yasal takograf sınırını gevşetemez. |
| Operasyoncu | Gidiş yükünü içe aktarır, gidiş aracı atar, dönüş havuzunu izler, uyarıyı kapatır, hatalı tonajı düzeltir, iletilemeyen rota SMS’ini yeniden gönderir. |
| İzleyici | Plan, harita ve uyarıyı görür. Kayıt değiştirmez. |

Bir kullanıcı ilk sürümde tek firmaya bağlıdır. Platform yöneticisi firma kullanıcısı değildir. Ekranların dökümü ve rolün sayfada ne yapacağı [arayüz planındadır](arayuz.md).

## 4. İş akışı

### Gidiş

1. Operasyoncu şablon dosyayı yükler.
2. Sistem satırları doğrular, adresleri koordinata çevirir, yükü gidiş kuyruğuna alır.
3. Sistem, tonajı ve dorse tipi uyan, konumu işe yetişen ve takografı elveren araçları sıralar.
4. Operasyoncu aracı seçer. Sefer bağlanır ve şoföre rota SMS’i gider.
5. Araç yükleme noktasına gidene ve yükü teslim edene kadar yeni bir yük alamaz.

### Dönüş

1. Dönüş fırsatı, navlunuyla birlikte tek tek veya aynı dosyayla havuza girer. Navlunu olmayan satır havuza düşmez.
2. Bir araç teslimatla boşaldığında, ya da dönüşte boşalacağı zaman ve yer belli olduğunda, sistem havuzu yeniden hesaplar.
3. Her uygun araç–fırsat çifti için boş kilometre, dolu kilometre, navlun ve yasal varış bakılır.
4. Sistem her araca en fazla bir, her yüke en fazla bir atama yapar ve kaydeder.
5. Firma ayarı otomatik ise atama kesinleşir. Firma onayı açtıysa operasyoncu onaylar.
6. Kesinleşen atama şoföre Netgsm ile SMS olarak gider. Netgsm gönderimi kabul edince atama kilitlenir.
7. Kilitten sonra atama, ancak yasal olarak sürdürülemiyorsa veya yük iptal olursa bozulur. İptal ve rota değişikliği şoföre ayrı SMS ile gider.

## 5. İş gereksinimleri

| No | Gereksinim | Karşılanma |
| --- | --- | --- |
| BR-1 | Operasyoncu, aracın konumuna göre yeni iş alıp alamayacağını görür. | Konum tazeliği, açık sefer ve tahmini boşalma zamanı birlikte değerlendirilir. |
| BR-2 | Operasyoncu aracın kaç ton yüklü olduğunu görür. | Önce açık yükün tonajı, sensör varsa sensör, gerekirse operasyoncu düzeltmesi. |
| BR-3 | Dolu araca yeni yük yazılamaz. | Plan yalnızca boş araca veya mevcut işi yeni yüklemeden önce biten araca açılır. |
| BR-4 | Gidiş yükleri tek tek yazılmadan sisteme girer. | Dosya içe aktarımı, satır satır hata raporu ve referans numarasıyla tekrar yükleme. |
| BR-5 | Dönüş fırsatı, havuzdaki navlunlu seçenekler içinde en yüksek faydayı veren uygun araca kendiliğinden bağlanır. | Fayda formülü, tek eşleşme ve otomatik atama modu. |
| BR-6 | Üretilen hiçbir plan, yürürlükteki takograf sınırını aşan bir sürüş programı içeremez. | Sürüme bağlı kural paketi. Firma bu sınırları yalnızca daraltabilir. |
| BR-7 | Sınır aşıldığında veya aşılmak üzereyken uyarı oluşur. | Uyarı kaydı, seviye ve kapatma. İlk sürümde bildirim uygulama içindedir. |
| BR-8 | Arvento kullanan firma ile Seyir kullanan firma aynı ekranları kullanır. | Sağlayıcıya özel adaptör, ortak araç anlık görüntüsü. |
| BR-9 | Bir firma başka firmanın aracını, yükünü, hesabını ve planını göremez. | Her kayıtta firma kimliği. Paylaşılan podda sorgu bu kimlik olmadan çalışmaz. Ayrı pod başka firmanın kimliğini kabul etmez. |
| BR-10 | Şoför, kendine kalan yükün yükleme ve boşaltma yerini ve zamanını telefonunda görür. | Netgsm SMS’i. Ayrı bir şoför uygulaması yoktur. |

## 6. Fonksiyonel gereksinimler

### Firma ve erişim

- FR-1.1 Platform yöneticisi firma oluşturur. Firmanın görünen adı, kısa kodu ve saat dilimi vardır. Saat dilimi `Europe/Istanbul` olarak başlar.
- FR-1.2 Firma yöneticisi operasyoncu ve izleyici ekler, rol değiştirir, erişimi kapatır.
- FR-1.3 Kapalı kullanıcı oturum açamaz. Askıdaki firmanın kullanıcıları operasyon yapamaz.

### Filo

- FR-2.1 Araç kaydında plaka, izleme sağlayıcısı, sağlayıcıdaki cihaz kimliği, taşıma kapasitesi (ton), dorse tipi ve dara vardır. Kapasite araca aittir. İlk müşterinin her tırı tentelidir ve kapasitesi 24 veya 25 tondur. Başka firmalar katalogdaki diğer kasa tiplerini ve kendi tonajlarını kullanır.
- FR-2.2 Sürücü kaydında ad, takograf sürücü kartı kimliği ve Türkiye cep telefonu vardır. Telefon `5XXXXXXXXX` biçimine getirilir. Araçla sürücü eşlemesi hem elle hem takip sisteminden gelen kart okumasıyla güncellenir.
- FR-2.3 Araç `serviste`, `bakımda` veya `arıza` durumundadır. Bakım ve arıza planlamaya kapalıdır.

### Konum, tonaj ve müsaitlik

- FR-3.1 Sistem, bağlı sağlayıcıdan aracın son konumunu, hızını, kontak durumunu ve sinyal zamanını alır.
- FR-3.2 Sinyal, firma eşiğinden eskiyse (başlangıç değeri 15 dakika) konum planlamada kullanılamaz ve uyarı açılır.
- FR-3.3 Açık seferi olan aracın yüklü tonajı, o seferin kalan yüküdür.
- FR-3.4 Sağlayıcı aks ağırlığı veya benzeri bir sensör değeri gönderiyorsa sistem bunu ayrıca saklar. Sensör ile yük kaydı, firma toleransından fazla ayrışırsa uyarı açılır. Sensör hiç gelmiyorsa tonaj yük kaydından gelir; sistem tonaj uydurmaz.
- FR-3.5 Operasyoncu tonajı düzeltebilir. Düzeltme, kim düzeltti ve önceki değer ile birlikte durur.
- FR-3.6 Planlanabilir araç şunların hepsini sağlar: serviste olmak, konumun taze olması, eşleşmiş sürücünün bulunması, üzerinde çakışan yük olmaması, yeni işin hazır zamanından önce boşalıyor olmak.
- FR-3.7 Boşalma yeri, açık seferin boşaltma noktasıdır. Boşalma zamanı, yasal molalar eklenmiş tahmini varıştır.

### Yük ve toplu giriş

- FR-4.1 Yükün yönü gidiş veya dönüştür. Dönüş kaydı havuzda fırsat olarak durur. Zorunlu alanlar: firma içi tekil referans, yükleme ili ve ilçesi, boşaltma ili ve ilçesi, tonaj, dorse tipi, hazır zamanı, teslim penceresi. Dönüş fırsatında navlun da zorunludur.
- FR-4.2 Adres metni koordinata çevrilir. Çevrilemeyen satır havuza düşmez; operasyoncu adresi düzeltir.
- FR-4.3 Toplu dosya `.xlsx` veya `.csv` olur. Geçerli satırlar kaydolur. Hatalı satırlar kaydolmaz ve neden koduyla rapora yazılır.
- FR-4.4 Aynı referans yeniden yüklenirse, yük henüz atanmamışsa güncellenir. Atanmış, yoldaki veya teslim edilmiş yük dosyadan değiştirilemez.
- FR-4.5 Yön boş bırakılırsa satır gidiş sayılır. Dönüş satırları fırsat olarak havuza, gidiş satırları operasyoncunun atama kuyruğuna gider.
- FR-4.6 Gidiş navlunu opsiyoneldir. Dönüş fırsatının navlunu Türk lirası olarak zorunludur. Navlunsuz dönüş satırı kaydolmaz.
- FR-4.7 İlk sürümde bir sefer bir yük taşır. Tonaj, araç kapasitesini aşıyorsa o araca önerilmez.

### Gidiş planı

- FR-5.1 Sistem, gidiş kuyruğundaki bir yük için planlanabilir araçları faydaya göre sıralar. Sıralama bilgi amaçlıdır; atamayı operasyoncu yapar.
- FR-5.2 Takografı, kapasitesi, dorse tipi veya zaman penceresi elvermeyen araç listede gerekçesiyle reddedilmiş olarak durur.
- FR-5.3 Operasyoncu reddedilmiş bir aracı gerekçeyi aşarak seçemez.

### Dönüş planı

- FR-6.1 Havuzdaki her dönüş fırsatı, dönüşte boşalacak veya boş olan planlanabilir araçlarla karşılaştırılır. Kasa tipi ve kalan tonaj uymayan çift elenir.
- FR-6.2 Sistem, firmanın tüm uygun çiftleri birlikte çözerek toplam faydası en yüksek birebir eşleşmeyi yazar. Açgözlü biçimde yükleri tek tek kapmak bu çözümü karşılamaz.
- FR-6.3 Varsayılan firma ayarı otomatik atamadır. Firma yöneticisi, atamanın operasyoncu onayıyla kesinleşmesini açabilir.
- FR-6.4 Netgsm gönderimi kabul edilmiş bir atama, hâlâ yasal ve yük duruyorsa, daha kârlı bir eşleşme çıksa bile yerinde kalır. Kabul öncesinde, yeni çözüm firma eşiğinden (başlangıç yüzde 15) daha iyiye gidiyorsa değişebilir.
- FR-6.5 Atama kartında navlun, boş kilometre, dolu kilometre, maliyet, net fayda, tahmini süre, eklenecek molalar ve elenen güçlü adayların gerekçesi görünür.

### Takograf

- FR-7.1 Kural değerleri kodun içine gömülü sayılar olarak durmaz. `TR-AETR-2026` paketinde saklanır ve plan, paketin kimliğiyle birlikte yazılır.
- FR-7.2 Firma yöneticisi günlük sürüş, haftalık sürüş veya mola payı için yasal değerden daha sıkı bir şirket limiti girebilir. Yasal değerden gevşek değer kaydedilemez.
- FR-7.3 Plan motoru sürüş parçalarını 4,5 saatlik dilimlere böler, gerekli molayı ve gün içi kalan hakkı süreye ekler, teslim penceresini buna göre dener.
- FR-7.4 Takograf ayrıntısı sağlayıcıdan geliyorsa durum `ölçülmüş` olur. Gelmiyorsa hız ve kontaktan `tahmini` sürüş üretilir. Tahmini sayaç gidiş önerisinde görünebilir. Otomatik dönüş ataması, firma ayrıca izin vermedikçe tahmini sayaçla kesinleşmez.
- FR-7.5 Hafta, Türkiye saatiyle pazartesi 00:00’da başlar ve pazar 24:00’ta biter. İki haftalık 90 saat hesabı, ardışık iki takvim haftasıdır.

### Uyarılar

- FR-8.1 Her uyarıda firma, araç, varsa sürücü, kod, seviye, ölçülen değer, sınır ve zaman vardır.
- FR-8.2 Aynı araç ve aynı kod için açık uyarı varken ikinci kayıt açılmaz; mevcut uyarı güncellenir.
- FR-8.3 Operasyoncu uyarıyı görüldü olarak işaretler. Koşul düzelince uyarı kapanır.
- FR-8.4 Operasyon uyarıları uygulama içi kutudadır. Şoföre takograf veya sinyal uyarısı SMS’i gitmez.

### Rota SMS’i

- FR-10.1 SMS, yük `atandi` olunca gider. `onerildi` kayıt şoföre yazılmaz.
- FR-10.2 Mesajda firma kısa adı, yön, plaka, referans, yükleme ili ve ilçesi, hazır zamanı, boşaltma ili ve ilçesi ve teslim penceresi vardır.
- FR-10.3 Yükleme yeri, boşaltma yeri, hazır zamanı veya teslim penceresi değişince güncelleme SMS’i gider. Yalnızca tahmini varışın birkaç dakika kayması mesaj üretmez.
- FR-10.4 İptal ve yasal olarak bozulan atama, şoföre iptal SMS’i gider. Yerine yeni atama çıktıysa onu ayrı bir atama SMS’i izler.
- FR-10.5 Telefonu boş olan şoförün ataması durur. Operasyoncuya `SMS_NO_PHONE` açılır. Atama, başarılı bir gönderim kabulü olmadan kilitlenmez.
- FR-10.6 Aynı atama ve aynı olay ikinci kez kuyruğa yazılmaz. Atama, SMS kabul edilmeden değişirse bekleyen mesaj gönderilmeden düşer.
- FR-10.7 Operasyoncu, iletilemeyen mesajı karttan yeniden gönderir. Yeniden gönderim kilidi açmaz.
- FR-10.8 Her firmanın kendi Netgsm kullanıcı kodu, API şifresi ve onaylı başlığı vardır. Paylaşılan podda bu üçü o firmanın şifreli kaydındadır. Ayrı podda, yalnızca o poda bağlı firmanın ortam değişkenidir: `NETGSM_USERCODE`, `NETGSM_PASSWORD`, `NETGSM_MSGHEADER`. Paylaşılan pod bu üç değişken doluysa açılmaz. Böylece bir firmanın başlığı diğer firmaların SMS’ine yazılmaz. Eksik hesapta yalnızca o firmanın SMS’i çıkmaz. Metin firma kısa adıyla başlar. Değerler ekrana geri açılmaz.

Uyarı kodları ve eşikler [iş kurallarında](is-kurallari.md) listelenir.

### İz ve açıklama

- FR-9.1 Atama, iptal, tonaj düzeltmesi, dosya içe aktarımı, kural paketi değişikliği, uyarı kapatma ve SMS kabulü kim tarafından ya da hangi iş tarafından, ne zaman yapıldığını saklar.
- FR-9.2 Bir plan yeniden hesaplandığında, hesabın girdiği konum, takograf özeti, mesafe ve kural paketi planla birlikte durur. Ekrandaki açıklama sonradan değişen fiyatla yeniden yazılmaz.

## 7. Veri ihtiyaçları

Firma başına tutulan ana kayıtlar: kullanıcı, araç, sürücü, sağlayıcı hesabı, yük, sefer ataması, takograf özeti, uyarı, SMS kuyruğu, içe aktarma sonucu, denetim kaydı.

Konum geçmişi, plan hesabı için son konumu ve son seferin izini tutacak kadar saklanır. Ham sağlayıcı cevabı, adaptör arızasını çözmek için sınırlı süre tutulur. Saklama süresi firma ayarıdır; başlangıç değeri 90 gündür.

Entegrasyon parolası ve PIN ekrana geri açılmaz. Yazılı halde şifreli durur.

## 8. Entegrasyon ihtiyaçları

Ortak anlık görüntü alanları: sağlayıcı, cihaz kimliği, plaka, enlem, boylam, hız, yön, kontak, ölçüm zamanı. Varsa kilometre, brüt ağırlık, sürücü kartı ve takograf sayaçları.

Arvento bağlantısı SOAP 1.1’dir. Adres `https://ws.arvento.com/v1/report.asmx`, sözleşme `report.asmx?WSDL`, ad alanı `http://www.arvento.com/`. Konum `GetVehicleStatusV4` ile alınır. Bu pakette enlem, boylam, hız, yön, plaka, cihaz kimliği ve sinyal zamanı vardır. Kontak yoktur. Takograf ve kontak `CANBUSTachographLastStatus` ile `TachographActiveFleetReport` içindedir. İkisinin cevap şeması `DataSet` olduğu için kolon adları örnek cevapla eşlenir. `CanBusEmptyInfo` tonaj sözleşmesi taşımaz. Ağırlık kolonu örnekte yoksa tonaj sefer kaydından gelir.

Seyir’in kamuya açık bir servis sözleşmesi bulunamadı. İlk sürüm Seyir adaptörünü aynı anlık görüntüye bağlar. Uç adres, kimlik doğrulama ve alan adları firmanın Seyir sözleşmesinden alınır. Sözleşme gelmeden Seyir adaptörü canlı veri çekmez; ekran ve kurallar Arvento veya elle girilen konumla çalışır.

Adres çözümü ve yol mesafesi Google Maps ile alınır. Adres, il ve ilçe sözlüğünden geçtikten sonra Geocoding API ile koordinata çevrilir. Boş ve dolu kilometre ile sürüş süresi, Routes API rota matrisinden gelir. Canlı trafik plana katılmaz. Aynı girdi aynı süreyi versin diye süre, trafiksiz sürüş süresidir. Google cevap vermezse kuş uçuşu mesafe 1,3 ile çarpılarak yalnızca taslak sıralama yapılır ve sonuç `yaklaşık` işaretlenir. Yaklaşık mesafe, otomatik dönüş atamasını kesinleştirmez. Operasyon haritası Maps JavaScript API ile çizilir. Sunucu anahtarı ile tarayıcı anahtarı ayrıdır.

Rota SMS’i Netgsm REST v2 ile gider: `POST https://api.netgsm.com.tr/sms/rest/v2/send`. Kimlik, HTTP Basic ile kullanıcı kodu ve API şifresidir. Gövde onaylı `msgheader`, Türkçe `encoding` ve alıcı listesi taşır. İletim sonucu `POST /sms/rest/v2/report` ile iş kimliğinden okunur. Mesaj, firmanın kendi şoförüne giden operasyon duyurusudur. Ticari pazarlama gönderimi değildir. `iysfilter` bu nedenle kapalıdır. Başlığın Netgsm’de onaylı olması canlı gönderimin koşuludur.

## 9. Başarı ölçütleri

İlk firma pilotunda bakılacaklar:

- İçe aktarılan gidiş dosyasında geçerli satırların tamamı kuyruğa iner, hatalı satırın nedeni dosyada görünür.
- Kapasiteyi, dorse tipini veya takografı aşan hiçbir çift atanamaz. Buna dönük denemeler otomatik testte kırmızı olur.
- Dönüş havuzunda, aynı girdiyle tekrarlanan hesap aynı eşleşmeyi üretir.
- Operasyoncu, atamanın boş kilometresini, net faydasını ve elenme gerekçesini ek bir hesap yapmadan okur.
- Konum sinyali eşiği aşınca araç planlanabilir listesinden çıkar ve uyarı açılır.
- İki firmanın verisi çapraz sorguda birbirine karışmaz.
- 100 araç ve 100 fırsatta eşleşme hesabı 10 saniyenin altında biter. Bu süre, elemeden sonra kalan Google mesafe çağrılarının önbellekli olduğu duruma aittir.
- `atandi` olan her sefer için tek bir atama SMS’i kuyruğa yazılır. Netgsm kabulü atamayı kilitler. Aynı olay ikinci SMS üretmez.

İş sonucu, pilotun ilk ayında boş kilometresinin ve süresinde yetişen teslimat oranının firma bazında raporlanmasıdır. Hedef oran sözleşme sırasında firmayla konur; ürün hedefi bu raporu üretebilmektir.

## 10. Varsayımlar

- Taşıma komple tırdır. Bir seferde bir yük vardır.
- Araçta bir sürücü vardır.
- Gidiş yükünün aracı operasyoncu tarafından seçilir. Sistem adayları sıralar.
- Dönüş ataması otomatiktir. Havuzdaki kayıt bir fırsattır ve navlunu girişte bellidir. Onay adımı firma isterse açılır.
- İlk müşterinin tırları tentelidir. Her aracın kapasitesi 24 veya 25 tondur. Ürün kataloğu tenteli, frigolu, sal, lowbed ve tankeri de taşır. Firma kullandığı tipleri açar.
- Adres ve yol mesafesi Google Maps’tir.
- Yasal sınır, Karayolu Taşıma Yönetmeliği madde 35’in zorunlu tuttuğu AETR’dir. Türkiye içi sefer de bu pakete tabidir.
- Fayda hesabının birimi Türk lirası ve kilometredir.
- Şoföre mobil uygulama yoktur. Yük ve rota Netgsm SMS’i ile gider.
- Atama, Netgsm gönderimi kabul edip iş kimliği dönünce kilitlenir. Telefona ulaştığı raporu kilit için beklenmez. Operasyoncu ayrıca “bildirildi” işareti koymaz.

## 11. Açık noktalar

Bunlar belgeyi bekletmez. Adaptörün canlıya çıkmasını bekletir.

| No | Soru | Durum |
| --- | --- | --- |
| A-1 | Pilot Arvento hesabında takograf ve CAN ağırlığı dolu mu? | Ertelendi. Metotlar WSDL’de var, kolonlar `DataSet` içinde. Örnek cevap gelene kadar takograf `tahmini`, tonaj sefer kaydındandır. |
| A-2 | Seyir servisinin adresi, kimlik yöntemi ve örnek cevabı nedir? | Ertelendi. Şirketten talep edilecek. Sözleşme gelmeden Seyir canlı veri çekmez. |
| A-3 | Dönüş navlunu havuza girerken biliniyor mu? | Kapandı. Dönüş kaydı fırsattır, navlunuyla girer. Uygun tır, dönüşte bu navlunla otomatik eşleşir. |
| A-4 | Dorse tipleri nelerdir? | Kapandı. Katalog: tenteli, frigolu, sal, lowbed, tanker. İlk müşterinin tamamı tenteli ve 24 veya 25 ton. |
| A-5 | Adres ve yol mesafesi hangi hizmetten gelir? | Kapandı. Google Maps. Geocoding, Routes API ve harita için Maps JavaScript API. |
| A-6 | Netgsm başlığı nerede durur? | Kapandı. Her firmanın kendi hesabı vardır. Ayrı podda ortam değişkeni, paylaşılan podda şifreli firma kaydıdır. Repoda değer yoktur. |

## 12. Kaynaklar

- Karayolu Taşıma Yönetmeliği madde 35. Şoförlerin çalışma ve dinlenme süreleri AETR’ye bağlıdır. 15 Mayıs 2025 tarihli ve 32901 sayılı değişiklik, kart ve takograf manipülasyonu için yaptırım ekler. Resmi metin: [mevzuat.gov.tr](https://www.mevzuat.gov.tr/MevzuatMetin/yonetmelik/7.5.24299.pdf).
- AETR sürüş, mola ve dinlenme uygulaması için 2026 özeti: günlük 9 saat (haftada iki kez 10), haftalık 56 saat, ardışık iki hafta 90 saat, 4,5 saat sonra 45 dakika mola. [SGK sirküleri 2026-041](https://www.denet.com.tr/vergi/dosyalar/sirkuler/SGKSIRK2026-041.pdf).
- 20 Temmuz 1999 tarihli ve 4411 sayılı kanunun ekindeki AETR nüshası daha eski sınırlar içerir. Kural paketi o nüshadaki on beş günlük hesaba değil, yukarıdaki güncel uygulamaya göre kurulur. Üretim kapısında konsolide metinle teyit edilir.
- Arvento rapor servisi, SOAP 1.1: [ws.arvento.com/v1/report.asmx](https://ws.arvento.com/v1/report.asmx). WSDL: [report.asmx?WSDL](https://ws.arvento.com/v1/report.asmx?WSDL). Konum `GetVehicleStatusV4`, takograf `TachographActiveFleetReport` ve `CANBUSTachographLastStatus`.
- Netgsm SMS REST v2: [netgsm.com.tr/dokuman](https://www.netgsm.com.tr/dokuman). Gönderim `POST /sms/rest/v2/send`, iletim raporu `POST /sms/rest/v2/report`.
- Google Geocoding API, Routes API rota matrisi ve Maps JavaScript API. Planlama süresi trafiksiz sürüş süresidir.
