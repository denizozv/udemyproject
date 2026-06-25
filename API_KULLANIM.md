# API KULLANIM KILAVUZU — E-Learning API

> Bu dosya, API'yi kullanacak kişi için **pratik bir kılavuzdur**. Her endpoint
> için: adres, metod, ne işe yaradığı, hangi FR/ACC gereksinimini karşıladığı,
> örnek istek (body), örnek cevap, olası hata kodları ve anlamları yazılır.
> Her geliştirme adımından sonra güncellenir.

---

## 1. Projeyi Çalıştırma

### Gereksinim
- Python 3.10+ kurulu olmalı.

### Kurulum (ilk sefer, bir kez)
Proje klasöründe (`udemyproject/`) terminal açıp:

```bash
pip install -r requirements.txt
```

### Çalıştırma
Proje klasöründeyken:

```bash
uvicorn main:app --reload
```

- `main:app` → `main.py` dosyasındaki `app` nesnesini çalıştır demektir.
- `--reload` → kodda değişiklik yapınca sunucu otomatik yeniden başlar (geliştirme kolaylığı).

### Adresler
| Ne | Adres |
|---|---|
| API kök adresi | http://127.0.0.1:8000 |
| **Swagger UI (dokümantasyon)** | **http://127.0.0.1:8000/docs** |
| ReDoc (alternatif dokümantasyon) | http://127.0.0.1:8000/redoc |

> Port varsayılan **8000**'dir. Değiştirmek için: `uvicorn main:app --reload --port 9000`

---

## 2. Endpoint'ler

### Health Check

| Özellik | Değer |
|---|---|
| **Adres** | `/` |
| **Metod** | `GET` |
| **Ne işe yarar** | API'nin ayakta olup olmadığını kontrol eder. |
| **İlgili FR/ACC** | — (altyapı endpoint'i, iş kuralı yok) |

**Örnek istek:** Body yok.

**Örnek cevap (200 OK):**
```json
{
  "status": "ok",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

**Olası hata kodları:** Yok (her zaman 200 döner; dönmüyorsa sunucu çalışmıyordur).

---

## 3. ROLES (Roller)

Roller: `Admin`, `Instructor`, `Student` gibi sistem rolleri.
Tüm adresler `/roles` ile başlar. Swagger'da **Roles** başlığı altındadır.

> **Not (kaynak):** BİZ FR/ACC setinde ROLES tablosuna özel CRUD FR'ı yoktur.
> Buradaki kurallar, mimari kuralda verilen "mükerrer kayıt → 409" örneğine ve
> şemadaki `is_active` kolonuna dayanır. "Kullanımdaki rol pasife alınamaz"
> kuralı (R4) `USER_ROLES` tablosu eklendiğinde devreye girecektir.

### 3.1 Rol oluştur

| Özellik | Değer |
|---|---|
| **Adres** | `/roles` |
| **Metod** | `POST` |
| **Ne işe yarar** | Yeni bir rol oluşturur. |
| **İlgili kural** | [R1] isim boş olamaz, [R2] isim benzersiz olmalı |

**Örnek istek (body):**
```json
{ "name": "Instructor" }
```
**Örnek cevap (201 Created):**
```json
{ "id": 2, "name": "Instructor", "is_active": true, "created_date": "2024-01-01 10:00:00" }
```
**Olası hatalar:**
| Kod | Anlamı |
|---|---|
| 409 | Aynı isimde rol zaten var. |
| 422 | Doğrulama hatası (örn. `name` boş/eksik). |

### 3.2 Rolleri listele

| Özellik | Değer |
|---|---|
| **Adres** | `/roles` (opsiyonel: `/roles?only_active=true`) |
| **Metod** | `GET` |
| **Ne işe yarar** | Tüm rolleri listeler; `only_active=true` ile yalnızca aktifler. |

**Örnek cevap (200 OK):**
```json
[
  { "id": 1, "name": "Admin", "is_active": true, "created_date": "2024-01-01 10:00:00" },
  { "id": 2, "name": "Instructor", "is_active": true, "created_date": "2024-01-01 10:00:00" }
]
```

### 3.3 Tek rol getir

| Özellik | Değer |
|---|---|
| **Adres** | `/roles/{id}` |
| **Metod** | `GET` |
| **Ne işe yarar** | Belirtilen id'li rolü döndürür. |
| **İlgili kural** | [R3] rol yoksa 404 |

**Örnek cevap (200 OK):**
```json
{ "id": 2, "name": "Instructor", "is_active": true, "created_date": "2024-01-01 10:00:00" }
```
**Olası hatalar:** `404` → o id'li rol bulunamadı.

### 3.4 Rol güncelle

| Özellik | Değer |
|---|---|
| **Adres** | `/roles/{id}` |
| **Metod** | `PUT` |
| **Ne işe yarar** | Rolün adını günceller. |
| **İlgili kural** | [R3] rol yoksa 404, [R2] yeni isim başka rolde varsa 409 |

**Örnek istek (body):**
```json
{ "name": "Egitmen" }
```
**Örnek cevap (200 OK):**
```json
{ "id": 2, "name": "Egitmen", "is_active": true, "created_date": "2024-01-01 10:00:00" }
```
**Olası hatalar:** `404` (rol yok), `409` (isim çakışması), `422` (doğrulama).

### 3.5 Rolü pasife al / yeniden aktifleştir

| Özellik | Değer |
|---|---|
| **Adres** | `/roles/{id}/deactivate` — `/roles/{id}/activate` |
| **Metod** | `PATCH` |
| **Ne işe yarar** | Rolü silmeden pasife alır (is_active=0) veya tekrar aktif eder (is_active=1). |
| **İlgili kural** | [R3] rol yoksa 404 |

**Örnek cevap (200 OK, deactivate):**
```json
{ "id": 2, "name": "Instructor", "is_active": false, "created_date": "2024-01-01 10:00:00" }
```
**Olası hatalar:** `404` → o id'li rol bulunamadı.

---

## 4. LANGUAGES (Diller)

Diller: `Turkce`, `Ingilizce`, `Almanca` gibi. Tüm adresler `/languages` ile
başlar. Swagger'da **Languages** başlığı altındadır. Yapı ROLES ile aynıdır;
isim kolonu `language_name`.

> **Not (kaynak):** Kurallar mimari "mükerrer → 409" örneğine ve şemadaki
> `is_active` kolonuna dayanır. **[R4] uygulandı:** dil **aktif bir kursta**
> kullanılıyorsa pasife alınamaz → **409** (FR10 acc6).

### 4.1 Dil oluştur
| Özellik | Değer |
|---|---|
| **Adres** | `/languages` |
| **Metod** | `POST` |
| **Ne işe yarar** | Yeni bir dil oluşturur. |
| **İlgili kural** | [R1] isim boş olamaz, [R2] isim benzersiz |

**Örnek istek:** `{ "language_name": "Turkce" }`
**Örnek cevap (201):** `{ "id": 1, "language_name": "Turkce", "is_active": true, "created_date": "2024-01-03 09:00:00" }`
**Olası hatalar:** `409` (aynı isim var), `422` (doğrulama).

### 4.2 Dilleri listele
| Özellik | Değer |
|---|---|
| **Adres** | `/languages` (opsiyonel: `?only_active=true`) |
| **Metod** | `GET` |
| **Ne işe yarar** | Tüm diller; `only_active=true` ile yalnızca aktifler. |

**Örnek cevap (200):**
```json
[ { "id": 1, "language_name": "Turkce", "is_active": true, "created_date": "2024-01-03 09:00:00" } ]
```

### 4.3 Tek dil getir
| Özellik | Değer |
|---|---|
| **Adres** | `/languages/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] dil yoksa 404 |

