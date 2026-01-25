#!/usr/bin/env python3
"""
PiSecure Update Manifest Generator
==================================

Generates comprehensive update manifests for safe software distribution.
Analyzes code changes and creates manifests with safety classifications.

Usage:
    python manifest_generator.py --version 1.2.0 --description "Bug fixes" --author "dev-team"
"""

import os
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import logging

from .update_classifier import UpdateClassifier, UpdateType, ConsensusImpact

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UpdateManifestGenerator:
    """Generates update manifests from code changes"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.classifier = UpdateClassifier()

    def generate_manifest(self, version: str, description: str, author: str,
                         target_branch: str = "main", source_branch: str = "HEAD",
                         dependencies: Optional[Dict[str, List[str]]] = None,
                         plugins: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive update manifest

        Args:
            version: New version string
            description: Update description
            author: Update author/organization
            target_branch: Target branch to compare against
            source_branch: Source branch with changes
            dependencies: Dependency changes (added, updated, removed)
            plugins: New plugins included in update

        Returns:
            Complete update manifest
        """

        logger.info(f"Generating manifest for version {version}")

        # Get git diff and changed files
        changed_files, diff_content = self._get_git_changes(target_branch, source_branch)

        # Analyze dependencies
        if not dependencies:
            dependencies = self._analyze_dependency_changes(changed_files)

        # Classify update safety
        mock_manifest = {
            'version': version,
            'dependencies': dependencies,
            'new_plugins': plugins or []
        }

        update_type = self.classifier.classify_update(mock_manifest, changed_files, diff_content)
        consensus_impact = self.classifier.assess_consensus_impact(mock_manifest, changed_files, diff_content)

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
                'min_version': self._calculate_min_version(version),
                'max_version': version.split('.')[0] + '.x.x',
                'breaking_changes': update_type == UpdateType.BREAKING
            },
            'testing_required': update_type in [UpdateType.COMPATIBLE, UpdateType.BREAKING],
            'auto_applicable': update_type == UpdateType.CRITICAL,
            'file_mapping': self._generate_file_mapping(changed_files),
            'total_size': self._calculate_total_size(changed_files),
            'checksums': self._calculate_file_checksums(changed_files),
            'git_info': {
                'target_branch': target_branch,
                'source_branch': source_branch,
                'commit_hash': self._get_current_commit(),
                'diff_summary': self._summarize_diff(diff_content)
            }
        }

        # Add plugins if provided
        if plugins:
            manifest['new_plugins'] = plugins

        # Add critical security flag if applicable
        if self._is_critical_security_update(diff_content):
            manifest['critical_security_update'] = True

        # Validate manifest
        is_valid, error = self.classifier.verify_update_safety(manifest, changed_files, diff_content)
        if not is_valid:
            logger.warning(f"Manifest safety check failed: {error}")
            manifest['safety_warnings'] = [error]

        logger.info(f"Manifest generated: {update_type.value.upper()} update")
        return manifest

    def _get_git_changes(self, target_branch: str, source_branch: str) -> tuple[List[str], str]:
        """Get changed files and diff from git"""
        try:
            # Get changed files
            cmd = ['git', 'diff', '--name-only', f'{target_branch}..{source_branch}']
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, check=True)
            changed_files = [f for f in result.stdout.strip().split('\n') if f]

            # Get diff content
            cmd = ['git', 'diff', f'{target_branch}..{source_branch}']
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, check=True)
            diff_content = result.stdout

            return changed_files, diff_content

        except subprocess.CalledProcessError as e:
            logger.error(f"Git diff failed: {e}")
            return [], ""

    def _analyze_dependency_changes(self, changed_files: List[str]) -> Dict[str, List[str]]:
        """Analyze dependency changes from requirements files"""
        dependencies = {'added': [], 'updated': [], 'removed': []}

        # Check for requirements file changes
        req_files = ['requirements.txt', 'setup.py', 'pyproject.toml']
        for req_file in req_files:
            if req_file in changed_files:
                logger.info(f"Detected changes to {req_file} - manual dependency review required")
                dependencies['manual_review_required'] = True

        return dependencies

    def _calculate_min_version(self, version: str) -> str:
        """Calculate minimum compatible version"""
        parts = version.split('.')
        if len(parts) >= 2:
            # Assume backward compatibility within major version
            return f"{parts[0]}.0.0"
        return "1.0.0"

    def _generate_file_mapping(self, changed_files: List[str]) -> Dict[str, str]:
        """Generate source -> destination file mapping"""
        mapping = {}

        for file in changed_files:
            if file.startswith(('pisecure/', 'docs/', 'examples/')):
                # Files that should be installed
                mapping[file] = f"/home/pi/PiSecure/{file}"
            elif file.endswith(('.py', '.json', '.yaml', '.yml')):
                # Python and config files
                mapping[file] = f"/home/pi/PiSecure/{file}"
            # Skip other files (tests, CI, etc.)

        return mapping

    def _calculate_total_size(self, changed_files: List[str]) -> int:
        """Calculate total size of changed files"""
        total_size = 0

        for file in changed_files:
            file_path = self.repo_path / file
            if file_path.exists():
                try:
                    total_size += file_path.stat().st_size
                except OSError:
                    pass

        return total_size

    def _calculate_file_checksums(self, changed_files: List[str]) -> Dict[str, str]:
        """Calculate SHA256 checksums for changed files"""
        checksums = {}

        for file in changed_files:
            file_path = self.repo_path / file
            if file_path.exists():
                try:
                    with open(file_path, 'rb') as f:
                        checksums[file] = hashlib.sha256(f.read()).hexdigest()
                except OSError:
                    logger.warning(f"Could not checksum {file}")

        return checksums

    def _get_current_commit(self) -> str:
        """Get current git commit hash"""
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                  cwd=self.repo_path, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def _summarize_diff(self, diff_content: str) -> Dict[str, Any]:
        """Summarize the git diff"""
        lines = diff_content.split('\n')

        summary = {
            'files_changed': 0,
            'additions': 0,
            'deletions': 0,
            'binary_files': 0
        }

        for line in lines:
            if line.startswith('+++ '):
                summary['files_changed'] += 1
            elif line.startswith('+') and not line.startswith('+++'):
                summary['additions'] += 1
            elif line.startswith('-') and not line.startswith('---'):
                summary['deletions'] += 1
            elif 'Binary files differ' in line:
                summary['binary_files'] += 1

        return summary

    def _is_critical_security_update(self, diff_content: str) -> bool:
        """Check if this is a critical security update"""
        security_keywords = [
            'security', 'vulnerability', 'exploit', 'cve-', 'patch',
            'authentication', 'authorization', 'encryption', 'certificate'
        ]

        diff_lower = diff_content.lower()
        return any(keyword in diff_lower for keyword in security_keywords)

    def save_manifest(self, manifest: Dict[str, Any], output_path: str):
        """Save manifest to file"""
        output_path = Path(output_path)

        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2, sort_keys=True)

        logger.info(f"Manifest saved to {output_path}")

    def validate_manifest(self, manifest_path: str) -> tuple[bool, str]:
        """Validate an existing manifest"""
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            # Basic validation
            required_fields = ['version', 'type', 'description', 'author', 'timestamp']
            for field in required_fields:
                if field not in manifest:
                    return False, f"Missing required field: {field}"

            # Version format validation
            if not self.classifier._is_valid_version(manifest['version']):
                return False, "Invalid version format"

            # Type validation
            valid_types = [t.value for t in UpdateType]
            if manifest['type'] not in valid_types:
                return False, f"Invalid update type: {manifest['type']}"

            return True, "Manifest is valid"

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"


