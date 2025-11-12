"""
Git Hook Installer Service

Handles installation, uninstallation, and management of git hooks for project sync.
Supports cross-platform hook installation with backup and chaining capabilities.
"""

import os
import shutil
import stat
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GitHookInstaller:
    """
    Service for installing and managing git hooks in project repositories.

    Features:
    - Cross-platform hook installation (Windows, Linux, macOS)
    - Hook chaining (preserves existing hooks)
    - Automatic backup and restore
    - Git repository validation
    - Execute permissions management on Unix systems
    """

    def __init__(self):
        """Initialize the GitHookInstaller."""
        self.backup_suffix = ".archon-backup"

    async def install_hook(
        self,
        repo_path: str,
        hook_name: str,
        hook_content: str,
        chain_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Install a git hook in the specified repository.

        Args:
            repo_path: Path to the git repository
            hook_name: Name of the hook (e.g., 'post-commit')
            hook_content: Content of the hook script
            chain_existing: If True, preserve and chain existing hooks

        Returns:
            Dict with installation status and details

        Raises:
            ValueError: If repository is invalid or hook installation fails
        """
        try:
            # Validate git repository
            if not await self.validate_git_repo(repo_path):
                raise ValueError(f"Not a valid git repository: {repo_path}")

            # Get hook path
            hook_path = self._get_hook_path(repo_path, hook_name)

            # Check if hook already exists
            existing_hook = None
            if hook_path.exists():
                logger.info(f"Existing hook found at {hook_path}")

                # Backup existing hook
                backup_path = await self.backup_existing_hook(hook_path)
                logger.info(f"Backed up existing hook to {backup_path}")

                if chain_existing:
                    # Read existing hook content for chaining
                    with open(hook_path, 'r', encoding='utf-8') as f:
                        existing_hook = f.read()

                    # Chain hooks: run existing hook first, then new hook
                    hook_content = self._chain_hooks(existing_hook, hook_content, hook_name)
                    logger.info(f"Chaining existing hook with new hook")

            # Write hook content
            with open(hook_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(hook_content)

            # Make executable on Unix systems
            if os.name != 'nt':
                self._make_executable(hook_path)

            logger.info(f"Successfully installed {hook_name} hook at {hook_path}")

            return {
                "success": True,
                "hook_path": str(hook_path),
                "chained": existing_hook is not None and chain_existing,
                "backup_created": existing_hook is not None,
                "installed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to install hook: {e}")
            raise ValueError(f"Hook installation failed: {e}")

    async def uninstall_hook(
        self,
        repo_path: str,
        hook_name: str,
        restore_backup: bool = True
    ) -> Dict[str, Any]:
        """
        Uninstall a git hook from the specified repository.

        Args:
            repo_path: Path to the git repository
            hook_name: Name of the hook to uninstall
            restore_backup: If True, restore the backup if it exists

        Returns:
            Dict with uninstallation status and details
        """
        try:
            hook_path = self._get_hook_path(repo_path, hook_name)

            if not hook_path.exists():
                logger.warning(f"Hook does not exist at {hook_path}")
                return {
                    "success": True,
                    "message": "Hook not found (already uninstalled)",
                    "uninstalled_at": datetime.utcnow().isoformat()
                }

            # Remove the hook
            hook_path.unlink()
            logger.info(f"Removed hook at {hook_path}")

            # Restore backup if requested
            backup_restored = False
            if restore_backup:
                backup_path = Path(str(hook_path) + self.backup_suffix)
                if backup_path.exists():
                    await self.restore_hook(str(hook_path))
                    backup_restored = True
                    logger.info(f"Restored backup from {backup_path}")

            return {
                "success": True,
                "hook_path": str(hook_path),
                "backup_restored": backup_restored,
                "uninstalled_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to uninstall hook: {e}")
            raise ValueError(f"Hook uninstallation failed: {e}")

    async def is_hook_installed(
        self,
        repo_path: str,
        hook_name: str
    ) -> Dict[str, Any]:
        """
        Check if a git hook is installed in the repository.

        Args:
            repo_path: Path to the git repository
            hook_name: Name of the hook to check

        Returns:
            Dict with installation status and details
        """
        try:
            hook_path = self._get_hook_path(repo_path, hook_name)

            if not hook_path.exists():
                return {
                    "installed": False,
                    "hook_path": str(hook_path),
                    "has_backup": False
                }

            # Check for backup
            backup_path = Path(str(hook_path) + self.backup_suffix)
            has_backup = backup_path.exists()

            # Get hook content preview
            with open(hook_path, 'r', encoding='utf-8') as f:
                content = f.read()
                is_archon_hook = "archon" in content.lower() or "PROJECT_ID" in content

            return {
                "installed": True,
                "hook_path": str(hook_path),
                "has_backup": has_backup,
                "is_archon_hook": is_archon_hook,
                "size_bytes": hook_path.stat().st_size,
                "modified_at": datetime.fromtimestamp(hook_path.stat().st_mtime).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to check hook status: {e}")
            return {
                "installed": False,
                "error": str(e)
            }

    async def backup_existing_hook(self, hook_path: Path) -> Path:
        """
        Create a backup of an existing hook.

        Args:
            hook_path: Path to the hook file

        Returns:
            Path to the backup file
        """
        backup_path = Path(str(hook_path) + self.backup_suffix)

        # If backup already exists, don't overwrite it
        if backup_path.exists():
            logger.warning(f"Backup already exists at {backup_path}, skipping")
            return backup_path

        shutil.copy2(hook_path, backup_path)
        logger.info(f"Created backup at {backup_path}")

        return backup_path

    async def restore_hook(self, hook_path: str) -> bool:
        """
        Restore a hook from its backup.

        Args:
            hook_path: Path to the hook file

        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            backup_path = Path(hook_path + self.backup_suffix)

            if not backup_path.exists():
                logger.warning(f"No backup found at {backup_path}")
                return False

            hook_path_obj = Path(hook_path)

            # Remove current hook if it exists
            if hook_path_obj.exists():
                hook_path_obj.unlink()

            # Restore from backup
            shutil.copy2(backup_path, hook_path_obj)

            # Make executable on Unix
            if os.name != 'nt':
                self._make_executable(hook_path_obj)

            # Remove backup file
            backup_path.unlink()

            logger.info(f"Restored hook from backup: {hook_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore hook: {e}")
            return False

    async def validate_git_repo(self, repo_path: str) -> bool:
        """
        Validate that the given path is a git repository.

        Args:
            repo_path: Path to check

        Returns:
            True if valid git repository, False otherwise
        """
        try:
            git_dir = Path(repo_path) / ".git"

            # Check if .git exists (directory or file for submodules)
            if not git_dir.exists():
                logger.warning(f"No .git directory/file found at {repo_path}")
                return False

            # If .git is a directory, check for basic git structure
            if git_dir.is_dir():
                hooks_dir = git_dir / "hooks"
                if not hooks_dir.exists():
                    # Create hooks directory if it doesn't exist
                    hooks_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created hooks directory at {hooks_dir}")

            return True

        except Exception as e:
            logger.error(f"Failed to validate git repository: {e}")
            return False

    def _get_hook_path(self, repo_path: str, hook_name: str) -> Path:
        """
        Get the path to a git hook file.

        Args:
            repo_path: Path to the git repository
            hook_name: Name of the hook

        Returns:
            Path to the hook file
        """
        return Path(repo_path) / ".git" / "hooks" / hook_name

    def _make_executable(self, file_path: Path) -> None:
        """
        Make a file executable on Unix systems.

        Args:
            file_path: Path to the file
        """
        try:
            # Get current permissions
            current_permissions = file_path.stat().st_mode

            # Add execute permissions for owner, group, and others
            new_permissions = current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

            # Set new permissions
            os.chmod(file_path, new_permissions)

            logger.debug(f"Made {file_path} executable")

        except Exception as e:
            logger.error(f"Failed to make file executable: {e}")
            raise

    def _chain_hooks(self, existing_hook: str, new_hook: str, hook_name: str) -> str:
        """
        Chain two hooks together, running the existing hook first.

        Args:
            existing_hook: Content of the existing hook
            new_hook: Content of the new hook
            hook_name: Name of the hook

        Returns:
            Combined hook content
        """
        # Extract shebang from new hook if present
        new_lines = new_hook.split('\n')
        shebang = new_lines[0] if new_lines[0].startswith('#!') else '#!/usr/bin/env python3'

        # Remove shebang from new hook content
        new_hook_body = '\n'.join(new_lines[1:]) if new_lines[0].startswith('#!') else new_hook

        # Create chained hook
        chained_hook = f"""{shebang}
# Chained git hook - created by Archon
# This hook runs both the original hook and Archon's sync hook

import sys
import subprocess

def run_original_hook():
    \"\"\"Run the original hook that was backed up.\"\"\"
    # Original hook content (preserved from backup)
{self._indent_code(existing_hook, 4)}

def run_archon_hook():
    \"\"\"Run the Archon sync hook.\"\"\"
{self._indent_code(new_hook_body, 4)}

if __name__ == "__main__":
    exit_code = 0

    # Run original hook first
    try:
        run_original_hook()
    except Exception as e:
        print(f"Warning: Original hook failed: {{e}}", file=sys.stderr)
        # Don't fail the commit due to original hook failure

    # Run Archon hook
    try:
        run_archon_hook()
    except Exception as e:
        print(f"Warning: Archon hook failed: {{e}}", file=sys.stderr)
        # Don't fail the commit due to Archon hook failure

    sys.exit(exit_code)
"""

        return chained_hook

    def _indent_code(self, code: str, spaces: int) -> str:
        """
        Indent code block by specified number of spaces.

        Args:
            code: Code to indent
            spaces: Number of spaces to indent

        Returns:
            Indented code
        """
        indent = ' ' * spaces
        lines = code.split('\n')
        return '\n'.join(indent + line if line.strip() else line for line in lines)
