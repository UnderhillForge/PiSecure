"""
Validator Rewards System for PiSecure

Comprehensive reward mechanism for network validators including:
- API service fees for public endpoints
- Block validation bonuses
- Staking rewards for network support
- Governance participation incentives

Validators play crucial role in network decentralization and can earn
significant rewards without mining hardware requirements.
"""

import time
import statistics
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class ValidatorTier(Enum):
    """Validator service tiers with different reward levels"""
    BASIC = "basic"           # Minimal services, basic rewards
    STANDARD = "standard"     # Standard API services
    PREMIUM = "premium"       # Full services, high availability
    ENTERPRISE = "enterprise" # Maximum services, SLA guarantees


class RewardType(Enum):
    """Types of validator rewards"""
    API_FEES = "api_fees"
    VALIDATION_BONUS = "validation_bonus"
    STAKING_REWARDS = "staking_rewards"
    GOVERNANCE_REWARDS = "governance_rewards"
    UPTIME_BONUS = "uptime_bonus"


@dataclass
class ValidatorProfile:
    """Profile information for a validator node"""
    node_id: str
    wallet_address: str
    tier: ValidatorTier
    services_offered: List[str] = field(default_factory=list)
    stake_amount: float = 0.0
    reputation_score: float = 1.0
    uptime_percentage: float = 100.0
    registered_at: float = field(default_factory=time.time)


@dataclass
class RewardEvent:
    """Individual reward event record"""
    validator_id: str
    reward_type: RewardType
    amount: float
    reason: str
    timestamp: float = field(default_factory=time.time)
    transaction_hash: Optional[str] = None


@dataclass
class ValidatorStats:
    """Performance statistics for validator tracking"""
    total_requests_served: int = 0
    blocks_validated: int = 0
    uptime_seconds: float = 0.0
    last_active: float = field(default_factory=time.time)
    api_calls_per_hour: float = 0.0
    error_rate: float = 0.0


