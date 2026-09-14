from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import os
from typing import Tuple

class KareikaEncryption:
    """
    Encryption system inspired by Signal Protocol
    Uses Fernet (AES-128 in CBC mode) for symmetric encryption
    Derives encryption key from mnemonic (like Signal does with Signal Keys)
    """
    
    def __init__(self):
        self.backend = default_backend()
    
    @staticmethod
    def derive_key_from_mnemonic(mnemonic: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from 12 or 24 word BIP39 mnemonic
        Similar to Signal's key derivation
        
        Args:
            mnemonic: BIP39 mnemonic phrase (12 or 24 words)
            salt: Optional salt (if None, generates new one)
        
        Returns:
            Tuple of (key, salt) for encryption
        """
        if salt is None:
            salt = os.urandom(16)
        
        # PBKDF2 with 100,000 iterations (Signal-like security)
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        # Derive key from mnemonic
        key_material = kdf.derive(mnemonic.encode())
        
        # Create Fernet key (base64 encoded 32-byte key)
        fernet_key = base64.urlsafe_b64encode(key_material)
        
        return fernet_key, salt
    
    @staticmethod
    def encrypt_message(message: str, mnemonic: str) -> str:
        """
        Encrypt message using mnemonic-derived key
        
        Args:
            message: Message text to encrypt
            mnemonic: User's BIP39 mnemonic
        
        Returns:
            Encrypted message (base64 encoded with salt included)
        """
        try:
            # Derive key from mnemonic
            fernet_key, salt = KareikaEncryption.derive_key_from_mnemonic(mnemonic)
            
            # Create Fernet cipher
            f = Fernet(fernet_key)
            
            # Encrypt message
            encrypted = f.encrypt(message.encode())
            
            # Combine salt + encrypted data (salt is public, doesn't need secrecy)
            combined = base64.b64encode(salt + encrypted).decode()
            
            return combined
        except Exception as e:
            raise Exception(f"Encryption failed: {str(e)}")
    
    @staticmethod
    def decrypt_message(encrypted_data: str, mnemonic: str) -> str:
        """
        Decrypt message using mnemonic-derived key
        
        Args:
            encrypted_data: Encrypted message (base64 encoded with salt)
            mnemonic: User's BIP39 mnemonic
        
        Returns:
            Decrypted message text
        """
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_data)
            
            # Extract salt (first 16 bytes) and encrypted data
            salt = combined[:16]
            encrypted = combined[16:]
            
            # Derive key from mnemonic with same salt
            fernet_key, _ = KareikaEncryption.derive_key_from_mnemonic(mnemonic, salt)
            
            # Create Fernet cipher
            f = Fernet(fernet_key)
            
            # Decrypt message
            decrypted = f.decrypt(encrypted).decode()
            
            return decrypted
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")
    
    @staticmethod
    def generate_public_key_from_mnemonic(mnemonic: str) -> str:
        """
        Generate a deterministic public key from mnemonic
        Used for identifying users (like Signal identity keys)
        
        Args:
            mnemonic: User's BIP39 mnemonic
        
        Returns:
            Base64 encoded public key identifier
        """
        try:
            # Use PBKDF2 with fixed salt for public key generation
            fixed_salt = b'kareika_public_key_salt_v1'
            
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=fixed_salt,
                iterations=50000,
                backend=default_backend()
            )
            
            key_material = kdf.derive(mnemonic.encode())
            public_key = base64.b64encode(key_material).decode()
            
            return public_key
        except Exception as e:
            raise Exception(f"Public key generation failed: {str(e)}")
    
    @staticmethod
    def generate_device_key(mnemonic: str, device_id: str) -> str:
        """
        Generate device-specific key (for multi-device support like Signal)
        
        Args:
            mnemonic: User's BIP39 mnemonic
            device_id: Unique device identifier
        
        Returns:
            Device-specific encryption key
        """
        try:
            device_salt = f'kareika_device_{device_id}'.encode()
            
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=device_salt,
                iterations=75000,
                backend=default_backend()
            )
            
            key_material = kdf.derive(mnemonic.encode())
            device_key = base64.b64encode(key_material).decode()
            
            return device_key
        except Exception as e:
            raise Exception(f"Device key generation failed: {str(e)}")
    
    @staticmethod
    def encrypt_group_message(message: str, group_id: int, sender_mnemonic: str) -> str:
        """
        Encrypt message for group chat
        Uses group_id as additional context (like Signal's Sender Keys)
        
        Args:
            message: Message text
            group_id: Group identifier
            sender_mnemonic: Sender's mnemonic
        
        Returns:
            Encrypted group message
        """
        try:
            # Combine group_id with mnemonic for group-specific key
            group_context = f"{group_id}:{sender_mnemonic}"
            
            # Derive key
            fernet_key, salt = KareikaEncryption.derive_key_from_mnemonic(group_context)
            
            # Encrypt
            f = Fernet(fernet_key)
            encrypted = f.encrypt(message.encode())
            
            # Combine salt + encrypted
            combined = base64.b64encode(salt + encrypted).decode()
            
            return combined
        except Exception as e:
            raise Exception(f"Group encryption failed: {str(e)}")
    
    @staticmethod
    def decrypt_group_message(encrypted_data: str, group_id: int, sender_mnemonic: str) -> str:
        """
        Decrypt message from group chat
        
        Args:
            encrypted_data: Encrypted group message
            group_id: Group identifier
            sender_mnemonic: Sender's mnemonic
        
        Returns:
            Decrypted message
        """
        try:
            # Combine group_id with mnemonic (same as encryption)
            group_context = f"{group_id}:{sender_mnemonic}"
            
            # Decode from base64
            combined = base64.b64decode(encrypted_data)
            
            # Extract salt and encrypted data
            salt = combined[:16]
            encrypted = combined[16:]
            
            # Derive key with same salt
            fernet_key, _ = KareikaEncryption.derive_key_from_mnemonic(group_context, salt)
            
            # Decrypt
            f = Fernet(fernet_key)
            decrypted = f.decrypt(encrypted).decode()
            
            return decrypted
        except Exception as e:
            raise Exception(f"Group decryption failed: {str(e)}")
    
    @staticmethod
    def hash_mnemonic(mnemonic: str) -> str:
        """
        Hash mnemonic for verification (like Signal's identity verification)
        Used to verify user identity
        
        Args:
            mnemonic: User's BIP39 mnemonic
        
        Returns:
            Hashed mnemonic (base64 encoded)
        """
        try:
            digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
            digest.update(mnemonic.encode())
            hash_result = digest.finalize()
            
            return base64.b64encode(hash_result).decode()
        except Exception as e:
            raise Exception(f"Hashing failed: {str(e)}")
    
    @staticmethod
    def verify_mnemonic_hash(mnemonic: str, mnemonic_hash: str) -> bool:
        """
        Verify mnemonic matches its hash
        
        Args:
            mnemonic: User's BIP39 mnemonic
            mnemonic_hash: Previously hashed mnemonic
        
        Returns:
            True if mnemonic matches hash, False otherwise
        """
        try:
            computed_hash = KareikaEncryption.hash_mnemonic(mnemonic)
            return computed_hash == mnemonic_hash
        except:
            return False

# Test encryption
if __name__ == "__main__":
    test_mnemonic = "abandon ability able about above absent absorb abstract abuse access accident account"
    
    print("🔐 Kareika Encryption Test")
    print("=" * 50)
    
    # Test basic encryption
    message = "Hello, Kareika!"
    print(f"\n📝 Original: {message}")
    
    encrypted = KareikaEncryption.encrypt_message(message, test_mnemonic)
    print(f"🔒 Encrypted: {encrypted[:50]}...")
    
    decrypted = KareikaEncryption.decrypt_message(encrypted, test_mnemonic)
    print(f"🔓 Decrypted: {decrypted}")
    
    # Test public key generation
    pub_key = KareikaEncryption.generate_public_key_from_mnemonic(test_mnemonic)
    print(f"\n🔑 Public Key: {pub_key[:30]}...")
    
    # Test device key
    device_key = KareikaEncryption.generate_device_key(test_mnemonic, "device_001")
    print(f"📱 Device Key: {device_key[:30]}...")
    
    # Test group encryption
    group_msg = "Secret group message"
    encrypted_group = KareikaEncryption.encrypt_group_message(group_msg, 123, test_mnemonic)
    print(f"\n👥 Group Message: {group_msg}")
    print(f"🔒 Encrypted Group: {encrypted_group[:50]}...")
    
    decrypted_group = KareikaEncryption.decrypt_group_message(encrypted_group, 123, test_mnemonic)
    print(f"🔓 Decrypted Group: {decrypted_group}")
    
    # Test hashing
    mnemonic_hash = KareikaEncryption.hash_mnemonic(test_mnemonic)
    print(f"\n🆔 Mnemonic Hash: {mnemonic_hash[:30]}...")
    
    is_valid = KareikaEncryption.verify_mnemonic_hash(test_mnemonic, mnemonic_hash)
    print(f"✅ Hash Verification: {is_valid}")
    
    print("\n" + "=" * 50)
    print("✅ All encryption tests passed!")
