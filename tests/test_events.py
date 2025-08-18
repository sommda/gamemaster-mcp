"""
Tests for adventure event management in DnDStorage.
"""

import pytest
from gamemaster_mcp.models import AdventureEvent, EventType


@pytest.fixture
def sample_event():
    """Create a sample adventure event for testing."""
    return AdventureEvent(
        event_type=EventType.COMBAT,
        title="Dragon Battle",
        description="The party fought a fierce red dragon in its lair",
        session_number=3,
        characters_involved=["Gandalf", "Legolas", "Aragorn"],
        location="Dragon's Lair",
        tags=["boss fight", "treasure"],
        importance=5
    )


class TestEventManagement:
    """Test adventure event operations."""
    
    def test_add_event(self, temp_storage, sample_event):
        """Test adding an adventure event."""
        temp_storage.add_event(sample_event)
        
        events = temp_storage.get_events()
        assert len(events) == 1
        assert events[0].title == "Dragon Battle"
        assert events[0].event_type == EventType.COMBAT
        assert events[0].importance == 5
    
    def test_get_events_empty(self, temp_storage):
        """Test getting events when none exist."""
        events = temp_storage.get_events()
        assert isinstance(events, list)
        assert len(events) == 0
    
    def test_get_events_with_limit(self, temp_storage):
        """Test getting events with limit."""
        # Add multiple events
        for i in range(5):
            event = AdventureEvent(
                event_type=EventType.ROLEPLAY,
                title=f"Event {i}",
                description=f"Description {i}",
                importance=1
            )
            temp_storage.add_event(event)
        
        events = temp_storage.get_events(limit=3)
        assert len(events) == 3
    
    def test_get_events_by_type(self, temp_storage):
        """Test getting events filtered by type."""
        combat_event = AdventureEvent(
            event_type=EventType.COMBAT,
            title="Combat Event",
            description="A battle",
            importance=1
        )
        roleplay_event = AdventureEvent(
            event_type=EventType.ROLEPLAY,
            title="Roleplay Event", 
            description="A conversation",
            importance=1
        )
        exploration_event = AdventureEvent(
            event_type=EventType.EXPLORATION,
            title="Exploration Event",
            description="Discovering a new area",
            importance=1
        )
        
        temp_storage.add_event(combat_event)
        temp_storage.add_event(roleplay_event)
        temp_storage.add_event(exploration_event)
        
        # Test filtering by type
        combat_events = temp_storage.get_events(event_type=EventType.COMBAT)
        assert len(combat_events) == 1
        assert combat_events[0].title == "Combat Event"
        
        roleplay_events = temp_storage.get_events(event_type=EventType.ROLEPLAY)
        assert len(roleplay_events) == 1
        assert roleplay_events[0].title == "Roleplay Event"
    
    def test_search_events(self, temp_storage):
        """Test searching events by query string."""
        event1 = AdventureEvent(
            event_type=EventType.EXPLORATION,
            title="Cave Exploration",
            description="The party explored a mysterious cave",
            importance=1
        )
        event2 = AdventureEvent(
            event_type=EventType.QUEST,
            title="Quest Completion",
            description="The party completed their first quest",
            importance=1
        )
        event3 = AdventureEvent(
            event_type=EventType.COMBAT,
            title="Cave Troll Fight",
            description="Encountered a troll in the cave depths",
            importance=2
        )
        
        temp_storage.add_event(event1)
        temp_storage.add_event(event2)
        temp_storage.add_event(event3)
        
        # Search by title
        cave_events = temp_storage.search_events("cave")
        assert len(cave_events) == 2  # Both "Cave Exploration" and "Cave Troll Fight"
        
        # Search by description
        quest_events = temp_storage.search_events("quest")
        assert len(quest_events) == 1  # "Quest Completion"
        
        # Search for specific term
        troll_events = temp_storage.search_events("troll")
        assert len(troll_events) == 1
        assert troll_events[0].title == "Cave Troll Fight"
    
    def test_event_importance_levels(self, temp_storage):
        """Test events with different importance levels."""
        minor_event = AdventureEvent(
            event_type=EventType.ROLEPLAY,
            title="Tavern Chat",
            description="Casual conversation with locals",
            importance=1
        )
        major_event = AdventureEvent(
            event_type=EventType.QUEST,
            title="Campaign Finale",
            description="The final confrontation with the BBEG",
            importance=5
        )
        
        temp_storage.add_event(minor_event)
        temp_storage.add_event(major_event)
        
        events = temp_storage.get_events()
        assert len(events) == 2
        
        # Find events by importance
        major_events = [e for e in events if e.importance >= 4]
        minor_events = [e for e in events if e.importance <= 2]
        
        assert len(major_events) == 1
        assert major_events[0].title == "Campaign Finale"
        assert len(minor_events) == 1
        assert minor_events[0].title == "Tavern Chat"
    
    def test_event_with_tags(self, temp_storage):
        """Test events with custom tags."""
        event = AdventureEvent(
            event_type=EventType.COMBAT,
            title="Boss Battle",
            description="Epic fight with the dragon lord",
            tags=["boss", "dragon", "epic", "loot"],
            importance=4
        )
        
        temp_storage.add_event(event)
        
        retrieved_events = temp_storage.get_events()
        assert len(retrieved_events) == 1
        assert len(retrieved_events[0].tags) == 4
        assert "boss" in retrieved_events[0].tags
        assert "epic" in retrieved_events[0].tags
    
    def test_event_with_characters_and_location(self, temp_storage):
        """Test events with character involvement and location tracking."""
        event = AdventureEvent(
            event_type=EventType.EXPLORATION,
            title="Dungeon Discovery",
            description="The party found a hidden entrance to ancient ruins",
            characters_involved=["Fighter", "Wizard", "Rogue"],
            location="Whispering Woods",
            session_number=5,
            importance=3
        )
        
        temp_storage.add_event(event)
        
        events = temp_storage.get_events()
        assert len(events) == 1
        
        event = events[0]
        assert len(event.characters_involved) == 3
        assert "Fighter" in event.characters_involved
        assert event.location == "Whispering Woods"
        assert event.session_number == 5