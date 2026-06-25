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