class ValidatorRewardsManager:
    """
    Comprehensive validator rewards management system

    Handles reward calculation, distribution, and tracking for all
    validator participation types in the PiSecure network.
    """

    def __init__(self):
        # Base reward rates (adjustable via governance)
        self.base_rates = {
            RewardType.API_FEES: {
                ValidatorTier.BASIC: 0.01,      # 0.01 314ST per API call
                ValidatorTier.STANDARD: 0.05,   # 0.05 314ST per API call
                ValidatorTier.PREMIUM: 0.10,    # 0.10 314ST per API call
                ValidatorTier.ENTERPRISE: 0.20  # 0.20 314ST per API call
            },
            RewardType.VALIDATION_BONUS: {
                ValidatorTier.BASIC: 0.5,       # 0.5 314ST per block
                ValidatorTier.STANDARD: 1.0,    # 1.0 314ST per block
                ValidatorTier.PREMIUM: 2.0,     # 2.0 314ST per block
                ValidatorTier.ENTERPRISE: 3.0   # 3.0 314ST per block
            },
            RewardType.STAKING_REWARDS: {
                "apy_base": 0.08,  # 8% base APY
                "apy_bonus_max": 0.04,  # Up to 4% bonus for high uptime/reputation
            },
            RewardType.GOVERNANCE_REWARDS: {
                "proposal_creation": 5.0,       # 5 314ST for creating proposals
                "voting_participation": 1.0,    # 1 314ST per vote
                "successful_proposal": 25.0,    # 25 314ST for successful proposals
            },
            RewardType.UPTIME_BONUS: {
                "threshold_99_9": 0.5,    # Bonus multiplier for 99.9% uptime
                "threshold_99_99": 1.0,  # Bonus for 99.99% uptime
            }
        }

        # Validator registry and tracking
        self.validators: Dict[str, ValidatorProfile] = {}
        self.validator_stats: Dict[str, ValidatorStats] = {}
        self.reward_history: List[RewardEvent] = []

        # Network-wide settings
        self.total_staked_tokens = 0.0
        self.network_reward_pool = 0.0  # Periodic reward distributions

    def register_validator(self, node_id: str, wallet_address: str,
                          tier: ValidatorTier, initial_stake: float = 0.0,
                          services: List[str] = None) -> ValidatorProfile:
        """
        Register a new validator node

        Args:
            node_id: Unique node identifier
            wallet_address: Validator's reward wallet
            tier: Service tier
            initial_stake: Initial stake amount
            services: List of services offered

        Returns:
            ValidatorProfile for the registered validator
        """
        if services is None:
            services = ["api", "validation"]

        profile = ValidatorProfile(
            node_id=node_id,
            wallet_address=wallet_address,
            tier=tier,
            services_offered=services,
            stake_amount=initial_stake,
            reputation_score=1.0
        )

        self.validators[node_id] = profile
        self.validator_stats[node_id] = ValidatorStats()
        self.total_staked_tokens += initial_stake

        # Log registration reward
        self._record_reward(node_id, RewardType.STAKING_REWARDS,
                          initial_stake * 0.01, "Validator registration bonus")

        return profile

    def calculate_api_fee_reward(self, validator_id: str, api_calls: int,
                               call_complexity: float = 1.0) -> float:
        """
        Calculate API service fee rewards

        Args:
            validator_id: Validator node ID
            api_calls: Number of API calls served
            call_complexity: Complexity multiplier (1.0 = standard)

        Returns:
            Reward amount in 314ST
        """
        if validator_id not in self.validators:
            return 0.0

        validator = self.validators[validator_id]
        base_rate = self.base_rates[RewardType.API_FEES][validator.tier]

        # Apply reputation and uptime bonuses
        reputation_multiplier = validator.reputation_score
        uptime_bonus = self._calculate_uptime_bonus(validator.uptime_percentage)

        effective_rate = base_rate * reputation_multiplier * uptime_bonus * call_complexity

        reward = api_calls * effective_rate

        # Record the reward event
        self._record_reward(validator_id, RewardType.API_FEES, reward,
                          f"API service fees: {api_calls} calls")

        return reward

    def calculate_validation_bonus(self, validator_id: str, blocks_validated: int) -> float:
        """
        Calculate block validation bonus rewards

        Args:
            validator_id: Validator node ID
            blocks_validated: Number of blocks validated

        Returns:
            Reward amount in 314ST
        """
        if validator_id not in self.validators:
            return 0.0

        validator = self.validators[validator_id]
        base_bonus = self.base_rates[RewardType.VALIDATION_BONUS][validator.tier]

        # Apply network participation bonus
        network_participation = self._calculate_network_participation(validator_id)
        participation_multiplier = 1.0 + (network_participation * 0.5)  # Up to 50% bonus

        effective_bonus = base_bonus * participation_multiplier

        reward = blocks_validated * effective_bonus

        # Record the reward event
        self._record_reward(validator_id, RewardType.VALIDATION_BONUS, reward,
                          f"Block validation bonus: {blocks_validated} blocks")

        return reward

    def calculate_staking_rewards(self, validator_id: str, time_period_days: int = 30) -> float:
        """
        Calculate staking rewards for locked tokens

        Args:
            validator_id: Validator node ID
            time_period_days: Time period for reward calculation

        Returns:
            Reward amount in 314ST
        """
        if validator_id not in self.validators:
            return 0.0

        validator = self.validators[validator_id]
        stake_amount = validator.stake_amount

        if stake_amount <= 0:
            return 0.0

        # Base APY calculation
        base_apy = self.base_rates[RewardType.STAKING_REWARDS]["apy_base"]

        # Performance bonuses
        uptime_bonus = self._calculate_uptime_bonus(validator.uptime_percentage)
        reputation_bonus = min(validator.reputation_score, 2.0)  # Cap at 2x

        # Stake amount bonus (larger stakes get slightly higher rewards)
        stake_bonus = min(stake_amount / 10000, 0.2)  # Up to 20% for 10k stake

        effective_apy = base_apy * uptime_bonus * reputation_bonus * (1 + stake_bonus)

        # Calculate reward for time period
        daily_rate = effective_apy / 365
        reward = stake_amount * daily_rate * time_period_days

        # Record the reward event
        self._record_reward(validator_id, RewardType.STAKING_REWARDS, reward,
                          f"Staking rewards: {time_period_days} days at {effective_apy:.1%} APY")

        return reward

    def calculate_governance_rewards(self, validator_id: str, actions: Dict[str, int]) -> float:
        """
        Calculate governance participation rewards

        Args:
            validator_id: Validator node ID
            actions: Dictionary of governance actions performed

        Returns:
            Reward amount in 314ST
        """
        if validator_id not in self.validators:
            return 0.0

        total_reward = 0.0
        rates = self.base_rates[RewardType.GOVERNANCE_REWARDS]

        # Proposal creation rewards
        proposals_created = actions.get('proposals_created', 0)
        total_reward += proposals_created * rates['proposal_creation']

        # Voting participation rewards
        votes_cast = actions.get('votes_cast', 0)
        total_reward += votes_cast * rates['voting_participation']

        # Successful proposal bonuses
        successful_proposals = actions.get('successful_proposals', 0)
        total_reward += successful_proposals * rates['successful_proposal']

        # Record the reward event
        if total_reward > 0:
            self._record_reward(validator_id, RewardType.GOVERNANCE_REWARDS, total_reward,
                              f"Governance participation: {proposals_created} proposals, {votes_cast} votes")

        return total_reward

    def update_validator_stats(self, validator_id: str, stats_update: Dict[str, Any]):
        """
        Update validator performance statistics

        Args:
            validator_id: Validator node ID
            stats_update: Statistics to update
        """
        if validator_id not in self.validator_stats:
            self.validator_stats[validator_id] = ValidatorStats()

        stats = self.validator_stats[validator_id]

        # Update statistics
        for key, value in stats_update.items():
            if hasattr(stats, key):
                setattr(stats, key, value)

        stats.last_active = time.time()

        # Update validator profile with derived metrics
        if validator_id in self.validators:
            profile = self.validators[validator_id]
            profile.uptime_percentage = self._calculate_uptime_percentage(validator_id)

    def get_validator_rewards_summary(self, validator_id: str,
                                   time_period_days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive rewards summary for a validator

        Args:
            validator_id: Validator node ID
            time_period_days: Time period for summary

        Returns:
            Dictionary with rewards breakdown
        """
        if validator_id not in self.validators:
            return {"error": "Validator not found"}

        profile = self.validators[validator_id]

        # Calculate all reward types
        api_rewards = self._calculate_recent_api_rewards(validator_id, time_period_days)
        validation_rewards = self._calculate_recent_validation_rewards(validator_id, time_period_days)
        staking_rewards = self.calculate_staking_rewards(validator_id, time_period_days)
        governance_rewards = self._calculate_recent_governance_rewards(validator_id, time_period_days)

        total_rewards = api_rewards + validation_rewards + staking_rewards + governance_rewards

        return {
            "validator_id": validator_id,
            "tier": profile.tier.value,
            "stake_amount": profile.stake_amount,
            "rewards_breakdown": {
                "api_fees": api_rewards,
                "validation_bonuses": validation_rewards,
                "staking_rewards": staking_rewards,
                "governance_rewards": governance_rewards,
                "total": total_rewards
            },
            "performance_metrics": {
                "uptime_percentage": profile.uptime_percentage,
                "reputation_score": profile.reputation_score,
                "services_offered": profile.services_offered
            },
            "time_period_days": time_period_days
        }

    def distribute_network_rewards(self, total_rewards: float):
        """
        Distribute network-wide rewards to validators based on participation

        Args:
            total_rewards: Total rewards to distribute
        """
        if not self.validators:
            return

        # Calculate participation weights
        total_weight = 0.0
        weights = {}

        for validator_id, profile in self.validators.items():
            # Weight based on stake, uptime, and services offered
            stake_weight = profile.stake_amount / 1000  # 1 weight per 1000 staked
            uptime_weight = profile.uptime_percentage / 100.0
            service_weight = len(profile.services_offered) * 0.5

            weight = (stake_weight + uptime_weight + service_weight) * profile.reputation_score
            weights[validator_id] = weight
            total_weight += weight

        # Distribute rewards proportionally
        for validator_id, weight in weights.items():
            if total_weight > 0:
                reward_amount = total_rewards * (weight / total_weight)
                self._record_reward(validator_id, RewardType.STAKING_REWARDS, reward_amount,
                                  "Network reward distribution")

    def _calculate_uptime_bonus(self, uptime_percentage: float) -> float:
        """Calculate uptime bonus multiplier"""
        if uptime_percentage >= 99.99:
            return 1.0 + self.base_rates[RewardType.UPTIME_BONUS]["threshold_99_99"]
        elif uptime_percentage >= 99.9:
            return 1.0 + self.base_rates[RewardType.UPTIME_BONUS]["threshold_99_9"]
        else:
            return 1.0

    def _calculate_network_participation(self, validator_id: str) -> float:
        """Calculate validator's network participation ratio"""
        if validator_id not in self.validator_stats:
            return 0.0

        stats = self.validator_stats[validator_id]
        total_validators = len(self.validators)

        if total_validators == 0:
            return 0.0

        # Participation based on recent activity vs other validators
        recent_activity = stats.blocks_validated + stats.total_requests_served

        # Simplified participation calculation
        participation = min(recent_activity / 1000, 1.0)  # Cap at 1.0

        return participation

    def _calculate_uptime_percentage(self, validator_id: str) -> float:
        """Calculate validator uptime percentage"""
        if validator_id not in self.validator_stats:
            return 100.0

        stats = self.validator_stats[validator_id]
        registered_time = self.validators[validator_id].registered_at
        total_time = time.time() - registered_time

        if total_time <= 0:
            return 100.0

        uptime_percentage = (stats.uptime_seconds / total_time) * 100.0
        return min(uptime_percentage, 100.0)

    def _calculate_recent_api_rewards(self, validator_id: str, days: int) -> float:
        """Calculate API rewards earned in recent period"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        recent_rewards = [
            event.amount for event in self.reward_history
            if event.validator_id == validator_id and
            event.reward_type == RewardType.API_FEES and
            event.timestamp >= cutoff_time
        ]

        return sum(recent_rewards)

    def _calculate_recent_validation_rewards(self, validator_id: str, days: int) -> float:
        """Calculate validation rewards earned in recent period"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        recent_rewards = [
            event.amount for event in self.reward_history
            if event.validator_id == validator_id and
            event.reward_type == RewardType.VALIDATION_BONUS and
            event.timestamp >= cutoff_time
        ]

        return sum(recent_rewards)

    def _calculate_recent_governance_rewards(self, validator_id: str, days: int) -> float:
        """Calculate governance rewards earned in recent period"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        recent_rewards = [
            event.amount for event in self.reward_history
            if event.validator_id == validator_id and
            event.reward_type == RewardType.GOVERNANCE_REWARDS and
            event.timestamp >= cutoff_time
        ]

        return sum(recent_rewards)

    def _record_reward(self, validator_id: str, reward_type: RewardType,
                      amount: float, reason: str, tx_hash: str = None):
        """
        Record a reward event in the history

        Args:
            validator_id: Validator that earned the reward
            reward_type: Type of reward earned
            amount: Reward amount
            reason: Description of why reward was earned
            tx_hash: Optional blockchain transaction hash
        """
        event = RewardEvent(
            validator_id=validator_id,
            reward_type=reward_type,
            amount=amount,
            reason=reason,
            transaction_hash=tx_hash
        )

        self.reward_history.append(event)

        # Keep only recent history (last 90 days)
        cutoff_time = time.time() - (90 * 24 * 60 * 60)
        self.reward_history = [
            event for event in self.reward_history
            if event.timestamp >= cutoff_time
        ]


# Convenience functions
def calculate_validator_rewards(validator_id: str, manager: ValidatorRewardsManager,
                              time_period_days: int = 30) -> Dict[str, Any]:
    """
    Convenience function to get validator rewards summary

    Args:
        validator_id: Validator node ID
        manager: ValidatorRewardsManager instance
        time_period_days: Time period for calculation

    Returns:
        Rewards summary dictionary
    """
    return manager.get_validator_rewards_summary(validator_id, time_period_days)


def register_validator_node(manager: ValidatorRewardsManager, node_id: str,
                          wallet_address: str, tier: ValidatorTier,
                          initial_stake: float = 0.0) -> ValidatorProfile:
    """
    Convenience function to register a validator

    Args:
        manager: ValidatorRewardsManager instance
        node_id: Unique node identifier
        wallet_address: Validator's reward wallet
        tier: Service tier
        initial_stake: Initial stake amount

    Returns:
        ValidatorProfile for the registered validator
    """
    return manager.register_validator(node_id, wallet_address, tier, initial_stake)