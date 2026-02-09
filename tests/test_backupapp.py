from unittest.mock import patch
from datetime import datetime
from pathlib import Path


class TestE2xBackupApp:
    """Tests for E2xBackupApp functionality."""

    def test_backup_notebook_with_backup_limit_set_to_one(
        self, backup_app, notebook_model, sample_notebook, mock_contents_manager
    ):
        """Test that a notebook is backed up correctly."""
        with patch("e2x_jupyter_backup.backup_app.datetime") as mock_datetime:
            # Set a fixed current time for testing
            fixed_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = fixed_time
            mock_datetime.strptime.side_effect = lambda s, fmt: datetime.strptime(s, fmt)

            backup_app.max_backup_files = 1  # Limit to 1 backup for testing
            backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)

            backup_files = backup_app.list_backups(
                Path(mock_contents_manager.root_dir) / ".backup", "test_notebook.ipynb"
            )
            assert len(backup_files) == 1
            assert backup_files[0].name.startswith("2024-01-01_12-00-00_test_notebook.ipynb")

            # Set a fixed current time for testing
            fixed_time = datetime(2024, 1, 1, 13, 0, 0)
            mock_datetime.now.return_value = fixed_time
            mock_datetime.strptime.side_effect = lambda s, fmt: datetime.strptime(s, fmt)
            backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)

            backup_files = backup_app.list_backups(
                Path(mock_contents_manager.root_dir) / ".backup", "test_notebook.ipynb"
            )
            assert len(backup_files) == 1  # Should still be 1 due to backup limit
            assert backup_files[0].name.startswith(
                "2024-01-01_13-00-00_test_notebook.ipynb"
            )  # Should be the new backup

    def test_backup_with_non_notebook_file(self, backup_app, mock_contents_manager):
        """Test that non-notebook files are not backed up."""
        model = {"type": "file", "name": "test_file.txt"}
        backup_app.backup(model, "test_file.txt", mock_contents_manager)
        backup_files = backup_app.list_backups(
            Path(mock_contents_manager.root_dir) / ".backup", "test_file.txt"
        )
        assert len(backup_files) == 0  # No backups should be created for non-notebook files

    def test_backup_disabled_by_max_backup_files(
        self, backup_app, notebook_model, sample_notebook, mock_contents_manager
    ):
        """Test that no backups are created when max_backup_files is set to 0."""
        backup_app.max_backup_files = 0  # Disable backups
        backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)
        backup_files = backup_app.list_backups(
            Path(mock_contents_manager.root_dir) / ".backup", "test_notebook.ipynb"
        )
        assert len(backup_files) == 0  # No backups should be created when disabled

    def test_backup_disabled_by_max_backup_size_mb(
        self, backup_app, notebook_model, sample_notebook, mock_contents_manager
    ):
        """Test that no backups are created when max_backup_size_mb is set to 0."""
        backup_app.max_backup_size_mb = 0  # Disable backups
        backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)
        backup_files = backup_app.list_backups(
            Path(mock_contents_manager.root_dir) / ".backup", "test_notebook.ipynb"
        )
        assert len(backup_files) == 0  # No backups should be created when disabled

    def test_skip_backup_with_same_timestamp(
        self, backup_app, notebook_model, sample_notebook, mock_contents_manager
    ):
        """Test that a backup is overwritten if created within min_seconds_between_backups."""
        with patch("e2x_jupyter_backup.backup_app.datetime") as mock_datetime:
            fixed_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = fixed_time
            mock_datetime.strptime.side_effect = lambda s, fmt: datetime.strptime(s, fmt)

            backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)
            backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)
            backup_files = backup_app.list_backups(
                Path(mock_contents_manager.root_dir) / ".backup", "test_notebook.ipynb"
            )
            assert len(backup_files) == 1  # Should still be 1 due to overwrite
            assert backup_files[0].name.startswith(
                "2024-01-01_12-00-00_test_notebook.ipynb"
            )  # Should be the new backup

    def test_prune_backups_by_file_count(
        self, backup_app, notebook_model, sample_notebook, mock_contents_manager
    ):
        """Test that old backups are pruned when max_backup_files is exceeded."""
        with patch("e2x_jupyter_backup.backup_app.datetime") as mock_datetime:
            base_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = base_time
            mock_datetime.strptime.side_effect = lambda s, fmt: datetime.strptime(s, fmt)

            backup_app.max_backup_files = 3
            for i in range(5):
                current_time = base_time.replace(hour=base_time.hour + i)
                mock_datetime.now.return_value = current_time
                backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)

            backup_files = sorted(
                backup_app.list_backups(
                    Path(mock_contents_manager.root_dir) / ".backup", "test_notebook.ipynb"
                ),
                reverse=True,
            )
            assert len(backup_files) == 3  # Should only keep the latest 3 backups
            assert backup_files[0].name.startswith(
                "2024-01-01_16-00-00_test_notebook.ipynb"
            )  # Latest backup
            assert backup_files[1].name.startswith(
                "2024-01-01_15-00-00_test_notebook.ipynb"
            )  # Second latest backup
            assert backup_files[2].name.startswith(
                "2024-01-01_14-00-00_test_notebook.ipynb"
            )  # Third latest backup

    def test_prune_backups_by_total_size(
        self, backup_app, notebook_model, large_sample_notebook, mock_contents_manager
    ):
        """Test that old backups are pruned when total size exceeds max_backup_size_mb."""
        with patch("e2x_jupyter_backup.backup_app.datetime") as mock_datetime:
            base_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = base_time
            mock_datetime.strptime.side_effect = lambda s, fmt: datetime.strptime(s, fmt)

            backup_app.max_backup_size_mb = 1
            backup_app.max_backup_files = -1  # No file count limit
            start_size = large_sample_notebook.stat().st_size / (1024 * 1024)
            max_backups = (
                int(backup_app.max_backup_size_mb / start_size) + 1
            )  # Calculate how many backups can fit within size limit
            for i in range(max_backups):
                current_time = base_time.replace(minute=base_time.minute + i)
                mock_datetime.now.return_value = current_time
                backup_app.backup(notebook_model, str(large_sample_notebook), mock_contents_manager)

            backup_files = backup_app.list_backups(
                Path(mock_contents_manager.root_dir) / ".backup", "large_notebook.ipynb"
            )
            assert (
                len(backup_files) < max_backups
            )  # Should have pruned some backups due to size limit

    def test_min_seconds_between_backups(
        self, backup_app, notebook_model, sample_notebook, mock_contents_manager
    ):
        """Test that backups are not created if min_seconds_between_backups is not met."""
        with patch("e2x_jupyter_backup.backup_app.datetime") as mock_datetime:
            base_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = base_time
            mock_datetime.strptime.side_effect = lambda s, fmt: datetime.strptime(s, fmt)

            backup_app.min_seconds_between_backups = 5  # 5 seconds
            backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)

            # Create a second backup
            current_time = base_time.replace(second=base_time.second + 3)
            mock_datetime.now.return_value = current_time
            backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)

            # Create a new backup within the min_seconds_between_backups window (should remove the previous backup)
            current_time = base_time.replace(second=base_time.second + 6)
            mock_datetime.now.return_value = current_time
            backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)

            backup_files = backup_app.list_backups(
                Path(mock_contents_manager.root_dir) / ".backup", "test_notebook.ipynb"
            )
            assert (
                len(backup_files) == 2
            )  # Should only have 2 backups due to overwrite of the second backup

            # Create a fourth backup
            current_time = base_time.replace(second=base_time.second + 9)
            mock_datetime.now.return_value = current_time
            backup_app.backup(notebook_model, str(sample_notebook), mock_contents_manager)

            backup_files = backup_app.list_backups(
                Path(mock_contents_manager.root_dir) / ".backup", "test_notebook.ipynb"
            )
            assert (
                len(backup_files) == 3
            )  # Should only have 3 backups due to time between last two backups being greater than min_seconds_between_backups

    def test_backup_with_absolute_backup_dir(
        self,
        backup_app_with_absolute_backup_dir,
        notebook_model,
        sample_notebook,
        mock_contents_manager,
    ):
        """Test that backups are created in the correct absolute backup directory."""
        with patch("e2x_jupyter_backup.backup_app.datetime") as mock_datetime:
            fixed_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = fixed_time
            mock_datetime.strptime.side_effect = lambda s, fmt: datetime.strptime(s, fmt)

            backup_app_with_absolute_backup_dir.backup(
                notebook_model, str(sample_notebook), mock_contents_manager
            )
            backup_files = backup_app_with_absolute_backup_dir.list_backups(
                Path(backup_app_with_absolute_backup_dir.backup_dir), "test_notebook.ipynb"
            )
            assert len(backup_files) == 1
            assert backup_files[0].name.startswith("2024-01-01_12-00-00_test_notebook.ipynb")
