"""
database.py
-----------
SQLite veritabanı bağlantısını ve tablo oluşturma yardımcılarını içerir.

NOT: Bu projede SQLAlchemy gibi bir ORM KULLANILMAZ.
Python'un yerleşik `sqlite3` modülüyle doğrudan bağlanırız.

Bu dosya bilinçli olarak "altyapı" katmanıdır:
- Veritabanına nasıl bağlanılacağını bilir (get_connection).
- Tabloların nasıl oluşturulacağını bilir (init_db).
- Hangi tabloların var olduğunu bilmez; tablo şemaları entity eklendikçe
  aşağıdaki TABLE_SCHEMAS listesine eklenecektir.
"""

import sqlite3
from pathlib import Path

# Veritabanı dosyasının yolu.
# __file__ = bu dosyanın (database.py) kendi yolu.
# .parent = bu dosyanın bulunduğu klasör (proje kök dizini).
# Sonuç: proje kökünde "db.sqlite" adında bir dosya kullanılır.
DB_PATH = Path(__file__).parent / "db.sqlite"


def get_connection() -> sqlite3.Connection:
    """
    SQLite veritabanına yeni bir bağlantı açar ve döndürür.

    Her istek/işlem için bu fonksiyon çağrılır, işlem bitince bağlantı kapatılır.
    Böylece bağlantılar açık kalıp birbirine karışmaz.
    """
    # sqlite3.connect: db.sqlite dosyasına bağlanır. Dosya yoksa otomatik oluşturulur.
    connection = sqlite3.connect(DB_PATH)

    # row_factory = sqlite3.Row: Sorgu sonuçlarına kolon ADIYLA erişmeyi sağlar.
    # Örn: row["name"]  (sadece row[0] değil). Okunabilirliği artırır.
    connection.row_factory = sqlite3.Row

    # PRAGMA foreign_keys = ON: SQLite'ta yabancı anahtar (FK) kontrolleri
    # varsayılan olarak KAPALIDIR. Bu satır onları açar; böylece ilişki
    # bütünlüğü (referential integrity) veritabanı seviyesinde de korunur.
    connection.execute("PRAGMA foreign_keys = ON;")

    return connection


