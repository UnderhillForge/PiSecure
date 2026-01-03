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

try:
    from .storage import HybridBlockchainStorage
    HYBRID_STORAGE_AVAILABLE = True
except ImportError:
    HYBRID_STORAGE_AVAILABLE = False


class SignBlock:
    """Individual block in the PiSecure blockchain"""

    def __init__(self, index: int, transactions: List[Dict], timestamp: float,
                 previous_hash: str, nonce: int = 0, algorithm: str = 'sha256'):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.algorithm = algorithm  # Mining algorithm: 'sha256' or 'sha3'
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate hash of the block using specified algorithm"""
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)

        if self.algorithm == 'sha3':
            return hashlib.sha3_256(block_string.encode()).hexdigest()
        elif self.algorithm == 'pi-optimized':
            return self._calculate_pi_optimized_hash(block_string)
        else:  # Default to sha256
            return hashlib.sha256(block_string.encode()).hexdigest()

    def _calculate_pi_optimized_hash(self, block_string: str) -> str:
        """Calculate Pi-optimized hash that benefits Raspberry Pi hardware"""
        try:
            # Get Raspberry Pi hardware information
            pi_info = self._get_pi_hardware_info()

            # Combine block data with Pi-specific hardware entropy
            enhanced_data = f"{block_string}|{pi_info['serial']}|{pi_info['temperature']}|{pi_info['uptime']}"

            # Use multiple hashing rounds optimized for ARM
            hash1 = hashlib.sha256(enhanced_data.encode()).digest()
            hash2 = hashlib.sha3_256(hash1).digest()
            hash3 = hashlib.blake2b(hash2, digest_size=32).digest()

            # Final ARM-optimized mixing (simulated NEON operations)
            final_hash = self._arm_optimized_mix(hash3, pi_info)

            return final_hash.hex()

        except Exception as e:
            # Fallback to SHA256 if Pi-specific features fail
            print(f"⚠️ Pi-optimized hash failed ({e}), falling back to SHA256")
            return hashlib.sha256(block_string.encode()).hexdigest()

    def _get_pi_hardware_info(self) -> Dict[str, str]:
        """Get Raspberry Pi hardware information for mining"""
        try:
            # CPU serial number (unique per Pi)
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                serial_match = None
                for line in cpuinfo.split('\n'):
                    if line.startswith('Serial'):
                        serial_match = line.split(':')[1].strip()
                        break
                serial = serial_match or 'unknown'

            # CPU temperature
            temperature = 'unknown'
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_milli = int(f.read().strip())
                    temperature = str(temp_milli // 1000)  # Convert to Celsius
            except:
                pass

            # System uptime (changes constantly)
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = f.read().split()[0]
                uptime = uptime_seconds.split('.')[0]  # Whole seconds only

            return {
                'serial': serial,
                'temperature': temperature,
                'uptime': uptime
            }

        except Exception as e:
            # Return safe defaults if hardware reading fails
            return {
                'serial': 'fallback',
                'temperature': '20',
                'uptime': str(int(time.time()))
            }

    def _arm_optimized_mix(self, data: bytes, pi_info: Dict[str, str]) -> bytes:
        """ARM-optimized mixing function (simulates NEON operations) with safe None handling"""
        try:
            # Safe conversion of hardware info with comprehensive None checking
            serial_str = pi_info.get('serial') or 'fallback'
            temp_str = pi_info.get('temperature') or '20'
            uptime_str = pi_info.get('uptime') or '0'

            # Convert to integers safely
            try:
                serial_num = int(serial_str[-8:], 16) if len(serial_str) >= 8 else 0x12345678
            except (ValueError, TypeError):
                serial_num = 0x12345678  # Safe fallback

            try:
                temp_num = int(temp_str) if temp_str and temp_str.isdigit() else 20
            except (ValueError, TypeError, AttributeError):
                temp_num = 20  # Safe fallback

            try:
                uptime_num = int(uptime_str) % 1000000 if uptime_str and uptime_str.isdigit() else 0
            except (ValueError, TypeError, AttributeError):
                uptime_num = 0  # Safe fallback

            # ARM-style mixing (simulated - would use actual NEON in C extension)
            mixed = bytearray(data)

            # XOR with hardware entropy (all values are now guaranteed to be integers)
            for i in range(len(mixed)):
                hw_byte = (serial_num >> (i % 32)) & 0xFF
                hw_byte ^= (temp_num + uptime_num) & 0xFF
                mixed[i] ^= hw_byte

            # Additional mixing rounds
            for round_num in range(3):  # 3 mixing rounds
                for i in range(len(mixed) - 4):
                    # Simulate ARM vector operations
                    val = int.from_bytes(mixed[i:i+4], 'little')
                    val = ((val << 13) | (val >> 19))  # Rotate
                    val ^= serial_num  # XOR with hardware (serial_num is now safe)
                    val = (val * 0x9E3779B9) & 0xFFFFFFFF  # Multiply
                    mixed[i:i+4] = val.to_bytes(4, 'little')

            return bytes(mixed)

        except Exception as e:
            # Log the error for debugging but don't crash
            print(f"⚠️ ARM mixing failed safely: {e}")
            # Return original data if mixing fails
            return data

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
                 difficulty: int = 8, use_hybrid_storage: bool = None,
                 mining_algorithm: str = 'sha3'):
        self.chain_file = Path(chain_file)
        self.pending_file = Path(chain_file).parent / "pending_transactions.json"
        self.names_file = Path(chain_file).parent / "name_registry.json"
        self.difficulty = difficulty
        self.chain: List[SignBlock] = []
        self.pending_transactions: List[Dict] = []
        self.name_registry: Dict[str, Dict[str, Any]] = {}  # name -> {address, registered_at, tx_hash}
        self.lock = threading.Lock()

        # Storage system - default to hybrid if available and not explicitly disabled
        if use_hybrid_storage is None:
            use_hybrid_storage = HYBRID_STORAGE_AVAILABLE  # Default to hybrid if available

        self.use_hybrid_storage = use_hybrid_storage and HYBRID_STORAGE_AVAILABLE
        if self.use_hybrid_storage:
            self.hybrid_storage = HybridBlockchainStorage(str(self.chain_file.parent))
            # Migrate from JSON if needed (only if JSON exists and no hybrid data)
            self.hybrid_storage.migrate_from_json(str(self.chain_file))
        else:
            self.hybrid_storage = None

        # Validation cache
        self._last_validation_time = 0
        self._validation_cache_timeout = 30  # Cache validation for 30 seconds
        self._cached_chain_valid = None

        # Load existing chain or create genesis
        self.load_chain()
        self.load_pending_transactions()
        self.load_name_registry()
        self._rebuild_name_registry()  # Rebuild from blockchain

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
        """Load blockchain from file or hybrid storage"""
        if self.use_hybrid_storage and self.hybrid_storage:
            # Load from hybrid storage
            self._load_chain_from_hybrid_storage()
        else:
            # Load from JSON file
            self._load_chain_from_json()

    def _load_chain_from_json(self):
        """Load blockchain from JSON file (legacy method)"""
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

                print(f"✅ Loaded blockchain with {len(self.chain)} blocks from JSON")

            except Exception as e:
                print(f"❌ Failed to load blockchain: {e}")
                self.chain = [self.create_genesis_block()]
                self.save_chain()
        else:
            # Create new blockchain
            self.chain = [self.create_genesis_block()]
            self.save_chain()

    def _load_chain_from_hybrid_storage(self):
        """Load blockchain from hybrid storage"""
        try:
            # Get all block hashes in order
            latest_height = self.hybrid_storage.index_db.get_latest_block_height()

            if latest_height < 0:
                # No blocks in hybrid storage, create genesis
                self.chain = [self.create_genesis_block()]
                self.hybrid_storage.save_block(self.chain[0].to_dict())
                print("✅ Created genesis block in hybrid storage")
                return

            # Load all blocks
            self.chain = []
            for height in range(latest_height + 1):
                block_hash = self.hybrid_storage.index_db.get_block_hash(height)
                if block_hash:
                    block_data = self.hybrid_storage.load_block(block_hash)
                    if block_data:
                        block = SignBlock(
                            index=block_data["index"],
                            transactions=block_data["transactions"],
                            timestamp=block_data["timestamp"],
                            previous_hash=block_data["previous_hash"],
                            nonce=block_data["nonce"]
                        )
                        block.hash = block_data["hash"]
                        self.chain.append(block)

            print(f"✅ Loaded blockchain with {len(self.chain)} blocks from hybrid storage")

        except Exception as e:
            print(f"❌ Failed to load from hybrid storage: {e}")
            # Fallback to JSON loading
            self.use_hybrid_storage = False
            self._load_chain_from_json()

    def save_chain(self):
        """Save blockchain to file or hybrid storage"""
        if self.use_hybrid_storage and self.hybrid_storage:
            # Hybrid storage handles block saving incrementally
            # All blocks are already saved when added
            return

        # Fallback to JSON storage
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
        elif tx_type == 'name_registration':
            return self._validate_name_registration(transaction)
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
        """Get wallet balance by tracking all transactions in the blockchain"""
        balance = 0.0

        # Track all transactions involving this wallet
        for block in self.chain:
            for tx in block.transactions:
                tx_type = tx.get('type', '')

                if tx_type == 'mining_reward':
                    # Mining rewards add to balance
                    if tx.get('recipient_address') == wallet_address:
                        balance += tx.get('amount', 0)

                elif tx_type == 'token_transfer':
                    # Token transfers
                    if tx.get('recipient_address') == wallet_address:
                        balance += tx.get('amount', 0)
                    elif tx.get('sender_address') == wallet_address:
                        balance -= tx.get('amount', 0)

                elif tx_type == 'batch_transfer':
                    # Batch transfers
                    transfers = tx.get('transfers', [])
                    for transfer in transfers:
                        if transfer.get('recipient') == wallet_address:
                            balance += transfer.get('amount', 0)
                    # Subtract total from sender
                    if tx.get('sender_address') == wallet_address:
                        balance -= tx.get('total_amount', 0)

                elif tx_type == 'name_registration':
                    # Name registration fee
                    if tx.get('wallet_address') == wallet_address:
                        balance -= tx.get('registration_fee', 5.0)

        return max(0.0, balance)  # Ensure balance never goes negative

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
        if self.use_hybrid_storage and self.hybrid_storage:
            return self.hybrid_storage.get_wallet_balance(wallet_address)
        return self._get_wallet_balance(wallet_address)

    def get_wallet_transactions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get all transactions involving a wallet"""
        if self.use_hybrid_storage and self.hybrid_storage:
            # Use hybrid storage for better performance
            return self._get_wallet_transactions_hybrid(wallet_address)
        else:
            # Fallback to in-memory scanning
            return self._get_wallet_transactions_memory(wallet_address)

    def _get_wallet_transactions_hybrid(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get wallet transactions using hybrid storage (database)"""
        if not self.hybrid_storage:
            return self._get_wallet_transactions_memory(wallet_address)

        try:
            return self.hybrid_storage.get_wallet_transactions(wallet_address)
        except Exception as e:
            print(f"Hybrid wallet lookup failed: {e}, falling back to memory")
            return self._get_wallet_transactions_memory(wallet_address)

    def _get_wallet_transactions_memory(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get wallet transactions by scanning in-memory chain"""
        wallet_transactions = []

        for block in self.chain:
            for tx in block.transactions:
                if tx.get('type') in ['token_transfer', 'batch_transfer', 'mining_reward']:
                    if (tx.get('sender_address') == wallet_address or
                        tx.get('recipient_address') == wallet_address):
                        wallet_transactions.append({
                            'tx_hash': hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest(),
                            'block_index': block.index,
                            'timestamp': tx.get('timestamp'),
                            'type': tx.get('type'),
                            'amount': tx.get('amount', 0),
                            'direction': 'incoming' if tx.get('recipient_address') == wallet_address else 'outgoing',
                            'sender': tx.get('sender_address'),
                            'recipient': tx.get('recipient_address')
                        })

        return wallet_transactions

    def mine_pending_transactions(self, miner_wallet_address: str = None, verbose: bool = False) -> Optional[SignBlock]:
        """Mine a new block with pending transactions and distribute mining rewards"""
        # Always mine blocks (like Bitcoin) - even without pending transactions
        # Mining rewards provide the incentive to maintain the network

        with self.lock:
            # Create mining reward transaction if miner wallet is specified
            block_transactions = self.pending_transactions.copy()

            if miner_wallet_address:
                # Calculate mining reward
                mining_reward = self.calculate_mining_reward(None, {})  # Simplified for now

                # Create mining reward transaction
                reward_tx = {
                    "type": "mining_reward",
                    "recipient_address": miner_wallet_address,
                    "amount": mining_reward,
                    "block_index": len(self.chain),  # Will be set when block is created
                    "timestamp": time.time(),
                    "signature": f"mining-reward-{len(self.chain)}"
                }

                # Add reward transaction at the beginning
                block_transactions.insert(0, reward_tx)

                if verbose:
                    print(f"💰 Mining reward: {mining_reward} tokens to {miner_wallet_address}")

            # Create new block
            last_block = self.chain[-1]
            new_block = SignBlock(
                index=last_block.index + 1,
                transactions=block_transactions,
                timestamp=time.time(),
                previous_hash=last_block.hash,
                algorithm=self.mining_algorithm  # Use configured mining algorithm
            )

            # Update block index in reward transaction
            if miner_wallet_address and block_transactions:
                block_transactions[0]["block_index"] = new_block.index

            # Mine the block
            if new_block.mine_block(self.difficulty, verbose):
                # Add to chain
                self.chain.append(new_block)

                # Save using appropriate storage method
                if self.use_hybrid_storage and self.hybrid_storage:
                    self.hybrid_storage.save_block(new_block.to_dict())
                else:
                    self.save_chain()

                # Invalidate validation cache
                self._cached_chain_valid = None

                # Clear pending transactions
                self.pending_transactions.clear()

                total_txs = len(new_block.transactions)
                reward_info = f" (+{mining_reward} reward)" if miner_wallet_address else ""
                print(f"✅ Mined new block: #{new_block.index} with {total_txs} transactions{reward_info}")

                # Trigger network discovery after successful block mining
                try:
                    import threading
                    threading.Thread(target=self._trigger_discovery_on_block, args=(new_block,), daemon=True).start()
                except Exception as e:
                    print(f"⚠️ Failed to trigger discovery after mining: {e}")

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
        """Validate the entire blockchain with caching"""
        current_time = time.time()

        # Return cached result if still valid
        if (self._cached_chain_valid is not None and
            current_time - self._last_validation_time < self._validation_cache_timeout):
            return self._cached_chain_valid

        # Perform full validation
        is_valid = True
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]

            # Check hash consistency
            if current.hash != current.calculate_hash():
                print(f"❌ Block {current.index} has invalid hash")
                is_valid = False
                break

            # Check chain linkage
            if current.previous_hash != previous.hash:
                print(f"❌ Block {current.index} has invalid previous hash")
                is_valid = False
                break

            # Check proof-of-work
            if not current.hash.startswith("0" * self.difficulty):
                print(f"❌ Block {current.index} has invalid proof-of-work")
                is_valid = False
                break

        # Cache the result
        self._cached_chain_valid = is_valid
        self._last_validation_time = current_time

        return is_valid

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

    def calculate_mining_reward(self, block: SignBlock = None, miner_stats: Dict = None) -> int:
        """Calculate sustainable mining reward based on work performed"""
        if miner_stats is None:
            miner_stats = {}

        base_reward = 10  # Stable base reward

        # Transaction volume bonus (0.5 tokens per tx)
        if block is not None:
            tx_bonus = len(block.transactions) * 0.5
        else:
            # If no block provided, use pending transactions count
            tx_bonus = len(self.pending_transactions) * 0.5

        # Security work bonus
        security_bonus = 0
        transactions_to_check = block.transactions if block is not None else self.pending_transactions
        for tx in transactions_to_check:
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

        # === EXCHANGE MINING REWARDS PROGRAM ===
        # Exchanges get 2x mining rewards for running infrastructure nodes
        exchange_bonus = 0
        miner_wallet = miner_stats.get('wallet_address', '')
        if self._is_exchange_node(miner_wallet):
            exchange_bonus = base_reward  # Additional full base reward (2x total)
            print(f"🏢 Exchange mining bonus: +{exchange_bonus} tokens for infrastructure contribution")

        total_reward = base_reward + tx_bonus + security_bonus + participation_bonus + uptime_bonus + p2p_bonus + exchange_bonus

        # Cap reward to prevent inflation
        return min(int(total_reward), 50)  # Increased cap for exchange rewards

    def _is_exchange_node(self, wallet_address: str) -> bool:
        """Check if a wallet belongs to a registered exchange node"""
        if not wallet_address:
            return False

        # Check exchange registry (loaded from configuration or blockchain state)
        exchange_registry = getattr(self, 'exchange_registry', set())

        # Also check for exchange-specific transaction patterns in recent blocks
        if self._has_exchange_transaction_pattern(wallet_address):
            return True

        return wallet_address in exchange_registry

    def _has_exchange_transaction_pattern(self, wallet_address: str) -> bool:
        """Check if wallet shows exchange-like transaction patterns"""
        if len(self.chain) < 10:  # Need some history
            return False

        recent_blocks = self.chain[-10:]  # Last 10 blocks
        exchange_indicators = 0

        for block in recent_blocks:
            for tx in block.transactions:
                if tx.get('recipient') == wallet_address or tx.get('sender') == wallet_address:
                    tx_type = tx.get('type', '')

                    # Exchanges typically have high volume of these transaction types
                    if tx_type in ['deposit', 'withdrawal', 'exchange_transfer']:
                        exchange_indicators += 1

                    # High frequency of small transfers (trading activity)
                    if tx_type == 'token_transfer' and tx.get('amount', 0) < 100:
                        exchange_indicators += 0.5

        # If wallet shows significant exchange-like activity, consider it an exchange
        return exchange_indicators >= 5

    def register_exchange_node(self, exchange_id: str, wallet_address: str, metadata: Dict = None) -> bool:
        """Register an exchange node for mining rewards program"""
        if not hasattr(self, 'exchange_registry'):
            self.exchange_registry = set()

        if not metadata:
            metadata = {}

        # Validate exchange credentials (in production, this would involve verification)
        if self._validate_exchange_registration(exchange_id, wallet_address, metadata):
            self.exchange_registry.add(wallet_address)
            print(f"🏢 Registered exchange node: {exchange_id} ({wallet_address})")

            # Create registration transaction on blockchain
            registration_tx = {
                "type": "exchange_registration",
                "exchange_id": exchange_id,
                "wallet_address": wallet_address,
                "metadata": metadata,
                "timestamp": time.time(),
                "signature": f"exchange-reg-{exchange_id}-{wallet_address}"
            }

            # Add to pending transactions
            self.pending_transactions.append(registration_tx)
            return True

        return False

    def _validate_exchange_registration(self, exchange_id: str, wallet_address: str, metadata: Dict) -> bool:
        """Validate exchange registration request"""
        # Basic validation - in production this would be more thorough
        required_fields = ['contact_email', 'jurisdiction', 'compliance_certified']

        for field in required_fields:
            if field not in metadata:
                print(f"❌ Missing required field: {field}")
                return False

        # Check if wallet address is valid format
        if not wallet_address or len(wallet_address) < 20:
            print("❌ Invalid wallet address format")
            return False

        # Check if exchange_id is unique
        existing_exchanges = [tx.get('exchange_id') for block in self.chain
                            for tx in block.transactions
                            if tx.get('type') == 'exchange_registration']

        if exchange_id in existing_exchanges:
            print(f"❌ Exchange ID already registered: {exchange_id}")
            return False

        return True

    # === CROSS-EXCHANGE SETTLEMENT SYSTEM ===
    def create_cross_exchange_settlement(self, from_exchange: str, to_exchange: str,
                                       amount: float, user_from: str, user_to: str,
                                       settlement_id: str = None) -> Dict:
        """Create an instant cross-exchange settlement transaction"""
        if not settlement_id:
            settlement_id = f"settlement_{int(time.time())}_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}"

        # Generate cryptographic secret for hash-locked transaction
        secret = hashlib.sha256(str(time.time() + amount).encode()).hexdigest()
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()

        settlement_tx = {
            "type": "cross_exchange_settlement",
            "settlement_id": settlement_id,
            "from_exchange": from_exchange,
            "to_exchange": to_exchange,
            "amount": amount,
            "user_from": user_from,
            "user_to": user_to,
            "secret_hash": secret_hash,
            "status": "pending_lock",
            "timestamp": time.time(),
            "lock_time": time.time() + 3600,  # 1 hour timeout
            "signature": f"settlement-{settlement_id}"
        }

        # Add to pending transactions
        self.pending_transactions.append(settlement_tx)

        return {
            "settlement_id": settlement_id,
            "secret": secret,  # Only return to initiating party
            "secret_hash": secret_hash,
            "transaction": settlement_tx
        }

    def lock_settlement_funds(self, settlement_id: str, exchange_wallet: str,
                            amount: float, secret_hash: str) -> bool:
        """Lock funds for cross-exchange settlement"""
        # Find the settlement transaction
        settlement_tx = None
        for tx in self.pending_transactions:
            if (tx.get('type') == 'cross_exchange_settlement' and
                tx.get('settlement_id') == settlement_id):
                settlement_tx = tx
                break

        if not settlement_tx:
            return False

        # Create hash-locked transfer
        lock_tx = {
            "type": "hash_locked_transfer",
            "settlement_id": settlement_id,
            "sender": exchange_wallet,
            "amount": amount,
            "secret_hash": secret_hash,
            "recipient": settlement_tx['to_exchange'],  # Will be claimable by recipient exchange
            "lock_time": settlement_tx['lock_time'],
            "status": "locked",
            "timestamp": time.time(),
            "signature": f"lock-{settlement_id}-{exchange_wallet}"
        }

        self.pending_transactions.append(lock_tx)
        settlement_tx['status'] = 'funds_locked'

        return True

    def complete_settlement(self, settlement_id: str, secret: str) -> bool:
        """Complete settlement by revealing the secret"""
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()

        # Find and update locked transactions
        settlement_completed = False
        for tx in self.pending_transactions:
            if (tx.get('type') == 'hash_locked_transfer' and
                tx.get('settlement_id') == settlement_id and
                tx.get('secret_hash') == secret_hash):

                # Verify secret matches hash
                if tx['secret_hash'] == secret_hash:
                    # Create the actual transfer
                    transfer_tx = {
                        "type": "token_transfer",
                        "sender": tx['sender'],
                        "recipient": tx['recipient'],
                        "amount": tx['amount'],
                        "settlement_id": settlement_id,
                        "timestamp": time.time(),
                        "signature": f"settlement-complete-{settlement_id}"
                    }

                    self.pending_transactions.append(transfer_tx)
                    tx['status'] = 'completed'
                    settlement_completed = True

        # Update settlement status
        for tx in self.pending_transactions:
            if (tx.get('type') == 'cross_exchange_settlement' and
                tx.get('settlement_id') == settlement_id):
                tx['status'] = 'completed'
                tx['completion_time'] = time.time()

        return settlement_completed

    def refund_expired_settlement(self, settlement_id: str) -> bool:
        """Refund expired settlement back to sender"""
        current_time = time.time()

        for tx in self.pending_transactions:
            if (tx.get('type') == 'hash_locked_transfer' and
                tx.get('settlement_id') == settlement_id and
                tx.get('lock_time') < current_time and
                tx.get('status') == 'locked'):

                # Create refund transaction
                refund_tx = {
                    "type": "settlement_refund",
                    "original_sender": tx['sender'],
                    "amount": tx['amount'],
                    "settlement_id": settlement_id,
                    "timestamp": time.time(),
                    "signature": f"refund-{settlement_id}"
                }

                self.pending_transactions.append(refund_tx)
                tx['status'] = 'refunded'
                return True

        return False

    # === PiNS (Pi Name System) Methods ===

    def load_name_registry(self):
        """Load name registry from file"""
        if self.names_file.exists():
            try:
                with open(self.names_file, 'r') as f:
                    self.name_registry = json.load(f)
                    print(f"✅ Loaded name registry with {len(self.name_registry)} registered names")
            except Exception as e:
                print(f"❌ Failed to load name registry: {e}")
                self.name_registry = {}

    def save_name_registry(self):
        """Save name registry to file"""
        try:
            # Ensure directory exists
            self.names_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.names_file, 'w') as f:
                json.dump(self.name_registry, f, indent=2)

        except Exception as e:
            print(f"❌ Failed to save name registry: {e}")

    def _rebuild_name_registry(self):
        """Rebuild name registry from blockchain transactions"""
        self.name_registry = {}

        for block in self.chain:
            for tx in block.transactions:
                if tx.get('type') == 'name_registration':
                    name = tx.get('name')
                    wallet_address = tx.get('wallet_address')
                    if name and wallet_address:
                        tx_hash = hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
                        self.name_registry[name] = {
                            'address': wallet_address,
                            'registered_at': tx.get('timestamp', block.timestamp),
                            'tx_hash': tx_hash,
                            'block_index': block.index
                        }

        # Save the rebuilt registry
        self.save_name_registry()

    def _validate_name_registration(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Validate name registration transaction"""
        try:
            # Required fields
            required_fields = ['name', 'wallet_address', 'registration_fee', 'signature']
            for field in required_fields:
                if field not in transaction:
                    return {
                        'valid': False,
                        'error': f'Missing required field: {field}'
                    }

            name = transaction['name']
            wallet_address = transaction['wallet_address']
            registration_fee = transaction['registration_fee']

            # Validate name format
            if not isinstance(name, str) or len(name) < 3 or len(name) > 32:
                return {
                    'valid': False,
                    'error': 'Name must be 3-32 characters long'
                }

            # Name can only contain alphanumeric characters and hyphens
            if not name.replace('-', '').isalnum():
                return {
                    'valid': False,
                    'error': 'Name can only contain letters, numbers, and hyphens'
                }

            # Check if name is already registered
            if name in self.name_registry:
                return {
                    'valid': False,
                    'error': f'Name "{name}" is already registered'
                }

            # Validate registration fee
            if registration_fee != 5.0:  # Fixed fee for now
                return {
                    'valid': False,
                    'error': f'Invalid registration fee: {registration_fee}. Must be 5.0 tokens'
                }

            # Check wallet balance (simplified - should verify the fee can be paid)
            wallet_balance = self._get_wallet_balance(wallet_address)
            if wallet_balance < registration_fee:
                return {
                    'valid': False,
                    'error': f'Insufficient balance for registration fee: {wallet_balance} < {registration_fee}'
                }

            # Reserved names (for system use)
            reserved_names = {'foundation', 'genesis', 'admin', 'system', 'pisecure'}
            if name.lower() in reserved_names:
                return {
                    'valid': False,
                    'error': f'Name "{name}" is reserved for system use'
                }

            return {'valid': True}

        except Exception as e:
            return {
                'valid': False,
                'error': f'Name registration validation error: {e}'
            }

    def register_name(self, name: str, wallet_address: str) -> str:
        """Register a name for a wallet address"""
        # Validate the name registration
        validation_result = self._validate_name_registration({
            'type': 'name_registration',
            'name': name,
            'wallet_address': wallet_address,
            'registration_fee': 5.0,
            'timestamp': time.time(),
            'signature': f'name_registration_{name}_{wallet_address}'
        })

        if not validation_result['valid']:
            raise ValueError(f"Name registration failed: {validation_result['error']}")

        # Create the registration transaction
        transaction = {
            'type': 'name_registration',
            'name': name,
            'wallet_address': wallet_address,
            'registration_fee': 5.0,
            'timestamp': time.time(),
            'signature': f'name_registration_{name}_{wallet_address}'
        }

        # Add to pending transactions
        tx_hash = self.add_transaction(transaction)

        # Update local registry immediately for validation
        self.name_registry[name] = {
            'address': wallet_address,
            'registered_at': time.time(),
            'tx_hash': tx_hash,
            'block_index': None  # Will be set when mined
        }

        return tx_hash

    def resolve_name(self, name: str) -> Optional[str]:
        """Resolve a name to wallet address"""
        if name in self.name_registry:
            return self.name_registry[name]['address']
        return None

    def check_name_availability(self, name: str) -> bool:
        """Check if a name is available for registration"""
        return name not in self.name_registry

    def get_name_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered name"""
        return self.name_registry.get(name)

    def get_registered_names(self) -> List[str]:
        """Get list of all registered names"""
        return list(self.name_registry.keys())

    def _trigger_discovery_on_block(self, block):
        """Trigger network discovery after successful block mining"""
        try:
            from pisecure.core.nat_traversal import node_discovery
            print(f"🔄 Triggering discovery after mining block #{block.index}...")

            # Perform discovery refresh to announce new block
            discovery_results = node_discovery.make_node_discoverable()
            if discovery_results['success_count'] > 0:
                print(f"✅ Mining-triggered discovery successful: {discovery_results['success_count']} methods")
            else:
                print("Mining-triggered discovery found no new endpoints")

        except Exception as e:
            print(f"⚠️ Mining-triggered discovery failed: {e}")

    def get_wallet_names(self, wallet_address: str) -> List[str]:
        """Get all names registered to a wallet address"""
        names = []
        for name, info in self.name_registry.items():
            if info['address'] == wallet_address:
                names.append(name)
        return names