**Olası hatalar:** `404` → o id'li dil bulunamadı.

### 4.4 Dil güncelle
| Özellik | Değer |
|---|---|
| **Adres** | `/languages/{id}` |
| **Metod** | `PUT` |
| **İlgili kural** | [R3] yoksa 404, [R2] isim çakışmasında 409 |

**Örnek istek:** `{ "language_name": "Almanca" }`
**Olası hatalar:** `404`, `409`, `422`.

### 4.5 Dili pasife al / yeniden aktifleştir
| Özellik | Değer |
|---|---|
| **Adres** | `/languages/{id}/deactivate` — `/languages/{id}/activate` |
| **Metod** | `PATCH` |
| **İlgili kural** | [R3] dil yoksa 404 |

**Örnek cevap (deactivate, 200):** `{ "id": 1, "language_name": "Turkce", "is_active": false, "created_date": "..." }`
**Olası hatalar:** `404`.

---

## 5. DIFFICULTY_LEVELS (Zorluk Seviyeleri)

Zorluk seviyeleri: `BEGINNER/Baslangic`, `INTERMEDIATE/Orta`, `ADVANCED/Ileri`.
Tüm adresler `/difficulty-levels` ile başlar. Swagger'da **Difficulty Levels**
başlığı altındadır. Her kaydın `code` (teknik kod) ve `name` (görünen ad) alanı
vardır; **benzersizlik `code` üzerindedir**.

> **Not (kaynak):** Benzersizlik kuralı BİZ FR10 acc5'e dayanır (aynı kod ile
> ikinci kayıt eklenemez). **[R4] uygulandı:** seviye **aktif bir kursta**
> kullanılıyorsa pasife alınamaz → **409** (FR10 acc6).

### 5.1 Seviye oluştur
| Özellik | Değer |
|---|---|
| **Adres** | `/difficulty-levels` |
| **Metod** | `POST` |
| **İlgili kural** | [R1] code/name boş olamaz, [R2] code benzersiz (FR10 acc5) |

**Örnek istek:** `{ "code": "BEGINNER", "name": "Baslangic" }`
**Örnek cevap (201):** `{ "id": 1, "code": "BEGINNER", "name": "Baslangic", "is_active": true, "created_date": "2024-01-01 10:00:00" }`
**Olası hatalar:** `409` (aynı code var), `422` (doğrulama).

### 5.2 Seviyeleri listele
| Özellik | Değer |
|---|---|
| **Adres** | `/difficulty-levels` (opsiyonel: `?only_active=true`) |
| **Metod** | `GET` |

**Örnek cevap (200):**
```json
[ { "id": 1, "code": "BEGINNER", "name": "Baslangic", "is_active": true, "created_date": "2024-01-01 10:00:00" } ]
```

