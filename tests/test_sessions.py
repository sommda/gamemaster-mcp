"""
Tests for session management in DnDStorage.
"""

from datetime import datetime

import pytest

from gamemaster_mcp.models import SessionNote


@pytest.fixture
def sample_session_note():
    """Create a sample session note for testing."""
    return SessionNote(
        session_number=1,
        date=datetime.now(),
        title="First Session",
        summary="The party met at the tavern and received their first quest",
        events=["Party formation", "Quest assignment", "Equipment purchase"],
        characters_present=["Gandalf", "Legolas", "Aragorn"],
        experience_gained=100,
        treasure_found=["50 gold pieces", "Health potion"],
    )


class TestSessionManagement:
    """Test session management operations."""

    def test_add_session_note(self, storage_with_campaign, sample_session_note):
        """Test adding session notes."""
        storage_with_campaign.add_session_note(sample_session_note)

        sessions = storage_with_campaign.get_sessions()
        assert len(sessions) == 1
        assert sessions[0].title == "First Session"
        assert sessions[0].session_number == 1
        assert len(sessions[0].events) == 3
        assert "Party formation" in sessions[0].events

    def test_add_session_note_no_campaign(self, temp_storage, sample_session_note):
        """Test adding session note when no campaign is loaded."""
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_session_note(sample_session_note)

    def test_get_sessions_empty(self, storage_with_campaign):
        """Test getting sessions when none exist."""
        sessions = storage_with_campaign.get_sessions()
        assert isinstance(sessions, list)
        assert len(sessions) == 0

    def test_multiple_session_notes(self, storage_with_campaign):
        """Test adding multiple session notes."""
        session1 = SessionNote(
            session_number=1,
            date=datetime.now(),
            title="Session One",
            summary="The adventure begins",
            characters_present=["Hero1", "Hero2"],
        )
        session2 = SessionNote(
            session_number=2,
            date=datetime.now(),
            title="Session Two",
            summary="The plot thickens",
            characters_present=["Hero1", "Hero2", "Hero3"],
        )

        storage_with_campaign.add_session_note(session1)
        storage_with_campaign.add_session_note(session2)

        sessions = storage_with_campaign.get_sessions()
        assert len(sessions) == 2

        # Sessions should be stored in order
        assert sessions[0].session_number == 1
        assert sessions[1].session_number == 2
        assert sessions[0].title == "Session One"
        assert sessions[1].title == "Session Two"

    def test_session_with_experience_and_treasure(self, storage_with_campaign):
        """Test session note with experience and treasure tracking."""
        session = SessionNote(
            session_number=3,
            date=datetime.now(),
            title="The Dragon's Hoard",
            summary="The party defeated the dragon and claimed its treasure",
            experience_gained=2500,
            treasure_found=[
                "5000 gold pieces",
                "Sword +2",
                "Ring of Protection",
                "Spell scroll (Fireball)",
            ],
            characters_present=["Fighter", "Wizard", "Cleric", "Rogue"],
        )

        storage_with_campaign.add_session_note(session)

        sessions = storage_with_campaign.get_sessions()
        assert len(sessions) == 1

        session = sessions[0]
        assert session.experience_gained == 2500
        assert len(session.treasure_found) == 4
        assert "Sword +2" in session.treasure_found
        assert len(session.characters_present) == 4

    def test_session_with_detailed_events(self, storage_with_campaign):
        """Test session note with detailed event tracking."""
        detailed_events = [
            "Party arrived at the village of Greenhill",
            "Met with Mayor Thompson about missing children",
            "Investigated the old mill on the outskirts",
            "Discovered tracks leading to the Darkwood",
            "Encountered and defeated three dire wolves",
            "Found the children's trail continuing deeper into forest",
            "Made camp at the forest edge",
        ]

        session = SessionNote(
            session_number=5,
            date=datetime.now(),
            title="The Missing Children",
            summary="Investigation leads the party into dangerous territory",
            events=detailed_events,
            characters_present=["Paladin", "Ranger", "Sorcerer"],
            notes="Party is low on supplies and may need to return to town",
        )

        storage_with_campaign.add_session_note(session)

        sessions = storage_with_campaign.get_sessions()
        assert len(sessions) == 1

        session = sessions[0]
        assert len(session.events) == 7
        assert "Party arrived at the village of Greenhill" in session.events
        assert "Made camp at the forest edge" in session.events
        assert "low on supplies" in session.notes

    def test_session_chronological_order(self, storage_with_campaign):
        """Test that sessions maintain chronological order."""
        # Add sessions out of numerical order
        session3 = SessionNote(
            session_number=3, date=datetime.now(), title="Session 3", summary="summary 3"
        )
        session1 = SessionNote(
            session_number=1, date=datetime.now(), title="Session 1", summary="summary 1"
        )
        session2 = SessionNote(
            session_number=2, date=datetime.now(), title="Session 2", summary="summary 2"
        )

        storage_with_campaign.add_session_note(session3)
        storage_with_campaign.add_session_note(session1)
        storage_with_campaign.add_session_note(session2)

        sessions = storage_with_campaign.get_sessions()
        assert len(sessions) == 3

        # Should be stored in the order they were added, not necessarily numerical order
        # (This documents current behavior - could be changed if sorting is desired)
        assert sessions[0].title == "Session 3"
        assert sessions[1].title == "Session 1"
        assert sessions[2].title == "Session 2"

    def test_session_date_tracking(self, storage_with_campaign):
        """Test that session dates are properly tracked."""
        test_date = datetime(2024, 3, 15, 19, 30)  # March 15, 2024 at 7:30 PM

        session = SessionNote(
            session_number=1,
            date=test_date,
            title="Campaign Launch",
            summary="The very first session of our new campaign",
        )

        storage_with_campaign.add_session_note(session)

        sessions = storage_with_campaign.get_sessions()
        assert len(sessions) == 1
        assert sessions[0].date == test_date
        assert sessions[0].date.year == 2024
        assert sessions[0].date.month == 3
        assert sessions[0].date.day == 15
