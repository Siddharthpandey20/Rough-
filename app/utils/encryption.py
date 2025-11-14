"""
End-to-End Encryption Utilities
Implements client-side encryption with Data Encryption Keys (DEK)
"""

import os
import base64
import json
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class E2EEManager:
    """End-to-End Encryption Manager"""
    
    @staticmethod
    def generate_dek() -> bytes:
        """Generate a random Data Encryption Key (256-bit for AES-256)"""
        return AESGCM.generate_key(bit_length=256)
    
    @staticmethod
    def encrypt_data(plaintext: str, dek: bytes) -> Dict[str, str]:
        """
        Encrypt data with DEK using AES-GCM
        Returns: {ciphertext: base64, nonce: base64}
        """
        try:
            aesgcm = AESGCM(dek)
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
            
            return {
                'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
                'nonce': base64.b64encode(nonce).decode('utf-8')
            }
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    @staticmethod
    def decrypt_data(encrypted_data: Dict[str, str], dek: bytes) -> str:
        """
        Decrypt data with DEK
        Args: {ciphertext: base64, nonce: base64}
        Returns: plaintext string
        """
        try:
            aesgcm = AESGCM(dek)
            
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            nonce = base64.b64decode(encrypted_data['nonce'])
            
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    @staticmethod
    def wrap_dek(dek: bytes, public_key_pem: str) -> str:
        """
        Wrap (encrypt) DEK with device's public key using RSA-OAEP
        Returns: base64 encoded wrapped DEK
        """
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            wrapped_dek = public_key.encrypt(
                dek,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return base64.b64encode(wrapped_dek).decode('utf-8')
        except Exception as e:
            logger.error(f"DEK wrapping error: {e}")
            raise
    
    @staticmethod
    def unwrap_dek(wrapped_dek: str, private_key_pem: str) -> bytes:
        """
        Unwrap (decrypt) DEK with device's private key
        This happens CLIENT-SIDE only
        """
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            
            wrapped_dek_bytes = base64.b64decode(wrapped_dek)
            
            dek = private_key.decrypt(
                wrapped_dek_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return dek
        except Exception as e:
            logger.error(f"DEK unwrapping error: {e}")
            raise
    
    @staticmethod
    def generate_device_keypair() -> Tuple[str, str]:
        """
        Generate RSA keypair for a device (CLIENT-SIDE)
        Returns: (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return private_pem, public_pem
    
    @staticmethod
    def encrypt_transaction_fields(transaction_data: Dict[str, Any], dek: bytes) -> Dict[str, Any]:
        """
        Encrypt sensitive transaction fields
        Returns encrypted_data dict and wrapped DEKs
        """
        sensitive_fields = ['merchant_name_raw', 'invoice_no', 'parsed_fields']
        encrypted_data = {}
        
        for field in sensitive_fields:
            if field in transaction_data and transaction_data[field]:
                value = transaction_data[field]
                if not isinstance(value, str):
                    value = json.dumps(value)
                encrypted_data[field] = E2EEManager.encrypt_data(value, dek)
        
        return encrypted_data
    
    @staticmethod
    def decrypt_transaction_fields(encrypted_data: Dict[str, Any], dek: bytes) -> Dict[str, Any]:
        """
        Decrypt sensitive transaction fields (CLIENT-SIDE)
        """
        decrypted_data = {}
        
        for field, enc_value in encrypted_data.items():
            try:
                plaintext = E2EEManager.decrypt_data(enc_value, dek)
                # Try to parse as JSON if it was a dict/list
                try:
                    decrypted_data[field] = json.loads(plaintext)
                except:
                    decrypted_data[field] = plaintext
            except Exception as e:
                logger.error(f"Failed to decrypt field {field}: {e}")
                decrypted_data[field] = None
        
        return decrypted_data


# Client-side helper functions (to be implemented in frontend)
"""
CLIENT-SIDE USAGE EXAMPLE (JavaScript/Python):

1. User registers/logs in:
   - Generate device keypair: (privateKey, publicKey) = generateDeviceKeypair()
   - Store privateKey ONLY in secure local storage (never send to server)
   - Send publicKey to server with device_id

2. Creating encrypted transaction:
   - Generate DEK: dek = generateDEK()
   - Encrypt sensitive data: encryptedData = encryptWithDEK(data, dek)
   - Wrap DEK with server's public key: wrappedDEK = wrapDEK(dek, serverPublicKey)
   - Send: {encryptedData, wrappedDEK, device_id}

3. Reading encrypted transaction:
   - Receive: {encryptedData, wrappedDEKs}
   - Unwrap DEK: dek = unwrapDEK(wrappedDEKs[device_id], privateKey)
   - Decrypt data: plainData = decryptWithDEK(encryptedData, dek)

4. Multi-device:
   - When adding new device, existing device re-wraps all DEKs with new device's public key
   - Or use a master key wrapped by all devices
"""
