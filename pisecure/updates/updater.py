"""
PiSecure OTA Updater
====================

Main OTA update orchestrator that coordinates verification, fetching,
installation, and rollback operations for secure over-the-air updates.
"""

import time
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from .verifier import UpdateVerifier
from .fetcher import UpdateFetcher
from .rollback import RollbackManager
from .auth import UpdateAuthority, UpdateSigner
from .update_classifier import UpdateClassifier, DependencyManager, UpdateType


class OTAUpdater:
    """Main OTA update orchestrator"""

    def __init__(self, blockchain=None):
        self.blockchain = blockchain

        # Initialize components
        self.verifier = UpdateVerifier()
        self.fetcher = UpdateFetcher(blockchain=blockchain)
        self.rollback = RollbackManager()
        self.authority = UpdateAuthority(blockchain=blockchain)

        # Update state
        self.current_update = None
        self.update_log = []

    def check_for_updates(self, current_version: str) -> List[Dict[str, Any]]:
        """
        Check for available updates

        Args:
            current_version: Current software version

        Returns:
            List of available updates
        """
        available_updates = []

        try:
            # Query blockchain for update registrations
            if self.blockchain:
                for block in reversed(self.blockchain.chain[-50:]):  # Last 50 blocks
                    for tx in block.transactions:
                        if tx.get('type') == 'update_registration':
                            update_info = tx.copy()
                            update_info['block_height'] = block.index
                            update_info['confirmed_at'] = block.timestamp

                            # Check version compatibility
                            update_version = update_info.get('version', '')
                            if self._is_version_newer(update_version, current_version):
                                available_updates.append(update_info)

            # Remove duplicates (keep latest)
            seen_hashes = set()
            unique_updates = []
            for update in sorted(available_updates, key=lambda x: x.get('timestamp', 0), reverse=True):
                update_hash = update.get('update_hash')
                if update_hash and update_hash not in seen_hashes:
                    seen_hashes.add(update_hash)
                    unique_updates.append(update)

            return unique_updates[:10]  # Return latest 10 updates

        except Exception as e:
            print(f"Failed to check for updates: {e}")
            return []

    def _is_version_newer(self, new_version: str, current_version: str) -> bool:
        """Compare version strings"""
        try:
            def parse_version(v):
                # Remove pre-release and build metadata
                v = v.split('-')[0].split('+')[0]
                return tuple(map(int, v.split('.')))

            new_parts = parse_version(new_version)
            current_parts = parse_version(current_version)

            return new_parts > current_parts

        except:
            # Fallback: string comparison
            return new_version > current_version

    def download_update(self, update_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download update package

        Args:
            update_info: Update information from blockchain

        Returns:
            Download result
        """
        try:
            update_hash = update_info.get('update_hash') or update_info.get('ipfs_hash')
            if not update_hash:
                return {
                    'success': False,
                    'error': 'No update hash found'
                }

            print(f"📥 Downloading update: {update_hash}")

            # Try to fetch the update
            result = self.fetcher.fetch_update(
                update_hash,
                expected_size=update_info.get('size')
            )

            if result['fetched']:
                print(f"✅ Update downloaded: {result['size']} bytes")
                return {
                    'success': True,
                    'local_path': result['local_path'],
                    'size': result['size'],
                    'source': result.get('source'),
                    'update_info': update_info
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Download failed'),
                    'update_info': update_info
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'update_info': update_info
            }

    def verify_update(self, package_path: str, update_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify downloaded update package and authorization

        Args:
            package_path: Path to downloaded package
            update_info: Update information

        Returns:
            Verification result
        """
        try:
            print(f"🔍 Verifying update package: {package_path}")

            # Step 1: Verify package signature and integrity
            verification = self.verifier.verify_package(package_path)

            if not verification['verified']:
                print(f"❌ Package verification failed: {verification.get('error')}")
                return {
                    'verified': False,
                    'error': verification.get('error'),
                    'stage': verification.get('stage'),
                    'verification_details': verification
                }

            manifest = verification['manifest']
            print("✅ Package verification successful")
            print(f"   Version: {manifest.get('version')}")
            print(f"   Publisher: {manifest.get('publisher', 'unknown')}")

            # Step 2: Verify update authorization
            signatures = manifest.get('signatures', [])
            if not signatures:
                return {
                    'verified': False,
                    'error': 'No authorization signatures found',
                    'stage': 'authorization',
                    'manifest': manifest
                }

            print(f"🔐 Checking authorization ({len(signatures)} signature(s))...")
            auth_result = self.authority.verify_update_signature(manifest, signatures)

            if not auth_result['authorized']:
                print(f"❌ Authorization failed: {auth_result.get('error', 'Unknown error')}")
                return {
                    'verified': False,
                    'error': f'Authorization failed: {auth_result.get("error", "Unknown error")}',
                    'stage': 'authorization',
                    'auth_details': auth_result,
                    'manifest': manifest
                }

            print("✅ Authorization verified")
            print(f"   Valid signatures: {auth_result['valid_signatures']}/{auth_result['total_signatures_checked']}")
            print(f"   Authorized signers: {', '.join(auth_result['authorized_signers'])}")

            return {
                'verified': True,
                'authorized': True,
                'manifest': manifest,
                'auth_details': auth_result,
                'verification_details': verification
            }

        except Exception as e:
            print(f"❌ Verification error: {e}")
            return {
                'verified': False,
                'error': str(e)
            }

    def apply_update(self, package_path: str, manifest: Dict[str, Any],
                    progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Apply the verified update

        Args:
            package_path: Path to update package
            manifest: Verified update manifest
            progress_callback: Optional progress callback function

        Returns:
            Update result
        """
        try:
            self.current_update = {
                'package_path': package_path,
                'manifest': manifest,
                'start_time': time.time(),
                'status': 'applying'
            }

            print("🔄 Applying update...")
            print(f"   Version: {manifest.get('version')}")
            print(f"   Description: {manifest.get('description', 'No description')}")

            # Create backup before applying
            current_version = self._get_current_version()
            backup_result = self.rollback.create_backup(current_version, f"Pre-update backup for {manifest.get('version')}")

            if not backup_result['success']:
                return {
                    'success': False,
                    'error': f'Backup creation failed: {backup_result.get("error")}',
                    'stage': 'backup'
                }

            backup_id = backup_result['backup_id']
            print(f"📦 Backup created: {backup_id}")

            # Extract and install update
            install_result = self._install_package(package_path, manifest, progress_callback)

            if install_result['success']:
                print("✅ Update applied successfully")

                # Update current version
                self._set_current_version(manifest.get('version'))

                # Log successful update
                self._log_update_event('applied', manifest, backup_id)

                return {
                    'success': True,
                    'version': manifest.get('version'),
                    'backup_id': backup_id,
                    'install_details': install_result
                }
            else:
                print(f"❌ Update installation failed: {install_result.get('error')}")

                # Attempt automatic rollback
                print("🔄 Attempting automatic rollback...")
                rollback_result = self.rollback.rollback_to_backup(backup_id)

                if rollback_result['success']:
                    print("✅ Automatic rollback successful")
                    self._log_update_event('rolled_back', manifest, backup_id, install_result.get('error'))
                else:
                    print("❌ Automatic rollback failed - manual intervention required")

                return {
                    'success': False,
                    'error': install_result.get('error'),
                    'stage': 'installation',
                    'rollback_attempted': rollback_result.get('success', False),
                    'backup_id': backup_id
                }

        except Exception as e:
            print(f"❌ Update application error: {e}")
            return {
                'success': False,
                'error': str(e),
                'stage': 'application'
            }
        finally:
            self.current_update = None

    def _install_package(self, package_path: str, manifest: Dict[str, Any],
                        progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """Install the update package"""
        try:
            import tarfile
            import zipfile

            # Determine package type
            package_path = Path(package_path)

            if package_path.suffix == '.gz' or '.tar.gz' in str(package_path):
                # Tar.gz package
                with tarfile.open(package_path, 'r:gz') as tar:
                    # Extract manifest
                    manifest_member = None
                    for member in tar.getmembers():
                        if member.name.endswith('manifest.json'):
                            manifest_member = member
                            break

                    if not manifest_member:
                        return {'success': False, 'error': 'No manifest found in package'}

                    # Extract all files
                    extract_path = Path("/tmp/pisecure_update")
                    extract_path.mkdir(exist_ok=True)

                    tar.extractall(extract_path, members=self._filter_safe_members(tar))

                    # Install files
                    return self._install_extracted_files(extract_path, manifest, progress_callback)

            elif package_path.suffix == '.zip':
                # Zip package
                with zipfile.ZipFile(package_path, 'r') as zipf:
                    # Extract to temporary directory
                    extract_path = Path("/tmp/pisecure_update")
                    extract_path.mkdir(exist_ok=True)

                    zipf.extractall(extract_path, members=self._filter_safe_members(zipf))

                    # Install files
                    return self._install_extracted_files(extract_path, manifest, progress_callback)

            else:
                return {'success': False, 'error': f'Unsupported package format: {package_path.suffix}'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _filter_safe_members(self, archive):
        """Filter archive members to prevent path traversal attacks"""
        import os

        for member in archive:
            # Prevent path traversal
            if os.path.isabs(member.name) or ".." in member.name:
                continue

            # Only allow safe file types
            if not member.name.endswith(('.py', '.json', '.yaml', '.yml', '.conf', '.service', '.txt')):
                continue

            yield member

    def _install_extracted_files(self, extract_path: Path, manifest: Dict[str, Any],
                               progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """Install files from extracted package"""
        try:
            files_installed = 0
            files_failed = 0

            # Get file mapping from manifest
            file_mapping = manifest.get('file_mapping', {})

            for source, destination in file_mapping.items():
                source_path = extract_path / source
                dest_path = Path(destination)

                if not source_path.exists():
                    print(f"Warning: Source file not found: {source_path}")
                    files_failed += 1
                    continue

                try:
                    # Ensure destination directory exists
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    import shutil
                    shutil.copy2(source_path, dest_path)
                    files_installed += 1

                    if progress_callback:
                        progress_callback(files_installed, len(file_mapping))

                except Exception as e:
                    print(f"Failed to install {source} -> {destination}: {e}")
                    files_failed += 1

            # Run post-install scripts if any
            post_install = manifest.get('post_install', [])
            for script in post_install:
                try:
                    result = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=60)
                    if result.returncode != 0:
                        print(f"Post-install script failed: {script}")
                        print(f"Output: {result.stderr}")
                except Exception as e:
                    print(f"Post-install script error: {e}")

            return {
                'success': True,
                'files_installed': files_installed,
                'files_failed': files_failed
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _get_current_version(self) -> str:
        """Get current software version"""
        try:
            import pisecure
            return pisecure.__version__
        except:
            return "unknown"

    def _set_current_version(self, version: str):
        """Update current version (this would typically update a version file)"""
        try:
            version_file = Path("/var/lib/pisecure/version")
            version_file.parent.mkdir(parents=True, exist_ok=True)
            version_file.write_text(version)
        except Exception as e:
            print(f"Failed to update version file: {e}")

    def _log_update_event(self, event_type: str, manifest: Dict[str, Any],
                         backup_id: str, error: str = None):
        """Log update event"""
        log_entry = {
            'timestamp': time.time(),
            'event_type': event_type,
            'version': manifest.get('version'),
            'backup_id': backup_id,
            'error': error
        }

        self.update_log.append(log_entry)

        # Save to log file
        try:
            log_file = Path("/var/lib/pisecure/update_log.json")
            log_file.parent.mkdir(parents=True, exist_ok=True)

            with open(log_file, 'w') as f:
                json.dump(self.update_log[-100:], f, indent=2)  # Keep last 100 entries
        except Exception as e:
            print(f"Failed to save update log: {e}")

    def get_update_history(self) -> List[Dict[str, Any]]:
        """Get update history"""
        try:
            log_file = Path("/var/lib/pisecure/update_log.json")
            if log_file.exists():
                with open(log_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return self.update_log

    def rollback_update(self, target_version: str = None) -> Dict[str, Any]:
        """
        Rollback to previous version

        Args:
            target_version: Specific version to rollback to (optional)

        Returns:
            Rollback result
        """
        try:
            backups = self.rollback.list_backups()

            if not backups:
                return {
                    'success': False,
                    'error': 'No backups available for rollback'
                }

            # Find appropriate backup
            target_backup = None
            if target_version:
                # Find backup for specific version
                for backup in backups:
                    if backup.get('version') == target_version:
                        target_backup = backup
                        break
            else:
                # Use latest backup
                target_backup = backups[0]

            if not target_backup:
                return {
                    'success': False,
                    'error': f'No backup found for version: {target_version}'
                }

            print(f"🔄 Rolling back to version: {target_backup.get('version')}")

            # Perform rollback
            result = self.rollback.rollback_to_backup(target_backup['backup_id'])

            if result['success']:
                # Update current version
                self._set_current_version(target_backup.get('version', 'unknown'))
                self._log_update_event('manual_rollback', {'version': target_backup.get('version')}, target_backup['backup_id'])

            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def emergency_rollback(self) -> Dict[str, Any]:
        """Perform emergency rollback to last known good state"""
        print("🚨 Initiating emergency rollback...")
        return self.rollback.emergency_rollback()

    def register_update(self, update_info: Dict[str, Any]) -> Optional[str]:
        """
        Register update information on blockchain

        Args:
            update_info: Update metadata

        Returns:
            Transaction hash if successful
        """
        return self.fetcher.register_update_on_chain(update_info)

    def cleanup_cache(self) -> Dict[str, Any]:
        """Clean up update cache"""
        return self.fetcher.cleanup_cache()

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system update status"""
        return {
            'current_version': self._get_current_version(),
            'available_updates': len(self.check_for_updates(self._get_current_version())),
            'backups_count': len(self.rollback.list_backups()),
            'cached_updates': len(self.fetcher.list_cached_updates()),
            'update_history': len(self.get_update_history()),
            'last_update_check': time.time()  # Would be stored persistently
        }