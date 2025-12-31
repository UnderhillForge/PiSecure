"""
PiSecure Rollback Manager
=========================

Automatic rollback system for failed updates with version history tracking
and recovery mechanisms. Ensures system stability and provides failsafe recovery.
"""

import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class RollbackManager:
    """Automatic rollback system for update failures"""

    def __init__(self, backup_dir: str = "/var/lib/pisecure/backups",
                 max_backups: int = 5):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = max_backups

        # System paths to backup
        self.system_paths = [
            "/usr/local/lib/pisecure",      # Python modules
            "/usr/local/bin/pisecure",      # CLI binary
            "/etc/pisecure",                # Configuration
            "/var/lib/pisecure/config",     # Runtime config
        ]

        # File extensions to backup
        self.backup_extensions = ['.py', '.json', '.yaml', '.yml', '.conf', '.service']

    def create_backup(self, version: str, description: str = "") -> Dict[str, Any]:
        """
        Create a backup before applying updates

        Args:
            version: Version being backed up
            description: Optional description of the backup

        Returns:
            Backup information dictionary
        """
        try:
            # Generate backup ID
            timestamp = int(time.time())
            backup_id = f"backup_{version}_{timestamp}"

            backup_path = self.backup_dir / backup_id
            backup_path.mkdir(parents=True, exist_ok=True)

            backup_info = {
                'backup_id': backup_id,
                'version': version,
                'timestamp': timestamp,
                'description': description,
                'files_backed_up': [],
                'total_size': 0
            }

            print(f"📦 Creating backup: {backup_id}")

            # Backup system files
            for system_path in self.system_paths:
                path_obj = Path(system_path)
                if path_obj.exists():
                    self._backup_path(path_obj, backup_path, backup_info)

            # Backup PiSecure package files
            import pisecure
            pisecure_path = Path(pisecure.__file__).parent
            self._backup_path(pisecure_path, backup_path / "pisecure", backup_info)

            # Save backup metadata
            metadata_file = backup_path / "backup_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(backup_info, f, indent=2)

            # Cleanup old backups
            self._cleanup_old_backups()

            print(f"✅ Backup created: {backup_id} ({len(backup_info['files_backed_up'])} files, {backup_info['total_size'] / (1024*1024):.1f} MB)")

            return {
                'success': True,
                'backup_id': backup_id,
                'backup_path': str(backup_path),
                'files_count': len(backup_info['files_backed_up']),
                'total_size': backup_info['total_size']
            }

        except Exception as e:
            print(f"❌ Backup creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _backup_path(self, source_path: Path, backup_root: Path, backup_info: Dict[str, Any]):
        """Backup a specific path"""
        try:
            if source_path.is_file():
                # Single file backup
                relative_path = source_path.name
                backup_file = backup_root / relative_path

                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, backup_file)

                file_size = backup_file.stat().st_size
                backup_info['files_backed_up'].append({
                    'original_path': str(source_path),
                    'backup_path': str(backup_file),
                    'size': file_size,
                    'type': 'file'
                })
                backup_info['total_size'] += file_size

            elif source_path.is_dir():
                # Directory backup
                for file_path in source_path.rglob('*'):
                    if file_path.is_file() and file_path.suffix in self.backup_extensions:
                        relative_path = file_path.relative_to(source_path)
                        backup_file = backup_root / relative_path

                        backup_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, backup_file)

                        file_size = backup_file.stat().st_size
                        backup_info['files_backed_up'].append({
                            'original_path': str(file_path),
                            'backup_path': str(backup_file),
                            'size': file_size,
                            'type': 'file'
                        })
                        backup_info['total_size'] += file_size

        except Exception as e:
            print(f"Failed to backup {source_path}: {e}")

    def rollback_to_backup(self, backup_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Rollback to a specific backup

        Args:
            backup_id: Backup ID to rollback to
            force: Force rollback even if validation fails

        Returns:
            Rollback result dictionary
        """
        try:
            backup_path = self.backup_dir / backup_id
            if not backup_path.exists():
                return {
                    'success': False,
                    'error': f'Backup not found: {backup_id}'
                }

            # Load backup metadata
            metadata_file = backup_path / "backup_metadata.json"
            if not metadata_file.exists():
                return {
                    'success': False,
                    'error': f'Backup metadata missing: {metadata_file}'
                }

            with open(metadata_file, 'r') as f:
                backup_info = json.load(f)

            print(f"🔄 Rolling back to backup: {backup_id}")
            print(f"   Version: {backup_info.get('version', 'unknown')}")
            print(f"   Created: {time.ctime(backup_info.get('timestamp', 0))}")
            print(f"   Files: {len(backup_info.get('files_backed_up', []))}")

            if not force:
                # Pre-rollback validation
                validation = self._validate_rollback(backup_info)
                if not validation['valid']:
                    return {
                        'success': False,
                        'error': f'Rollback validation failed: {validation["error"]}',
                        'validation_details': validation
                    }

            # Perform rollback
            rollback_stats = self._perform_rollback(backup_info, backup_path)

            # Post-rollback verification
            verification = self._verify_rollback(backup_info)

            return {
                'success': True,
                'backup_id': backup_id,
                'version_restored': backup_info.get('version'),
                'files_restored': rollback_stats['files_restored'],
                'verification': verification,
                'rollback_stats': rollback_stats
            }

        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _perform_rollback(self, backup_info: Dict[str, Any], backup_path: Path) -> Dict[str, Any]:
        """Perform the actual rollback operation"""
        stats = {'files_restored': 0, 'errors': 0}

        for file_info in backup_info.get('files_backed_up', []):
            try:
                original_path = Path(file_info['original_path'])
                backup_file = Path(file_info['backup_path'])

                # Ensure original directory exists
                original_path.parent.mkdir(parents=True, exist_ok=True)

                # Restore file
                shutil.copy2(backup_file, original_path)
                stats['files_restored'] += 1

            except Exception as e:
                print(f"Failed to restore {file_info['original_path']}: {e}")
                stats['errors'] += 1

        return stats

    def _validate_rollback(self, backup_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rollback feasibility"""
        try:
            # Check backup integrity
            for file_info in backup_info.get('files_backed_up', []):
                backup_file = Path(file_info['backup_path'])
                if not backup_file.exists():
                    return {
                        'valid': False,
                        'error': f'Backup file missing: {backup_file}'
                    }

                # Verify file size matches
                expected_size = file_info.get('size', 0)
                actual_size = backup_file.stat().st_size
                if expected_size != actual_size:
                    return {
                        'valid': False,
                        'error': f'Backup file size mismatch: {backup_file} ({actual_size} vs {expected_size})'
                    }

            # Check system health
            if not self._check_system_health():
                return {
                    'valid': False,
                    'error': 'System health check failed'
                }

            return {'valid': True}

        except Exception as e:
            return {
                'valid': False,
                'error': f'Validation error: {e}'
            }

    def _verify_rollback(self, backup_info: Dict[str, Any]) -> Dict[str, Any]:
        """Verify rollback was successful"""
        try:
            verified = 0
            failed = 0

            for file_info in backup_info.get('files_backed_up', []):
                original_path = Path(file_info['original_path'])
                if original_path.exists():
                    # Check file size
                    expected_size = file_info.get('size', 0)
                    actual_size = original_path.stat().st_size
                    if expected_size == actual_size:
                        verified += 1
                    else:
                        failed += 1
                        print(f"Size mismatch after rollback: {original_path}")
                else:
                    failed += 1
                    print(f"File missing after rollback: {original_path}")

            return {
                'verified': verified,
                'failed': failed,
                'total': verified + failed,
                'success_rate': verified / (verified + failed) if (verified + failed) > 0 else 0
            }

        except Exception as e:
            return {
                'error': str(e),
                'verified': 0,
                'failed': 0,
                'total': 0
            }

    def _check_system_health(self) -> bool:
        """Check basic system health before rollback"""
        try:
            # Check disk space
            stat = shutil.disk_usage('/')
            free_space_gb = stat.free / (1024**3)
            if free_space_gb < 1:  # Less than 1GB free
                print("Warning: Low disk space for rollback")
                return False

            # Check if critical processes are running
            # This is system-specific and might need customization

            return True

        except Exception as e:
            print(f"System health check failed: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []

        try:
            for backup_dir in self.backup_dir.glob('backup_*'):
                if backup_dir.is_dir():
                    metadata_file = backup_dir / "backup_metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                info = json.load(f)
                                backups.append(info)
                        except:
                            # Fallback info without metadata
                            backups.append({
                                'backup_id': backup_dir.name,
                                'path': str(backup_dir),
                                'timestamp': backup_dir.stat().st_mtime
                            })
        except Exception as e:
            print(f"Failed to list backups: {e}")

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return backups

    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific backup"""
        try:
            backup_path = self.backup_dir / backup_id
            metadata_file = backup_path / "backup_metadata.json"

            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    return json.load(f)

        except Exception as e:
            print(f"Failed to get backup info: {e}")

        return None

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a specific backup"""
        try:
            backup_path = self.backup_dir / backup_id
            if backup_path.exists():
                shutil.rmtree(backup_path)
                print(f"✅ Backup deleted: {backup_id}")
                return True
            else:
                print(f"❌ Backup not found: {backup_id}")
                return False

        except Exception as e:
            print(f"❌ Failed to delete backup: {e}")
            return False

    def _cleanup_old_backups(self):
        """Clean up old backups to maintain max_backups limit"""
        try:
            backups = self.list_backups()

            if len(backups) > self.max_backups:
                to_delete = backups[self.max_backups:]

                for backup in to_delete:
                    backup_id = backup.get('backup_id')
                    if backup_id:
                        self.delete_backup(backup_id)
                        print(f"🗑️ Cleaned up old backup: {backup_id}")

        except Exception as e:
            print(f"Failed to cleanup old backups: {e}")

    def create_recovery_snapshot(self) -> Dict[str, Any]:
        """Create a recovery snapshot for emergency rollback"""
        try:
            # Create emergency backup
            emergency_id = f"emergency_{int(time.time())}"
            result = self.create_backup("emergency", "Emergency recovery snapshot")

            if result['success']:
                # Mark as emergency backup
                emergency_marker = self.backup_dir / emergency_id / "EMERGENCY_BACKUP"
                emergency_marker.write_text("This is an emergency recovery backup created automatically")

                print("🚨 Emergency recovery snapshot created")
                print("   Use this if the system becomes unstable after update")

            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def emergency_rollback(self) -> Dict[str, Any]:
        """Perform emergency rollback to latest emergency backup"""
        try:
            backups = self.list_backups()

            # Find latest emergency backup
            emergency_backup = None
            for backup in backups:
                backup_path = self.backup_dir / backup['backup_id']
                emergency_marker = backup_path / "EMERGENCY_BACKUP"
                if emergency_marker.exists():
                    emergency_backup = backup
                    break

            if not emergency_backup:
                return {
                    'success': False,
                    'error': 'No emergency backup found'
                }

            print("🚨 Performing emergency rollback...")
            return self.rollback_to_backup(emergency_backup['backup_id'], force=True)

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }