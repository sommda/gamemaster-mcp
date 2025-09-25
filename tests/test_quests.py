"""
Tests for quest management in DnDStorage.
"""

import pytest

from gamemaster_mcp.models import Quest


@pytest.fixture
def sample_quest():
    """Create a sample quest for testing."""
    return Quest(
        title="Find the Lost Sword",
        description="Retrieve the legendary sword from the ancient ruins",
        giver="Village Elder",
        status="active",
        objectives=["Enter the ruins", "Find the sword", "Return to village"],
        reward="500 gold pieces",
    )


class TestQuestManagement:
    """Test quest CRUD operations."""

    def test_add_quest(self, storage_with_campaign, sample_quest):
        """Test adding a quest to campaign."""
        storage_with_campaign.add_quest(sample_quest)

        retrieved = storage_with_campaign.get_quest(sample_quest.title)
        assert retrieved is not None
        assert retrieved.title == sample_quest.title
        assert retrieved.status == sample_quest.status
        assert retrieved.giver == sample_quest.giver

    def test_add_quest_no_campaign(self, temp_storage, sample_quest):
        """Test adding quest when no campaign is loaded."""
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_quest(sample_quest)

    def test_get_nonexistent_quest(self, storage_with_campaign):
        """Test getting a quest that doesn't exist."""
        quest = storage_with_campaign.get_quest("Nonexistent Quest")
        assert quest is None

    def test_update_quest_status(self, storage_with_campaign, sample_quest):
        """Test updating quest status."""
        storage_with_campaign.add_quest(sample_quest)

        storage_with_campaign.update_quest_status(sample_quest.title, "completed")

        updated = storage_with_campaign.get_quest(sample_quest.title)
        assert updated.status == "completed"

    def test_update_quest_status_nonexistent(self, storage_with_campaign):
        """Test updating status of quest that doesn't exist."""
        with pytest.raises(ValueError):
            storage_with_campaign.update_quest_status("Nonexistent Quest", "completed")

    def test_list_quests_empty(self, storage_with_campaign):
        """Test listing quests when none exist."""
        quests = storage_with_campaign.list_quests()
        assert isinstance(quests, list)
        assert len(quests) == 0

    def test_list_quests_all(self, storage_with_campaign, sample_quest):
        """Test listing all quests."""
        storage_with_campaign.add_quest(sample_quest)

        quests = storage_with_campaign.list_quests()
        assert len(quests) == 1
        assert sample_quest.title in quests

    def test_list_quests_by_status(self, storage_with_campaign):
        """Test listing quests filtered by status."""
        # Add quests with different statuses
        quest1 = Quest(title="Active Quest", description="Test", status="active")
        quest2 = Quest(title="Completed Quest", description="Test", status="completed")
        quest3 = Quest(title="Failed Quest", description="Test", status="failed")

        storage_with_campaign.add_quest(quest1)
        storage_with_campaign.add_quest(quest2)
        storage_with_campaign.add_quest(quest3)

        # Test filtering by status
        active_quests = storage_with_campaign.list_quests(status="active")
        assert len(active_quests) == 1
        assert "Active Quest" in active_quests

        completed_quests = storage_with_campaign.list_quests(status="completed")
        assert len(completed_quests) == 1
        assert "Completed Quest" in completed_quests

        failed_quests = storage_with_campaign.list_quests(status="failed")
        assert len(failed_quests) == 1
        assert "Failed Quest" in failed_quests

    def test_quest_objectives(self, storage_with_campaign):
        """Test quest with multiple objectives."""
        quest = Quest(
            title="Rescue Mission",
            description="Save the captured villagers",
            status="active",
            objectives=[
                "Locate the bandit hideout",
                "Infiltrate the camp",
                "Free the prisoners",
                "Escort villagers to safety",
            ],
        )

        storage_with_campaign.add_quest(quest)

        retrieved = storage_with_campaign.get_quest("Rescue Mission")
        assert len(retrieved.objectives) == 4
        assert "Locate the bandit hideout" in retrieved.objectives
        assert "Escort villagers to safety" in retrieved.objectives

    def test_quest_completion_tracking(self, storage_with_campaign):
        """Test tracking completed objectives."""
        quest = Quest(
            title="Gather Components",
            description="Collect magical components for the ritual",
            status="active",
            objectives=["Find moonstone", "Collect dragon scale", "Obtain phoenix feather"],
            completed_objectives=["Find moonstone"],  # One already completed
        )

        storage_with_campaign.add_quest(quest)

        retrieved = storage_with_campaign.get_quest("Gather Components")
        assert len(retrieved.objectives) == 3
        assert len(retrieved.completed_objectives) == 1
        assert "Find moonstone" in retrieved.completed_objectives
        assert retrieved.status == "active"  # Still active since not all objectives complete
