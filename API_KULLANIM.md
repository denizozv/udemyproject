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
> `is_active` kolonuna dayanır. "Kullanımdaki dil pasife alınamaz" kuralı (R4)
> `COURSES` tablosu eklendiğinde devreye girecektir.

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

## 5. Hata Kodları Sözlüğü (ileride kullanılacak)

İş kuralları eklendikçe aşağıdaki HTTP kodları kullanılacaktır:

| Kod | Anlamı | Ne zaman döner |
|---|---|---|
| 200 | OK | İşlem başarılı |
| 201 | Created | Yeni kayıt başarıyla oluşturuldu |
| 400 | Bad Request | Geçersiz/eksik veri (genel) |
| 404 | Not Found | İşaret edilen kayıt bulunamadı (örn. olmayan bir FK) |
| 409 | Conflict | Mükerrer kayıt / kural çakışması (örn. aynı isim+eğitmen+fiyat) |
| 422 | Unprocessable Entity | Doğrulama (validation) hatası (Pydantic) |
