# C++ Module Segfault Debugging Guide

## Issue Summary
The PiHash C++ module experiences a segmentation fault when calling `compute()` or `compute_pihash()`, even in the original unmodified code from HEAD.

## Test Case to Reproduce
```python
import sys
sys.path.insert(0, '/home/pi/PiSecure/build')
import pisecure.pisecure_cpp_pihash as pihash

pi = pihash.PiHash(1, 1, False)
result = pihash.compute_pihash([0xaa], 0)  # ← Segmentation fault here
```

## Segfault Characteristics
- **Occurs**: Inside `PiHash::Compute()` function
- **Stack Location**: Unknown (no Python exception, raw segfault)
- **Module State**: Creation succeeds, only computation fails
- **Not VideoCore Related**: Exists in original code before VideoCore changes

## Affected Functions
- `pi.compute([data], nonce, None)`
- `pihash.compute_pihash([data], nonce=0, rounds=8, memory_mb=256)`
- `pihash.mine_block([data], difficulty)`

## Likely Causes (in priority order)

### 1. Memory-Hard Mixing Function
**File**: `cpp/hw/pihash.cpp` - `MemoryHardMix()` function
**Risk**: Accessing uninitialized memory buffer
**Check**: 
- Verify buffer allocation and bounds
- Check loop indexes don't exceed buffer size
- Ensure memory_bytes_ is properly initialized

### 2. SHA256 Implementation
**File**: `cpp/crypto/sha256.cpp`
**Risk**: Buffer overflow or invalid memory access in sha256()
**Check**:
- Verify sha256_ctx structures are properly zero-initialized
- Check padding and block processing loops
- Look for off-by-one errors in buffer indexing

### 3. pybind11 Type Conversion
**File**: `cpp/bindings/pybind_pihash.cpp`
**Risk**: Incorrect C++ ↔ Python marshalling
**Check**:
- Verify std::vector<uint8_t> conversion from Python list
- Check HardwareFingerprint struct field types
- Ensure nullptr is properly handled for optional fingerprint

### 4. Uninitialized Member Variables
**Location**: `PiHash::Compute()` or constructor
**Risk**: Using uninitialized pointers or buffers
**Check**:
- Verify all member variables initialized in constructor
- Check cached_fingerprint_ usage
- Verify memory_bytes_ calculation

## Debugging Steps

### Step 1: Run with GDB
```bash
cd /home/pi/PiSecure/build
gdb --args python3 -c "
import sys; sys.path.insert(0, '.'); 
import pisecure.pisecure_cpp_pihash as pihash;
pihash.compute_pihash([0xaa], 0)
"
(gdb) run
(gdb) bt  # Full backtrace
(gdb) info registers
```

### Step 2: Run with Valgrind
```bash
cd /home/pi/PiSecure/build
valgrind --leak-check=full --show-leak-kinds=all python3 -c "
import sys; sys.path.insert(0, '.'); 
import pisecure.pisecure_cpp_pihash as pihash;
pihash.compute_pihash([0xaa], 0)
"
```

### Step 3: Add Debug Output
Insert logging in `cpp/hw/pihash.cpp`:
```cpp
std::string PiHash::Compute(const std::vector<uint8_t>& data, uint32_t nonce, ...) {
    std::cerr << "DEBUG: Compute() entry, data size=" << data.size() << std::endl;
    
    HardwareFingerprint hw_fp;
    if (fingerprint == nullptr) {
        std::cerr << "DEBUG: Calling GetHardwareFingerprint()" << std::endl;
        hw_fp = GetHardwareFingerprint();
        std::cerr << "DEBUG: GetHardwareFingerprint() returned" << std::endl;
    }
    
    // ... continue with debug output at each step
}
```

### Step 4: Isolate the Problem Function
Create minimal test executable that calls only one function at a time:
```cpp
// test_sha256_only.cpp
#include "cpp/crypto/sha256.h"
#include <iostream>
int main() {
    uint8_t data[] = {0xaa, 0xbb};
    uint8_t hash[32];
    pisecure::crypto::sha256(data, 2, hash);
    return 0;
}
```

## Common Segfault Patterns

### Pattern 1: Uninitialized Pointer
```cpp
// BAD: mailbox_ptr_ not initialized
void MailboxWait() {
    volatile uint32_t* status = mailbox_ptr_ + 6;  // If mailbox_ptr_ is garbage
    if (!(*status & mask)) return;  // SEGFAULT
}

// GOOD:
void MailboxWait() {
    if (!mailbox_ptr_) return;  // Check first
    volatile uint32_t* status = mailbox_ptr_ + 6;
    if (!(*status & mask)) return;
}
```

### Pattern 2: Buffer Overflow
```cpp
// BAD: No bounds check
for (int i = 0; i < huge_number; i++) {
    buffer[i] = data[i];  // buffer might be small
}

// GOOD:
for (int i = 0; i < std::min(buffer_size, data_size); i++) {
    buffer[i] = data[i];
}
```

### Pattern 3: Use-After-Free
```cpp
// BAD: Using deleted memory
HardwareFingerprint fp;
HardwareFingerprint* ptr = &fp;
{ 
    // fp scope ends here
}
ptr->cpu_serial;  // SEGFAULT - fp was stack-allocated
```

## Recommended Action Items

1. **Immediate**: Run with GDB to get backtrace
2. **Follow-up**: Compare memory access patterns to similar working code
3. **Verify**: Check all array/vector access for bounds
4. **Test**: Create minimal reproducers for each function
5. **Fix**: Apply minimal fix to restore runtime functionality

## Files to Examine
- `cpp/hw/pihash.cpp` - Main logic
- `cpp/hw/pihash.h` - Structure definitions
- `cpp/crypto/sha256.cpp` - Hash implementation
- `cpp/crypto/sha256.h` - Hash interface
- `cpp/bindings/pybind_pihash.cpp` - Python bindings

## Expected GDB Output Pattern
```
#0  0x... in <function_name> () from /home/pi/PiSecure/build/pisecure/pisecure_cpp_pihash.cpython-313-aarch64-linux-gnu.so
#1  0x... in <calling_function> () from ...
#2  0x... in <pybind11_wrapper> () from ...
#3  0x... in <python_interpreter> () from ...
...
```

The "#0" line will indicate the exact function causing the crash.

---

**Note**: This is a pre-existing issue unrelated to VideoCore integration. VideoCore mailbox code compiles cleanly and has proper error handling.
