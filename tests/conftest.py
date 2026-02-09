"""Shared fixtures for e2x-jupyter-backup tests."""

import os
from logging import Logger
from unittest.mock import MagicMock

import nbformat
import pytest

from e2x_jupyter_backup import E2xBackupApp


@pytest.fixture
def temp_notebook_dir(tmp_path):
    """Create a temporary directory structure for notebook testing."""
    notebook_dir = tmp_path / "notebooks"
    notebook_dir.mkdir()
    return notebook_dir


@pytest.fixture
def temp_backup_dir(tmp_path):
    """Create a temporary backup directory."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir


@pytest.fixture
def sample_notebook(temp_notebook_dir):
    """Create a sample notebook file."""
    notebook_path = temp_notebook_dir / "test_notebook.ipynb"
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("print('Hello, World!')"))

    nbformat.write(nb, notebook_path)
    return notebook_path


@pytest.fixture
def large_sample_notebook(temp_notebook_dir):
    """Create a large sample notebook file for testing pruning."""
    notebook_path = temp_notebook_dir / "large_notebook.ipynb"
    nb = nbformat.v4.new_notebook()
    for i in range(100):  # Add 100 code cells to create a large notebook
        nb.cells.append(nbformat.v4.new_code_cell(f"print('Cell {i}')"))
    nb.cells.append(nbformat.v4.new_markdown_cell("This is a test notebook." * 1000))
    nbformat.write(nb, notebook_path)
    return notebook_path


@pytest.fixture
def backup_app():
    """Create a basic E2xBackupApp instance."""
    app = E2xBackupApp()
    app.log = Logger("test_logger")
    return app


@pytest.fixture
def backup_app_with_absolute_backup_dir(tmp_path):
    """Create an E2xBackupApp instance with an absolute backup directory."""
    app = E2xBackupApp()
    app.log = Logger("test_logger")
    app.backup_dir = os.path.abspath(tmp_path / "absolute_backup_dir")
    return app


@pytest.fixture
def mock_contents_manager(temp_notebook_dir):
    """Create a mock ContentsManager."""
    manager = MagicMock()
    manager.root_dir = str(temp_notebook_dir)
    return manager


@pytest.fixture
def notebook_model():
    """Create a sample notebook model dictionary."""
    return {
        "type": "notebook",
        "name": "test_notebook.ipynb",
        "path": "test_notebook.ipynb",
    }


@pytest.fixture
def file_model():
    """Create a sample file model dictionary (not a notebook)."""
    return {
        "type": "file",
        "name": "test_file.txt",
        "path": "test_file.txt",
    }
