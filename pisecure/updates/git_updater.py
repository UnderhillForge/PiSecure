#!/usr/bin/env python3
"""
PiSecure Git-Based Update Manager
==================================

Direct GitHub integration for development and early adoption phases.
Simple updates from GitHub commits without blockchain complexity.

Usage:
    For development: pisecure update check --git
    For production: pisecure update check (blockchain-based)
"""

import os
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import urllib.request

from .update_classifier import UpdateClassifier, UpdateType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitUpdateManager:
    """Git-based update manager for direct GitHub integration"""

    def __init__(self, repo_url: str = "https://github.com/UnderhillForge/PiSecure.git",
                 local_path: str = "/home/pi/PiSecure"):
        self.repo_url = repo_url
        self.local_path = Path(local_path)
        self.classifier = UpdateClassifier()

        # GitHub API
        self.github_api = "https://api.github.com"
        self.repo_owner = "UnderhillForge"
        self.repo_name = "PiSecure"

    def check_git_updates(self) -> List[Dict[str, Any]]:
        """
        Check GitHub for new commits since current version

        Returns:
            List of available updates from Git commits
        """

        try:
            # Get current commit hash
            current_commit = self._get_current_commit()
            if not current_commit:
                logger.warning("Could not determine current commit")
                return []

            # Get latest commits from GitHub
            latest_commits = self._get_github_commits(limit=20)

            if not latest_commits:
                logger.warning("Could not fetch GitHub commits")
                return []

            # Find commits newer than current
            new_commits = []
            for commit in latest_commits:
                if commit['sha'] == current_commit:
                    break  # Stop at current commit
                new_commits.append(commit)

            # Convert commits to update format
            updates = []
            for commit in reversed(new_commits):  # Oldest first
                update = self._commit_to_update(commit)
                if update:
                    updates.append(update)

            return updates

        except Exception as e:
            logger.error(f"Git update check failed: {e}")
            return []

    def apply_git_update(self, commit_hash: str, force: bool = False) -> Dict[str, Any]:
        """
        Apply update by pulling specific commit from GitHub

        Args:
            commit_hash: Git commit hash to update to
            force: Skip safety checks

        Returns:
            Update result
        """

        try:
            logger.info(f"Applying Git update to commit: {commit_hash}")

            # Verify commit exists
            commit_info = self._get_commit_info(commit_hash)
            if not commit_info:
                return {
                    'success': False,
                    'error': f'Commit {commit_hash} not found'
                }

            # Classify update safety
            update_info = self._commit_to_update(commit_info)
            if not update_info:
                return {
                    'success': False,
                    'error': 'Could not classify update'
                }

            # Safety check
            if not force and update_info['type'] == 'BREAKING':
                return {
                    'success': False,
                    'error': 'Breaking changes require --force flag'
                }

            # Create backup
            backup_result = self._create_backup(f"Git update to {commit_hash[:8]}")
            if not backup_result['success']:
                return {
                    'success': False,
                    'error': f'Backup failed: {backup_result.get("error")}'
                }

            # Pull changes from Git
            pull_result = self._git_pull_commit(commit_hash)
            if not pull_result['success']:
                # Attempt rollback
                self._rollback_to_backup(backup_result['backup_id'])
                return pull_result

            # Update dependencies if needed
            dep_result = self._update_dependencies_if_needed(commit_info)
            if not dep_result['success']:
                logger.warning(f"Dependency update failed: {dep_result['error']}")

            # Restart services
            restart_result = self._restart_services()

            # Update version tracking
            self._update_version(commit_info)

            logger.info(f"✅ Successfully updated to {commit_hash[:8]}")

            return {
                'success': True,
                'commit': commit_hash,
                'version': update_info.get('version', 'unknown'),
                'backup_id': backup_result['backup_id'],
                'services_restarted': restart_result['success']
            }

        except Exception as e:
            logger.error(f"Git update application failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_current_commit(self) -> Optional[str]:
        """Get current Git commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.local_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def _get_github_commits(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent commits from GitHub API"""
        try:
            url = f"{self.github_api}/repos/{self.repo_owner}/{self.repo_name}/commits?per_page={limit}"
            logger.debug(f"Fetching commits from: {url}")

            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())

            commits = []
            for item in data:
                commits.append({
                    'sha': item['sha'],
                    'message': item['commit']['message'],
                    'author': item['commit']['author']['name'],
                    'date': item['commit']['author']['date'],
                    'url': item['html_url']
                })

            return commits

        except Exception as e:
            logger.error(f"Failed to fetch GitHub commits: {e}")
            return []

    def _get_commit_info(self, commit_hash: str) -> Optional[Dict[str, Any]]:
        """Get detailed commit information"""
        try:
            url = f"{self.github_api}/repos/{self.repo_owner}/{self.repo_name}/commits/{commit_hash}"

            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())

            return {
                'sha': data['sha'],
                'message': data['commit']['message'],
                'author': data['commit']['author']['name'],
                'date': data['commit']['author']['date'],
                'files': [f['filename'] for f in data.get('files', [])],
                'stats': data.get('stats', {})
            }

        except Exception as e:
            logger.error(f"Failed to get commit info: {e}")
            return None

    def _commit_to_update(self, commit: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert Git commit to update format"""
        try:
            # Get changed files for this commit
            changed_files = commit.get('files', [])
            if not changed_files:
                # Try to get files from GitHub API
                commit_details = self._get_commit_info(commit['sha'])
                if commit_details:
                    changed_files = commit_details.get('files', [])

            # Classify update
            mock_manifest = {'version': commit['sha'][:8]}
            update_type = self.classifier.classify_update(mock_manifest, changed_files)

            return {
                'version': f"git-{commit['sha'][:8]}",
                'type': update_type.value,
                'description': commit['message'].split('\n')[0],  # First line only
                'author': commit.get('author', 'Unknown'),
                'commit': commit['sha'],
                'date': commit.get('date', ''),
                'files_changed': len(changed_files),
                'auto_applicable': update_type in [UpdateType.CRITICAL, UpdateType.SAFE],
                'breaking': update_type == UpdateType.BREAKING
            }

        except Exception as e:
            logger.error(f"Failed to convert commit to update: {e}")
            return None

    def _git_pull_commit(self, commit_hash: str) -> Dict[str, Any]:
        """Pull specific commit from Git repository"""
        try:
            # Stash any local changes
            subprocess.run(['git', 'stash'], cwd=self.local_path, check=True)

            # Fetch latest changes
            subprocess.run(['git', 'fetch', 'origin'], cwd=self.local_path, check=True)

            # Reset to specific commit
            subprocess.run(['git', 'reset', '--hard', commit_hash],
                         cwd=self.local_path, check=True)

            return {'success': True}

        except subprocess.CalledProcessError as e:
            logger.error(f"Git pull failed: {e}")
            return {
                'success': False,
                'error': f'Git operation failed: {e}'
            }
        except Exception as e:
            logger.error(f"Git pull error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _update_dependencies_if_needed(self, commit_info: Dict[str, Any]) -> Dict[str, Any]:
        """Update Python dependencies if requirements changed"""
        try:
            changed_files = commit_info.get('files', [])

            # Check if requirements files changed
            req_files = ['requirements.txt', 'setup.py', 'pyproject.toml']
            if any(f in changed_files for f in req_files):
                logger.info("Requirements files changed, updating dependencies...")

                # Install/update dependencies
                result = subprocess.run([
                    'pip', 'install', '-r', 'requirements.txt'
                ], cwd=self.local_path, capture_output=True, text=True)

                if result.returncode == 0:
                    return {'success': True}
                else:
                    return {
                        'success': False,
                        'error': result.stderr
                    }

            return {'success': True}

        except Exception as e:
            logger.error(f"Dependency update failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _restart_services(self) -> Dict[str, Any]:
        """Restart PiSecure services"""
        try:
            # Restart systemd services
            services = ['pisecure', 'pisecure-mining', 'pisecure-dashboard']

            for service in services:
                try:
                    subprocess.run(['sudo', 'systemctl', 'restart', service],
                                 check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    logger.warning(f"Failed to restart {service}")

            return {'success': True}

        except Exception as e:
            logger.error(f"Service restart failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _create_backup(self, reason: str) -> Dict[str, Any]:
        """Create backup before update"""
        try:
            from .rollback import RollbackManager
            rollback = RollbackManager()

            result = rollback.create_backup("unknown", reason)
            return result

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _rollback_to_backup(self, backup_id: str) -> bool:
        """Rollback to backup on failure"""
        try:
            from .rollback import RollbackManager
            rollback = RollbackManager()

            result = rollback.rollback_to_backup(backup_id)
            return result.get('success', False)

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def _update_version(self, commit_info: Dict[str, Any]):
        """Update version tracking"""
        try:
            version_file = Path("/var/lib/pisecure/version")
            version_file.parent.mkdir(parents=True, exist_ok=True)

            version = f"git-{commit_info['sha'][:8]}"
            version_file.write_text(version)

        except Exception as e:
            logger.warning(f"Failed to update version file: {e}")

    def get_git_status(self) -> Dict[str, Any]:
        """Get Git repository status"""
        try:
            status = {
                'current_commit': self._get_current_commit(),
                'is_clean': self._is_working_directory_clean(),
                'has_uncommitted_changes': not self._is_working_directory_clean(),
                'branch': self._get_current_branch(),
                'remote_url': self._get_remote_url()
            }

            # Check GitHub connectivity
            try:
                self._get_github_commits(limit=1)
                status['github_accessible'] = True
            except:
                status['github_accessible'] = False

            return status

        except Exception as e:
            return {
                'error': str(e),
                'github_accessible': False
            }

    def _is_working_directory_clean(self) -> bool:
        """Check if working directory is clean"""
        try:
            result = subprocess.run(['git', 'status', '--porcelain'],
                                  cwd=self.local_path, capture_output=True, text=True)
            return len(result.stdout.strip()) == 0
        except:
            return False

    def _get_current_branch(self) -> str:
        """Get current Git branch"""
        try:
            result = subprocess.run(['git', 'branch', '--show-current'],
                                  cwd=self.local_path, capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "unknown"

    def _get_remote_url(self) -> str:
        """Get Git remote URL"""
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'],
                                  cwd=self.local_path, capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "unknown"


# Global instance
git_updater = GitUpdateManager()

if __name__ == '__main__':
    # Test the Git updater
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("Testing Git Update Manager...")

        # Test status
        status = git_updater.get_git_status()
        print(f"Git Status: {status}")

        # Test update check
        updates = git_updater.check_git_updates()
        print(f"Available Updates: {len(updates)}")

        for update in updates[:3]:  # Show first 3
            print(f"  • {update['version']} - {update['description']}")

    else:
        print("Usage: python git_updater.py test")