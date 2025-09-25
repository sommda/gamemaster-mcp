"""
Tests for Monster management in game state.
"""

import pytest

from gamemaster_mcp.models import AbilityScore, Attack, Monster


@pytest.fixture
def sample_monster():
    """Create a sample monster for testing."""
    return Monster(
        name="Goblin Scout",
        monster_type="Goblin",
        hit_points_max=8,
        hit_points_current=8,
        armor_class=14,
        size="Small",
        creature_type="humanoid",
        alignment="neutral evil",
        speed=30,
        challenge_rating="1/4",
        experience_value=50,
        description="A small, sneaky goblin with beady eyes and sharp teeth.",
        location="Forest Clearing",
        abilities={
            "strength": AbilityScore(score=8),
            "dexterity": AbilityScore(score=14),
            "constitution": AbilityScore(score=10),
            "intelligence": AbilityScore(score=10),
            "wisdom": AbilityScore(score=8),
            "charisma": AbilityScore(score=8),
        },
        attacks=[
            Attack(weapon="Scimitar", attack_roll_modifier=4, damage_roll="1d6+2"),
            Attack(weapon="Shortbow", attack_roll_modifier=4, damage_roll="1d6+2"),
        ],
        skills={"stealth": 6},
        senses=["darkvision 60 ft"],
        languages=["Common", "Goblin"],
        special_abilities=["Nimble Escape"],
    )


@pytest.fixture
def sample_dragon():
    """Create a sample dragon for testing."""
    return Monster(
        name="Young Red Dragon",
        monster_type="Dragon",
        hit_points_max=178,
        hit_points_current=178,
        armor_class=18,
        size="Large",
        creature_type="dragon",
        alignment="chaotic evil",
        speed=40,
        challenge_rating="10",
        experience_value=5900,
        abilities={
            "strength": AbilityScore(score=23),
            "dexterity": AbilityScore(score=10),
            "constitution": AbilityScore(score=21),
            "intelligence": AbilityScore(score=14),
            "wisdom": AbilityScore(score=11),
            "charisma": AbilityScore(score=19),
        },
        damage_immunities=["fire"],
        senses=["blindsight 30 ft", "darkvision 120 ft"],
        languages=["Common", "Draconic"],
        legendary_actions=["Detect", "Tail Attack", "Wing Attack"],
        legendary_actions_per_turn=3,
    )


class TestMonsterModel:
    """Test Monster model functionality."""

    def test_monster_creation(self, sample_monster):
        """Test creating a monster with all basic properties."""
        assert sample_monster.name == "Goblin Scout"
        assert sample_monster.monster_type == "Goblin"
        assert sample_monster.hit_points_max == 8
        assert sample_monster.hit_points_current == 8
        assert sample_monster.armor_class == 14
        assert sample_monster.challenge_rating == "1/4"
        assert sample_monster.experience_value == 50

    def test_monster_ability_modifiers(self, sample_monster):
        """Test that ability score modifiers are calculated correctly."""
        assert sample_monster.abilities["strength"].mod == -1  # 8 -> -1
        assert sample_monster.abilities["dexterity"].mod == 2  # 14 -> +2
        assert sample_monster.abilities["constitution"].mod == 0  # 10 -> 0

    def test_monster_with_attacks(self, sample_monster):
        """Test monster with attack actions."""
        assert len(sample_monster.attacks) == 2

        scimitar = sample_monster.attacks[0]
        assert scimitar.weapon == "Scimitar"
        assert scimitar.attack_roll_modifier == 4
        assert scimitar.damage_roll == "1d6+2"

        shortbow = sample_monster.attacks[1]
        assert shortbow.weapon == "Shortbow"
        assert shortbow.attack_roll_modifier == 4
        assert shortbow.damage_roll == "1d6+2"

    def test_monster_default_values(self):
        """Test monster creation with minimal parameters."""
        basic_monster = Monster(
            name="Basic Goblin", monster_type="Goblin", hit_points_max=5, hit_points_current=5
        )

        # Check defaults
        assert basic_monster.armor_class == 10
        assert basic_monster.size == "Medium"
        assert basic_monster.creature_type == "humanoid"
        assert basic_monster.alignment == "neutral"
        assert basic_monster.speed == 30
        assert basic_monster.challenge_rating == "1/8"
        assert basic_monster.experience_value == 25
        assert basic_monster.status == "alive"

    def test_monster_status_tracking(self, sample_monster):
        """Test monster status changes."""
        assert sample_monster.status == "alive"

        # Simulate taking damage
        sample_monster.hit_points_current = 0
        sample_monster.status = "dead"

        assert sample_monster.hit_points_current == 0
        assert sample_monster.status == "dead"

    def test_monster_special_abilities(self, sample_dragon):
        """Test monster with special abilities and legendary actions."""
        assert "fire" in sample_dragon.damage_immunities
        assert len(sample_dragon.legendary_actions) == 3
        assert sample_dragon.legendary_actions_per_turn == 3
        assert "blindsight 30 ft" in sample_dragon.senses
        assert "Draconic" in sample_dragon.languages


