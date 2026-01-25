#!/usr/bin/env python3
"""
Phase 3 WebSocket Client - Quick Test
Connects to ws://127.0.0.1:3142 and performs subscribe/ping
"""
import time
import json
import argparse
import ssl
from websocket import create_connection


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://127.0.0.1:3142")
    parser.add_argument(
        "--insecure", action="store_true", help="Disable TLS cert verification for wss"
    )
    args = parser.parse_args()

    print(f"Connecting to {args.url}...")
    sslopt = None
    if args.url.startswith("wss://") and args.insecure:
        sslopt = {"cert_reqs": ssl.CERT_NONE}
    ws = create_connection(args.url, sslopt=sslopt)
    print("Connected.")

    # Ping
    req = {"jsonrpc": "2.0", "method": "ping", "id": 1}
    ws.send(json.dumps(req))
    print("Sent ping")
    resp = ws.recv()
    print("Ping response:", resp)

    # Subscribe to bucket updates
    sub = {"jsonrpc": "2.0", "method": "subscribe", "params": ["bucket"], "id": 2}
    ws.send(json.dumps(sub))
    print("Subscribed to bucket updates")

    # Wait a bit for potential broadcasts
    print("Waiting for messages (5s)...")
    start = time.time()
    while time.time() - start < 5:
        ws.settimeout(1)
        try:
            msg = ws.recv()
            print("Received:", msg)
        except Exception:
            pass

    ws.close()
    print("Done.")


if __name__ == "__main__":
    main()
