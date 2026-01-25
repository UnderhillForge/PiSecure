"""
PiSecure Market Data & Analytics Engine
======================================

Real-time market data and advanced analytics for cryptocurrency exchanges
integrating 314ST token trading.
"""

import hashlib
import json
import time
import statistics
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
from pathlib import Path


class MarketDataEngine:
    """Real-time market data and analytics for 314ST trading"""

    def __init__(self, blockchain=None):
        self.blockchain = blockchain
        self.price_feeds = {}
        self.analytics = AnalyticsEngine()
        self.real_time_data = RealTimeDataStream()

        # Market data storage
        self.price_history = deque(maxlen=10000)  # Last 10k price points
        self.volume_history = deque(maxlen=10000)
        self.order_book_snapshots = deque(maxlen=1000)

        # Trading pairs
        self.trading_pairs = ['314ST/USDT', '314ST/BTC', '314ST/ETH', '314ST/USDC']

    async def initialize_market_data(self):
        """Initialize market data feeds and analytics"""
        # Connect to multiple price oracles
        oracles = ['CoinGecko', 'CoinMarketCap', 'Kaiko', 'CryptoCompare']

        for oracle in oracles:
            feed = await self.connect_oracle(oracle)
            self.price_feeds[oracle] = feed

            # Set up real-time price streaming
            feed.on_price_update(self._handle_price_update)
            feed.on_trade(self._handle_trade_update)

        print("📊 Initialized market data feeds from multiple oracles")

    async def connect_oracle(self, oracle_name: str) -> 'PriceFeed':
        """Connect to a price oracle (simulated)"""
        # In production, this would connect to real APIs
        feed = PriceFeed(oracle_name)
        await feed.connect()
        return feed

    async def _handle_price_update(self, oracle: str, price_data: Dict):
        """Handle real-time price updates"""
        # Store price data
        self.price_history.append({
            'timestamp': time.time(),
            'oracle': oracle,
            'price': price_data['price'],
            'volume': price_data.get('volume', 0),
            'pair': price_data.get('pair', '314ST/USDT')
        })

        # Update analytics
        await self.analytics.update_price_metrics(price_data)

        # Broadcast to real-time stream
        await self.real_time_data.broadcast_price_update(price_data)

    async def _handle_trade_update(self, oracle: str, trade_data: Dict):
        """Handle real-time trade updates"""
        # Store volume data
        self.volume_history.append({
            'timestamp': time.time(),
            'oracle': oracle,
            'amount': trade_data['amount'],
            'price': trade_data['price'],
            'side': trade_data['side'],  # 'buy' or 'sell'
            'pair': trade_data.get('pair', '314ST/USDT')
        })

        # Update analytics
        await self.analytics.update_volume_metrics(trade_data)

    def get_real_time_price(self, pair: str = '314ST/USDT') -> Dict:
        """Get current real-time price for a trading pair"""
        if not self.price_history:
            return {'price': 0.0, 'timestamp': time.time(), 'sources': 0}

        # Get latest prices from all oracles
        recent_prices = {}
        cutoff_time = time.time() - 300  # Last 5 minutes

        for price_point in reversed(self.price_history):
            if price_point['timestamp'] < cutoff_time:
                break
            if price_point['pair'] == pair:
                oracle = price_point['oracle']
                if oracle not in recent_prices:
                    recent_prices[oracle] = price_point['price']

        if not recent_prices:
            return {'price': 0.0, 'timestamp': time.time(), 'sources': 0}

        # Calculate aggregate price
        prices = list(recent_prices.values())
        avg_price = statistics.mean(prices)

        return {
            'price': avg_price,
            'high': max(prices),
            'low': min(prices),
            'sources': len(prices),
            'timestamp': time.time(),
            'pair': pair
        }

    def get_price_history(self, pair: str = '314ST/USDT', hours: int = 24) -> List[Dict]:
        """Get historical price data"""
        cutoff_time = time.time() - (hours * 3600)
        history = []

        for price_point in self.price_history:
            if price_point['timestamp'] >= cutoff_time and price_point['pair'] == pair:
                history.append(price_point)

        return history

    def get_volume_metrics(self, pair: str = '314ST/USDT', hours: int = 24) -> Dict:
        """Get volume metrics for a trading pair"""
        cutoff_time = time.time() - (hours * 3600)
        volume_data = []

        for volume_point in self.volume_history:
            if volume_point['timestamp'] >= cutoff_time and volume_point['pair'] == pair:
                volume_data.append(volume_point)

        if not volume_data:
            return {'total_volume': 0, 'buy_volume': 0, 'sell_volume': 0}

        total_volume = sum(v['amount'] for v in volume_data)
        buy_volume = sum(v['amount'] for v in volume_data if v['side'] == 'buy')
        sell_volume = sum(v['amount'] for v in volume_data if v['side'] == 'sell')

        return {
            'total_volume': total_volume,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'trade_count': len(volume_data),
            'avg_trade_size': total_volume / len(volume_data) if volume_data else 0
        }

    async def get_real_time_analytics(self) -> Dict:
        """Get comprehensive real-time market analytics"""
        analytics = await self.analytics.get_comprehensive_analytics()

        # Add market-specific metrics
        current_time = time.time()

        analytics.update({
            'price_volatility': self._calculate_volatility(hours=1),
            'trading_volume_24h': self.get_volume_metrics(hours=24)['total_volume'],
            'market_depth': await self._calculate_market_depth(),
            'whale_movements': await self._detect_whale_movements(),
            'sentiment_analysis': await self._get_market_sentiment(),
            'correlation_matrix': self._calculate_asset_correlations(),
            'liquidity_score': await self._calculate_liquidity_score(),
            'market_efficiency': self._calculate_market_efficiency(),
            'timestamp': current_time
        })

        return analytics

    def _calculate_volatility(self, hours: int = 1) -> float:
        """Calculate price volatility"""
        prices = []
        cutoff_time = time.time() - (hours * 3600)

        for price_point in self.price_history:
            if price_point['timestamp'] >= cutoff_time:
                prices.append(price_point['price'])

        if len(prices) < 2:
            return 0.0

        # Calculate standard deviation of returns
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)

        if not returns:
            return 0.0

        return statistics.stdev(returns) * 100  # As percentage

    async def _calculate_market_depth(self) -> Dict:
        """Calculate market depth across all trading pairs"""
        depth = {}

        for pair in self.trading_pairs:
            # Get order book snapshot (simplified)
            order_book = await self._get_order_book_snapshot(pair)

            depth[pair] = {
                'bid_depth': sum(order['volume'] for order in order_book.get('bids', [])),
                'ask_depth': sum(order['volume'] for order in order_book.get('asks', [])),
                'spread': self._calculate_spread(order_book),
                'levels': len(order_book.get('bids', [])) + len(order_book.get('asks', []))
            }

        return depth

    async def _get_order_book_snapshot(self, pair: str) -> Dict:
        """Get current order book snapshot (simplified)"""
        # In production, this would query actual order books
        return {
            'bids': [
                {'price': 1.05, 'volume': 1000},
                {'price': 1.04, 'volume': 2000},
                {'price': 1.03, 'volume': 1500}
            ],
            'asks': [
                {'price': 1.06, 'volume': 1200},
                {'price': 1.07, 'volume': 1800},
                {'price': 1.08, 'volume': 900}
            ]
        }

    def _calculate_spread(self, order_book: Dict) -> float:
        """Calculate bid-ask spread"""
        if not order_book.get('bids') or not order_book.get('asks'):
            return 0.0

        best_bid = max(bid['price'] for bid in order_book['bids'])
        best_ask = min(ask['price'] for ask in order_book['asks'])

        return ((best_ask - best_bid) / best_bid) * 100  # As percentage

    async def _detect_whale_movements(self) -> List[Dict]:
        """Detect large trades (whale movements)"""
        whale_threshold = 10000  # 10k 314ST
        recent_whales = []

        cutoff_time = time.time() - 3600  # Last hour

        for trade in reversed(list(self.volume_history)):
            if trade['timestamp'] < cutoff_time:
                break

            if trade['amount'] >= whale_threshold:
                recent_whales.append({
                    'timestamp': trade['timestamp'],
                    'amount': trade['amount'],
                    'price': trade['price'],
                    'side': trade['side'],
                    'oracle': trade['oracle']
                })

        return recent_whales[:10]  # Top 10 recent whales

    async def _get_market_sentiment(self) -> Dict:
        """Calculate market sentiment indicators"""
        # Simplified sentiment analysis
        recent_trades = list(self.volume_history)[-100:]  # Last 100 trades

        if not recent_trades:
            return {'sentiment': 'neutral', 'score': 0.0}

        buy_volume = sum(t['amount'] for t in recent_trades if t['side'] == 'buy')
        sell_volume = sum(t['amount'] for t in recent_trades if t['side'] == 'sell')
        total_volume = buy_volume + sell_volume

        if total_volume == 0:
            return {'sentiment': 'neutral', 'score': 0.0}

        # Sentiment score: positive = bullish, negative = bearish
        sentiment_score = (buy_volume - sell_volume) / total_volume

        if sentiment_score > 0.2:
            sentiment = 'bullish'
        elif sentiment_score < -0.2:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'

        return {
            'sentiment': sentiment,
            'score': sentiment_score,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume
        }

    def _calculate_asset_correlations(self) -> Dict:
        """Calculate correlation matrix between 314ST and other assets"""
        # Simplified correlation calculation
        correlations = {}

        for pair in self.trading_pairs:
            if pair == '314ST/USDT':
                continue

            # Calculate correlation with 314ST/USDT
            corr = self._calculate_pair_correlation('314ST/USDT', pair)
            correlations[pair] = corr

        return correlations

    def _calculate_pair_correlation(self, pair1: str, pair2: str) -> float:
        """Calculate correlation between two trading pairs"""
        # Simplified - in production would use proper statistical correlation
        return 0.0  # Placeholder

    async def _calculate_liquidity_score(self) -> float:
        """Calculate overall market liquidity score"""
        depth = await self._calculate_market_depth()

        if not depth:
            return 0.0

        # Average liquidity across all pairs
        total_depth = 0
        pair_count = 0

        for pair_data in depth.values():
            total_depth += pair_data['bid_depth'] + pair_data['ask_depth']
            pair_count += 1

        if pair_count == 0:
            return 0.0

        avg_depth = total_depth / pair_count

        # Normalize to 0-100 scale (simplified)
        liquidity_score = min(avg_depth / 10000, 1.0) * 100

        return liquidity_score

    def _calculate_market_efficiency(self) -> float:
        """Calculate market efficiency score"""
        # Measure how quickly price discrepancies are corrected
        if len(self.price_history) < 10:
            return 0.0

        # Calculate price mean reversion speed
        recent_prices = [p['price'] for p in list(self.price_history)[-10:]]
        mean_price = statistics.mean(recent_prices)

        # Efficiency = how close recent prices are to mean
        deviations = [abs(p - mean_price) / mean_price for p in recent_prices]
        avg_deviation = statistics.mean(deviations)

        # Convert to efficiency score (lower deviation = higher efficiency)
        efficiency = (1 - avg_deviation) * 100

        return max(0, efficiency)

    def get_market_overview(self) -> Dict:
        """Get comprehensive market overview"""
        return {
            'trading_pairs': self.trading_pairs,
            'current_prices': {pair: self.get_real_time_price(pair) for pair in self.trading_pairs},
            '24h_volume': {pair: self.get_volume_metrics(pair, 24) for pair in self.trading_pairs},
            'market_cap': self._estimate_market_cap(),
            'dominance': self._calculate_dominance(),
            'fear_greed_index': self._calculate_fear_greed_index(),
            'top_gainers_losers': self._get_top_movers(),
            'timestamp': time.time()
        }

    def _estimate_market_cap(self) -> float:
        """Estimate 314ST market capitalization"""
        # Simplified calculation
        circulating_supply = 100000000  # 100M 314ST (example)
        current_price = self.get_real_time_price()['price']

        return circulating_supply * current_price

    def _calculate_dominance(self) -> float:
        """Calculate 314ST dominance in crypto market"""
        # Simplified - would compare to total crypto market cap
        return 0.15  # 0.15% dominance (example)

    def _calculate_fear_greed_index(self) -> int:
        """Calculate crypto fear & greed index for 314ST"""
        # Simplified calculation based on volatility and volume
        volatility = self._calculate_volatility(hours=24)
        volume_trend = self._calculate_volume_trend()

        # Fear & Greed Index (0-100)
        if volatility > 10:  # High volatility = fear
            return 25
        elif volume_trend > 0.5:  # High volume = greed
            return 75
        else:
            return 50

    def _calculate_volume_trend(self) -> float:
        """Calculate volume trend (positive = increasing)"""
        if len(self.volume_history) < 48:  # Need at least 48 data points
            return 0.0

        # Compare recent volume to older volume
        recent_volume = sum(v['amount'] for v in list(self.volume_history)[-24:])
        older_volume = sum(v['amount'] for v in list(self.volume_history)[-48:-24])

        if older_volume == 0:
            return 0.0

        return (recent_volume - older_volume) / older_volume

    def _get_top_movers(self) -> Dict:
        """Get top gaining and losing assets"""
        # Simplified - would analyze price changes across pairs
        return {
            'gainers': ['314ST/BTC (+5.2%)', '314ST/ETH (+3.1%)'],
            'losers': ['314ST/USDC (-1.8%)']
        }


