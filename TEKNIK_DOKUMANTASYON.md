# TEKNİK DOKÜMANTASYON — E-Learning API

> Bu dosya bir **geliştirme günlüğü + kod açıklamasıdır**. Amacı: kod bilgisi
> zayıf bir analistin bile projede ne yapıldığını, hangi dosyanın neden var
> olduğunu ve her fonksiyonun ne işe yaradığını anlayabilmesidir.
> Her geliştirme adımından sonra bu dosya güncellenir.

---

## Teknoloji Yığını (Stack)

| Katman | Seçim | Neden |
|---|---|---|
| Dil | Python | Okunabilir, hızlı geliştirme |
| API çatısı | FastAPI | Otomatik Swagger/ReDoc, hızlı, Pydantic ile entegre |
| Veritabanı | SQLite | Kurulum gerektirmez, tek dosya (`db.sqlite`) |
| DB erişimi | `sqlite3` (yerleşik modül) | **ORM YOK** — basit ve şeffaf, her SQL açıkça görülür |
| Doğrulama | Pydantic | İstek/cevap modelleri + validation |
| Sunucu | Uvicorn | FastAPI'yi çalıştıran ASGI sunucusu |

---

## Klasör / Dosya Yapısı (Adım 3 sonu)

```
udemyproject/
├── main.py                    # Giriş noktası; FastAPI'yi kurar, router'ları toplar
├── database.py                # SQLite bağlantısı + tablo şemaları (TABLE_SCHEMAS) + init_db
├── db.sqlite                  # SQLite veritabanı dosyası (uygulama ilk çalışınca otomatik oluşur)
├── requirements.txt           # Python bağımlılıkları (fastapi, uvicorn)
├── models/                    # Pydantic istek/cevap modelleri (entity bazlı)
│   ├── __init__.py            # Klasörü Python paketi yapar
│   ├── role.py                # ROLES modelleri: RoleCreate / RoleUpdate / RoleResponse
│   └── language.py            # LANGUAGES modelleri: LanguageCreate / Update / Response
├── routers/                   # Entity router'ları (her entity'nin endpoint'leri ayrı dosyada)
│   ├── __init__.py            # Klasörü Python paketi yapar
│   ├── roles.py               # ROLES endpoint'leri (CRUD + iş kuralları)
│   └── languages.py           # LANGUAGES endpoint'leri (CRUD + iş kuralları)
├── TEKNIK_DOKUMANTASYON.md    # Bu dosya
└── API_KULLANIM.md            # API kullanım kılavuzu
```

