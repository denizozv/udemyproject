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

## Klasör / Dosya Yapısı (Adım 19 sonu — 17 tablo tamam)

```
udemyproject/
├── main.py                    # Giriş noktası; FastAPI'yi kurar, router'ları toplar
├── database.py                # SQLite bağlantısı + tablo şemaları (TABLE_SCHEMAS) + init_db
├── security.py                # Şifre hash/verify (PBKDF2, ek bağımlılık yok)
├── db.sqlite                  # SQLite veritabanı dosyası (uygulama ilk çalışınca otomatik oluşur)
├── requirements.txt           # Python bağımlılıkları (fastapi, uvicorn)
├── models/                    # Pydantic istek/cevap modelleri (entity bazlı)
│   ├── __init__.py            # Klasörü Python paketi yapar
│   ├── role.py                # ROLES modelleri
│   ├── language.py            # LANGUAGES modelleri
│   ├── difficulty_level.py    # DIFFICULTY_LEVELS modelleri (code + name)
│   ├── payment_method.py      # PAYMENT_METHODS modelleri (code + name)
│   ├── payment_status.py      # PAYMENT_STATUSES modelleri (code + name)
│   ├── category.py            # CATEGORIES modelleri (parent_id + name)
│   ├── user.py                # USERS modelleri (register/update/şifre/response)
│   ├── user_role.py           # USER_ROLES modelleri (user_id + role_id)
│   ├── blacklist.py           # BLACKLIST modelleri (kara liste)
│   ├── course.py              # COURSES modelleri (çok FK + price)
│   ├── course_instructor.py   # COURSE_INSTRUCTORS modelleri (kurs↔eğitmen)
│   ├── review.py              # REVIEWS modelleri (rating + comment)
│   ├── cart.py                # CARTS modelleri (kullanıcı sepeti)
│   ├── cart_item.py           # CART_ITEMS modelleri (sepet kalemi + özet)
│   ├── order.py               # ORDERS modelleri (sipariş)
│   ├── order_item.py          # ORDER_ITEMS modelleri (sipariş kalemi + snapshot)
│   └── payment.py             # PAYMENTS modelleri (ödeme + durum değişimi)
├── routers/                   # Entity router'ları (her entity'nin endpoint'leri ayrı dosyada)
│   ├── __init__.py            # Klasörü Python paketi yapar
│   ├── roles.py               # ROLES endpoint'leri
│   ├── languages.py           # LANGUAGES endpoint'leri
│   ├── difficulty_levels.py   # DIFFICULTY_LEVELS endpoint'leri
│   ├── payment_methods.py     # PAYMENT_METHODS endpoint'leri
│   ├── payment_statuses.py    # PAYMENT_STATUSES endpoint'leri
│   ├── categories.py          # CATEGORIES endpoint'leri (self-referencing ağaç)
│   ├── users.py               # USERS endpoint'leri (kayıt, profil, soft-delete)
│   ├── user_roles.py          # USER_ROLES endpoint'leri (rol atama/kaldırma)
│   ├── blacklist.py           # BLACKLIST endpoint'leri (yasakla/kaldır)
│   ├── courses.py             # COURSES endpoint'leri (CRUD + filtre)
│   ├── course_instructors.py  # COURSE_INSTRUCTORS endpoint'leri (eğitmen ata/kaldır)
│   ├── reviews.py             # REVIEWS endpoint'leri (değerlendirme CRUD)
│   ├── carts.py               # CARTS endpoint'leri (sepet + lazy yardımcı)
│   ├── cart_items.py          # CART_ITEMS endpoint'leri (sepete ekle/çıkar/özet)
│   ├── orders.py              # ORDERS endpoint'leri (sipariş oluştur/listele/getir)
│   ├── order_items.py         # ORDER_ITEMS endpoint'leri (kalem oluştur/listele/getir)
│   └── payments.py            # PAYMENTS endpoint'leri (ödeme + durum değişimi)
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

### Adım 4 — DIFFICULTY_LEVELS entity'si

Lookup şablonu uygulandı; yeni nokta: **iki anlamlı kolon** (`code`, `name`) var
ve benzersizlik **yalnızca `code`** üzerindedir (BİZ FR10 acc5: "aynı kod ile
ikinci kayıt eklenemez"). `name` zorunludur ama benzersiz değildir.

#### Eklenen/değişen dosyalar

**1) `database.py` → `difficulty_levels` tablosu:**
```sql
CREATE TABLE IF NOT EXISTS difficulty_levels (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT    NOT NULL UNIQUE,
    name         TEXT    NOT NULL,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
```
`code` → NOT NULL + **UNIQUE**. `name` → sadece NOT NULL (UNIQUE değil).

**2) `models/difficulty_level.py` (YENİ):** `DifficultyLevelCreate/Update/Response`.
- Hem `code` hem `name` için boş-olamaz doğrulaması (ortak `_bos_olamaz` yardımcı
  fonksiyonu ile). İkisinden biri boşsa **422**.

**3) `routers/difficulty_levels.py` (YENİ):**
`router = APIRouter(prefix="/difficulty-levels", tags=["Difficulty Levels"])`.

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `seviye_olustur` | POST `/difficulty-levels` | [R2] aynı `code` varsa **409**. |
  | `seviyeleri_listele` | GET `/difficulty-levels` | Tümü; `only_active=true`. |
  | `seviye_getir` | GET `/difficulty-levels/{id}` | [R3] yoksa **404**. |
  | `seviye_guncelle` | PUT `/difficulty-levels/{id}` | [R3] 404, [R2] `code` çakışmasında 409. |
  | `seviye_pasiflestir` | PATCH `.../{id}/deactivate` | `is_active=0`. [R3] 404. |
  | `seviye_aktiflestir` | PATCH `.../{id}/activate` | `is_active=1`. [R3] 404. |

**4) `main.py` → `app.include_router(difficulty_levels.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R1]** `code` ve `name` boş olamaz → **422**.
- **[R2]** `code` benzersiz → mükerrer kodda **409** (FR10 acc5).
- **[R3]** Olmayan `id` → **404**.
- **[R4] (ERTELENDİ)** "Aktif kursta kullanılan seviye pasife alınamaz" (FR10 acc6)
  → `COURSES` tablosu gelince eklenecek.

#### Yapılan test (doğrulama)
Tüm senaryolar geçti: oluştur ✓, mükerrer code→409 ✓, code/name boş→422 ✓,
listele/filtre ✓, getir ✓, 404 ✓, güncelle ✓, code çakışması→409 ✓, pasife/aktif ✓.

---

### Adım 5 — PAYMENT_METHODS + PAYMENT_STATUSES (birlikte)

Bu iki lookup tablosu, DIFFICULTY_LEVELS ile **birebir aynı yapıdadır**
(id, code, name, is_active, created_date; benzersizlik `code` üzerinde). Aynı
şablon iki entity'ye uygulandı.

#### Eklenen/değişen dosyalar

**1) `database.py` → iki tablo eklendi:**
```sql
CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_date TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS payment_statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_date TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
```

