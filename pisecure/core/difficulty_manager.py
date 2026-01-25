"""
Hybrid Difficulty Management System for PiSecure

Combines traditional difficulty adjustment with time-based throttling
to provide precise control over mining rates and token economics.

Key Features:
- Network-aware difficulty adjustment based on miner count
- Time-based throttling to prevent excessive mining
- Economic controls for sustainable token supply
- Integration with PiHash algorithm
- Configurable parameters for different network phases
"""

import time
import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class NetworkPhase(Enum):
    """Network development phases"""
    SOLO_MINING = "solo"          # 1 miner (pre-launch)
    EARLY_ADOPTION = "early"       # 2-10 miners
    GROWTH_PHASE = "growth"       # 11-100 miners
    MATURE_NETWORK = "mature"      # 100+ miners


@dataclass
class DifficultyConfig:
    """Configuration for difficulty management"""
    target_blocks_per_hour: float
    min_block_time_seconds: int
    max_difficulty: int
    adjustment_interval_blocks: int
    max_adjustment_percent: float
    network_phase: NetworkPhase


@dataclass
class MiningStats:
    """Real-time mining statistics"""
    active_miners: int
    recent_blocks: List[Dict]
    current_difficulty: int
    average_block_time: float
    network_hashrate: float
    timestamp: float


