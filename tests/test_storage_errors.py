"""
Tests for error handling in DnDStorage operations.
"""

import pytest
from gamemaster_mcp.models import Character, NPC, Location, Quest, CharacterClass, Race, AbilityScore


class TestStorageErrorHandling:
    """Test error handling in storage operations."""
    
    def test_operations_without_campaign_fail(self, temp_storage):
        """Test that operations requiring a campaign fail when none is loaded."""
        sample_character = Character(
            name="Test Character",
            character_class=CharacterClass(name="Fighter", level=1),
            race=Race(name="Human"),
            abilities={"strength": AbilityScore(score=15)}
        )
        
        # Character operations should fail
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_character(sample_character)
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.get_character("test")
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.update_character("test", hit_points_current=10)
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.remove_character("test")
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.list_characters()
    
    def test_npc_operations_without_campaign_fail(self, temp_storage):
        """Test that NPC operations fail when no campaign is loaded."""
        sample_npc = NPC(name="Test NPC")
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_npc(sample_npc)
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.get_npc("test")
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.list_npcs()
    
    def test_location_operations_without_campaign_fail(self, temp_storage):
        """Test that location operations fail when no campaign is loaded."""
        sample_location = Location(name="Test Location", location_type="test", description="test")
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_location(sample_location)
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.get_location("test")
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.list_locations()
    
    def test_quest_operations_without_campaign_fail(self, temp_storage):
        """Test that quest operations fail when no campaign is loaded."""
        sample_quest = Quest(title="Test Quest", description="Test description")
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_quest(sample_quest)
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.get_quest("test")
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.list_quests()
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.update_quest_status("test", "completed")
    
    def test_game_state_operations_without_campaign_fail(self, temp_storage):
        """Test that game state operations fail when no campaign is loaded."""
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.update_game_state(current_location="test")
        
        # get_game_state should return None rather than raise an error
        game_state = temp_storage.get_game_state()
        assert game_state is None
    
    def test_session_operations_without_campaign_fail(self, temp_storage):
        """Test that session operations fail when no campaign is loaded."""
        from gamemaster_mcp.models import SessionNote
        from datetime import datetime
        
        sample_session = SessionNote(
            session_number=1,
            date=datetime.now(),
            summary="Test session"
        )
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_session_note(sample_session)
        
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.get_sessions()
    
    def test_update_nonexistent_character(self, storage_with_campaign):
        """Test updating a character that doesn't exist."""
        with pytest.raises(ValueError):
            storage_with_campaign.update_character("Nonexistent Character", hit_points_current=10)
    
    def test_update_nonexistent_quest_status(self, storage_with_campaign):
        """Test updating status of quest that doesn't exist."""
        with pytest.raises(ValueError):
            storage_with_campaign.update_quest_status("Nonexistent Quest", "completed")
    
    def test_load_nonexistent_campaign(self, temp_storage):
        """Test loading a campaign that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            temp_storage.load_campaign("Nonexistent Campaign")
    
    def test_get_campaign_file_without_current_campaign(self, temp_storage):
        """Test getting campaign file path when no campaign is loaded."""
        with pytest.raises(ValueError, match="No campaign name provided and no current campaign"):
            temp_storage._get_campaign_file()
    
    def test_invalid_campaign_name_characters(self, temp_storage):
        """Test creating campaign with invalid filename characters."""
        # These should be sanitized, not cause errors
        campaign = temp_storage.create_campaign(
            name="Test/Campaign\\With:Invalid*Characters?",
            description="Test description"
        )
        
        assert campaign is not None
        assert campaign.name == "Test/Campaign\\With:Invalid*Characters?"  # Name preserved
        
        # File should be created with sanitized name
        campaign_file = temp_storage._get_campaign_file()
        assert campaign_file.exists()
        # Filename should not contain invalid characters
        assert "/" not in campaign_file.name
        assert "\\" not in campaign_file.name
        assert ":" not in campaign_file.name
    
    def test_duplicate_character_names(self, storage_with_campaign):
        """Test adding characters with duplicate names."""
        character1 = Character(
            name="Gandalf",
            character_class=CharacterClass(name="Wizard", level=5),
            race=Race(name="Human"),
            abilities={"strength": AbilityScore(score=10)}
        )
        character2 = Character(
            name="Gandalf",  # Same name
            character_class=CharacterClass(name="Fighter", level=3),
            race=Race(name="Elf"),
            abilities={"strength": AbilityScore(score=15)}
        )
        
        # First character should be added successfully
        storage_with_campaign.add_character(character1)
        
        # Second character should overwrite the first (current behavior)
        storage_with_campaign.add_character(character2)
        
        retrieved = storage_with_campaign.get_character("Gandalf")
        assert retrieved.character_class.name == "Fighter"  # Should be the second one
        assert retrieved.character_class.level == 3
    
    def test_empty_string_names(self, storage_with_campaign):
        """Test operations with empty string names."""
        # Empty character name
        with pytest.raises(ValueError):
            storage_with_campaign.get_character("")
        
        # Empty NPC name  
        with pytest.raises(ValueError):
            storage_with_campaign.get_npc("")
        
        # Empty location name
        with pytest.raises(ValueError):
            storage_with_campaign.get_location("")
        
        # Empty quest title
        with pytest.raises(ValueError):
            storage_with_campaign.get_quest("")