**2) Modeller (YENİ):** `models/payment_method.py` ve `models/payment_status.py`
— her biri `...Create/Update/Response`. code ve name için boş-olamaz doğrulaması.

**3) Router'lar (YENİ):**
- `routers/payment_methods.py` → `prefix="/payment-methods"`, tag "Payment Methods".
  Fonksiyonlar: `yontem_olustur / yontemleri_listele / yontem_getir /
  yontem_guncelle / yontem_pasiflestir / yontem_aktiflestir`.
- `routers/payment_statuses.py` → `prefix="/payment-statuses"`, tag "Payment Statuses".
  Fonksiyonlar: `durum_olustur / durumlari_listele / durum_getir /
  durum_guncelle / durum_pasiflestir / durum_aktiflestir`.

**4) `main.py` → iki router da bağlandı** (`include_router`).

#### Uygulanan iş kuralları (her iki entity için)
- **[R1]** `code` ve `name` boş olamaz → **422**.
- **[R2]** `code` benzersiz → mükerrer kodda **409** (FR10 acc5).
- **[R3]** Olmayan `id` → **404**.
- **[R4] (ERTELENDİ)** PENDING/COMPLETED bir ödemede kullanılan yöntem/durum
  pasife alınamaz (FR10 acc6) → `PAYMENTS` tablosu gelince eklenecek.

#### Yapılan test (doğrulama)
`import main` ile tüm uygulamanın yüklendiği doğrulandı. Her iki entity için
tüm senaryolar geçti: oluştur ✓, mükerrer code→409 ✓, code/name boş→422 ✓,
listele/filtre ✓, getir ✓, 404 ✓, güncelle ✓, code çakışması→409 ✓, pasife/aktif ✓.

> **Durum:** Tüm 5 lookup/leaf tablo (ROLES, LANGUAGES, DIFFICULTY_LEVELS,
> PAYMENT_METHODS, PAYMENT_STATUSES) tamamlandı. Sırada ilişkili (FK içeren)
> entity'ler var.

---

### Adım 6 — CATEGORIES entity'si (ilk FK / self-referencing ağaç)

İlk yabancı anahtarlı (FK) ve **self-referencing** (kendine referans veren)
tablo. `parent_id` bir üst kategoriyi işaret eder; NULL ise kök kategoridir.

#### Eklenen/değişen dosyalar

**1) `database.py` → `categories` tablosu:**
```sql
CREATE TABLE IF NOT EXISTS categories (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id    INTEGER,                       -- NULL = kök kategori
    name         TEXT    NOT NULL,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);
```
- `parent_id` nullable + kendi tablosuna FK. `PRAGMA foreign_keys = ON`
  (database.py'de açık) sayesinde parent'ın varlığı DB seviyesinde de korunur.
- `name` sadece NOT NULL (UNIQUE değil — bkz. kapsam notu).

**2) `models/category.py` (YENİ):** `CategoryCreate/Update/Response`.
- `parent_id: int | None` → opsiyonel; None = kök.
- `name` boş-olamaz doğrulaması.

**3) `routers/categories.py` (YENİ):** `prefix="/categories"`, tag "Categories".
- Yardımcı `_parent_var_mi(cursor, parent_id)` → verilen parent gerçekten var mı?

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `kategori_olustur` | POST `/categories` | [R-parent] parent_id verilirse mevcut olmalı, yoksa **400**. |
  | `kategorileri_listele` | GET `/categories` | `only_active=true` ve `parent_id` filtreleri (parent_id=0 → kökler). |
  | `kategori_getir` | GET `/categories/{id}` | [R3] yoksa **404**. |
  | `kategori_guncelle` | PUT `/categories/{id}` | [R3] 404; [R-self] parent==kendi id→**400**; [R-parent] parent yoksa→**400**. |
  | `kategori_pasiflestir` | PATCH `.../{id}/deactivate` | `is_active=0`. [R3] 404. |
  | `kategori_aktiflestir` | PATCH `.../{id}/activate` | `is_active=1`. [R3] 404. |

