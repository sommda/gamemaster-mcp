"""
Tests for character management in DnDStorage.
"""

import pytest
from gamemaster_mcp.models import Character, CharacterClass, Race, AbilityScore


@pytest.fixture
def sample_character():
    """Create a sample character for testing."""
    return Character(
        name="Gandalf",
        player_name="Test Player",
        character_class=CharacterClass(name="Wizard", level=5),
        race=Race(name="Human"),
        abilities={
            "strength": AbilityScore(score=10),
            "dexterity": AbilityScore(score=14),
            "constitution": AbilityScore(score=12),
            "intelligence": AbilityScore(score=18),
            "wisdom": AbilityScore(score=16),
            "charisma": AbilityScore(score=13),
        },
        hit_points_max=40,
        hit_points_current=40,
        armor_class=12
    )


class TestCharacterManagement:
    """Test character CRUD operations."""
    
    def test_add_character(self, storage_with_campaign, sample_character):
        """Test adding a character to campaign."""
        storage_with_campaign.add_character(sample_character)
        
        retrieved = storage_with_campaign.get_character(sample_character.name)
        assert retrieved is not None
        assert retrieved.name == sample_character.name
        assert retrieved.character_class.name == sample_character.character_class.name
    
    def test_add_character_no_campaign(self, temp_storage, sample_character):
        """Test adding character when no campaign is loaded."""
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_character(sample_character)
    
    def test_get_nonexistent_character(self, storage_with_campaign):
        """Test getting a character that doesn't exist."""
        character = storage_with_campaign.get_character("Nonexistent Character")
        assert character is None
    
    def test_list_characters_empty(self, storage_with_campaign):
        """Test listing characters when none exist."""
        characters = storage_with_campaign.list_characters()
        assert isinstance(characters, list)
        assert len(characters) == 0
    
    def test_list_characters_with_data(self, storage_with_campaign, sample_character):
        """Test listing characters after adding one."""
        storage_with_campaign.add_character(sample_character)
        
        characters = storage_with_campaign.list_characters()
        assert len(characters) == 1
        assert sample_character.name in characters
    
    def test_update_character(self, storage_with_campaign, sample_character):
        """Test updating character properties."""
        storage_with_campaign.add_character(sample_character)
        
        storage_with_campaign.update_character(
            sample_character.name,
            hit_points_current=25,
            armor_class=15
        )
        
        updated = storage_with_campaign.get_character(sample_character.name)
        assert updated.hit_points_current == 25
        assert updated.armor_class == 15
    
    def test_update_nonexistent_character(self, storage_with_campaign):
        """Test updating a character that doesn't exist."""
        with pytest.raises(ValueError):
            storage_with_campaign.update_character("Nonexistent", hit_points_current=10)
    
    def test_remove_character(self, storage_with_campaign, sample_character):
        """Test removing a character."""
        storage_with_campaign.add_character(sample_character)
        
        storage_with_campaign.remove_character(sample_character.name)
        
        assert storage_with_campaign.get_character(sample_character.name) is None
        assert len(storage_with_campaign.list_characters()) == 0
    
    def test_remove_nonexistent_character(self, storage_with_campaign):
        """Test removing a character that doesn't exist."""
        storage_with_campaign.remove_character("Nonexistent")