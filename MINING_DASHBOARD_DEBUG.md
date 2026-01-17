# Mining Dashboard Real-Time Stats Issue

## Current Status: Dashboard shows ACTIVE but stats frozen at 0

**Last tested:** 2026-01-17
**Command:** `pisecure monitor --wallet pi_test --testnet`
**Symptom:** Dashboard shows ACTIVE status, CPU heating (76.8°C), but Hashrate/Nonce/Hashes all stuck at 0, uptime frozen at 2s

## What We're Trying to Fix

Get real-time mining stats updating in the dashboard:
- ⚡ Hashrate should update every ~10 seconds
- 🔢 Nonce should increment continuously  
- 🔨 Hashes should climb
- 🎯 Progress should show best zeros found

## Changes Made (All in this session)

### 1. Reduced Sample Interval (blockchain.py line ~1064)
```python
sample_interval = 10  # Update every 10 hashes (~10 seconds at 1 H/s)
```
Previously was 100 hashes (2 minutes) and 1000 hashes (15 minutes).

### 2. Fixed Hash Counter (blockchain.py line ~1072)
```python
self.blockchain.mining_session['hashes_tried'] = hashes_tried
```
Was `+= 1` which didn't track cumulative count correctly.

### 3. Released Lock During Mining (blockchain.py line ~1708-1750)
```python
# Prepare block WITH lock
with self.lock:
    # ... create block ...
# Release lock, then mine WITHOUT lock
new_block.mine_block(self.difficulty, verbose)
# Re-acquire lock to add block to chain
with self.lock:
    self.chain.append(new_block)
```
Prevents 60+ second lock hold during mining.

### 4. Made ALL Session Updates Lock-Free (blockchain.py multiple lines)
Removed `with self.blockchain.lock:` from:
- Line ~1044: Session initialization in `mine_block()`
- Line ~1072: Nonce/hashes update every iteration
- Line ~1089: Best zeros update
- Line ~1096: Blocks found increment
- Line ~1108: Hashrate update

Also in cli.py line ~837: Background thread session init

**Rationale:** Simple dict assignments are atomic in Python, no lock needed.

### 5. Made Chain Info Lock-Free (blockchain.py line ~1945)
```python
def get_chain_info(self) -> Dict[str, Any]:
    # Use cached validation instead of calling validate_chain()
    is_valid = self._cached_chain_valid if self._cached_chain_valid is not None else True
```

## Current Problem

Mining IS running (CPU temp proves it), but session state not visible to dashboard:
- Dashboard reads: `blockchain.get_live_mining_stats()` → all values 0
- Mining writes: `self.blockchain.mining_session['hashes_tried'] = hashes_tried`
- Both should be lock-free now, so no contention

## Next Debugging Steps

### Step 1: Verify mining_session dict is being written
Add print statement in mine_block() to confirm updates:
```python
# Around line 1072 in blockchain.py after session update
if hashes_tried % 10 == 0:  # Every 10 hashes
    print(f"DEBUG: Session updated - Nonce: {self.nonce}, Hashes: {hashes_tried}")
```

### Step 2: Verify dashboard is reading from same blockchain instance
The background mining thread gets `blockchain` passed to it. Dashboard creates its own instance.
**Check in cli.py around line 956-970** - are both using the SAME blockchain object?

### Step 3: Check for instance mismatch
```python
# In mine_with_dashboard() around line 824, add:
print(f"Mining thread blockchain id: {id(blockchain)}")

# In monitor command around line 965, add:
print(f"Dashboard blockchain id: {id(blockchain)}")
```
If IDs differ, they're separate instances - mining updates one, dashboard reads another!

### Step 4: Verify blockchain reference exists in Block
```python
# In mine_block() around line 1070, add:
if iteration == 1:
    print(f"DEBUG: hasattr blockchain? {hasattr(self, 'blockchain')}")
    if hasattr(self, 'blockchain'):
        print(f"DEBUG: blockchain.mining_session = {self.blockchain.mining_session}")
```

## Likely Root Cause

**HYPOTHESIS:** Dashboard and mining thread are using DIFFERENT blockchain instances.

Evidence:
- Mining thread gets blockchain passed from cli.py line 924: `mine_with_dashboard(blockchain, ...)`
- Dashboard creates its own blockchain at cli.py line ~965: `blockchain = SignChain(testnet=testnet)`
- These are TWO SEPARATE OBJECTS with separate mining_session dicts
- Mining updates one instance's dict, dashboard reads the other instance's dict

## Fix If Hypothesis Correct

Pass the SAME blockchain instance to both dashboard and mining thread:

```python
# Around line 820 in cli.py, BEFORE creating mining thread:
dashboard = MiningDashboard(blockchain, testnet, syndicate_mode)

# Then pass blockchain to mining thread:
mining_thread = threading.Thread(
    target=mine_with_dashboard,
    args=(blockchain, wallet, limit, safe_mode),
    daemon=True
)

# Start mining thread BEFORE dashboard.run()
mining_thread.start()

# Then run dashboard (which already has blockchain reference)
dashboard.run()
```

## Quick Test

Add this RIGHT AFTER session update in blockchain.py line ~1072:
```python
self.blockchain.mining_session['hashes_tried'] = hashes_tried
print(f"WRITE: hashes={hashes_tried}", end='\r', flush=True)
```

And in monitor.py get_current_stats() around line 393:
```python
mining_stats = self.blockchain.get_live_mining_stats()
print(f"READ: hashes={mining_stats.get('hashes_tried', 0)}", flush=True)
```

If you see WRITE incrementing but READ always 0 → **different instances confirmed**.

## Files Modified

- `/home/pi/PiSecure/pisecure/core/blockchain.py` (mining session updates, lock removal)
- `/home/pi/PiSecure/pisecure/cli.py` (background thread session init)
- `/home/pi/PiSecure/pisecure/monitor.py` (no changes yet, but may need instance fix)

## Logs to Check

- `/tmp/pisecure_mining_debug.log` - Mining thread startup
- `/tmp/pisecure_mining_heartbeat.txt` - Mining loop iterations
- `/tmp/pisecure_mining_error.log` - Any exceptions
- `/tmp/pisecure_dashboard_debug.log` - Dashboard iterations (if enabled)

## Temperature Notes

- Idle: ~64°C
- Light mining: 71-73°C (LIGHT_THROTTLE)
- Heavy mining: 76-77°C (HEAVY_THROTTLE)
- Consider cooling solution or reduce mining intensity

## Quick Resume Command

When you're back:
```bash
cd /home/pi/PiSecure
pisecure monitor --wallet pi_test --testnet
# Wait 20 seconds, if still frozen at 0:
# → Instance mismatch, implement fix above
```
