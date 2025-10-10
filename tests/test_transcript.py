"""
Tests for transcript management in DnDStorage.
"""

from gamemaster_mcp.models import TranscriptEntry, TranscriptTool


class TestTranscriptManagement:
    """Test transcript operations."""

    def test_get_empty(self, storage_with_campaign):
        empty_transcript = storage_with_campaign.get_transcript()
        assert empty_transcript is None

    def test_add_entry_and_get(self, storage_with_campaign):
        storage_with_campaign.add_transcript_entry(
            player_entry="command 1", game_response="response 1"
        )
        storage_with_campaign.add_transcript_entry(
            player_entry="command 2", game_response="response 2"
        )

        transcript = storage_with_campaign.get_transcript()
        assert len(transcript.entries) == 2
        assert isinstance(transcript.entries[0], TranscriptEntry)
        assert isinstance(transcript.entries[1], TranscriptEntry)
        assert transcript.entries[0].player_entry == "command 1"
        assert transcript.entries[0].game_response == "response 1"
        assert transcript.entries[1].player_entry == "command 2"
        assert transcript.entries[1].game_response == "response 2"

        assert transcript.campaign == storage_with_campaign.get_current_campaign().name
        assert transcript.session_number == 0

    def test_add_tool_call(self, storage_with_campaign):
        """Test adding tool call entries to transcript."""
        storage_with_campaign.add_transcript_entry(
            tool_name="create_character",
            tool_params={"name": "Gandalf", "level": 20},
            tool_response="Character created successfully"
        )
        storage_with_campaign.add_transcript_entry(
            tool_name="roll_dice",
            tool_params={"dice": "2d6", "modifier": 3},
            tool_response="Rolled 2d6+3 = 11"
        )

        transcript = storage_with_campaign.get_transcript()
        assert len(transcript.entries) == 2
        assert isinstance(transcript.entries[0], TranscriptTool)
        assert isinstance(transcript.entries[1], TranscriptTool)

        assert transcript.entries[0].tool_name == "create_character"
        assert transcript.entries[0].tool_params == {"name": "Gandalf", "level": 20}
        assert transcript.entries[0].tool_response == "Character created successfully"

        assert transcript.entries[1].tool_name == "roll_dice"
        assert transcript.entries[1].tool_params == {"dice": "2d6", "modifier": 3}
        assert transcript.entries[1].tool_response == "Rolled 2d6+3 = 11"

    def test_add_mixed_entries(self, storage_with_campaign):
        """Test adding both player interactions and tool calls to transcript."""
        storage_with_campaign.add_transcript_entry(
            player_entry="I attack the goblin",
            game_response="Roll for attack"
        )
        storage_with_campaign.add_transcript_entry(
            tool_name="roll_dice",
            tool_params={"dice": "1d20", "modifier": 5},
            tool_response="Rolled 1d20+5 = 18"
        )
        storage_with_campaign.add_transcript_entry(
            player_entry="Does it hit?",
            game_response="Yes! The goblin has AC 15, you hit!"
        )

        transcript = storage_with_campaign.get_transcript()
        assert len(transcript.entries) == 3
        assert isinstance(transcript.entries[0], TranscriptEntry)
        assert isinstance(transcript.entries[1], TranscriptTool)
        assert isinstance(transcript.entries[2], TranscriptEntry)

    def test_add_entry_validation_error(self, storage_with_campaign):
        """Test that adding entry with neither player nor tool params raises error."""
        import pytest

        with pytest.raises(ValueError, match="Must provide either"):
            storage_with_campaign.add_transcript_entry()

    def test_add_entry_conflicting_params_error(self, storage_with_campaign):
        """Test that adding entry with both player and tool params raises error."""
        import pytest

        with pytest.raises(ValueError, match="Cannot provide both"):
            storage_with_campaign.add_transcript_entry(
                player_entry="test",
                game_response="response",
                tool_name="test_tool",
                tool_params={},
                tool_response="tool response"
            )
