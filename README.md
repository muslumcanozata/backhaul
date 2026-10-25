# Backhaul

Türkiye içi karayolu taşımacılığı yapan firmalar için çok kiracılı tır planlama ürünü. Gidiş yükleri toplu girilir. Dönüş yükleri havuzdan, takograf sınırları ve boş kapasite içinde en yüksek faydayı verecek araca otomatik atanır. Araç konumu ve sürücü verisi Arvento ile Seyir üzerinden gelir. Kesinleşen yük ve rota şoföre Netgsm SMS’i ile gider.

## Dokümanlar

| Doküman | İçerik |
| --- | --- |
| [İş gereksinimleri](docs/brd.md) | Amaç, kapsam, roller, gereksinimler, başarı ölçütleri |
| [İş kuralları](docs/is-kurallari.md) | Müsaitlik, tonaj, takograf kural paketi, uyarılar, fayda hesabı |
| [Mimari ve teslimat](docs/mimari-ve-teslimat.md) | Monorepo, entegrasyonlar, fazlar, üretim kapıları |

Uygulama iskeleti bu dokümanlar gözden geçirildikten sonra kurulur: `apps/api` (FastAPI) ve `apps/web` (Vite, React, TypeScript).

## Kilitlenen kapsam

- Çok kiracılı ürün. Her kiracı bir nakliye firmasıdır.
- Coğrafya Türkiye içidir. Sürüş ve dinlenme sınırları, Karayolu Taşıma Yönetmeliği madde 35 üzerinden AETR kural paketine bağlanır.
- Bir araçta aynı anda tek yük ve tek sürücü vardır.
- Gidiş atamasını operasyoncu yapar. Dönüş atamasını sistem yapar.
- Şoföre mobil uygulama yoktur. Rota bildirimi Netgsm SMS’idir.
