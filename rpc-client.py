#!/usr/bin/env python3
"""
PiSecure RPC Client - JSON-RPC 2.0 Testing Tool

Tests blockchain queries, network diagnostics, and threat reporting
"""

import socket
import json
import argparse
import sys
from typing import Any, Dict, Optional


class RPCClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 3142):
        self.host = host
        self.port = port
        self.request_id = 1

    def _send_request(self, method: str, params: list = None) -> Dict[str, Any]:
        """Send JSON-RPC 2.0 request"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self.request_id,
        }
        if params:
            request["params"] = params

        self.request_id += 1

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))

            # Send HTTP POST with JSON body
            http_request = f"POST / HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n"
            http_request += "Content-Type: application/json\r\n"

            json_body = json.dumps(request)
            http_request += f"Content-Length: {len(json_body)}\r\n\r\n"
            http_request += json_body

            sock.send(http_request.encode())

            # Receive response
            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk

            sock.close()

            # Parse HTTP response - extract JSON body after headers
            response_str = response_data.decode()
            body_start = response_str.find("\r\n\r\n")
            if body_start != -1:
                json_body = response_str[body_start + 4 :].strip()
                if json_body:
                    return json.loads(json_body)

            # Try parsing without HTTP headers (in case piping/testing)
            try:
                return json.loads(response_str.strip())
            except:
                return {"error": "Invalid response format"}

        except Exception as e:
            return {"error": str(e)}

    # ===== Blockchain Queries =====
    def getblockcount(self) -> Dict[str, Any]:
        """Get blockchain height and stats"""
        return self._send_request("getblockcount")

    def getblock(self, block_hash: str) -> Dict[str, Any]:
        """Get block by hash"""
        return self._send_request("getblock", [block_hash])

    def getheader(self, height: int) -> Dict[str, Any]:
        """Get block header by height"""
        return self._send_request("getheader", [height])

    def gettransaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction by hash"""
        return self._send_request("gettransaction", [tx_hash])

    def getmempool(self) -> Dict[str, Any]:
        """Get mempool transactions"""
        return self._send_request("getmempool")

    # ===== Network Diagnostics =====
    def getpeers(self) -> Dict[str, Any]:
        """Get connected peers"""
        return self._send_request("getpeers")

    def getnetworkstats(self) -> Dict[str, Any]:
        """Get network statistics"""
        return self._send_request("getnetworkstats")

    # ===== Threat Reporting =====
    def getthreats(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get recent threats (default last hour)"""
        return self._send_request("getthreats", [time_window])

    def reportthreat(
        self, threat_type: str, ip: int, severity: float
    ) -> Dict[str, Any]:
        """Report a threat"""
        params = {"type": threat_type, "ip": ip, "severity": severity}
        return self._send_request("reportthreat", [params])

    # ===== Validator Stats =====
    def getvalidatorstats(self) -> Dict[str, Any]:
        """Get validator statistics"""
        return self._send_request("getvalidatorstats")

    def getpursestatus(self) -> Dict[str, Any]:
        """Get validator purse status"""
        return self._send_request("getpursestatus")


def print_result(name: str, result: Dict[str, Any]) -> None:
    """Pretty print RPC result"""
    print(f"\n{'='*60}")
    print(f"Method: {name}")
    print(f"{'='*60}")
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    elif "result" in result:
        print(json.dumps(result["result"], indent=2))
    else:
        print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description="PiSecure RPC Client")
    parser.add_argument("--host", default="127.0.0.1", help="RPC server host")
    parser.add_argument("--port", type=int, default=3142, help="RPC server port")
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    parser.add_argument(
        "--blockchain", action="store_true", help="Test blockchain queries"
    )
    parser.add_argument(
        "--network", action="store_true", help="Test network diagnostics"
    )
    parser.add_argument("--threats", action="store_true", help="Test threat reporting")
    parser.add_argument("--validator", action="store_true", help="Test validator stats")

    args = parser.parse_args()

    # Default to all tests if no specific test selected
    if not any(
        [args.test_all, args.blockchain, args.network, args.threats, args.validator]
    ):
        args.test_all = True

    client = RPCClient(args.host, args.port)

    try:
        if args.test_all or args.blockchain:
            print_result("getblockcount", client.getblockcount())
            print_result("getmempool", client.getmempool())

        if args.test_all or args.network:
            print_result("getnetworkstats", client.getnetworkstats())
            print_result("getpeers", client.getpeers())

        if args.test_all or args.threats:
            print_result("getthreats", client.getthreats())
            # Test threat reporting
            threat_result = client.reportthreat("suspicious_behavior", 192168001, 0.75)
            print_result("reportthreat", threat_result)

        if args.test_all or args.validator:
            print_result("getvalidatorstats", client.getvalidatorstats())
            print_result("getpursestatus", client.getpursestatus())

    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
