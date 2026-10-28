# Backhaul

Türkiye içi karayolu taşımacılığı yapan firmalar için çok kiracılı tır planlama ürünü. Gidiş yükleri toplu girilir. Dönüş yükleri navlunu belli fırsat olarak havuza girer ve uygun tıra otomatik atanır. Araç konumu ve sürücü verisi Arvento ile Seyir üzerinden gelir. Adres ve yol mesafesi Google Maps’tedir. Kesinleşen yük ve rota şoföre Netgsm SMS’i ile gider.

## Dokümanlar

| Doküman | İçerik |
| --- | --- |
| [İş gereksinimleri](docs/brd.md) | Amaç, kapsam, roller, gereksinimler, başarı ölçütleri |
| [İş kuralları](docs/is-kurallari.md) | Müsaitlik, tonaj, takograf kural paketi, uyarılar, fayda hesabı |
| [Mimari ve teslimat](docs/mimari-ve-teslimat.md) | Monorepo, entegrasyonlar, fazlar, üretim kapıları |
| [MVP](docs/mvp.md) | İlk yayının sınırı, dilimleri ve kabul ölçütleri |
| [Arayüz](docs/arayuz.md) | Sefer masası, sicil kabuğu, sayfalar ve rol sınırları |
| [İş akışları](docs/workflow.md) | UI senaryoları, Mermaid UML diyagramları |

Uygulama `apps/api` (FastAPI) ve `apps/web` (Vite, React, TypeScript) altındadır. İlk dilim firma, kullanıcı, araç ve pod izolasyonudur.

```bash
cd apps/api && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env   # JWT_SECRET ve SECRETS_KEY doldurulur
make test
make api
```

## Kilitlenen kapsam

- Çok kiracılı ürün. Her kiracı bir nakliye firmasıdır. Aynı imaj, firmanın kendi podunda veya birçok firmanın paylaştığı podda çalışır. Veri ve entegrasyon hesapları iki biçimde de ayrıdır.
- Coğrafya Türkiye içidir. Sürüş ve dinlenme sınırları, Karayolu Taşıma Yönetmeliği madde 35 üzerinden AETR kural paketine bağlanır.
- Bir araçta aynı anda tek yük ve tek sürücü vardır.
- Gidiş atamasını operasyoncu yapar. Dönüş fırsatını sistem, navlun ve yol mesafesine göre atar.
- İlk müşterinin tırları tentelidir. Kapasite araç başına 24 veya 25 tondur.
- Şoföre mobil uygulama yoktur. Rota bildirimi Netgsm SMS’idir.
