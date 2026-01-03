"""
PiSecure Decentralized Exchange (DEX)
=====================================

Native DEX functionality for 314ST token trading with automated market making,
liquidity pools, and cross-chain interoperability.
"""

import hashlib
import json
import time
import math
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class PiSecureDEX:
    """Decentralized exchange for 314ST token trading"""

    def __init__(self, blockchain=None):
        self.blockchain = blockchain
        self.order_book = OrderBook()
        self.liquidity_pools = {}
        self.cross_chain_bridges = ['Ethereum', 'Bitcoin', 'Solana']
        self.trading_pairs = ['314ST/USDT', '314ST/BTC', '314ST/ETH']

    async def create_liquidity_pool(self, token_a: str, token_b: str,
                                   initial_liquidity_a: float,
                                   initial_liquidity_b: float,
                                   creator: str) -> Dict:
        """Create a new automated market maker liquidity pool"""
        pool_id = f"{token_a}_{token_b}_{int(time.time())}"

        # Calculate initial price and liquidity
        initial_price = initial_liquidity_b / initial_liquidity_a
        total_liquidity = math.sqrt(initial_liquidity_a * initial_liquidity_b)

        pool = {
            'pool_id': pool_id,
            'token_a': token_a,
            'token_b': token_b,
            'reserve_a': initial_liquidity_a,
            'reserve_b': initial_liquidity_b,
            'total_liquidity': total_liquidity,
            'price': initial_price,
            'creator': creator,
            'created_at': time.time(),
            'fee': 0.003,  # 0.3% trading fee
            'active': True
        }

        self.liquidity_pools[pool_id] = pool

        # Create blockchain transaction for pool creation
        pool_tx = {
            "type": "liquidity_pool_created",
            "pool_id": pool_id,
            "token_a": token_a,
            "token_b": token_b,
            "initial_liquidity_a": initial_liquidity_a,
            "initial_liquidity_b": initial_liquidity_b,
            "creator": creator,
            "timestamp": time.time(),
            "signature": f"pool-create-{pool_id}"
        }

        if self.blockchain:
            self.blockchain.pending_transactions.append(pool_tx)

        print(f"🏊 Created liquidity pool: {pool_id} with {total_liquidity:.2f} total liquidity")
        return pool

    async def add_liquidity(self, pool_id: str, amount_a: float, amount_b: float,
                           provider: str) -> bool:
        """Add liquidity to an existing pool"""
        if pool_id not in self.liquidity_pools:
            return False

        pool = self.liquidity_pools[pool_id]

        # Calculate liquidity tokens to mint
        liquidity_minted = min(
            amount_a * pool['total_liquidity'] / pool['reserve_a'],
            amount_b * pool['total_liquidity'] / pool['reserve_b']
        )

        # Update pool reserves
        pool['reserve_a'] += amount_a
        pool['reserve_b'] += amount_b
        pool['total_liquidity'] += liquidity_minted

        # Recalculate price
        pool['price'] = pool['reserve_b'] / pool['reserve_a']

        # Create liquidity provision transaction
        liquidity_tx = {
            "type": "liquidity_added",
            "pool_id": pool_id,
            "provider": provider,
            "amount_a": amount_a,
            "amount_b": amount_b,
            "liquidity_tokens": liquidity_minted,
            "timestamp": time.time(),
            "signature": f"liquidity-add-{pool_id}-{provider}"
        }

        if self.blockchain:
            self.blockchain.pending_transactions.append(liquidity_tx)

        print(f"💧 Added liquidity to {pool_id}: {liquidity_minted:.2f} tokens")
        return True

    async def remove_liquidity(self, pool_id: str, liquidity_amount: float,
                              provider: str) -> Tuple[float, float]:
        """Remove liquidity from a pool"""
        if pool_id not in self.liquidity_pools:
            return 0.0, 0.0

        pool = self.liquidity_pools[pool_id]

        # Calculate token amounts to return
        amount_a = liquidity_amount * pool['reserve_a'] / pool['total_liquidity']
        amount_b = liquidity_amount * pool['reserve_b'] / pool['total_liquidity']

        # Update pool
        pool['reserve_a'] -= amount_a
        pool['reserve_b'] -= amount_b
        pool['total_liquidity'] -= liquidity_amount

        # Create liquidity removal transaction
        remove_tx = {
            "type": "liquidity_removed",
            "pool_id": pool_id,
            "provider": provider,
            "liquidity_amount": liquidity_amount,
            "amount_a_returned": amount_a,
            "amount_b_returned": amount_b,
            "timestamp": time.time(),
            "signature": f"liquidity-remove-{pool_id}-{provider}"
        }

        if self.blockchain:
            self.blockchain.pending_transactions.append(remove_tx)

        print(f"🏊 Removed liquidity from {pool_id}: {amount_a:.2f} A, {amount_b:.2f} B")
        return amount_a, amount_b

    async def swap_tokens(self, pool_id: str, amount_in: float, token_in: str,
                         min_amount_out: float, trader: str) -> Dict:
        """Execute token swap through liquidity pool"""
        if pool_id not in self.liquidity_pools:
            return {'success': False, 'error': 'Pool not found'}

        pool = self.liquidity_pools[pool_id]

        # Determine input/output tokens
        if token_in == pool['token_a']:
            reserve_in = pool['reserve_a']
            reserve_out = pool['reserve_b']
            token_out = pool['token_b']
        else:
            reserve_in = pool['reserve_b']
            reserve_out = pool['reserve_a']
            token_out = pool['token_a']

        # Calculate output amount with AMM formula
        amount_in_with_fee = amount_in * (1 - pool['fee'])
        amount_out = (amount_in_with_fee * reserve_out) / (reserve_in + amount_in_with_fee)

        if amount_out < min_amount_out:
            return {
                'success': False,
                'error': f'Insufficient output amount: {amount_out:.2f} < {min_amount_out:.2f}'
            }

        # Update pool reserves
        if token_in == pool['token_a']:
            pool['reserve_a'] += amount_in
            pool['reserve_b'] -= amount_out
        else:
            pool['reserve_b'] += amount_in
            pool['reserve_a'] -= amount_out

        # Update price
        pool['price'] = pool['reserve_b'] / pool['reserve_a']

        # Create swap transaction
        swap_tx = {
            "type": "token_swap",
            "pool_id": pool_id,
            "trader": trader,
            "token_in": token_in,
            "token_out": token_out,
            "amount_in": amount_in,
            "amount_out": amount_out,
            "fee": amount_in * pool['fee'],
            "price_impact": self._calculate_price_impact(pool, amount_in, reserve_in),
            "timestamp": time.time(),
            "signature": f"swap-{pool_id}-{trader}-{int(time.time())}"
        }

        if self.blockchain:
            self.blockchain.pending_transactions.append(swap_tx)

        print(f"🔄 Token swap: {amount_in:.2f} {token_in} -> {amount_out:.2f} {token_out}")
        return {
            'success': True,
            'amount_out': amount_out,
            'fee': amount_in * pool['fee'],
            'price_impact': swap_tx['price_impact'],
            'transaction': swap_tx
        }

    def _calculate_price_impact(self, pool: Dict, amount_in: float, reserve_in: float) -> float:
        """Calculate price impact of a trade"""
        # Simplified price impact calculation
        return (amount_in / reserve_in) * 100  # Percentage

    async def execute_cross_chain_swap(self, from_chain: str, to_chain: str,
                                     amount: float, user_address: str) -> Dict:
        """Execute atomic cross-chain swap"""
        if from_chain not in self.cross_chain_bridges or to_chain not in self.cross_chain_bridges:
            return {'success': False, 'error': 'Unsupported chain'}

        # Generate unique swap ID
        swap_id = f"cross_chain_{int(time.time())}_{hashlib.sha256(user_address.encode()).hexdigest()[:8]}"

        # Create bridge transaction
        bridge_tx = {
            "type": "cross_chain_bridge",
            "swap_id": swap_id,
            "from_chain": from_chain,
            "to_chain": to_chain,
            "amount": amount,
            "user_address": user_address,
            "status": "initiating",
            "timestamp": time.time(),
            "signature": f"bridge-{swap_id}"
        }

        # Simulate bridge execution (in production, this would interact with actual bridges)
        settlement_tx = {
            "type": "cross_chain_settlement",
            "swap_id": swap_id,
            "recipient": user_address,
            "amount": amount * 0.995,  # 0.5% bridge fee
            "status": "completed",
            "timestamp": time.time() + 30,  # Assume 30 second settlement
            "signature": f"settlement-{swap_id}"
        }

        if self.blockchain:
            self.blockchain.pending_transactions.extend([bridge_tx, settlement_tx])

        print(f"🌉 Cross-chain swap initiated: {amount:.2f} from {from_chain} to {to_chain}")
        return {
            'success': True,
            'swap_id': swap_id,
            'estimated_settlement': 30,  # seconds
            'fee': amount * 0.005,
            'final_amount': amount * 0.995,
            'transactions': [bridge_tx, settlement_tx]
        }

    def get_pool_stats(self, pool_id: str) -> Dict:
        """Get statistics for a liquidity pool"""
        if pool_id not in self.liquidity_pools:
            return {}

        pool = self.liquidity_pools[pool_id]
        return {
            'pool_id': pool_id,
            'token_pair': f"{pool['token_a']}/{pool['token_b']}",
            'current_price': pool['price'],
            'reserve_a': pool['reserve_a'],
            'reserve_b': pool['reserve_b'],
            'total_liquidity': pool['total_liquidity'],
            'trading_fee': pool['fee'] * 100,  # as percentage
            '24h_volume': self._calculate_24h_volume(pool_id),
            'active': pool['active']
        }

    def _calculate_24h_volume(self, pool_id: str) -> float:
        """Calculate 24-hour trading volume for a pool"""
        if not self.blockchain:
            return 0.0

        volume = 0.0
        cutoff_time = time.time() - 86400  # 24 hours ago

        for block in reversed(self.blockchain.chain):
            if block.timestamp < cutoff_time:
                break

            for tx in block.transactions:
                if (tx.get('type') == 'token_swap' and
                    tx.get('pool_id') == pool_id and
                    tx.get('timestamp', 0) > cutoff_time):
                    volume += tx.get('amount_in', 0)

        return volume

    def get_market_overview(self) -> Dict:
        """Get overview of all trading pairs and market statistics"""
        overview = {
            'total_pools': len(self.liquidity_pools),
            'total_liquidity': 0.0,
            '24h_volume': 0.0,
            'trading_pairs': {},
            'top_pools': []
        }

        for pool_id, pool in self.liquidity_pools.items():
            if not pool['active']:
                continue

            pair = f"{pool['token_a']}/{pool['token_b']}"
            volume = self._calculate_24h_volume(pool_id)

            overview['total_liquidity'] += pool['total_liquidity']
            overview['24h_volume'] += volume

            overview['trading_pairs'][pair] = {
                'price': pool['price'],
                'liquidity': pool['total_liquidity'],
                'volume_24h': volume,
                'fee': pool['fee'] * 100
            }

        # Sort pools by liquidity for top pools
        sorted_pools = sorted(
            [(pid, p) for pid, p in self.liquidity_pools.items() if p['active']],
            key=lambda x: x[1]['total_liquidity'],
            reverse=True
        )
        overview['top_pools'] = [pid for pid, _ in sorted_pools[:5]]

        return overview