# -----------------------------------------------------------------------------
# TABLO ŞEMALARI
# -----------------------------------------------------------------------------
# Her entity eklendiğinde, o entity'nin "CREATE TABLE IF NOT EXISTS ..." SQL
# metni bu listeye eklenecektir. Şu an liste BOŞTUR; çünkü henüz hiçbir entity
# tanımlamadık. İskelet bu haliyle hatasız çalışır (oluşturulacak tablo yoktur).
#
# Örnek (sonraki adımlarda eklenecek):
#   """
#   CREATE TABLE IF NOT EXISTS roles (
#       id   INTEGER PRIMARY KEY AUTOINCREMENT,
#       name TEXT NOT NULL UNIQUE
#   );
#   """
TABLE_SCHEMAS: list[str] = [
    # --- ROLES (Adım 2) ---------------------------------------------------
    # Kaynak: Excel "ROLES" tablosu. Kolonlar birebir Excel'den alınmıştır.
    #   id           -> Birincil anahtar (PK). INTEGER + AUTOINCREMENT = otomatik artan.
    #   name         -> Rol adı. Boş olamaz (NOT NULL) ve benzersizdir (UNIQUE).
    #   is_active    -> Aktif mi? SQLite'ta gerçek bool yoktur; 1 = aktif, 0 = pasif.
    #                   Varsayılan 1 (yeni rol aktif oluşturulur).
    #   created_date -> Kaydın oluşturulma tarihi. Değer verilmezse SQLite o anki
    #                   yerel tarih-saati otomatik yazar (datetime('now','localtime')).
    """
    CREATE TABLE IF NOT EXISTS roles (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT    NOT NULL UNIQUE,
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    );
    """,
    # --- LANGUAGES (Adım 3) -----------------------------------------------
    # Kaynak: Excel "LANGUAGES" tablosu. Kolonlar birebir Excel'den alınmıştır.
    #   id            -> Birincil anahtar (PK), otomatik artan.
    #   language_name -> Dil adı. Boş olamaz (NOT NULL) ve benzersizdir (UNIQUE).
    #   is_active     -> 1 = aktif, 0 = pasif. Varsayılan 1.
    #   created_date  -> Verilmezse o anki yerel tarih-saat otomatik yazılır.
    """
    CREATE TABLE IF NOT EXISTS languages (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        language_name TEXT    NOT NULL UNIQUE,
        is_active     INTEGER NOT NULL DEFAULT 1,
        created_date  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    );
    """,
    # --- DIFFICULTY_LEVELS (Adım 4) ---------------------------------------
    # Kaynak: Excel "DIFFICULTY_LEVELS" tablosu. Kolonlar birebir Excel'den.
    #   id           -> Birincil anahtar (PK), otomatik artan.
    #   code         -> Teknik kod (örn. BEGINNER). Boş olamaz + BENZERSİZ (UNIQUE).
    #                   FR10 acc5: aynı kod ile ikinci kayıt eklenemez.
    #   name         -> Görünen ad (örn. Baslangic). Boş olamaz (NOT NULL).
    #                   Not: name UNIQUE DEĞİLDİR; benzersizlik kuralı code üzerindedir.
    #   is_active    -> 1 = aktif, 0 = pasif. Varsayılan 1.
    #   created_date -> Verilmezse o anki yerel tarih-saat otomatik yazılır.
    """
    CREATE TABLE IF NOT EXISTS difficulty_levels (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        code         TEXT    NOT NULL UNIQUE,
        name         TEXT    NOT NULL,
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    );
    """,
    # --- PAYMENT_METHODS (Adım 5) -----------------------------------------
    # Kaynak: Excel "PAYMENT_METHODS". Yapı DIFFICULTY_LEVELS ile birebir aynı.
    #   code -> Boş olamaz + BENZERSİZ (örn. CREDIT_CARD). FR10 acc5.
    #   name -> Görünen ad (örn. Kredi Karti). Boş olamaz.
    """
    CREATE TABLE IF NOT EXISTS payment_methods (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        code         TEXT    NOT NULL UNIQUE,
        name         TEXT    NOT NULL,
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    );
    """,
    # --- PAYMENT_STATUSES (Adım 5) ----------------------------------------
    # Kaynak: Excel "PAYMENT_STATUSES". Yapı DIFFICULTY_LEVELS ile birebir aynı.
    #   code -> Boş olamaz + BENZERSİZ (örn. PENDING). FR10 acc5.
    #   name -> Görünen ad (örn. Beklemede). Boş olamaz.
    """
    CREATE TABLE IF NOT EXISTS payment_statuses (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        code         TEXT    NOT NULL UNIQUE,
        name         TEXT    NOT NULL,
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    );
    """,
    # --- CATEGORIES (Adım 6) ----------------------------------------------
    # Kaynak: Excel "CATEGORIES". İlk SELF-REFERENCING (kendine FK veren) tablo.
    #   id           -> Birincil anahtar (PK), otomatik artan.
    #   parent_id    -> Üst kategori. NULL ise kök (root) kategoridir.
    #                   Doluysa categories.id'ye FK (kendi tablosuna referans).
    #   name         -> Kategori adı. Boş olamaz (NOT NULL).
    #                   Not: BİZ setinde CATEGORIES için isim benzersizliği YOK;
    #                   bu yüzden UNIQUE konmadı.
    #   is_active    -> 1 = aktif, 0 = pasif. Varsayılan 1.
    #   created_date -> Verilmezse o anki yerel tarih-saat otomatik yazılır.
    # FOREIGN KEY (parent_id) -> categories(id): parent'ın gerçekten var olmasını
    #   veritabanı seviyesinde de garanti eder (PRAGMA foreign_keys = ON ile).
    """
    CREATE TABLE IF NOT EXISTS categories (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id    INTEGER,
        name         TEXT    NOT NULL,
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (parent_id) REFERENCES categories(id)
    );
    """,
    # --- USERS (Adım 7) ---------------------------------------------------
    # Kaynak: Excel "USERS". Soft-delete'li çekirdek entity.
    #   id            -> PK, otomatik artan.
    #   full_name     -> Ad soyad. Boş olamaz (NOT NULL).
    #   mail          -> E-posta. Boş olamaz. Benzersizlik İŞ KATMANINDA kontrol
    #                    edilir (DB'de UNIQUE konmadı — bkz. aşağıdaki not).
    #   password_hash -> Şifrenin hash'lenmiş hali (security.py). Düz şifre ASLA
    #                    saklanmaz ve hiçbir cevapta dönmez.
    #   phone         -> Telefon (yalnız rakam). Excel NULL'a izin verse de kayıt
    #                    (register) sırasında BİZ FR1 acc1/acc2 gereği zorunludur.
    #   birth_date    -> Doğum tarihi (YYYY-MM-DD). Gelecek tarih olamaz (acc7).
    #   is_active     -> 1 = aktif, 0 = pasif (soft-delete).
    #   created_date  -> Otomatik.
    #   deleted_date  -> Soft-delete tarihi. NULL = silinmemiş. (FR3)
    #
    # NEDEN mail'e DB-UNIQUE konmadı: Soft-delete + 90 gün saklama kuralı (FR3
    # acc5) gereği, saklama süresi dolduktan sonra aynı e-posta yeniden
    # kullanılabilmelidir. Kayıt silinse de satır fiziksel durduğu için katı bir
    # UNIQUE kısıtı bu yeniden kullanımı engellerdi. Bu yüzden benzersizlik
    # (aktif kullanıcı + saklama penceresi) iş katmanında uygulanır.
    """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name     TEXT    NOT NULL,
        mail          TEXT    NOT NULL,
        password_hash TEXT    NOT NULL,
        phone         TEXT,
        birth_date    TEXT,
        is_active     INTEGER NOT NULL DEFAULT 1,
        created_date  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        deleted_date  TEXT
    );
    """,
    # --- USER_ROLES (Adım 8) ----------------------------------------------
    # Kaynak: Excel "USER_ROLES". Kullanıcı <-> Rol çoka-çok (many-to-many)
    # bağlantı (junction) tablosu.
    #   id           -> PK, otomatik artan.
    #   user_id      -> FK -> users.id. Boş olamaz.
    #   role_id      -> FK -> roles.id. Boş olamaz.
    #   created_date -> Otomatik.
    #   deleted_date -> Soft-delete tarihi. NULL = AKTİF atama. Doluysa rol
    #                   kaldırılmış demektir. (Bu tabloda is_active kolonu YOKTUR;
    #                   aktiflik deleted_date IS NULL ile belirlenir.)
    # FK'lar user/role'ün gerçekten var olmasını DB seviyesinde de garanti eder.
    """
    CREATE TABLE IF NOT EXISTS user_roles (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL,
        role_id      INTEGER NOT NULL,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        deleted_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );
    """,
    # --- BLACKLIST (Adım 9) -----------------------------------------------
    # Kaynak: Excel "BLACKLIST". Kullanıcıların kara listeye alınması.
    #   id           -> PK, otomatik artan.
    #   user_id      -> Yasaklanan kullanıcı. FK -> users.id. Boş olamaz.
    #   banned_by    -> Yasağı uygulayan (admin) kullanıcı. FK -> users.id. Boş olamaz.
    #   reason       -> Yasak gerekçesi. Boş olamaz (FR12 acc3).
    #   ban_until    -> Yasağın bitiş tarih-saati. NULL ise SÜRESİZ yasak (acc4).
    #   is_active    -> 1 = yasak kaydı aktif, 0 = kaldırılmış (soft, acc7).
    #                   NOT: "geçerli yasak" = is_active=1 VE (ban_until NULL veya
    #                   ban_until > şu an). Süresi geçmiş yasak geçerli sayılmaz (acc6).
    #   created_date -> Otomatik.
    """
    CREATE TABLE IF NOT EXISTS blacklist (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL,
        banned_by    INTEGER NOT NULL,
        reason       TEXT    NOT NULL,
        ban_until    TEXT,
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (banned_by) REFERENCES users(id)
    );
    """,
    # --- COURSES (Adım 10) ------------------------------------------------
    # Kaynak: Excel "COURSES". Çok yabancı anahtarlı (FK) içerik tablosu.
    #   id            -> PK, otomatik artan.
    #   category_id   -> FK -> categories.id. Boş olamaz; AKTİF bir kategori olmalı.
    #   language_id   -> FK -> languages.id.  Boş olamaz; AKTİF bir dil olmalı.
    #   course_name   -> Kurs adı. Boş olamaz.
    #   price         -> Fiyat. SQLite'ta REAL (ondalık sayı). FR9 acc3 gereği > 0
    #                    (sıfır veya negatif olamaz).
    #   description   -> Açıklama. NULL olabilir (opsiyonel).
    #   difficulty_id -> FK -> difficulty_levels.id. Boş olamaz; AKTİF olmalı.
    #   is_active     -> 1 = aktif, 0 = pasif (soft-delete).
    #   created_date  -> Otomatik.
    #   deleted_date  -> Soft-delete tarihi. NULL = silinmemiş.
    # NOT: Eğitmen bilgisi COURSES'ta TUTULMAZ; COURSE_INSTRUCTORS tablosunda
    #      (kurs<->eğitmen çoka-çok) tutulacaktır.
    """
    CREATE TABLE IF NOT EXISTS courses (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id   INTEGER NOT NULL,
        language_id   INTEGER NOT NULL,
        course_name   TEXT    NOT NULL,
        price         REAL    NOT NULL,
        description   TEXT,
        difficulty_id INTEGER NOT NULL,
        is_active     INTEGER NOT NULL DEFAULT 1,
        created_date  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        deleted_date  TEXT,
        FOREIGN KEY (category_id)   REFERENCES categories(id),
        FOREIGN KEY (language_id)   REFERENCES languages(id),
        FOREIGN KEY (difficulty_id) REFERENCES difficulty_levels(id)
    );
    """,
    # --- COURSE_INSTRUCTORS (Adım 13) -------------------------------------
    # Kaynak: Excel "COURSE_INSTRUCTORS". Kurs <-> Eğitmen çoka-çok bağlantısı.
    #   id            -> PK, otomatik artan.
    #   course_id     -> FK -> courses.id. Boş olamaz.
    #   instructor_id -> FK -> users.id. Boş olamaz. (Aktif 'Instructor' rolü olmalı.)
    #   is_primary    -> 1 = kursun birincil (asıl) eğitmeni, 0 = yardımcı.
    #                    Bir kursta aynı anda en fazla 1 aktif primary olabilir.
    #   created_date  -> Otomatik.
    #   deleted_date  -> Soft-delete tarihi. NULL = AKTİF atama. (is_active kolonu yok.)
    """
    CREATE TABLE IF NOT EXISTS course_instructors (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id     INTEGER NOT NULL,
        instructor_id INTEGER NOT NULL,
        is_primary    INTEGER NOT NULL DEFAULT 0,
        created_date  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        deleted_date  TEXT,
        FOREIGN KEY (course_id)     REFERENCES courses(id),
        FOREIGN KEY (instructor_id) REFERENCES users(id)
    );
    """,
    # --- REVIEWS (Adım 14) ------------------------------------------------
    # Kaynak: Excel "REVIEWS". Kurs değerlendirmeleri.
    #   id           -> PK, otomatik artan.
    #   course_id    -> FK -> courses.id. Boş olamaz.
    #   user_id      -> FK -> users.id. Boş olamaz.
    #   rating       -> Puan, 1-5 arası (FR6 acc5). Boş olamaz (acc4).
    #   comment      -> Yorum. NULL olabilir (opsiyonel).
    #   created_date -> Otomatik.
    #   deleted_date -> Soft-delete tarihi. NULL = AKTİF değerlendirme.
    # NOT: "Aynı kullanıcı bir kursa tek AKTİF değerlendirme" kuralı (acc3) iş
    #      katmanında uygulanır.
    """
    CREATE TABLE IF NOT EXISTS reviews (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id    INTEGER NOT NULL,
        user_id      INTEGER NOT NULL,
        rating       INTEGER NOT NULL,
        comment      TEXT,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        deleted_date TEXT,
        FOREIGN KEY (course_id) REFERENCES courses(id),
        FOREIGN KEY (user_id)   REFERENCES users(id)
    );
    """,
    # --- CARTS (Adım 15) --------------------------------------------------
    # Kaynak: Excel "CARTS". Kullanıcının sepeti.
    #   id           -> PK, otomatik artan.
    #   user_id      -> FK -> users.id. Boş olamaz ve BENZERSİZ (UNIQUE):
    #                   kullanıcı başına en fazla BİR sepet (FR7 acc1 "tek aktif sepet"
    #                   bu projede tek sepet olarak uygulanır; Excel'de is_active yok).
    #   created_date -> Otomatik.
    # NOT: Sepet kalıcıdır; checkout'ta (sipariş) içeriği (CART_ITEMS) temizlenir,
    #      sepet satırı kullanıcıda kalır ve yeniden kullanılır.
    """
    CREATE TABLE IF NOT EXISTS carts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL UNIQUE,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,
    # --- CART_ITEMS (Adım 16) ---------------------------------------------
    # Kaynak: Excel "CART_ITEMS". Sepetteki kurs kalemleri.
    #   id           -> PK, otomatik artan.
    #   cart_id      -> FK -> carts.id. Boş olamaz.
    #   course_id    -> FK -> courses.id. Boş olamaz.
    #   created_date -> Otomatik.
    # NOT: Excel'de deleted_date YOKTUR -> sepetten çıkarma KALICI silmedir
    #      (FR7 acc6 "CART_ITEM silinir"). Aynı sepette aynı kurs en fazla bir kez
    #      bulunabilir (acc3, iş katmanında kontrol edilir).
    """
    CREATE TABLE IF NOT EXISTS cart_items (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        cart_id      INTEGER NOT NULL,
        course_id    INTEGER NOT NULL,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (cart_id)   REFERENCES carts(id),
        FOREIGN KEY (course_id) REFERENCES courses(id)
    );
    """,
    # --- ORDERS (Adım 17) -------------------------------------------------
    # Kaynak: Excel "ORDERS". Kesinleşmiş sipariş (IMMUTABLE).
    #   id           -> PK, otomatik artan.
    #   user_id      -> FK -> users.id. Boş olamaz.
    #   total_price  -> Sipariş toplam tutarı (REAL). >= 0.
    #                   Tutarlılık (kalemler toplamına eşitlik, FR8 acc6) ve "en az
    #                   bir kalem" kuralı CHECKOUT akışında uygulanır.
    #   created_date -> Otomatik.
    # NOT: Sipariş immutable kabul edilir; güncelleme/silme endpoint'i yoktur.
    """
    CREATE TABLE IF NOT EXISTS orders (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL,
        total_price  REAL    NOT NULL,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,
    # --- ORDER_ITEMS (Adım 18) --------------------------------------------
    # Kaynak: Excel "ORDER_ITEMS". Sipariş kalemleri.
    #   id           -> PK, otomatik artan.
    #   order_id     -> FK -> orders.id. Boş olamaz.
    #   course_id    -> FK -> courses.id. Boş olamaz.
    #   unit_price   -> Kursun SİPARİŞ ANINDAKİ fiyatı (snapshot, FR8 acc5). >= 0.
    #                   Kurs fiyatı sonradan değişse de bu değer sabit kalır.
    #   created_date -> Otomatik.
    # NOT: Sipariş immutable; ORDER_ITEMS için güncelleme/silme endpoint'i yoktur.
    #      Aynı kurs aynı siparişte en fazla bir kez (veri bütünlüğü, iş katmanında).
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id     INTEGER NOT NULL,
        course_id    INTEGER NOT NULL,
        unit_price   REAL    NOT NULL,
        created_date TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (order_id)  REFERENCES orders(id),
        FOREIGN KEY (course_id) REFERENCES courses(id)
    );
    """,
    # --- PAYMENTS (Adım 19) -----------------------------------------------
    # Kaynak: Excel "PAYMENTS". Sipariş ödemesi (Order ile 1:1).
    #   id                -> PK, otomatik artan.
    #   order_id          -> FK -> orders.id. Boş olamaz ve BENZERSİZ (UNIQUE):
    #                        bir siparişin en fazla bir ödemesi olur (FR §3.11).
    #   payment_method_id -> FK -> payment_methods.id. Aktif olmalı (FR8 acc2).
    #   payment_status_id -> FK -> payment_statuses.id. Yeni ödeme PENDING başlar (acc7).
    #   payment_date      -> İşlem (deneme) zaman damgası.
    #   address           -> Adres. Boş olamaz (FR8 acc3).
    #   created_date      -> Otomatik.
    # NOT: Payment'ta userId TUTULMAZ; kullanıcıya Payment -> Order -> User
    #      zinciriyle ulaşılır (veri tekrarını önler).
    """
    CREATE TABLE IF NOT EXISTS payments (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id          INTEGER NOT NULL UNIQUE,
        payment_method_id INTEGER NOT NULL,
        payment_status_id INTEGER NOT NULL,
        payment_date      TEXT    NOT NULL,
        address           TEXT    NOT NULL,
        created_date      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (order_id)          REFERENCES orders(id),
        FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id),
        FOREIGN KEY (payment_status_id) REFERENCES payment_statuses(id)
    );
    """,
]


def init_db() -> None:
    """
    Veritabanını başlatır: TABLE_SCHEMAS içindeki tüm tabloları oluşturur.

    Uygulama her başladığında çağrılır. "IF NOT EXISTS" sayesinde tablolar
    zaten varsa tekrar oluşturulmaz; bu fonksiyonu defalarca çağırmak güvenlidir.
    """
    # Bağlantıyı aç.
    connection = get_connection()
    try:
        # cursor: SQL komutlarını çalıştırmak için kullanılan "imleç" nesnesi.
        cursor = connection.cursor()

        # Listedeki her şema metnini sırayla çalıştır.
        for schema in TABLE_SCHEMAS:
            # executescript: tek seferde birden fazla SQL ifadesi çalıştırabilir.
            cursor.executescript(schema)

        # commit: yapılan değişiklikleri (tablo oluşturma) kalıcı olarak kaydeder.
        connection.commit()
    finally:
        # İşlem başarılı da olsa hata da alsa bağlantıyı mutlaka kapat.
        connection.close()
