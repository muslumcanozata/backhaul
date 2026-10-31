# Dönüş rotası planlayıcı: kararlar, varsayımlar, açık noktalar

Sürüm: 0.4  
Tarih: 31 Ekim 2026

Kural dosyaları: `.cursor/rules/return-routing-*.mdc` ve `.cursor/rules/aetr-tachograph.mdc`. Bu belge onların dayandığı kararları tutar. Kod, varsayımı buradan okur. Koda gömmez.

## 1. Kararlar

Kullanıcıdan gelen kararlar. Değişirse önce burası değişir.

| # | Karar |
| --- | --- |
| K-1 | Tüm tenantlarda takograf kuralı AETR (`TR-AETR-2026`). Tenant bazlı kural seçimi yok. |
| K-2 | Bağlayıcı kapasite birimi ton. Desi kararı geri alındı. |
| K-3 | Dönüşte navlun zorunlu. |
| K-4 | Çok duraklı dönüş rotası uygulanır. |
| K-5 | Gidişte en fazla 2 durak (boşaltma noktası). Dönüşte en fazla 3 durak (yükleme noktası), yani en fazla 3 ardışık yük. Her yük bir yükleme ve bir boşaltma noktasıdır. Teyit edildi. |
| K-6 | Karar ölçütü verimlilik ve takograf uyumu. |
| K-7 | Tüm tenantlar Arvento ve Seyir takograf verisine yetkili. |
| K-8 | Planlayıcı genel, çok kiracılı. Hiçbir firmaya özel kodlanmaz. |
| K-9 | Prompt Cursor kuralı olarak projede durur. |
| K-10 | Bir durakta tek yük alınır. Araçta yük varken başka yük alınmaz. Yük boşaltıldıktan sonra yeni yük alınabilir. Yük birleştirme yoktur. |
| K-11 | Yasal yük sınırı, tırın ton kapasitesidir (`capacity_tons`). Ayrı brüt ağırlık veya dara kontrolü yok. |
| K-12 | Köprü ve otoyol ücreti Routes API'den gelir. Bunun getirdiği Google maliyeti kabul edildi. |
| K-13 | Yakıt, sürücü, bakım gibi giderler tenant ayarındaki km başına maliyetten hesaplanır. |
| K-14 | Manuel plana kıyas (`compare_with_manual`) 2. faza ayrıldı. |
| K-15 | Kasa tipi kataloğu yeterli (tenteli, frigolu, sal, lowbed, tanker). |
| K-16 | Mola konumu önerilmez. Planlayıcı takograf kalan süresine göre sürücüye zaman tavsiyesi verir. |
| K-17 | Routes API geçiş ücretine şimdilik güvenilir. Yetersiz çıkarsa sonra çözüm üretilir. |
| K-18 | Planlama gidiş yükü tamamen boşaltıldıktan sonra başlar. Dönüş üste (Ordu gibi) bitecek şekilde planlanır. Son dönüş yükünü üste boşaltmak zorunlu değil. Yük boşaltılıp kârlı dönülmesi yeterli. |
| K-19 | Yükler netleştikçe ve onaylanıp kilitlendikçe sürücüye SMS gider. Kilitsiz yükler öneri kalır. |
| K-20 | Gidiş planı Excel'i plaka, sürücü, çıkış zamanı, durak 1, durak 2 ve tahmini varışı taşır. Tır ataması dosyadan gelir. |
| K-21 | Planlamada öncelik tasarruf ve takograf verimliliğidir. |
| K-22 | Routes API'ye gereksiz para harcanmaz. Geçiş ücreti `toll_enabled` ile açılır, varsayılan kapalıdır. Zincir devam değerlendirmesi yaklaşık mesafeyle yapılır, Routes çağrısı yapmaz. Testler ağa çıkmaz. |

## 2. Varsayımlar

Benim yorumum. Onayla ya da düzelt.

