"""
PiSecure Blockchain Implementation
==================================

Core blockchain classes for SignChain - a proof-of-work blockchain
with hardware-verified mining exclusive to Raspberry Pi devices.
"""

import hashlib
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class SignBlock:
    """Individual block in the PiSecure blockchain"""

    def __init__(self, index: int, transactions: List[Dict], timestamp: float,
                 previous_hash: str, nonce: int = 0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate SHA256 hash of the block"""
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)

        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int = 4, verbose: bool = False) -> bool:
        """Mine the block with proof-of-work"""
        target = "0" * difficulty
        start_time = time.time()
        hashes_tried = 0
        last_update = 0

        if verbose:
            print(f"\n🎯 Mining Block #{self.index}")
            print(f"   Target: {target} (Difficulty: {difficulty})")
            print(f"   Transactions: {len(self.transactions)}")
            print(f"   Previous Hash: {self.previous_hash[:24]}...")
            print("\n" + "="*60)

        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
            hashes_tried += 1

            # Show progress every 5000 attempts in verbose mode (less frequent)
            if verbose and hashes_tried % 5000 == 0:
                elapsed = time.time() - start_time
                hashrate = hashes_tried / elapsed if elapsed > 0 else 0
                current_prefix = self.hash[:difficulty]
                progress = sum(1 for a, b in zip(current_prefix, target) if a == b)

                # Clear line and update in place
                print(f"\r⛏️  Mining... Nonce: {self.nonce:,} | Progress: {progress}/{difficulty} | Hashrate: {hashrate:.0f} H/s", end="", flush=True)

            # Prevent infinite loop in testing
            if self.nonce > 1000000:
                if verbose:
                    print(f"\n❌ Mining failed - exceeded 1M attempts")
                return False

        # Found a valid nonce!
        elapsed = time.time() - start_time
        hashrate = hashes_tried / elapsed if elapsed > 0 else 0

        if verbose:
            # Clear the progress line and show success
            print(f"\r{' '*60}")  # Clear the line
            print(f"\r🎉 BLOCK FOUND! 🎉")
            print(f"   Nonce: {self.nonce:,}")
            print(f"   Hash: {self.hash[:48]}...")
            print(f"   Attempts: {hashes_tried:,}")
            print(f"   Time: {elapsed:.2f}s")
            print(f"   Hashrate: {hashrate:.0f} H/s")
            print("="*60)

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary"""
        return {
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }


class SignChain:
    """PiSecure Private Blockchain with Hardware Verification"""

    def __init__(self, chain_file: str = "/var/lib/pisecure/blockchain.json",
                 difficulty: int = 4):
        self.chain_file = Path(chain_file)
        self.pending_file = Path(chain_file).parent / "pending_transactions.json"
        self.difficulty = difficulty
        self.chain: List[SignBlock] = []
        self.pending_transactions: List[Dict] = []
        self.lock = threading.Lock()

        # Load existing chain or create genesis
        self.load_chain()
        self.load_pending_transactions()

    def create_genesis_block(self) -> SignBlock:
        """Create the genesis block"""
        genesis_transactions = [{
            "type": "genesis",
            "data": {
                "message": "PiSecure Blockchain Initialized",
                "timestamp": time.time(),
                "version": "0.1.0"
            },
            "signature": "pisecure-genesis-signature",
            "timestamp": time.time()
        }]

        genesis = SignBlock(
            index=0,
            transactions=genesis_transactions,
            timestamp=time.time(),
            previous_hash="0"
        )

        return genesis

    def load_chain(self):
        """Load blockchain from file"""
        if self.chain_file.exists():
            try:
                with open(self.chain_file, 'r') as f:
                    chain_data = json.load(f)

                self.chain = []
                for block_data in chain_data:
                    block = SignBlock(
                        index=block_data["index"],
                        transactions=block_data["transactions"],
                        timestamp=block_data["timestamp"],
                        previous_hash=block_data["previous_hash"],
                        nonce=block_data["nonce"]
                    )
                    block.hash = block_data["hash"]
                    self.chain.append(block)

                print(f"✅ Loaded blockchain with {len(self.chain)} blocks")

            except Exception as e:
                print(f"❌ Failed to load blockchain: {e}")
                self.chain = [self.create_genesis_block()]
                self.save_chain()
        else:
            # Create new blockchain
            self.chain = [self.create_genesis_block()]
            self.save_chain()

    def save_chain(self):
        """Save blockchain to file"""
        try:
            chain_data = [block.to_dict() for block in self.chain]

            # Ensure directory exists
            self.chain_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.chain_file, 'w') as f:
                json.dump(chain_data, f, indent=2)

        except Exception as e:
            print(f"❌ Failed to save blockchain: {e}")

    def load_pending_transactions(self):
        """Load pending transactions from file"""
        if self.pending_file.exists():
            try:
                with open(self.pending_file, 'r') as f:
                    pending_data = json.load(f)
                    self.pending_transactions = pending_data
                    print(f"✅ Loaded {len(self.pending_transactions)} pending transactions")
            except Exception as e:
                print(f"❌ Failed to load pending transactions: {e}")
                self.pending_transactions = []

    def save_pending_transactions(self):
        """Save pending transactions to file"""
        try:
            # Ensure directory exists
            self.pending_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.pending_file, 'w') as f:
                json.dump(self.pending_transactions, f, indent=2)

        except Exception as e:
            print(f"❌ Failed to save pending transactions: {e}")

    def add_transaction(self, transaction: Dict[str, Any]) -> str:
        """Add transaction to pending transactions with wallet validation"""
        with self.lock:
            # Validate transaction based on type
            validation_result = self._validate_transaction(transaction)
            if not validation_result['valid']:
                raise ValueError(f"Transaction validation failed: {validation_result['error']}")

            # Add timestamp if not present
            if "timestamp" not in transaction:
                transaction["timestamp"] = time.time()

            self.pending_transactions.append(transaction)

            # Save pending transactions to persist across script runs
            self.save_pending_transactions()

            # Return transaction hash for tracking
            tx_string = json.dumps(transaction, sort_keys=True)
            return hashlib.sha256(tx_string.encode()).hexdigest()

    def _validate_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Validate transaction before adding to pending pool"""
        tx_type = transaction.get('type', '')

        if tx_type == 'token_transfer':
            return self._validate_token_transfer(transaction)
        elif tx_type == 'batch_transfer':
            return self._validate_batch_transfer(transaction)
        elif tx_type in ['genesis', 'test_transaction', 'sensor_reading']:
            # These don't require wallet validation
            return {'valid': True}
        else:
            return {
                'valid': False,
                'error': f'Unknown transaction type: {tx_type}'
            }

    def _validate_token_transfer(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Validate token transfer transaction"""
        try:
            # Required fields
            required_fields = ['sender_address', 'recipient_address', 'amount', 'signature']
            for field in required_fields:
                if field not in transaction:
                    return {
                        'valid': False,
                        'error': f'Missing required field: {field}'
                    }

            sender_address = transaction['sender_address']
            amount = transaction['amount']

            # Validate amount
            if not isinstance(amount, (int, float)) or amount <= 0:
                return {
                    'valid': False,
                    'error': f'Invalid amount: {amount}'
                }

            # Check sender balance (simplified - should query wallet system)
            # In production, this would query the wallet system or maintain balances
            sender_balance = self._get_wallet_balance(sender_address)
            if sender_balance < amount:
                return {
                    'valid': False,
                    'error': f'Insufficient balance: {sender_balance} < {amount}'
                }

            # Verify signature (simplified - should use wallet system)
            # In production, this would verify against sender's public key
            signature = transaction.get('signature')
            if not signature:
                return {
                    'valid': False,
                    'error': 'Missing transaction signature'
                }

            # For now, accept all signatures (implement proper verification later)
            # sender_public_key = self._get_wallet_public_key(sender_address)
            # if not self._verify_transaction_signature(transaction, signature, sender_public_key):
            #     return {'valid': False, 'error': 'Invalid transaction signature'}

            return {'valid': True}

        except Exception as e:
            return {
                'valid': False,
                'error': f'Transfer validation error: {e}'
            }

    def _validate_batch_transfer(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Validate batch transfer transaction"""
        try:
            # Required fields
            required_fields = ['sender_address', 'transfers', 'total_amount', 'signature']
            for field in required_fields:
                if field not in transaction:
                    return {
                        'valid': False,
                        'error': f'Missing required field: {field}'
                    }

            sender_address = transaction['sender_address']
            transfers = transaction['transfers']
            total_amount = transaction['total_amount']

            # Validate transfers list
            if not isinstance(transfers, list) or not transfers:
                return {
                    'valid': False,
                    'error': 'Invalid transfers list'
                }

            # Validate each transfer
            calculated_total = 0
            for transfer in transfers:
                if not isinstance(transfer, dict):
                    return {
                        'valid': False,
                        'error': 'Invalid transfer format'
                    }

                recipient = transfer.get('recipient')
                amount = transfer.get('amount')

                if not recipient or not isinstance(amount, (int, float)) or amount <= 0:
                    return {
                        'valid': False,
                        'error': f'Invalid transfer: {transfer}'
                    }

                calculated_total += amount

            # Verify total amount
            if abs(calculated_total - total_amount) > 0.001:  # Small tolerance for float precision
                return {
                    'valid': False,
                    'error': f'Total amount mismatch: {calculated_total} vs {total_amount}'
                }

            # Check sender balance
            sender_balance = self._get_wallet_balance(sender_address)
            if sender_balance < total_amount:
                return {
                    'valid': False,
                    'error': f'Insufficient balance for batch: {sender_balance} < {total_amount}'
                }

            return {'valid': True}

        except Exception as e:
            return {
                'valid': False,
                'error': f'Batch transfer validation error: {e}'
            }

    def _get_wallet_balance(self, wallet_address: str) -> float:
        """Get wallet balance (simplified implementation)"""
        # In production, this would query a wallet database or service
        # For now, return a mock balance
        # This should be replaced with actual wallet balance checking

        # Mock implementation - check if wallet has been seen in recent transactions
        for block in reversed(self.chain[-10:]):  # Check last 10 blocks
            for tx in block.transactions:
                if tx.get('type') in ['token_transfer', 'batch_transfer']:
                    # If wallet was recipient, add to balance
                    if tx.get('recipient_address') == wallet_address:
                        # This is very simplified - real implementation would track balances properly
                        return 1000.0  # Mock balance
                    # If wallet was sender, subtract from balance
                    elif tx.get('sender_address') == wallet_address:
                        return 500.0  # Mock balance

        return 100.0  # Default mock balance

    def _get_wallet_public_key(self, wallet_address: str) -> Optional[str]:
        """Get wallet public key (placeholder)"""
        # In production, this would query wallet service
        return None

    def _verify_transaction_signature(self, transaction: Dict[str, Any],
                                    signature: str, public_key_pem: str) -> bool:
        """Verify transaction signature (placeholder)"""
        # In production, this would use cryptography library
        return True  # Mock validation

    def get_wallet_balance(self, wallet_address: str) -> float:
        """Public method to get wallet balance"""
        return self._get_wallet_balance(wallet_address)

    def get_wallet_transactions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get all transactions involving a wallet"""
        wallet_transactions = []

        for block in self.chain:
            for tx in block.transactions:
                if tx.get('type') in ['token_transfer', 'batch_transfer']:
                    if (tx.get('sender_address') == wallet_address or
                        tx.get('recipient_address') == wallet_address):
                        wallet_transactions.append({
                            'tx_hash': hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest(),
                            'block_index': block.index,
                            'timestamp': tx.get('timestamp'),
                            'type': tx.get('type'),
                            'amount': tx.get('amount', 0),
                            'direction': 'incoming' if tx.get('recipient_address') == wallet_address else 'outgoing'
                        })

        return wallet_transactions

    def mine_pending_transactions(self, verbose: bool = False) -> Optional[SignBlock]:
        """Mine a new block with pending transactions"""
        if not self.pending_transactions:
            return None

        with self.lock:
            # Create new block
            last_block = self.chain[-1]
            new_block = SignBlock(
                index=last_block.index + 1,
                transactions=self.pending_transactions.copy(),
                timestamp=time.time(),
                previous_hash=last_block.hash
            )

            # Mine the block
            if new_block.mine_block(self.difficulty, verbose):
                # Add to chain
                self.chain.append(new_block)
                self.save_chain()

                # Clear pending transactions
                self.pending_transactions.clear()

                print(f"✅ Mined new block: {new_block.index} with {len(new_block.transactions)} transactions")
                return new_block
            else:
                print("❌ Failed to mine block")
                return None

    def get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction by hash"""
        for block in self.chain:
            for transaction in block.transactions:
                tx_string = json.dumps(transaction, sort_keys=True)
                if hashlib.sha256(tx_string.encode()).hexdigest() == tx_hash:
                    return transaction
        return None

    def validate_chain(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]

            # Check hash consistency
            if current.hash != current.calculate_hash():
                print(f"❌ Block {current.index} has invalid hash")
                return False

            # Check chain linkage
            if current.previous_hash != previous.hash:
                print(f"❌ Block {current.index} has invalid previous hash")
                return False

            # Check proof-of-work
            if not current.hash.startswith("0" * self.difficulty):
                print(f"❌ Block {current.index} has invalid proof-of-work")
                return False

        return True

    def get_chain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return {
            "blocks": len(self.chain),
            "pending_transactions": len(self.pending_transactions),
            "difficulty": self.difficulty,
            "latest_block": self.chain[-1].to_dict() if self.chain else None,
            "is_valid": self.validate_chain(),
            "network_health": self._calculate_network_health()
        }

    def _calculate_network_health(self) -> Dict[str, Any]:
        """Calculate network health metrics for adaptive systems"""
        if not self.chain:
            return {"participation": 0, "avg_block_time": 0, "health_score": 0}

        # Calculate average block time (last 10 blocks)
        recent_blocks = self.chain[-10:] if len(self.chain) > 1 else self.chain
        if len(recent_blocks) > 1:
            block_times = []
            for i in range(1, len(recent_blocks)):
                time_diff = recent_blocks[i].timestamp - recent_blocks[i-1].timestamp
                block_times.append(time_diff)
            avg_block_time = sum(block_times) / len(block_times)
        else:
            avg_block_time = 600  # 10 minutes default

        # Participation score based on transaction volume
        total_txs = sum(len(block.transactions) for block in recent_blocks)
        participation = min(1.0, total_txs / 50)  # Scale to 0-1

        # Health score combines multiple factors
        health_score = (participation * 0.6) + ((1 - min(1, avg_block_time / 1200)) * 0.4)

        return {
            "participation": participation,
            "avg_block_time": avg_block_time,
            "health_score": health_score
        }

    def adapt_difficulty(self) -> int:
        """Adapt difficulty based on network health"""
        health = self._calculate_network_health()
        current_difficulty = self.difficulty

        # Target: 10 minute average block time
        target_block_time = 600
        actual_block_time = health["avg_block_time"]

        if actual_block_time < target_block_time * 0.8:
            # Blocks too fast - increase difficulty slightly
            new_difficulty = min(current_difficulty + 1, 8)  # Cap at 8
        elif actual_block_time > target_block_time * 1.2:
            # Blocks too slow - decrease difficulty
            new_difficulty = max(current_difficulty - 1, 2)  # Floor at 2
        else:
            # Optimal range - maintain current difficulty
            new_difficulty = current_difficulty

        if new_difficulty != current_difficulty:
            self.difficulty = new_difficulty
            print(f"⚖️ Difficulty adapted: {current_difficulty} → {new_difficulty}")

        return new_difficulty

    def calculate_mining_reward(self, block: SignBlock, miner_stats: Dict = None) -> int:
        """Calculate sustainable mining reward based on work performed"""
        if miner_stats is None:
            miner_stats = {}

        base_reward = 10  # Stable base reward

        # Transaction volume bonus (0.5 tokens per tx)
        tx_bonus = len(block.transactions) * 0.5

        # Security work bonus
        security_bonus = 0
        for tx in block.transactions:
            tx_type = tx.get('type', '')
            if tx_type in ['security_alert', 'threat_detected', 'system_compromise']:
                security_bonus += 3  # High value security work
            elif tx_type in ['device_auth', 'bundle_verify', 'token_validate']:
                security_bonus += 1  # Standard security work

        # Participation bonus based on network health
        health = self._calculate_network_health()
        participation_bonus = base_reward * (1 - health["participation"]) * 0.5

        # Uptime/reliability bonus
        uptime_bonus = miner_stats.get('uptime_percentage', 100) / 100 * 2

        # P2P contribution bonus
        p2p_bonus = miner_stats.get('p2p_contributions', 0) * 0.1

        total_reward = base_reward + tx_bonus + security_bonus + participation_bonus + uptime_bonus + p2p_bonus

        # Cap reward to prevent inflation
        return min(int(total_reward), 30)