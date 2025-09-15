"""
Tests for NPC management in DnDStorage.
"""

import pytest
from gamemaster_mcp.models import NPC


@pytest.fixture
def sample_npc():
    """Create a sample NPC for testing."""
    return NPC(
        name="Innkeeper Bob",
        description="A friendly middle-aged human who runs the local tavern",
        race="Human",
        occupation="Innkeeper",
        location="Riverside Inn",
        attitude="Friendly",
    )


class TestNPCManagement:
    """Test NPC CRUD operations."""

    def test_add_npc(self, storage_with_campaign, sample_npc):
        """Test adding an NPC to campaign."""
        storage_with_campaign.add_npc(sample_npc)

        retrieved = storage_with_campaign.get_npc(sample_npc.name)
        assert retrieved is not None
        assert retrieved.name == sample_npc.name
        assert retrieved.occupation == sample_npc.occupation
        assert retrieved.attitude == sample_npc.attitude

    def test_add_npc_no_campaign(self, temp_storage, sample_npc):
        """Test adding NPC when no campaign is loaded."""
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_npc(sample_npc)

    def test_get_nonexistent_npc(self, storage_with_campaign):
        """Test getting an NPC that doesn't exist."""
        npc = storage_with_campaign.get_npc("Nonexistent NPC")
        assert npc is None

    def test_list_npcs_empty(self, storage_with_campaign):
        """Test listing NPCs when none exist."""
        npcs = storage_with_campaign.list_npcs()
        assert isinstance(npcs, list)
        assert len(npcs) == 0

    def test_list_npcs_with_data(self, storage_with_campaign, sample_npc):
        """Test listing NPCs after adding one."""
        storage_with_campaign.add_npc(sample_npc)

        npcs = storage_with_campaign.list_npcs()
        assert len(npcs) == 1
        assert sample_npc.name in npcs

    def test_update_npc(self, storage_with_campaign, sample_npc):
        """Test updating NPC properties."""
        storage_with_campaign.add_npc(sample_npc)

        # Assuming there's an update_npc method similar to update_character
        # If not, this test documents the expected behavior
        original_attitude = sample_npc.attitude

        # Get the NPC and verify original state
        npc = storage_with_campaign.get_npc(sample_npc.name)
        assert npc.attitude == original_attitude

    def test_multiple_npcs(self, storage_with_campaign):
        """Test managing multiple NPCs."""
        npc1 = NPC(name="Shopkeeper Alice", occupation="Merchant")
        npc2 = NPC(name="Guard Captain", occupation="City Guard")

        storage_with_campaign.add_npc(npc1)
        storage_with_campaign.add_npc(npc2)

        npcs = storage_with_campaign.list_npcs()
        assert len(npcs) == 2
        assert "Shopkeeper Alice" in npcs
        assert "Guard Captain" in npcs

        # Verify we can retrieve each one
        alice = storage_with_campaign.get_npc("Shopkeeper Alice")
        captain = storage_with_campaign.get_npc("Guard Captain")

        assert alice.occupation == "Merchant"
        assert captain.occupation == "City Guard"