| # | Varsayım | Etki |
| --- | --- | --- |
| V-2 | Gidişteki 2 durak sınırı girdi doğrulamasıdır. Gidiş planı değiştirilmez, aşan satır veri uyarısı olur. | Gidiş planı sabit kalır. |
| V-3 | Kapasite yük başınadır: `yük.tonnage ≤ araç.capacity_tons`. Aks bazlı ağırlık kapsam dışı. | Şema değişmez. |
| V-4 | Yükte tonaj yoksa satır eksik veri sayılır ve rotaya alınmaz. `capacity_tons` boş veya sıfırsa tır aday olmaz. | Eksik veri sessizce geçilmez. |
| V-5 | Zincirde yük sırası çözücünün parçasıdır. Her yükün alma zamanı, bir önceki yükün boşaltma varışı ve molalarla belirlenir. | Zincir üretimi mesafe matrisi çağrısını artırır. Aday budama gerekir. |
| V-6 | Planlayıcı `apps/api/app/routing/` altında modüldür. Ayrı `agent/` paketi yok. | Mevcut FastAPI yapısıyla uyumlu. |
| V-7 | Hedef sırası: sert kısıt, sonra fayda (TL), sonra düşük boş km, sonra yüksek ton doluluğu. | Çatışmada fayda öncelikli. |
| V-8 | Teknik doküman Türkçe, kod tanımlayıcıları İngilizce. | Projenin mevcut düzeni. |
| V-9 | "Takograf" yazımı kullanılır. "Tapograf" değil. | Kod ve çıktıda tek biçim. |
| V-10 | Takograf yetkisi var sayıldığı için ölçülmüş sayaç esastır. Sürücü eşleşmezse veya veri gelmezse sayaç `tahmini` kalır ve uyarı çıkar. | Mevcut `tahmini_ile_otomatik_atama` bayrağı korunur. |
| V-11 | Geçiş ücreti bilinmiyorsa 0 sayılmaz. Çift "ücreti bilinmiyor" işaretlenir ve otomatik atamaya alınmaz. | Ücret yoksa yapay olarak kârlı görünen rota seçilmesin diye. |
| V-12 | Fayda formülü: `Σ navlun − Σ (boş km × boş maliyet + dolu km × dolu maliyet) − Σ geçiş ücreti`. Bekleme ve konaklama maliyeti yok. | Bekleme maliyeti istenirse ayara yeni katsayı gerekir. |
| V-14 | Üs noktası tenant ayarıdır: yeni `home_base` (il, ilçe veya koordinat). Çamsan için Ordu, başka firma için başka şehir. Koda Ordu gömülmez. Tanımsızsa zincir son boşaltmada biter ve uyarı çıkar. | Ayar ekranı ve `TenantSettings`'e alan eklenir. |
| V-15 | Üse boş dönüş bacağı fayda formülündeki boş km'ye ve takograf kontrolüne girer. Üse dönüş durak sayılmaz. | Üsten uzak ama navlunu yüksek yük, boş dönüş maliyetiyle birlikte değerlendirilir. |
| V-16 | Yalnız ilk yük atanır. Devam yükleri öneri olarak kalır (`chain_note`), ilk yük kilitlenince sıradaki yük aynı araca atanır ve SMS'i o zaman gider. Planlama ufku sabit değil, zincir en fazla 3 yük ve takograf süresiyle sınırlı. | Mevcut `return_approval` ve SMS akışı yük bazında çalışır. Uygulandı. |
| V-17 | Yükleme ve boşaltma süresi zincir zamanlamasına girmez. Bekleme dinlenme sayılmaz. Günlük dinlenme 11 saat alınır. | Zincir temkinli çıkar. |
| V-18 | Üs noktası tanımsızsa uyarı üretilmez, zincir son boşaltmada biter. Ayar ekranı bunu yazar. | Uyarı kodu gerekirse eklenir. |
| V-13 | Sürücü tavsiyesi saf zaman ifadesidir: "N saat sonra 45 dk mola", "günlük sürüşe X saat kaldı", "bu bacaktan sonra günlük dinlenme gerekir". Tavsiye yük kartında (`driver_advice`) görünür. Excel dışa aktarımına eklenmedi, çünkü mevcut dışa aktarım yeniden içe aktarılabilir biçimde. SMS'e eklenmez. | SMS metni mevcut hatta kalır. |