### 5.3 Tek seviye getir
| Özellik | Değer |
|---|---|
| **Adres** | `/difficulty-levels/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] kayıt yoksa 404 |

**Olası hatalar:** `404`.

### 5.4 Seviye güncelle
| Özellik | Değer |
|---|---|
| **Adres** | `/difficulty-levels/{id}` |
| **Metod** | `PUT` |
| **İlgili kural** | [R3] yoksa 404, [R2] code çakışmasında 409 |

**Örnek istek:** `{ "code": "INTERMEDIATE", "name": "Orta" }`
**Olası hatalar:** `404`, `409`, `422`.

### 5.5 Seviyeyi pasife al / yeniden aktifleştir
| Özellik | Değer |
|---|---|
| **Adres** | `/difficulty-levels/{id}/deactivate` — `.../{id}/activate` |
| **Metod** | `PATCH` |
| **İlgili kural** | [R3] kayıt yoksa 404 |

**Olası hatalar:** `404`.

---

## 6. PAYMENT_METHODS (Ödeme Yöntemleri)

Ödeme yöntemleri: `CREDIT_CARD/Kredi Karti`, `DEBIT_CARD/Banka Karti`,
`BANK_TRANSFER/Havale-EFT`. Tüm adresler `/payment-methods` ile başlar
(Swagger'da **Payment Methods**). Yapı DIFFICULTY_LEVELS ile aynı: `code`
(benzersiz) + `name`.

> **Not (kaynak):** Benzersizlik FR10 acc5'e dayanır. "Ödemede kullanılan
> yöntem pasife alınamaz" kuralı (R4, FR10 acc6) `PAYMENTS` gelince eklenecek.

| # | Adres | Metod | İş | Kural / Hatalar |
|---|---|---|---|---|
| 6.1 | `/payment-methods` | POST | Oluştur | [R1] code/name boş→422, [R2] code mükerrer→409 |
| 6.2 | `/payment-methods` (`?only_active=true`) | GET | Listele | — |
| 6.3 | `/payment-methods/{id}` | GET | Tek getir | [R3] yoksa 404 |
| 6.4 | `/payment-methods/{id}` | PUT | Güncelle | [R3] 404, [R2] code çakışma→409, 422 |
| 6.5 | `/payment-methods/{id}/deactivate` | PATCH | Pasife al | [R3] 404 |
| 6.6 | `/payment-methods/{id}/activate` | PATCH | Aktifleştir | [R3] 404 |

**Örnek istek (POST):** `{ "code": "CREDIT_CARD", "name": "Kredi Karti" }`
**Örnek cevap (201):** `{ "id": 1, "code": "CREDIT_CARD", "name": "Kredi Karti", "is_active": true, "created_date": "2024-01-01 10:00:00" }`

---

## 7. PAYMENT_STATUSES (Ödeme Durumları)

Ödeme durumları: `PENDING/Beklemede`, `COMPLETED/Tamamlandi`, `FAILED/Basarisiz`,
`REFUNDED/Iade Edildi`. Tüm adresler `/payment-statuses` ile başlar (Swagger'da
**Payment Statuses**). Yapı PAYMENT_METHODS ile birebir aynı.

> **Not (kaynak):** Benzersizlik FR10 acc5. R4 (kullanımdaki durum pasife
> alınamaz, FR10 acc6) `PAYMENTS` gelince eklenecek.

| # | Adres | Metod | İş | Kural / Hatalar |
|---|---|---|---|---|
| 7.1 | `/payment-statuses` | POST | Oluştur | [R1] code/name boş→422, [R2] code mükerrer→409 |
| 7.2 | `/payment-statuses` (`?only_active=true`) | GET | Listele | — |
| 7.3 | `/payment-statuses/{id}` | GET | Tek getir | [R3] yoksa 404 |
| 7.4 | `/payment-statuses/{id}` | PUT | Güncelle | [R3] 404, [R2] code çakışma→409, 422 |
| 7.5 | `/payment-statuses/{id}/deactivate` | PATCH | Pasife al | [R3] 404 |
| 7.6 | `/payment-statuses/{id}/activate` | PATCH | Aktifleştir | [R3] 404 |

**Örnek istek (POST):** `{ "code": "PENDING", "name": "Beklemede" }`
**Örnek cevap (201):** `{ "id": 1, "code": "PENDING", "name": "Beklemede", "is_active": true, "created_date": "2024-01-01 10:00:00" }`

---

## 8. CATEGORIES (Kategoriler)

Kategoriler çok seviyeli bir **ağaç** oluşturur: her kategorinin bir üst
kategorisi (`parent_id`) olabilir. `parent_id` boş (null) ise kategori bir
**kök** kategoridir. Tüm adresler `/categories` ile başlar (Swagger'da
**Categories**).

> **Not (kaynak / kapsam):** BİZ FR10 acc3 (parent ile bağlama), acc4 (kendine
> parent olamama) uygulanır. **İsim benzersizliği** ve **çok-düzeyli döngü /
> maksimum derinlik** BİZ setinde olmadığından uygulanmadı. **[R4] uygulandı:**
> kategori **aktif bir kursta** kullanılıyorsa pasife alınamaz → **409** (FR10 acc6).

### 8.1 Kategori oluştur
| Özellik | Değer |
|---|---|
| **Adres** | `/categories` |
| **Metod** | `POST` |
| **İş** | Yeni kategori; `parent_id` yoksa kök olur. |
| **İlgili kural** | [R1] name boş→422, [R-parent] parent_id mevcut değilse→400 |

**Örnek istek (alt kategori):** `{ "parent_id": 1, "name": "Web Gelistirme" }`
**Örnek istek (kök):** `{ "name": "Yazilim" }`
**Örnek cevap (201):** `{ "id": 2, "parent_id": 1, "name": "Web Gelistirme", "is_active": true, "created_date": "2024-01-03 10:05:00" }`
**Olası hatalar:** `400` (parent yok), `422` (name boş).

### 8.2 Kategorileri listele
| Özellik | Değer |
|---|---|
| **Adres** | `/categories` |
| **Metod** | `GET` |
| **Filtreler** | `only_active=true` → aktifler; `parent_id=X` → X'in çocukları; `parent_id=0` → kök kategoriler |

**Örnek:** `GET /categories?parent_id=0` → tüm kök kategoriler.
**Örnek cevap (200):**
```json
[ { "id": 1, "parent_id": null, "name": "Yazilim", "is_active": true, "created_date": "2024-01-03 10:00:00" } ]
```

### 8.3 Tek kategori getir
| Özellik | Değer |
|---|---|
| **Adres** | `/categories/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] kategori yoksa 404 |

**Olası hatalar:** `404`.

### 8.4 Kategori güncelle
| Özellik | Değer |
|---|---|
| **Adres** | `/categories/{id}` |
| **Metod** | `PUT` |
| **İş** | Ad + üst kategori (parent_id) güncellenir. `parent_id: null` → köke taşı. |
| **İlgili kural** | [R3] yoksa 404; [R-self] parent==kendi id→400; [R-parent] parent yoksa→400 |

**Örnek istek:** `{ "parent_id": 1, "name": "Mobil Gelistirme" }`
**Olası hatalar:** `404`, `400` (self-loop veya parent yok), `422`.

### 8.5 Kategoriyi pasife al / yeniden aktifleştir
| Özellik | Değer |
|---|---|
| **Adres** | `/categories/{id}/deactivate` — `.../{id}/activate` |
| **Metod** | `PATCH` |
| **İlgili kural** | [R3] kategori yoksa 404 |

**Olası hatalar:** `404`.

---

## 9. USERS (Kullanıcılar)

