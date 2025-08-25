"""
Shared pytest fixtures for DnDStorage tests.
"""

import pytest
import tempfile
import shutil
from datetime import datetime

from gamemaster_mcp.storage import DnDStorage
from gamemaster_mcp.models import (
    Campaign, Character, NPC, Location, Quest, CombatEncounter,
    SessionNote, GameState, AdventureEvent, EventType,
    CharacterClass, Race, AbilityScore, Item, Spell,
    Attack, CombatParticipant
)


@pytest.fixture
def temp_storage():
    """Create a temporary storage instance for testing."""
    temp_dir = tempfile.mkdtemp()
    storage = DnDStorage(temp_dir)
    yield storage
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_campaign():
    """Create a sample campaign for testing."""
    return Campaign(
        name="Test Campaign",
        description="A test campaign for unit tests",
        dm_name="Test DM",
        setting="Test Realm",
        game_state=GameState(campaign_name = "Test Campaign")
    )


@pytest.fixture
def storage_with_campaign(temp_storage, sample_campaign):
    """Create a storage instance with a campaign already loaded."""
    temp_storage.create_campaign(
        sample_campaign.name,
        sample_campaign.description,
        sample_campaign.dm_name,
        sample_campaign.setting
    )
    return temp_storage