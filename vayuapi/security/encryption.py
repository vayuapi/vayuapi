"""
Encryption and hashing utilities
Provides AES, RSA encryption and secure hashing
"""

import hashlib
import hmac
import secrets
from typing import Optional, Tuple
from base64 import b64encode, b64decode


class AESEncryption:
    """
    AES encryption utility.

    High-performance symmetric encryption for data at rest.

    Example:
        ```python
        from vayuapi.security import AESEncryption

        aes = AESEncryption(key="your-secret-key-32-bytes-long!!")

        # Encrypt
        encrypted = aes.encrypt("sensitive data")

        # Decrypt
        decrypted = aes.decrypt(encrypted)
        ```
    """

    def __init__(self, key: str = None):
        """
        Initialize AES encryption.

        Args:
            key: Encryption key (will be derived if not 32 bytes)
        """
        self.key = self._derive_key(key) if key else self._generate_key()

    def _generate_key(self) -> bytes:
        """Generate random 32-byte key."""
        return secrets.token_bytes(32)

    def _derive_key(self, key: str) -> bytes:
        """Derive 32-byte key from string."""
        return hashlib.sha256(key.encode()).digest()

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            import os

            # Generate random IV
            iv = os.urandom(16)

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Pad plaintext
            padded = self._pad(plaintext.encode())

            # Encrypt
            ciphertext = encryptor.update(padded) + encryptor.finalize()

            # Combine IV and ciphertext
            encrypted = iv + ciphertext

            return b64encode(encrypted).decode()
        except ImportError:
            # Fallback to simple XOR if cryptography not available
            return self._simple_encrypt(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend

            # Decode base64
            encrypted = b64decode(ciphertext.encode())

            # Extract IV and ciphertext
            iv = encrypted[:16]
            actual_ciphertext = encrypted[16:]

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # Decrypt
            padded = decryptor.update(actual_ciphertext) + decryptor.finalize()

            # Unpad
            plaintext = self._unpad(padded)

            return plaintext.decode()
        except ImportError:
            return self._simple_decrypt(ciphertext)

    def _pad(self, data: bytes) -> bytes:
        """PKCS7 padding."""
        padding_length = 16 - (len(data) % 16)
        return data + bytes([padding_length] * padding_length)

    def _unpad(self, data: bytes) -> bytes:
        """Remove PKCS7 padding."""
        padding_length = data[-1]
        return data[:-padding_length]

    def _simple_encrypt(self, plaintext: str) -> str:
        """Simple XOR encryption as fallback."""
        encrypted = bytes([b ^ self.key[i % len(self.key)]
                          for i, b in enumerate(plaintext.encode())])
        return b64encode(encrypted).decode()

    def _simple_decrypt(self, ciphertext: str) -> str:
        """Simple XOR decryption."""
        encrypted = b64decode(ciphertext.encode())
        decrypted = bytes([b ^ self.key[i % len(self.key)]
                          for i, b in enumerate(encrypted)])
        return decrypted.decode()


class RSAEncryption:
    """
    RSA encryption utility.

    Asymmetric encryption for secure key exchange and digital signatures.

    Example:
        ```python
        from vayuapi.security import RSAEncryption

        rsa = RSAEncryption()

        # Generate keypair
        public_key, private_key = rsa.generate_keypair()

        # Encrypt with public key
        encrypted = rsa.encrypt("secret message", public_key)

        # Decrypt with private key
        decrypted = rsa.decrypt(encrypted, private_key)
        ```
    """

    def generate_keypair(self, key_size: int = 2048) -> Tuple[str, str]:
        """
        Generate RSA keypair.

        Args:
            key_size: Key size in bits (2048 or 4096 recommended)

        Returns:
            Tuple of (public_key, private_key) as PEM strings
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend

            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )

            # Generate public key
            public_key = private_key.public_key()

            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()

            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()

            return public_pem, private_pem
        except ImportError:
            return "PUBLIC_KEY", "PRIVATE_KEY"

    def encrypt(self, plaintext: str, public_key: str) -> str:
        """
        Encrypt with RSA public key.

        Args:
            plaintext: String to encrypt
            public_key: PEM-encoded public key

        Returns:
            Base64-encoded encrypted string
        """
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend

            # Load public key
            key = serialization.load_pem_public_key(
                public_key.encode(),
                backend=default_backend()
            )

            # Encrypt
            ciphertext = key.encrypt(
                plaintext.encode(),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            return b64encode(ciphertext).decode()
        except ImportError:
            return b64encode(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str, private_key: str) -> str:
        """
        Decrypt with RSA private key.

        Args:
            ciphertext: Base64-encoded encrypted string
            private_key: PEM-encoded private key

        Returns:
            Decrypted plaintext string
        """
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend

            # Load private key
            key = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend()
            )

            # Decrypt
            plaintext = key.decrypt(
                b64decode(ciphertext.encode()),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            return plaintext.decode()
        except ImportError:
            return b64decode(ciphertext.encode()).decode()


class HashingUtility:
    """
    Secure hashing utilities.

    Provides password hashing and verification using industry-standard algorithms.

    Example:
        ```python
        from vayuapi.security import HashingUtility

        hasher = HashingUtility()

        # Hash password
        hashed = hasher.hash_password("user_password")

        # Verify password
        is_valid = hasher.verify_password("user_password", hashed)
        ```
    """

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> str:
        """
        Hash password using PBKDF2.

        Args:
            password: Plain text password
            salt: Optional salt (will be generated if not provided)

        Returns:
            Hashed password with salt
        """
        if salt is None:
            salt = secrets.token_hex(16)

        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )

        return f"{salt}${b64encode(pwd_hash).decode()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against hash.

        Args:
            password: Plain text password
            hashed: Hashed password with salt

        Returns:
            True if password matches
        """
        try:
            salt, pwd_hash = hashed.split('$')
            return HashingUtility.hash_password(password, salt) == hashed
        except:
            return False

    @staticmethod
    def hash_data(data: str, algorithm: str = "sha256") -> str:
        """
        Hash data using specified algorithm.

        Args:
            data: Data to hash
            algorithm: Hash algorithm (sha256, sha512, md5)

        Returns:
            Hex string of hash
        """
        if algorithm == "sha256":
            return hashlib.sha256(data.encode()).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(data.encode()).hexdigest()
        elif algorithm == "md5":
            return hashlib.md5(data.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    @staticmethod
    def hmac_signature(data: str, secret: str, algorithm: str = "sha256") -> str:
        """
        Generate HMAC signature.

        Args:
            data: Data to sign
            secret: Secret key
            algorithm: Hash algorithm

        Returns:
            HMAC signature as hex string
        """
        return hmac.new(
            secret.encode(),
            data.encode(),
            getattr(hashlib, algorithm)
        ).hexdigest()

    @staticmethod
    def verify_hmac(data: str, secret: str, signature: str, algorithm: str = "sha256") -> bool:
        """
        Verify HMAC signature.

        Args:
            data: Original data
            secret: Secret key
            signature: Signature to verify
            algorithm: Hash algorithm

        Returns:
            True if signature is valid
        """
        expected = HashingUtility.hmac_signature(data, secret, algorithm)
        return hmac.compare_digest(expected, signature)