Kullanıcı kaydı, profil, şifre ve hesap silme işlemleri. Tüm adresler `/users`
ile başlar (Swagger'da **Users**).

> **GÜVENLİK:** Şifre PBKDF2 ile hash'lenip saklanır; **hiçbir cevapta şifre ya da
> password_hash dönmez.**
>
> **Not (kaynak / kapsam):** Kurallar BİZ FR1 + FR3'e dayanır. Login (FR2),
> hatalı denemede kilit ve "yeni kullanıcıya Student rolü atama" (FR1 acc8)
> ileriki adımlara (auth / USER_ROLES) ertelendi.

### 9.1 Kullanıcı kaydı (register)
| Özellik | Değer |
|---|---|
| **Adres** | `/users` |
| **Metod** | `POST` |
| **İş** | Yeni kullanıcı oluşturur (aktif). |
| **İlgili FR/kural** | FR1 acc2/3/5/6/7 (422), acc4+FR3 acc5 (mail kullanımda→409), acc9 (aktif), **acc8 (otomatik Student rolü)** |

> **acc8:** Kayıt başarılı olunca kullanıcıya otomatik **Student** rolü atanır
> (USER_ROLES). Sistemde aktif 'Student' rolü yoksa kayıt **409** ile reddedilir
> (önce `POST /roles {"name":"Student"}`).

**Örnek istek:**
```json
{ "full_name": "Ahmet Yilmaz", "mail": "ahmet@elearning.com", "password": "GizliSifre123", "phone": "05321112233", "birth_date": "1985-04-12" }
```
**Örnek cevap (201):**
```json
{ "id": 1, "full_name": "Ahmet Yilmaz", "mail": "ahmet@elearning.com", "phone": "05321112233", "birth_date": "1985-04-12", "is_active": true, "created_date": "2024-01-05 09:20:00", "deleted_date": null }
```
**Olası hatalar:** `409` (bu e-posta kullanımda), `422` (zorunlu alan/format: kısa şifre, geçersiz mail, harfli telefon, gelecek doğum tarihi vb.).

### 9.2 Kullanıcıları listele
| Özellik | Değer |
|---|---|
| **Adres** | `/users` (opsiyonel: `?only_active=true`) |
| **Metod** | `GET` |

### 9.3 Tek kullanıcı getir
| Özellik | Değer |
|---|---|
| **Adres** | `/users/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] kullanıcı yoksa 404 |

### 9.4 Profil güncelle
| Özellik | Değer |
|---|---|
| **Adres** | `/users/{id}` |
| **Metod** | `PUT` |
| **İş** | full_name, mail, phone, birth_date güncellenir (şifre hariç). |
| **İlgili kural** | [R3] 404, [R-mail] yeni mail kullanımda→409, 422 |

**Örnek istek:** `{ "full_name": "Ahmet Y.", "mail": "ahmet@elearning.com", "phone": "05329998877", "birth_date": "1985-04-12" }`

### 9.5 Şifre değiştir
| Özellik | Değer |
|---|---|
| **Adres** | `/users/{id}/password` |
| **Metod** | `PATCH` |
| **İlgili kural** | yeni şifre ≥8 (422), [R3] 404 |

**Örnek istek:** `{ "new_password": "YeniSifre456" }`

### 9.6 Hesabı sil (soft-delete)
| Özellik | Değer |
|---|---|
| **Adres** | `/users/{id}` |
| **Metod** | `DELETE` |
| **İş** | Fiziksel silmez; is_active=0, deleted_date=now (FR3 acc1). |
| **İlgili kural** | [R3] 404 |

**Örnek cevap (200):** `{ "id": 1, ..., "is_active": false, "deleted_date": "2024-05-01 10:00:00" }`
**Not:** Silinen e-posta, saklama süresi (90 gün) dolana dek yeni kayıtta kullanılamaz (FR3 acc5).

### 9.7 Silinmiş hesabı yeniden aktifleştir
| Özellik | Değer |
|---|---|
| **Adres** | `/users/{id}/reactivate` |
| **Metod** | `PATCH` |
| **İş** | is_active=1, deleted_date=NULL (FR3 acc3). |
| **İlgili kural** | [R3] 404 |

### 9.8 Kendi hesabını şifreyle sil (self-delete)
| Özellik | Değer |
|---|---|
| **Adres** | `/users/{id}/delete-account` |
| **Metod** | `POST` |
| **İş** | Kullanıcı kendi hesabını siler; mevcut şifresini doğrulatır, sonra soft-delete. |
| **İlgili kural** | şifre yanlış→403; [R3] 404; zaten silinmişse idempotent |

**Örnek istek:** `{ "password": "GizliSifre123" }`
**Örnek cevap (200):** `{ "id": 3, ..., "is_active": false, "deleted_date": "2024-05-01 10:00:00" }`
**Olası hatalar:** `403` (şifre hatalı), `404` (kullanıcı yok).

### 9.9 Saklama süresi dolanları temizle (bakım — FR3 acc4)
| Özellik | Değer |
|---|---|
| **Adres** | `/users/cleanup-expired` (opsiyonel: `?dry_run=false`) |
| **Metod** | `POST` |
| **İş** | 90 günü geçmiş silinmiş hesapları **kalıcı** siler (+ bağlı user_roles/blacklist). |
| **Güvenlik** | Varsayılan `dry_run=true` → silmez, rapor verir. Gerçek silme için `dry_run=false`. |
| **Atlama** | `banned_by` ile referanslı hesap silinmez; raporda `skipped` altında listelenir. |

**Örnek cevap (200):**
```json
{ "dry_run": true, "retention_days": 90, "candidate_count": 2, "deleted_user_ids": [3], "skipped": [{ "id": 1, "reason": "banned_by referansı var; başka kullanıcıların yasak kayıtlarında kullanılıyor." }] }
```

---

## 10. USER_ROLES (Kullanıcı Rolleri)

Kullanıcı ↔ rol bağlantısı (çoka-çok). Bir kullanıcının birden fazla aktif rolü
olabilir. Tüm adresler `/user-roles` ile başlar (Swagger'da **User Roles**).
Aktiflik `deleted_date` boş (null) olmasıyla belirlenir; cevapta kolaylık için
`is_active` (türetilmiş) alanı da döner.

> **Not (kaynak / kapsam):** BİZ FR11. Admin yetkisi (acc1) ve audit log (acc8)
> auth adımına ertelendi. Yeni kullanıcıya otomatik Student rolü (FR1 acc8) henüz
> kayıt akışına bağlanmadı (roller seed'lenmedi).

### 10.1 Kullanıcıya rol ata
| Özellik | Değer |
|---|---|
| **Adres** | `/user-roles` |
| **Metod** | `POST` |
| **İlgili kural** | [R-user] user yoksa 400, [R-role] rol yok/pasif→400 (acc2), [R-dup] aktif aynı atama→409 (acc4) |

**Örnek istek:** `{ "user_id": 1, "role_id": 2 }`
**Örnek cevap (201):** `{ "id": 1, "user_id": 1, "role_id": 2, "is_active": true, "created_date": "2024-01-05 09:20:00", "deleted_date": null }`
**Olası hatalar:** `400` (geçersiz user/role veya rol pasif), `409` (zaten aktif atanmış).

### 10.2 Atamaları listele
| Özellik | Değer |
|---|---|
| **Adres** | `/user-roles` |
| **Metod** | `GET` |
| **Filtreler** | `user_id=X` → o kullanıcının atamaları; `only_active=true` → yalnızca aktifler |

### 10.3 Tek atamayı getir
| Özellik | Değer |
|---|---|
| **Adres** | `/user-roles/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] yoksa 404 |

### 10.4 Rol atamasını kaldır (soft-delete)
| Özellik | Değer |
|---|---|
| **Adres** | `/user-roles/{id}` |
| **Metod** | `DELETE` |
| **İş** | Fiziksel silmez; deleted_date=now (FR11 acc6). |
| **İlgili kural** | [R3] 404; [R-last] kullanıcının son aktif rolü kaldırılamaz→409 (acc5) |

**Olası hatalar:** `404`, `409` (son aktif rol). Zaten kaldırılmış bir kayda tekrar
istek atılırsa kayıt değişmeden döner (idempotent). Kaldırılan rol, sonradan
`POST /user-roles` ile yeniden atanabilir.