**4) `main.py` → `app.include_router(categories.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R1]** `name` boş olamaz → **422**.
- **[R-parent]** `parent_id` verilirse mevcut bir kategori olmalı → **400** (FR10 acc3).
- **[R-self]** `parent_id`, kategorinin kendi id'sine eşit olamaz → **400** (FR10 acc4).
- **[R3]** Olmayan `id` → **404**.
- **[R4] (ERTELENDİ)** Aktif kursta kullanılan kategori pasife alınamaz (FR10 acc6)
  → `COURSES` gelince eklenecek.

> **KAPSAM NOTU (BİZ seti):** CATEGORIES için **isim benzersizliği** ve
> **çok-düzeyli döngü (A→B→A) / maksimum derinlik** kuralları BİZ setinde
> **YOKTUR** (bunlar CLAUDE setine ait; kullanılmıyor). Bu yüzden eklenmedi;
> yalnızca self-loop (acc4) engellendi. Gerekirse ileride istenirse eklenebilir.

#### Yapılan test (doğrulama)
Tüm senaryolar geçti: kök oluştur ✓, alt kategori oluştur ✓, geçersiz parent→400 ✓,
boş isim→422 ✓, listele (tümü / kökler / çocuklar) ✓, getir ✓, 404 ✓, güncelle ✓,
self-loop→400 ✓, geçersiz parent (update)→400 ✓, köke taşı ✓, pasife/aktif ✓.

---

### Adım 7 — USERS entity'si (çekirdek + şifre güvenliği + soft-delete)

İlk soft-delete'li (`deleted_date`) ve şifre güvenliği içeren entity.

> **Karar (analist onayı):** Şifre saklama yöntemi **PBKDF2 (hashlib)** seçildi —
> ek bağımlılık yok, "basit/minimal" mimariye uygun. (bcrypt değil.)

#### Eklenen/değişen dosyalar

**1) `security.py` (YENİ) — şifre yardımcıları:**
- `hash_password(plain)` → rastgele salt üretir, PBKDF2-SHA256 (200.000 tur) ile
  hash'ler, `pbkdf2_sha256$<tur>$<salt>$<hash>` metnini döndürür.
- `verify_password(plain, stored)` → girişte (FR2) kullanılacak; `hmac.compare_digest`
  ile güvenli karşılaştırma yapar.
- **NEDEN:** Düz şifre asla saklanmaz. Geri döndürülemez hash + salt güvenlidir.

**2) `database.py` → `users` tablosu** (id, full_name, mail, password_hash, phone,
birth_date, is_active, created_date, deleted_date).
- **mail'e DB-UNIQUE konmadı** — çünkü FR3 acc5 gereği saklama süresi (90 gün)
  dolunca aynı e-posta yeniden kullanılabilmeli; benzersizlik iş katmanında
  (aktif + saklama penceresi) uygulanır.

**3) `models/user.py` (YENİ):**
- `UserCreate` (register): full_name, mail, password, phone, birth_date — beşi de
  zorunlu. Doğrulamalar: mail regex (acc3), password ≥8 (acc5), phone yalnız rakam
  10–11 hane (acc6), birth_date geçerli + gelecekte olamaz (acc7). mail küçük
  harfe normalize edilir.
- `UserUpdate` (profil): şifre hariç aynı alanlar.
- `PasswordChange`: yeni şifre ≥8.
- `UserResponse`: **password/password_hash İÇERMEZ** (güvenlik).

**4) `routers/users.py` (YENİ):** `prefix="/users"`, tag "Users".
- `_satiri_cevir` cevaba password_hash'i bilinçli olarak almaz.
- `_mail_kullanimda_mi(cursor, mail, haric_id)` → mail aktif bir kullanıcıda ya da
  saklama (90g) süresi dolmamış silinmiş kayıtta mı? (FR1 acc4 + FR3 acc5).

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `kullanici_kaydet` | POST `/users` | [R1] format→422, [R-mail] kullanımda→409, aktif oluştur (acc9). |
  | `kullanicilari_listele` | GET `/users` | `only_active=true` filtresi. |
  | `kullanici_getir` | GET `/users/{id}` | [R3] yoksa 404. |
  | `kullanici_guncelle` | PUT `/users/{id}` | [R3] 404, [R-mail] kullanımda→409. |
  | `sifre_degistir` | PATCH `/users/{id}/password` | Yeni şifre hash'lenir; [R1] 422, [R3] 404. |
  | `kullanici_sil` | DELETE `/users/{id}` | Soft-delete: is_active=0, deleted_date=now (FR3 acc1). |
  | `kullanici_yeniden_aktiflestir` | PATCH `/users/{id}/reactivate` | is_active=1, deleted_date=NULL (FR3 acc3). |

**5) `main.py` → `app.include_router(users.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R1]** Zorunlu alan + format (full_name/mail/password≥8/phone/birth_date) → **422**.
- **[R-mail]** Aktif veya saklamada (90g) aynı mail → **409** (FR1 acc4 + FR3 acc5).
- **[R3]** Olmayan id → **404**.
- Soft-delete (FR3 acc1) ve reactivate (FR3 acc3) uygulandı.
- **GÜVENLİK:** `password_hash` hiçbir cevapta yer almaz; şifre PBKDF2 ile saklanır.

#### ERTELENENLER
- **[FR1 acc8]** Yeni kullanıcıya varsayılan **Student** rolü atama → `USER_ROLES` gelince.
- **[FR2]** Giriş (login), 5 hatalı denemede kilit, login'de onaylı yeniden
  aktifleştirme → ayrı **auth** adımı (henüz kapsam dışı).
- **[FR3 acc4]** Saklama süresi dolan verinin kalıcı silinmesi/anonimleştirilmesi
  → zamanlanmış batch (kapsam dışı).

#### Yapılan test (doğrulama)
hash/verify ✓, kayıt ✓, mükerrer mail (case-insensitive)→409 ✓, **cevapta şifre yok** ✓,
tüm doğrulamalar→422 ✓, profil güncelleme ✓, mail çakışması→409 ✓, şifre değiştir ✓,
soft-delete (deleted_date set) ✓, saklama içinde mail tekrar kayıt→409 ✓,
reactivate (deleted_date temizlendi) ✓, only_active liste ✓, 404 ✓.

---

### Adım 8 — USER_ROLES entity'si (kullanıcı↔rol junction)

İlk çoka-çok (many-to-many) bağlantı tablosu. Aktiflik bu tabloda `is_active`
kolonu yerine **`deleted_date IS NULL`** ile belirlenir (soft-delete).

#### Eklenen/değişen dosyalar

**1) `database.py` → `user_roles` tablosu** (id, user_id FK→users, role_id FK→roles,
created_date, deleted_date). FK'lar user/role varlığını DB seviyesinde garanti eder.

**2) `models/user_role.py` (YENİ):**
- `UserRoleCreate`: user_id + role_id.
- `UserRoleResponse`: id, user_id, role_id, **is_active (TÜRETİLMİŞ: deleted_date
  IS NULL)**, created_date, deleted_date.