class HybridDifficultyManager:
    """
    Hybrid difficulty management combining algorithmic adjustment with time controls

    Provides precise control over mining rates through:
    - Network-aware target setting
    - Dynamic difficulty adjustment
    - Time-based throttling
    - Economic parameter tuning
    """

    def __init__(self):
        # Default configurations for each network phase
        self.phase_configs = {
            NetworkPhase.SOLO_MINING: DifficultyConfig(
                target_blocks_per_hour=2.0,      # Very slow for solo mining
                min_block_time_seconds=1800,     # 30 minutes minimum
                max_difficulty=50,               # Reasonable for Pi hardware
                adjustment_interval_blocks=1,     # Adjust every block
                max_adjustment_percent=25.0,     # Gentle adjustments
                network_phase=NetworkPhase.SOLO_MINING
            ),
            NetworkPhase.EARLY_ADOPTION: DifficultyConfig(
                target_blocks_per_hour=8.0,      # Moderate speed
                min_block_time_seconds=450,      # 7.5 minutes minimum
                max_difficulty=100,              # Higher difficulty
                adjustment_interval_blocks=3,     # Adjust every 3 blocks
                max_adjustment_percent=20.0,     # Moderate adjustments
                network_phase=NetworkPhase.EARLY_ADOPTION
            ),
            NetworkPhase.GROWTH_PHASE: DifficultyConfig(
                target_blocks_per_hour=15.0,     # Faster mining
                min_block_time_seconds=240,      # 4 minutes minimum
                max_difficulty=200,              # Significant difficulty
                adjustment_interval_blocks=5,     # Adjust every 5 blocks
                max_adjustment_percent=15.0,     # Smaller adjustments
                network_phase=NetworkPhase.GROWTH_PHASE
            ),
            NetworkPhase.MATURE_NETWORK: DifficultyConfig(
                target_blocks_per_hour=25.0,     # Fast mining
                min_block_time_seconds=144,      # 2.4 minutes minimum
                max_difficulty=500,              # High difficulty
                adjustment_interval_blocks=10,    # Adjust every 10 blocks
                max_adjustment_percent=10.0,     # Conservative adjustments
                network_phase=NetworkPhase.MATURE_NETWORK
            )
        }

        # Current state
        self.current_config = self.phase_configs[NetworkPhase.SOLO_MINING]
        self.mining_stats_history: List[MiningStats] = []
        self.last_adjustment_block = 0

        # Economic controls - gradual reduction instead of hard caps
        self.difficulty_multiplier = 1.0  # Base difficulty multiplier
        self.supply_decay_rate = 0.02     # 2% monthly reduction in mining rewards
        self.emergency_throttle_active = False

    def get_current_config(self, network_stats: Dict) -> DifficultyConfig:
        """
        Determine appropriate difficulty configuration based on network state

        Args:
            network_stats: Current network statistics

        Returns:
            Appropriate DifficultyConfig for current network state
        """
        active_miners = network_stats.get('active_miners', 1)

        # Determine network phase
        if active_miners <= 1:
            phase = NetworkPhase.SOLO_MINING
        elif active_miners <= 10:
            phase = NetworkPhase.EARLY_ADOPTION
        elif active_miners <= 100:
            phase = NetworkPhase.GROWTH_PHASE
        else:
            phase = NetworkPhase.MATURE_NETWORK

        # Get base config for phase
        config = self.phase_configs[phase].__class__(
            **self.phase_configs[phase].__dict__
        )

        # Apply economic adjustments
        config = self._apply_economic_adjustments(config, network_stats)

        # Apply emergency throttling if needed
        if self.emergency_throttle_active:
            config = self._apply_emergency_throttling(config)

        self.current_config = config
        return config

    def calculate_optimal_difficulty(self, network_stats: Dict,
                                   recent_blocks: List[Dict]) -> Tuple[int, str]:
        """
        Calculate optimal difficulty based on network conditions

        Args:
            network_stats: Current network statistics
            recent_blocks: Recent block data for analysis

        Returns:
            Tuple of (optimal_difficulty, reasoning)
        """
        config = self.get_current_config(network_stats)

        # Analyze recent mining activity
        if not recent_blocks:
            return config.max_difficulty // 2, "No recent blocks - using conservative difficulty"

        # Calculate actual vs target mining rate
        actual_rate = self._calculate_mining_rate(recent_blocks)
        target_rate = config.target_blocks_per_hour

        # Calculate adjustment factor
        if actual_rate == 0:
            adjustment_factor = 0.5  # Reduce difficulty if no mining
        else:
            adjustment_factor = target_rate / actual_rate

        # Limit adjustment magnitude
        max_adjustment = config.max_adjustment_percent / 100.0
        adjustment_factor = max(1 - max_adjustment, min(1 + max_adjustment, adjustment_factor))

        # Get current difficulty (from last block or default)
        current_difficulty = recent_blocks[-1].get('difficulty', 4) if recent_blocks else 4

        # Calculate new difficulty
        new_difficulty = int(current_difficulty * adjustment_factor)

        # Clamp to valid range
        new_difficulty = max(1, min(config.max_difficulty, new_difficulty))

        # Generate reasoning
        reasoning = self._generate_adjustment_reasoning(
            actual_rate, target_rate, current_difficulty, new_difficulty, config
        )

        return new_difficulty, reasoning

    def should_throttle_mining(self, last_block_time: float,
                              current_difficulty: int) -> Tuple[bool, float]:
        """
        Determine if mining should be throttled based on time constraints

        Args:
            last_block_time: Timestamp of last block
            current_difficulty: Current difficulty level

        Returns:
            Tuple of (should_throttle, wait_seconds)
        """
        config = self.current_config
        current_time = time.time()

        # Check minimum block time
        time_since_last_block = current_time - last_block_time
        if time_since_last_block < config.min_block_time_seconds:
            wait_time = config.min_block_time_seconds - time_since_last_block
            return True, wait_time

        # Check emergency throttling
        if self.emergency_throttle_active:
            # During emergency, enforce stricter timing
            emergency_min_time = config.min_block_time_seconds * 2
            if time_since_last_block < emergency_min_time:
                wait_time = emergency_min_time - time_since_last_block
                return True, wait_time

        return False, 0.0

    def update_mining_stats(self, network_stats: Dict, recent_blocks: List[Dict]):
        """
        Update internal mining statistics for decision making

        Args:
            network_stats: Current network statistics
            recent_blocks: Recent block data
        """
        stats = MiningStats(
            active_miners=network_stats.get('active_miners', 1),
            recent_blocks=recent_blocks[-20:],  # Keep last 20 blocks
            current_difficulty=recent_blocks[-1].get('difficulty', 4) if recent_blocks else 4,
            average_block_time=self._calculate_average_block_time(recent_blocks),
            network_hashrate=self._estimate_network_hashrate(recent_blocks),
            timestamp=time.time()
        )

        self.mining_stats_history.append(stats)

        # Keep only recent history (last 24 hours)
        cutoff_time = time.time() - (24 * 60 * 60)
        self.mining_stats_history = [
            s for s in self.mining_stats_history if s.timestamp > cutoff_time
        ]

    def activate_emergency_throttling(self, reason: str = "Supply cap exceeded"):
        """
        Activate emergency throttling to slow mining significantly

        Args:
            reason: Reason for emergency throttling
        """
        self.emergency_throttle_active = True
        print(f"🚨 EMERGENCY THROTTLING ACTIVATED: {reason}")

        # Increase minimum block times by 5x
        for config in self.phase_configs.values():
            config.min_block_time_seconds *= 5

    def deactivate_emergency_throttling(self):
        """Deactivate emergency throttling and restore normal operation"""
        if self.emergency_throttle_active:
            self.emergency_throttle_active = False
            print("✅ Emergency throttling deactivated")

            # Restore original timing
            self._reset_phase_configs()

    def apply_supply_decay(self, months_since_launch: int) -> float:
        """
        Apply gradual supply decay over time (like Bitcoin halving but smoother)

        Args:
            months_since_launch: Months since network launch

        Returns:
            Supply multiplier (1.0 = normal, 0.5 = half rewards, etc.)
        """
        # Gradual decay: reduce mining rewards by supply_decay_rate per month
        decay_multiplier = (1 - self.supply_decay_rate) ** months_since_launch

        # Never go below 10% of original rewards (ensures long-term mining viability)
        decay_multiplier = max(0.1, decay_multiplier)

        return decay_multiplier

    def _calculate_mining_rate(self, recent_blocks: List[Dict]) -> float:
        """Calculate blocks per hour from recent block data"""
        if len(recent_blocks) < 2:
            return 0.0

        # Use last 10 blocks for calculation
        blocks = recent_blocks[-10:]
        if len(blocks) < 2:
            return 0.0

        time_span = blocks[-1]['timestamp'] - blocks[0]['timestamp']
        if time_span <= 0:
            return 0.0

        blocks_per_second = len(blocks) / time_span
        blocks_per_hour = blocks_per_second * 3600

        return blocks_per_hour

    def _calculate_average_block_time(self, recent_blocks: List[Dict]) -> float:
        """Calculate average time between blocks"""
        if len(recent_blocks) < 2:
            return float('inf')

        timestamps = [block['timestamp'] for block in recent_blocks]
        intervals = []

        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            if interval > 0:
                intervals.append(interval)

        if not intervals:
            return float('inf')

        return statistics.mean(intervals)

    def _estimate_network_hashrate(self, recent_blocks: List[Dict]) -> float:
        """
        Estimate total network hashrate based on block times and difficulty

        Note: This is a rough estimate for monitoring purposes
        """
        if not recent_blocks:
            return 0.0

        # Simplified hashrate estimation
        avg_difficulty = statistics.mean([b.get('difficulty', 4) for b in recent_blocks])
        avg_block_time = self._calculate_average_block_time(recent_blocks)

        if avg_block_time == 0 or avg_block_time == float('inf'):
            return 0.0

        # Rough estimation: hashrate proportional to difficulty / block_time
        estimated_hashrate = avg_difficulty / avg_block_time

        return estimated_hashrate

    def _apply_economic_adjustments(self, config: DifficultyConfig,
                                   network_stats: Dict) -> DifficultyConfig:
        """Apply economic adjustments to difficulty config"""
        # Could adjust based on token price, market conditions, etc.
        # For now, return config unchanged
        return config

    def _apply_emergency_throttling(self, config: DifficultyConfig) -> DifficultyConfig:
        """Apply emergency throttling parameters"""
        # Create a copy and modify
        emergency_config = DifficultyConfig(**config.__dict__)

        # Drastically increase minimum block time
        emergency_config.min_block_time_seconds *= 10  # 10x slower

        # Reduce target blocks per hour
        emergency_config.target_blocks_per_hour /= 5  # 5x fewer blocks

        return emergency_config

    def _reset_phase_configs(self):
        """Reset phase configurations to original values"""
        # Restore original timing values
        self.phase_configs[NetworkPhase.SOLO_MINING].min_block_time_seconds = 1800
        self.phase_configs[NetworkPhase.EARLY_ADOPTION].min_block_time_seconds = 450
        self.phase_configs[NetworkPhase.GROWTH_PHASE].min_block_time_seconds = 240
        self.phase_configs[NetworkPhase.MATURE_NETWORK].min_block_time_seconds = 144

    def _generate_adjustment_reasoning(self, actual_rate: float, target_rate: float,
                                      old_difficulty: int, new_difficulty: int,
                                      config: DifficultyConfig) -> str:
        """Generate human-readable reasoning for difficulty adjustment"""
        rate_ratio = actual_rate / target_rate if target_rate > 0 else 0

        if rate_ratio > 1.1:
            trend = "faster than target"
            action = "increasing"
        elif rate_ratio < 0.9:
            trend = "slower than target"
            action = "decreasing"
        else:
            trend = "on target"
            action = "maintaining"

        return (
            f"Mining {trend} ({actual_rate:.1f} vs {target_rate:.1f} blocks/hour). "
            f"{action.capitalize()} difficulty from {old_difficulty} to {new_difficulty} "
            f"(phase: {config.network_phase.value})"
        )

    def get_network_health_report(self) -> Dict:
        """
        Generate comprehensive network health report

        Returns:
            Dictionary with network health metrics
        """
        if not self.mining_stats_history:
            return {"status": "No data available"}

        latest_stats = self.mining_stats_history[-1]

        return {
            "network_phase": self.current_config.network_phase.value,
            "active_miners": latest_stats.active_miners,
            "current_difficulty": latest_stats.current_difficulty,
            "average_block_time": latest_stats.average_block_time,
            "network_hashrate": latest_stats.network_hashrate,
            "emergency_throttling": self.emergency_throttle_active,
            "blocks_per_hour": len(latest_stats.recent_blocks) / 24,  # Rough estimate
            "last_updated": latest_stats.timestamp
        }


# Convenience functions
def get_optimal_difficulty(network_stats: Dict, recent_blocks: List[Dict]) -> Tuple[int, str]:
    """
    Convenience function to get optimal difficulty

    Args:
        network_stats: Current network statistics
        recent_blocks: Recent block data

    Returns:
        Tuple of (difficulty, reasoning)
    """
    manager = HybridDifficultyManager()
    return manager.calculate_optimal_difficulty(network_stats, recent_blocks)


def should_throttle_mining(last_block_time: float, current_difficulty: int) -> Tuple[bool, float]:
    """
    Convenience function to check mining throttling

    Args:
        last_block_time: Timestamp of last block
        current_difficulty: Current difficulty level

    Returns:
        Tuple of (should_throttle, wait_seconds)
    """
    manager = HybridDifficultyManager()
    return manager.should_throttle_mining(last_block_time, current_difficulty)