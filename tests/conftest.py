"""
Shared pytest fixtures for DnDStorage tests.
"""

import shutil
import tempfile

import pytest

from gamemaster_mcp.models import (
    Campaign,
    GameState,
)
from gamemaster_mcp.storage import DnDStorage


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
        game_state=GameState(campaign_name="Test Campaign"),
    )


@pytest.fixture
def storage_with_campaign(temp_storage, sample_campaign) -> Campaign:
    """Create a storage instance with a campaign already loaded."""
    temp_storage.create_campaign(
        sample_campaign.name,
        sample_campaign.description,
        sample_campaign.dm_name,
        sample_campaign.setting,
    )
    return temp_storage
