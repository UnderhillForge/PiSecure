"""
PiSecure Device Fingerprint
===========================

Hardware-bound device fingerprinting using exclusive Raspberry Pi features
for unique device identification and tamper detection.
"""

import hashlib
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional


class DeviceFingerprint:
    """Hardware-based device fingerprinting for Raspberry Pi"""

    def __init__(self, cache_file: str = "/var/lib/pisecure/device_fingerprint.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Fingerprint components with weights for uniqueness
        self.fingerprint_components = {
            'cpu_serial': {'weight': 0.20, 'required': True},
            'hardware_rng': {'weight': 0.15, 'required': False},
            'videocore_info': {'weight': 0.15, 'required': True},
            'mac_addresses': {'weight': 0.10, 'required': False},
            'otp_registers': {'weight': 0.10, 'required': False},
            'tpm_data': {'weight': 0.10, 'required': False},  # Future TPM support
            'storage_info': {'weight': 0.10, 'required': False},
            'system_uuid': {'weight': 0.10, 'required': False}
        }

        # Cached fingerprint data
        self._cached_fingerprint = None
        self._fingerprint_data = {}

    def generate_fingerprint(self, force_refresh: bool = False) -> str:
        """
        Generate unique device fingerprint from hardware features

        Args:
            force_refresh: Force regeneration instead of using cache

        Returns:
            SHA256 hash of combined hardware features
        """
        if not force_refresh and self._cached_fingerprint:
            return self._cached_fingerprint

        # Collect all hardware features
        fingerprint_data = self._collect_hardware_features()

        # Store for inspection
        self._fingerprint_data = fingerprint_data

        # Create deterministic fingerprint string
        components = []
        for component_name in sorted(fingerprint_data.keys()):
            if fingerprint_data[component_name]['present']:
                value = fingerprint_data[component_name]['value']
                components.append(f"{component_name}:{value}")

        # Add timestamp salt for uniqueness
        timestamp_salt = str(int(time.time() // (24 * 60 * 60)))  # Daily salt
        components.append(f"salt:{timestamp_salt}")

        # Generate final fingerprint
        fingerprint_string = "|".join(components)
        fingerprint = hashlib.sha256(fingerprint_string.encode()).hexdigest()

        # Cache result
        self._cached_fingerprint = fingerprint
        self._save_fingerprint_cache(fingerprint, fingerprint_data)

        return fingerprint

    def _collect_hardware_features(self) -> Dict[str, Any]:
        """Collect all hardware fingerprint components"""
        features = {}

        # CPU Serial Number (most unique)
        features['cpu_serial'] = self._get_cpu_serial()

        # Hardware RNG sample
        features['hardware_rng'] = self._get_hardware_rng_sample()

        # VideoCore GPU information
        features['videocore_info'] = self._get_videocore_info()

        # MAC addresses
        features['mac_addresses'] = self._get_mac_addresses()

        # OTP registers
        features['otp_registers'] = self._get_otp_registers()

        # TPM data (if available)
        features['tpm_data'] = self._get_tpm_data()

        # Storage information
        features['storage_info'] = self._get_storage_info()

        # System UUID
        features['system_uuid'] = self._get_system_uuid()

        return features

    def _get_cpu_serial(self) -> Dict[str, Any]:
        """Get CPU serial number"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        serial = line.split(':')[1].strip()
                        return {
                            'present': True,
                            'value': serial,
                            'confidence': 1.0
                        }
        except Exception:
            pass

        return {
            'present': False,
            'value': None,
            'confidence': 0.0
        }

    def _get_hardware_rng_sample(self) -> Dict[str, Any]:
        """Get sample from hardware RNG"""
        try:
            with open('/dev/hwrng', 'rb') as rng:
                sample = rng.read(16).hex()
                return {
                    'present': True,
                    'value': sample,
                    'confidence': 0.9
                }
        except Exception:
            pass

        return {
            'present': False,
            'value': None,
            'confidence': 0.0
        }

    def _get_videocore_info(self) -> Dict[str, Any]:
        """Get VideoCore GPU information"""
        try:
            # Get GPU memory
            result = subprocess.run(['vcgencmd', 'get_mem', 'gpu'],
                                  capture_output=True, text=True, timeout=2)
            gpu_mem = "unknown"
            if result.returncode == 0 and 'gpu=' in result.stdout:
                gpu_mem = result.stdout.strip()

            # Get temperature (as additional entropy)
            temp_result = subprocess.run(['vcgencmd', 'measure_temp'],
                                       capture_output=True, text=True, timeout=2)
            temp = "unknown"
            if temp_result.returncode == 0 and 'temp=' in temp_result.stdout:
                temp = temp_result.stdout.strip()

            value = f"{gpu_mem}|{temp}"
            return {
                'present': True,
                'value': value,
                'confidence': 0.95
            }
        except Exception:
            pass

        return {
            'present': False,
            'value': None,
            'confidence': 0.0
        }

    def _get_mac_addresses(self) -> Dict[str, Any]:
        """Get network interface MAC addresses"""
        try:
            result = subprocess.run(['cat', '/sys/class/net/*/address'],
                                  capture_output=True, text=True, timeout=2)

            if result.returncode == 0:
                macs = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                # Sort for consistency
                macs.sort()
                value = "|".join(macs)
                return {
                    'present': True,
                    'value': value,
                    'confidence': 0.8
                }
        except Exception:
            pass

        return {
            'present': False,
            'value': None,
            'confidence': 0.0
        }

    def _get_otp_registers(self) -> Dict[str, Any]:
        """Get OTP register values"""
        try:
            result = subprocess.run(['vcgencmd', 'otp_dump'],
                                  capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and result.stdout.strip():
                # Extract key registers (17, 28, 29 are commonly unique)
                lines = result.stdout.strip().split('\n')
                otp_values = {}

                for line in lines:
                    if ':' in line:
                        reg, value = line.split(':', 1)
                        try:
                            reg_num = int(reg.strip(), 16)
                            val = int(value.strip(), 16)
                            otp_values[reg_num] = val
                        except:
                            continue

                # Use specific registers for fingerprinting
                key_regs = [17, 28, 29]  # Model/revision, customer OTP, etc.
                values = []
                for reg in key_regs:
                    if reg in otp_values:
                        values.append(f"{reg}:{otp_values[reg]}")

                if values:
                    return {
                        'present': True,
                        'value': "|".join(values),
                        'confidence': 0.9
                    }
        except Exception:
            pass

        return {
            'present': False,
            'value': None,
            'confidence': 0.0
        }

    def _get_tpm_data(self) -> Dict[str, Any]:
        """Get TPM data (if available)"""
        # Placeholder for TPM integration
        # This would read TPM PCRs, EK certificate, etc.
        try:
            # Check if TPM tools are available
            result = subprocess.run(['tpm2_pcrread'],
                                  capture_output=True, timeout=2)

            if result.returncode == 0:
                # Extract PCR 0 (BIOS measurements)
                pcr_data = "tpm_available"
                return {
                    'present': True,
                    'value': pcr_data,
                    'confidence': 0.95
                }
        except Exception:
            pass

        return {
            'present': False,
            'value': None,
            'confidence': 0.0
        }

    def _get_storage_info(self) -> Dict[str, Any]:
        """Get storage device information"""
        try:
            # Get disk serial numbers
            result = subprocess.run(['lsblk', '-o', 'NAME,SERIAL', '-n'],
                                  capture_output=True, text=True, timeout=2)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                serials = []

                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] != '':
                        serials.append(parts[1])

                if serials:
                    serials.sort()  # Consistent ordering
                    return {
                        'present': True,
                        'value': "|".join(serials),
                        'confidence': 0.85
                    }
        except Exception:
            pass

        return {
            'present': False,
            'value': None,
            'confidence': 0.0
        }

    def _get_system_uuid(self) -> Dict[str, Any]:
        """Get system UUID"""
        try:
            # Try DMI UUID first
            with open('/sys/devices/virtual/dmi/id/product_uuid', 'r') as f:
                uuid = f.read().strip()
                return {
                    'present': True,
                    'value': uuid,
                    'confidence': 0.9
                }
        except Exception:
            pass

        try:
            # Fallback to machine-id
            with open('/etc/machine-id', 'r') as f:
                machine_id = f.read().strip()
                return {
                    'present': True,
                    'value': machine_id,
                    'confidence': 0.7
                }
        except Exception:
            pass

        return {
            'present': False,
            'value': None,
            'confidence': 0.0
        }

    def _save_fingerprint_cache(self, fingerprint: str, data: Dict[str, Any]):
        """Save fingerprint data to cache file"""
        try:
            cache_data = {
                'fingerprint': fingerprint,
                'generated_at': time.time(),
                'components': data,
                'version': '1.0'
            }

            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            print(f"Failed to save fingerprint cache: {e}")

    def load_fingerprint_cache(self) -> Optional[str]:
        """Load cached fingerprint"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)

                # Validate cache structure
                if 'fingerprint' in cache_data and 'generated_at' in cache_data:
                    # Check if cache is recent (within 24 hours)
                    if time.time() - cache_data['generated_at'] < 24 * 60 * 60:
                        self._cached_fingerprint = cache_data['fingerprint']
                        self._fingerprint_data = cache_data.get('components', {})
                        return self._cached_fingerprint

        except Exception as e:
            print(f"Failed to load fingerprint cache: {e}")

        return None

    def get_fingerprint_info(self) -> Dict[str, Any]:
        """Get detailed fingerprint information"""
        fingerprint = self.generate_fingerprint()

        # Calculate confidence score
        total_weight = 0
        weighted_score = 0

        for component_name, component_data in self._fingerprint_data.items():
            config = self.fingerprint_components.get(component_name, {})
            weight = config.get('weight', 0)
            confidence = component_data.get('confidence', 0)

            total_weight += weight
            weighted_score += weight * confidence

        overall_confidence = weighted_score / total_weight if total_weight > 0 else 0

        return {
            'fingerprint': fingerprint,
            'confidence_score': overall_confidence,
            'components': self._fingerprint_data,
            'generated_at': time.time(),
            'cache_file': str(self.cache_file)
        }

    def verify_fingerprint_integrity(self, expected_fingerprint: str) -> Dict[str, Any]:
        """
        Verify that current hardware matches expected fingerprint

        Args:
            expected_fingerprint: Previously generated fingerprint

        Returns:
            Verification result
        """
        current_fingerprint = self.generate_fingerprint(force_refresh=True)

        if current_fingerprint == expected_fingerprint:
            return {
                'verified': True,
                'current_fingerprint': current_fingerprint,
                'expected_fingerprint': expected_fingerprint,
                'match': True
            }
        else:
            # Detailed mismatch analysis
            return {
                'verified': False,
                'current_fingerprint': current_fingerprint,
                'expected_fingerprint': expected_fingerprint,
                'match': False,
                'analysis': self._analyze_fingerprint_changes(expected_fingerprint)
            }

    def _analyze_fingerprint_changes(self, expected_fingerprint: str) -> Dict[str, Any]:
        """Analyze what changed in the fingerprint"""
        # This would compare component by component to identify changes
        # For now, return basic analysis
        return {
            'possible_causes': [
                'Hardware component replaced',
                'System update changed hardware enumeration',
                'Virtual machine migration',
                'TPM/secure element changes'
            ],
            'recommendations': [
                'Verify physical hardware integrity',
                'Check for unauthorized system modifications',
                'Regenerate device certificates if compromised'
            ]
        }

    def export_fingerprint(self, export_path: str) -> bool:
        """Export fingerprint data for backup/sharing"""
        try:
            info = self.get_fingerprint_info()

            with open(export_path, 'w') as f:
                json.dump(info, f, indent=2)

            return True
        except Exception:
            return False

    def import_fingerprint(self, import_path: str) -> bool:
        """Import fingerprint data (for verification purposes)"""
        try:
            with open(import_path, 'r') as f:
                imported_data = json.load(f)

            # Validate structure
            if 'fingerprint' in imported_data and 'components' in imported_data:
                # Store for comparison
                self._imported_fingerprint = imported_data
                return True

        except Exception:
            pass

        return False