**3) `routers/user_roles.py` (YENİ):** `prefix="/user-roles"`, tag "User Roles".
Yardımcılar: `_user_var_mi`, `_rol_aktif_mi`, `_aktif_atama_var_mi`, `_aktif_rol_sayisi`.

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `rol_ata` | POST `/user-roles` | [R-user] user yoksa 400; [R-role] rol yok/pasif→400; [R-dup] aktif aynı atama→**409**. |
  | `atamalari_listele` | GET `/user-roles` | `user_id` ve `only_active` filtreleri. |
  | `atama_getir` | GET `/user-roles/{id}` | [R3] yoksa 404. |
  | `rol_kaldir` | DELETE `/user-roles/{id}` | Soft-delete (deleted_date). [R3] 404; [R-last] son aktif rol→**409**; zaten pasifse idempotent. |

**4) `main.py` → `app.include_router(user_roles.router)` eklendi.**

#### Uygulanan iş kuralları (BİZ FR11)
- **[R-user]** `user_id` mevcut olmalı → **400**.
- **[R-role]** `role_id` mevcut ve **aktif** olmalı → **400** (acc2).
- **[R-dup]** Aynı rol kullanıcıya iki kez aktif atanamaz → **409** (acc4).
- **[R3]** Olmayan id → **404**.
- **[R-last]** Kullanıcının son aktif rolü kaldırılamaz → **409** (acc5).
- Rol kaldırma = soft-delete, kayıt silinmez (acc6). Soft-delete sonrası aynı rol
  yeniden atanabilir (yeni aktif kayıt oluşur).

#### ERTELENENLER
- **[acc1]** Yalnızca Admin yetkisi, **[acc8]** rol değişiklik audit log → auth adımı.
- **[FR1 acc8]** Yeni kullanıcıya otomatik **Student** rolü atama → roller
  seed'lenmediği için kayıt akışına BAĞLANMADI; analist kararıyla eklenebilir.

#### Yapılan test (doğrulama)
Atama ✓, mükerrer aktif→409 ✓, user yok→400 ✓, rol yok→400 ✓, pasif rol→400 ✓,
listele (user/aktif filtre) ✓, getir ✓, 404 ✓, kaldır (soft-delete) ✓,
son aktif rol→409 ✓, idempotent tekrar kaldırma ✓, soft-delete sonrası yeniden atama ✓.

---

### Adım 9 — BLACKLIST entity'si (kara liste)

Kullanıcıları yasaklama. Soft-delete `is_active` ile yapılır. Önemli kavram:
**"geçerli yasak"** = `is_active=1` VE (süresiz VEYA `ban_until` gelecekte).
Süresi geçmiş yasak geçerli sayılmaz (acc6).

#### Eklenen/değişen dosyalar

**1) `database.py` → `blacklist` tablosu** (id, user_id FK→users, banned_by FK→users,
reason, ban_until, is_active, created_date).

**2) `models/blacklist.py` (YENİ):**
- `BlacklistCreate`: user_id, banned_by, reason (boş olamaz), ban_until (opsiyonel;
  `_ban_until_normalize` ile 'YYYY-MM-DD' veya tam tarih-saat kabul edilip normalize
  edilir; boş = süresiz).
- `BlacklistResponse`: kolonlar + **`is_valid` (TÜRETİLMİŞ: yasak şu an geçerli mi)**.

**3) `routers/blacklist.py` (YENİ):** `prefix="/blacklist"`, tag "Blacklist".
- `_ban_gecerli_mi(is_active, ban_until)` → is_valid'i hesaplar.
- `_gecerli_yasak_var_mi(cursor, user_id)` → acc5 için kullanıcının şu an geçerli
  yasağı var mı?

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `yasakla` | POST `/blacklist` | [R1] reason→422; [R-user] user/banned_by yok→400; [R-active] geçerli yasak var→**409**. |
  | `yasaklari_listele` | GET `/blacklist` | `user_id`, `only_active`, `only_valid` filtreleri. |
  | `yasak_getir` | GET `/blacklist/{id}` | [R3] yoksa 404. |
  | `yasak_kaldir` | PATCH `/blacklist/{id}/lift` | Soft (is_active=0, acc7). [R3] 404; zaten pasifse idempotent. |

**4) `main.py` → `app.include_router(blacklist.router)` eklendi.**

#### Uygulanan iş kuralları (BİZ FR12)
- **[R1]** `reason` zorunlu → **422** (acc3).
- **[R-user]** `user_id` ve `banned_by` mevcut olmalı → **400** (acc2).
- **[R-active]** Kullanıcının zaten geçerli yasağı varsa → **409** (acc5).
- Süreli/süresiz yasak `ban_until` ile (acc4); süresi geçen geçerli sayılmaz (acc6).
- **[R3]** Olmayan id → **404**.
- Yasak kaldırma = soft (is_active=0), kayıt silinmez (acc7).

#### KAPSAM NOTU (BİZ)
Admin yetkisi (acc1) ve "admin kendini/başka admini yasaklayamaz" gibi rol-bağımlı
kurallar BİZ FR12'de yoktur (CLAUDE setine ait); uygulanmadı.

#### Yapılan test (doğrulama)
reason boş→422 ✓, geçersiz ban_until→422 ✓, süresiz yasak ✓, geçerli yasak varken
ikinci→409 ✓, user/banned_by yok→400 ✓, getir/404 ✓, only_valid liste ✓,
lift (soft)→is_active false ✓, idempotent lift ✓, lift sonrası tekrar yasak ✓,
**süresi geçmiş yasak is_valid=False → aynı kullanıcıya yeni yasak eklenebiliyor** ✓.

---

### Adım 10 — COURSES entity'si (çok FK'lı içerik tablosu)

İlk üç farklı FK içeren ana içerik tablosu (kategori + dil + zorluk seviyesi).

#### Eklenen/değişen dosyalar

**1) `database.py` → `courses` tablosu** (id, category_id FK→categories,
language_id FK→languages, course_name, price REAL, description, difficulty_id
FK→difficulty_levels, is_active, created_date, deleted_date).

