"""
Tests for transcript tree storage layer.

Tests cover:
- Loading and saving transcript trees
- Current parent tracking
- Tree manipulation (add interaction, start/end combat, start/end adventure)
- Migration from old flat format to new tree format
- Tree traversal and search
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from gamemaster_mcp.storage import DnDStorage
from gamemaster_mcp.models import (
    Campaign,
    GameState,
    TranscriptTree,
    TranscriptInteraction,
    TranscriptCombat,
    TranscriptAdventure,
    ResponseText,
    ResponseTools,
    InteractionToolCall,
)


@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary storage instance."""
    storage = DnDStorage(data_dir=tmp_path)
    return storage


@pytest.fixture
def storage_with_campaign(temp_storage):
    """Create storage with a test campaign."""
    campaign = temp_storage.create_campaign(
        name="Test Campaign",
        description="A test campaign",
        dm_name="Test DM"
    )
    return temp_storage


class TestTranscriptTreeCreation:
    """Test creating and loading transcript trees."""

    def test_create_empty_transcript(self, storage_with_campaign):
        """Test creating an empty transcript tree."""
        campaign = storage_with_campaign.get_current_campaign()

        # Create empty transcript
        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[]
        )

        storage_with_campaign._save_transcript(transcript)

        # Load it back
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)

        assert loaded is not None
        assert loaded.campaign == "Test Campaign"
        assert loaded.session_number == 1
        assert len(loaded.children) == 0
        assert loaded.current_parent_id is None

    def test_save_and_load_transcript_with_interactions(self, storage_with_campaign):
        """Test saving and loading transcript with interactions."""
        campaign = storage_with_campaign.get_current_campaign()

        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[
                TranscriptInteraction(
                    user_text="I look around",
                    responses=[ResponseText(content="You see a dark corridor")]
                ),
                TranscriptInteraction(
                    user_text="I move forward",
                    responses=[ResponseText(content="You enter the corridor")]
                )
            ]
        )

        storage_with_campaign._save_transcript(transcript)
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)

        assert len(loaded.children) == 2
        assert loaded.children[0].user_text == "I look around"
        assert loaded.children[1].user_text == "I move forward"

    def test_save_transcript_with_full_tree(self, storage_with_campaign):
        """Test saving complex tree with combat and adventure nodes."""
        campaign = storage_with_campaign.get_current_campaign()

        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[
                TranscriptInteraction(
                    user_text="We enter the dungeon",
                    responses=[ResponseText(content="You see darkness")]
                ),
                TranscriptCombat(
                    participants=["Gareth", "Goblin"],
                    result="victory",
                    summary="Quick fight with goblin",
                    actions=[
                        TranscriptInteraction(
                            user_text="I attack",
                            responses=[ResponseText(content="Hit!")]
                        )
                    ],
                    location="Dungeon entrance"
                ),
                TranscriptAdventure(
                    title="Find the Key",
                    summary="Retrieved the ancient key",
                    actions=[
                        TranscriptInteraction(
                            user_text="We search the room",
                            responses=[ResponseText(content="You find a key")]
                        )
                    ]
                )
            ]
        )

        storage_with_campaign._save_transcript(transcript)
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)

        assert len(loaded.children) == 3
        assert loaded.children[0].node_type == "interaction"
        assert loaded.children[1].node_type == "combat"
        assert loaded.children[1].location == "Dungeon entrance"
        assert len(loaded.children[1].actions) == 1
        assert loaded.children[2].node_type == "adventure"
        assert loaded.children[2].title == "Find the Key"


class TestCurrentParentTracking:
    """Test current parent node tracking."""

    def test_initial_current_parent_is_root(self, storage_with_campaign):
        """Test that initial current parent is the transcript root."""
        campaign = storage_with_campaign.get_current_campaign()

        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[]
        )

        storage_with_campaign._save_transcript(transcript)

        # Current parent should default to transcript root ID
        parent_id = storage_with_campaign.get_current_parent_id(campaign.name)
        assert parent_id is None or parent_id == transcript.id

    def test_set_and_get_current_parent(self, storage_with_campaign):
        """Test setting and getting current parent."""
        campaign = storage_with_campaign.get_current_campaign()

        # Set current parent
        test_id = "test_node_123"
        storage_with_campaign.set_current_parent_id(campaign.name, test_id)

        # Get it back
        parent_id = storage_with_campaign.get_current_parent_id(campaign.name)
        assert parent_id == test_id

    def test_current_parent_persists_in_transcript(self, storage_with_campaign):
        """Test that current_parent_id is saved in transcript metadata."""
        campaign = storage_with_campaign.get_current_campaign()

        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[],
            current_parent_id="combat_node_456"
        )

        storage_with_campaign._save_transcript(transcript)
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)

        assert loaded.current_parent_id == "combat_node_456"