---

## 11. BLACKLIST (Kara Liste)

Kullanıcı yasaklama. Tüm adresler `/blacklist` ile başlar (Swagger'da **Blacklist**).
Önemli kavram: **geçerli yasak** = `is_active=true` VE (süresiz veya `ban_until`
gelecekte). Cevapta `is_valid` (türetilmiş) bu durumu gösterir.

> **Not (kaynak / kapsam):** BİZ FR12. Admin yetkisi (acc1) ve "kendini/başka
> admini yasaklayamama" gibi rol-bağımlı kurallar BİZ'de olmadığından uygulanmadı.

### 11.1 Kullanıcıyı yasakla
| Özellik | Değer |
|---|---|
| **Adres** | `/blacklist` |
| **Metod** | `POST` |
| **İlgili kural** | [R1] reason zorunlu→422 (acc3); [R-user] user/banned_by yok→400 (acc2); [R-active] geçerli yasak var→409 (acc5) |

**Örnek istek (süresiz):** `{ "user_id": 6, "banned_by": 1, "reason": "Spam icerik paylasimi" }`
**Örnek istek (süreli):** `{ "user_id": 3, "banned_by": 1, "reason": "Tekrarli sikayet", "ban_until": "2024-12-31 00:00:00" }`
**Örnek cevap (201):**
```json
{ "id": 1, "user_id": 6, "banned_by": 1, "reason": "Spam icerik paylasimi", "ban_until": null, "is_active": true, "is_valid": true, "created_date": "2024-05-15 09:00:00" }
```
**Olası hatalar:** `400` (user/banned_by yok), `409` (zaten geçerli yasak), `422` (reason boş / ban_until format).

### 11.2 Kara liste kayıtlarını listele
| Özellik | Değer |
|---|---|
| **Adres** | `/blacklist` |
| **Metod** | `GET` |
| **Filtreler** | `user_id=X`; `only_active=true` (is_active); `only_valid=true` (şu an geçerli) |

### 11.3 Tek kayıt getir
| Özellik | Değer |
|---|---|
| **Adres** | `/blacklist/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] yoksa 404 |

### 11.4 Yasağı kaldır (soft)
| Özellik | Değer |
|---|---|
| **Adres** | `/blacklist/{id}/lift` |
| **Metod** | `PATCH` |
| **İş** | is_active=0 (FR12 acc7). Fiziksel silmez. |
| **İlgili kural** | [R3] 404; zaten pasifse idempotent |

---

## 12. COURSES (Kurslar)

Kurslar. Tüm adresler `/courses` ile başlar (Swagger'da **Courses**). Her kurs bir
kategoriye, bir dile ve bir zorluk seviyesine bağlıdır (hepsi aktif olmalı).

> **Not (kaynak / kapsam):** BİZ FR9 (price>0, aktif kategori/dil/seviye) ve FR4
> (fiyat aralığı, aktif filtre). Eğitmen bilgisi/araması, ortalama puan ve
> popülerlik sıralaması COURSE_INSTRUCTORS / REVIEWS / ORDER_ITEMS adımlarına
> bırakıldı.

### 12.1 Kurs oluştur
| Özellik | Değer |
|---|---|
| **Adres** | `/courses` |
| **Metod** | `POST` |
| **İlgili kural** | [R1] course_name boş / price≤0→422 (acc2/3); [R-fk] kategori/dil/seviye mevcut+aktif değilse→400 (acc4/5) |

**Örnek istek:**
```json
{ "category_id": 2, "language_id": 1, "course_name": "Spring Boot ile REST API", "price": 499.9, "description": "Sifirdan REST API gelistirme", "difficulty_id": 2 }
```
**Örnek cevap (201):**
```json
{ "id": 1, "category_id": 2, "language_id": 1, "course_name": "Spring Boot ile REST API", "price": 499.9, "description": "Sifirdan REST API gelistirme", "difficulty_id": 2, "is_active": true, "created_date": "2024-02-01 12:00:00", "deleted_date": null }
```
**Olası hatalar:** `400` (pasif/olmayan kategori/dil/seviye), `422` (price≤0, kısa ad).

### 12.2 Kursları listele / filtrele
| Özellik | Değer |
|---|---|
| **Adres** | `/courses` |
| **Metod** | `GET` |
| **Filtreler** | `q` (ad araması), `category_id`, `language_id`, `difficulty_id`, `min_price`, `max_price`, `only_active=true` |

**Örnek:** `GET /courses?q=React&max_price=300&only_active=true`
**Olası hatalar:** `400` (min_price > max_price, FR4 acc4).

### 12.3 Tek kurs getir
| Özellik | Değer |
|---|---|
| **Adres** | `/courses/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] yoksa 404 |

### 12.4 Kursu güncelle
| Özellik | Değer |
|---|---|
| **Adres** | `/courses/{id}` |
| **Metod** | `PUT` |
| **İlgili kural** | [R3] 404; [R1] 422; [R-fk] 400 |

**Örnek istek:** `{ "category_id": 3, "language_id": 1, "course_name": "Android Kotlin", "price": 599.0, "description": "Kotlin ile mobil", "difficulty_id": 3 }`

### 12.5 Kursu pasife al / yeniden aktifleştir
| Özellik | Değer |
|---|---|
| **Adres** | `/courses/{id}/deactivate` — `.../{id}/activate` |
| **Metod** | `PATCH` |
| **İş** | deactivate: is_active=0 + deleted_date; activate: is_active=1 + deleted_date=null |
| **İlgili kural** | [R3] 404 |

---

## 13. COURSE_INSTRUCTORS (Kurs Eğitmenleri)

