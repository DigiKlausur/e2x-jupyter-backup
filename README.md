# e2x-jupyter-backup

The `e2x-jupyter-backup` package provides automatic backup creation for Jupyter notebooks. It creates timestamped backups whenever you save a notebook, ensuring your work is safely stored.

## Features

- Automatic timestamped backups on notebook save
- Configurable backup retention (by count and total size)
- Support for both relative and absolute backup paths
- Smart backup intervals to avoid excessive backups
- Easy integration with JupyterLab and Jupyter Notebook

## Installation

To install the package from the repository, use the following commands:

```bash
git clone https://github.com/Digiklausur/e2x-jupyter-backup.git
cd e2x-jupyter-backup
pip install .
```

## Usage

### Enable Backup Hook

To enable automatic backups, add the following to your Jupyter configuration file (e.g., `jupyter_server_config.py`):

```python
# ~/.jupyter/jupyter_server_config.py
from e2x_jupyter_backup import get_post_save_hook

c.FileContentsManager.post_save_hook = get_post_save_hook()
```

### Configuration

To customize backup behavior, create a `jupyter_backup_config.py` file in your Jupyter config directory:

```python
# ~/.jupyter/jupyter_backup_config.py
c = get_config()

# Backup directory - can be relative (to each notebook) or absolute
# Default: '.backup'
c.E2xBackupApp.backup_dir = '.backup'

# Maximum number of backup files to keep per notebook
# Set to 0 to disable backups
# Default: 10
c.E2xBackupApp.max_backup_files = 10

# Maximum total size of all backups for a single notebook in MB
# Set to 0 to disable size limit
# Default: 100
c.E2xBackupApp.max_backup_size_mb = 100

# Minimum seconds between backups for the same notebook
# If you save within this interval, it may overwrite the most recent backup
# Default: 20
c.E2xBackupApp.min_seconds_between_backups = 20
```

### How It Works

**Backup Naming**: Backups are named with timestamps: `YYYY-MM-DD_HH-MM-SS_notebook.ipynb`

**Relative Paths** (default): When `backup_dir` is relative (e.g., `.backup`), backups are created in a subdirectory next to each notebook:
```
notebooks/
  my_notebook.ipynb
  .backup/
    2026-02-06_14-30-15_my_notebook.ipynb
    2026-02-06_15-45-22_my_notebook.ipynb
```

**Absolute Paths**: When `backup_dir` is absolute (e.g., `/home/user/backups`), the notebook's relative path from the Jupyter root is preserved:
```
/home/user/backups/
  project1/
    2026-02-06_14-30-15_notebook.ipynb
  project2/
    2026-02-06_15-45-22_analysis.ipynb
```

**Cleanup**: Old backups are automatically deleted based on:
- Count: Keeps only the most recent `max_backup_files` backups
- Size: Removes oldest backups if total size exceeds `max_backup_size_mb`

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.