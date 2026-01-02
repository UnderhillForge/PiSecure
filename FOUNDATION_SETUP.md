# Foundation Trust Setup Instructions

**PRIVATE - For Initial Setup Only**

## 🎯 **Foundation Trust Initialization**

### **Pre-Setup Requirements**
- [ ] Genesis block mined successfully
- [ ] API server operational on port 3142
- [ ] Genesis private key accessible
- [ ] Mining rewards accumulating

### **Step 1: Verify Genesis Key Access**
```bash
# Confirm genesis keys are accessible
ls -la pisecure/updates/
# Should show:
# -rw------- 1 user user genesis_auth_priv.key
# -rw-r--r-- 1 user user genesis_auth_pub.key

# Test key loading
python3 -c "
from pisecure.api.economics import foundation_trust
print('Genesis key loaded:', foundation_trust.genesis_private_key is not None)
print('Public key loaded:', foundation_trust.genesis_public_key is not None)
"
```

### **Step 2: Initialize Foundation Trust**
```bash
# Start API server if not running
pisecure api start

# Check foundation status (should be initialized automatically)
curl http://localhost:3142/api/v1/foundation/status

# Expected initial response:
{
  "address": "foundation_314st",
  "balance": 0,
  "funds_allocated": {"development": 0, "grants": 0, "marketing": 0, "reserve": 0},
  "active_grants": 0,
  "allocation_rules": {"development": 0.4, "grants": 0.3, "marketing": 0.15, "reserve": 0.15},
  "total_transactions": 0,
  "genesis_key_loaded": true
}
```

## 💰 **Initial Foundation Funding**

### **Option 1: Mining Donations (Recommended)**
```python
#!/usr/bin/env python3
# foundation_donation.py - Automated mining reward donations

import time
import requests
from pisecure_client import PiSecureClient

DONATION_RATE = 0.50  # Donate 50% of mining rewards

def donate_to_foundation():
    client = PiSecureClient()

    # Get current balance
    balance_response = client.get_wallet_balance('your_mining_wallet')
    if 'error' in balance_response:
        print(f"Error getting balance: {balance_response['error']}")
        return False

    balance = balance_response.get('balance', 0)
    donation_amount = balance * DONATION_RATE

    if donation_amount < 100:  # Minimum donation
        print(f"Balance too low for donation: {balance}")
        return False

    # Create donation transaction
    tx = client.create_transfer_transaction(
        'your_mining_wallet',
        'foundation_314st',
        donation_amount,
        f'Foundation donation - {donation_amount} 314ST'
    )

    # Submit transaction
    result = client.submit_transaction(tx)
    if 'transaction_hash' in result:
        print(f"Donated {donation_amount} 314ST to foundation: {result['transaction_hash']}")
        return True
    else:
        print(f"Donation failed: {result}")
        return False

# Run donation script
if __name__ == '__main__':
    while True:
        try:
            donate_to_foundation()
        except Exception as e:
            print(f"Donation error: {e}")
        time.sleep(3600)  # Check every hour
```

### **Option 2: Direct Genesis Allocation**
```bash
# Manually allocate initial foundation funds
# (Use only if mining approach is insufficient)

# Create allocation transaction
curl -X POST http://localhost:3142/api/v1/foundation/sign-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "type": "fund_allocation",
    "amount": 25000,
    "category": "reserve",
    "purpose": "Initial foundation seed funding"
  }'

# Execute the signed transaction (from the response above)
curl -X POST http://localhost:3142/api/v1/foundation/execute-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "type": "fund_allocation",
      "amount": 25000,
      "category": "reserve",
      "purpose": "Initial foundation seed funding"
    },
    "signature": "PASTE_SIGNATURE_HERE"
  }'
```

## 🏦 **Foundation Fund Management**

### **Monitor Foundation Balance**
```bash
# Real-time balance monitoring
watch -n 60 'curl -s http://localhost:3142/api/v1/foundation/status | jq .balance'

# Daily balance reports
curl http://localhost:3142/api/v1/foundation/status
```

### **Fund Allocation Process**
```bash
# Allocate funds to development category
curl -X POST http://localhost:3142/api/v1/foundation/sign-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "type": "fund_allocation",
    "amount": 50000,
    "category": "development",
    "purpose": "Protocol security audit and improvements"
  }'

# Execute allocation
curl -X POST http://localhost:3142/api/v1/foundation/execute-transaction \
  -H "Content-Type: application/json" \
  -d '{"transaction": {...}, "signature": "SIGNATURE"}'
```

### **Grant Payment Process**
```bash
# Pay approved grant
curl -X POST http://localhost:3142/api/v1/foundation/sign-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "type": "grant_payment",
    "amount": 15000,
    "grant_id": "grant_xyz789",
    "purpose": "Monthly grant payment to developer"
  }'

# Execute payment
curl -X POST http://localhost:3142/api/v1/foundation/execute-transaction \
  -H "Content-Type: application/json" \
  -d '{"transaction": {...}, "signature": "SIGNATURE"}'
```