class TestTreeManipulation:
    """Test tree manipulation methods."""

    def test_add_interaction_to_root(self, storage_with_campaign):
        """Test adding interaction to transcript root."""
        campaign = storage_with_campaign.get_current_campaign()

        # Start with empty transcript
        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[]
        )
        storage_with_campaign._save_transcript(transcript)
        storage_with_campaign.set_current_parent_id(campaign.name, transcript.id)

        # Add interaction
        interaction = storage_with_campaign.add_transcript_interaction(
            user_text="Test input",
            responses=[{"type": "text", "content": "Test response"}]
        )

        # Load and verify
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)
        assert len(loaded.children) == 1
        assert loaded.children[0].user_text == "Test input"

    def test_start_combat_creates_node_and_updates_parent(self, storage_with_campaign):
        """Test starting combat creates node and sets it as current parent."""
        campaign = storage_with_campaign.get_current_campaign()

        # Start with empty transcript
        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[]
        )
        storage_with_campaign._save_transcript(transcript)

        # Start combat
        combat = storage_with_campaign.start_transcript_combat(
            participants=["Gareth", "Orc"],
            location="Dark Cave"
        )

        # Current parent should be combat node
        parent_id = storage_with_campaign.get_current_parent_id(campaign.name)
        assert parent_id == combat.id

        # Combat should be in transcript children
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)
        assert len(loaded.children) == 1
        assert loaded.children[0].node_type == "combat"
        assert loaded.children[0].participants == ["Gareth", "Orc"]

    def test_add_interaction_to_combat(self, storage_with_campaign):
        """Test adding interactions to active combat."""
        campaign = storage_with_campaign.get_current_campaign()

        # Create transcript and start combat
        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[]
        )
        storage_with_campaign._save_transcript(transcript)

        combat = storage_with_campaign.start_transcript_combat(
            participants=["Gareth", "Orc"]
        )

        # Add interactions (should go to combat)
        storage_with_campaign.add_transcript_interaction(
            user_text="I attack",
            responses=[{"type": "text", "content": "Hit!"}]
        )
        storage_with_campaign.add_transcript_interaction(
            user_text="I attack again",
            responses=[{"type": "text", "content": "Miss!"}]
        )

        # Verify interactions are in combat
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)
        combat_node = loaded.children[0]
        assert len(combat_node.actions) == 2
        assert combat_node.actions[0].user_text == "I attack"
        assert combat_node.actions[1].user_text == "I attack again"

    def test_end_combat_finalizes_and_restores_parent(self, storage_with_campaign):
        """Test ending combat sets summary and restores parent."""
        campaign = storage_with_campaign.get_current_campaign()

        # Setup
        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[]
        )
        storage_with_campaign._save_transcript(transcript)

        original_parent = transcript.id
        combat = storage_with_campaign.start_transcript_combat(
            participants=["Gareth", "Orc"]
        )

        # End combat
        storage_with_campaign.end_transcript_combat(
            result="victory",
            summary="Defeated orc in 2 rounds",
            casualties=["Orc"]
        )

        # Current parent should be restored to root
        parent_id = storage_with_campaign.get_current_parent_id(campaign.name)
        assert parent_id == original_parent

        # Combat should have summary
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)
        combat_node = loaded.children[0]
        assert combat_node.result == "victory"
        assert combat_node.summary == "Defeated orc in 2 rounds"
        assert combat_node.casualties == ["Orc"]

    def test_start_adventure_creates_node(self, storage_with_campaign):
        """Test starting adventure creates node and sets as current parent."""
        campaign = storage_with_campaign.get_current_campaign()

        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[]
        )
        storage_with_campaign._save_transcript(transcript)

        # Start adventure
        adventure = storage_with_campaign.start_transcript_adventure(
            title="The Lost Temple"
        )

        # Current parent should be adventure
        parent_id = storage_with_campaign.get_current_parent_id(campaign.name)
        assert parent_id == adventure.id

        # Adventure in transcript
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)
        assert len(loaded.children) == 1
        assert loaded.children[0].node_type == "adventure"
        assert loaded.children[0].title == "The Lost Temple"

    def test_combat_within_adventure(self, storage_with_campaign):
        """Test starting combat within an adventure."""
        campaign = storage_with_campaign.get_current_campaign()

        transcript = TranscriptTree(
            campaign=campaign.name,
            session_number=1,
            children=[]
        )
        storage_with_campaign._save_transcript(transcript)

        # Start adventure
        adventure = storage_with_campaign.start_transcript_adventure(
            title="Temple Quest"
        )
        adventure_id = adventure.id

        # Add interaction to adventure
        storage_with_campaign.add_transcript_interaction(
            user_text="We enter temple",
            responses=[{"type": "text", "content": "You see..."}]
        )

        # Start combat (should be child of adventure)
        combat = storage_with_campaign.start_transcript_combat(
            participants=["Gareth", "Guardian"]
        )

        # Add combat interaction
        storage_with_campaign.add_transcript_interaction(
            user_text="I fight",
            responses=[{"type": "text", "content": "Hit!"}]
        )

        # End combat (parent should return to adventure)
        storage_with_campaign.end_transcript_combat(
            result="victory",
            summary="Defeated guardian"
        )

        parent_id = storage_with_campaign.get_current_parent_id(campaign.name)
        assert parent_id == adventure_id

        # Verify structure
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)
        adventure_node = loaded.children[0]
        assert len(adventure_node.actions) == 2  # interaction + combat
        assert adventure_node.actions[0].node_type == "interaction"
        assert adventure_node.actions[1].node_type == "combat"
        assert len(adventure_node.actions[1].actions) == 1  # combat interaction


