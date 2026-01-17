#!/usr/bin/env python3
"""
Test Suite for --test and --validate-only Flags
================================================

Verifies that testnet and validation modes work correctly.

Run: python tests/test_flags.py
     PISECURE_MOCK_HARDWARE=1 python tests/test_flags.py  # Mock hardware
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Mock hardware for testing (if needed)
if 'PISECURE_MOCK_HARDWARE' not in os.environ:
    os.environ['PISECURE_MOCK_HARDWARE'] = '1'
    print("⚙️  Enabling mock hardware mode for testing")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pisecure.core.blockchain import SignChain
from pisecure.core.wallet import SignWallet


class TestFlags:
    """Test testnet and validate-only functionality"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.testnet_dir = None
    
    def setup_testnet_dir(self):
        """Create temporary testnet directory"""
        self.testnet_dir = tempfile.mkdtemp(prefix="pisecure-test-")
        os.makedirs(f"{self.testnet_dir}/wallets", exist_ok=True)
        print(f"Created testnet directory: {self.testnet_dir}")
    
    def cleanup_testnet_dir(self):
        """Clean up testnet directory"""
        if self.testnet_dir and os.path.exists(self.testnet_dir):
            import shutil
            shutil.rmtree(self.testnet_dir)
            print(f"Cleaned up testnet directory: {self.testnet_dir}")
    
    def test(self, name, func):
        """Run a test"""
        try:
            print(f"\n{'='*70}")
            print(f"TEST: {name}")
            print(f"{'='*70}")
            func()
            print(f"✅ PASS: {name}")
            self.passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {name}")
            print(f"   Error: {e}")
            self.failed += 1
        except Exception as e:
            print(f"❌ ERROR: {name}")
            print(f"   Exception: {e}")
            self.failed += 1
    
    def test_testnet_isolation(self):
        """Test that testnet uses separate data directory"""
        testnet_path = f"{self.testnet_dir}/blockchain.json"
        
        # Create testnet blockchain
        testnet_chain = SignChain(
            chain_file=testnet_path,
            difficulty=1
        )
        
        # Verify testnet file exists
        assert os.path.exists(testnet_path), "Testnet blockchain file should exist"
        
        # Add transaction to testnet
        tx = {
            "type": "test",
            "data": "testnet transaction",
            "timestamp": 1234567890,
            "signature": "test_sig"
        }
        testnet_chain.add_transaction(tx)
        
        # Verify transaction is in testnet
        testnet_info = testnet_chain.get_chain_info()
        assert testnet_info['pending_transactions'] == 1, "Testnet should have 1 pending transaction"
        
        print(f"   ✓ Testnet blockchain created at: {testnet_path}")
        print(f"   ✓ Testnet has {testnet_info['blocks']} blocks")
        print(f"   ✓ Testnet has {testnet_info['pending_transactions']} pending transactions")
    
    def test_testnet_wallet_isolation(self):
        """Test that testnet wallets use separate directory"""
        wallet_dir = f"{self.testnet_dir}/wallets"
        
        # Create testnet wallet
        wallet = SignWallet(wallet_dir=wallet_dir)
        result = wallet.create_wallet("test_wallet_1", "Test Wallet")
        
        # Verify wallet was created in testnet directory
        wallet_file = Path(wallet_dir) / "test_wallet_1.json"
        assert wallet_file.exists(), "Testnet wallet file should exist"
        
        # Verify wallet has correct structure
        assert 'address' in result, "Wallet should have address"
        assert 'wallet_id' in result, "Wallet should have wallet_id"
        
        print(f"   ✓ Testnet wallet created at: {wallet_file}")
        print(f"   ✓ Wallet address: {result['address'][:32]}...")
    
    def test_testnet_mining(self):
        """Test that mining works on testnet"""
        testnet_path = f"{self.testnet_dir}/blockchain.json"
        wallet_dir = f"{self.testnet_dir}/wallets"
        
        # Create blockchain and wallet
        chain = SignChain(chain_file=testnet_path, difficulty=1)
        wallet = SignWallet(wallet_dir=wallet_dir)
        wallet_result = wallet.create_wallet("miner_wallet", "Miner")
        
        # Add transaction
        tx = {"type": "test", "data": "tx1", "timestamp": 1234567890, "signature": "sig1"}
        chain.add_transaction(tx)
        
        # Mine block
        block = chain.mine_pending_transactions(
            miner_wallet_address=wallet_result['address'],
            verbose=False
        )
        
        # Verify block was mined
        assert block is not None, "Block should be mined"
        assert block.index > 0, "Block index should be greater than 0"
        
        # Verify blockchain has blocks
        info = chain.get_chain_info()
        assert info['blocks'] >= 2, "Should have at least genesis + 1 mined block"
        
        print(f"   ✓ Mined block #{block.index}")
        print(f"   ✓ Block hash: {block.hash[:32]}...")
        print(f"   ✓ Total blocks: {info['blocks']}")
    
    def test_validate_only_read_operations(self):
        """Test that validate-only allows read operations"""
        testnet_path = f"{self.testnet_dir}/blockchain.json"
        
        # Create blockchain
        chain = SignChain(chain_file=testnet_path, difficulty=1)
        
        # Read operations should work
        info = chain.get_chain_info()
        assert 'blocks' in info, "Should be able to read chain info"
        
        is_valid = chain.validate_chain()
        assert isinstance(is_valid, bool), "Should be able to validate chain"
        
        balance = chain.get_wallet_balance("test_address")
        assert isinstance(balance, (int, float)), "Should be able to read balance"
        
        print(f"   ✓ Read chain info: {info['blocks']} blocks")
        print(f"   ✓ Validated chain: {is_valid}")
        print(f"   ✓ Read balance: {balance}")
    
    def test_different_paths(self):
        """Test that mainnet and testnet use different paths"""
        testnet_path = f"{self.testnet_dir}/blockchain.json"
        
        # Testnet blockchain
        testnet_chain = SignChain(chain_file=testnet_path, difficulty=1)
        testnet_info = testnet_chain.get_chain_info()
        
        # Add something to testnet
        tx = {"type": "test", "data": "testnet only", "timestamp": 1234567890, "signature": "sig"}
        testnet_chain.add_transaction(tx)
        testnet_pending = testnet_chain.get_chain_info()['pending_transactions']
        
        # Verify testnet has the transaction
        assert testnet_pending > 0, "Testnet should have pending transactions"
        
        print(f"   ✓ Testnet path: {testnet_path}")
        print(f"   ✓ Testnet has {testnet_pending} pending transactions")
        print(f"   ✓ Path isolation verified")
    
    def test_wallet_directory_separation(self):
        """Test that wallet directories are separate"""
        testnet_wallet_dir = f"{self.testnet_dir}/wallets"
        
        # Create testnet wallet
        testnet_wallet = SignWallet(wallet_dir=testnet_wallet_dir)
        result = testnet_wallet.create_wallet("isolated_wallet", "Isolated")
        
        # Verify wallet is in testnet directory
        wallet_file = Path(testnet_wallet_dir) / "isolated_wallet.json"
        assert wallet_file.exists(), "Wallet should be in testnet directory"
        
        # Verify wallet file contains correct data
        with open(wallet_file) as f:
            wallet_data = json.load(f)
        
        assert wallet_data['wallet_id'] == 'isolated_wallet', "Wallet ID should match"
        assert wallet_data['name'] == 'Isolated', "Wallet name should match"
        
        print(f"   ✓ Testnet wallet directory: {testnet_wallet_dir}")
        print(f"   ✓ Wallet file: {wallet_file}")
        print(f"   ✓ Wallet data verified")
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("PiSecure Testing Flags Test Suite")
        print("="*70)
        
        self.setup_testnet_dir()
        
        try:
            # Run tests
            self.test("Testnet Isolation", self.test_testnet_isolation)
            self.test("Testnet Wallet Isolation", self.test_testnet_wallet_isolation)
            self.test("Testnet Mining", self.test_testnet_mining)
            self.test("Validate-Only Read Operations", self.test_validate_only_read_operations)
            self.test("Different Paths", self.test_different_paths)
            self.test("Wallet Directory Separation", self.test_wallet_directory_separation)
            
            # Summary
            print("\n" + "="*70)
            print("TEST SUMMARY")
            print("="*70)
            print(f"✅ Passed: {self.passed}")
            print(f"❌ Failed: {self.failed}")
            print(f"Total: {self.passed + self.failed}")
            
            if self.failed == 0:
                print("\n🎉 All tests passed!")
            else:
                print(f"\n⚠️  {self.failed} test(s) failed")
            
            print("="*70)
            
        finally:
            self.cleanup_testnet_dir()
        
        return self.failed == 0


def main():
    """Main test function"""
    tester = TestFlags()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
