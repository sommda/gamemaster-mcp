"""
Tests for game state management in DnDStorage.
"""

import pytest
from gamemaster_mcp.models import GameState


class TestGameStateManagement:
    """Test game state operations."""
    
    def test_get_initial_game_state(self, storage_with_campaign, sample_campaign):
        """Test getting initial game state."""
        game_state = storage_with_campaign.get_game_state()
        assert game_state is not None
        assert game_state.campaign_name == sample_campaign.name
        assert game_state.current_session == 1
        assert not game_state.in_combat
        assert game_state.party_level == 1
        assert game_state.current_turn is None
    
    def test_update_game_state_location(self, storage_with_campaign):
        """Test updating game state location."""
        storage_with_campaign.update_game_state(
            current_location="Dragon's Lair",
            current_date_in_game="Day 15 of Spring"
        )
        
        updated = storage_with_campaign.get_game_state()
        assert updated.current_location == "Dragon's Lair"
        assert updated.current_date_in_game == "Day 15 of Spring"
    
    def test_update_game_state_party_info(self, storage_with_campaign):
        """Test updating party-related game state."""
        storage_with_campaign.update_game_state(
            party_level=5,
            party_funds="1500 gold pieces"
        )
        
        updated = storage_with_campaign.get_game_state()
        assert updated.party_level == 5
        assert updated.party_funds == "1500 gold pieces"
    
    def test_update_game_state_combat(self, storage_with_campaign):
        """Test updating combat-related game state."""
        initiative_order = [
            {"name": "Fighter", "initiative": 18},
            {"name": "Goblin", "initiative": 15},
            {"name": "Wizard", "initiative": 12}
        ]
        
        storage_with_campaign.update_game_state(
            in_combat=True,
            current_turn="Fighter",
            initiative_order=initiative_order
        )
        
        updated = storage_with_campaign.get_game_state()
        assert updated.in_combat is True
        assert updated.current_turn == "Fighter"
        assert len(updated.initiative_order) == 3
        assert updated.initiative_order[0]["name"] == "Fighter"
        assert updated.initiative_order[0]["initiative"] == 18
    
    def test_update_game_state_quests(self, storage_with_campaign):
        """Test updating active quests in game state."""
        active_quests = ["Find the Lost Sword", "Rescue the Princess", "Defeat the Dragon"]
        
        storage_with_campaign.update_game_state(
            active_quests=active_quests
        )
        
        updated = storage_with_campaign.get_game_state()
        assert len(updated.active_quests) == 3
        assert "Find the Lost Sword" in updated.active_quests
        assert "Defeat the Dragon" in updated.active_quests
    
    def test_update_game_state_session(self, storage_with_campaign):
        """Test updating session information."""
        storage_with_campaign.update_game_state(
            current_session=7,
            notes="The party is currently exploring the Shadowfell"
        )
        
        updated = storage_with_campaign.get_game_state()
        assert updated.current_session == 7
        assert "Shadowfell" in updated.notes
    
    def test_update_game_state_no_campaign(self, temp_storage):
        """Test updating game state when no campaign is loaded."""
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.update_game_state(current_location="Test")
    
    def test_get_game_state_no_campaign(self, temp_storage):
        """Test getting game state when no campaign is loaded."""
        game_state = temp_storage.get_game_state()
        assert game_state is None
    
    def test_game_state_persistence(self, storage_with_campaign):
        """Test that game state changes persist."""
        # Make multiple updates
        storage_with_campaign.update_game_state(current_location="Tavern")
        storage_with_campaign.update_game_state(party_level=3)
        storage_with_campaign.update_game_state(in_combat=True)
        
        # Get final state
        final_state = storage_with_campaign.get_game_state()
        
        # All updates should be preserved
        assert final_state.current_location == "Tavern"
        assert final_state.party_level == 3
        assert final_state.in_combat is True
    
    def test_game_state_updated_timestamp(self, storage_with_campaign):
        """Test that game state updated_at timestamp changes."""
        initial_state = storage_with_campaign.get_game_state()
        initial_time = initial_state.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        storage_with_campaign.update_game_state(current_location="New Location")
        
        updated_state = storage_with_campaign.get_game_state()
        assert updated_state.updated_at > initial_time