**Tasarım ilkesi:** Sorumluluklar ayrıdır.
- `database.py` → veritabanına *nasıl* bağlanılır / tablolar *nasıl* oluşturulur.
- `models/` → veri *neye benzer* (doğrulama kuralları).
- `routers/` → hangi *adres* hangi *işi* yapar (endpoint'ler).
- `main.py` → her şeyi *birbirine bağlar* (montaj). Endpoint İÇERMEZ.

---

## Geliştirme Günlüğü

### Adım 1 — Boş çalışan iskelet kurulumu

Bu adımda **hiçbir entity tanımlanmadı**. Sadece tüm projenin üzerine
oturacağı temel iskelet kuruldu. Amaç: hatasız ayağa kalkan, Swagger'ı açık,
router/model eklemeye hazır bir başlangıç.

#### 1) `database.py` — ne yapar, satır satır

- `DB_PATH = Path(__file__).parent / "db.sqlite"`
  Veritabanı dosyasının yolunu belirler. `__file__` bu dosyanın yolu,
  `.parent` bulunduğu klasör; sonuç proje kökündeki `db.sqlite`.

- **`get_connection()`** — Veritabanına yeni bir bağlantı açar.
  - `sqlite3.connect(DB_PATH)` → `db.sqlite`'a bağlanır (dosya yoksa oluşturur).
  - `connection.row_factory = sqlite3.Row` → sorgu sonuçlarına kolon ADIYLA
    erişmeyi sağlar (örn. `row["name"]`), okunabilirlik için.
  - `PRAGMA foreign_keys = ON` → SQLite'ta varsayılan KAPALI olan yabancı
    anahtar kontrollerini açar; ilişki bütünlüğü korunur.
  - Bağlantıyı `return` eder.

- **`TABLE_SCHEMAS`** — Bir liste. İçinde her entity'nin `CREATE TABLE` SQL
  metni tutulur. **Şu an boştur** çünkü henüz entity yok. Entity ekledikçe
  buraya tablo şeması ekleyeceğiz.

- **`init_db()`** — Tabloları oluşturur.
  - Bağlantı açar, bir `cursor` (imleç) alır.
  - `TABLE_SCHEMAS` içindeki her şemayı `executescript` ile çalıştırır.
  - `commit()` ile değişiklikleri kalıcı kaydeder.
  - `finally` bloğunda bağlantıyı **her durumda** kapatır.
  - `CREATE TABLE IF NOT EXISTS` kullanıldığı için defalarca çağrılması güvenlidir.

#### 2) `main.py` — ne yapar, satır satır

- **`lifespan(app)`** — Uygulamanın yaşam döngüsünü yöneten fonksiyon.
  - `yield`'den ÖNCE: uygulama açılırken çalışır → `init_db()` çağrılır
    (tablolar hazırlanır).
  - `yield`'den SONRA: uygulama kapanırken çalışır (şimdilik boş).

- **`app = FastAPI(...)`** — Uygulama nesnesini oluşturur.
  - `title`, `description`, `version` → Swagger UI başlığında görünür.
  - `lifespan=lifespan` → yukarıdaki açılış/kapanış mantığını bağlar.

- **`health_check()`** (`GET /`) — Basit sağlık kontrolü.
  - API ayakta mı diye bakmak için. İş kuralı yok.
  - `{"status": "ok", "docs": "/docs", "redoc": "/redoc"}` döner.
  - Swagger'da "Health" etiketi (tag) altında görünür.

- **ROUTER bölümü** — Şu an boş. Entity router'ları hazırlandıkça buraya
  `from routers import X` + `app.include_router(X.router)` satırları eklenecek.

#### 3) `models/__init__.py` ve `routers/__init__.py`

- Bu boş `__init__.py` dosyaları, klasörlerin Python **paketi** olarak
  tanınmasını sağlar (içe aktarma `from models import ...` çalışsın diye).
  İçerikleri şu an sadece açıklama yorumudur.

#### 4) `requirements.txt`

- Projenin çalışması için gereken paketler: `fastapi` ve `uvicorn[standard]`.
  `pydantic`, FastAPI ile birlikte otomatik kurulur.

---

### Adım 2 — ROLES entity'si

İlk gerçek entity olarak **ROLES** eklendi. Sonraki entity'lere örnek olacak
"şablonu" da bu adımda kurmuş olduk: her entity için **model + tablo şeması +
router** üçlüsü.

> **Karar notları (analist onayıyla):**
> - İş kuralı kaynağı: **BİZ** FR/ACC seti.
> - Şema: **Excel kesin** — Excel'de olmayan kolon eklenmez.
> - BİZ setinde ROLES tablosuna özel bir CRUD FR'ı yoktur; bu yüzden ROLES'a,
>   mimari kuralda verilen "mükerrer kayıt → 409" örneği ve şemadaki `is_active`
>   kolonuna dayanan soft-deactivate uygulandı.

#### Eklenen/değişen dosyalar

**1) `database.py` → `TABLE_SCHEMAS` listesine `roles` tablosu eklendi:**
```sql
CREATE TABLE IF NOT EXISTS roles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
```
- `id` → otomatik artan birincil anahtar.
- `name` → `NOT NULL` (boş olamaz) + `UNIQUE` (benzersiz). Mükerrer ismi
  veritabanı seviyesinde de engeller.
- `is_active` → SQLite'ta bool yoktur; **1=aktif, 0=pasif**. Varsayılan 1.
- `created_date` → değer verilmezse SQLite o anki yerel zamanı otomatik yazar.

**2) `models/role.py` (YENİ) — Pydantic modelleri:**
- **`RoleCreate`** → POST (oluşturma) isteğinde beklenen veri. Sadece `name`.
  - `name`: zorunlu metin, 2–50 karakter (temel akıl-sağlığı sınırı).
  - `isim_bos_olamaz` (`field_validator`): `name`'i `.strip()` ile kırpar; sadece
    boşluksa hata verir → FastAPI **422** döner.
- **`RoleUpdate`** → PUT (güncelleme) isteğinde beklenen veri (yine `name`).
- **`RoleResponse`** → istemciye dönen model: `id`, `name`, `is_active`,
  `created_date`. (`is_active` cevapta True/False olarak gösterilir.)
- Her modelde `model_config = ConfigDict(json_schema_extra={"example": ...})`
  ile Swagger'a örnek gövde/veri eklendi.

**3) `routers/roles.py` (YENİ) — endpoint'ler:**
- `router = APIRouter(prefix="/roles", tags=["Roles"])` → tüm adresler `/roles`
  ile başlar; Swagger'da "Roles" başlığı altında toplanır.
- **`_satiri_role_cevir(row)`** → veritabanı satırını (`sqlite3.Row`)
  `RoleResponse`'a çevirir; `is_active` sayısını (0/1) True/False yapar.