## 3. Açık noktalar

Cevap gelmeden ilgili kısım uygulanmaz veya varsayılanla kalır.

| # | Soru | Neden önemli |
| --- | --- | --- |
| O-3 | Routes geçiş ücreti uygulama sırasında gerçek çağrıyla doğrulanır. Binek araç varsayımı ve Türkiye kapsamı belirsiz (K-17 ile şimdilik güvenilir). Ücret dönmezse V-11 devreye girer ve çözüm sonra üretilir. | Fayda hesabının bir bileşeni. |
| O-11 | Seyir takograf alanlarının birimi ve seçimi (`remaining_drive_period` mi, `not_used_drive_period` mi) gerçek cevapla doğrulanacak. | Yanlış alan sürüş payını bozar. |
| O-12 | `TR-AETR-2026` değerleri konsolide resmi metinle karşılaştırılacak. | Kural belgesi bunu üretim öncesi şart koşuyor. |

Kapananlar: maliyet katsayıları (K-13), durak sayımı (K-5), yasal yük sınırı verisi (K-11), Google maliyeti (K-12), manuel plan şeması ve kıyas (K-14, 2. faza), mola konumu (K-16), kasa tipi (K-15), desi (K-2).

## 4. 2. faza ayrılanlar

- Manuel plana kıyas: km, doluluk ve maliyet/kâr farkı. Manuel planın Excel şeması bu fazda belirlenir.

## 5. Uygulama durumu

Yapıldı: tek yük zinciri (öneri ve rolling atama), `STOP_LIMIT`, `WINDOW`, üs noktası ve üse dönüş maliyeti, opt-in geçiş ücreti (Routes `TOLLS`, ağa çıkmadan test edildi), takograf simülasyonu ve sürücü tavsiyesi, ayar ve kart alanları.

Yapılmadı: gidiş planı Excel şablonu (K-20) ve gidişte 2 durak doğrulaması, Arvento takograf adaptörü, Excel dışa aktarımda tavsiye, canlı Routes ile geçiş ücreti doğrulaması (para harcanmaması için).

## 6. Bağımlılıklar ve etkilenen yerler

Uygulama başlayınca güncellenecekler:

- **Şema:** kapasite ve yasal yük için yeni alan gerekmez (`capacity_tons`, `tonnage` var).
- **`docs/is-kurallari.md`:** "her araca en fazla bir yük" kuralı (Eşleştirme, madde 4) ardışık zincirle değişir. Eşzamanlı yük hâlâ yok. Durak sınırı eklenir.
- **Routes entegrasyonu (`apps/api/app/geo.py`):** `extraComputations: ["TOLLS"]`, `travelAdvisory.tollInfo` alan maskesi, yol önbelleğinde ücret sütunu, TRY para birimi.
- **Excel şablonu:** Gidiş planı için yeni şablon: plaka, sürücü, çıkış zamanı, durak 1, durak 2, tahmini varış. Mevcut yük şablonunda tonaj kolonu zaten var.
- **Tenant ayarı:** `home_base` alanı (V-14), ayar ekranı ve API.
- **SMS hattı:** Yük bazlı kilitte SMS (V-16). Mevcut atama hattı tek yük için çalışıyor. Zincirde sıradaki yük kilitlenince tetiklenmesi gerekir.
- **Arvento takograf adaptörü:** henüz yok. K-7 Arvento'da ancak bu adaptör yazılınca ölçülmüş sayaç verir.
- **Mevcut dönüş çözücü:** `returns.py`, `planning.py` ve `matching.py` tek yüklü eşleştirmeyi çözüyor. Zincir bunun üstüne kurulur.
