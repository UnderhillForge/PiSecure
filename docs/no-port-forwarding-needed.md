# Do I Need Port Forwarding for PiSecure?

## Quick Answer: NO! 🎉

You can mine and validate PiSecure tokens **without any router configuration**, just like Bitcoin, Ethereum, and other cryptocurrencies.

## How It Works

### Outbound-Only Mode (Default)
Your PiSecure node:
- ✅ Connects to other nodes
- ✅ Downloads and syncs the blockchain
- ✅ Mines new blocks and validates transactions
- ✅ Broadcasts transactions to the network
- ✅ Earns mining/validation rewards

**No port forwarding required!**

### What You're Missing (Optional)
Without incoming connections:
- ❌ Other nodes can't sync from you
- ❌ Won't help seed the network
- ❌ Slightly fewer peer connections (but plenty for mining)

**Think of it like BitTorrent**: You can download (leech) without seeding, but seeding helps the network.

## Automatic Upgrades

PiSecure tries these methods automatically (no config needed):

1. **UPnP Auto-Configuration**: Works on 60% of home routers
2. **Relay Network**: Routes through community nodes
3. **Outbound-Only**: Guaranteed fallback that always works

## Want to Help the Network? (Optional)

If you want to enable incoming connections for full node mode:

### Option 1: Enable UPnP (Easiest)
Most modern routers have UPnP:
- Router admin → Advanced → UPnP: **Enabled**
- Restart PiSecure node
- Done! ✅

### Option 2: Manual Port Forward (5 minutes)
Router admin panel → Port Forwarding:
```
External Port: 3142
Internal IP: <your Pi's IP, e.g., 192.168.1.50>
Internal Port: 3142
Protocol: TCP
```

### Option 3: Do Nothing
Outbound-only mode works perfectly for mining/validation!

## How Other Cryptos Handle This

| Network | Default Behavior |
|---------|------------------|
| Bitcoin | Outbound-only works, incoming optional for full node |
| Ethereum | Outbound-only works, incoming improves peer count |
| Monero | Outbound-only works, incoming helps network |
| **PiSecure** | **Same as above - outbound-only is fully functional** |

## Security Note

**Incoming connections disabled = More secure!**
- Reduces attack surface
- No exposed services from internet
- Perfect for home miners

## Checking Your Mode

When starting the API server or mining dashboard, look for:

```
📡 Node Mode: Outbound-Only (incoming connections disabled)
```
or
```
📡 Node Mode: Full Node (incoming connections enabled)
🌐 Discovered public IP: x.x.x.x via UPnP
```

## Common Questions

### "My node shows 'outbound-only' - is that bad?"
No! Your node works perfectly. You can mine, validate, and earn rewards.

### "Do I need a static IP?"
No. Dynamic IPs work fine with UPnP or relay network.

### "What about IPv6?"
Planned for future releases. IPv6 makes this even easier (no NAT!).

### "Can I disable incoming connections intentionally?"
Yes! Set `PISECURE_LISTEN_MODE=outbound-only` environment variable.

### "Will this affect my mining rewards?"
No. Mining rewards depend on solving blocks, not network connectivity.

## Comparison to Traditional Mining Pools

Traditional pools require you to connect to them (outbound), not the other way around. PiSecure works the same way - you connect to the network, not vice versa.

## Technical Details

For the curious:
- PiSecure uses **active peer discovery** via bootstrap nodes
- Maintains **8-16 outbound connections** by default
- Uses **gossip protocol** for transaction/block propagation
- Bootstrap nodes have incoming connections enabled
- Light clients work via **client-server model** for API queries

## Summary

✅ **Just start mining** - port forwarding is optional  
✅ **Automatic UPnP** tries to configure itself  
✅ **Outbound-only mode** is fully functional  
✅ **Same as Bitcoin/Ethereum** - no special requirements  

Port forwarding is for **advanced users who want to help the network**, not a requirement for mining!