class TestMonsterGameStateIntegration:
    """Test monster integration with game state."""

    def test_add_monster_to_game_state(self, storage_with_campaign, sample_monster):
        """Test adding a monster to the game state."""
        campaign = storage_with_campaign.get_current_campaign()
        campaign.game_state.monsters.append(sample_monster)
        storage_with_campaign._save_campaign()

        # Verify monster was added
        monsters = campaign.game_state.monsters
        assert len(monsters) == 1
        assert monsters[0].name == sample_monster.name

    def test_multiple_monsters_in_game_state(
        self, storage_with_campaign, sample_monster, sample_dragon
    ):
        """Test managing multiple monsters in game state."""
        campaign = storage_with_campaign.get_current_campaign()
        campaign.game_state.monsters.extend([sample_monster, sample_dragon])
        storage_with_campaign._save_campaign()

        monsters = campaign.game_state.monsters
        assert len(monsters) == 2

        # Find each monster
        goblin = next((m for m in monsters if m.monster_type == "Goblin"), None)
        dragon = next((m for m in monsters if m.monster_type == "Dragon"), None)

        assert goblin is not None
        assert dragon is not None
        assert goblin.challenge_rating == "1/4"
        assert dragon.challenge_rating == "10"

    def test_remove_monster_from_game_state(self, storage_with_campaign, sample_monster):
        """Test removing a monster from game state."""
        campaign = storage_with_campaign.get_current_campaign()
        campaign.game_state.monsters.append(sample_monster)

        # Verify monster was added
        assert len(campaign.game_state.monsters) == 1

        # Remove monster
        campaign.game_state.monsters.remove(sample_monster)
        storage_with_campaign._save_campaign()

        # Verify monster was removed
        assert len(campaign.game_state.monsters) == 0

    def test_update_monster_in_game_state(self, storage_with_campaign, sample_monster):
        """Test updating monster properties in game state."""
        campaign = storage_with_campaign.get_current_campaign()
        campaign.game_state.monsters.append(sample_monster)

        # Update monster
        monster = campaign.game_state.monsters[0]
        original_hp = monster.hit_points_current
        monster.hit_points_current = 3
        monster.status = "injured"

        storage_with_campaign._save_campaign()

        # Verify changes persist
        updated_monster = campaign.game_state.monsters[0]
        assert updated_monster.hit_points_current == 3
        assert updated_monster.status == "injured"
        assert updated_monster.hit_points_current != original_hp

    def test_monster_location_tracking(self, storage_with_campaign, sample_monster):
        """Test tracking monster locations."""
        campaign = storage_with_campaign.get_current_campaign()
        campaign.game_state.monsters.append(sample_monster)

        # Update location
        monster = campaign.game_state.monsters[0]
        assert monster.location == "Forest Clearing"

        monster.location = "Dark Cave"
        storage_with_campaign._save_campaign()

        # Verify location update
        updated_monster = campaign.game_state.monsters[0]
        assert updated_monster.location == "Dark Cave"

    def test_monster_persistence_across_reloads(self, temp_storage, sample_monster):
        """Test that monsters persist when campaign is reloaded."""
        from gamemaster_mcp.storage import DnDStorage

        # Create campaign
        temp_storage.create_campaign(
            "Monster Test Campaign", "Test campaign for monster persistence"
        )

        # Add monster to game state
        campaign = temp_storage.get_current_campaign()
        campaign.game_state.monsters.append(sample_monster)
        temp_storage._save_campaign()

        # Create new storage instance and load campaign
        new_storage = DnDStorage(temp_storage.data_dir)
        new_storage.load_campaign("Monster Test Campaign")

        # Verify monster persisted
        reloaded_campaign = new_storage.get_current_campaign()
        monsters = reloaded_campaign.game_state.monsters

        assert len(monsters) == 1
        assert monsters[0].name == sample_monster.name
        assert monsters[0].monster_type == sample_monster.monster_type
        assert monsters[0].hit_points_max == sample_monster.hit_points_max

    def test_empty_monster_list_by_default(self, storage_with_campaign):
        """Test that new game states have empty monster list."""
        campaign = storage_with_campaign.get_current_campaign()
        assert isinstance(campaign.game_state.monsters, list)
        assert len(campaign.game_state.monsters) == 0


