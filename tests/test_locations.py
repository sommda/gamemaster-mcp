"""
Tests for location management in DnDStorage.
"""

import pytest
from gamemaster_mcp.models import Location


@pytest.fixture
def sample_location():
    """Create a sample location for testing."""
    return Location(
        name="Riverside Inn",
        location_type="tavern",
        description="A cozy tavern by the river",
        population=20,
        government="None",
        notable_features=["Great ale", "Warm fireplace"],
        npcs=["Innkeeper Bob"],
    )


class TestLocationManagement:
    """Test location CRUD operations."""

    def test_add_location(self, storage_with_campaign, sample_location):
        """Test adding a location to campaign."""
        storage_with_campaign.add_location(sample_location)

        retrieved = storage_with_campaign.get_location(sample_location.name)
        assert retrieved is not None
        assert retrieved.name == sample_location.name
        assert retrieved.location_type == sample_location.location_type
        assert retrieved.description == sample_location.description

    def test_add_location_no_campaign(self, temp_storage, sample_location):
        """Test adding location when no campaign is loaded."""
        with pytest.raises(ValueError, match="No current campaign"):
            temp_storage.add_location(sample_location)

    def test_get_nonexistent_location(self, storage_with_campaign):
        """Test getting a location that doesn't exist."""
        location = storage_with_campaign.get_location("Nonexistent Location")
        assert location is None

    def test_list_locations_empty(self, storage_with_campaign):
        """Test listing locations when none exist."""
        locations = storage_with_campaign.list_locations()
        assert isinstance(locations, list)
        assert len(locations) == 0

    def test_list_locations_with_data(self, storage_with_campaign, sample_location):
        """Test listing locations after adding one."""
        storage_with_campaign.add_location(sample_location)

        locations = storage_with_campaign.list_locations()
        assert len(locations) == 1
        assert sample_location.name in locations

    def test_location_with_npcs(self, storage_with_campaign):
        """Test location with associated NPCs."""
        location = Location(
            name="The Trading Post",
            location_type="shop",
            description="A well-stocked general store",
            npcs=["Merchant Smith", "Shop Assistant"],
        )

        storage_with_campaign.add_location(location)

        retrieved = storage_with_campaign.get_location("The Trading Post")
        assert len(retrieved.npcs) == 2
        assert "Merchant Smith" in retrieved.npcs
        assert "Shop Assistant" in retrieved.npcs

    def test_location_with_connections(self, storage_with_campaign):
        """Test location with connections to other locations."""
        location = Location(
            name="Crossroads",
            location_type="intersection",
            description="A busy crossroads where four paths meet",
            connections=["North Village", "South Harbor", "East Forest", "West Mountains"],
        )

        storage_with_campaign.add_location(location)

        retrieved = storage_with_campaign.get_location("Crossroads")
        assert len(retrieved.connections) == 4
        assert "North Village" in retrieved.connections
        assert "West Mountains" in retrieved.connections

    def test_multiple_locations(self, storage_with_campaign):
        """Test managing multiple locations."""
        tavern = Location(name="The Prancing Pony", location_type="tavern", description="tavern")
        shop = Location(name="Weapons & More", location_type="armory", description="armory")
        temple = Location(name="Temple of Light", location_type="temple", description="temple")

        storage_with_campaign.add_location(tavern)
        storage_with_campaign.add_location(shop)
        storage_with_campaign.add_location(temple)

        locations = storage_with_campaign.list_locations()
        assert len(locations) == 3
        assert "The Prancing Pony" in locations
        assert "Weapons & More" in locations
        assert "Temple of Light" in locations