Kurs ↔ eğitmen bağlantısı (çoka-çok). Tüm adresler `/course-instructors` ile
başlar (Swagger'da **Course Instructors**). Aktiflik `deleted_date` boş olmasıyla;
cevapta `is_active` (türetilmiş) döner.

> **Kurallar (BİZ FR9 + kararlar):** instructor aktif 'Instructor' rolüne sahip
> olmalı (acc1); kurs başına en fazla 1 aktif primary; aynı eğitmen aynı kursa
> 2 kez aktif atanamaz.

### 13.1 Kursa eğitmen ata
| Özellik | Değer |
|---|---|
| **Adres** | `/course-instructors` |
| **Metod** | `POST` |
| **İlgili kural** | [R-course] kurs yok→400; [R-instructor] yok/Instructor rolü yok→400; [R-dup] 409; [R-primary] ikinci primary→409 |

**Örnek istek:** `{ "course_id": 1, "instructor_id": 1, "is_primary": true }`
**Örnek cevap (201):** `{ "id": 1, "course_id": 1, "instructor_id": 1, "is_primary": true, "is_active": true, "created_date": "2024-02-01 12:00:00", "deleted_date": null }`
**Olası hatalar:** `400` (geçersiz kurs/kullanıcı veya Instructor rolü yok), `409` (zaten atanmış / kursta primary var).

### 13.2 Atamaları listele
| Özellik | Değer |
|---|---|
| **Adres** | `/course-instructors` |
| **Metod** | `GET` |
| **Filtreler** | `course_id`, `instructor_id`, `only_active=true` |

### 13.3 Tek atamayı getir
| Özellik | Değer |
|---|---|
| **Adres** | `/course-instructors/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] 404 |

### 13.4 Atamayı birincil (primary) yap
| Özellik | Değer |
|---|---|
| **Adres** | `/course-instructors/{id}/make-primary` |
| **Metod** | `PATCH` |
| **İlgili kural** | [R3] 404; pasifse→409; kursta başka primary varsa→409; zaten primary ise idempotent |

### 13.5 Atamayı kaldır (soft-delete)
| Özellik | Değer |
|---|---|
| **Adres** | `/course-instructors/{id}` |
| **Metod** | `DELETE` |
| **İş** | deleted_date=now. Fiziksel silmez. |
| **İlgili kural** | [R3] 404; zaten pasifse idempotent |

---

## 14. REVIEWS (Değerlendirmeler)

Kurs değerlendirmeleri (puan + yorum). Tüm adresler `/reviews` ile başlar
(Swagger'da **Reviews**). Aktiflik `deleted_date` boş olmasıyla; cevapta
`is_active` (türetilmiş) döner.

> **Not (kapsam):** BİZ FR6. **acc2 uygulandı:** yalnızca kursu satın almış
> (ödemesi COMPLETED) kullanıcı değerlendirebilir → aksi halde **403**. **acc6**
> (ortalama puana dahil) ileride.

### 14.1 Değerlendirme yap
| Özellik | Değer |
|---|---|
| **Adres** | `/reviews` |
| **Metod** | `POST` |
| **İlgili kural** | [R1] rating 1-5 zorunlu→422 (acc4/5); [R-fk] course/user→400; [R-owned] satın almamış→403 (acc2); [R-tek] aktif review varsa→409 (acc3) |

**Örnek istek:** `{ "course_id": 1, "user_id": 3, "rating": 5, "comment": "Cok faydali bir kurstu" }`
**Örnek cevap (201):** `{ "id": 1, "course_id": 1, "user_id": 3, "rating": 5, "comment": "Cok faydali bir kurstu", "is_active": true, "created_date": "2024-03-20 18:00:00", "deleted_date": null }`
**Olası hatalar:** `400` (kurs/kullanıcı yok), `403` (satın almamış), `409` (zaten aktif değerlendirme), `422` (rating eksik/aralık dışı).

### 14.2 Değerlendirmeleri listele
| Özellik | Değer |
|---|---|
| **Adres** | `/reviews` |
| **Metod** | `GET` |
| **Filtreler** | `course_id`, `user_id`, `only_active=true` |

### 14.3 Tek değerlendirme getir
| Özellik | Değer |
|---|---|
| **Adres** | `/reviews/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] 404 |

### 14.4 Değerlendirmeyi güncelle
| Özellik | Değer |
|---|---|
| **Adres** | `/reviews/{id}` |
| **Metod** | `PUT` |
| **İş** | rating + comment güncellenir (acc7). |
| **İlgili kural** | [R3] 404; [R1] rating 1-5→422 |

**Örnek istek:** `{ "rating": 4, "comment": "Icerik guzel ama biraz hizli" }`

### 14.5 Değerlendirmeyi kaldır (soft-delete)
| Özellik | Değer |
|---|---|
| **Adres** | `/reviews/{id}` |
| **Metod** | `DELETE` |
| **İş** | deleted_date=now (acc7). Sonra kullanıcı tekrar değerlendirebilir. |
| **İlgili kural** | [R3] 404; zaten pasifse idempotent |

---

## 15. CARTS (Sepetler)

Kullanıcı sepeti — kullanıcı başına en fazla bir sepet. Tüm adresler `/carts`
ile başlar (Swagger'da **Carts**).

> **Not (kaynak/kapsam):** Excel'de `is_active`/`deleted_date` yok; "tek aktif
> sepet" (FR7 acc1) `user_id` benzersizliğiyle uygulanır. Sepet hem açık
> `POST /carts` ile, hem de CART_ITEMS adımında "sepete ekle" sırasında otomatik
> (lazy) oluşturulur.

### 15.1 Sepet oluştur
| Özellik | Değer |
|---|---|
| **Adres** | `/carts` |
| **Metod** | `POST` |
| **İlgili kural** | [R-user] user yok→400; [R-tek] kullanıcının sepeti varsa→409 (acc1) |

**Örnek istek:** `{ "user_id": 3 }`
**Örnek cevap (201):** `{ "id": 1, "user_id": 3, "created_date": "2024-03-01 13:00:00" }`
**Olası hatalar:** `400` (kullanıcı yok), `409` (zaten sepeti var).

### 15.2 Sepetleri listele
| Özellik | Değer |
|---|---|
| **Adres** | `/carts` (opsiyonel: `?user_id=3`) |
| **Metod** | `GET` |

### 15.3 Tek sepet getir
| Özellik | Değer |
|---|---|
| **Adres** | `/carts/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] 404 |

---

## 16. CART_ITEMS (Sepet Kalemleri)

Sepetteki kurslar. Tüm adresler `/cart-items` ile başlar (Swagger'da **Cart Items**).
"Sepete ekle" `{user_id, course_id}` alır; kullanıcının sepeti yoksa otomatik oluşur.

> **Not (kapsam):** BİZ FR7. **acc4 uygulandı:** zaten satın alınmış (ödemesi
> COMPLETED) kurs sepete eklenemez → **409**. Çıkarma kalıcı silmedir (Excel'de
> soft-delete yok).

### 16.1 Sepete kurs ekle
| Özellik | Değer |
|---|---|
| **Adres** | `/cart-items` |
| **Metod** | `POST` |
| **İlgili kural** | [R-user]/[R-course] yok→400; lazy sepet (acc1/acc2); [R-dup] aynı kurs→409 (acc3); [R-owned] satın alınmış→409 (acc4) |

**Örnek istek:** `{ "user_id": 3, "course_id": 1 }`
**Örnek cevap (201):** `{ "id": 1, "cart_id": 1, "course_id": 1, "created_date": "2024-03-01 13:05:00" }`
**Olası hatalar:** `400` (kullanıcı/kurs yok), `409` (kurs sepette zaten var **veya** zaten satın alınmış).

### 16.2 Sepet kalemlerini listele
| Özellik | Değer |
|---|---|
| **Adres** | `/cart-items` (`?cart_id=` veya `?user_id=`) |
| **Metod** | `GET` |

### 16.3 Sepet özeti (toplam tutar — FR7 acc5)
| Özellik | Değer |
|---|---|
| **Adres** | `/cart-items/summary?user_id=3` |
| **Metod** | `GET` |
| **İş** | Kalemler (kurs adı + fiyat) + `item_count` + `total_price`. Sepet yoksa boş özet. |
| **İlgili kural** | [R-user] kullanıcı yok→400 |

**Örnek cevap (200):**
```json
{ "user_id": 3, "cart_id": 1, "items": [ {"course_id": 3, "course_name": "Android Kotlin", "price": 599.0} ], "item_count": 1, "total_price": 599.0 }
```

### 16.4 Tek kalem getir
| Özellik | Değer |
|---|---|
| **Adres** | `/cart-items/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] 404 |

