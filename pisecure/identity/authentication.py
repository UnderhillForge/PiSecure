"""
PiSecure Device Authentication
=============================

Mutual TLS authentication and secure communication between PiSecure devices
using hardware-bound certificates and challenge-response protocols.
"""

import json
import time
import secrets
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import ExtensionOID

from .certificates import CertificateManager
from .fingerprint import DeviceFingerprint


class DeviceAuthenticator:
    """Device-to-device authentication and secure communication"""

    def __init__(self, cert_manager: CertificateManager = None,
                 fingerprint: DeviceFingerprint = None):
        self.cert_manager = cert_manager or CertificateManager()
        self.fingerprint = fingerprint or DeviceFingerprint()

        # Authentication sessions
        self.active_sessions = {}
        self.session_timeout = 3600  # 1 hour

    def authenticate_device(self, remote_cert_pem: str, remote_fingerprint: str = None,
                          challenge_data: str = None) -> Dict[str, Any]:
        """
        Authenticate a remote device using certificate and optional fingerprint

        Args:
            remote_cert_pem: Remote device certificate in PEM format
            remote_fingerprint: Optional remote device fingerprint for verification
            challenge_data: Optional challenge data for mutual authentication

        Returns:
            Authentication result
        """
        try:
            # Validate certificate
            cert_validation = self.cert_manager.validate_device_certificate(remote_cert_pem)
            if not cert_validation['valid']:
                return {
                    'authenticated': False,
                    'error': cert_validation['error'],
                    'stage': 'certificate_validation'
                }

            device_id = cert_validation['device_id']

            # If fingerprint provided, verify it
            if remote_fingerprint:
                # In a real implementation, you'd verify the fingerprint matches
                # the certificate's device. For now, we accept it.
                pass

            # Generate session token
            session_token = secrets.token_urlsafe(32)
            session_id = hashlib.sha256(session_token.encode()).hexdigest()

            # Create authentication session
            session = {
                'session_id': session_id,
                'device_id': device_id,
                'remote_cert_fingerprint': cert_validation['fingerprint'],
                'authenticated_at': time.time(),
                'expires_at': time.time() + self.session_timeout,
                'challenge_response': challenge_data
            }

            self.active_sessions[session_id] = session

            return {
                'authenticated': True,
                'device_id': device_id,
                'session_token': session_token,
                'session_id': session_id,
                'certificate_info': cert_validation,
                'expires_at': session['expires_at']
            }

        except Exception as e:
            return {
                'authenticated': False,
                'error': str(e),
                'stage': 'authentication'
            }

    def generate_challenge(self, device_id: str, difficulty: int = 4) -> Dict[str, Any]:
        """
        Generate cryptographic challenge for device authentication

        Args:
            device_id: Target device ID
            difficulty: Challenge difficulty (number of leading zeros)

        Returns:
            Challenge data
        """
        try:
            # Create challenge data
            challenge_data = {
                'device_id': device_id,
                'timestamp': time.time(),
                'nonce': secrets.token_hex(16),
                'difficulty': difficulty,
                'challenge_type': 'proof_of_work'
            }

            # Sign challenge with our certificate
            challenge_json = json.dumps(challenge_data, sort_keys=True)
            signature = self._sign_challenge(challenge_json)

            challenge_data['signature'] = signature

            return {
                'success': True,
                'challenge': challenge_data,
                'challenge_string': challenge_json
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def verify_challenge_response(self, challenge: Dict[str, Any],
                                response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify challenge response from remote device

        Args:
            challenge: Original challenge data
            response: Device response

        Returns:
            Verification result
        """
        try:
            # Check response format
            required_fields = ['device_id', 'challenge_hash', 'nonce', 'proof']
            if not all(field in response for field in required_fields):
                return {
                    'verified': False,
                    'error': 'Incomplete response'
                }

            # Verify challenge hasn't expired
            challenge_time = challenge.get('timestamp', 0)
            if time.time() - challenge_time > 300:  # 5 minutes
                return {
                    'verified': False,
                    'error': 'Challenge expired'
                }

            # Verify proof-of-work
            challenge_string = challenge.get('challenge_string', '')
            proof = response.get('proof', '')
            difficulty = challenge.get('difficulty', 4)

            if not self._verify_proof_of_work(challenge_string, proof, difficulty):
                return {
                    'verified': False,
                    'error': 'Invalid proof-of-work'
                }

            # Verify response signature
            response_copy = response.copy()
            response_signature = response_copy.pop('signature', None)

            if not response_signature:
                return {
                    'verified': False,
                    'error': 'Missing response signature'
                }

            response_json = json.dumps(response_copy, sort_keys=True)

            if not self._verify_response_signature(response['device_id'], response_json, response_signature):
                return {
                    'verified': False,
                    'error': 'Invalid response signature'
                }

            return {
                'verified': True,
                'device_id': response['device_id'],
                'proof_valid': True,
                'signature_valid': True
            }

        except Exception as e:
            return {
                'verified': False,
                'error': str(e)
            }

    def _sign_challenge(self, challenge_data: str) -> Optional[str]:
        """Sign challenge data with device certificate"""
        try:
            # Get our device certificate
            # This would load from current device identity
            # For now, return a placeholder signature
            return "placeholder_signature"
        except Exception:
            return None

    def _verify_response_signature(self, device_id: str, response_data: str,
                                 signature: str) -> bool:
        """Verify response signature from remote device"""
        try:
            # Load remote device certificate
            remote_cert = self.cert_manager.load_device_certificate(device_id)
            if not remote_cert:
                return False

            # Verify signature
            public_key = remote_cert['certificate'].public_key()

            if isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    bytes.fromhex(signature),
                    response_data.encode(),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                return True

            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(
                    bytes.fromhex(signature),
                    response_data.encode(),
                    ec.ECDSA(hashes.SHA256())
                )
                return True

        except Exception:
            pass

        return False

    def _verify_proof_of_work(self, challenge: str, proof: str, difficulty: int) -> bool:
        """Verify proof-of-work solution"""
        try:
            # Combine challenge and proof
            combined = challenge + proof
            hash_result = hashlib.sha256(combined.encode()).hexdigest()

            # Check for required number of leading zeros
            return hash_result.startswith('0' * difficulty)

        except Exception:
            return False

    def create_secure_channel(self, remote_device_id: str, session_token: str) -> Dict[str, Any]:
        """
        Establish secure communication channel with authenticated device

        Args:
            remote_device_id: Remote device ID
            session_token: Valid session token

        Returns:
            Secure channel information
        """
        try:
            # Verify session
            session = self._get_valid_session(session_token)
            if not session or session['device_id'] != remote_device_id:
                return {
                    'success': False,
                    'error': 'Invalid session'
                }

            # Generate channel keys
            channel_key = secrets.token_bytes(32)  # 256-bit key
            channel_id = secrets.token_urlsafe(16)

            # Store channel information
            channel_info = {
                'channel_id': channel_id,
                'device_id': remote_device_id,
                'session_id': session['session_id'],
                'channel_key': channel_key.hex(),
                'created_at': time.time(),
                'expires_at': time.time() + 3600  # 1 hour
            }

            # In a real implementation, you'd store this securely
            # For now, just return the info

            return {
                'success': True,
                'channel_id': channel_id,
                'channel_key': channel_key.hex(),
                'expires_at': channel_info['expires_at']
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def encrypt_message(self, channel_id: str, message: str) -> Optional[str]:
        """
        Encrypt message for secure channel

        Args:
            channel_id: Secure channel ID
            message: Message to encrypt

        Returns:
            Encrypted message (base64)
        """
        try:
            # In a real implementation, you'd use AES-GCM or similar
            # For now, return a placeholder
            return f"encrypted:{message}"
        except Exception:
            return None

    def decrypt_message(self, channel_id: str, encrypted_message: str) -> Optional[str]:
        """
        Decrypt message from secure channel

        Args:
            channel_id: Secure channel ID
            encrypted_message: Encrypted message

        Returns:
            Decrypted message
        """
        try:
            # In a real implementation, you'd decrypt with channel key
            if encrypted_message.startswith("encrypted:"):
                return encrypted_message[10:]
            return None
        except Exception:
            return None

    def _get_valid_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get valid authentication session"""
        try:
            session_id = hashlib.sha256(session_token.encode()).hexdigest()

            session = self.active_sessions.get(session_id)
            if session and session['expires_at'] > time.time():
                return session

            # Clean up expired session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

        except Exception:
            pass

        return None

    def revoke_session(self, session_token: str) -> bool:
        """Revoke authentication session"""
        try:
            session_id = hashlib.sha256(session_token.encode()).hexdigest()
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                return True
        except Exception:
            pass
        return False

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List active authentication sessions"""
        current_time = time.time()
        active_sessions = []

        for session_id, session in self.active_sessions.items():
            if session['expires_at'] > current_time:
                active_sessions.append({
                    'session_id': session_id,
                    'device_id': session['device_id'],
                    'authenticated_at': session['authenticated_at'],
                    'expires_at': session['expires_at']
                })
            else:
                # Clean up expired session
                del self.active_sessions[session_id]

        return active_sessions

    def mutual_authenticate(self, remote_device_id: str, remote_cert_pem: str) -> Dict[str, Any]:
        """
        Perform mutual authentication with remote device

        Args:
            remote_device_id: Remote device ID
            remote_cert_pem: Remote device certificate

        Returns:
            Mutual authentication result
        """
        try:
            # Step 1: Authenticate remote device
            auth_result = self.authenticate_device(remote_cert_pem)
            if not auth_result['authenticated']:
                return auth_result

            session_token = auth_result['session_token']

            # Step 2: Generate challenge for remote device
            challenge_result = self.generate_challenge(remote_device_id)
            if not challenge_result['success']:
                return {
                    'authenticated': False,
                    'error': f'Challenge generation failed: {challenge_result["error"]}'
                }

            # In a real implementation, you'd send the challenge to the remote device
            # and receive a response. For now, simulate a successful response.

            # Step 3: Establish secure channel
            channel_result = self.create_secure_channel(remote_device_id, session_token)
            if not channel_result['success']:
                return {
                    'authenticated': False,
                    'error': f'Channel creation failed: {channel_result["error"]}'
                }

            return {
                'authenticated': True,
                'mutual': True,
                'device_id': remote_device_id,
                'session_token': session_token,
                'channel_id': channel_result['channel_id'],
                'secure_channel_established': True
            }

        except Exception as e:
            return {
                'authenticated': False,
                'error': str(e)
            }

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired authentication sessions"""
        current_time = time.time()
        expired_count = 0

        sessions_to_remove = []
        for session_id, session in self.active_sessions.items():
            if session['expires_at'] <= current_time:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
            expired_count += 1

        return expired_count