class AnalyticsEngine:
    """Advanced analytics engine for market data"""

    def __init__(self):
        self.price_metrics = {}
        self.volume_metrics = {}
        self.indicators = {}

    async def update_price_metrics(self, price_data: Dict):
        """Update price-based analytics"""
        pair = price_data.get('pair', '314ST/USDT')

        if pair not in self.price_metrics:
            self.price_metrics[pair] = {
                'prices': deque(maxlen=1000),
                'sma_20': 0,
                'sma_50': 0,
                'rsi': 50,
                'macd': 0
            }

        metrics = self.price_metrics[pair]
        metrics['prices'].append(price_data['price'])

        # Update technical indicators
        await self._update_technical_indicators(metrics)

    async def update_volume_metrics(self, trade_data: Dict):
        """Update volume-based analytics"""
        pair = trade_data.get('pair', '314ST/USDT')

        if pair not in self.volume_metrics:
            self.volume_metrics[pair] = {
                'volumes': deque(maxlen=1000),
                'vwap': 0,
                'volume_sma': 0
            }

        metrics = self.volume_metrics[pair]
        metrics['volumes'].append(trade_data['amount'])

        # Update volume indicators
        self._update_volume_indicators(metrics)

    async def _update_technical_indicators(self, metrics: Dict):
        """Update technical analysis indicators"""
        prices = list(metrics['prices'])

        if len(prices) >= 20:
            metrics['sma_20'] = statistics.mean(prices[-20:])

        if len(prices) >= 50:
            metrics['sma_50'] = statistics.mean(prices[-50:])

        # RSI calculation (simplified)
        if len(prices) >= 14:
            gains = []
            losses = []

            for i in range(1, min(15, len(prices))):
                change = prices[-i] - prices[-i-1]
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))

            avg_gain = statistics.mean(gains) if gains else 0
            avg_loss = statistics.mean(losses) if losses else 0

            if avg_loss == 0:
                metrics['rsi'] = 100
            else:
                rs = avg_gain / avg_loss
                metrics['rsi'] = 100 - (100 / (1 + rs))

    def _update_volume_indicators(self, metrics: Dict):
        """Update volume-based indicators"""
        volumes = list(metrics['volumes'])

        if volumes:
            metrics['volume_sma'] = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else statistics.mean(volumes)

    async def get_comprehensive_analytics(self) -> Dict:
        """Get comprehensive market analytics"""
        analytics = {
            'technical_indicators': {},
            'volume_analysis': {},
            'market_sentiment': {},
            'risk_metrics': {}
        }

        # Compile technical indicators
        for pair, metrics in self.price_metrics.items():
            analytics['technical_indicators'][pair] = {
                'sma_20': metrics['sma_20'],
                'sma_50': metrics['sma_50'],
                'rsi': metrics['rsi'],
                'macd': metrics['macd'],
                'trend': 'bullish' if metrics['sma_20'] > metrics['sma_50'] else 'bearish'
            }

        # Compile volume analysis
        for pair, metrics in self.volume_metrics.items():
            analytics['volume_analysis'][pair] = {
                'volume_sma': metrics['volume_sma'],
                'current_volume': metrics['volumes'][-1] if metrics['volumes'] else 0
            }

        return analytics


