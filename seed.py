"""
seed.py
-------
Örnek (demo) veri yükleyici. Excel'deki örnek kayıtları veritabanına ekler ki
yeni gelen kişi uygulamayı açar açmaz dolu bir sistemde Swagger'dan deneme yapsın.

Çalıştırma:  py seed.py     (veya: python seed.py)

NOT:
- IDEMPOTENT: Veritabanında zaten veri varsa (roles dolu) hiçbir şey yapmaz.
  Sıfırdan yüklemek için önce db.sqlite dosyasını silin, sonra tekrar çalıştırın.
- Excel'deki bcrypt şifre hash'leri kullanılamaz (farklı algoritma). Tüm demo
  kullanıcılara ortak DEMO ŞİFRESİ atanır ve PBKDF2 ile hash'lenir:
      DEMO ŞİFRESİ = "Sifre1234"
  Yani örn. ahmet@elearning.com / Sifre1234 ile login olunabilir.
"""

from database import get_connection, init_db
from security import hash_password

DEMO_SIFRE = "Sifre1234"


def seed() -> None:
    init_db()  # tablolar yoksa oluştur
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Idempotent koruma: zaten veri varsa çık.
        if cur.execute("SELECT COUNT(*) AS n FROM roles").fetchone()["n"] > 0:
            print("Veritabanında zaten veri var; seed atlandı. "
                  "(Sıfırdan yüklemek için db.sqlite'ı silip tekrar çalıştırın.)")
            return

        sifre = hash_password(DEMO_SIFRE)

        # --- ROLES ---
        cur.executemany(
            "INSERT INTO roles (id, name, is_active, created_date) VALUES (?, ?, ?, ?)",
            [
                (1, "Admin", 1, "2024-01-01 10:00:00"),
                (2, "Instructor", 1, "2024-01-01 10:00:00"),
                (3, "Student", 1, "2024-01-01 10:00:00"),
            ],
        )

        # --- LANGUAGES ---
        cur.executemany(
            "INSERT INTO languages (id, language_name, is_active, created_date) VALUES (?, ?, ?, ?)",
            [
                (1, "Turkce", 1, "2024-01-03 09:00:00"),
                (2, "Ingilizce", 1, "2024-01-03 09:00:00"),
                (3, "Almanca", 1, "2024-01-03 09:00:00"),
            ],
        )

        # --- DIFFICULTY_LEVELS ---
        cur.executemany(
            "INSERT INTO difficulty_levels (id, code, name, is_active, created_date) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "BEGINNER", "Baslangic", 1, "2024-01-01 10:00:00"),
                (2, "INTERMEDIATE", "Orta", 1, "2024-01-01 10:00:00"),
                (3, "ADVANCED", "Ileri", 1, "2024-01-01 10:00:00"),
            ],
        )

        # --- PAYMENT_METHODS ---
        cur.executemany(
            "INSERT INTO payment_methods (id, code, name, is_active, created_date) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "CREDIT_CARD", "Kredi Karti", 1, "2024-01-01 10:00:00"),
                (2, "DEBIT_CARD", "Banka Karti", 1, "2024-01-01 10:00:00"),
                (3, "BANK_TRANSFER", "Havale/EFT", 1, "2024-01-01 10:00:00"),
            ],
        )

        # --- PAYMENT_STATUSES ---
        cur.executemany(
            "INSERT INTO payment_statuses (id, code, name, is_active, created_date) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "PENDING", "Beklemede", 1, "2024-01-01 10:00:00"),
                (2, "COMPLETED", "Tamamlandi", 1, "2024-01-01 10:00:00"),
                (3, "FAILED", "Basarisiz", 1, "2024-01-01 10:00:00"),
                (4, "REFUNDED", "Iade Edildi", 1, "2024-01-01 10:00:00"),
            ],
        )

        # --- CATEGORIES (önce kök kategoriler 1 ve 4, sonra çocuklar) ---
        cur.executemany(
            "INSERT INTO categories (id, parent_id, name, is_active, created_date) VALUES (?, ?, ?, ?, ?)",
            [
                (1, None, "Yazilim", 1, "2024-01-03 10:00:00"),
                (4, None, "Tasarim", 1, "2024-01-03 10:10:00"),
                (2, 1, "Web Gelistirme", 1, "2024-01-03 10:05:00"),
                (3, 1, "Mobil Gelistirme", 1, "2024-01-03 10:06:00"),
                (5, 4, "UI/UX", 1, "2024-01-03 10:12:00"),
            ],
        )

        # --- USERS (password_hash demo şifresinden) ---
        cur.executemany(
            "INSERT INTO users (id, full_name, mail, password_hash, phone, birth_date, is_active, created_date, deleted_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "Ahmet Yilmaz", "ahmet@elearning.com", sifre, "05321112233", "1985-04-12", 1, "2024-01-05 09:20:00", None),
                (2, "Elif Demir", "elif@elearning.com", sifre, "05334445566", "1990-08-22", 1, "2024-01-06 11:45:00", None),
                (3, "Mehmet Kaya", "mehmet@gmail.com", sifre, "05357778899", "1998-01-30", 1, "2024-02-10 14:10:00", None),
                (4, "Zeynep Sahin", "zeynep@gmail.com", sifre, "05360001122", "2000-11-05", 0, "2024-02-11 16:35:00", "2024-05-01 10:00:00"),
                (5, "Deniz Oz", "deniz@elearning.com", sifre, "05373334455", "1992-06-18", 1, "2024-01-02 08:00:00", None),
                (6, "Can Yildiz", "can@gmail.com", sifre, "05381234567", "1995-07-14", 1, "2024-05-10 12:00:00", None),
            ],
        )

        # --- USER_ROLES ---
        cur.executemany(
            "INSERT INTO user_roles (id, user_id, role_id, created_date, deleted_date) VALUES (?, ?, ?, ?, ?)",
            [
                (1, 3, 3, "2024-02-10 14:10:00", None),
                (2, 4, 3, "2024-02-11 16:35:00", None),
                (3, 2, 2, "2024-01-06 11:45:00", None),
                (4, 1, 2, "2024-01-05 09:20:00", None),
                (5, 1, 1, "2024-01-10 09:00:00", None),
                (6, 5, 3, "2024-01-02 08:00:00", None),
                (7, 5, 2, "2024-03-01 10:00:00", None),
                (8, 6, 3, "2024-05-10 12:00:00", None),
            ],
        )

        # --- BLACKLIST ---
        cur.executemany(
            "INSERT INTO blacklist (id, user_id, banned_by, reason, ban_until, is_active, created_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 6, 1, "Spam icerik paylasimi", None, 1, "2024-05-15 09:00:00"),
                (2, 3, 1, "Tekrarli sikayet", "2024-04-01 00:00:00", 0, "2024-03-01 09:00:00"),
            ],
        )

        # --- COURSES ---
        cur.executemany(
            "INSERT INTO courses (id, category_id, language_id, course_name, price, description, difficulty_id, is_active, created_date, deleted_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 2, 1, "Spring Boot ile REST API", 499.9, "Sifirdan REST API gelistirme", 2, 1, "2024-02-01 12:00:00", None),
                (2, 2, 2, "React Temelleri", 299.5, "Modern React ekosistemi", 1, 1, "2024-02-03 12:00:00", None),
                (3, 3, 1, "Android Kotlin", 599.0, "Kotlin ile mobil uygulama", 3, 1, "2024-02-05 12:00:00", None),
                (4, 5, 1, "Figma ile UI Tasarimi", 199.9, "Tasarim sistemleri olusturma", 1, 1, "2024-03-05 12:00:00", None),
            ],
        )

        # --- COURSE_INSTRUCTORS ---
        cur.executemany(
            "INSERT INTO course_instructors (id, course_id, instructor_id, is_primary, created_date, deleted_date) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, 1, 1, 1, "2024-02-01 12:00:00", None),
                (2, 2, 2, 1, "2024-02-03 12:00:00", None),
                (3, 3, 1, 1, "2024-02-05 12:00:00", None),
                (4, 4, 5, 1, "2024-03-05 12:00:00", None),
                (5, 1, 2, 0, "2024-02-15 09:00:00", None),
                (6, 4, 1, 0, "2024-03-10 09:00:00", None),
            ],
        )

        # --- REVIEWS ---
        cur.executemany(
            "INSERT INTO reviews (id, course_id, user_id, rating, comment, created_date, deleted_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 1, 3, 5, "Cok faydali bir kurstu", "2024-03-20 18:00:00", None),
                (2, 2, 3, 5, "React ogrenmek icin ideal", "2024-03-25 21:00:00", None),
                (3, 2, 4, 4, "Icerik guzel ama biraz hizli", "2024-03-21 19:30:00", None),
                (4, 4, 4, 3, "Beklentinin biraz altinda", "2024-03-28 10:15:00", "2024-04-01 09:00:00"),
            ],
        )

        # --- CARTS ---
        cur.executemany(
            "INSERT INTO carts (id, user_id, created_date) VALUES (?, ?, ?)",
            [
                (1, 3, "2024-03-01 13:00:00"),
                (2, 4, "2024-03-02 15:20:00"),
            ],
        )

        # --- CART_ITEMS ---
        cur.executemany(
            "INSERT INTO cart_items (id, cart_id, course_id, created_date) VALUES (?, ?, ?, ?)",
            [
                (1, 1, 3, "2024-03-01 13:05:00"),
                (2, 1, 4, "2024-03-01 13:07:00"),
                (3, 2, 1, "2024-03-02 15:25:00"),
            ],
        )

        # --- ORDERS ---
        cur.executemany(
            "INSERT INTO orders (id, user_id, total_price, created_date) VALUES (?, ?, ?, ?)",
            [
                (1, 3, 799.4, "2024-03-15 14:25:00"),
                (2, 4, 499.4, "2024-04-02 09:10:00"),
            ],
        )

        # --- ORDER_ITEMS ---
        cur.executemany(
            "INSERT INTO order_items (id, order_id, course_id, unit_price, created_date) VALUES (?, ?, ?, ?, ?)",
            [
                (1, 1, 1, 499.9, "2024-03-15 14:25:00"),
                (2, 1, 2, 299.5, "2024-03-15 14:25:00"),
                (3, 2, 2, 299.5, "2024-04-02 09:10:00"),
                (4, 2, 4, 199.9, "2024-04-02 09:10:00"),
            ],
        )

        # --- PAYMENTS ---
        cur.executemany(
            "INSERT INTO payments (id, order_id, payment_method_id, payment_status_id, payment_date, address, created_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 1, 1, 2, "2024-03-15 14:30:00", "Istanbul Kadikoy Moda Cad. No:12", "2024-03-15 14:30:00"),
                (2, 2, 3, 1, "2024-04-02 09:15:00", "Ankara Cankaya Kizilay Sok. No:5", "2024-04-02 09:15:00"),
            ],
        )

        conn.commit()
        print("Seed tamamlandı. Demo şifresi:", DEMO_SIFRE)
        print("Örnek giriş: ahmet@elearning.com /", DEMO_SIFRE)
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
