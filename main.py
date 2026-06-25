"""
main.py
-------
Uygulamanın giriş noktası (entry point).

Bu dosyanın TEK görevi:
1. FastAPI uygulamasını oluşturmak (Swagger/ReDoc dokümantasyonu ile).
2. Uygulama açılırken veritabanını hazırlamak (tabloları oluşturmak).
3. Entity router'larını toplamak (include_router) — şimdilik hiç yok.

KURAL: Endpoint'ler burada YAZILMAZ. Her entity'nin kendi router dosyası
(routers/ altında) olur. main.py sadece "montaj" yapar.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db


# lifespan: Uygulamanın yaşam döngüsünü yönetir.
# "yield" satırından ÖNCEKİ kod uygulama AÇILIRKEN bir kez çalışır.
# "yield" satırından SONRAKİ kod uygulama KAPANIRKEN çalışır.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Uygulama açılışında ---
    # Veritabanı tablolarını oluştur (zaten varsa dokunmaz).
    init_db()

    yield  # <-- Uygulama bu noktada çalışmaya başlar ve istekleri karşılar.

    # --- Uygulama kapanışında ---
    # Şimdilik kapanışta yapılacak bir temizlik yok.


# FastAPI uygulama nesnesini oluştur.
# title/description/version değerleri Swagger UI'da (/docs) başlıkta görünür.
app = FastAPI(
    title="E-Learning API",
    description=(
        "Udemy benzeri bir e-learning platformunun backend API'si.\n\n"
        "SQLite + FastAPI + Pydantic ile geliştirilmiştir (ORM kullanılmaz).\n\n"
        "Dokümantasyon: Swagger UI -> /docs , ReDoc -> /redoc"
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get(
    "/",
    tags=["Health"],
    summary="Sağlık kontrolü (health check)",
    description=(
        "API'nin ayakta olup olmadığını kontrol eder. "
        "Herhangi bir iş kuralı uygulamaz; sadece servisin yanıt verdiğini gösterir."
    ),
)
def health_check():
    """
    Basit sağlık kontrolü endpoint'i.
    API çalışıyorsa {"status": "ok"} döner ve dokümantasyon adresini bildirir.
    """
    return {"status": "ok", "docs": "/docs", "redoc": "/redoc"}


# -----------------------------------------------------------------------------
# ROUTER'LAR
# -----------------------------------------------------------------------------
# Her entity'nin router'ı hazır oldukça buraya eklenir:
#   from routers import <entity>         # router dosyasını içe aktar
#   app.include_router(<entity>.router)  # endpoint'lerini uygulamaya bağla

from routers import languages  # LANGUAGES entity router'ı (Adım 3)
from routers import roles  # ROLES entity router'ı (Adım 2)

app.include_router(roles.router)
app.include_router(languages.router)