### 16.5 Sepetten kurs çıkar
| Özellik | Değer |
|---|---|
| **Adres** | `/cart-items/{id}` |
| **Metod** | `DELETE` |
| **İş** | Kalemi **kalıcı** siler (FR7 acc6). |
| **İlgili kural** | [R3] 404 |

---

## 17. ORDERS (Siparişler)

Kesinleşmiş siparişler (immutable). Tüm adresler `/orders` ile başlar (Swagger'da
**Orders**). Güncelleme/silme yoktur.

> **Not (kapsam):** BİZ FR8. Gerçek siparişler checkout akışıyla üretilir; tutar/
> kalem tutarlılığı (acc6) checkout adımında garanti edilecek. Bu manuel CRUD
> temel işlemler içindir.

### 17.1 Sipariş oluştur
| Özellik | Değer |
|---|---|
| **Adres** | `/orders` |
| **Metod** | `POST` |
| **İlgili kural** | [R1] total_price≥0→422; [R-user] user yok→400 |

**Örnek istek:** `{ "user_id": 3, "total_price": 799.4 }`
**Örnek cevap (201):** `{ "id": 1, "user_id": 3, "total_price": 799.4, "created_date": "2024-03-15 14:25:00" }`
**Olası hatalar:** `400` (kullanıcı yok), `422` (total_price < 0).

### 17.2 Siparişleri listele
| Özellik | Değer |
|---|---|
| **Adres** | `/orders` (opsiyonel: `?user_id=3`) |
| **Metod** | `GET` |

### 17.3 Tek sipariş getir
| Özellik | Değer |
|---|---|
| **Adres** | `/orders/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] 404 |

---

## 18. ORDER_ITEMS (Sipariş Kalemleri)

Siparişe ait kurslar; her kalem kursun **sipariş anındaki fiyatını** (`unit_price`)
saklar (snapshot). Tüm adresler `/order-items` ile başlar (Swagger'da **Order
Items**). Immutable → güncelleme/silme yoktur.

### 18.1 Sipariş kalemi oluştur
| Özellik | Değer |
|---|---|
| **Adres** | `/order-items` |
| **Metod** | `POST` |
| **İlgili kural** | [R1] unit_price≥0→422; [R-order]/[R-course] yok→400; [R-dup] aynı kurs aynı siparişte→409 |

**Örnek istek:** `{ "order_id": 1, "course_id": 1, "unit_price": 499.9 }`
**Örnek cevap (201):** `{ "id": 1, "order_id": 1, "course_id": 1, "unit_price": 499.9, "created_date": "2024-03-15 14:25:00" }`
**Olası hatalar:** `400` (sipariş/kurs yok), `409` (kurs siparişte zaten var), `422` (unit_price<0).

### 18.2 Sipariş kalemlerini listele
| Özellik | Değer |
|---|---|
| **Adres** | `/order-items` (`?order_id=` / `?course_id=`) |
| **Metod** | `GET` |

### 18.3 Tek kalem getir
| Özellik | Değer |
|---|---|
| **Adres** | `/order-items/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] 404 |

---

## 19. PAYMENTS (Ödemeler)