**2) `models/course.py` (YENİ):** `CourseCreate/Update/Response`.
- `price: float = Field(gt=0)` → sıfır/negatif reddedilir (FR9 acc3) → 422.
- `course_name` boş olamaz, `description` opsiyonel.

**3) `routers/courses.py` (YENİ):** `prefix="/courses"`, tag "Courses".
- `_aktif_mi(cursor, tablo, id)` → lookup kaydı mevcut+aktif mi?
- `_fk_kontrol(...)` → 3 FK'yı tek seferde doğrular (mevcut+aktif değilse 400).

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `kurs_olustur` | POST `/courses` | [R1] 422; [R-fk] kategori/dil/zorluk mevcut+aktif→**400** (acc4/5). |
  | `kurslari_listele` | GET `/courses` | Filtreler: `q`, `category_id`, `language_id`, `difficulty_id`, `min_price`, `max_price`, `only_active`. [R-price-range] min>max→**400** (FR4 acc4). |
  | `kurs_getir` | GET `/courses/{id}` | [R3] yoksa 404. |
  | `kurs_guncelle` | PUT `/courses/{id}` | [R3] 404; [R1] 422; [R-fk] 400. |
  | `kurs_pasiflestir` | PATCH `.../{id}/deactivate` | is_active=0, deleted_date=now (FR9 acc7). |
  | `kurs_aktiflestir` | PATCH `.../{id}/activate` | is_active=1, deleted_date=NULL. |

**4) `main.py` → `app.include_router(courses.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R1]** `course_name` boş olamaz, `price` > 0 → **422** (FR9 acc2/acc3).
- **[R-fk]** category/language/difficulty mevcut **ve aktif** → **400** (FR9 acc4/acc5).
- **[R-price-range]** Listede `min_price > max_price` → **400** (FR4 acc4).
- **[R3]** Olmayan id → **404**.
- Soft-delete (is_active + deleted_date); pasif kurs `only_active` listesinde çıkmaz (FR9 acc7).

#### ERTELENENLER
- Eğitmen-özel yetki ve "yalnızca kendi kursunu düzenleme" (FR9 acc1/acc6/acc8)
  → `COURSE_INSTRUCTORS` + auth.
- Eğitmen adıyla arama, ortalama puan, popülerlik sıralaması (FR4/FR5)
  → `COURSE_INSTRUCTORS` / `REVIEWS` / `ORDER_ITEMS` adımlarında.
- **[R4]** "Aktif kursta kullanılan kategori/dil/seviye pasife alınamaz" (FR10 acc6)
  → lookup deactivate endpoint'lerine HENÜZ eklenmedi (analist onayıyla eklenecek).

#### Yapılan test (doğrulama)
price≤0→422 ✓, kısa ad→422 ✓, oluştur ✓, pasif kategori→400 ✓, olmayan dil→400 ✓,
listele ✓, ad arama (q) ✓, fiyat filtresi ✓, min>max→400 ✓, getir/404 ✓,
güncelle ✓, güncellemede pasif FK→400 ✓, pasife al/aktif et ✓, only_active ✓.

---

### Adım 11 — Geri-bağlanan kurallar: [R4] + FR1 acc8

Yeni entity eklenmedi; daha önce ertelenen iki kural devreye alındı.

**1) [R4] Aktif kursta kullanılan lookup pasife alınamaz (FR10 acc6):**
`routers/categories.py`, `routers/languages.py`, `routers/difficulty_levels.py`
içindeki **deactivate** fonksiyonlarına, `is_active=0` yapmadan önce şu kontrol
eklendi: ilgili lookup'ı kullanan **aktif bir kurs** varsa **409** döner.
- kategori: `SELECT 1 FROM courses WHERE category_id=? AND is_active=1`
- dil: `... WHERE language_id=? AND is_active=1`
- seviye: `... WHERE difficulty_id=? AND is_active=1`

**2) FR1 acc8 — Kayıtta otomatik Student rolü:**
`routers/users.py` → `kullanici_kaydet`:
- Kullanıcı oluşturulmadan ÖNCE aktif `Student` rolü (`lower(name)='student'`)
  aranır. Yoksa kayıt **409** ile reddedilir (yarım kayıt kalmaz — atomik).
- Varsa: kullanıcı eklenir + aynı transaction'da `user_roles`'a Student ataması
  yapılır, sonra tek `commit`. Sabit: `VARSAYILAN_ROL = "Student"`.

#### Yapılan test (doğrulama)
[R4]: kullanımdaki kategori/dil/seviye pasife→409 ✓; kurs pasife alınınca lookup
pasife alınabiliyor ✓. acc8: Student rolü yokken kayıt→409 ✓; rol varken kayıt +
otomatik Student ataması ✓.

---

### Adım 12 — Self-delete (şifreli) + saklama temizliği (FR3 acc4)

Analistle görüşülüp kararlaştırılan iki yeni özellik eklendi (yeni tablo yok;
`users` router'ına iki endpoint).

**1) `POST /users/{id}/delete-account` — kendi şifresiyle silme:**
- Gövde: `{ "password": "..." }`. `verify_password` ile mevcut hash karşılaştırılır.
- Şifre yanlış → **403** (silme yapılmaz). Doğru → soft-delete (is_active=0,
  deleted_date=now, FR3 acc1). Kullanıcı yoksa **404**. Zaten silinmişse idempotent.
- Mevcut `DELETE /users/{id}` (şifresiz, admin/zorunlu silme) korunur.
- Yeni modeller: `AccountDeleteRequest`.

**2) `POST /users/cleanup-expired?dry_run=true` — FR3 acc4 kalıcı silme:**
- `is_active=0` ve `deleted_date < (now - 90 gün)` olan hesapları bulur.
- **Güvenlik:** `dry_run=true` (varsayılan) → silmez, yalnızca raporlar.
  `dry_run=false` → gerçekten siler.
- Kalıcı silme: kullanıcı + bağlı `user_roles` + `blacklist` (user_id) kayıtları
  aynı transaction'da silinir (önce bağlılar, sonra kullanıcı → FK güvenli).
- **Atlama:** Kullanıcı başka kayıtlarda `banned_by` ile referanslıysa silinmez;
  rapordaki `skipped` altında nedeniyle listelenir.
- Yeni modeller: `CleanupReport`, `CleanupSkipped`.
- _Not: Orders/Reviews/Course_Instructors eklendiğinde temizlik onları da
  kapsayacak şekilde genişletilmeli._

#### Yapılan test (doğrulama)
Self-delete: yanlış şifre→403 ✓, doğru şifre→soft-delete ✓, idempotent ✓, 404 ✓.
Cleanup: taze hesap aday değil ✓, süresi geçmiş hesap dry_run'da raporlanır ama
silinmez ✓, dry_run=false'ta kullanıcı + user_roles silinir ✓, banned_by
referanslı hesap atlanır + raporlanır ✓.

---

### Adım 13 — COURSE_INSTRUCTORS entity'si (kurs↔eğitmen çoka-çok)

> **Analist kararları:** (1) Kurs başına **en fazla 1 aktif primary** eğitmen.
> (2) `instructor_id` **aktif 'Instructor' rolüne** sahip olmalı (FR9 acc1).

#### Eklenen/değişen dosyalar

**1) `database.py` → `course_instructors` tablosu** (id, course_id FK→courses,
instructor_id FK→users, is_primary, created_date, deleted_date). Aktiflik
`deleted_date IS NULL` ile.

**2) `models/course_instructor.py` (YENİ):** `CourseInstructorCreate`
(course_id, instructor_id, is_primary), `CourseInstructorResponse`
(is_primary + türetilmiş is_active).

**3) `routers/course_instructors.py` (YENİ):** `prefix="/course-instructors"`,
tag "Course Instructors". Yardımcılar: `_course_var_mi`, `_user_var_mi`,
`_instructor_rolu_var_mi` (USER_ROLES + ROLES join), `_aktif_atama_var_mi`,
`_aktif_primary_var_mi`.

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `egitmen_ata` | POST `/course-instructors` | [R-course] 400; [R-instructor] yok/rol yok→400; [R-dup] 409; [R-primary] ikinci primary→409. |
  | `atamalari_listele` | GET `/course-instructors` | `course_id`, `instructor_id`, `only_active` filtreleri. |
  | `atama_getir` | GET `/course-instructors/{id}` | [R3] 404. |
  | `primary_yap` | PATCH `.../{id}/make-primary` | Atamayı primary yapar; [R3] 404, pasifse 409, başka primary varsa 409, zaten primary ise idempotent. |
  | `egitmen_kaldir` | DELETE `/course-instructors/{id}` | Soft-delete (deleted_date); [R3] 404, zaten pasifse idempotent. |

**4) `main.py` → `app.include_router(course_instructors.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R-course]** `course_id` mevcut → yoksa **400**.
- **[R-instructor]** `instructor_id` mevcut + aktif 'Instructor' rolü → yoksa **400** (FR9 acc1).
- **[R-dup]** Aynı eğitmen aynı kursa iki kez aktif atanamaz → **409**.
- **[R-primary]** Kurs başına en fazla 1 aktif primary → ikinci primary **409**.
- **[R3]** Olmayan id → **404**. Kaldırma = soft-delete.

