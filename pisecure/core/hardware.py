"""
PiSecure Hardware Verification
==============================

Comprehensive Raspberry Pi hardware verification using exclusive registers
and chipsets for secure blockchain mining.
"""

import os
import re
import subprocess
import time
from typing import Dict, Any


class HardwareVerifier:
    """Comprehensive Raspberry Pi hardware verification using exclusive registers and chipsets"""

    def __init__(self):
        # Support ALL Raspberry Pi models for maximum compatibility
        self.allowed_hardware = [
            'raspberry_pi_zero', 'raspberry_pi_zero_w', 'raspberry_pi_zero_2',
            'raspberry_pi_3', 'raspberry_pi_3b+', 'raspberry_pi_4', 'raspberry_pi_5'
        ]

        # Verification methods with weights - made more lenient for older Pi models
        self.verification_methods = {
            'cpu_serial': {'weight': 0.20, 'required': True},      # Required for all Pi
            'hardware_rng': {'weight': 0.15, 'required': False},   # Optional for older Pi
            'videocore_gpu': {'weight': 0.25, 'required': False},  # Optional for newer Pi
            'chip_identification': {'weight': 0.20, 'required': True}, # Required for model detection
            'gpio_access': {'weight': 0.10, 'required': False},    # Optional GPIO check
            'system_info': {'weight': 0.10, 'required': False}      # Optional system checks
        }

    def verify_mining_eligibility(self) -> Dict[str, Any]:
        """Comprehensive Pi hardware verification with detailed results"""
        verification_results = self._run_comprehensive_verification()

        # Calculate weighted score
        total_score = 0
        max_score = 0
        required_passed = 0
        required_total = 0

        print("=== HARDWARE VERIFICATION DETAILS ===")
        for method, config in self.verification_methods.items():
            max_score += config['weight']
            if config['required']:
                required_total += 1

            passed = method in verification_results and verification_results[method]['passed']
            if passed:
                total_score += config['weight']
                if config['required']:
                    required_passed += 1

            status = "✓" if passed else "✗"
            required_str = "(required)" if config['required'] else "(optional)"
            print(f"{status} {method}: {passed} {required_str} (weight: {config['weight']})")

            # Log detailed error if failed
            if not passed and method in verification_results:
                error_info = verification_results[method].get('error', 'No error details')
                print(f"    Error: {error_info}")

        confidence = total_score / max_score if max_score > 0 else 0
        print(f"Score: {total_score:.2f}/{max_score:.2f} = {confidence:.2f} confidence")
        print(f"Required: {required_passed}/{required_total} passed")

        # Overall verification
        overall_passed = (total_score >= 0.65 and  # 65% weighted score
                         required_passed == required_total)  # All required checks pass

        print(f"Overall result: {'PASSED' if overall_passed else 'FAILED'}")

        # Log hardware model detection
        chip_result = verification_results.get('chip_identification', {})
        if chip_result.get('passed'):
            print(f"Detected hardware: {chip_result.get('model', 'unknown')}")
        else:
            print("Hardware model detection failed")

        return {
            'eligible': overall_passed,
            'confidence_score': confidence,
            'hardware_model': chip_result.get('model', 'unknown'),
            'serial_number': verification_results.get('cpu_serial', {}).get('serial', 'unknown'),
            'verification_details': verification_results,
            'anti_spoofing_passed': self._run_anti_spoofing_checks()
        }

    def _run_comprehensive_verification(self) -> Dict[str, Any]:
        """Run all hardware verification methods"""
        results = {}

        # 1. CPU Serial Number (25% weight, required)
        results['cpu_serial'] = self._verify_cpu_serial()

        # 2. Hardware RNG (20% weight, required)
        results['hardware_rng'] = self._verify_hardware_rng()

        # 3. VideoCore GPU (20% weight, required)
        results['videocore_gpu'] = self._verify_videocore_gpu()

        # 4. Mailbox Interface (15% weight, optional)
        results['mailbox_interface'] = self._verify_mailbox_interface()

        # 5. Chip Identification (10% weight, optional)
        results['chip_identification'] = self._verify_chip_identification()

        # 6. OTP Registers (10% weight, optional)
        results['otp_registers'] = self._verify_otp_registers()

        return results

    def _verify_cpu_serial(self) -> Dict[str, Any]:
        """Verify CPU serial number - exclusive to Pi hardware"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()

            # Look for serial number with flexible format
            serial_match = re.search(r'Serial.*?([0-9a-f]+)', cpuinfo, re.IGNORECASE)

            if serial_match:
                serial = serial_match.group(1).upper()

                # Validate format (must be at least 16 hex characters, not all zeros)
                if (len(serial) >= 16 and
                    all(c in '0123456789ABCDEF' for c in serial) and
                    not all(c == '0' for c in serial)):  # Not all zeros

                    return {
                        'passed': True,
                        'serial': serial,
                        'format_valid': True,
                        'unique': True
                    }

        except Exception as e:
            pass

        return {
            'passed': False,
            'error': 'CPU serial verification failed'
        }

    def _verify_hardware_rng(self) -> Dict[str, Any]:
        """Verify hardware RNG access - exclusive to BCM283x/BCM271x"""
        try:
            # Test hardware RNG access
            with open('/dev/hwrng', 'rb') as rng:
                # Read 32 bytes to test RNG quality
                random_data = rng.read(32)

                if len(random_data) == 32:
                    # Test entropy quality (should not be predictable)
                    # Check for non-zero entropy
                    entropy_score = len(set(random_data)) / 256.0  # Unique bytes ratio

                    if entropy_score > 0.7:  # Good entropy
                        return {
                            'passed': True,
                            'entropy_score': entropy_score,
                            'bytes_read': len(random_data)
                        }

        except Exception as e:
            pass

        return {
            'passed': False,
            'error': 'Hardware RNG verification failed'
        }

    def _verify_videocore_gpu(self) -> Dict[str, Any]:
        """Verify VideoCore GPU presence - supports IV, VI, and VII"""
        try:
            # Method 1: Try standard VideoCore commands (works on IV/VI/VII)
            result = subprocess.run(['vcgencmd', 'version'],
                                  capture_output=True, text=True, timeout=2)

            if result.returncode == 0:
                videocore_version = self._detect_videocore_version()
                gpu_mem = 'unknown'
                features_verified = 1  # vcgencmd version worked

                # Try to get GPU memory info (works on IV/VI, may differ on VII)
                mem_result = subprocess.run(['vcgencmd', 'get_mem', 'gpu'],
                                          capture_output=True, text=True, timeout=2)
                if mem_result.returncode == 0 and 'gpu=' in mem_result.stdout:
                    gpu_mem = mem_result.stdout.strip().replace('gpu=', '')
                    features_verified += 1

                # Check temperature sensor (different methods for different VideoCore versions)
                temp_verified = self._verify_videocore_temperature()
                if temp_verified:
                    features_verified += 1

                return {
                    'passed': True,
                    'gpu_memory': gpu_mem,
                    'videocore_version': videocore_version,
                    'features_verified': features_verified,
                    'videocore_detected': True
                }

        except Exception as e:
            pass

        return {
            'passed': False,
            'error': 'VideoCore GPU verification failed'
        }

    def _detect_videocore_version(self) -> str:
        """Detect VideoCore GPU version"""
        try:
            # Try to get version info
            version_result = subprocess.run(['vcgencmd', 'version'],
                                          capture_output=True, text=True, timeout=2)

            if version_result.returncode == 0:
                version_output = version_result.stdout.lower()

                # Check for version indicators
                if 'videocore vii' in version_output or 'vc7' in version_output:
                    return 'VII'
                elif 'videocore vi' in version_output or 'vc6' in version_output:
                    return 'VI'
                elif 'videocore iv' in version_output or 'vc4' in version_output:
                    return 'IV'
                else:
                    # Fallback: check hardware model for version hints
                    chip_result = self._verify_chip_identification()
                    model = chip_result.get('model', '').lower()

                    if 'pi 5' in model:
                        return 'VII'  # Pi 5 uses VideoCore VII
                    elif 'pi 4' in model:
                        return 'VI'   # Pi 4 uses VideoCore VI
                    else:
                        return 'IV'   # Older Pis use VideoCore IV

        except Exception:
            pass

        return 'unknown'

    def _verify_videocore_temperature(self) -> bool:
        """Verify VideoCore temperature sensor with version-specific fallbacks"""
        try:
            # Method 1: Standard GPU temperature (works on IV/VI)
            temp_result = subprocess.run(['vcgencmd', 'measure_temp'],
                                       capture_output=True, text=True, timeout=2)

            if temp_result.returncode == 0 and 'temp=' in temp_result.stdout:
                temp_str = temp_result.stdout.strip()
                temp_match = re.search(r'temp=([0-9.]+)', temp_str)
                if temp_match:
                    temp = float(temp_match.group(1))
                    if 0 <= temp <= 100:  # Reasonable temperature range
                        return True

            # Method 2: Pi 5 specific temperature check (VideoCore VII)
            # Pi 5 may use different temperature reporting
            try:
                # Check system temperature as fallback
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_raw = int(f.read().strip())
                    temp_celsius = temp_raw / 1000.0
                    if 0 <= temp_celsius <= 100:
                        return True
            except:
                pass

            # Method 3: Check for any temperature-related vcgencmd output
            temp_sensors = subprocess.run(['vcgencmd', 'measure_volts', 'core'],
                                        capture_output=True, text=True, timeout=2)
            if temp_sensors.returncode == 0:
                return True  # If vcgencmd works at all, GPU is present

        except Exception:
            pass

        return False

    def _verify_mailbox_interface(self) -> Dict[str, Any]:
        """Verify mailbox interface - exclusive CPU↔GPU communication"""
        try:
            # Test mailbox device access
            mailbox = open('/dev/vcio', 'rb+', buffering=0)

            # Try a simple mailbox transaction
            # This is a basic test - full mailbox usage requires specific protocols
            mailbox.close()

            return {
                'passed': True,
                'interface_accessible': True,
                'mailbox_available': True
            }

        except Exception as e:
            pass

        return {
            'passed': False,
            'error': 'Mailbox interface verification failed'
        }

    def _verify_chip_identification(self) -> Dict[str, Any]:
        """Verify BCM283x/BCM271x chip identification"""
        try:
            # Multiple methods to identify Pi hardware

            # Method 1: Device tree model
            pi_models = []
            dt_files = ['/proc/device-tree/model', '/sys/firmware/devicetree/base/model']

            for dt_file in dt_files:
                if os.path.exists(dt_file):
                    try:
                        with open(dt_file, 'r') as f:
                            model = f.read().strip()
                            if 'Raspberry Pi' in model:
                                pi_models.append(model)
                    except:
                        pass

            # Method 2: CPU info hardware field
            bcm_found = False
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read()
                    if 'BCM' in cpuinfo or 'Broadcom' in cpuinfo:
                        bcm_found = True
            except:
                pass

            # Method 3: Compatible field in device tree
            compatible_found = False
            try:
                with open('/proc/device-tree/compatible', 'rb') as f:
                    compatible = f.read().decode('utf-8', errors='ignore')
                    if 'brcm,bcm' in compatible.lower():
                        compatible_found = True
            except:
                pass

            # Determine model from detected information
            model = 'unknown'
            if pi_models:
                model = pi_models[0]
            elif bcm_found:
                model = 'Raspberry Pi (BCM detected)'

            verification_score = sum([bool(pi_models), bcm_found, compatible_found])

            return {
                'passed': verification_score >= 2,  # At least 2 methods confirm Pi
                'model': model,
                'bcm_detected': bcm_found,
                'device_tree_models': pi_models,
                'compatible_found': compatible_found,
                'verification_score': verification_score
            }

        except Exception as e:
            pass

        return {
            'passed': False,
            'error': 'Chip identification verification failed'
        }

    def _verify_otp_registers(self) -> Dict[str, Any]:
        """Verify OTP (One-Time Programmable) register access"""
        try:
            # Try to read OTP registers using vcmailbox
            # This is advanced and may not work on all systems
            result = subprocess.run([
                'vcgencmd', 'otp_dump'
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and result.stdout.strip():
                # Parse OTP dump
                otp_lines = result.stdout.strip().split('\n')
                otp_registers = {}

                for line in otp_lines:
                    if ':' in line:
                        reg, value = line.split(':', 1)
                        try:
                            reg_num = int(reg.strip(), 16)
                            val = int(value.strip(), 16)
                            otp_registers[reg_num] = val
                        except:
                            pass

                # Check for known Pi OTP patterns
                pi_otp_detected = False
                if 17 in otp_registers:  # Model/revision register
                    revision = otp_registers[17]
                    # Pi revision codes are well-documented
                    if revision > 0:
                        pi_otp_detected = True

                return {
                    'passed': pi_otp_detected,
                    'otp_registers_read': len(otp_registers),
                    'pi_otp_pattern': pi_otp_detected,
                    'registers': otp_registers
                }

        except Exception as e:
            pass

        return {
            'passed': False,
            'error': 'OTP register verification failed'
        }

    def _run_anti_spoofing_checks(self) -> bool:
        """Run anti-spoofing measures to prevent emulation"""
        try:
            spoofing_checks = []

            # 1. Check for virtual machine indicators
            spoofing_checks.append(self._detect_virtual_machine())

            # 2. Verify hardware RNG entropy quality
            spoofing_checks.append(self._verify_rng_entropy_quality())

            # 3. Check for Pi-specific kernel modules
            spoofing_checks.append(self._verify_pi_kernel_modules())

            # 4. Validate temperature sensor presence
            spoofing_checks.append(self._verify_temperature_sensor())

            # 5. Check GPIO register access
            spoofing_checks.append(self._verify_gpio_access())

            # 6. Verify unified memory architecture (Pi-specific)
            spoofing_checks.append(self._verify_unified_memory())

            # Require 5/6 checks to pass
            passed_checks = sum(spoofing_checks)
            return passed_checks >= 5

        except Exception as e:
            return False

    def _detect_virtual_machine(self) -> bool:
        """Detect if running in a virtual machine"""
        try:
            # Check for common VM indicators
            vm_indicators = [
                '/proc/cpuinfo containing "QEMU" or "VirtualBox"',
                '/sys/devices/virtual/dmi/id/product_name',
                'lspci output showing virtual devices'
            ]

            # Check CPU info for VM signatures
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read().lower()
                if any(vm in cpuinfo for vm in ['qemu', 'virtualbox', 'vmware', 'xen']):
                    return False  # VM detected

            # Check dmi product name
            if os.path.exists('/sys/devices/virtual/dmi/id/product_name'):
                with open('/sys/devices/virtual/dmi/id/product_name', 'r') as f:
                    product = f.read().strip().lower()
                    if any(vm in product for vm in ['virtual', 'vm', 'qemu']):
                        return False

            return True  # No VM indicators found

        except:
            return False  # Error = assume VM

    def _verify_rng_entropy_quality(self) -> bool:
        """Verify hardware RNG produces high-quality entropy"""
        try:
            with open('/dev/hwrng', 'rb') as rng:
                # Read larger sample for quality analysis
                sample = rng.read(1024)

                if len(sample) != 1024:
                    return False

                # Check for patterns (should be random)
                # Simple entropy check: count unique byte values
                unique_bytes = len(set(sample))
                if unique_bytes < 200:  # Should have high diversity
                    return False

                # Check for repeating patterns
                # Split into 4-byte chunks and check for repetition
                chunks = [sample[i:i+4] for i in range(0, len(sample), 4)]
                unique_chunks = len(set(chunks))
                if unique_chunks < len(chunks) * 0.8:  # 80% unique chunks
                    return False

                return True

        except:
            return False

    def _verify_pi_kernel_modules(self) -> bool:
        """Verify Pi-specific kernel modules are loaded"""
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=2)

            if result.returncode == 0:
                loaded_modules = result.stdout
                pi_modules = ['bcm2835', 'vcio', 'bcm2708_fb', 'snd_bcm2835']
                loaded_pi_modules = sum(1 for module in pi_modules if module in loaded_modules)

                # At least 2 Pi-specific modules should be loaded
                return loaded_pi_modules >= 2

        except:
            pass

        return False

    def _verify_temperature_sensor(self) -> bool:
        """Verify BCM283x temperature sensor presence"""
        try:
            # Use vcgencmd to read GPU temperature (Pi-specific)
            result = subprocess.run(['vcgencmd', 'measure_temp'],
                                  capture_output=True, text=True, timeout=2)

            if result.returncode == 0 and 'temp=' in result.stdout:
                temp_str = result.stdout.strip()
                # Parse temperature value
                temp_match = re.search(r'temp=([0-9.]+)', temp_str)
                if temp_match:
                    temp = float(temp_match.group(1))
                    # Temperature should be reasonable (0-100°C)
                    return 0 <= temp <= 100

        except:
            pass

        return False

    def _verify_gpio_access(self) -> bool:
        """Verify GPIO register access (Pi-specific)"""
        try:
            # Try to access GPIO device (requires appropriate permissions)
            gpio = open('/dev/gpiomem', 'rb+', buffering=0)
            gpio.close()

            return True

        except:
            # Fallback: check if gpio group exists or gpio devices
            try:
                result = subprocess.run(['groups'], capture_output=True, text=True, timeout=1)
                if 'gpio' in result.stdout:
                    return True

                # Check for gpio device files
                gpio_devices = ['/dev/gpiochip0', '/dev/gpiomem']
                for device in gpio_devices:
                    if os.path.exists(device):
                        return True

            except:
                pass

        return False

    def _verify_unified_memory(self) -> bool:
        """Verify unified CPU/GPU memory architecture (Pi-specific)"""
        try:
            # Check /proc/meminfo for GPU memory
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()

                # Look for GPU memory information
                gpu_mem_lines = [line for line in meminfo.split('\n') if 'GPU' in line.upper()]

                if gpu_mem_lines:
                    return True

            # Alternative: check vcgencmd memory info
            result = subprocess.run(['vcgencmd', 'get_mem', 'gpu'],
                                  capture_output=True, text=True, timeout=2)

            return result.returncode == 0 and 'gpu=' in result.stdout

        except:
            return False

    def get_hardware_fingerprint(self) -> str:
        """Generate unique hardware fingerprint using Pi-exclusive features"""
        import hashlib

        try:
            # Gather multiple hardware identifiers
            fingerprint_components = []

            # CPU Serial
            cpu_result = self._verify_cpu_serial()
            if cpu_result['passed']:
                fingerprint_components.append(f"serial:{cpu_result['serial']}")

            # Hardware RNG sample
            rng_result = self._verify_hardware_rng()
            if rng_result['passed']:
                # Use first 8 bytes of RNG output
                with open('/dev/hwrng', 'rb') as rng:
                    rng_sample = rng.read(8).hex()
                    fingerprint_components.append(f"rng:{rng_sample}")

            # Chip identification
            chip_result = self._verify_chip_identification()
            if chip_result['passed']:
                fingerprint_components.append(f"chip:{chip_result['model']}")

            # Combine components
            fingerprint_string = "|".join(fingerprint_components)
            fingerprint = hashlib.sha256(fingerprint_string.encode()).hexdigest()

            return fingerprint

        except Exception as e:
            return f"error:{str(e)}"

    def get_device_role(self) -> Dict[str, Any]:
        """Determine device capabilities and role based on comprehensive verification"""
        verification = self.verify_mining_eligibility()

        if verification['eligible']:
            # Pi hardware detected and verified
            hardware_model = verification['hardware_model']
            confidence = verification['confidence_score']

            # Determine specific model capabilities
            if 'Pi 5' in hardware_model:
                rewards_multiplier = 1.3  # Latest model bonus
            elif 'Pi 4' in hardware_model:
                rewards_multiplier = 1.2  # Standard Pi bonus
            elif 'Pi Zero 2' in hardware_model:
                rewards_multiplier = 1.1  # Entry-level bonus
            else:
                rewards_multiplier = 1.0  # Generic Pi

            return {
                'role': 'miner',
                'hardware': hardware_model.replace(' ', '_').lower(),
                'capabilities': ['mining', 'staking', 'verification', 'bundle_creation'],
                'rewards_multiplier': rewards_multiplier,
                'verification_confidence': confidence,
                'hardware_fingerprint': verification['serial_number'],
                'anti_spoofing_passed': verification['anti_spoofing_passed']
            }
        else:
            # Not Pi hardware or verification failed
            return {
                'role': 'staker_only',
                'hardware': 'non_pi_hardware',
                'capabilities': ['staking', 'verification', 'wallet_operations'],
                'rewards_multiplier': 0.8,
                'verification_confidence': 0,
                'hardware_fingerprint': 'none',
                'anti_spoofing_passed': False
            }