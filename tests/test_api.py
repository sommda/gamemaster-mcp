"""
Tests for outward-facing API.
"""

import pytest, asyncio, json
from gamemaster_mcp.storage import DnDStorage
from gamemaster_mcp.main import override_storage
from gamemaster_mcp.main import (
    create_campaign, get_campaign_info, list_campaigns, load_campaign, get_campaign, get_campaigns, get_current_campaign
)

def unwrap_tool(obj):
    # Try the most common attributes in order
    for attr in ("__wrapped__", "func", "function", "wrapped", "target"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            return fn
    raise TypeError(f"Cannot unwrap tool {obj!r}; expose a plain function for testing.")


class TestAPI:

    async def test_create_campaign(self, temp_storage, sample_campaign):
        """Test creating a new campaign."""
        override_storage(temp_storage)
        results = await create_campaign.run({
            "name": sample_campaign.name,
            "description": sample_campaign.description,
            "dm_name": sample_campaign.dm_name,
            "setting": sample_campaign.setting
        })
        assert(len(results) == 1)
        assert(sample_campaign.name in results[0].text)

    async def test_get_campaign_info(self, storage_with_campaign):
        """Test grabbing basic campaign info."""
        override_storage(storage_with_campaign)
        results = await get_campaign_info.run({})
        assert(len(results) == 1)
        print(results[0].text)
        assert(storage_with_campaign.get_current_campaign().name in results[0].text)

    async def test_list_campaigns(self, storage_with_campaign):
        """Test listing campaigns."""
        override_storage(storage_with_campaign)
        results = await list_campaigns.run({})
        assert(len(results) == 1)
        print(results[0].text)
        assert(storage_with_campaign.get_current_campaign().name in results[0].text)

    async def test_load_campaign(self, storage_with_campaign):
        """Test loading a current campaigns."""
        override_storage(storage_with_campaign)
        name = storage_with_campaign.get_current_campaign().name
        results = await load_campaign.run({
            "name": name
        })
        assert(len(results) == 1)
        assert(name in results[0].text)

    async def test_get_campaign(self, storage_with_campaign):
        """Test loading a campaign as a resource."""
        override_storage(storage_with_campaign)
        name = storage_with_campaign.get_current_campaign().name
        campaign = await get_campaign.read({
            "campaign_name": name
        })
        assert(campaign.name == name)
        assert(campaign.dm_name == "Test DM")

    async def test_get_campaigns(self, storage_with_campaign):
        """Test getting all campaigns as a resource."""
        override_storage(storage_with_campaign)
        name = storage_with_campaign.get_current_campaign().name
        campaigns = json.loads(await get_campaigns.read())
        print(campaigns)
        assert(len(campaigns) == 1)
        assert(campaigns[0] == name)

    async def test_get_current_campaign(self, storage_with_campaign):
        """Test getting name of current campaign."""
        override_storage(storage_with_campaign)
        name = storage_with_campaign.get_current_campaign().name
        current_campaign_name = await get_current_campaign.read()
        assert(name == current_campaign_name)
