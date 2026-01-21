#!/usr/bin/env python3
"""
Test script for MetaMask integration
Tests the frontend JavaScript and backend API endpoints
"""

import json
import os
import sys

# Add PiSecure to path
sys.path.insert(0, os.path.dirname(__file__))

def test_metamask_js_exists():
    """Test that MetaMask JavaScript file exists"""
    js_file = "dashboard/web/static/js/metamask.js"
    if not os.path.exists(js_file):
        print(f"❌ FAIL: {js_file} does not exist")
        return False
    
    print(f"✅ PASS: {js_file} exists")
    
    # Check file size
    size = os.path.getsize(js_file)
    print(f"   File size: {size} bytes")
    
    # Check for key functions
    with open(js_file, 'r') as f:
        content = f.read()
        
    required_functions = [
        'MetamaskIntegration',
        'connect',
        'signMessage',
        'getBalance',
        'registerWalletWithPiSecure'
    ]
    
    for func in required_functions:
        if func in content:
            print(f"   ✓ Function '{func}' found")
        else:
            print(f"   ✗ Function '{func}' NOT found")
            return False
    
    return True


def test_wallet_html_metamask():
    """Test that wallets.html includes MetaMask integration"""
    html_file = "dashboard/web/templates/wallets.html"
    if not os.path.exists(html_file):
        print(f"❌ FAIL: {html_file} does not exist")
        return False
    
    with open(html_file, 'r') as f:
        content = f.read()
    
    # Check for MetaMask script inclusion
    if 'metamask.js' not in content:
        print(f"❌ FAIL: metamask.js not included in {html_file}")
        return False
    
    print(f"✅ PASS: metamask.js included in {html_file}")
    
    # Check for MetaMask UI elements
    required_elements = [
        'metamask-connect-btn',
        'metamask-status',
        'metamask-account',
        'MetaMask Wallet'
    ]
    
    for element in required_elements:
        if element in content:
            print(f"   ✓ Element '{element}' found")
        else:
            print(f"   ✗ Element '{element}' NOT found")
            return False
    
    return True


def test_api_endpoint_in_app():
    """Test that API endpoint is added to app.py"""
    app_file = "dashboard/web/app.py"
    if not os.path.exists(app_file):
        print(f"❌ FAIL: {app_file} does not exist")
        return False
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Check for MetaMask API endpoint
    if '/api/wallets/metamask/link' not in content:
        print(f"❌ FAIL: MetaMask API endpoint not found in {app_file}")
        return False
    
    print(f"✅ PASS: MetaMask API endpoint found in {app_file}")
    
    # Check for endpoint function
    if 'api_wallet_metamask_link' in content:
        print(f"   ✓ API function 'api_wallet_metamask_link' found")
    else:
        print(f"   ✗ API function 'api_wallet_metamask_link' NOT found")
        return False
    
    # Check for address validation
    if 'Invalid MetaMask address format' in content:
        print(f"   ✓ Address validation found")
    else:
        print(f"   ✗ Address validation NOT found")
        return False
    
    return True


def test_metamask_storage_directory():
    """Test that MetaMask storage directory can be created"""
    import tempfile
    from pathlib import Path
    
    # Create a temporary test directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "metamask"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        if test_dir.exists():
            print(f"✅ PASS: MetaMask storage directory can be created")
            
            # Test writing a sample wallet file
            test_wallet = {
                'wallet_id': 'metamask_test1234',
                'name': 'Test MetaMask Wallet',
                'metamask_address': '0x1234567890123456789012345678901234567890',
                'chain_id': '0x1',
                'wallet_type': 'metamask'
            }
            
            test_file = test_dir / "test_wallet.json"
            with open(test_file, 'w') as f:
                json.dump(test_wallet, f, indent=2)
            
            if test_file.exists():
                print(f"   ✓ Test wallet file created successfully")
                
                # Read it back
                with open(test_file, 'r') as f:
                    loaded_wallet = json.load(f)
                
                if loaded_wallet['metamask_address'] == test_wallet['metamask_address']:
                    print(f"   ✓ Wallet data read back correctly")
                    return True
                else:
                    print(f"   ✗ Wallet data mismatch")
                    return False
            else:
                print(f"   ✗ Test wallet file NOT created")
                return False
        else:
            print(f"❌ FAIL: MetaMask storage directory NOT created")
            return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("MetaMask Integration Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        ("MetaMask JavaScript Module", test_metamask_js_exists),
        ("Wallet HTML Integration", test_wallet_html_metamask),
        ("API Endpoint Integration", test_api_endpoint_in_app),
        ("Storage Directory", test_metamask_storage_directory)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        print("-" * 60)
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ FAIL: Exception occurred: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
