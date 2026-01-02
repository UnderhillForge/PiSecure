#!/usr/bin/env python3
"""
PiSecure Update Classifier and Safety Checker
==============================================

Automatically classifies updates by safety level and verifies consensus compatibility.
Ensures blockchain integrity while enabling safe software updates.
"""

import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UpdateType(Enum):
    """Update safety classification levels"""
    CRITICAL = "critical"      # Security patches, auto-apply
    SAFE = "safe"             # Backward compatible, user approval
    COMPATIBLE = "compatible"  # May need coordination, safe for most
    BREAKING = "breaking"     # Requires network consensus


class ConsensusImpact(Enum):
    """Impact on blockchain consensus"""
    NONE = "none"                    # No consensus impact
    MINOR = "minor"                  # Minor changes, backward compatible
    COMPATIBLE = "compatible"        # Compatible changes requiring coordination
    BREAKING = "breaking"            # Breaking changes requiring hard fork


class UpdateClassifier:
    """Classifies updates by safety level and consensus impact"""

    def __init__(self):
        # Files that cannot be changed without consensus
        self.consensus_protected_files = {
            'pisecure/core/blockchain.py',
            'pisecure/core/tokens.py',
            'pisecure/core/wallet.py',
            'pisecure/core/consensus.py',
            'pisecure/network/protocol.py'
        }

        # API files that must maintain backward compatibility
        self.api_files = {
            'pisecure/api/server.py',
            'pisecure/api/client.py',
            'pisecure/api/__init__.py'
        }

        # Transaction validation patterns
        self.transaction_validation_patterns = [
            r'def.*validate.*transaction',
            r'class.*TransactionValidator',
            r'if.*tx.*type.*==',
            r'self\._validate_.*transaction'
        ]

    def classify_update(self, manifest: Dict[str, Any],
                       changed_files: List[str],
                       codebase_diff: str = "") -> UpdateType:
        """
        Classify update safety level based on manifest and changes

        Args:
            manifest: Update manifest
            changed_files: List of changed files
            codebase_diff: Git diff of changes

        Returns:
            UpdateType classification
        """

        # Check for explicitly marked critical updates
        if manifest.get('critical_security_update', False):
            return UpdateType.CRITICAL

        # Check for consensus-breaking changes
        if self._has_consensus_breaking_changes(changed_files, codebase_diff):
            return UpdateType.BREAKING

        # Check for API compatibility issues
        if self._has_api_breaking_changes(changed_files, codebase_diff):
            return UpdateType.BREAKING

        # Check for new dependencies or major version changes
        if self._has_dependency_changes(manifest):
            return UpdateType.COMPATIBLE

        # Check for plugin additions
        if manifest.get('new_plugins'):
            return UpdateType.SAFE

        # Check for major version bump
        if self._is_major_version_update(manifest):
            return UpdateType.COMPATIBLE

        # Default to safe for minor updates and patches
        return UpdateType.SAFE

    def assess_consensus_impact(self, manifest: Dict[str, Any],
                              changed_files: List[str],
                              codebase_diff: str = "") -> ConsensusImpact:
        """
        Assess impact on blockchain consensus

        Args:
            manifest: Update manifest
            changed_files: List of changed files
            codebase_diff: Git diff of changes

        Returns:
            ConsensusImpact level
        """

        # Check if consensus-protected files changed
        consensus_files_changed = set(changed_files) & self.consensus_protected_files
        if consensus_files_changed:
            logger.warning(f"Consensus-protected files changed: {consensus_files_changed}")

            # Check if changes are truly breaking
            if self._are_changes_consensus_breaking(codebase_diff):
                return ConsensusImpact.BREAKING
            else:
                return ConsensusImpact.COMPATIBLE

        # Check transaction validation changes
        if self._transaction_validation_changed(codebase_diff):
            return ConsensusImpact.BREAKING

        # Check for new transaction types (could be compatible)
        if self._adds_new_transaction_types(codebase_diff):
            return ConsensusImpact.COMPATIBLE

        # API changes might affect compatibility
        api_files_changed = set(changed_files) & self.api_files
        if api_files_changed and self._has_breaking_api_changes(codebase_diff):
            return ConsensusImpact.COMPATIBLE

        return ConsensusImpact.NONE

    def verify_update_safety(self, manifest: Dict[str, Any],
                           changed_files: List[str],
                           codebase_diff: str = "") -> Tuple[bool, str]:
        """
        Comprehensive safety verification

        Args:
            manifest: Update manifest
            changed_files: List of changed files
            codebase_diff: Git diff of changes

        Returns:
            (is_safe, reason) tuple
        """

        # Basic validation
        if not manifest.get('version'):
            return False, "Missing version in manifest"

        if not manifest.get('description'):
            return False, "Missing description in manifest"

        # Check version format
        if not self._is_valid_version(manifest['version']):
            return False, "Invalid version format"

        # Verify no critical consensus violations
        consensus_impact = self.assess_consensus_impact(manifest, changed_files, codebase_diff)
        if consensus_impact == ConsensusImpact.BREAKING:
            return False, "Update contains consensus-breaking changes"

        # Check dependency safety
        dep_issues = self._check_dependency_safety(manifest)
        if dep_issues:
            return False, f"Dependency issues: {dep_issues}"

        # Verify file safety
        file_issues = self._check_file_safety(changed_files, manifest)
        if file_issues:
            return False, f"File safety issues: {file_issues}"

        return True, "Update passed safety verification"

    def _has_consensus_breaking_changes(self, changed_files: List[str],
                                      codebase_diff: str) -> bool:
        """Check if changes break consensus"""
        # Consensus-protected files changed
        if set(changed_files) & self.consensus_protected_files:
            return True

        # Transaction validation changes
        if self._transaction_validation_changed(codebase_diff):
            return True

        # Block validation changes
        if self._block_validation_changed(codebase_diff):
            return True

        return False

    def _has_api_breaking_changes(self, changed_files: List[str],
                                codebase_diff: str) -> bool:
        """Check for breaking API changes"""
        api_files_changed = set(changed_files) & self.api_files
        if not api_files_changed:
            return False

        # Look for breaking patterns in diff
        breaking_patterns = [
            r'remove.*endpoint',
            r'delete.*route',
            r'change.*response.*format',
            r'break.*compatibility'
        ]

        for pattern in breaking_patterns:
            if re.search(pattern, codebase_diff, re.IGNORECASE):
                return True

        return False

    def _has_dependency_changes(self, manifest: Dict[str, Any]) -> bool:
        """Check if update adds or changes dependencies"""
        deps = manifest.get('dependencies', {})
        return bool(deps.get('added') or deps.get('updated') or deps.get('removed'))

    def _is_major_version_update(self, manifest: Dict[str, Any]) -> bool:
        """Check if this is a major version update"""
        try:
            version = manifest.get('version', '0.0.0')
            major_version = int(version.split('.')[0])
            return major_version > 1  # Assuming current is 1.x.x
        except:
            return False

    def _are_changes_consensus_breaking(self, codebase_diff: str) -> bool:
        """Deep analysis of whether changes break consensus"""
        # Look for dangerous patterns
        dangerous_patterns = [
            r'change.*difficulty',
            r'modify.*target',
            r'alter.*block.*time',
            r'change.*reward.*amount',
            r'modify.*genesis',
            r'alter.*consensus.*rules'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, codebase_diff, re.IGNORECASE):
                return True

        return False

    def _transaction_validation_changed(self, codebase_diff: str) -> bool:
        """Check if transaction validation logic changed"""
        for pattern in self.transaction_validation_patterns:
            if re.search(pattern, codebase_diff):
                return True
        return False

    def _block_validation_changed(self, codebase_diff: str) -> bool:
        """Check if block validation logic changed"""
        block_patterns = [
            r'def.*validate.*block',
            r'class.*BlockValidator',
            r'if.*block.*hash',
            r'self\._validate_.*block'
        ]

        for pattern in block_patterns:
            if re.search(pattern, codebase_diff):
                return True
        return False

    def _adds_new_transaction_types(self, codebase_diff: str) -> bool:
        """Check if new transaction types are added"""
        new_tx_patterns = [
            r'add.*transaction.*type',
            r'new.*tx.*type',
            r'extend.*transaction.*types'
        ]

        for pattern in new_tx_patterns:
            if re.search(pattern, codebase_diff, re.IGNORECASE):
                return True
        return False

    def _check_dependency_safety(self, manifest: Dict[str, Any]) -> Optional[str]:
        """Check dependency safety"""
        deps = manifest.get('dependencies', {})

        # Check for known problematic packages
        problematic_packages = ['crypto', 'ssl', 'hashlib']  # Core Python modules that shouldn't be replaced

        for dep in deps.get('added', []):
            package_name = dep.split('==')[0].split('>=')[0].split('>')[0].strip()
            if package_name in problematic_packages:
                return f"Cannot add core Python module: {package_name}"

        # Check for major version jumps
        for dep in deps.get('updated', []):
            if '>=' in dep or '>' in dep:
                # Major version constraint - requires testing
                pass

        return None

    def _check_file_safety(self, changed_files: List[str], manifest: Dict[str, Any]) -> Optional[str]:
        """Check file safety"""
        # Don't allow changes to system directories
        system_paths = ['/etc/', '/usr/', '/bin/', '/sbin/']
        for file in changed_files:
            for sys_path in system_paths:
                if file.startswith(sys_path):
                    return f"Cannot modify system file: {file}"

        # Check file size limits
        total_size = manifest.get('total_size', 0)
        if total_size > 100 * 1024 * 1024:  # 100MB limit
            return f"Update too large: {total_size} bytes"

        return None

    def _is_valid_version(self, version: str) -> bool:
        """Validate semantic version format"""
        version_pattern = r'^\d+\.\d+\.\d+(-[\w\.\-]+)?(\+[\w\.\-]+)?$'
        return bool(re.match(version_pattern, version))

    def generate_update_manifest(self, version: str, changed_files: List[str],
                               dependencies: Dict[str, List[str]],
                               description: str, author: str) -> Dict[str, Any]:
        """
        Generate update manifest from changes

        Args:
            version: New version string
            changed_files: List of changed files
            dependencies: Dependency changes
            description: Update description
            author: Update author

        Returns:
            Complete update manifest
        """

        # Classify the update
        mock_manifest = {'version': version, 'dependencies': dependencies}
        update_type = self.classify_update(mock_manifest, changed_files)

        # Assess consensus impact
        consensus_impact = self.assess_consensus_impact(mock_manifest, changed_files)

        # Generate manifest
        manifest = {
            'version': version,
            'type': update_type.value,
            'description': description,
            'author': author,
            'timestamp': int(__import__('time').time()),
            'consensus_impact': consensus_impact.value,
            'dependencies': dependencies,
            'changed_files': changed_files,
            'compatibility': {
                'min_version': '1.0.0',  # Would be calculated
                'max_version': version.split('.')[0] + '.x.x',
                'breaking_changes': update_type == UpdateType.BREAKING
            },
            'testing_required': update_type in [UpdateType.COMPATIBLE, UpdateType.BREAKING],
            'auto_applicable': update_type == UpdateType.CRITICAL
        }

        return manifest


