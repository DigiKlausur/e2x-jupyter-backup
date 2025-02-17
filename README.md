# e2x-jupyter-backup

The `e2x-jupyter-backup` package provides tools for creating and managing backups of Jupyter notebooks. It ensures that your work is safely stored and can be easily restored in case of data loss or corruption.

## Features

- Automated backups of Jupyter notebooks
- Easy restoration of backups
- Customizable backup schedules
- Support for multiple storage backends

## Installation

To install the package from the repository, use the following commands:

```bash
git clone https://github.com/Digiklausur/e2x-jupyter-backup.git
cd e2x-jupyter-backup
pip install .
```

## Usage

To configure the backups, you need to edit the `jupyter_backup_config.py` file located in the `jupyter` directory. 

Here is an example configuration:

```python
# jupyter_backup_config.py

c = get_config()

# Set the backup directory, relative to the notebook
c.BackupApp.backup_dir = '.backup'

# Maximum number of backup files to keep, set to 0 to disable backups
c.BackupApp.max_backup_files = 10
```

To enable the post save hook, you need to activate it in the `jupyter_notebook_config.py`file located in the `jupyter` directory.

```python
# jupyter_notebook_config.py
c = get_config()

# Enable the post save hook to automatically create backups
from e2x_jupyter_backup import get_post_save_hook
c.FileContentsManager.post_save_hook = get_post_save_hook()
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.