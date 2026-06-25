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

from fastapi import Depends, FastAPI

from auth_deps import require_role
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

from routers import auth  # AUTH (login) router'ı (Adım 24)
from routers import blacklist  # BLACKLIST router'ı (Adım 9)
from routers import cart_items  # CART_ITEMS router'ı (Adım 16)
from routers import carts  # CARTS router'ı (Adım 15)
from routers import categories  # CATEGORIES router'ı (Adım 6)
from routers import course_instructors  # COURSE_INSTRUCTORS router'ı (Adım 13)
from routers import courses  # COURSES router'ı (Adım 10)
from routers import difficulty_levels  # DIFFICULTY_LEVELS router'ı (Adım 4)
from routers import languages  # LANGUAGES entity router'ı (Adım 3)
from routers import order_items  # ORDER_ITEMS router'ı (Adım 18)
from routers import orders  # ORDERS router'ı (Adım 17)
from routers import payment_methods  # PAYMENT_METHODS router'ı (Adım 5)
from routers import payment_statuses  # PAYMENT_STATUSES router'ı (Adım 5)
from routers import payments  # PAYMENTS router'ı (Adım 19)
from routers import reviews  # REVIEWS router'ı (Adım 14)
from routers import roles  # ROLES entity router'ı (Adım 2)
from routers import user_roles  # USER_ROLES router'ı (Adım 8)
from routers import users  # USERS entity router'ı (Adım 7)

app.include_router(roles.router)
app.include_router(languages.router)
app.include_router(difficulty_levels.router)
app.include_router(payment_methods.router)
app.include_router(payment_statuses.router)
app.include_router(categories.router)
app.include_router(users.router)
# FR11 / FR12: kullanıcı rolleri ve kara liste yönetimi TAMAMEN Admin'e özeldir
# (okuma dahil) -> router seviyesinde Admin guard'ı.
app.include_router(user_roles.router, dependencies=[Depends(require_role("Admin"))])
app.include_router(blacklist.router, dependencies=[Depends(require_role("Admin"))])
app.include_router(courses.router)
app.include_router(course_instructors.router)
app.include_router(reviews.router)
app.include_router(carts.router)
app.include_router(cart_items.router)
app.include_router(orders.router)
app.include_router(order_items.router)
app.include_router(payments.router)
app.include_router(auth.router)
