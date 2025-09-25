"""
Tests for DnDStorage initialization and basic functionality.
"""


class TestStorageInitialization:
    """Test storage initialization and basic functionality."""

    def test_storage_creates_directories(self, temp_storage):
        """Test that storage creates necessary directories."""
        assert temp_storage.data_dir.exists()
        assert (temp_storage.data_dir / "campaigns").exists()
        assert (temp_storage.data_dir / "events").exists()

    def test_storage_starts_with_no_campaign(self, temp_storage):
        """Test that storage starts with no current campaign."""
        assert temp_storage.get_current_campaign() is None

    def test_storage_starts_with_empty_events(self, temp_storage):
        """Test that storage starts with empty events list."""
        events = temp_storage.get_events()
        assert isinstance(events, list)
        assert len(events) == 0
