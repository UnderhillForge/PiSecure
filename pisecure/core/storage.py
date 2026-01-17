"""
PiSecure Scalable Storage System
=================================

Hybrid storage implementation combining:
- Block files for raw blockchain data
- SQLite database for indexing and UTXO set
- In-memory caches for performance

Inspired by Bitcoin Core's storage architecture.
"""

import sqlite3
import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Iterator
import struct
import os


class BlockFileStorage:
    """Handles raw block data storage in binary files"""

    def __init__(self, data_dir: str = "/var/lib/pisecure"):
        self.data_dir = Path(data_dir)
        self.blocks_dir = self.data_dir / "blocks"
        self.blocks_dir.mkdir(parents=True, exist_ok=True)

        # Block file configuration
        self.blocks_per_file = 1000  # Blocks per .blk file
        self.magic_bytes = b'\xf9\xbe\xb4\xd9'  # PiSecure block magic

    def save_block(self, block_data: Dict[str, Any]) -> Tuple[str, int]:
        """Save block to appropriate file, return (filename, offset)"""
        block_index = block_data['index']

        # Determine which file this block belongs to
        file_index = block_index // self.blocks_per_file
        filename = f"blk{file_index:05d}.dat"
        filepath = self.blocks_dir / filename

        # Serialize block to binary format
        block_bytes = self._serialize_block(block_data)

        # Append to file and get offset
        with open(filepath, 'ab') as f:
            offset = f.tell()
            f.write(self.magic_bytes)
            f.write(struct.pack('<I', len(block_bytes)))  # Block size
            f.write(block_bytes)

        return str(filename), offset

    def load_block(self, filename: str, offset: int) -> Optional[Dict[str, Any]]:
        """Load block from file at specific offset"""
        filepath = self.blocks_dir / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath, 'rb') as f:
                f.seek(offset)

                # Read magic bytes
                magic = f.read(4)
                if magic != self.magic_bytes:
                    return None

                # Read block size
                size_bytes = f.read(4)
                if len(size_bytes) != 4:
                    return None
                block_size = struct.unpack('<I', size_bytes)[0]

                # Read block data
                block_bytes = f.read(block_size)
                if len(block_bytes) != block_size:
                    return None

                return self._deserialize_block(block_bytes)

        except (OSError, struct.error):
            return None

    def _serialize_block(self, block_data: Dict[str, Any]) -> bytes:
        """Serialize block to binary format"""
        # Convert to JSON then encode
        json_str = json.dumps(block_data, sort_keys=True, separators=(',', ':'))
        return json_str.encode('utf-8')

    def _deserialize_block(self, block_bytes: bytes) -> Dict[str, Any]:
        """Deserialize block from binary format"""
        json_str = block_bytes.decode('utf-8')
        return json.loads(json_str)