class TestMonsterCombatScenarios:
    """Test monster functionality in combat scenarios."""

    def test_monster_damage_tracking(self, sample_monster):
        """Test tracking damage to monsters."""
        original_hp = sample_monster.hit_points_current
        damage = 3

        sample_monster.hit_points_current -= damage
        assert sample_monster.hit_points_current == original_hp - damage

    def test_monster_death(self, sample_monster):
        """Test monster death mechanics."""
        sample_monster.hit_points_current = 0
        sample_monster.status = "dead"

        assert sample_monster.hit_points_current == 0
        assert sample_monster.status == "dead"

    def test_monster_healing(self, sample_dragon):
        """Test monster healing."""
        # Damage the dragon first
        sample_dragon.hit_points_current = 100

        # Heal it
        healing = 25
        new_hp = min(sample_dragon.hit_points_current + healing, sample_dragon.hit_points_max)
        sample_dragon.hit_points_current = new_hp

        assert sample_dragon.hit_points_current == 125

    def test_monster_conditions(self, sample_monster):
        """Test applying conditions to monsters."""
        # Add condition immunity
        sample_monster.condition_immunities.append("charmed")
        assert "charmed" in sample_monster.condition_immunities

    def test_multiple_monster_encounter(self, storage_with_campaign):
        """Test encounter with multiple monsters of same type."""
        campaign = storage_with_campaign.get_current_campaign()

        # Create multiple goblins
        goblin1 = Monster(
            name="Goblin 1", monster_type="Goblin", hit_points_max=7, hit_points_current=7
        )
        goblin2 = Monster(
            name="Goblin 2", monster_type="Goblin", hit_points_max=7, hit_points_current=7
        )
        goblin3 = Monster(
            name="Goblin 3", monster_type="Goblin", hit_points_max=7, hit_points_current=7
        )

        campaign.game_state.monsters.extend([goblin1, goblin2, goblin3])

        # Verify all monsters are present
        assert len(campaign.game_state.monsters) == 3

        # Each should have unique names but same type
        names = [m.name for m in campaign.game_state.monsters]
        types = [m.monster_type for m in campaign.game_state.monsters]

        assert len(set(names)) == 3  # Unique names
        assert len(set(types)) == 1  # Same type
        assert types[0] == "Goblin"
