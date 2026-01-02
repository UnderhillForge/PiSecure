#!/usr/bin/env python3
"""
PiSecure Python Client Examples - Non-Financial Use Cases
========================================================

Examples of using PiSecure blockchain for applications that don't require
wallets or token balances. These focus on data immutability, verification,
and decentralized record-keeping.
"""

import time
import json
import hashlib
from typing import Dict, Any, List

# Assuming PiSecure client is available
from pisecure_client import PiSecureClient


class SupplyChainTracker:
    """Track products through supply chain without financial transactions."""

    def __init__(self):
        self.client = PiSecureClient()

    def record_product_creation(self, product_id: str, manufacturer: str,
                               product_type: str, specifications: Dict[str, Any]) -> str:
        """Record when a product is first created/manufactured."""
        data = {
            "event_type": "product_creation",
            "product_id": product_id,
            "manufacturer": manufacturer,
            "product_type": product_type,
            "specifications": specifications,
            "creation_timestamp": int(time.time()),
            "location": "Manufacturing Facility A"
        }

        tx = {
            "type": "supply_chain_event",
            "data": data,
            "signature": "",  # Would be signed by manufacturer
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)

    def record_quality_inspection(self, product_id: str, inspector: str,
                                test_results: Dict[str, Any]) -> str:
        """Record quality control inspection results."""
        data = {
            "event_type": "quality_inspection",
            "product_id": product_id,
            "inspector": inspector,
            "test_results": test_results,
            "passed": all(test_results.values()),  # Simple pass/fail logic
            "inspection_timestamp": int(time.time())
        }

        tx = {
            "type": "supply_chain_event",
            "data": data,
            "signature": "",  # Would be signed by inspector
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)

    def record_shipment(self, product_id: str, from_location: str,
                       to_location: str, carrier: str) -> str:
        """Record product shipment between locations."""
        data = {
            "event_type": "shipment",
            "product_id": product_id,
            "from_location": from_location,
            "to_location": to_location,
            "carrier": carrier,
            "shipment_timestamp": int(time.time())
        }

        tx = {
            "type": "supply_chain_event",
            "data": data,
            "signature": "",  # Would be signed by carrier
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)


class IoTDataCollector:
    """Collect and store IoT sensor data on blockchain."""

    def __init__(self):
        self.client = PiSecureClient()

    def submit_sensor_reading(self, device_id: str, sensor_type: str,
                            value: float, unit: str, location: str = None) -> str:
        """Submit a sensor reading to the blockchain."""
        data = {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "location": location,
            "timestamp": int(time.time()),
            "reading_id": hashlib.sha256(f"{device_id}{sensor_type}{time.time()}".encode()).hexdigest()[:16]
        }

        tx = {
            "type": "sensor_reading",
            "data": data,
            "signature": "",  # Would be signed by device
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)

    def submit_environmental_data(self, station_id: str, readings: Dict[str, Any]) -> str:
        """Submit comprehensive environmental monitoring data."""
        data = {
            "station_id": station_id,
            "readings": readings,
            "timestamp": int(time.time()),
            "data_quality_score": self._calculate_data_quality(readings)
        }

        tx = {
            "type": "environmental_data",
            "data": data,
            "signature": "",  # Would be signed by monitoring station
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)

    def _calculate_data_quality(self, readings: Dict[str, Any]) -> float:
        """Calculate data quality score based on reading consistency."""
        # Simple quality calculation - in real implementation would be more sophisticated
        if all(isinstance(v, (int, float)) for v in readings.values()):
            return 1.0
        return 0.8