class RealTimeDataStream:
    """Real-time data streaming for market data"""

    def __init__(self):
        self.subscribers = set()
        self.price_subscribers = set()
        self.trade_subscribers = set()

    async def broadcast_price_update(self, price_data: Dict):
        """Broadcast price update to subscribers"""
        message = {
            'type': 'price_update',
            'data': price_data,
            'timestamp': time.time()
        }

        # In production, this would send to WebSocket connections
        print(f"📡 Broadcasting price update: {price_data}")

    async def broadcast_trade_update(self, trade_data: Dict):
        """Broadcast trade update to subscribers"""
        message = {
            'type': 'trade_update',
            'data': trade_data,
            'timestamp': time.time()
        }

        print(f"📡 Broadcasting trade update: {trade_data}")

    async def subscribe_to_prices(self, callback):
        """Subscribe to real-time price updates"""
        self.price_subscribers.add(callback)

    async def subscribe_to_trades(self, callback):
        """Subscribe to real-time trade updates"""
        self.trade_subscribers.add(callback)


class PriceFeed:
    """Price feed connection to external oracles"""

    def __init__(self, name: str):
        self.name = name
        self.connected = False
        self.price_callbacks = []
        self.trade_callbacks = []

    async def connect(self):
        """Connect to price feed (simulated)"""
        self.connected = True
        print(f"🔗 Connected to {self.name} price feed")

    def on_price_update(self, callback):
        """Register price update callback"""
        self.price_callbacks.append(callback)

    def on_trade(self, callback):
        """Register trade update callback"""
        self.trade_callbacks.append(callback)

    async def simulate_price_update(self, price: float, volume: float = 0):
        """Simulate a price update (for testing)"""
        if not self.connected:
            return

        price_data = {
            'price': price,
            'volume': volume,
            'pair': '314ST/USDT',
            'timestamp': time.time()
        }

        for callback in self.price_callbacks:
            await callback(self.name, price_data)