#### Yapılan test (doğrulama)
ata+primary ✓, dup→409 ✓, ikinci primary→409 ✓, yardımcı atama ✓, Instructor rolü
yok→400 ✓, olmayan kurs/kullanıcı→400 ✓, listele/getir/404 ✓, make-primary çakışma→409 ✓,
primary kaldırınca devir→ok ✓, idempotent ✓, soft-delete sonrası yeniden atama ✓.

---

### Adım 14 — REVIEWS entity'si (kurs değerlendirmeleri)

> **Analist kararı:** FR6 **acc2** (yalnızca satın almış kullanıcı değerlendirir)
> **ERTELENDİ** — `ORDER_ITEMS` eklenince [R4] gibi geri-bağlanacak.

#### Eklenen/değişen dosyalar

**1) `database.py` → `reviews` tablosu** (id, course_id FK→courses, user_id FK→users,
rating, comment, created_date, deleted_date).

**2) `models/review.py` (YENİ):** `ReviewCreate` (course_id, user_id, rating 1-5,
comment opsiyonel), `ReviewUpdate` (rating, comment), `ReviewResponse`
(+ türetilmiş is_active).

**3) `routers/reviews.py` (YENİ):** `prefix="/reviews"`, tag "Reviews".

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `degerlendirme_yap` | POST `/reviews` | [R1] rating 1-5→422; [R-fk] course/user→400; [R-tek] aktif review varsa→**409** (acc3). |
  | `degerlendirmeleri_listele` | GET `/reviews` | `course_id`, `user_id`, `only_active` filtreleri. |
  | `degerlendirme_getir` | GET `/reviews/{id}` | [R3] 404. |
  | `degerlendirme_guncelle` | PUT `/reviews/{id}` | rating+comment; [R3] 404, [R1] 422 (acc7). |
  | `degerlendirme_kaldir` | DELETE `/reviews/{id}` | Soft-delete; [R3] 404, idempotent. |