class TestMigration:
    """Test migration from old flat format to new tree format."""

    def test_detect_old_format(self, storage_with_campaign):
        """Test detecting old transcript format."""
        campaign = storage_with_campaign.get_current_campaign()
        transcript_dir = storage_with_campaign._get_transcript_dir(campaign.name)
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = transcript_dir / "session_1.json"

        # Write old format
        old_data = {
            "id": "old123",
            "campaign": campaign.name,
            "session_number": 1,
            "entries": [
                {
                    "transcript_id": "old123",
                    "timestamp": "2025-01-15T10:00:00",
                    "player_entry": "I attack",
                    "game_response": "Roll for attack"
                }
            ]
        }

        with open(transcript_file, 'w') as f:
            json.dump(old_data, f)

        # Load should migrate
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)

        # Should be new format
        assert hasattr(loaded, 'children')
        assert not hasattr(loaded, 'entries')
        assert len(loaded.children) == 1
        assert loaded.children[0].user_text == "I attack"
        assert loaded.children[0].responses[0].content == "Roll for attack"

    def test_migration_creates_backup(self, storage_with_campaign):
        """Test that migration creates backup of old file."""
        campaign = storage_with_campaign.get_current_campaign()
        transcript_dir = storage_with_campaign._get_transcript_dir(campaign.name)
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = transcript_dir / "session_1.json"

        # Write old format
        old_data = {
            "id": "old123",
            "campaign": campaign.name,
            "session_number": 1,
            "entries": []
        }

        with open(transcript_file, 'w') as f:
            json.dump(old_data, f)

        # Load (triggers migration)
        storage_with_campaign._load_transcript(campaign.name, 1)

        # Backup should exist
        backup_file = transcript_dir / "session_1.json.old"
        assert backup_file.exists()

    def test_migrate_multiple_entries(self, storage_with_campaign):
        """Test migrating transcript with multiple entries."""
        campaign = storage_with_campaign.get_current_campaign()
        transcript_dir = storage_with_campaign._get_transcript_dir(campaign.name)
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = transcript_dir / "session_1.json"

        # Write old format with multiple entries
        old_data = {
            "id": "old123",
            "campaign": campaign.name,
            "session_number": 1,
            "entries": [
                {
                    "transcript_id": "old123",
                    "timestamp": "2025-01-15T10:00:00",
                    "player_entry": "Entry 1",
                    "game_response": "Response 1"
                },
                {
                    "transcript_id": "old123",
                    "timestamp": "2025-01-15T10:05:00",
                    "player_entry": "Entry 2",
                    "game_response": "Response 2"
                },
                {
                    "transcript_id": "old123",
                    "timestamp": "2025-01-15T10:10:00",
                    "player_entry": "Entry 3",
                    "game_response": "Response 3"
                }
            ]
        }

        with open(transcript_file, 'w') as f:
            json.dump(old_data, f)

        # Load and migrate
        loaded = storage_with_campaign._load_transcript(campaign.name, 1)

        # All entries should become interactions
        assert len(loaded.children) == 3
        for i, child in enumerate(loaded.children, 1):
            assert child.node_type == "interaction"
            assert child.user_text == f"Entry {i}"
            assert child.responses[0].content == f"Response {i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