class OrderBook:
    """Centralized order book for limit orders (complements AMM pools)"""

    def __init__(self):
        self.buy_orders = {}  # price -> list of orders
        self.sell_orders = {}  # price -> list of orders
        self.order_counter = 0

    def place_buy_order(self, user_id: str, price: float, amount: float) -> str:
        """Place a buy limit order"""
        order_id = f"buy_{self.order_counter}"
        self.order_counter += 1

        order = {
            'id': order_id,
            'user_id': user_id,
            'type': 'buy',
            'price': price,
            'amount': amount,
            'remaining': amount,
            'status': 'open',
            'timestamp': time.time()
        }

        if price not in self.buy_orders:
            self.buy_orders[price] = []
        self.buy_orders[price].append(order)

        # Sort buy orders by price (highest first)
        self.buy_orders[price].sort(key=lambda x: x['timestamp'])

        return order_id

    def place_sell_order(self, user_id: str, price: float, amount: float) -> str:
        """Place a sell limit order"""
        order_id = f"sell_{self.order_counter}"
        self.order_counter += 1

        order = {
            'id': order_id,
            'user_id': user_id,
            'type': 'sell',
            'price': price,
            'amount': amount,
            'remaining': amount,
            'status': 'open',
            'timestamp': time.time()
        }

        if price not in self.sell_orders:
            self.sell_orders[price] = []
        self.sell_orders[price].append(order)

        # Sort sell orders by price (lowest first)
        self.sell_orders[price].sort(key=lambda x: x['timestamp'])

        return order_id

    def match_orders(self) -> List[Dict]:
        """Match buy and sell orders"""
        matches = []

        # Get sorted price levels
        buy_prices = sorted(self.buy_orders.keys(), reverse=True)  # Highest first
        sell_prices = sorted(self.sell_orders.keys())  # Lowest first

        for buy_price in buy_prices:
            for sell_price in sell_prices:
                if buy_price >= sell_price:
                    match = self._execute_match(buy_price, sell_price)
                    if match:
                        matches.append(match)
                    else:
                        break  # No more matches at this price level

        return matches

    def _execute_match(self, buy_price: float, sell_price: float) -> Optional[Dict]:
        """Execute a match between buy and sell orders"""
        buy_orders = self.buy_orders.get(buy_price, [])
        sell_orders = self.sell_orders.get(sell_price, [])

        if not buy_orders or not sell_orders:
            return None

        buy_order = buy_orders[0]
        sell_order = sell_orders[0]

        match_amount = min(buy_order['remaining'], sell_order['remaining'])
        match_price = sell_price  # Price priority to seller

        # Update remaining amounts
        buy_order['remaining'] -= match_amount
        sell_order['remaining'] -= match_amount

        # Remove filled orders
        if buy_order['remaining'] == 0:
            buy_orders.pop(0)
            if not buy_orders:
                del self.buy_orders[buy_price]

        if sell_order['remaining'] == 0:
            sell_orders.pop(0)
            if not sell_orders:
                del self.sell_orders[sell_price]

        return {
            'buy_order_id': buy_order['id'],
            'sell_order_id': sell_order['id'],
            'buyer': buy_order['user_id'],
            'seller': sell_order['user_id'],
            'amount': match_amount,
            'price': match_price,
            'timestamp': time.time()
        }

    def get_order_book(self, depth: int = 10) -> Dict:
        """Get current order book state"""
        buy_prices = sorted(self.buy_orders.keys(), reverse=True)[:depth]
        sell_prices = sorted(self.sell_orders.keys())[:depth]

        return {
            'bids': [
                {
                    'price': price,
                    'total_volume': sum(order['remaining'] for order in self.buy_orders[price])
                }
                for price in buy_prices
            ],
            'asks': [
                {
                    'price': price,
                    'total_volume': sum(order['remaining'] for order in self.sell_orders[price])
                }
                for price in sell_prices
            ]
        }