**4) `main.py` → `app.include_router(reviews.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R1]** `rating` zorunlu + 1-5 → **422** (FR6 acc4/acc5).
- **[R-fk]** `course_id`/`user_id` mevcut → yoksa **400**.
- **[R-tek]** Bir kullanıcı bir kursa tek **aktif** değerlendirme → **409** (acc3).
- **[R3]** Olmayan id → **404**. Silme = soft-delete (acc7); sonra yeniden değerlendirilebilir.

#### ERTELENENLER
- **[acc2]** Yalnızca satın almış kullanıcı → `ORDER_ITEMS` gelince geri-bağlanacak.
- **[acc6]** Kursun ortalama puanına dahil etme (FR4 acc10/FR5 acc2 okuma/hesap) → ileride.

#### Yapılan test (doğrulama)
rating 1-5 dışı→422 ✓, oluştur ✓, tek aktif review→409 ✓, course/user yok→400 ✓,
listele/getir/404 ✓, güncelle ✓, update rating aralık dışı→422 ✓, soft-delete +
sonrasında yeniden değerlendirme ✓, idempotent ✓.

---

### Adım 15 — CARTS entity'si (kullanıcı sepeti)

> **Analist kararları:** (1) Tek sepet = `user_id` UNIQUE (Excel'de is_active yok).
> (2) Sepet oluşturma: **hem açık `POST /carts` hem lazy** (CART_ITEMS'ta otomatik).

#### Eklenen/değişen dosyalar

**1) `database.py` → `carts` tablosu** (id, user_id **UNIQUE** FK→users, created_date).

**2) `models/cart.py` (YENİ):** `CartCreate` (user_id), `CartResponse`.

**3) `routers/carts.py` (YENİ):** `prefix="/carts"`, tag "Carts".
- **`sepet_getir_veya_olustur(cursor, user_id)`** → yeniden kullanılabilir yardımcı;
  sepet varsa döndürür, yoksa oluşturur (commit etmez). CART_ITEMS adımındaki
  **lazy** "sepete ekle" akışı bunu kullanacak.

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `sepet_olustur` | POST `/carts` | [R-user] user yok→400; [R-tek] kullanıcının sepeti varsa→**409** (acc1). |
  | `sepetleri_listele` | GET `/carts` | `user_id` filtresi. |
  | `sepet_getir` | GET `/carts/{id}` | [R3] 404. |

**4) `main.py` → `app.include_router(carts.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R-user]** `user_id` mevcut → yoksa **400**.
- **[R-tek]** Kullanıcı başına tek sepet (user_id UNIQUE) → ikinci sepet **409** (FR7 acc1).
- **[R3]** Olmayan id → **404**.

#### Yapılan test (doğrulama)
sepet oluştur ✓, ikinci sepet→409 ✓, olmayan user→400 ✓, listele/filtre ✓,
getir/404 ✓, lazy yardımcı mevcut sepeti döndürür ✓.

---

### Adım 16 — CART_ITEMS entity'si (sepet kalemleri)

> **Analist kararı:** "Sepete ekle" girdisi **`{user_id, course_id}`** (lazy sepet).

#### Eklenen/değişen dosyalar

**1) `database.py` → `cart_items` tablosu** (id, cart_id FK→carts, course_id FK→courses,
created_date). Excel'de `deleted_date` **yok** → çıkarma **hard delete**.

**2) `models/cart_item.py` (YENİ):** `CartItemCreate` (user_id, course_id),
`CartItemResponse`, `CartSummaryItem`, `CartSummary` (FR7 acc5 özet).

**3) `routers/cart_items.py` (YENİ):** `prefix="/cart-items"`, tag "Cart Items".
`routers.carts.sepet_getir_veya_olustur` ile lazy sepet.

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `sepete_ekle` | POST `/cart-items` | [R-user]/[R-course] 400; lazy sepet; [R-dup] aynı kurs→**409** (acc3). |
  | `kalemleri_listele` | GET `/cart-items` | `cart_id` / `user_id` filtreleri. |
  | `sepet_ozeti` | GET `/cart-items/summary?user_id=` | FR7 acc5: kalemler (ad+fiyat) + toplam tutar. Sepet yoksa boş özet. |
  | `kalem_getir` | GET `/cart-items/{id}` | [R3] 404. |
  | `sepetten_cikar` | DELETE `/cart-items/{id}` | KALICI siler (acc6); [R3] 404. |

**4) `main.py` → `app.include_router(cart_items.router)` eklendi.**

#### Uygulanan iş kuralları (BİZ FR7)
- **[R-user]/[R-course]** mevcut olmalı → **400**.
- Lazy sepet (acc1/acc2): kullanıcının sepeti yoksa eklemede otomatik oluşur.
- **[R-dup]** Aynı kurs sepette iki kez olamaz → **409** (acc3).
- Sepetten çıkarma = kalıcı silme (acc6). Özet (acc5) toplam tutarı verir.
- **[R3]** Olmayan id → **404**.

#### ERTELENEN
- **[acc4]** Zaten satın alınmış kurs sepete eklenemez → `ORDER_ITEMS` gelince bağlanacak.

#### Yapılan test (doğrulama)
lazy sepet oluşumu ✓, dup→409 ✓, user/course yok→400 ✓, listele ✓, özet+toplam ✓,
boş sepet özeti ✓, getir/404 ✓, çıkar (hard delete) ✓, çıkar tekrar→404 ✓.

---

### Adım 17 — ORDERS entity'si (sipariş, temel CRUD)

> **Strateji (analist kararı):** Önce 3 tablonun (ORDERS, ORDER_ITEMS, PAYMENTS)
> temel CRUD'ı; sonra ayrı bir adımda **checkout** endpoint'i.

#### Eklenen/değişen dosyalar
**1) `database.py` → `orders` tablosu** (id, user_id FK→users, total_price REAL,
created_date). Sipariş immutable.

**2) `models/order.py` (YENİ):** `OrderCreate` (user_id, total_price ≥ 0),
`OrderResponse`.

**3) `routers/orders.py` (YENİ):** `prefix="/orders"`, tag "Orders".

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `siparis_olustur` | POST `/orders` | [R1] total_price≥0→422; [R-user] user yok→400. |
  | `siparisleri_listele` | GET `/orders` | `user_id` filtresi. |
  | `siparis_getir` | GET `/orders/{id}` | [R3] 404. |

  Immutable olduğu için **PUT/DELETE yok**.