class DocumentTimestampingService:
    """Timestamp documents and digital content."""

    def __init__(self):
        self.client = PiSecureClient()

    def timestamp_document(self, document_hash: str, document_name: str,
                         author: str, content_type: str = "document") -> str:
        """Create an immutable timestamp for a document."""
        data = {
            "content_hash": document_hash,
            "document_name": document_name,
            "author": author,
            "content_type": content_type,
            "timestamp": int(time.time()),
            "blockchain_timestamp": int(time.time())
        }

        tx = {
            "type": "document_timestamp",
            "data": data,
            "signature": "",  # Would be signed by timestamping service
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)

    def timestamp_research_data(self, research_id: str, dataset_hash: str,
                              researcher: str, methodology: str) -> str:
        """Timestamp research data and methodology."""
        data = {
            "research_id": research_id,
            "dataset_hash": dataset_hash,
            "researcher": researcher,
            "methodology": methodology,
            "timestamp": int(time.time()),
            "data_integrity_verified": True
        }

        tx = {
            "type": "research_timestamp",
            "data": data,
            "signature": "",  # Would be signed by research institution
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)


class AuditLogger:
    """Create tamper-proof audit logs for systems and applications."""

    def __init__(self):
        self.client = PiSecureClient()

    def log_security_event(self, event_type: str, severity: str,
                         description: str, source_system: str,
                         user_id: str = None, ip_address: str = None) -> str:
        """Log a security event to the blockchain."""
        data = {
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "source_system": source_system,
            "user_id": user_id,
            "ip_address": ip_address,
            "timestamp": int(time.time()),
            "event_id": hashlib.sha256(f"{source_system}{event_type}{time.time()}".encode()).hexdigest()[:16]
        }

        tx = {
            "type": "security_audit",
            "data": data,
            "signature": "",  # Would be signed by logging system
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)

    def log_system_change(self, change_type: str, component: str,
                        old_version: str, new_version: str,
                        change_reason: str, operator: str) -> str:
        """Log system configuration changes."""
        data = {
            "change_type": change_type,
            "component": component,
            "old_version": old_version,
            "new_version": new_version,
            "change_reason": change_reason,
            "operator": operator,
            "timestamp": int(time.time()),
            "change_id": hashlib.sha256(f"{component}{change_type}{time.time()}".encode()).hexdigest()[:16]
        }

        tx = {
            "type": "system_change",
            "data": data,
            "signature": "",  # Would be signed by system administrator
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)


class ContentVerificationService:
    """Verify authenticity and ownership of digital content."""

    def __init__(self):
        self.client = PiSecureClient()

    def register_content(self, content_hash: str, title: str, creator: str,
                        content_type: str, metadata: Dict[str, Any] = None) -> str:
        """Register digital content on the blockchain."""
        data = {
            "content_hash": content_hash,
            "title": title,
            "creator": creator,
            "content_type": content_type,
            "metadata": metadata or {},
            "registration_timestamp": int(time.time()),
            "content_id": hashlib.sha256(f"{creator}{content_hash}".encode()).hexdigest()[:16]
        }

        tx = {
            "type": "content_registration",
            "data": data,
            "signature": "",  # Would be signed by content creator
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)

    def verify_content_authenticity(self, content_hash: str) -> Dict[str, Any]:
        """Verify if content hash exists on blockchain and get metadata."""
        # This would search blockchain transactions for the content hash
        # For demonstration, we'll show how to query recent transactions

        # In practice, you'd need to search through blockchain history
        # This is a simplified example
        try:
            # Get recent transactions and search for content registration
            recent_tx = []  # Would be populated from blockchain queries

            for tx in recent_tx:
                if tx.get("type") == "content_registration":
                    tx_data = tx.get("data", {})
                    if tx_data.get("content_hash") == content_hash:
                        return {
                            "authentic": True,
                            "registration_data": tx_data,
                            "blockchain_timestamp": tx.get("timestamp"),
                            "transaction_hash": tx.get("hash")
                        }

            return {"authentic": False, "reason": "Content not found on blockchain"}

        except Exception as e:
            return {"authentic": False, "reason": f"Verification failed: {str(e)}"}


