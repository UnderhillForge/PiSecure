"""
PiSecure Certificate Management
===============================

X.509 certificate generation, signing, and validation for device identity
and mutual authentication in Raspberry Pi networks.
"""

import datetime
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.backends import default_backend


class CertificateManager:
    """X.509 certificate management for device identity"""

    def __init__(self, cert_dir: str = "/var/lib/pisecure/certificates",
                 key_dir: str = "/var/lib/pisecure/keys"):
        self.cert_dir = Path(cert_dir)
        self.key_dir = Path(key_dir)

        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self.key_dir.mkdir(parents=True, exist_ok=True)

        # Certificate Authority settings
        self.ca_cert_file = self.cert_dir / "ca.crt"
        self.ca_key_file = self.key_dir / "ca.key"

        # Device certificates
        self.device_cert_dir = self.cert_dir / "devices"
        self.device_key_dir = self.key_dir / "devices"
        self.device_cert_dir.mkdir(exist_ok=True)
        self.device_key_dir.mkdir(exist_ok=True)

    def initialize_ca(self, organization: str = "PiSecure Network",
                     common_name: str = "PiSecure CA") -> Dict[str, Any]:
        """
        Initialize Certificate Authority for the network

        Args:
            organization: Organization name for CA
            common_name: Common name for CA certificate

        Returns:
            CA initialization result
        """
        try:
            # Check if CA already exists
            if self.ca_cert_file.exists() and self.ca_key_file.exists():
                return {
                    'success': True,
                    'message': 'CA already initialized',
                    'ca_cert': str(self.ca_cert_file),
                    'ca_key': str(self.ca_key_file)
                }

            # Generate CA private key
            ca_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            # Generate CA certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ])

            ca_cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                ca_private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365*10)  # 10 years
            ).add_extension(
                x509.SubjectKeyIdentifier.from_public_key(ca_private_key.public_key()),
                critical=False
            ).add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                    x509.SubjectKeyIdentifier.from_public_key(ca_private_key.public_key())
                ),
                critical=False
            ).add_extension(
                x509.BasicConstraints(ca=True, path_length=3),
                critical=True
            ).add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_cert_sign=True,
                    crl_sign=True
                ),
                critical=True
            ).sign(ca_private_key, hashes.SHA256(), default_backend())

            # Save CA certificate
            with open(self.ca_cert_file, 'wb') as f:
                f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

            # Save CA private key
            with open(self.ca_key_file, 'wb') as f:
                f.write(ca_private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            return {
                'success': True,
                'message': 'CA initialized successfully',
                'ca_cert': str(self.ca_cert_file),
                'ca_key': str(self.ca_key_file),
                'ca_fingerprint': ca_cert.fingerprint(hashes.SHA256()).hex()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def generate_device_certificate(self, device_id: str, device_fingerprint: str,
                                  device_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate X.509 certificate for a device

        Args:
            device_id: Unique device identifier
            device_fingerprint: Hardware fingerprint
            device_info: Additional device information

        Returns:
            Certificate generation result
        """
        try:
            # Load CA certificate and key
            if not self.ca_cert_file.exists() or not self.ca_key_file.exists():
                return {
                    'success': False,
                    'error': 'CA not initialized. Run initialize_ca() first.'
                }

            with open(self.ca_cert_file, 'rb') as f:
                ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

            with open(self.ca_key_file, 'rb') as f:
                ca_private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend())

            # Generate device private key
            device_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            # Device certificate subject
            device_info = device_info or {}
            organization = device_info.get('organization', 'PiSecure Devices')
            location = device_info.get('location', 'Unknown')

            subject = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, location),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, device_id),
            ])

            # Generate device certificate
            device_cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                ca_cert.subject
            ).public_key(
                device_private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365*2)  # 2 years
            ).add_extension(
                x509.SubjectKeyIdentifier.from_public_key(device_private_key.public_key()),
                critical=False
            ).add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                    ca_cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_KEY_IDENTIFIER).value
                ),
                critical=False
            ).add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True
            ).add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    data_encipherment=True
                ),
                critical=True
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtensionOID.CLIENT_AUTH,
                    x509.oid.ExtensionOID.SERVER_AUTH
                ]),
                critical=False
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(device_id),
                    x509.DNSName(f"{device_id}.pisecure.local"),
                ]),
                critical=False
            ).sign(ca_private_key, hashes.SHA256(), default_backend())

            # Save device certificate
            cert_file = self.device_cert_dir / f"{device_id}.crt"
            with open(cert_file, 'wb') as f:
                f.write(device_cert.public_bytes(serialization.Encoding.PEM))

            # Save device private key
            key_file = self.device_key_dir / f"{device_id}.key"
            with open(key_file, 'wb') as f:
                f.write(device_private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            # Create certificate metadata
            metadata = {
                'device_id': device_id,
                'fingerprint': device_fingerprint,
                'cert_serial': str(device_cert.serial_number),
                'issued_at': device_cert.not_valid_before.isoformat(),
                'expires_at': device_cert.not_valid_after.isoformat(),
                'cert_file': str(cert_file),
                'key_file': str(key_file),
                'ca_fingerprint': ca_cert.fingerprint(hashes.SHA256()).hex(),
                'created_at': datetime.datetime.utcnow().isoformat()
            }

            metadata_file = self.device_cert_dir / f"{device_id}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            return {
                'success': True,
                'device_id': device_id,
                'cert_file': str(cert_file),
                'key_file': str(key_file),
                'cert_fingerprint': device_cert.fingerprint(hashes.SHA256()).hex(),
                'metadata': metadata
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def load_device_certificate(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Load device certificate and metadata"""
        try:
            metadata_file = self.device_cert_dir / f"{device_id}.json"
            cert_file = self.device_cert_dir / f"{device_id}.crt"
            key_file = self.device_key_dir / f"{device_id}.key"

            if not all([metadata_file.exists(), cert_file.exists(), key_file.exists()]):
                return None

            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Load certificate
            with open(cert_file, 'rb') as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())

            # Load private key
            with open(key_file, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend())

            return {
                'metadata': metadata,
                'certificate': cert,
                'private_key': private_key,
                'cert_pem': cert_file.read_text(),
                'key_pem': key_file.read_text()
            }

        except Exception as e:
            print(f"Failed to load device certificate {device_id}: {e}")
            return None

    def validate_device_certificate(self, cert_pem: str, device_id: str = None) -> Dict[str, Any]:
        """
        Validate a device certificate

        Args:
            cert_pem: PEM-encoded certificate
            device_id: Expected device ID (optional)

        Returns:
            Validation result
        """
        try:
            # Load certificate
            cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())

            # Load CA certificate for validation
            if not self.ca_cert_file.exists():
                return {
                    'valid': False,
                    'error': 'CA certificate not found'
                }

            with open(self.ca_cert_file, 'rb') as f:
                ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

            # Validate certificate chain
            try:
                ca_cert.public_key().verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    cert.signature_hash_algorithm,
                    default_backend()
                )
            except:
                return {
                    'valid': False,
                    'error': 'Certificate signature verification failed'
                }

            # Check expiration
            now = datetime.datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                return {
                    'valid': False,
                    'error': 'Certificate expired or not yet valid'
                }

            # Check device ID if provided
            if device_id:
                cert_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                if not cert_cn or cert_cn[0].value != device_id:
                    return {
                        'valid': False,
                        'error': f'Certificate CN mismatch: expected {device_id}, got {cert_cn[0].value if cert_cn else "None"}'
                    }

            # Check extensions
            try:
                basic_constraints = cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
                if basic_constraints.value.ca:
                    return {
                        'valid': False,
                        'error': 'Certificate has CA constraints (device cert should not)'
                    }
            except:
                pass  # Extension not present, that's OK

            return {
                'valid': True,
                'device_id': cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
                'issuer': cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
                'serial': str(cert.serial_number),
                'not_before': cert.not_valid_before.isoformat(),
                'not_after': cert.not_valid_after.isoformat(),
                'fingerprint': cert.fingerprint(hashes.SHA256()).hex()
            }

        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    def revoke_certificate(self, device_id: str, reason: str = "unspecified") -> bool:
        """
        Revoke a device certificate

        Args:
            device_id: Device to revoke certificate for
            reason: Revocation reason

        Returns:
            Success status
        """
        try:
            metadata_file = self.device_cert_dir / f"{device_id}.json"
            if not metadata_file.exists():
                return False

            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Mark as revoked
            metadata['revoked'] = True
            metadata['revoked_at'] = datetime.datetime.utcnow().isoformat()
            metadata['revocation_reason'] = reason

            # Save updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Move certificate files to revoked directory
            revoked_dir = self.cert_dir / "revoked"
            revoked_dir.mkdir(exist_ok=True)

            import shutil

            # Move files
            cert_file = self.device_cert_dir / f"{device_id}.crt"
            key_file = self.device_key_dir / f"{device_id}.key"

            if cert_file.exists():
                shutil.move(str(cert_file), str(revoked_dir / f"{device_id}.crt.revoked"))

            if key_file.exists():
                shutil.move(str(key_file), str(revoked_dir / f"{device_id}.key.revoked"))

            return True

        except Exception as e:
            print(f"Failed to revoke certificate for {device_id}: {e}")
            return False

    def list_certificates(self) -> List[Dict[str, Any]]:
        """List all device certificates"""
        certificates = []

        try:
            for metadata_file in self.device_cert_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        certificates.append(metadata)
                except:
                    continue
        except Exception as e:
            print(f"Failed to list certificates: {e}")

        return certificates

    def get_ca_certificate(self) -> Optional[str]:
        """Get CA certificate in PEM format"""
        try:
            if self.ca_cert_file.exists():
                return self.ca_cert_file.read_text()
        except:
            pass
        return None

    def export_certificate_chain(self, device_id: str, export_path: str) -> bool:
        """
        Export device certificate with CA certificate for external use

        Args:
            device_id: Device ID
            export_path: Path to export certificate chain

        Returns:
            Success status
        """
        try:
            device_cert = self.load_device_certificate(device_id)
            ca_cert_pem = self.get_ca_certificate()

            if not device_cert or not ca_cert_pem:
                return False

            # Combine certificates
            cert_chain = device_cert['cert_pem'] + "\n" + ca_cert_pem

            with open(export_path, 'w') as f:
                f.write(cert_chain)

            return True

        except Exception as e:
            print(f"Failed to export certificate chain: {e}")
            return False