Sipariş ödemeleri (sipariş başına bir ödeme). Tüm adresler `/payments` ile başlar
(Swagger'da **Payments**). Yeni ödeme otomatik **PENDING** başlar.

> **Not (kapsam):** BİZ FR8. Durum geçişi yan etkileri (sepet pasife, kurs erişimi,
> iade — acc8-11) checkout/erişim akışına bırakıldı. Payment'ta user tutulmaz;
> kullanıcıya Payment→Order→User zinciriyle ulaşılır.

### 19.1 Ödeme oluştur
| Özellik | Değer |
|---|---|
| **Adres** | `/payments` |
| **Metod** | `POST` |
| **İlgili kural** | [R1] address→422 (acc3); [R-order] 400; [R-tek] order'ın ödemesi varsa→409 (§3.11); [R-method] pasif/yok→400 (acc2); durum otomatik PENDING (acc7) |

**Örnek istek:** `{ "order_id": 1, "payment_method_id": 1, "address": "Istanbul Kadikoy Moda Cad. No:12" }`
**Örnek cevap (201):** `{ "id": 1, "order_id": 1, "payment_method_id": 1, "payment_status_id": 1, "payment_date": "2024-03-15 14:30:00", "address": "Istanbul Kadikoy Moda Cad. No:12", "created_date": "2024-03-15 14:30:00" }`
**Olası hatalar:** `400` (sipariş yok / yöntem pasif), `409` (siparişin ödemesi var veya PENDING durumu tanımlı değil), `422` (address boş).

### 19.2 Ödemeleri listele
| Özellik | Değer |
|---|---|
| **Adres** | `/payments` (opsiyonel: `?order_id=1`) |
| **Metod** | `GET` |

### 19.3 Tek ödeme getir
| Özellik | Değer |
|---|---|
| **Adres** | `/payments/{id}` |
| **Metod** | `GET` |
| **İlgili kural** | [R3] 404 |

### 19.4 Ödeme durumunu değiştir
| Özellik | Değer |
|---|---|
| **Adres** | `/payments/{id}/status` |
| **Metod** | `PATCH` |
| **İş** | Durumu değiştirir (örn. COMPLETED/FAILED/REFUNDED). |
| **İlgili kural** | [R3] 404; yeni durum aktif değilse→400 |

**Örnek istek:** `{ "payment_status_id": 2 }`

---

## 20. CHECKOUT (Sepeti Siparişe Dönüştürme — FR8)

Sepetten tek adımda sipariş + kalemler + ödeme üretir ve sepeti temizler.

### 20.1 Checkout
| Özellik | Değer |
|---|---|
| **Adres** | `/orders/checkout` |
| **Metod** | `POST` |
| **Ne işe yarar** | Sepeti siparişe dönüştürür: ORDER + ORDER_ITEM'lar (fiyat snapshot) + PENDING PAYMENT; sepeti temizler. |
| **İlgili FR** | FR8 acc3/acc4/acc5/acc6/acc7 |

**Örnek istek:**
```json
{ "user_id": 3, "payment_method_id": 1, "address": "Istanbul Kadikoy Moda Cad. No:12" }
```
**Örnek cevap (201):**
```json
{
  "order": { "id": 1, "user_id": 3, "total_price": 799.4, "created_date": "2024-03-15 14:25:00" },
  "items": [
    { "id": 1, "order_id": 1, "course_id": 1, "unit_price": 499.9, "created_date": "2024-03-15 14:25:00" },
    { "id": 2, "order_id": 1, "course_id": 2, "unit_price": 299.5, "created_date": "2024-03-15 14:25:00" }
  ],
  "payment": { "id": 1, "order_id": 1, "payment_method_id": 1, "payment_status_id": 1, "payment_date": "2024-03-15 14:30:00", "address": "Istanbul Kadikoy Moda Cad. No:12", "created_date": "2024-03-15 14:30:00" },
  "item_count": 2,
  "total_price": 799.4
}
```
**Olası hatalar:**
| Kod | Anlamı |
|---|---|
| 400 | Geçersiz `user_id` veya pasif/geçersiz `payment_method_id` |
| 409 | Sepet boş (checkout yapılamaz) veya aktif `PENDING` durumu tanımlı değil |
| 422 | Doğrulama hatası (`address` boş) |

---

## 21. AUTH — Giriş (FR2)

### 21.1 Login
| Özellik | Değer |
|---|---|
| **Adres** | `/auth/login` |
| **Metod** | `POST` |
| **Ne işe yarar** | E-posta + şifre ile giriş; kimlik + aktif roller döner. |
| **İlgili FR** | FR2 acc1–acc10 |

> **Not:** Token/JWT yoktur; login yalnızca kimliği doğrular ve rolleri döndürür.

**Örnek istek:** `{ "mail": "ahmet@elearning.com", "password": "GizliSifre123", "confirm_reactivation": false }`
**Örnek cevap (200, başarılı):**
```json
{ "success": true, "reactivation_required": false, "user_id": 1, "full_name": "Ahmet Yilmaz", "mail": "ahmet@elearning.com", "roles": ["Student", "Instructor"], "message": "Giriş başarılı." }
```
**Örnek cevap (200, silinmiş hesap — onay gerekli):** `{ "success": false, "reactivation_required": true, ... }` → `confirm_reactivation=true` ile tekrar gönderilir.
**Olası hatalar:** `401` (e-posta/şifre hatalı veya saklama süresi dolmuş hesap), `403` (kara listede).

---

## 22. COURSES — Katalog ve Detay (FR4 / FR5)

### 22.1 Kurs kataloğu (FR4)
| Özellik | Değer |
|---|---|
| **Adres** | `/courses/catalog` |
| **Metod** | `GET` |
| **Filtreler** | `q` (kurs adı **veya** eğitmen adı), `category_id`, `language_id`, `difficulty_id`, `min_price`, `max_price` |
| **Sıralama** | `sort` = `popularity` (varsayılan), `price`, `rating`, `newest` |
| **Sayfalama** | `page` (1'den), sayfa başına 12 |

**Örnek cevap (200):**
```json
{ "items": [ { "id": 1, "course_name": "Spring Boot ile REST API", "category_id": 2, "language_id": 1, "difficulty_id": 2, "price": 499.9, "primary_instructor": "Ahmet Yilmaz", "average_rating": 4.5, "review_count": 12 } ], "page": 1, "page_size": 12, "total": 37, "total_pages": 4, "sort": "popularity" }
```
**Olası hatalar:** `400` (min_price > max_price veya geçersiz `sort`).

### 22.2 Kurs detayı (FR5)
| Özellik | Değer |
|---|---|
| **Adres** | `/courses/{id}/detail` (opsiyonel: `?viewer_user_id=`) |
| **Metod** | `GET` |
| **Ne işe yarar** | Kurs + ortalama puan + değerlendirme sayısı + aktif eğitmenler + aktif yorumlar. |
| **İlgili kural** | [R3] yok→404; pasif kurs erişim sahibi olmayana→404 (acc4) |

**Örnek cevap (200):**
```json
{ "id": 1, "course_name": "Spring Boot ile REST API", "description": "...", "price": 499.9, "category_id": 2, "language_id": 1, "difficulty_id": 2, "is_active": true, "average_rating": 4.5, "review_count": 12, "instructors": [ { "instructor_id": 1, "full_name": "Ahmet Yilmaz", "is_primary": true } ], "reviews": [ { "id": 1, "user_id": 3, "rating": 5, "comment": "...", "created_date": "..." } ] }
```

---

## 23. USERS — Sahip Olunan Kurslar (erişim)

### 23.1 Kullanıcının kursları
| Özellik | Değer |
|---|---|
| **Adres** | `/users/{id}/courses` |
| **Metod** | `GET` |
| **Ne işe yarar** | Kullanıcının erişim sahibi olduğu (ödemesi COMPLETED) kurslar. |
| **İlgili kural** | [R3] kullanıcı yok→404; erişim COMPLETED'dan türetilir (FR8 acc8/10/11) |

**Örnek cevap (200):** `[ { "id": 1, "course_name": "Spring Boot ile REST API", "price": 499.9, ... } ]`

---

## 24. Hata Kodları Sözlüğü

İş kuralları eklendikçe aşağıdaki HTTP kodları kullanılacaktır:

| Kod | Anlamı | Ne zaman döner |
|---|---|---|
| 200 | OK | İşlem başarılı |
| 201 | Created | Yeni kayıt başarıyla oluşturuldu |
| 400 | Bad Request | Geçersiz/eksik veri (genel) |
| 404 | Not Found | İşaret edilen kayıt bulunamadı (örn. olmayan bir FK) |
| 409 | Conflict | Mükerrer kayıt / kural çakışması (örn. aynı isim+eğitmen+fiyat) |
| 422 | Unprocessable Entity | Doğrulama (validation) hatası (Pydantic) |