## 📊 **Foundation Operations**

### **Daily Operations**
```bash
# Morning foundation check
curl http://localhost:3142/api/v1/foundation/status

# Review recent transactions
curl http://localhost:3142/api/v1/foundation/transactions?limit=10

# Check allocation status
curl http://localhost:3142/api/v1/foundation/status | jq .funds_allocated
```

### **Weekly Operations**
```bash
# Generate foundation report
python3 -c "
import requests
status = requests.get('http://localhost:3142/api/v1/foundation/status').json()
print('Foundation Report:')
print(f'Balance: {status[\"balance\"]} 314ST')
print(f'Allocations: {status[\"funds_allocated\"]}')
print(f'Transactions: {status[\"total_transactions\"]}')
"
```

### **Monthly Operations**
```bash
# Review allocation distribution
curl http://localhost:3142/api/v1/foundation/status

# Adjust allocation rules if needed
# (Requires governance proposal process)

# Generate financial report for board review
```

## 🗳️ **Governance Setup**

### **Create Initial Board**
```python
# Appoint initial board members (your authority)
initial_board = [
    {'name': 'Board Member 1', 'role': 'Technical Lead', 'address': 'board_addr_1'},
    {'name': 'Board Member 2', 'role': 'Community Manager', 'address': 'board_addr_2'},
    {'name': 'Board Member 3', 'role': 'Treasurer', 'address': 'board_addr_3'},
    # ... appoint 7 total
]

# Board operates under your supreme authority
# You can override any board decision
```

### **Set Up Governance Proposals**
```bash
# Create initial governance proposal
curl -X POST http://localhost:3142/api/v1/governance/create-proposal \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Initial Board Compensation Structure",
    "description": "Establish fair compensation for board members",
    "type": "governance",
    "proposed_by": "supreme_arbiter"
  }'
```

## 🔐 **Security Measures**

### **Genesis Key Protection**
- Store genesis private key offline (hardware wallet recommended)
- Never expose private key to internet-connected systems
- Use multi-signature for large transactions when possible
- Regular key backup and recovery testing

### **Foundation Transaction Security**
- All foundation transactions require genesis signature
- Transaction history is immutable and public
- Large transactions (>10k 314ST) should have board review
- Emergency protocols for key compromise

### **Access Control**
- Only you can sign foundation transactions
- Board has advisory role only
- Community can monitor but not control foundation funds
- Transparent transaction logging

## 📈 **Foundation Growth Tracking**

### **Funding Milestones**
- **Week 1**: 35,000+ 314ST (Initial funding achieved)
- **Month 1**: 100,000+ 314ST (Fully funded)
- **Month 3**: 300,000+ 314ST (Growth phase)
- **Month 6**: 600,000+ 314ST (Mature ecosystem)

### **Allocation Tracking**
```bash
# Monitor allocation distribution
curl http://localhost:3142/api/v1/foundation/status | jq '
.funds_allocated | to_entries | sort_by(.value) | reverse | .[]
| select(.value > 0) | "\(.key): \(.value) 314ST"
'
```

### **Grant Program Launch**
```bash
# Launch first grant program when foundation reaches 50k 314ST
curl -X POST http://localhost:3142/api/v1/foundation/grant \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "PiSecure Mobile SDK",
    "developer": "mobile_developer_team",
    "funding_requested": 25000,
    "milestones": ["Design", "Development", "Testing", "Release"],
    "description": "Native mobile SDK for PiSecure ecosystem"
  }'
```

## 🚨 **Emergency Procedures**

### **If Genesis Key Is Compromised**
1. Immediately pause all foundation operations
2. Generate new key pair (requires protocol upgrade)
3. Community vote on key transition
4. Implement multi-signature requirements

### **If Foundation Funds Are Low**
1. Increase mining donation rate temporarily
2. Reduce non-essential allocations
3. Activate community donation campaigns
4. Consider protocol adjustments for more fees

### **If Board Becomes Dysfunctional**
1. Appoint new board members (your authority)
2. Implement performance requirements
3. Add term limits and accountability measures
4. Consider governance structure changes

## 🎯 **Success Metrics**

### **Foundation Health**
- [ ] Balance growing through mining donations
- [ ] Funds allocated according to rules (40/30/15/15)
- [ ] Active grant program with approved projects
- [ ] Transparent transaction history
- [ ] Board operating effectively

### **Ecosystem Impact**
- [ ] Developer grants awarded and utilized
- [ ] Marketing funds driving adoption
- [ ] Development funds improving protocol
- [ ] Reserve funds available for emergencies
- [ ] Community confidence in governance

---

**This foundation setup ensures you maintain complete control over ecosystem funds while establishing transparent, accountable governance structures. The benevolent dictator model with board oversight provides both decisive leadership and professional management.**