class SQLiteIndex:
    """SQLite database for blockchain indexing and UTXO set"""

    def __init__(self, db_path: str = "/var/lib/pisecure/pisecure.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local connections for SQLite
        self._local = threading.local()

        # Initialize database
        self._init_db()

    @property
    def conn(self):
        """Get thread-local database connection"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        return self._local.conn

    def _init_db(self):
        """Initialize database schema"""
        with self.conn as conn:
            # Blocks table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS blocks (
                    hash TEXT PRIMARY KEY,
                    height INTEGER UNIQUE,
                    previous_hash TEXT,
                    timestamp REAL,
                    nonce INTEGER,
                    difficulty INTEGER,
                    tx_count INTEGER,
                    file_name TEXT,
                    file_offset INTEGER,
                    size INTEGER,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            ''')

            # Transactions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    hash TEXT PRIMARY KEY,
                    block_hash TEXT,
                    block_height INTEGER,
                    tx_index INTEGER,
                    timestamp REAL,
                    size INTEGER,
                    sender_address TEXT,
                    recipient_address TEXT,
                    amount REAL,
                    tx_type TEXT,
                    FOREIGN KEY (block_hash) REFERENCES blocks(hash)
                )
            ''')

            # UTXO set table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS utxo (
                    tx_hash TEXT,
                    output_index INTEGER,
                    amount REAL,
                    script TEXT,
                    block_height INTEGER,
                    address TEXT,
                    PRIMARY KEY (tx_hash, output_index)
                )
            ''')

            # Create indexes for performance (with error handling)
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_blocks_height ON blocks(height)',
                'CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON blocks(timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_transactions_block ON transactions(block_hash)',
                'CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender_address)',
                'CREATE INDEX IF NOT EXISTS idx_transactions_recipient ON transactions(recipient_address)',
                'CREATE INDEX IF NOT EXISTS idx_utxo_address ON utxo(address)',
                'CREATE INDEX IF NOT EXISTS idx_utxo_tx_hash ON utxo(tx_hash)'
            ]

            for index_sql in indexes:
                try:
                    conn.execute(index_sql)
                except sqlite3.Error as e:
                    print(f"Warning: Failed to create index: {e}")
                    # Try to drop and recreate if index is corrupted
                    try:
                        # Extract index name from SQL
                        index_name = index_sql.split('idx_')[1].split(' ')[0]
                        conn.execute(f'DROP INDEX IF EXISTS idx_{index_name}')
                        conn.execute(index_sql)
                        print(f"Recreated index: idx_{index_name}")
                    except sqlite3.Error as recreate_e:
                        print(f"Failed to recreate index idx_{index_name}: {recreate_e}")

    def add_block(self, block_data: Dict[str, Any], file_name: str, file_offset: int, size: int):
        """Add block to index"""
        block_hash = block_data['hash']
        height = block_data['index']

        with self.conn as conn:
            conn.execute('''
                INSERT OR REPLACE INTO blocks
                (hash, height, previous_hash, timestamp, nonce, difficulty, tx_count,
                 file_name, file_offset, size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                block_hash, height, block_data['previous_hash'],
                block_data['timestamp'], block_data['nonce'],
                4,  # difficulty (hardcoded for now)
                len(block_data['transactions']),
                file_name, file_offset, size
            ))

            # Add transactions
            for i, tx in enumerate(block_data['transactions']):
                tx_hash = hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
                conn.execute('''
                    INSERT OR REPLACE INTO transactions
                    (hash, block_hash, block_height, tx_index, timestamp, size,
                     sender_address, recipient_address, amount, tx_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (tx_hash, block_hash, height, i, tx.get('timestamp', 0), len(str(tx)),
                      tx.get('sender_address'), tx.get('recipient_address'),
                      tx.get('amount', 0), tx.get('type')))

                # Update UTXO set
                self._update_utxo_for_transaction(tx, height)

    def get_block_location(self, block_hash: str) -> Optional[Tuple[str, int]]:
        """Get file location for block"""
        with self.conn as conn:
            result = conn.execute(
                'SELECT file_name, file_offset FROM blocks WHERE hash = ?',
                (block_hash,)
            ).fetchone()

            return (result[0], result[1]) if result else None

    def get_block_height(self, block_hash: str) -> Optional[int]:
        """Get block height by hash"""
        with self.conn as conn:
            result = conn.execute(
                'SELECT height FROM blocks WHERE hash = ?',
                (block_hash,)
            ).fetchone()

            return result[0] if result else None

    def get_latest_block_height(self) -> int:
        """Get height of latest block"""
        with self.conn as conn:
            result = conn.execute(
                'SELECT MAX(height) FROM blocks'
            ).fetchone()

            return result[0] if result and result[0] is not None else -1

    def get_block_hash(self, height: int) -> Optional[str]:
        """Get block hash by height"""
        with self.conn as conn:
            result = conn.execute(
                'SELECT hash FROM blocks WHERE height = ?',
                (height,)
            ).fetchone()

            return result[0] if result else None

    def get_wallet_transactions(self, wallet_address: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transactions for a wallet address"""
        with self.conn as conn:
            result = conn.execute('''
                SELECT hash, block_height, timestamp, sender_address, recipient_address,
                       amount, tx_type
                FROM transactions
                WHERE sender_address = ? OR recipient_address = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (wallet_address, wallet_address, limit)).fetchall()

            transactions = []
            for row in result:
                tx_hash, block_height, timestamp, sender, recipient, amount, tx_type = row
                transactions.append({
                    'tx_hash': tx_hash,
                    'block_index': block_height,
                    'timestamp': timestamp,
                    'type': tx_type,
                    'amount': amount,
                    'direction': 'incoming' if recipient == wallet_address else 'outgoing',
                    'sender': sender,
                    'recipient': recipient
                })

            return transactions

    def _update_utxo_for_transaction(self, tx: Dict[str, Any], block_height: int):
        """Update UTXO set for a transaction"""
        # This is a simplified implementation
        # In production, you'd need proper transaction parsing

        tx_type = tx.get('type')

        if tx_type == 'token_transfer':
            # Remove spent inputs (simplified)
            # sender = tx.get('sender_address')
            # amount = tx.get('amount')

            # Add new outputs
            recipient = tx.get('recipient_address')
            amount = tx.get('amount', 0)

            if recipient and amount > 0:
                # Generate a fake tx hash for this output
                tx_hash = hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
                with self.conn as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO utxo
                        (tx_hash, output_index, amount, script, block_height, address)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (tx_hash, 0, amount, '', block_height, recipient))

        elif tx_type == 'mining_reward':
            # Mining rewards create new coins for the miner
            recipient = tx.get('recipient_address')
            amount = tx.get('amount', 0)

            if recipient and amount > 0:
                # Generate a unique tx hash for the mining reward
                tx_hash = hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
                with self.conn as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO utxo
                        (tx_hash, output_index, amount, script, block_height, address)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (tx_hash, 0, amount, 'mining_reward', block_height, recipient))

    def get_wallet_balance(self, address: str) -> float:
        """Get wallet balance by summing UTXO for address"""
        try:
            with self.conn as conn:
                result = conn.execute('''
                    SELECT COALESCE(SUM(amount), 0) as balance
                    FROM utxo
                    WHERE address = ?
                ''', (address,)).fetchone()

                return float(result[0]) if result else 0.0
        except sqlite3.Error as e:
            print(f"SQLite error getting wallet balance for {address}: {e}")
            # Try to reinitialize the database if there are index issues
            try:
                self._init_db()
                # Retry the query
                with self.conn as conn:
                    result = conn.execute('''
                        SELECT COALESCE(SUM(amount), 0) as balance
                        FROM utxo
                        WHERE address = ?
                    ''', (address,)).fetchone()
                    return float(result[0]) if result else 0.0
            except sqlite3.Error as retry_e:
                print(f"Failed to retry wallet balance query: {retry_e}")
                return 0.0


class MemoryCache:
    """In-memory cache for frequently accessed data"""

    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}

    def get(self, key: str) -> Any:
        """Get item from cache"""
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None

    def put(self, key: str, value: Any):
        """Put item in cache"""
        if len(self.cache) >= self.max_size:
            # Remove least recently used
            lru_key = min(self.access_times, key=self.access_times.get)
            del self.cache[lru_key]
            del self.access_times[lru_key]

        self.cache[key] = value
        self.access_times[key] = time.time()


class HybridBlockchainStorage:
    """Main hybrid storage coordinator"""

    def __init__(self, data_dir: str = None):
        # Determine data directory with fallback for permission issues
        if data_dir is None:
            # Try system directory first, fall back to user directory
            system_dir = Path("/var/lib/pisecure")
            user_dir = Path.home() / ".pisecure"

            # Try system directory, fall back to user directory if no permission
            try:
                system_dir.mkdir(parents=True, exist_ok=True)
                # Test write permission by creating a test file
                test_file = system_dir / ".write_test"
                test_file.touch()
                test_file.unlink()
                self.data_dir = system_dir
            except (OSError, PermissionError):
                # Fall back to user directory
                user_dir.mkdir(parents=True, exist_ok=True)
                self.data_dir = user_dir
                print(f"⚠️ Using user directory for storage: {self.data_dir}")
        else:
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize storage components
        self.block_storage = BlockFileStorage(str(self.data_dir))
        self.index_db = SQLiteIndex(str(self.data_dir / "pisecure.db"))
        self.cache = MemoryCache(max_size=500)

        # Migration flag
        self.migrated = self._check_migration_status()

    def _check_migration_status(self) -> bool:
        """Check if migration from JSON to hybrid storage is complete"""
        migration_file = self.data_dir / ".migration_complete"
        return migration_file.exists()

    def migrate_from_json(self, json_file: str = "/var/lib/pisecure/blockchain.json"):
        """Migrate existing JSON blockchain to hybrid storage"""
        json_path = Path(json_file)

        if not json_path.exists():
            print("No JSON blockchain file found, starting fresh")
            self._mark_migration_complete()
            return

        if self.migrated:
            print("Migration already completed")
            return

        print("Migrating blockchain from JSON to hybrid storage...")

        try:
            with open(json_path, 'r') as f:
                chain_data = json.load(f)

            for block_data in chain_data:
                # Save to block files
                filename, offset = self.block_storage.save_block(block_data)

                # Calculate size (approximate)
                block_bytes = self.block_storage._serialize_block(block_data)
                size = len(self.block_storage.magic_bytes) + 4 + len(block_bytes)

                # Add to index
                self.index_db.add_block(block_data, filename, offset, size)

            self._mark_migration_complete()
            print(f"✅ Migrated {len(chain_data)} blocks to hybrid storage")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

    def _mark_migration_complete(self):
        """Mark migration as complete"""
        migration_file = self.data_dir / ".migration_complete"
        migration_file.touch()

    def save_block(self, block_data: Dict[str, Any]):
        """Save block using hybrid storage"""
        # Save to block files
        filename, offset = self.block_storage.save_block(block_data)

        # Calculate size
        block_bytes = self.block_storage._serialize_block(block_data)
        size = len(self.block_storage.magic_bytes) + 4 + len(block_bytes)

        # Add to index
        self.index_db.add_block(block_data, filename, offset, size)

        # Cache the block location
        block_hash = block_data['hash']
        self.cache.put(f"block_location_{block_hash}", (filename, offset))

    def load_block(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Load block from hybrid storage"""
        # Check cache first
        cached_location = self.cache.get(f"block_location_{block_hash}")
        if cached_location:
            filename, offset = cached_location
        else:
            # Get location from database
            location = self.index_db.get_block_location(block_hash)
            if not location:
                return None
            filename, offset = location

            # Cache for future use
            self.cache.put(f"block_location_{block_hash}", (filename, offset))

        # Load from file
        return self.block_storage.load_block(filename, offset)

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        latest_height = self.index_db.get_latest_block_height()

        return {
            "blocks": latest_height + 1,
            "latest_block_height": latest_height,
            "storage_type": "hybrid",
            "data_directory": str(self.data_dir)
        }

    def get_wallet_balance(self, address: str) -> float:
        """Get wallet balance"""
        return self.index_db.get_wallet_balance(address)

    def get_wallet_transactions(self, wallet_address: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get wallet transactions"""
        return self.index_db.get_wallet_transactions(wallet_address, limit)

    def close(self):
        """Close all storage connections"""
        # SQLite connections will close automatically
        pass