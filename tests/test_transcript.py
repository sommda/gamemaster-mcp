"""
Tests for adventure event management in DnDStorage.
"""


class TestTranscriptManagement:
    """Test transcript operations."""

    def test_get_empty(self, storage_with_campaign):
        empty_transcript = storage_with_campaign.get_transcript()
        assert empty_transcript is None

    def test_add_entry_and_get(self, storage_with_campaign):
        storage_with_campaign.add_transcript_entry("command 1", "response 1")
        storage_with_campaign.add_transcript_entry("command 2", "response 2")

        transcript = storage_with_campaign.get_transcript()
        # Transcript now uses children (TranscriptInteraction nodes)
        assert len(transcript.children) == 2
        assert transcript.children[0].user_text == "command 1"
        assert transcript.children[0].responses[0].content == "response 1"
        assert transcript.children[1].user_text == "command 2"
        assert transcript.children[1].responses[0].content == "response 2"

        assert transcript.campaign == storage_with_campaign.get_current_campaign().name
        assert transcript.session_number == 1  # current_session defaults to 1
