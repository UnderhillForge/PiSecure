"""
PiSecure Legacy Module

This directory contains old/deprecated code that has been refactored
into the modular architecture. Code here is kept for reference and
gradual migration, but should not be used in new code.

ARCHIVED FILES:
===============

Architecture Refactoring:
- wallet_old.py - Old wallet implementation
- cli_legacy.py - Original cli.py before modularization

Consensus Logic (moved to kernel/):
- consensus.py → pisecure/kernel/consensus.py
- validation.py → pisecure/kernel/validation.py
- pihash.py → pisecure/kernel/pihash.py

Testing & Debug (not part of production):
- conftest_test_fix.py - Testing configuration
- debug_bootstrap.py - Bootstrap debugging tool
- test_dashboard.py - Dashboard tests
- test_mempool_sanity.py - Mempool sanity tests
- test_websocket_implementation.py - WebSocket tests
- test_websocket_integration.py - WebSocket integration tests
- PHASE1_QUICKSTART.py - Old quickstart guide
- monitor.py - Old monitoring code (use monitoring.py in core/)

MIGRATION NOTES:
===============

1. When adding new code, DO NOT import from legacy/
2. Legacy code is for reference only during migration
3. Use new architecture patterns from interfaces/, node/, common/
4. Gradually migrate functions from legacy to production modules
5. Remove legacy files once all functionality is migrated

USAGE:
======

If you need to understand old patterns:
- Check legacy/ for reference
- See ARCHITECTURE_ANALYSIS.md for why changes were made
- Check BITCOIN_PATTERNS.md for new patterns to use
"""

__all__ = []
