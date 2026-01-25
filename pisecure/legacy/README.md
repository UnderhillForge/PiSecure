# Legacy Code Archive

This directory contains deprecated implementations that have been superseded by newer versions.

## Archived Modules

### `wallet_old.py`
**Superseded by:** `pisecure/core/wallet_v2.py`

**Reason for replacement:**
- Old implementation used XOR encryption (insecure)
- No UTXO tracking (balance drift)
- No HD wallet support
- JSON file storage (not atomic)
- Missing Bitcoin Core best practices

**New features in wallet_v2:**
- Fernet encryption (AES-128-CBC + HMAC)
- UTXO tracking with coin selection algorithms
- HD wallet with BIP32-style derivation
- SQLite database with WAL mode
- ScriptPubKeyManager architecture
- Address book with labels
- Watch-only wallet support
- Fee estimation

**Migration path:**
Use `pisecure/core/wallet_v2.py` and CLI at `scripts/pswallet_v2.py`

---

## Code Preservation

All legacy code is preserved here for:
1. **Reference** - Understanding historical design decisions
2. **Rollback** - Quick recovery if needed
3. **Comparison** - Analyzing improvements
4. **Documentation** - Learning purposes

Do not use legacy code in production. If you need a feature from legacy code, port it to the current implementation instead.