class DependencyManager:
    """Safe dependency management for updates"""

    def __init__(self):
        self.test_env_path = Path("/tmp/pisecure_dep_test")
        self.backup_env_path = Path("/home/pi/PiSecure/backup_env")

    def check_dependency_conflicts(self, new_requirements: Dict[str, List[str]]) -> List[str]:
        """Check for dependency conflicts"""
        conflicts = []

        # This would use pip-tools or similar to check conflicts
        # For now, basic checks

        try:
            from pkg_resources import get_distribution
            for dep in new_requirements.get('added', []):
                package_name = dep.split('==')[0].split('>=')[0].split('>')[0].strip()
                try:
                    get_distribution(package_name)
                    conflicts.append(f"Package {package_name} already installed")
                except:
                    pass  # Package not installed, OK
        except ImportError:
            # pkg_resources not available, skip check
            pass

        return conflicts

    def test_dependency_installation(self, requirements: Dict[str, List[str]]) -> bool:
        """Test dependency installation in isolated environment"""
        try:
            # Create test environment
            import subprocess
            import venv

            venv.create(self.test_env_path, with_pip=True)

            # Install dependencies in test environment
            pip_path = self.test_env_path / "bin" / "pip"
            requirements_file = self.test_env_path / "requirements.txt"

            # Write requirements
            with open(requirements_file, 'w') as f:
                for dep_type, deps in requirements.items():
                    for dep in deps:
                        f.write(f"{dep}\n")

            # Install
            result = subprocess.run([
                str(pip_path), 'install', '-r', str(requirements_file)
            ], capture_output=True, text=True, timeout=300)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Dependency testing failed: {e}")
            return False
        finally:
            # Cleanup test environment
            import shutil
            if self.test_env_path.exists():
                shutil.rmtree(self.test_env_path)

    def verify_core_functionality(self, test_env_path: Path) -> bool:
        """Verify core PiSecure functionality still works"""
        try:
            python_path = test_env_path / "bin" / "python"

            # Test basic imports
            test_commands = [
                "import sys; print('Python OK')",
                "import pisecure; print('PiSecure import OK')",
                "from pisecure.core.blockchain import SignChain; print('Blockchain import OK')"
            ]

            import subprocess
            for cmd in test_commands:
                result = subprocess.run([
                    str(python_path), '-c', cmd
                ], capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    logger.error(f"Core functionality test failed: {cmd}")
                    logger.error(f"Error: {result.stderr}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Core functionality verification failed: {e}")
            return False


# Global instances
update_classifier = UpdateClassifier()
dependency_manager = DependencyManager()

if __name__ == '__main__':
    # Test the classifier
    import sys

    if len(sys.argv) < 2:
        print("Usage: python update_classifier.py <manifest_file>")
        sys.exit(1)

    manifest_file = sys.argv[1]

    try:
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)

        changed_files = manifest.get('changed_files', [])

        # Classify update
        update_type = update_classifier.classify_update(manifest, changed_files)

        # Assess consensus impact
        consensus_impact = update_classifier.assess_consensus_impact(manifest, changed_files)

        # Verify safety
        is_safe, reason = update_classifier.verify_update_safety(manifest, changed_files)

        print("Update Classification Results:")
        print(f"Version: {manifest.get('version')}")
        print(f"Type: {update_type.value.upper()}")
        print(f"Consensus Impact: {consensus_impact.value.upper()}")
        print(f"Safe: {'✅ YES' if is_safe else '❌ NO'}")
        print(f"Reason: {reason}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)