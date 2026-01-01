"""
PiSecure Device Identity
=======================

Main device identity management combining hardware fingerprints,
certificates, and authentication for secure device identification.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from .fingerprint import DeviceFingerprint
from .certificates import CertificateManager


class DeviceIdentity:
    """Comprehensive device identity management"""

    def __init__(self, identity_file: str = "/var/lib/pisecure/device_identity.json"):
        self.identity_file = Path(identity_file)
        self.identity_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.fingerprint = DeviceFingerprint()
        self.certificates = CertificateManager()

        # Load existing identity
        self.identity_data = self._load_identity()

    def initialize_device(self, device_name: str = None, organization: str = "PiSecure Network",
                         auto_generate_cert: bool = True) -> Dict[str, Any]:
        """
        Initialize device identity

        Args:
            device_name: Custom device name (optional)
            organization: Organization name
            auto_generate_cert: Automatically generate certificate

        Returns:
            Initialization result
        """
        try:
            # Generate hardware fingerprint
            fingerprint = self.fingerprint.generate_fingerprint(force_refresh=True)
            fingerprint_info = self.fingerprint.get_fingerprint_info()

            # Generate device ID
            device_id = device_name or f"pi-{fingerprint[:16]}"

            # Initialize certificate authority if needed
            ca_result = self.certificates.initialize_ca(organization=organization)

            identity_data = {
                'device_id': device_id,
                'device_name': device_name,
                'organization': organization,
                'fingerprint': fingerprint,
                'fingerprint_confidence': fingerprint_info['confidence_score'],
                'initialized_at': time.time(),
                'version': '1.0',
                'capabilities': self._detect_capabilities(),
                'certificate_status': 'none'
            }

            # Generate device certificate if requested
            if auto_generate_cert:
                cert_result = self.certificates.generate_device_certificate(
                    device_id=device_id,
                    device_fingerprint=fingerprint,
                    device_info={
                        'organization': organization,
                        'location': 'Auto-detected'
                    }
                )

                if cert_result['success']:
                    identity_data['certificate_status'] = 'active'
                    identity_data['certificate_fingerprint'] = cert_result['cert_fingerprint']
                    identity_data['certificate_issued'] = time.time()
                else:
                    identity_data['certificate_error'] = cert_result.get('error')

            # Save identity
            self.identity_data = identity_data
            self._save_identity(identity_data)

            return {
                'success': True,
                'device_id': device_id,
                'fingerprint': fingerprint,
                'certificate_generated': auto_generate_cert and identity_data.get('certificate_status') == 'active',
                'identity_file': str(self.identity_file)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _detect_capabilities(self) -> List[str]:
        """Detect device capabilities"""
        capabilities = []

        # Check hardware verification
        try:
            from ..core.hardware import HardwareVerifier
            hw_verifier = HardwareVerifier()
            hw_result = hw_verifier.verify_mining_eligibility()

            if hw_result['eligible']:
                capabilities.append('mining')
                capabilities.append('blockchain')

                # Check specific hardware
                if 'Pi 5' in hw_result['hardware_model']:
                    capabilities.append('high_performance')
                elif 'Pi 4' in hw_result['hardware_model']:
                    capabilities.append('standard_performance')
        except:
            pass

        # Check for TPM
        try:
            import subprocess
            result = subprocess.run(['tpm2_pcrread'], capture_output=True, timeout=2)
            if result.returncode == 0:
                capabilities.append('tpm')
                capabilities.append('secure_boot')
        except:
            pass

        # Check for GPIO
        try:
            with open('/dev/gpiomem', 'rb'):
                capabilities.append('gpio')
                capabilities.append('iot_device')
        except:
            pass

        # Always include basic capabilities
        capabilities.extend([
            'networking',
            'cryptography',
            'identity_management'
        ])

        return list(set(capabilities))  # Remove duplicates

    def get_identity(self) -> Dict[str, Any]:
        """Get current device identity information"""
        if not self.identity_data:
            return {'error': 'Device not initialized'}

        # Add current status
        identity = self.identity_data.copy()

        # Check certificate status
        if identity.get('certificate_status') == 'active':
            device_id = identity.get('device_id')
            cert_info = self.certificates.load_device_certificate(device_id)
            if cert_info:
                cert = cert_info['certificate']
                identity['certificate'] = {
                    'serial': str(cert.serial_number),
                    'not_before': cert.not_valid_before.isoformat(),
                    'not_after': cert.not_valid_after.isoformat(),
                    'fingerprint': cert.fingerprint(hashes.SHA256()).hex()
                }
            else:
                identity['certificate_status'] = 'missing'

        # Add fingerprint verification
        fingerprint_check = self.fingerprint.verify_fingerprint_integrity(
            identity.get('fingerprint', '')
        )
        identity['fingerprint_verification'] = fingerprint_check

        return identity

    def verify_identity(self) -> Dict[str, Any]:
        """
        Verify complete device identity integrity

        Returns:
            Verification result
        """
        identity = self.get_identity()
        if 'error' in identity:
            return {
                'verified': False,
                'error': identity['error']
            }

        issues = []
        warnings = []

        # Check fingerprint integrity
        fp_verification = identity.get('fingerprint_verification', {})
        if not fp_verification.get('verified', False):
            issues.append('Hardware fingerprint mismatch - possible tampering')

        # Check certificate status
        cert_status = identity.get('certificate_status')
        if cert_status != 'active':
            issues.append(f'Certificate status: {cert_status}')
        else:
            # Check certificate validity
            cert_info = identity.get('certificate', {})
            if cert_info:
                try:
                    import datetime
                    not_after = datetime.datetime.fromisoformat(cert_info['not_after'])
                    if datetime.datetime.utcnow() > not_after:
                        issues.append('Certificate expired')
                    elif (not_after - datetime.datetime.utcnow()).days < 30:
                        warnings.append('Certificate expires soon')
                except:
                    warnings.append('Could not verify certificate expiration')

        # Check capabilities still available
        current_capabilities = self._detect_capabilities()
        original_capabilities = identity.get('capabilities', [])
        lost_capabilities = set(original_capabilities) - set(current_capabilities)
        if lost_capabilities:
            warnings.append(f'Lost capabilities: {", ".join(lost_capabilities)}')

        return {
            'verified': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'capabilities': current_capabilities,
            'identity': identity
        }

    def update_identity(self, updates: Dict[str, Any]) -> bool:
        """
        Update device identity information

        Args:
            updates: Dictionary of updates to apply

        Returns:
            Success status
        """
        try:
            # Validate updates
            allowed_updates = {
                'device_name', 'organization', 'capabilities'
            }

            filtered_updates = {
                k: v for k, v in updates.items()
                if k in allowed_updates
            }

            if filtered_updates:
                self.identity_data.update(filtered_updates)
                self.identity_data['updated_at'] = time.time()
                self._save_identity(self.identity_data)
                return True

            return False

        except Exception as e:
            print(f"Failed to update identity: {e}")
            return False

    def export_identity(self, export_path: str) -> bool:
        """
        Export device identity for backup or sharing

        Args:
            export_path: Path to export identity data

        Returns:
            Success status
        """
        try:
            export_data = {
                'identity': self.get_identity(),
                'exported_at': time.time(),
                'version': '1.0'
            }

            # Include certificate if available
            device_id = self.identity_data.get('device_id')
            if device_id:
                cert_chain_path = f"{export_path}.chain.pem"
                if self.certificates.export_certificate_chain(device_id, cert_chain_path):
                    export_data['certificate_chain'] = cert_chain_path

            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            return True

        except Exception as e:
            print(f"Failed to export identity: {e}")
            return False

    def import_identity(self, import_path: str) -> bool:
        """
        Import device identity from backup

        Args:
            import_path: Path to import identity data

        Returns:
            Success status
        """
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)

            identity = import_data.get('identity')
            if not identity:
                return False

            # Validate identity structure
            required_fields = ['device_id', 'fingerprint']
            if not all(field in identity for field in required_fields):
                return False

            # Update identity
            self.identity_data = identity
            self._save_identity(identity)

            return True

        except Exception as e:
            print(f"Failed to import identity: {e}")
            return False

    def rotate_certificate(self) -> Dict[str, Any]:
        """
        Rotate device certificate for security

        Returns:
            Certificate rotation result
        """
        try:
            device_id = self.identity_data.get('device_id')
            fingerprint = self.identity_data.get('fingerprint')

            if not device_id or not fingerprint:
                return {
                    'success': False,
                    'error': 'Device identity not properly initialized'
                }

            # Generate new certificate
            cert_result = self.certificates.generate_device_certificate(
                device_id=device_id,
                device_fingerprint=fingerprint,
                device_info={
                    'organization': self.identity_data.get('organization', 'PiSecure Network'),
                    'location': 'Certificate Rotation'
                }
            )

            if cert_result['success']:
                # Update identity data
                self.identity_data['certificate_fingerprint'] = cert_result['cert_fingerprint']
                self.identity_data['certificate_rotated_at'] = time.time()
                self._save_identity(self.identity_data)

                return {
                    'success': True,
                    'new_fingerprint': cert_result['cert_fingerprint'],
                    'rotated_at': time.time()
                }
            else:
                return {
                    'success': False,
                    'error': cert_result.get('error')
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _load_identity(self) -> Optional[Dict[str, Any]]:
        """Load device identity from file"""
        try:
            if self.identity_file.exists():
                with open(self.identity_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load identity: {e}")
        return None

    def _save_identity(self, identity_data: Dict[str, Any]) -> None:
        """Save device identity to file"""
        try:
            with open(self.identity_file, 'w') as f:
                json.dump(identity_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save identity: {e}")

    def get_capabilities(self) -> List[str]:
        """Get current device capabilities"""
        return self._detect_capabilities()

    def is_initialized(self) -> bool:
        """Check if device identity is initialized"""
        return self.identity_data is not None and 'device_id' in self.identity_data