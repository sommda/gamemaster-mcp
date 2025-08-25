"""
Tests for data persistence across DnDStorage instances.
"""

import pytest
import tempfile
import shutil
from gamemaster_mcp.storage import DnDStorage
from gamemaster_mcp.models import (
    Character, NPC, Location, Quest, AdventureEvent, EventType,
    CharacterClass, Race, AbilityScore, SessionNote
)
from datetime import datetime
from pathlib import Path


class TestStoragePersistence:
    """Test data persistence across storage instances."""
    
    def test_campaign_persists_across_instances(self, temp_dir, sample_campaign):
        """Test that campaigns persist when creating new storage instances."""
        # Create storage and campaign
        storage1 = DnDStorage(temp_dir)
        storage1.create_campaign(sample_campaign.name, sample_campaign.description)
        
        # Create new storage instance
        storage2 = DnDStorage(temp_dir)
        
        # Should load the most recent campaign
        current = storage2.get_current_campaign()
        assert current is not None
        assert current.name == sample_campaign.name
        assert current.description == sample_campaign.description
    
    def test_events_persist_across_instances(self, temp_dir):
        """Test that events persist when creating new storage instances."""
        # Create storage and event
        storage1 = DnDStorage(temp_dir)
        event = AdventureEvent(
            campaign="Test Campaign",
            event_type=EventType.SESSION,
            title="Session Start",
            description="The campaign begins",
            importance=1
        )
        storage1.add_event(event)
        
        # Create new storage instance
        storage2 = DnDStorage(temp_dir)
        
        # Should load the events
        events = storage2.get_events()
        assert len(events) == 1
        assert events[0].title == "Session Start"
    
    def test_character_data_persists(self, temp_dir):
        """Test that character data persists across instances."""
        character = Character(
            name="Persistent Hero",
            player_name="Test Player",
            character_class=CharacterClass(name="Paladin", level=3),
            race=Race(name="Dragonborn"),
            abilities={
                "strength": AbilityScore(score=16),
                "charisma": AbilityScore(score=14)
            },
            hit_points_max=25,
            hit_points_current=20,
            armor_class=18
        )
        
        # Create storage, campaign, and character
        storage1 = DnDStorage(temp_dir)
        storage1.create_campaign("Test Campaign", "Test description")
        storage1.add_character(character)
        
        # Create new storage instance
        storage2 = DnDStorage(temp_dir)
        
        # Character should persist
        retrieved = storage2.get_character("Persistent Hero")
        assert retrieved is not None
        assert retrieved.player_name == "Test Player"
        assert retrieved.character_class.name == "Paladin"
        assert retrieved.character_class.level == 3
        assert retrieved.hit_points_current == 20
    
    def test_quest_progress_persists(self, temp_dir):
        """Test that quest progress persists across instances."""
        quest = Quest(
            title="The Persistent Quest",
            description="A quest that should survive storage reloads",
            status="active",
            objectives=["Find the artifact", "Return to questgiver"],
            completed_objectives=["Find the artifact"],
            giver="Persistent NPC",
            reward="100 gold"
        )
        
        # Create storage, campaign, and quest
        storage1 = DnDStorage(temp_dir)
        storage1.create_campaign("Test Campaign", "Test description")
        storage1.add_quest(quest)
        
        # Update quest status
        storage1.update_quest_status("The Persistent Quest", "completed")
        
        # Create new storage instance
        storage2 = DnDStorage(temp_dir)
        
        # Quest and its updates should persist
        retrieved = storage2.get_quest("The Persistent Quest")
        assert retrieved is not None
        assert retrieved.status == "completed"
        assert "Find the artifact" in retrieved.completed_objectives
        assert retrieved.giver == "Persistent NPC"
    
    def test_game_state_persists(self, temp_dir):
        """Test that game state persists across instances."""
        # Create storage, campaign, and update game state
        storage1 = DnDStorage(temp_dir)
        storage1.create_campaign("Test Campaign", "Test description")
        storage1.update_game_state(
            current_location="Persistent Tavern",
            party_level=4,
            party_funds="500 gold",
            current_session=3,
            in_combat=False
        )
        
        # Create new storage instance
        storage2 = DnDStorage(temp_dir)
        
        # Game state should persist
        game_state = storage2.get_game_state()
        assert game_state is not None
        assert game_state.current_location == "Persistent Tavern"
        assert game_state.party_level == 4
        assert game_state.party_funds == "500 gold"
        assert game_state.current_session == 3
        assert game_state.in_combat is False
    
    def test_session_notes_persist(self, temp_dir):
        """Test that session notes persist across instances."""
        session = SessionNote(
            session_number=5,
            date=datetime(2024, 3, 15),
            title="Persistent Session",
            summary="This session should persist across storage reloads",
            events=["Event 1", "Event 2", "Event 3"],
            characters_present=["Hero1", "Hero2"],
            experience_gained=250
        )
        
        # Create storage, campaign, and session
        storage1 = DnDStorage(temp_dir)
        storage1.create_campaign("Test Campaign", "Test description")
        storage1.add_session_note(session)
        
        # Create new storage instance
        storage2 = DnDStorage(temp_dir)
        
        # Session should persist
        sessions = storage2.get_sessions()
        assert len(sessions) == 1
        assert sessions[0].title == "Persistent Session"
        assert sessions[0].session_number == 5
        assert len(sessions[0].events) == 3
        assert sessions[0].experience_gained == 250
    
    def test_multiple_campaigns_persist(self, temp_dir):
        """Test that multiple campaigns can be saved and loaded."""
        # Create storage and multiple campaigns
        storage1 = DnDStorage(temp_dir)
        storage1.create_campaign("Campaign One", "First campaign")
        storage1.create_campaign("Campaign Two", "Second campaign")
        storage1.create_campaign("Campaign Three", "Third campaign")
        
        # Create new storage instance
        storage2 = DnDStorage(temp_dir)
        
        # All campaigns should be available
        campaigns = storage2.list_campaigns()
        assert len(campaigns) == 3
        assert "Campaign One" in campaigns
        assert "Campaign Two" in campaigns
        assert "Campaign Three" in campaigns
        
        # Should load the most recent (Campaign Three)
        current = storage2.get_current_campaign()
        assert current.name == "Campaign Three"
        
        # Should be able to load other campaigns
        loaded = storage2.load_campaign("Campaign One")
        assert loaded.name == "Campaign One"
        assert loaded.description == "First campaign"
    
    def test_file_structure_maintained(self, temp_dir):
        """Test that the expected file structure is maintained."""
        # Create storage with data
        storage1 = DnDStorage(temp_dir)
        storage1.create_campaign("File Test Campaign", "Testing file structure")
        
        event = AdventureEvent(
            campaign="Test Campaign",
            event_type=EventType.WORLD,
            title="World Event",
            description="Something happened in the world",
            importance=1
        )
        storage1.add_event(event)
        
        # Check file structure
        data_dir = Path(temp_dir)
        assert (data_dir / "campaigns").exists()
        assert (data_dir / "events").exists()
        
        # Check specific files
        campaign_files = list((data_dir / "campaigns").glob("*.json"))
        assert len(campaign_files) == 1
        assert "File Test Campaign" in campaign_files[0].name
        
        events_file = data_dir / "events" / "adventure_log.json"
        assert events_file.exists()
        
        # Create new storage instance and verify it can read the files
        storage2 = DnDStorage(temp_dir)
        assert storage2.get_current_campaign() is not None
        assert len(storage2.get_events()) == 1
    
    def test_data_integrity_across_instances(self, temp_dir):
        """Test that complex data maintains integrity across instances."""
        # Create a complex campaign with interconnected data
        storage1 = DnDStorage(temp_dir)
        storage1.create_campaign("Integrity Test", "Testing data integrity")
        
        # Add character
        character = Character(
            name="Test Hero",
            character_class=CharacterClass(name="Ranger", level=7),
            race=Race(name="Elf", traits=["Darkvision", "Keen Senses"]),
            abilities={
                "strength": AbilityScore(score=14),
                "dexterity": AbilityScore(score=18),
                "wisdom": AbilityScore(score=16)
            }
        )
        storage1.add_character(character)
        
        # Add related NPC
        npc = NPC(
            name="Quest Giver",
            description="An old wizard with a mysterious past",
            location="Tower",
            relationships={"Test Hero": "Mentor"}
        )
        storage1.add_npc(npc)
        
        # Add location
        location = Location(
            name="Tower",
            location_type="wizard tower",
            description="an old wizard tower",
            npcs=["Quest Giver"],
            connections=["Village", "Forest"]
        )
        storage1.add_location(location)
        
        # Add quest
        quest = Quest(
            title="Tower Defense",
            description="Protect the tower from invaders",
            giver="Quest Giver",
            status="active"
        )
        storage1.add_quest(quest)
        
        # Create new storage instance
        storage2 = DnDStorage(temp_dir)
        
        # Verify all data integrity
        char = storage2.get_character("Test Hero")
        assert char.character_class.level == 7
        assert len(char.race.traits) == 2
        assert char.abilities["dexterity"].score == 18
        
        npc_retrieved = storage2.get_npc("Quest Giver")
        assert npc_retrieved.location == "Tower"
        assert npc_retrieved.relationships["Test Hero"] == "Mentor"
        
        loc = storage2.get_location("Tower")
        assert "Quest Giver" in loc.npcs
        assert "Village" in loc.connections
        
        quest_retrieved = storage2.get_quest("Tower Defense")
        assert quest_retrieved.giver == "Quest Giver"
        assert quest_retrieved.status == "active"