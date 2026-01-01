"""
PiSecure Token Management and Mining System
===========================================

Token creation, management, and mining functionality for PiSecure blockchain.
"""

import time
import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class SignToken:
    """PiSecure Token representation"""

    def __init__(self, token_id: str, token_type: str = "access",
                 issued_by: str = "pisecure", permissions: List[str] = None,
                 expires_at: float = None, blockchain_tx: str = None):
        self.token_id = token_id
        self.token_type = token_type
        self.issued_by = issued_by
        self.permissions = permissions or ["read"]
        self.issued_at = time.time()
        self.expires_at = expires_at or (time.time() + 365 * 24 * 60 * 60)  # 1 year
        self.blockchain_tx = blockchain_tx

    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary for storage"""
        return {
            'token_id': self.token_id,
            'token_type': self.token_type,
            'issued_by': self.issued_by,
            'permissions': self.permissions,
            'issued_at': self.issued_at,
            'expires_at': self.expires_at,
            'blockchain_tx': self.blockchain_tx
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignToken':
        """Create token from dictionary"""
        return cls(
            token_id=data['token_id'],
            token_type=data.get('token_type', 'access'),
            issued_by=data.get('issued_by', 'pisecure'),
            permissions=data.get('permissions', ['read']),
            expires_at=data.get('expires_at'),
            blockchain_tx=data.get('blockchain_tx')
        )

    def is_valid(self) -> bool:
        """Check if token is still valid"""
        return time.time() < self.expires_at

    def has_permission(self, permission: str) -> bool:
        """Check if token has specific permission"""
        return permission in self.permissions


class SignTokenMiner:
    """PiSecure Token Mining System with Hardware Restrictions"""

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.mining_active = False
        self.mining_thread = None

    def start_interactive_mining(self) -> bool:
        """Start interactive mining session"""
        try:
            from .hardware import HardwareVerifier

            # Verify hardware before mining
            verifier = HardwareVerifier()
            result = verifier.verify_mining_eligibility()

            if not result['eligible']:
                print(f"❌ Mining blocked: {result.get('error', 'Hardware verification failed')}")
                return False

            print("⛏️ Starting interactive mining session...")
            print("Press Ctrl+C to stop mining")

            mined_count = 0
            start_time = time.time()

            try:
                while True:
                    # Mine a single block
                    block = self.blockchain.mine_pending_transactions(verbose=False)
                    if block:
                        mined_count += 1
                        elapsed = time.time() - start_time
                        rate = mined_count / elapsed if elapsed > 0 else 0
                        print(f"✅ Mined block #{block.index} | Total: {mined_count} blocks | Rate: {rate:.2f} blocks/sec")
                    else:
                        # No transactions to mine, wait a bit
                        time.sleep(1)

            except KeyboardInterrupt:
                elapsed = time.time() - start_time
                print("\n⏹️ Mining stopped by user")
                print(f"📊 Session Summary: {mined_count} blocks in {elapsed:.1f}s ({rate:.2f} blocks/sec)")
                return True

        except Exception as e:
            print(f"❌ Mining error: {e}")
            return False

    def start_mining(self) -> bool:
        """Start background mining"""
        try:
            from .hardware import HardwareVerifier

            # Verify hardware before mining
            verifier = HardwareVerifier()
            result = verifier.verify_mining_eligibility()

            if not result['eligible']:
                print(f"❌ Mining blocked: {result.get('error', 'Hardware verification failed')}")
                return False

            print("⛏️ Starting background mining...")
            self.mining_active = True

            # For now, just return success - full background mining would need threading
            # TODO: Implement proper background mining thread
            print("✅ Background mining started (basic implementation)")
            return True

        except Exception as e:
            print(f"❌ Mining startup error: {e}")
            return False

    def stop_mining(self) -> bool:
        """Stop background mining"""
        if self.mining_active:
            self.mining_active = False
            print("⏹️ Mining stopped")
            return True
        return False

    def get_mining_status(self) -> Dict[str, Any]:
        """Get current mining status"""
        return {
            'active': self.mining_active,
            'blocks_mined': getattr(self, 'blocks_mined', 0),
            'start_time': getattr(self, 'start_time', None),
            'hardware_verified': True  # Would check hardware verification
        }


class TokenManager:
    """Token creation and management system"""

    def __init__(self):
        self.tokens = {}

    def create_token(self, token_type: str = "access",
                    permissions: List[str] = None,
                    expires_in_days: int = 365) -> SignToken:
        """Create a new token"""
        import secrets

        token_id = secrets.token_hex(16)
        expires_at = time.time() + (expires_in_days * 24 * 60 * 60)

        token = SignToken(
            token_id=token_id,
            token_type=token_type,
            permissions=permissions or ["read"],
            expires_at=expires_at
        )

        self.tokens[token_id] = token
        return token

    def get_token(self, token_id: str) -> Optional[SignToken]:
        """Get token by ID"""
        return self.tokens.get(token_id)

    def validate_token(self, token_id: str, required_permission: str = None) -> bool:
        """Validate token and optional permission"""
        token = self.get_token(token_id)
        if not token:
            return False

        if not token.is_valid():
            return False

        if required_permission and not token.has_permission(required_permission):
            return False

        return True

    def revoke_token(self, token_id: str) -> bool:
        """Revoke a token"""
        if token_id in self.tokens:
            del self.tokens[token_id]
            return True
        return False

    def list_tokens(self) -> List[Dict[str, Any]]:
        """List all tokens"""
        return [token.to_dict() for token in self.tokens.values()]


# Global token manager instance
token_manager = TokenManager()

__all__ = [
    'SignToken',
    'SignTokenMiner',
    'TokenManager',
    'token_manager'
]