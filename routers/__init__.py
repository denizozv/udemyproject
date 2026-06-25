"""
routers/ paketi
---------------
Her entity'nin endpoint'leri kendi router dosyasında tutulur.
Örn. ileride: routers/roles.py, routers/courses.py ...

Her router dosyası bir APIRouter nesnesi tanımlar; main.py bu router'ları
include_router ile uygulamaya bağlar.

Bu __init__.py dosyası, "routers" klasörünün bir Python paketi olarak
tanınmasını sağlar. Şu an boştur; entity'ler eklendikçe doldurulacak.
"""