- Her endpoint `get_connection()` ile bağlanır, işini yapar, `finally`'de
  bağlantıyı kapatır. Endpoint'ler ve uyguladıkları kurallar:

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `rol_olustur` | POST `/roles` | Yeni rol. [R2] aynı isim varsa **409**; `sqlite3.IntegrityError` da 409'a çevrilir (güvenlik ağı). |
  | `rolleri_listele` | GET `/roles` | Tüm roller; `only_active=true` ile sadece aktifler. |
  | `rol_getir` | GET `/roles/{id}` | Tek rol; [R3] yoksa **404**. |
  | `rol_guncelle` | PUT `/roles/{id}` | İsim günceller; [R3] yoksa 404, [R2] isim başka rolde varsa 409. |
  | `rol_pasiflestir` | PATCH `/roles/{id}/deactivate` | `is_active=0` (soft-delete). [R3] yoksa 404. |
  | `rol_aktiflestir` | PATCH `/roles/{id}/activate` | `is_active=1`. [R3] yoksa 404. |

**4) `main.py` → router bağlandı:**
```python
from routers import roles
app.include_router(roles.router)
```

#### Uygulanan iş kuralları (özet)
- **[R1]** `name` boş olamaz → Pydantic, **422**.
- **[R2]** `name` benzersiz → mükerrerde **409 Conflict**.
- **[R3]** Olmayan `id` → **404 Not Found**.
- **[R4] (ERTELENDİ)** "Bir kullanıcıda aktif kullanılan rol pasife alınamaz"
  kuralı, `USER_ROLES` tablosu eklendiğinde `rol_pasiflestir` içine eklenecek.

#### Yapılan test (doğrulama)
Endpoint fonksiyonları doğrudan çağrılarak test edildi; tüm senaryolar geçti:
oluştur ✓, mükerrer→409 ✓, boş isim→422 ✓, listele/filtre ✓, tek getir ✓,
olmayan id→404 ✓, güncelle ✓, isim çakışması→409 ✓, pasife al/aktif et ✓.

---

### Adım 3 — LANGUAGES entity'si

ROLES şablonu birebir uygulandı (model + tablo şeması + router). LANGUAGES de
FK'sız bir lookup tablosudur; tek farkı isim kolonunun adı: `language_name`.

#### Eklenen/değişen dosyalar

**1) `database.py` → `TABLE_SCHEMAS`'a `languages` tablosu:**
```sql
CREATE TABLE IF NOT EXISTS languages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    language_name TEXT    NOT NULL UNIQUE,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_date  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
```
Kolonlar Excel'e birebir: `id`, `language_name` (NOT NULL + UNIQUE),
`is_active` (1/0), `created_date` (otomatik).

**2) `models/language.py` (YENİ):** `LanguageCreate`, `LanguageUpdate`,
`LanguageResponse`. ROLES ile aynı mantık; alan adı `language_name`.
`isim_bos_olamaz` validatörü boş/boşluk ismi reddeder (422).

**3) `routers/languages.py` (YENİ):**
`router = APIRouter(prefix="/languages", tags=["Languages"])`. Endpoint'ler:

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `dil_olustur` | POST `/languages` | Yeni dil. [R2] aynı isim varsa **409**. |
  | `dilleri_listele` | GET `/languages` | Tümü; `only_active=true` ile aktifler. |
  | `dil_getir` | GET `/languages/{id}` | Tek dil; [R3] yoksa **404**. |
  | `dil_guncelle` | PUT `/languages/{id}` | İsim günceller; [R3] 404, [R2] çakışmada 409. |
  | `dil_pasiflestir` | PATCH `/languages/{id}/deactivate` | `is_active=0`. [R3] yoksa 404. |
  | `dil_aktiflestir` | PATCH `/languages/{id}/activate` | `is_active=1`. [R3] yoksa 404. |

**4) `main.py` → `app.include_router(languages.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R1]** `language_name` boş olamaz → **422**.
- **[R2]** `language_name` benzersiz → mükerrerde **409**.
- **[R3]** Olmayan `id` → **404**.
- **[R4] (ERTELENDİ)** "Bir dile bağlı aktif kurs varken pasife alınamaz"
  kuralı, `COURSES` tablosu eklendiğinde `dil_pasiflestir` içine eklenecek.

#### Yapılan test (doğrulama)
Tüm senaryolar geçti: oluştur ✓, mükerrer→409 ✓, boş isim→422 ✓, listele/filtre ✓,
tek getir ✓, olmayan id→404 ✓, güncelle ✓, isim çakışması→409 ✓, pasife al/aktif et ✓.

---

## Sonraki Adım

Önerilen sıradaki entity: **DIFFICULTY_LEVELS** (FK'sız lookup; farkı: `code` +
`name` iki kolonu var, ikisi de benzersiz olmalı — FR10 acc5 "aynı kod ile ikinci
kayıt eklenemez"). Analist onayı beklenir.
