"""
UTXO (Unspent Transaction Output) Tracking
===========================================

Lightweight balance tracking for Mac clients and efficient balance calculation.
Allows clients to validate balances without scanning entire blockchain.
"""

import json
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path


class UTXOSet:
    """Unspent Transaction Output set for efficient balance tracking
    
    Maintains a set of unspent outputs per address, enabling O(1) balance lookups
    instead of O(n) blockchain scans. Syncs from Pi5 nodes.
    """
    
    def __init__(self, utxo_file: str = "~/.pisecure/utxo_set.json"):
        self.utxo_file = Path(utxo_file).expanduser()
        self.utxo_file.parent.mkdir(parents=True, exist_ok=True)
        self.utxos: Dict[str, List[Dict[str, Any]]] = self._load_utxo_set()
    
    def _load_utxo_set(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load UTXO set from file"""
        if self.utxo_file.exists():
            try:
                with open(self.utxo_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_utxo_set(self):
        """Save UTXO set to file"""
        with open(self.utxo_file, 'w') as f:
            json.dump(self.utxos, f, indent=2)
    
    def add_output(self, address: str, tx_hash: str, tx_index: int, 
                   amount: float, block_height: int):
        """Add an unspent output for an address
        
        Args:
            address: Recipient address
            tx_hash: Transaction hash
            tx_index: Output index in transaction
            amount: Output amount
            block_height: Block containing transaction
        """
        if address not in self.utxos:
            self.utxos[address] = []
        
        self.utxos[address].append({
            'tx_hash': tx_hash,
            'tx_index': tx_index,
            'amount': amount,
            'block_height': block_height
        })
        self._save_utxo_set()
    
    def spend_output(self, address: str, tx_hash: str, tx_index: int):
        """Remove a spent output
        
        Args:
            address: Address spending the output
            tx_hash: Transaction hash of the spent output
            tx_index: Output index of the spent output
        """
        if address in self.utxos:
            self.utxos[address] = [
                utxo for utxo in self.utxos[address]
                if not (utxo['tx_hash'] == tx_hash and utxo['tx_index'] == tx_index)
            ]
            self._save_utxo_set()
    
    def get_balance(self, address: str) -> float:
        """Calculate balance from unspent outputs - O(1) operation
        
        Args:
            address: Address to check
            
        Returns:
            Total balance from unspent outputs
        """
        if address not in self.utxos:
            return 0.0
        return sum(utxo['amount'] for utxo in self.utxos[address])
    
    def get_unspent_outputs(self, address: str) -> List[Dict[str, Any]]:
        """Get all unspent outputs for an address
        
        Args:
            address: Address to query
            
        Returns:
            List of unspent transaction outputs
        """
        return self.utxos.get(address, [])
    
    def sync_from_blockchain(self, blockchain):
        """Sync UTXO set from blockchain (Pi5 → Mac)
        
        This reconstructs the UTXO set by replaying all transactions in the blockchain.
        Should be called after syncing blocks from a peer.
        
        Args:
            blockchain: SignChain instance to sync from
        """
        self.utxos = {}
        
        try:
            for block_height, block in enumerate(blockchain.chain):
                for tx_index, tx in enumerate(block.transactions):
                    tx_hash = self._calculate_transaction_hash(tx)
                    
                    # Add outputs (receipts)
                    if tx.get('type') == 'token_transfer':
                        recipient = tx.get('recipient_address')
                        amount = tx.get('amount')
                        if recipient and amount:
                            self.add_output(recipient, tx_hash, 0, amount, block_height)
                        
                        # Remove sender's previous UTXO
                        sender = tx.get('sender_address')
                        if sender and 'previous_tx_hash' in tx:
                            self.spend_output(sender, tx['previous_tx_hash'], 0)
                    
                    elif tx.get('type') == 'batch_transfer':
                        sender = tx.get('sender_address')
                        transfers = tx.get('transfers', [])
                        
                        # Add all recipient outputs
                        for transfer_idx, transfer in enumerate(transfers):
                            recipient = transfer.get('recipient')
                            amount = transfer.get('amount')
                            if recipient and amount:
                                self.add_output(recipient, tx_hash, transfer_idx, amount, block_height)
                        
                        # Mark sender outputs as spent
                        if sender and 'previous_tx_hash' in tx:
                            self.spend_output(sender, tx['previous_tx_hash'], 0)
                    
                    elif tx.get('type') == 'mining_reward':
                        miner = tx.get('miner_address')
                        reward = tx.get('reward', 50.0)
                        if miner and reward:
                            self.add_output(miner, tx_hash, 0, reward, block_height)
            
            self._save_utxo_set()
            
        except Exception as e:
            print(f"[DEBUG] UTXO sync failed: {e}")
    
    @staticmethod
    def _calculate_transaction_hash(transaction: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of a transaction
        
        Args:
            transaction: Transaction data
            
        Returns:
            Hex-encoded transaction hash
        """
        tx_copy = transaction.copy()
        tx_copy.pop('signature', None)
        tx_string = json.dumps(tx_copy, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def clear(self):
        """Clear all UTXO data"""
        self.utxos = {}
        self._save_utxo_set()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get UTXO set statistics
        
        Returns:
            Statistics dictionary
        """
        total_outputs = sum(len(outputs) for outputs in self.utxos.values())
        total_balance = sum(self.get_balance(addr) for addr in self.utxos.keys())
        
        return {
            'addresses': len(self.utxos),
            'total_outputs': total_outputs,
            'total_balance': total_balance,
            'utxo_file': str(self.utxo_file)
        }
