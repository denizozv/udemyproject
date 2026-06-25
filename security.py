"""
security.py
-----------
Şifre güvenliği yardımcıları (ek bağımlılık YOK — yalnızca Python'un yerleşik
hashlib/os/hmac modülleri kullanılır).

NEDEN: Düz (plain) şifre asla veritabanına yazılmaz. Bunun yerine şifre,
geri döndürülemez şekilde "hash"lenir. Burada PBKDF2-SHA256 + rastgele "salt"
(tuz) kullanılır; bu yöntem kaba kuvvet saldırılarına karşı yavaş ve güvenlidir.

Saklanan format (tek bir metin):
    pbkdf2_sha256$<iterasyon>$<salt_hex>$<hash_hex>
Örn: pbkdf2_sha256$200000$9f3a...$c81d...
"""

import hashlib
import hmac
import os
import secrets

# Hash parametreleri.
_ALGORITHM = "sha256"     # özet (digest) algoritması
_ITERATIONS = 200_000      # PBKDF2 tur sayısı (ne kadar yüksekse o kadar yavaş = güvenli)
_SALT_BYTES = 16           # her şifre için rastgele tuz uzunluğu (bayt)


def hash_password(plain_password: str) -> str:
    """
    Düz şifreyi alır, rastgele bir salt üretip PBKDF2 ile hash'ler ve
    saklanabilir tek bir metin döndürür.
    """
    # os.urandom: kriptografik olarak güçlü rastgele bayt üretir (salt için).
    salt = os.urandom(_SALT_BYTES)
    # pbkdf2_hmac: şifre + salt'ı _ITERATIONS kez işleyip türetilmiş anahtar (dk) üretir.
    derived = hashlib.pbkdf2_hmac(
        _ALGORITHM, plain_password.encode("utf-8"), salt, _ITERATIONS
    )
    # Salt ve hash'i hex metne çevirip parçaları '$' ile birleştir.
    return f"pbkdf2_{_ALGORITHM}${_ITERATIONS}${salt.hex()}${derived.hex()}"


def generate_token() -> str:
    """
    Login'de üretilen rastgele, tahmin edilemez (opak) bearer token döndürür.
    secrets.token_urlsafe kriptografik olarak güçlüdür; ~43 karakterlik URL-güvenli
    bir metin verir. Token veritabanındaki sessions tablosunda saklanır.
    """
    return secrets.token_urlsafe(32)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Kullanıcının girdiği düz şifrenin, saklanan hash ile eşleşip eşleşmediğini
    kontrol eder. (Giriş/login akışında — FR2 — kullanılacak.)
    """
    try:
        # Saklanan metni 4 parçaya ayır: "pbkdf2_sha256", iterasyon, salt, hash.
        prefix, iterations_str, salt_hex, hash_hex = stored_hash.split("$")
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        algorithm = prefix.split("_", 1)[1]  # "pbkdf2_sha256" -> "sha256"
        # Aynı salt ve parametrelerle yeniden hash'le.
        derived = hashlib.pbkdf2_hmac(
            algorithm, plain_password.encode("utf-8"), salt, iterations
        )
        # compare_digest: zamanlama saldırılarına karşı güvenli karşılaştırma.
        return hmac.compare_digest(derived, expected)
    except Exception:
        # Saklanan metin bozuksa/biçimsizse güvenli tarafta kal: eşleşme yok.
        return False
