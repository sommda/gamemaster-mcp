"""
Tests for adventure event management in DnDStorage.
"""

import pytest
from gamemaster_mcp.models import Transcript


class TestTranscriptManagement:
    """Test transcript operations."""
    
    def test_get_empty(self, storage_with_campaign):
        empty_transcript = storage_with_campaign.get_transcript()
        assert empty_transcript is None

    def test_add_entry_and_get(self, storage_with_campaign):
        storage_with_campaign.add_transcript_entry("command 1", "response 1")
        storage_with_campaign.add_transcript_entry("command 2", "response 2")

        transcript = storage_with_campaign.get_transcript()
        assert len(transcript.entries) == 2
        assert transcript.entries[0].player_entry == "command 1"
        assert transcript.entries[0].game_response == "response 1"
        assert transcript.entries[1].player_entry == "command 2"
        assert transcript.entries[1].game_response == "response 2"

        assert transcript.campaign == storage_with_campaign.get_current_campaign().name
        assert transcript.session_number == 0

        
