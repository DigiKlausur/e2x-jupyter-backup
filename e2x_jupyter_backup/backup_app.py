import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

from jupyter_core.application import JupyterApp
from traitlets import Int, Unicode

from ._version import __version__


class E2xBackupApp(JupyterApp):
    """Jupyter application for backing up notebooks to a local directory.

    This application automatically creates timestamped backups of Jupyter notebooks
    when they are saved. It supports both absolute and relative backup directories
    and can automatically prune old backups based on a maximum count.

    Attributes:
        max_backup_files: Maximum number of backup files to keep per notebook.
            Set to 0 to disable backups. Older backups are automatically deleted.
        backup_dir: Directory to store backups in. Can be absolute or relative.
            If relative, backups are stored relative to the notebook's directory.
            If absolute, the notebook's relative path from root is preserved.
    """

    description = "Backup Jupyter notebooks to a local directory"
    version = __version__

    config_file_name = Unicode(
        "jupyter_backup_config.py",
        config=True,
        help="Configuration file to load",
    )

    max_backup_files = Int(
        10,
        config=True,
        help="Maximum number of backup files to keep. Set to 0 to disable backups",
    )

    max_backup_size_mb = Int(
        100,
        config=True,
        help=(
            "Maximum size of all backups for a single notebook in megabytes. "
            "Set to 0 to disable size limit."
        ),
    )

    min_seconds_between_backups = Int(
        20,
        config=True,
        help=(
            "Minimum number of seconds between backups for the same notebook. "
            "If a backup is created within this interval, it may overwrite the "
            "most recent backup instead of creating a new one."
        ),
    )
    backup_dir = Unicode(".backup", config=True, help="Directory to store backups in")

    def list_backups(self, backup_dir: Path, filename: str) -> List[Path]:
        """List all backup files for a given notebook filename.

        Searches for files matching the backup naming pattern:
        YYYY-MM-DD_HH-MM-SS_{filename}

        Args:
            backup_dir: Directory containing backup files.
            filename: Original notebook filename to find backups for.

        Returns:
            List of Path objects pointing to backup files, unsorted.
        """
        # First find all files that end in filename
        candidate_files = backup_dir.glob(f"*{filename}")
        # Timestamp pattern
        timestamp_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_$")
        # Filter everything based on the timestamps
        backup_files = []
        for candidate_file in candidate_files:
            part = candidate_file.name.replace(filename, "")
            if timestamp_pattern.match(part):
                backup_files.append(candidate_file)
        return backup_files

    def prune_old_backups(self, backup_dir: Path, filename: str) -> None:
        """Remove old backup files exceeding the maximum count.

        Keeps only the most recent backup files up to max_backup_files.
        Older backups are automatically deleted.
        Additionally, if max_backup_size_mb is set, ensures total size does not exceed this limit.

        Args:
            backup_dir: Directory containing backup files.
            filename: Original notebook filename to prune backups for.
        """
        backup_files = sorted(self.list_backups(backup_dir, filename), reverse=True)
        remaining_backups = backup_files
        if self.max_backup_files > 0:
            remaining_backups = backup_files[: self.max_backup_files]
            for old_backup in backup_files[self.max_backup_files :]:
                old_backup.unlink()
                self.log.info(f"Deleted old backup {old_backup}")
        if self.max_backup_size_mb > 0:
            total_size_mb = sum(f.stat().st_size for f in remaining_backups) / (1024 * 1024)
            while total_size_mb > self.max_backup_size_mb and remaining_backups:
                oldest_backup = remaining_backups.pop()
                oldest_backup.unlink()
                self.log.info(f"Deleted old backup {oldest_backup} to reduce total size")
                total_size_mb = sum(f.stat().st_size for f in remaining_backups) / (1024 * 1024)

    def should_overwrite_backup(self, backup_dir: Path, filename: str, timestamp: datetime) -> bool:
        """Decide whether a new backup should overwrite the most recent backup.

        This prevents backup clutter during rapid-save bursts (e.g., autosave, Ctrl+S spam)
        while preserving backups from distinct editing sessions.

        The strategy is:
        - Preserve the first save that starts a new editing session
        - Overwrite subsequent rapid saves within the same burst

        Examples (assuming min_seconds_between_backups = 20 seconds):

        Scenario 1 - Normal interval between saves (no overwrite):
            Existing backups: 10:00:00 (70 sec ago), 09:58:00
            New save: 10:01:10 (now)
            → Don't overwrite. Each save represents a distinct editing moment.

        Scenario 2 - First rapid save after normal interval (no overwrite):
            Existing backups: 10:00:50 (15 sec ago), 10:00:00
            New save: 10:01:05 (now)
            → Don't overwrite. The 10:00:50 backup marks the start of a new editing
               session and should be preserved as a restore point.

        Scenario 3 - Multiple rapid saves in succession (overwrite):
            Existing backups: 10:01:00 (8 sec ago), 10:00:55 (13 sec ago)
            New save: 10:01:08 (now)
            → Overwrite the 10:01:00 backup. We're in a burst of rapid saves
               (autosave or user repeatedly saving). Keep only the most recent
               from this burst to avoid clutter.

        Scenario 4 - Insufficient backup history (no overwrite):
            Existing backups: 10:00:00
            New save: 10:00:05 (now)
            → Don't overwrite. Need at least 2 backups to detect a burst pattern.

        Args:
            backup_dir: Directory containing backup files.
            filename: Original notebook filename to check backups for.
            timestamp: Current timestamp when the backup is being considered.

        Returns:
            True if the new backup should overwrite the most recent backup, False otherwise.
        """
        existing_backups = sorted(self.list_backups(backup_dir, filename), reverse=True)
        if len(existing_backups) < 2:
            return False
        latest_backup = existing_backups[0].name.replace(filename, "")[:-1]
        second_latest_backup = existing_backups[1].name.replace(filename, "")[:-1]
        latest_time = datetime.strptime(latest_backup, "%Y-%m-%d_%H-%M-%S")
        if (timestamp - latest_time).total_seconds() > self.min_seconds_between_backups:
            return False
        second_latest_time = datetime.strptime(second_latest_backup, "%Y-%m-%d_%H-%M-%S")
        if (latest_time - second_latest_time).total_seconds() < self.min_seconds_between_backups:
            return True
        return False

    def backup(self, model: Dict[str, Any], os_path: str, contents_manager: Any) -> None:
        """Create a timestamped backup of a notebook file.

        This method is called as a post-save hook. It creates a backup only for
        notebook files and handles both absolute and relative backup directories.

        For absolute backup_dir:
            Preserves the notebook's relative path from the Jupyter root.
            Example: /backup_root/subdir/notebook.ipynb

        For relative backup_dir:
            Creates backup directory relative to the notebook.
            Example: notebook_dir/.backup/notebook.ipynb

        Args:
            model: Jupyter contents model containing file metadata.
                Must have a 'type' key (e.g., 'notebook', 'file').
            os_path: Absolute filesystem path to the notebook being saved.
            contents_manager: Jupyter ContentsManager instance with root_dir attribute.
        """
        if model["type"] != "notebook":
            return
        if self.max_backup_files == 0 or self.max_backup_size_mb == 0:
            self.log.info("Backup disabled")
            return

        full_backup_dir = Path(os.path.expandvars(self.backup_dir)).expanduser()

        notebook_parent_dir, filename = os.path.split(os_path)

        # Determine backup directory path based on whether backup_dir is absolute or relative
        if full_backup_dir.is_absolute():
            relative_path = Path(notebook_parent_dir).relative_to(contents_manager.root_dir)
            backup_dir = full_backup_dir / relative_path
        else:
            backup_dir = Path(notebook_parent_dir) / full_backup_dir

        backup_dir.mkdir(parents=True, exist_ok=True)  # Ensure backup directory exists

        current_time = datetime.now()
        timestamp_str = current_time.strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"{timestamp_str}_{filename}"
        backup_path = backup_dir / backup_filename

        # Skip backup if it already exists for this timestamp
        if backup_path.exists():
            return

        if self.should_overwrite_backup(backup_dir, filename, current_time):
            self.log.info("Overwriting the most recent backup due to minimum interval setting.")
            # Get the most recent backup file and unlink it
            existing_backups = sorted(self.list_backups(backup_dir, filename), reverse=True)
            existing_backups[0].unlink()

        shutil.copy2(os_path, backup_path)
        self.log.info(f"Backed up {os_path} to {backup_path}")

        # Prune old backups
        self.prune_old_backups(backup_dir, filename)


def get_post_save_hook() -> Callable:
    """Create a post-save hook function for Jupyter notebook backups.

    Initializes an E2xBackupApp instance and returns a hook function that can
    be registered with Jupyter's FileContentsManager to automatically backup
    notebooks when they are saved.

    Configuration is loaded from jupyter_backup_config.py or Jupyter config files.

    Returns:
        A callable that can be used as a Jupyter post_save_hook. The function
        signature matches Jupyter's requirements:
        func(model, os_path, contents_manager, **kwargs)

    Example:
        In jupyter_server_config.py:
        >>> from e2x_jupyter_backup import get_post_save_hook
        >>> c.FileContentsManager.post_save_hook = get_post_save_hook()
    """
    app = E2xBackupApp()
    app.initialize()

    def post_save_hook(model, os_path, contents_manager, **kwargs):
        app.backup(model, os_path, contents_manager)

    return post_save_hook