**4) `main.py` → `app.include_router(orders.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R1]** `total_price` ≥ 0 → **422**.
- **[R-user]** `user_id` mevcut → yoksa **400**.
- **[R3]** Olmayan id → **404**.

#### ERTELENEN (checkout adımında)
- **[acc6]** `total_price` = OrderItem'ların `unit_price` toplamı.
- "En az bir kalem" (boş sipariş yok). Bu tutarlılık checkout'ta garanti edilecek.

#### Yapılan test (doğrulama)
total_price<0→422 ✓, oluştur ✓, olmayan user→400 ✓, total=0 geçerli ✓,
listele/getir/404 ✓.

---

### Adım 18 — ORDER_ITEMS entity'si (sipariş kalemleri)

#### Eklenen/değişen dosyalar
**1) `database.py` → `order_items` tablosu** (id, order_id FK→orders, course_id
FK→courses, unit_price REAL, created_date). Immutable.

**2) `models/order_item.py` (YENİ):** `OrderItemCreate` (order_id, course_id,
unit_price ≥ 0), `OrderItemResponse`.

**3) `routers/order_items.py` (YENİ):** `prefix="/order-items"`, tag "Order Items".

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `kalem_olustur` | POST `/order-items` | [R1] unit_price≥0→422; [R-order]/[R-course] yok→400; [R-dup] aynı kurs aynı siparişte→**409**. |
  | `kalemleri_listele` | GET `/order-items` | `order_id` / `course_id` filtreleri. |
  | `kalem_getir` | GET `/order-items/{id}` | [R3] 404. |

  Immutable → **PUT/DELETE yok**.

**4) `main.py` → `app.include_router(order_items.router)` eklendi.**

#### Uygulanan iş kuralları
- **[R1]** `unit_price` ≥ 0 → **422**.
- **[R-order]/[R-course]** mevcut olmalı → **400**.
- **[R-dup]** Aynı kurs aynı siparişte iki kez olamaz → **409** (veri bütünlüğü).
- **[R3]** Olmayan id → **404**.
- `unit_price` sipariş anındaki fiyatı yansıtır (snapshot, FR8 acc5).

#### Yapılan test (doğrulama)
unit_price<0→422 ✓, oluştur ✓, aynı kurs aynı sipariş→409 ✓, order/course yok→400 ✓,
listele/getir/404 ✓, **fiyat snapshot** (kurs fiyatı değişince kalem unit_price sabit) ✓.

---

### Adım 19 — PAYMENTS entity'si (ödeme — son tablo)

> **Analist kararı:** Yeni ödeme durumu **otomatik PENDING** (POST status almaz).

#### Eklenen/değişen dosyalar
**1) `database.py` → `payments` tablosu** (id, order_id **UNIQUE** FK→orders,
payment_method_id FK→payment_methods, payment_status_id FK→payment_statuses,
payment_date, address, created_date). order_id UNIQUE → sipariş başına tek ödeme.

**2) `models/payment.py` (YENİ):** `PaymentCreate` (order_id, payment_method_id,
address — status almaz), `PaymentStatusChange` (payment_status_id), `PaymentResponse`.

**3) `routers/payments.py` (YENİ):** `prefix="/payments"`, tag "Payments".
Sabit: `BASLANGIC_DURUM_KODU = "PENDING"`.

  | Fonksiyon | Metod + Adres | Yaptığı iş & kural |
  |---|---|---|
  | `odeme_olustur` | POST `/payments` | [R1] address→422; [R-order] 400; [R-tek] order'ın ödemesi varsa→**409**; [R-method] pasif/yok→400; durum otomatik **PENDING** (yoksa 409). |
  | `odemeleri_listele` | GET `/payments` | `order_id` filtresi. |
  | `odeme_getir` | GET `/payments/{id}` | [R3] 404. |
  | `odeme_durumu_degistir` | PATCH `/payments/{id}/status` | [R3] 404; yeni durum aktif değilse→**400**. |

**4) `main.py` → `app.include_router(payments.router)` eklendi.**

#### Uygulanan iş kuralları (BİZ FR8)
- **[R1]** `address` zorunlu → **422** (acc3).
- **[R-order]** `order_id` mevcut → yoksa **400**.
- **[R-tek]** Sipariş başına tek ödeme (§3.11) → **409**.
- **[R-method]** `payment_method_id` aktif → yoksa **400** (acc2).
- **[acc7]** Yeni ödeme otomatik **PENDING** (aktif PENDING durumu yoksa 409).
- Durum değişimi: PATCH ile; yeni durum aktif olmalı (400).
- **[R3]** Olmayan id → **404**.

#### ERTELENEN (checkout / ödeme işleme)
- acc8-acc11 durum geçişi yan etkileri (sepeti pasife alma, kurs erişimi, iade ile
  erişim kaldırma) → checkout/erişim akışında.

#### Yapılan test (doğrulama)
PENDING yokken→409 ✓, address boş→422 ✓, oluştur (otomatik PENDING) ✓,
ikinci ödeme→409 ✓, olmayan sipariş→400 ✓, pasif yöntem→400 ✓, getir/404 ✓,
durum değiştir ✓, geçersiz durum→400 ✓.

---

## 🎉 Tüm 17 tablo tamamlandı

ROLES, LANGUAGES, DIFFICULTY_LEVELS, PAYMENT_METHODS, PAYMENT_STATUSES, CATEGORIES,
USERS, USER_ROLES, BLACKLIST, COURSES, COURSE_INSTRUCTORS, REVIEWS, CARTS,
CART_ITEMS, ORDERS, ORDER_ITEMS, PAYMENTS.

## Sonraki Adım — CHECKOUT akışı (FR8)

Önerilen son büyük adım: **`POST /orders/checkout`** — kullanıcının sepetinden
(CART_ITEMS) tek transaction'da:
1. ORDER oluştur, her kurs için ORDER_ITEM (`unit_price` = kursun o anki fiyatı, snapshot),
2. `total_price` = kalemler toplamı (acc6),
3. PAYMENT (PENDING) oluştur (adres + yöntem),
4. sepeti temizle (CART_ITEMS sil).
Kurallar: boş sepetle checkout yok (acc... → 409/400). Bu adım gelince ertelenen
**REVIEWS acc2** ve **CART_ITEMS acc4** (satın alma geçmişi) de geri-bağlanabilir.
Analist onayı beklenir.