class VotingSystem:
    """Record votes and election results on blockchain."""

    def __init__(self):
        self.client = PiSecureClient()

    def record_vote(self, election_id: str, voter_id_hash: str,
                   candidate_id: str, voting_station: str) -> str:
        """Record an anonymous vote (voter ID is hashed for privacy)."""
        data = {
            "election_id": election_id,
            "voter_id_hash": voter_id_hash,  # Hashed for privacy
            "candidate_id": candidate_id,
            "voting_station": voting_station,
            "vote_timestamp": int(time.time()),
            "vote_id": hashlib.sha256(f"{election_id}{voter_id_hash}{time.time()}".encode()).hexdigest()[:16]
        }

        tx = {
            "type": "vote_record",
            "data": data,
            "signature": "",  # Would be signed by voting system
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)

    def record_election_result(self, election_id: str, results: Dict[str, Any],
                             audit_info: Dict[str, Any]) -> str:
        """Record final election results with audit trail."""
        data = {
            "election_id": election_id,
            "results": results,
            "audit_info": audit_info,
            "result_timestamp": int(time.time()),
            "total_votes_counted": sum(results.values()) if isinstance(results, dict) else 0
        }

        tx = {
            "type": "election_result",
            "data": data,
            "signature": "",  # Would be signed by election authority
            "timestamp": int(time.time())
        }

        return self.client.submit_transaction(tx)


# Example usage
if __name__ == "__main__":
    # Supply chain example
    tracker = SupplyChainTracker()

    # Record product creation
    product_tx = tracker.record_product_creation(
        product_id="WIDGET-001",
        manufacturer="Acme Corp",
        product_type="Industrial Widget",
        specifications={"weight": "5kg", "dimensions": "30x20x15cm", "material": "steel"}
    )
    print(f"Product created: {product_tx}")

    # IoT data collection
    collector = IoTDataCollector()

    # Submit temperature reading
    sensor_tx = collector.submit_sensor_reading(
        device_id="TEMP-001",
        sensor_type="temperature",
        value=23.5,
        unit="celsius",
        location="Warehouse A"
    )
    print(f"Temperature reading submitted: {sensor_tx}")

    # Document timestamping
    timestamp_service = DocumentTimestampingService()

    # Timestamp a legal document
    doc_hash = hashlib.sha256(b"Legal document content").hexdigest()
    doc_tx = timestamp_service.timestamp_document(
        document_hash=doc_hash,
        document_name="Service Agreement.pdf",
        author="Legal Department",
        content_type="legal_contract"
    )
    print(f"Document timestamped: {doc_tx}")

    # Audit logging
    auditor = AuditLogger()

    # Log security event
    audit_tx = auditor.log_security_event(
        event_type="login_attempt",
        severity="medium",
        description="Failed login attempt from unknown IP",
        source_system="web_server",
        ip_address="192.168.1.100"
    )
    print(f"Security event logged: {audit_tx}")

    # Content verification
    content_service = ContentVerificationService()

    # Register digital art
    art_hash = hashlib.sha256(b"Digital artwork data").hexdigest()
    art_tx = content_service.register_content(
        content_hash=art_hash,
        title="Digital Landscape #42",
        creator="Artist Name",
        content_type="digital_art",
        metadata={"medium": "digital", "year": 2024, "technique": "AI_generated"}
    )
    print(f"Content registered: {art_tx}")

    # Voting system
    voting = VotingSystem()

    # Record anonymous vote
    voter_hash = hashlib.sha256(b"voter_ssn_or_id").hexdigest()
    vote_tx = voting.record_vote(
        election_id="PRES-2024",
        voter_id_hash=voter_hash,
        candidate_id="CANDIDATE_A",
        voting_station="Precinct_001"
    )
    print(f"Vote recorded: {vote_tx}")

    print("\nAll examples completed successfully!")
    print("These demonstrate PiSecure's capabilities for non-financial blockchain applications.")