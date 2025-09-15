"""
Tests for campaign management in DnDStorage.
"""

import pytest
from gamemaster_mcp.storage import DnDStorage


class TestCampaignManagement:
    """Test campaign CRUD operations."""

    def test_create_campaign(self, temp_storage, sample_campaign):
        """Test creating a new campaign."""
        created = temp_storage.create_campaign(
            name=sample_campaign.name,
            description=sample_campaign.description,
            dm_name=sample_campaign.dm_name,
            setting=sample_campaign.setting,
        )

        assert created.name == sample_campaign.name
        assert created.description == sample_campaign.description
        assert created.dm_name == sample_campaign.dm_name
        assert created.setting == sample_campaign.setting

        # Should be set as current campaign
        current = temp_storage.get_current_campaign()
        assert current is not None
        assert current.name == sample_campaign.name

    def test_create_campaign_saves_to_file(self, temp_storage, sample_campaign):
        """Test that creating a campaign saves it to disk."""
        temp_storage.create_campaign(sample_campaign.name, sample_campaign.description)

        # Check file exists
        campaign_file = temp_storage._get_campaign_file()
        assert campaign_file.exists()

    def test_list_campaigns_empty(self, temp_storage):
        """Test listing campaigns when none exist."""
        campaigns = temp_storage.list_campaigns()
        assert isinstance(campaigns, list)
        assert len(campaigns) == 0

    def test_list_campaigns_with_data(self, temp_storage, sample_campaign):
        """Test listing campaigns after creating one."""
        temp_storage.create_campaign(sample_campaign.name, sample_campaign.description)

        campaigns = temp_storage.list_campaigns()
        assert len(campaigns) == 1
        assert sample_campaign.name in campaigns

    def test_load_campaign(self, temp_storage):
        """Test loading a specific campaign."""
        # Create two campaigns
        temp_storage.create_campaign("Campaign 1", "First campaign")
        temp_storage.create_campaign("Campaign 2", "Second campaign")

        # Load the first one
        loaded = temp_storage.load_campaign("Campaign 1")
        assert loaded.name == "Campaign 1"
        assert loaded.description == "First campaign"

        # Should be current campaign
        current = temp_storage.get_current_campaign()
        assert current.name == "Campaign 1"

    def test_load_nonexistent_campaign(self, temp_storage):
        """Test loading a campaign that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            temp_storage.load_campaign("Nonexistent Campaign")

    def test_update_campaign(self, temp_storage, sample_campaign):
        """Test updating campaign properties."""
        temp_storage.create_campaign(sample_campaign.name, sample_campaign.description)

        temp_storage.update_campaign(
            description="Updated description", dm_name="New DM", world_notes="Some world notes"
        )

        updated = temp_storage.get_current_campaign()
        assert updated.description == "Updated description"
        assert updated.dm_name == "New DM"
        assert updated.world_notes == "Some world notes"
