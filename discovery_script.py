#!/usr/bin/env python3
"""
PiSecure Network Discovery Script
Called by systemd timer service
"""

from pisecure.core.nat_traversal import node_discovery
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info('🔄 Running scheduled network discovery...')
    try:
        results = node_discovery.make_node_discoverable()
        if results['success_count'] > 0:
            logger.info(f'✅ Discovery successful: {results["success_count"]} methods')
            for endpoint in results.get('endpoints', []):
                logger.info(f'   📡 {endpoint.get("type", "unknown")}: {endpoint.get("ip", "unknown")}')
        else:
            logger.warning('⚠️ No discovery methods succeeded')
    except Exception as e:
        logger.error(f'❌ Discovery failed: {e}')

if __name__ == '__main__':
    main()
