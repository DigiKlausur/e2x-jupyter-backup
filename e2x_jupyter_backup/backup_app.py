import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from jupyter_core.application import JupyterApp
from traitlets import Int, Unicode

from ._version import __version__


class E2xBackupApp(JupyterApp):
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
    backup_dir = Unicode(".backup", config=True, help="Directory to store backups in")

    def prune_old_backups(self, backup_dir, filename):
        backup_files = sorted(backup_dir.glob(f"*_{filename}"), reverse=True)
        for old_backup in backup_files[self.max_backup_files :]:
            old_backup.unlink()
            self.log.info(f"Deleted old backup {old_backup}")

    def backup(self, model, os_path, contents_manager):
        if model["type"] != "notebook":
            return
        if self.max_backup_files <= 0:
            self.log.info("Backup disabled")
            return
        directory, filename = os.path.split(os_path)
        backup_dir = Path(directory) / self.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)  # Ensure backup directory exists

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"{timestamp}_{filename}"
        backup_path = backup_dir / backup_filename

        # Skip backup if it already exists for this timestamp
        if backup_path.exists():
            return

        shutil.copy2(os_path, backup_path)
        self.log.info(f"Backed up {os_path} to {backup_path}")

        # Prune old backups
        self.prune_old_backups(backup_dir, filename)


def get_post_save_hook() -> Callable:
    """
    Return a post-save hook that backs up notebooks to a local directory

    Returns:
        Callable: Post-save hook function
    """
    app = E2xBackupApp()
    app.initialize()

    def post_save_hook(model, os_path, contents_manager, **kwargs):
        app.backup(model, os_path, contents_manager)

    return post_save_hook