def main():
    """Command line interface for manifest generation"""
    parser = argparse.ArgumentParser(description="PiSecure Update Manifest Generator")

    parser.add_argument('--version', required=True, help='New version number')
    parser.add_argument('--description', required=True, help='Update description')
    parser.add_argument('--author', required=True, help='Update author/organization')
    parser.add_argument('--target-branch', default='main', help='Target branch for comparison')
    parser.add_argument('--source-branch', default='HEAD', help='Source branch with changes')
    parser.add_argument('--dependencies', help='JSON file with dependency changes')
    parser.add_argument('--plugins', help='JSON file with new plugins')
    parser.add_argument('--output', '-o', default='update_manifest.json', help='Output manifest file')
    parser.add_argument('--validate', help='Validate existing manifest file')

    args = parser.parse_args()

    generator = UpdateManifestGenerator()

    if args.validate:
        # Validate existing manifest
        is_valid, message = generator.validate_manifest(args.validate)
        if is_valid:
            print(f"✅ {message}")
            return 0
        else:
            print(f"❌ {message}")
            return 1

    # Load dependencies if provided
    dependencies = None
    if args.dependencies:
        try:
            with open(args.dependencies, 'r') as f:
                dependencies = json.load(f)
        except Exception as e:
            print(f"❌ Error loading dependencies file: {e}")
            return 1

    # Load plugins if provided
    plugins = None
    if args.plugins:
        try:
            with open(args.plugins, 'r') as f:
                plugins = json.load(f)
        except Exception as e:
            print(f"❌ Error loading plugins file: {e}")
            return 1

    # Generate manifest
    try:
        manifest = generator.generate_manifest(
            version=args.version,
            description=args.description,
            author=args.author,
            target_branch=args.target_branch,
            source_branch=args.source_branch,
            dependencies=dependencies,
            plugins=plugins
        )

        # Save manifest
        generator.save_manifest(manifest, args.output)

        # Print summary
        print("📦 Update Manifest Generated"        print("=" * 30)
        print(f"Version: {manifest['version']}")
        print(f"Type: {manifest['type'].upper()}")
        print(f"Consensus Impact: {manifest['consensus_impact'].upper()}")
        print(f"Files Changed: {len(manifest['changed_files'])}")
        print(f"Total Size: {manifest['total_size']} bytes")
        print(f"Auto-applicable: {'✅' if manifest['auto_applicable'] else '❌'}")
        print(f"Testing Required: {'✅' if manifest['testing_required'] else '❌'}")
        print(f"Saved to: {args.output}")

        if manifest.get('safety_warnings'):
            print("
⚠️  Safety Warnings:"            for warning in manifest['safety_warnings']:
                print(f"   • {warning}")

        return 0

    except Exception as e:
        print(f"❌ Manifest generation failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())