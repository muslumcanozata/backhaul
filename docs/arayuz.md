# Arayüz planı

Sürüm: 0.2  
Tarih: 25 Ekim 2026

Bu belge ekranları, her ekrandaki işi ve rol sınırını tanımlar. İş kuralları [iş kurallarında](is-kurallari.md), ilk yayının sınırı [MVP planında](mvp.md) durur. Menüde görünen bir düğme yetki değildir. API, rolün yapamayacağı isteği 403 ile keser. Başka firmanın kaydı 404 döner. Ayrı pod başka firma kimliğini reddeder.

## 1. Kabuk

Görsel kabuk, MUI Store’daki ücretsiz [Minimal](https://mui.com/store/items/minimal-dashboard-free/) sürümüdür (`material-kit-react`, MIT). Demo sayfaları, grafik, arama, bildirim ve Pro satış kutusu alınmaz. Tema, 280 piksel açık yan menü, üst çubuk, kart, düğme ve ortadaki giriş formu Vite uygulamasına taşınır.

Menü maddeleri, roller ve sayfa işleri bu belgede kalır. Şablonun Overview, Customers ve Integrations maddeleri kullanılmaz.

İki kabuk vardır. Platform yöneticisi sefer masasını açamaz. Firma kullanıcısı firma sicilini açamaz. Aynı görsel kabuğun içinde, rolün göremeyeceği madde rayda durmaz.

**Sicil.** Platform yöneticisinin sayfaları. Firma listesi ve firma dosyası karttadır. Harita, yük ve şoför SMS’i bu kabukta yoktur.

**Sefer masası.** Firma sayfaları. Gün üç kartta durur: gidiş kuyruğu, son konum, dönüş havuzu. Üstte boş araç, bakım, sinyal ve şoförsüz sayıları ayrı kartlardadır. Satır seçilince sağdan dosya çekmecesi açılır. Masa kaybolmaz. Durumlar sözcükle yazılır: boş, yüklü, boşalacak, bakımda, arıza.

İzleyici yazma düğmelerini görmez. Operasyoncu ayar ve kullanıcı sayfalarını görmez.

## 2. Sayfalar

### Sicil / Firmalar

Platform yöneticisi.

- Firma listesi: ad, kod, durum, son başarılı Arvento çekimi, açık kritik uyarı sayısı. Uyarı sayısı vardır, uyarı metni ve yük yoktur.
- Firma açma ve askıya alma. Askıdaki firmanın kullanıcısı operasyon yapamaz.
- Firma dosyası: kullanıcı ekleme, rol, erişimi kapatma. Netgsm ve Arvento için yalnızca “kayıtlı” veya “eksik”. Sır değeri gösterilmez ve forma geri yazılmaz.

MVP’de açma, liste ve kullanıcı ekleme vardır. Askıya alma ve çekim sağlığı M2’den sonra aynı sayfaya eklenir.

### Sicil / Sağlık

Platform yöneticisi. Sonraki sürüm.

- Pod biçimi, başarısız Arvento ve Netgsm işlerinin firma bazında sayısı.
- Yük, plaka ve SMS metni bu sayfada yoktur.

### Özet (Masa)

Firma yöneticisi, operasyoncu ve izleyici okur. Operasyon yazma, kuyruk sayfalarındadır.

- Üst KPI: boş araç, gidiş kuyruğu, dönüş havuzu, açık uyarı.
- Grafikler: filo müsaitliği, yük durumu dağılımı, dönüş faydası.
- Canlı harita ve yaklaşan gidiş / dönüş özet listeleri.
- Gidiş ve dönüş sayfalarına kısayol.

### Takip

Üç firma rolü okur. Yazma yoktur. Platform yöneticisi bu sayfayı açamaz.

- Google haritasında firmanın bütün araçları. Anahtar yoksa Türkiye taslağı aynı soket verisini gösterir.
- Bağlantı WebSocket `/live` üzerindedir. Açılışta son konumlar gelir. Elle konum ve Arvento çekimi aynı firma odasına yeni noktayı yazar.
- Liste plaka, şoför, hız ve sinyal yaşını gösterir. Satır seçilince harita o araca kayar.

### Araçlar

Liste firma yöneticisi, operasyoncu ve izleyiciye açıktır. Ana veriyi firma yöneticisi yazar. Elle konum ve tonaj düzeltmesini operasyoncu da yapar.

- Liste: plaka, kasa, kapasite, durum, şoför, son sinyal yaşı, müsaitlik.
- Müsait değilse gerekçe görünür: bakım, arıza, bayat sinyal, şoför yok, üzerinde iş var.
- Dosya: plaka, kapasite, dara, kasa, cihaz kimliği, bağlı şoför, son konum, hız, yön, açık sefer, takograf özeti, son SMS.
- Durum değiştirme: serviste, bakımda, arıza.
- Sonraki sürümde aynı dosyaya aks ağırlığı ve rota sapması eklenir. MVP’de bu alanlar yoktur.

### Şoförler

Liste üç firma rolüne açıktır. Kayıt firma yöneticisinindir.

- Liste: ad, telefon, kart, bağlı araç.
- Dosya: telefon, takograf kartı, bugünkü sürüş özeti, bu şoföre giden son SMS’ler ve iletim durumu.
- Operasyoncu SMS’i buradan da yeniden gönderir. Şoför ekleyemez.

### Gidiş kuyruğu

Operasyoncu ve firma yöneticisi yazar. İzleyici okur.

- Tablo: referans, rota, tonaj, hazır zamanı, durum.
- Tek satır ekleme formu. Excel içe ve dışa aktarma. Şablon indirme.
- Satır seçince dosya paneli: uygun araçlar, atama, iptal, yer güncelleme.
- Kuyruktan çıkarma atanmamış veya atanmış satırı iptal eder.

### Dönüş havuzu

Aynı yazma sınırı gidişle aynıdır. Onay modu kapalıyken sistem atar. Onay açıksa operasyoncu öneriyi onaylar.

- Tablo: navlun, fayda, aracı firma, durum. Navlunsuz satır forma girmez.
- Excel içe/dışa aktarma, tek satır ekleme, Hesapla.
- Fırsat dosyası: fayda kırılımı, takograf, elenen adaylar, SMS.

### Bildirimler (üst çubuk)

Üç firma rolü okur. Menüde ayrı Uyarılar sayfası yoktur. Üst çubuktaki zil ikonu açılır.

- Rozet: okunmamış uyarı sayısı.
- Liste: seviye, kod, araç, ölçülen / sınır. Operasyoncu ve firma yöneticisi Görüldü işaretler.
- Kapanış, koşul düzelince kendiliğinden olur. Şoföre SMS gitmez.

### Ayarlar

Yalnızca firma yöneticisi. Operasyoncu ve izleyici sayfayı görmez.

- Açık kasa tipleri. Katalog: tenteli, frigolu, sal, lowbed, tanker.
- Boş ve dolu kilometre maliyeti.
- Şirket takograf limiti. Yasal paketten büyük değer kaydedilemez.
- Tahmini takografla otomatik dönüş bayrağı. Başlangıç kapalı.
- Dönüş atamasında onay isteme. Başlangıç kapalı, yani atama otomatik.
- Entegrasyon durumu: Arvento son başarılı çekim, Netgsm üçlüsü kayıtlı mı. Değer gösterilmez.
- Sonraki sürümde e-posta uyarısı ve Seyir bağlantısı bu sayfaya eklenir.

### Kullanıcılar

Firma yöneticisi kendi firmasının operasyoncu ve izleyicisini ekler, rolünü değiştirir, erişimi kapatır. Platform yöneticisi de firma dosyasından aynı işi yapar. Operasyoncu kullanıcı açamaz.

### Denetim

Firma yöneticisi okur. Sonraki sürümde izleyici de okur. Operasyoncu bu sayfayı görmez.

- Atama, iptal, tonaj düzeltmesi, dosya, ayar, SMS kabulü ve uyarı kapatma.
- Satır: kim, ne zaman, eski ve yeni değer. SMS numarası maskeli dışa aktarılır.

### Raporlar

Sonraki sürüm. İzleyici dahil üç firma rolü okur. Yazma yoktur.

- Firma bazında boş kilometre, atanan fırsat sayısı, süresinde teslim.
- Başka firmanın toplamı yoktur.

## 3. Rol sınırı

| Sayfa | Platform | Firma yöneticisi | Operasyoncu | İzleyici |
| --- | --- | --- | --- | --- |
| Firmalar, sağlık | Yazar | Yok | Yok | Yok |
| Özet, gidiş, dönüş | Yok | Yazar | Yazar | Okur |
| Bildirimler (üst çubuk) | Yok | Yazar | Yazar | Okur |
| Takip | Yok | Okur | Okur | Okur |
| Araç ve şoför ana verisi | Yok | Yazar | Okur | Okur |
| Elle konum, tonaj düzeltmesi, SMS yeniden gönder | Yok | Yazar | Yazar | Yok |
| Ayarlar, kullanıcılar | Firma dosyasında yazar | Yazar | Yok | Yok |
| Denetim | Yok | Okur | Yok | Sonraki sürümde okur |
| Raporlar | Yok | Okur | Okur | Okur |

Firma yöneticisi operasyon sayfalarında operasyoncu ile aynı işi yapar. Ek olarak ayar, kullanıcı ve denetim açar. Platform yöneticisinin belirteci `/vehicles`, `/loads` ve `/alerts` üzerinde 403 alır.

## 4. MVP’de kurulacak ekran sırası

M1’deki geçici formlar bu kabuğun yerini alır.

1. M1 kapanırken sicil kabuğu: firmalar, firma dosyası, kullanıcı. Sefer masasında araç ve şoför listesi, ayarlar. Rol dışı sayfa ve düğme görünmez.
2. M2 masa iskeleti: gidiş kuyruğu, harita, yük dosyası, içe aktarma sonucu.
3. M3 uyarı listesi ve araç dosyasındaki takograf özeti.
4. M4 dönüş sütunu, fayda paneli, SMS durumu.

Denetim, raporlar, sağlık ve Seyir alanı bu sıranın dışındadır. Sayfadaki yerleri yukarıda sabittir. İlk yayında rayda durmazlar.
