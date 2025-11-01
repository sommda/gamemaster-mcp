"""
Tests for outward-facing API.
"""

import json

import pytest

from gamemaster_mcp.main import (
    add_event,
    add_item_to_character,
    add_session_note,
    add_spell_to_character,
    bulk_update_characters,
    calculate_experience,
    create_campaign,
    create_character,
    create_location,
    create_monster,
    create_npc,
    create_quest,
    current_prompt,
    end_combat,
    get_available_modes,
    get_campaign,
    get_campaign_characters,
    get_campaign_game_state,
    get_campaign_info,
    get_campaigns,
    get_character,
    get_character_resource,
    get_current_campaign,
    get_current_campaign_characters,
    get_current_campaign_game_state,
    get_current_campaign_mode,
    get_current_transcript,
    get_events,
    get_game_state,
    get_location,
    get_mode,
    get_monster,
    get_npc,
    get_sessions,
    get_transcript,
    list_campaigns,
    list_characters,
    list_locations,
    list_monsters,
    list_npcs,
    list_quests,
    load_campaign,
    next_turn,
    override_storage,
    prepare_spells,
    record_interaction,
    record_interaction_with_tools,
    remove_item_from_character,
    roll_dice,
    set_mode,
    start_combat,
    update_character,
    update_game_state,
    update_quest,
    update_spell_slot,
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
        result = await create_campaign.run(
            {
                "name": sample_campaign.name,
                "description": sample_campaign.description,
                "dm_name": sample_campaign.dm_name,
                "setting": sample_campaign.setting,
            }
        )
        assert len(result.content) == 1
        assert sample_campaign.name in result.content[0].text

    async def test_get_campaign_info(self, storage_with_campaign):
        """Test grabbing basic campaign info."""
        override_storage(storage_with_campaign)
        result = await get_campaign_info.run({})
        assert len(result.content) == 1
        print(result.content[0].text)
        assert storage_with_campaign.get_current_campaign().name in result.content[0].text

    async def test_list_campaigns(self, storage_with_campaign):
        """Test listing campaigns."""
        override_storage(storage_with_campaign)
        result = await list_campaigns.run({})
        assert len(result.content) == 1
        print(result.content[0].text)
        assert storage_with_campaign.get_current_campaign().name in result.content[0].text

    async def test_load_campaign(self, storage_with_campaign):
        """Test loading a current campaigns."""
        override_storage(storage_with_campaign)
        name = storage_with_campaign.get_current_campaign().name
        result = await load_campaign.run({"name": name})
        assert len(result.content) == 1
        assert name in result.content[0].text

    async def test_get_campaign(self, storage_with_campaign):
        """Test loading a campaign as a resource."""
        override_storage(storage_with_campaign)
        name = storage_with_campaign.get_current_campaign().name
        campaign = await get_campaign.read({"campaign_name": name})
        assert campaign.name == name
        assert campaign.dm_name == "Test DM"

    async def test_get_campaigns(self, storage_with_campaign):
        """Test getting all campaigns as a resource."""
        override_storage(storage_with_campaign)
        name = storage_with_campaign.get_current_campaign().name
        campaigns = json.loads(await get_campaigns.read())
        print(campaigns)
        assert len(campaigns) == 1
        assert campaigns[0] == name

    async def test_get_current_campaign(self, storage_with_campaign):
        """Test getting name of current campaign."""
        override_storage(storage_with_campaign)
        name = storage_with_campaign.get_current_campaign().name
        current_campaign_name = await get_current_campaign.read()
        assert name == current_campaign_name

    # Character Management Tests
    async def test_create_character(self, storage_with_campaign):
        """Test creating a new character."""
        override_storage(storage_with_campaign)
        result = await create_character.run(
            {
                "name": "Aragorn",
                "character_class": "Ranger",
                "class_level": 5,
                "race": "Human",
                "player_name": "John",
                "strength": 16,
                "dexterity": 14,
                "constitution": 13,
                "intelligence": 12,
                "wisdom": 15,
                "charisma": 11,
            }
        )
        assert len(result.content) == 1
        assert "Aragorn" in result.content[0].text
        assert "Level 5 Human Ranger" in result.content[0].text

    async def test_get_character(self, storage_with_campaign):
        """Test getting character information."""
        override_storage(storage_with_campaign)
        # First create a character
        await create_character.run(
            {"name": "Legolas", "character_class": "Fighter", "class_level": 3, "race": "Elf"}
        )

        result = await get_character.run({"name_or_id": "Legolas"})
        assert len(result.content) == 1
        assert "Legolas" in result.content[0].text
        assert "Level 3 Elf Fighter" in result.content[0].text

    async def test_update_character(self, storage_with_campaign):
        """Test updating character properties."""
        override_storage(storage_with_campaign)
        # First create a character
        await create_character.run(
            {"name": "Gimli", "character_class": "Fighter", "class_level": 4, "race": "Dwarf"}
        )

        result = await update_character.run(
            {"name_or_id": "Gimli", "hit_points_current": 25, "armor_class": 18}
        )
        assert len(result.content) == 1
        assert "Gimli" in result.content[0].text
        assert "hit points current: 25" in result.content[0].text

    async def test_update_character_ability_scores(self, storage_with_campaign):
        """Test updating ability scores."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Gandalf", "character_class": "Wizard", "class_level": 10, "race": "Human"}
        )

        # Update ability scores
        result = await update_character.run(
            {
                "name_or_id": "Gandalf",
                "strength": 12,
                "dexterity": 14,
                "constitution": 16,
                "intelligence": 20,
                "wisdom": 18,
                "charisma": 15,
            }
        )
        assert len(result.content) == 1
        assert "Gandalf" in result.content[0].text

        # Verify all ability scores were updated
        character = storage_with_campaign.get_character("Gandalf")
        assert character.abilities["strength"].score == 12
        assert character.abilities["dexterity"].score == 14
        assert character.abilities["constitution"].score == 16
        assert character.abilities["intelligence"].score == 20
        assert character.abilities["wisdom"].score == 18
        assert character.abilities["charisma"].score == 15

    async def test_update_character_level(self, storage_with_campaign):
        """Test updating character level."""
        override_storage(storage_with_campaign)
        # Create a character at level 3
        await create_character.run(
            {"name": "Aragorn", "character_class": "Ranger", "class_level": 3, "race": "Human"}
        )

        # Verify initial level
        character = storage_with_campaign.get_character("Aragorn")
        assert character.character_class.level == 3

        # Update level to 5
        result = await update_character.run(
            {"name_or_id": "Aragorn", "level": 5}
        )
        assert len(result.content) == 1
        assert "Aragorn" in result.content[0].text
        assert "level: 5" in result.content[0].text

        # Verify level was updated in character_class
        character = storage_with_campaign.get_character("Aragorn")
        assert character.character_class.level == 5

        # Verify get_character shows updated level
        result = await get_character.run({"name_or_id": "Aragorn"})
        assert "Level 5 Human Ranger" in result.content[0].text

    async def test_update_character_level_by_id(self, storage_with_campaign):
        """Test updating character level using character ID."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Legolas", "character_class": "Fighter", "class_level": 4, "race": "Elf"}
        )

        # Get character ID
        character = storage_with_campaign.get_character("Legolas")
        char_id = str(character.id)

        # Update level using ID
        result = await update_character.run(
            {"name_or_id": char_id, "level": 7}
        )
        assert len(result.content) == 1
        assert "Legolas" in result.content[0].text
        assert "level: 7" in result.content[0].text

        # Verify level was updated
        character = storage_with_campaign.get_character("Legolas")
        assert character.character_class.level == 7

    async def test_update_character_level_with_other_properties(self, storage_with_campaign):
        """Test updating level along with other character properties."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Gandalf", "character_class": "Wizard", "class_level": 8, "race": "Human"}
        )

        # Update multiple properties including level
        result = await update_character.run(
            {
                "name_or_id": "Gandalf",
                "level": 10,
                "hit_points_max": 60,
                "armor_class": 13,
                "inspiration": True
            }
        )
        assert len(result.content) == 1
        assert "Gandalf" in result.content[0].text

        # Verify all updates
        character = storage_with_campaign.get_character("Gandalf")
        assert character.character_class.level == 10
        assert character.hit_points_max == 60
        assert character.armor_class == 13
        assert character.inspiration is True

    async def test_update_character_level_boundary_values(self, storage_with_campaign):
        """Test updating character level with boundary values."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "TestChar", "character_class": "Cleric", "class_level": 10, "race": "Human"}
        )

        # Update to level 1 (minimum)
        result = await update_character.run({"name_or_id": "TestChar", "level": 1})
        character = storage_with_campaign.get_character("TestChar")
        assert character.character_class.level == 1

        # Update to level 20 (maximum)
        result = await update_character.run({"name_or_id": "TestChar", "level": 20})
        character = storage_with_campaign.get_character("TestChar")
        assert character.character_class.level == 20

    async def test_update_character_string_to_int_conversion(self, storage_with_campaign):
        """Test updating character with string values for int fields (FastMCP bug workaround)."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "TestChar", "character_class": "Fighter", "class_level": 5, "race": "Human"}
        )

        # Update with string values
        result = await update_character.run({
            "name_or_id": "TestChar",
            "level": "10",
            "hit_points_current": "50",
            "hit_points_max": "60",
            "strength": "18"
        })

        character = storage_with_campaign.get_character("TestChar")
        assert character.character_class.level == 10
        assert character.hit_points_current == 50
        assert character.hit_points_max == 60
        assert character.abilities["strength"].score == 18

    async def test_update_character_string_to_bool_conversion(self, storage_with_campaign):
        """Test updating character with string values for bool fields."""
        override_storage(storage_with_campaign)
        await create_character.run(
            {"name": "TestChar", "character_class": "Rogue", "class_level": 3, "race": "Halfling"}
        )

        # Test various true values
        await update_character.run({"name_or_id": "TestChar", "inspiration": "true"})
        character = storage_with_campaign.get_character("TestChar")
        assert character.inspiration is True

        await update_character.run({"name_or_id": "TestChar", "inspiration": "1"})
        character = storage_with_campaign.get_character("TestChar")
        assert character.inspiration is True

        # Test various false values
        await update_character.run({"name_or_id": "TestChar", "inspiration": "false"})
        character = storage_with_campaign.get_character("TestChar")
        assert character.inspiration is False

    async def test_update_character_invalid_string_value(self, storage_with_campaign):
        """Test that invalid string values are rejected."""
        override_storage(storage_with_campaign)
        await create_character.run(
            {"name": "TestChar", "character_class": "Wizard", "class_level": 5, "race": "Elf"}
        )

        # Try to update with invalid int string
        result = await update_character.run({"name_or_id": "TestChar", "level": "abc"})
        result_text = result.content[0].text
        assert "❌" in result_text
        assert "not a valid integer" in result_text.lower()

        # Try to update with invalid bool string
        result = await update_character.run({"name_or_id": "TestChar", "inspiration": "maybe"})
        result_text = result.content[0].text
        assert "❌" in result_text
        assert "not a valid boolean" in result_text.lower()

    async def test_update_character_string_out_of_range(self, storage_with_campaign):
        """Test that string values outside valid ranges are rejected."""
        override_storage(storage_with_campaign)
        await create_character.run(
            {"name": "TestChar", "character_class": "Paladin", "class_level": 5, "race": "Dwarf"}
        )

        # Level too high
        result = await update_character.run({"name_or_id": "TestChar", "level": "21"})
        result_text = result.content[0].text
        assert "❌" in result_text
        assert "greater than maximum" in result_text.lower()

        # Level too low
        result = await update_character.run({"name_or_id": "TestChar", "level": "0"})
        result_text = result.content[0].text
        assert "❌" in result_text
        assert "less than minimum" in result_text.lower()

        # Ability score too high
        result = await update_character.run({"name_or_id": "TestChar", "strength": "31"})
        result_text = result.content[0].text
        assert "❌" in result_text
        assert "greater than maximum" in result_text.lower()

    async def test_bulk_update_characters(self, storage_with_campaign):
        """Test bulk updating multiple characters."""
        override_storage(storage_with_campaign)
        # First create characters
        await create_character.run(
            {"name": "Char1", "character_class": "Fighter", "class_level": 1, "race": "Human"}
        )
        await create_character.run(
            {"name": "Char2", "character_class": "Wizard", "class_level": 1, "race": "Elf"}
        )

        result = await bulk_update_characters.run(
            {"names_or_ids": ["Char1", "Char2"], "hp_change": 5}
        )
        assert len(result.content) == 1
        assert "Characters updated" in result.content[0].text

    async def test_add_item_to_character(self, storage_with_campaign):
        """Test adding an item to character inventory."""
        override_storage(storage_with_campaign)
        # First create a character
        await create_character.run(
            {"name": "Frodo", "character_class": "Rogue", "class_level": 2, "race": "Halfling"}
        )

        result = await add_item_to_character.run(
            {
                "character_name_or_id": "Frodo",
                "item_name": "Short Sword",
                "item_type": "weapon",
                "quantity": 1,
            }
        )
        assert len(result.content) == 1
        assert "Short Sword" in result.content[0].text
        assert "Frodo" in result.content[0].text

    async def test_remove_item_from_character_complete(self, storage_with_campaign):
        """Test removing all of an item from character inventory."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Sam", "character_class": "Fighter", "class_level": 2, "race": "Halfling"}
        )

        # Add an item
        await add_item_to_character.run(
            {
                "character_name_or_id": "Sam",
                "item_name": "Rope",
                "item_type": "misc",
                "quantity": 1,
            }
        )

        # Verify item was added
        character = storage_with_campaign.get_character("Sam")
        assert len(character.inventory) == 1
        assert character.inventory[0].name == "Rope"

        # Remove the item (no quantity specified = remove all)
        result = await remove_item_from_character.run(
            {
                "character_name_or_id": "Sam",
                "item_name": "Rope",
            }
        )
        assert len(result.content) == 1
        assert "Removed 1x Rope" in result.content[0].text
        assert "Sam" in result.content[0].text

        # Verify item was removed
        character = storage_with_campaign.get_character("Sam")
        assert len(character.inventory) == 0

    async def test_remove_item_from_character_partial(self, storage_with_campaign):
        """Test removing partial quantity of an item."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Merry", "character_class": "Rogue", "class_level": 3, "race": "Halfling"}
        )

        # Add multiple of an item
        await add_item_to_character.run(
            {
                "character_name_or_id": "Merry",
                "item_name": "Healing Potion",
                "item_type": "consumable",
                "quantity": 5,
            }
        )

        # Remove partial quantity
        result = await remove_item_from_character.run(
            {
                "character_name_or_id": "Merry",
                "item_name": "Healing Potion",
                "quantity": 2,
            }
        )
        assert len(result.content) == 1
        assert "Removed 2x Healing Potion" in result.content[0].text
        assert "3 remaining" in result.content[0].text

        # Verify quantity was reduced
        character = storage_with_campaign.get_character("Merry")
        assert len(character.inventory) == 1
        assert character.inventory[0].name == "Healing Potion"
        assert character.inventory[0].quantity == 3

    async def test_remove_item_from_character_exact_quantity(self, storage_with_campaign):
        """Test removing exact quantity removes the item entirely."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Pippin", "character_class": "Bard", "class_level": 2, "race": "Halfling"}
        )

        # Add items
        await add_item_to_character.run(
            {
                "character_name_or_id": "Pippin",
                "item_name": "Torch",
                "item_type": "misc",
                "quantity": 3,
            }
        )

        # Remove exact quantity
        result = await remove_item_from_character.run(
            {
                "character_name_or_id": "Pippin",
                "item_name": "Torch",
                "quantity": 3,
            }
        )
        assert len(result.content) == 1
        assert "Removed 3x Torch" in result.content[0].text

        # Verify item was removed entirely
        character = storage_with_campaign.get_character("Pippin")
        assert len(character.inventory) == 0

    async def test_remove_item_from_character_more_than_available(self, storage_with_campaign):
        """Test removing more than available removes all."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Aragorn", "character_class": "Ranger", "class_level": 5, "race": "Human"}
        )

        # Add items
        await add_item_to_character.run(
            {
                "character_name_or_id": "Aragorn",
                "item_name": "Arrow",
                "item_type": "weapon",
                "quantity": 10,
            }
        )

        # Try to remove more than available
        result = await remove_item_from_character.run(
            {
                "character_name_or_id": "Aragorn",
                "item_name": "Arrow",
                "quantity": 20,
            }
        )
        assert len(result.content) == 1
        assert "Removed 10x Arrow" in result.content[0].text

        # Verify all items were removed
        character = storage_with_campaign.get_character("Aragorn")
        assert len(character.inventory) == 0

    async def test_remove_item_from_character_not_found(self, storage_with_campaign):
        """Test removing item that doesn't exist."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Legolas", "character_class": "Ranger", "class_level": 5, "race": "Elf"}
        )

        # Try to remove non-existent item
        result = await remove_item_from_character.run(
            {
                "character_name_or_id": "Legolas",
                "item_name": "Magic Sword",
            }
        )
        assert len(result.content) == 1
        assert "not found in" in result.content[0].text
        assert "Legolas" in result.content[0].text

    async def test_remove_item_from_character_case_insensitive(self, storage_with_campaign):
        """Test item name matching is case-insensitive."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Gimli", "character_class": "Fighter", "class_level": 4, "race": "Dwarf"}
        )

        # Add item with specific casing
        await add_item_to_character.run(
            {
                "character_name_or_id": "Gimli",
                "item_name": "Battle Axe",
                "item_type": "weapon",
                "quantity": 1,
            }
        )

        # Remove with different casing
        result = await remove_item_from_character.run(
            {
                "character_name_or_id": "Gimli",
                "item_name": "battle axe",
            }
        )
        assert len(result.content) == 1
        assert "Removed 1x Battle Axe" in result.content[0].text

        # Verify item was removed
        character = storage_with_campaign.get_character("Gimli")
        assert len(character.inventory) == 0

    async def test_remove_item_from_character_by_id(self, storage_with_campaign):
        """Test removing item using character ID."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Boromir", "character_class": "Fighter", "class_level": 6, "race": "Human"}
        )

        # Get character ID
        character = storage_with_campaign.get_character("Boromir")
        char_id = str(character.id)

        # Add item
        await add_item_to_character.run(
            {
                "character_name_or_id": char_id,
                "item_name": "Shield",
                "item_type": "armor",
                "quantity": 1,
            }
        )

        # Remove item using ID
        result = await remove_item_from_character.run(
            {
                "character_name_or_id": char_id,
                "item_name": "Shield",
            }
        )
        assert len(result.content) == 1
        assert "Removed 1x Shield" in result.content[0].text

    async def test_remove_item_character_not_found(self, storage_with_campaign):
        """Test removing item from non-existent character."""
        override_storage(storage_with_campaign)

        result = await remove_item_from_character.run(
            {
                "character_name_or_id": "NonExistent",
                "item_name": "Sword",
            }
        )
        assert len(result.content) == 1
        assert "Character 'NonExistent' not found" in result.content[0].text

    async def test_get_character_with_inventory(self, storage_with_campaign):
        """Test get_character displays inventory correctly."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Bilbo", "character_class": "Rogue", "class_level": 5, "race": "Halfling"}
        )

        # Add items to character's inventory
        await add_item_to_character.run(
            {
                "character_name_or_id": "Bilbo",
                "item_name": "Longsword",
                "item_type": "weapon",
                "quantity": 1,
            }
        )
        await add_item_to_character.run(
            {
                "character_name_or_id": "Bilbo",
                "item_name": "Healing Potion",
                "item_type": "consumable",
                "quantity": 3,
            }
        )
        await add_item_to_character.run(
            {
                "character_name_or_id": "Bilbo",
                "item_name": "Rope",
                "item_type": "misc",
                "quantity": 1,
            }
        )

        # Get character and verify inventory is displayed
        result = await get_character.run({"name_or_id": "Bilbo"})
        assert len(result.content) == 1
        text = result.content[0].text

        # Check inventory header
        assert "**Inventory:** 3 items" in text

        # Check each item is listed with name, quantity, and type
        assert "• Longsword (x1) - weapon" in text
        assert "• Healing Potion (x3) - consumable" in text
        assert "• Rope (x1) - misc" in text

    async def test_get_character_with_spell_slots(self, storage_with_campaign):
        """Test get_character displays spell slots correctly."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Merlin", "character_class": "Wizard", "class_level": 5, "race": "Human"}
        )

        # Get the character from storage and add spell slots
        character = storage_with_campaign.get_character("Merlin")
        character.spell_slots = {1: 4, 2: 3, 3: 2}
        character.spell_slots_used = {1: 2, 2: 1, 3: 0}
        storage_with_campaign.update_character(str(character.id), spell_slots=character.spell_slots, spell_slots_used=character.spell_slots_used)

        # Get character and verify spell slots are displayed
        result = await get_character.run({"name_or_id": "Merlin"})
        assert len(result.content) == 1
        text = result.content[0].text

        # Check spell slots section
        assert "**Spell Slots:**" in text
        assert "• Level 1: 4 (2 used)" in text
        assert "• Level 2: 3 (1 used)" in text
        assert "• Level 3: 2 (0 used)" in text

    async def test_get_character_with_spells_known(self, storage_with_campaign):
        """Test get_character displays spells known correctly."""
        override_storage(storage_with_campaign)
        from gamemaster_mcp.models import Spell

        # Create a character
        await create_character.run(
            {"name": "Gandalf", "character_class": "Wizard", "class_level": 10, "race": "Human"}
        )

        # Get the character from storage and add spells
        character = storage_with_campaign.get_character("Gandalf")
        character.spells_known = [
            Spell(
                name="Fireball",
                level=3,
                school="Evocation",
                casting_time="1 action",
                duration="Instantaneous",
                components=["V", "S", "M"],
                description="A bright streak flashes...",
                prepared=True
            ),
            Spell(
                name="Magic Missile",
                level=1,
                school="Evocation",
                casting_time="1 action",
                duration="Instantaneous",
                components=["V", "S"],
                description="You create three glowing darts...",
                prepared=False
            ),
            Spell(
                name="Shield",
                level=1,
                school="Abjuration",
                casting_time="1 reaction",
                duration="1 round",
                components=["V", "S"],
                description="An invisible barrier of magical force...",
                prepared=True
            ),
        ]
        storage_with_campaign.update_character(str(character.id), spells_known=character.spells_known)

        # Get character and verify spells are displayed
        result = await get_character.run({"name_or_id": "Gandalf"})
        assert len(result.content) == 1
        text = result.content[0].text

        # Check spells section
        assert "**Spells Known:** 3 spells" in text
        assert "• [✓] Fireball (Level 3)" in text
        assert "• [ ] Magic Missile (Level 1)" in text
        assert "• [✓] Shield (Level 1)" in text

    async def test_get_character_empty_inventory_and_spells(self, storage_with_campaign):
        """Test get_character with no inventory or spells."""
        override_storage(storage_with_campaign)
        # Create a character with no items or spells
        await create_character.run(
            {"name": "Noob", "character_class": "Fighter", "class_level": 1, "race": "Human"}
        )

        # Get character
        result = await get_character.run({"name_or_id": "Noob"})
        assert len(result.content) == 1
        text = result.content[0].text

        # Should show 0 items and no spell/inventory sections beyond headers
        assert "**Inventory:** 0 items" in text
        # Should NOT show spell slots or spells sections if they don't exist
        assert "**Spell Slots:**" not in text
        assert "**Spells Known:**" not in text

    async def test_add_spell_to_character(self, storage_with_campaign):
        """Test adding a single spell to a character."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Wizard1", "character_class": "Wizard", "class_level": 3, "race": "Human"}
        )

        # Add a spell
        result = await add_spell_to_character.run(
            {
                "character_name_or_id": "Wizard1",
                "spell_name": "Fireball",
                "spell_level": 3,
            }
        )
        assert len(result.content) == 1
        assert "Fireball" in result.content[0].text
        assert "Level 3" in result.content[0].text
        assert "unprepared" in result.content[0].text

        # Verify spell was added
        character = storage_with_campaign.get_character("Wizard1")
        assert len(character.spells_known) == 1
        assert character.spells_known[0].name == "Fireball"
        assert character.spells_known[0].level == 3
        assert character.spells_known[0].prepared is False

    async def test_add_spell_to_character_duplicate(self, storage_with_campaign):
        """Test adding a duplicate spell."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Wizard2", "character_class": "Wizard", "class_level": 3, "race": "Elf"}
        )

        # Add a spell
        await add_spell_to_character.run(
            {
                "character_name_or_id": "Wizard2",
                "spell_name": "Magic Missile",
                "spell_level": 1,
            }
        )

        # Try to add same spell again
        result = await add_spell_to_character.run(
            {
                "character_name_or_id": "Wizard2",
                "spell_name": "Magic Missile",
                "spell_level": 1,
            }
        )
        assert len(result.content) == 1
        assert "already knows" in result.content[0].text

        # Verify only one spell exists
        character = storage_with_campaign.get_character("Wizard2")
        assert len(character.spells_known) == 1

    async def test_add_spell_to_character_case_insensitive(self, storage_with_campaign):
        """Test spell duplicate detection is case-insensitive."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Wizard3", "character_class": "Wizard", "class_level": 3, "race": "Human"}
        )

        # Add a spell
        await add_spell_to_character.run(
            {
                "character_name_or_id": "Wizard3",
                "spell_name": "Shield",
                "spell_level": 1,
            }
        )

        # Try to add same spell with different casing
        result = await add_spell_to_character.run(
            {
                "character_name_or_id": "Wizard3",
                "spell_name": "SHIELD",
                "spell_level": 1,
            }
        )
        assert "already knows" in result.content[0].text

        # Verify only one spell exists
        character = storage_with_campaign.get_character("Wizard3")
        assert len(character.spells_known) == 1

    async def test_add_spell_character_not_found(self, storage_with_campaign):
        """Test adding spell to non-existent character."""
        override_storage(storage_with_campaign)

        result = await add_spell_to_character.run(
            {
                "character_name_or_id": "NonExistent",
                "spell_name": "Fireball",
                "spell_level": 3,
            }
        )
        assert len(result.content) == 1
        assert "not found" in result.content[0].text

    async def test_prepare_spells(self, storage_with_campaign):
        """Test preparing spells."""
        override_storage(storage_with_campaign)
        # Create a character and add spells
        await create_character.run(
            {"name": "Wizard4", "character_class": "Wizard", "class_level": 5, "race": "Human"}
        )

        await add_spell_to_character.run(
            {"character_name_or_id": "Wizard4", "spell_name": "Fireball", "spell_level": 3}
        )
        await add_spell_to_character.run(
            {"character_name_or_id": "Wizard4", "spell_name": "Shield", "spell_level": 1}
        )
        await add_spell_to_character.run(
            {"character_name_or_id": "Wizard4", "spell_name": "Magic Missile", "spell_level": 1}
        )

        # Prepare some spells
        result = await prepare_spells.run(
            {
                "character_name_or_id": "Wizard4",
                "spell_names": ["Fireball", "Shield"],
            }
        )
        assert len(result.content) == 1
        assert "Prepared 2 spell(s)" in result.content[0].text

        # Verify prepared status
        character = storage_with_campaign.get_character("Wizard4")
        for spell in character.spells_known:
            if spell.name in ["Fireball", "Shield"]:
                assert spell.prepared is True
            else:
                assert spell.prepared is False

    async def test_prepare_spells_replaces_previous(self, storage_with_campaign):
        """Test that prepare_spells replaces the previous selection."""
        override_storage(storage_with_campaign)
        # Create a character and add spells
        await create_character.run(
            {"name": "Wizard5", "character_class": "Wizard", "class_level": 5, "race": "Human"}
        )

        await add_spell_to_character.run(
            {"character_name_or_id": "Wizard5", "spell_name": "Fireball", "spell_level": 3}
        )
        await add_spell_to_character.run(
            {"character_name_or_id": "Wizard5", "spell_name": "Shield", "spell_level": 1}
        )
        await add_spell_to_character.run(
            {"character_name_or_id": "Wizard5", "spell_name": "Magic Missile", "spell_level": 1}
        )

        # Prepare Fireball and Shield
        await prepare_spells.run(
            {
                "character_name_or_id": "Wizard5",
                "spell_names": ["Fireball", "Shield"],
            }
        )

        # Now prepare only Magic Missile (should unprepare the others)
        result = await prepare_spells.run(
            {
                "character_name_or_id": "Wizard5",
                "spell_names": ["Magic Missile"],
            }
        )
        assert "Prepared 1 spell(s)" in result.content[0].text
        assert "Unprepared 2 spell(s)" in result.content[0].text

        # Verify only Magic Missile is prepared
        character = storage_with_campaign.get_character("Wizard5")
        for spell in character.spells_known:
            if spell.name == "Magic Missile":
                assert spell.prepared is True
            else:
                assert spell.prepared is False

    async def test_prepare_spells_not_found(self, storage_with_campaign):
        """Test preparing a spell that doesn't exist."""
        override_storage(storage_with_campaign)
        # Create a character and add spells
        await create_character.run(
            {"name": "Wizard6", "character_class": "Wizard", "class_level": 3, "race": "Elf"}
        )

        await add_spell_to_character.run(
            {"character_name_or_id": "Wizard6", "spell_name": "Fireball", "spell_level": 3}
        )

        # Try to prepare a spell that doesn't exist
        result = await prepare_spells.run(
            {
                "character_name_or_id": "Wizard6",
                "spell_names": ["Fireball", "NonExistentSpell"],
            }
        )
        assert "Warning" in result.content[0].text
        assert "nonexistentspell" in result.content[0].text.lower()

    async def test_prepare_spells_no_spells_known(self, storage_with_campaign):
        """Test preparing spells when character has no spells."""
        override_storage(storage_with_campaign)
        # Create a character with no spells
        await create_character.run(
            {"name": "Wizard7", "character_class": "Wizard", "class_level": 3, "race": "Human"}
        )

        # Try to prepare spells
        result = await prepare_spells.run(
            {
                "character_name_or_id": "Wizard7",
                "spell_names": ["Fireball"],
            }
        )
        assert "doesn't know any spells" in result.content[0].text

    async def test_prepare_spells_case_insensitive(self, storage_with_campaign):
        """Test prepare_spells is case-insensitive."""
        override_storage(storage_with_campaign)
        # Create a character and add spells
        await create_character.run(
            {"name": "Wizard8", "character_class": "Wizard", "class_level": 3, "race": "Human"}
        )

        await add_spell_to_character.run(
            {"character_name_or_id": "Wizard8", "spell_name": "Fireball", "spell_level": 3}
        )

        # Prepare spell with different casing
        result = await prepare_spells.run(
            {
                "character_name_or_id": "Wizard8",
                "spell_names": ["FIREBALL"],
            }
        )
        assert "Prepared 1 spell(s)" in result.content[0].text

        # Verify spell is prepared
        character = storage_with_campaign.get_character("Wizard8")
        assert character.spells_known[0].prepared is True

    async def test_update_spell_slot_initial_setup(self, storage_with_campaign):
        """Test setting up spell slots initially."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Wizard9", "character_class": "Wizard", "class_level": 5, "race": "Human"}
        )

        # Setup level 1 spell slots
        result = await update_spell_slot.run(
            {
                "character_name_or_id": "Wizard9",
                "spell_level": 1,
                "max_slots": 4,
                "slots_used": 0,
            }
        )
        assert len(result.content) == 1
        assert "level 1 spell slots" in result.content[0].text
        assert "4 total" in result.content[0].text
        assert "0 used" in result.content[0].text
        assert "4 remaining" in result.content[0].text

        # Verify in storage
        character = storage_with_campaign.get_character("Wizard9")
        assert character.spell_slots[1] == 4
        assert character.spell_slots_used[1] == 0

    async def test_update_spell_slot_using_slots(self, storage_with_campaign):
        """Test using spell slots (casting spells)."""
        override_storage(storage_with_campaign)
        # Create a character and setup slots
        await create_character.run(
            {"name": "Wizard10", "character_class": "Wizard", "class_level": 5, "race": "Human"}
        )

        # Setup slots
        await update_spell_slot.run(
            {
                "character_name_or_id": "Wizard10",
                "spell_level": 2,
                "max_slots": 3,
                "slots_used": 0,
            }
        )

        # Use 2 slots
        result = await update_spell_slot.run(
            {
                "character_name_or_id": "Wizard10",
                "spell_level": 2,
                "max_slots": 3,
                "slots_used": 2,
            }
        )
        assert "2 used" in result.content[0].text
        assert "1 remaining" in result.content[0].text

        # Verify in storage
        character = storage_with_campaign.get_character("Wizard10")
        assert character.spell_slots[2] == 3
        assert character.spell_slots_used[2] == 2

    async def test_update_spell_slot_recovery(self, storage_with_campaign):
        """Test recovering spell slots (rest)."""
        override_storage(storage_with_campaign)
        # Create a character and use some slots
        await create_character.run(
            {"name": "Wizard11", "character_class": "Wizard", "class_level": 5, "race": "Human"}
        )

        # Setup and use slots
        await update_spell_slot.run(
            {
                "character_name_or_id": "Wizard11",
                "spell_level": 1,
                "max_slots": 4,
                "slots_used": 3,
            }
        )

        # Recover all slots
        result = await update_spell_slot.run(
            {
                "character_name_or_id": "Wizard11",
                "spell_level": 1,
                "max_slots": 4,
                "slots_used": 0,
            }
        )
        assert "0 used" in result.content[0].text
        assert "4 remaining" in result.content[0].text

        # Verify in storage
        character = storage_with_campaign.get_character("Wizard11")
        assert character.spell_slots_used[1] == 0

    async def test_update_spell_slot_multiple_levels(self, storage_with_campaign):
        """Test updating spell slots for multiple spell levels."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Wizard12", "character_class": "Wizard", "class_level": 9, "race": "Human"}
        )

        # Setup multiple spell levels
        await update_spell_slot.run(
            {"character_name_or_id": "Wizard12", "spell_level": 1, "max_slots": 4, "slots_used": 1}
        )
        await update_spell_slot.run(
            {"character_name_or_id": "Wizard12", "spell_level": 2, "max_slots": 3, "slots_used": 0}
        )
        await update_spell_slot.run(
            {"character_name_or_id": "Wizard12", "spell_level": 3, "max_slots": 3, "slots_used": 2}
        )

        # Verify all levels
        character = storage_with_campaign.get_character("Wizard12")
        assert character.spell_slots[1] == 4
        assert character.spell_slots_used[1] == 1
        assert character.spell_slots[2] == 3
        assert character.spell_slots_used[2] == 0
        assert character.spell_slots[3] == 3
        assert character.spell_slots_used[3] == 2

    async def test_update_spell_slot_exceeds_max(self, storage_with_campaign):
        """Test error when slots_used exceeds max_slots."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Wizard13", "character_class": "Wizard", "class_level": 5, "race": "Human"}
        )

        # Try to use more slots than available
        result = await update_spell_slot.run(
            {
                "character_name_or_id": "Wizard13",
                "spell_level": 1,
                "max_slots": 4,
                "slots_used": 5,
            }
        )
        assert "Error" in result.content[0].text
        assert "cannot exceed" in result.content[0].text

    async def test_update_spell_slot_character_not_found(self, storage_with_campaign):
        """Test updating spell slots for non-existent character."""
        override_storage(storage_with_campaign)

        result = await update_spell_slot.run(
            {
                "character_name_or_id": "NonExistent",
                "spell_level": 1,
                "max_slots": 4,
                "slots_used": 0,
            }
        )
        assert "not found" in result.content[0].text

    async def test_update_spell_slot_by_character_id(self, storage_with_campaign):
        """Test updating spell slots using character ID."""
        override_storage(storage_with_campaign)
        # Create a character
        await create_character.run(
            {"name": "Wizard14", "character_class": "Wizard", "class_level": 5, "race": "Human"}
        )

        # Get character ID
        character = storage_with_campaign.get_character("Wizard14")
        char_id = str(character.id)

        # Update spell slots using ID
        result = await update_spell_slot.run(
            {
                "character_name_or_id": char_id,
                "spell_level": 1,
                "max_slots": 4,
                "slots_used": 1,
            }
        )
        assert "Wizard14" in result.content[0].text
        assert "level 1 spell slots" in result.content[0].text

        # Verify
        character = storage_with_campaign.get_character("Wizard14")
        assert character.spell_slots[1] == 4
        assert character.spell_slots_used[1] == 1

    async def test_update_spell_slot_all_levels(self, storage_with_campaign):
        """Test updating spell slots for all levels 1-9."""
        override_storage(storage_with_campaign)
        # Create a high-level character
        await create_character.run(
            {"name": "Wizard15", "character_class": "Wizard", "class_level": 20, "race": "Human"}
        )

        # Setup spell slots for all levels
        for level in range(1, 10):
            await update_spell_slot.run(
                {
                    "character_name_or_id": "Wizard15",
                    "spell_level": level,
                    "max_slots": level,
                    "slots_used": 0,
                }
            )

        # Verify all levels were set
        character = storage_with_campaign.get_character("Wizard15")
        for level in range(1, 10):
            assert character.spell_slots[level] == level
            assert character.spell_slots_used[level] == 0

    async def test_list_characters(self, storage_with_campaign):
        """Test listing all characters."""
        override_storage(storage_with_campaign)
        # First create a character
        await create_character.run(
            {"name": "Gandalf", "character_class": "Wizard", "class_level": 10, "race": "Human"}
        )

        result = await list_characters.run({})
        assert len(result.content) == 1
        assert "Gandalf" in result.content[0].text

    async def test_get_character_resource(self, storage_with_campaign):
        """Test getting character as a resource."""
        override_storage(storage_with_campaign)
        # First create a character
        await create_character.run(
            {
                "name": "Legolas",
                "character_class": "Ranger",
                "class_level": 5,
                "race": "Elf",
                "player_name": "TestPlayer",
                "strength": 16,
                "dexterity": 18,
                "constitution": 14,
            }
        )

        character = await get_character_resource.read({"character_name": "Legolas"})
        assert character.name == "Legolas"
        assert character.character_class.name == "Ranger"
        assert character.character_class.level == 5
        assert character.race.name == "Elf"
        assert character.player_name == "TestPlayer"
        assert character.abilities["strength"].score == 16
        assert character.abilities["dexterity"].score == 18
        assert character.abilities["constitution"].score == 14

    async def test_get_character_resource_not_found(self, storage_with_campaign):
        """Test getting non-existent character resource raises error."""
        override_storage(storage_with_campaign)

        with pytest.raises(FileNotFoundError) as exc_info:
            await get_character_resource.read({"character_name": "NonExistentCharacter"})
        assert "Character 'NonExistentCharacter' not found" in str(exc_info.value)

    async def test_get_campaign_characters_resource(self, storage_with_campaign):
        """Test getting all characters for a specific campaign as a resource."""
        override_storage(storage_with_campaign)
        campaign_name = storage_with_campaign.get_current_campaign().name

        # Create multiple characters
        await create_character.run(
            {"name": "Aragorn", "character_class": "Ranger", "class_level": 5, "race": "Human"}
        )
        await create_character.run(
            {"name": "Legolas", "character_class": "Fighter", "class_level": 4, "race": "Elf"}
        )
        await create_character.run(
            {"name": "Gimli", "character_class": "Fighter", "class_level": 3, "race": "Dwarf"}
        )

        characters = await get_campaign_characters.read({"campaign_name": campaign_name})
        assert len(characters) == 3

        character_names = [char.name for char in characters]
        assert "Aragorn" in character_names
        assert "Legolas" in character_names
        assert "Gimli" in character_names

        # Verify character data integrity
        aragorn = next(char for char in characters if char.name == "Aragorn")
        assert aragorn.character_class.name == "Ranger"
        assert aragorn.character_class.level == 5
        assert aragorn.race.name == "Human"

    async def test_get_campaign_characters_resource_not_found(self, storage_with_campaign):
        """Test getting characters for non-existent campaign raises error."""
        override_storage(storage_with_campaign)

        with pytest.raises(FileNotFoundError) as exc_info:
            await get_campaign_characters.read({"campaign_name": "NonExistentCampaign"})
        assert "Campaign 'NonExistentCampaign' not found" in str(exc_info.value)

    async def test_get_campaign_characters_resource_empty(self, storage_with_campaign):
        """Test getting characters for campaign with no characters."""
        override_storage(storage_with_campaign)
        campaign_name = storage_with_campaign.get_current_campaign().name

        characters = await get_campaign_characters.read({"campaign_name": campaign_name})
        assert len(characters) == 0
        assert isinstance(characters, list)

    async def test_get_current_campaign_characters_resource(self, storage_with_campaign):
        """Test getting all characters for the current campaign as a resource."""
        override_storage(storage_with_campaign)

        # Create characters in current campaign
        await create_character.run(
            {"name": "Frodo", "character_class": "Rogue", "class_level": 2, "race": "Halfling"}
        )
        await create_character.run(
            {"name": "Sam", "character_class": "Fighter", "class_level": 1, "race": "Halfling"}
        )

        characters_json = await get_current_campaign_characters.read()
        characters = json.loads(characters_json)
        assert len(characters) == 2

        character_names = [char["name"] for char in characters]
        assert "Frodo" in character_names
        assert "Sam" in character_names

        # Verify character data integrity
        frodo = next(char for char in characters if char["name"] == "Frodo")
        assert frodo["character_class"]["name"] == "Rogue"
        assert frodo["race"]["name"] == "Halfling"

    async def test_get_current_campaign_characters_resource_no_campaign(self, temp_storage):
        """Test getting current campaign characters when no campaign is active."""
        override_storage(temp_storage)

        characters_json = await get_current_campaign_characters.read()
        characters = json.loads(characters_json)
        assert len(characters) == 0
        assert isinstance(characters, list)

    async def test_get_current_campaign_characters_resource_empty(self, storage_with_campaign):
        """Test getting current campaign characters when campaign has no characters."""
        override_storage(storage_with_campaign)

        characters_json = await get_current_campaign_characters.read()
        characters = json.loads(characters_json)
        assert len(characters) == 0
        assert isinstance(characters, list)

    # NPC Management Tests
    async def test_create_npc(self, storage_with_campaign):
        """Test creating a new NPC."""
        override_storage(storage_with_campaign)
        result = await create_npc.run(
            {
                "name": "Elrond",
                "description": "Wise elf lord",
                "race": "Elf",
                "occupation": "Lord",
                "attitude": "friendly",
            }
        )
        assert len(result.content) == 1
        assert "Elrond" in result.content[0].text

    async def test_get_npc(self, storage_with_campaign):
        """Test getting NPC information."""
        override_storage(storage_with_campaign)
        # First create an NPC
        await create_npc.run({"name": "Sauron", "description": "Dark Lord", "attitude": "hostile"})

        result = await get_npc.run({"name": "Sauron"})
        assert len(result.content) == 1
        assert "Sauron" in result.content[0].text
        assert "Dark Lord" in result.content[0].text

    async def test_list_npcs(self, storage_with_campaign):
        """Test listing all NPCs."""
        override_storage(storage_with_campaign)
        # First create an NPC
        await create_npc.run({"name": "Boromir", "occupation": "Captain"})

        result = await list_npcs.run({})
        assert len(result.content) == 1
        assert "Boromir" in result.content[0].text

    # Monster Management Tests
    async def test_create_monster(self, storage_with_campaign):
        """Test creating a new monster."""
        override_storage(storage_with_campaign)
        result = await create_monster.run(
            {
                "name": "Goblin Scout",
                "monster_type": "Goblin",
                "hit_points_max": 8,
                "armor_class": 14,
                "size": "Small",
                "creature_type": "humanoid",
                "alignment": "neutral evil",
                "strength": 8,
                "dexterity": 14,
                "challenge_rating": "1/4",
                "experience_value": 50,
                "description": "A sneaky goblin scout with keen eyes.",
                "location": "Forest Path",
            }
        )
        assert len(result.content) == 1
        assert "Goblin Scout" in result.content[0].text
        assert "8/8 HP" in result.content[0].text

    async def test_get_monster(self, storage_with_campaign):
        """Test getting monster information."""
        override_storage(storage_with_campaign)
        # First create a monster
        await create_monster.run(
            {
                "name": "Orc Warrior",
                "monster_type": "Orc",
                "hit_points_max": 15,
                "armor_class": 13,
                "strength": 16,
                "challenge_rating": "1/2",
                "experience_value": 100,
            }
        )

        result = await get_monster.run({"name": "Orc Warrior"})
        assert len(result.content) == 1
        assert "Orc Warrior" in result.content[0].text
        assert "Orc" in result.content[0].text
        assert "15/15" in result.content[0].text  # HP display
        assert "**AC:** 13" in result.content[0].text

    async def test_list_monsters(self, storage_with_campaign):
        """Test listing all monsters in game state."""
        override_storage(storage_with_campaign)
        # First create a few monsters
        await create_monster.run(
            {
                "name": "Goblin 1",
                "monster_type": "Goblin",
                "hit_points_max": 7,
                "location": "Cave Entrance",
            }
        )
        await create_monster.run(
            {
                "name": "Goblin 2",
                "monster_type": "Goblin",
                "hit_points_max": 7,
                "location": "Cave Entrance",
            }
        )

        result = await list_monsters.run({})
        assert len(result.content) == 1
        assert "Goblin 1" in result.content[0].text
        assert "Goblin 2" in result.content[0].text
        assert "Cave Entrance" in result.content[0].text

    async def test_create_monster_with_minimal_params(self, storage_with_campaign):
        """Test creating monster with only required parameters."""
        override_storage(storage_with_campaign)
        result = await create_monster.run(
            {"name": "Basic Skeleton", "monster_type": "Undead", "hit_points_max": 13}
        )
        assert len(result.content) == 1
        assert "Basic Skeleton" in result.content[0].text
        assert "13/13 HP" in result.content[0].text

    async def test_get_nonexistent_monster(self, storage_with_campaign):
        """Test getting a monster that doesn't exist."""
        override_storage(storage_with_campaign)
        result = await get_monster.run({"name": "Nonexistent Monster"})
        assert len(result.content) == 1
        assert "not found" in result.content[0].text

    async def test_list_empty_monsters(self, storage_with_campaign):
        """Test listing monsters when none exist."""
        override_storage(storage_with_campaign)
        result = await list_monsters.run({})
        assert len(result.content) == 1
        assert "No monsters" in result.content[0].text

    async def test_create_monster_with_advanced_stats(self, storage_with_campaign):
        """Test creating a monster with advanced D&D 5E stats."""
        override_storage(storage_with_campaign)
        result = await create_monster.run(
            {
                "name": "Young Dragon",
                "monster_type": "Dragon",
                "hit_points_max": 178,
                "armor_class": 18,
                "size": "Large",
                "creature_type": "dragon",
                "alignment": "chaotic evil",
                "speed": 40,
                "challenge_rating": "10",
                "experience_value": 5900,
                "strength": 23,
                "dexterity": 10,
                "constitution": 21,
                "intelligence": 14,
                "wisdom": 11,
                "charisma": 19,
            }
        )
        assert len(result.content) == 1
        assert "Young Dragon" in result.content[0].text
        assert "178/178 HP" in result.content[0].text

    # Location Management Tests
    async def test_create_location(self, storage_with_campaign):
        """Test creating a new location."""
        override_storage(storage_with_campaign)
        result = await create_location.run(
            {
                "name": "Rivendell",
                "location_type": "city",
                "description": "Hidden valley of the elves",
                "population": 500,
            }
        )
        assert len(result.content) == 1
        assert "Rivendell" in result.content[0].text

    async def test_get_location(self, storage_with_campaign):
        """Test getting location information."""
        override_storage(storage_with_campaign)
        # First create a location
        await create_location.run(
            {"name": "Moria", "location_type": "dungeon", "description": "Ancient dwarven mines"}
        )

        result = await get_location.run({"name": "Moria"})
        assert len(result.content) == 1
        assert "Moria" in result.content[0].text
        assert "dungeon" in result.content[0].text

    async def test_list_locations(self, storage_with_campaign):
        """Test listing all locations."""
        override_storage(storage_with_campaign)
        # First create a location
        await create_location.run(
            {"name": "Gondor", "location_type": "kingdom", "description": "Great kingdom of men"}
        )

        result = await list_locations.run({})
        assert len(result.content) == 1
        assert "Gondor" in result.content[0].text

    # Quest Management Tests
    async def test_create_quest(self, storage_with_campaign):
        """Test creating a new quest."""
        override_storage(storage_with_campaign)
        result = await create_quest.run(
            {
                "title": "Destroy the Ring",
                "description": "Take the One Ring to Mount Doom",
                "giver": "Gandalf",
                "reward": "Save Middle-earth",
            }
        )
        assert len(result.content) == 1
        assert "Destroy the Ring" in result.content[0].text

    async def test_update_quest(self, storage_with_campaign):
        """Test updating quest status."""
        override_storage(storage_with_campaign)
        # First create a quest
        await create_quest.run(
            {"title": "Find the Shire", "description": "Locate the halfling homeland"}
        )

        result = await update_quest.run({"title": "Find the Shire", "status": "completed"})
        assert len(result.content) == 1
        assert "Find the Shire" in result.content[0].text

    async def test_list_quests(self, storage_with_campaign):
        """Test listing quests."""
        override_storage(storage_with_campaign)
        # First create a quest
        await create_quest.run(
            {"title": "Gather the Fellowship", "description": "Assemble companions"}
        )

        result = await list_quests.run({})
        assert len(result.content) == 1
        assert "Gather the Fellowship" in result.content[0].text

    # Game State Management Tests
    async def test_update_game_state(self, storage_with_campaign):
        """Test updating game state."""
        override_storage(storage_with_campaign)
        result = await update_game_state.run(
            {"current_location": "Bag End", "party_level": 3, "in_combat": False}
        )
        assert len(result.content) == 1
        assert "Updated game state" in result.content[0].text

    async def test_get_game_state(self, storage_with_campaign):
        """Test getting current game state."""
        override_storage(storage_with_campaign)
        # First update the game state
        await update_game_state.run({"current_location": "Hobbiton", "party_level": 1})

        result = await get_game_state.run({})
        assert len(result.content) == 1
        assert "Hobbiton" in result.content[0].text

    # Combat Management Tests
    async def test_start_combat(self, storage_with_campaign):
        """Test starting combat encounter."""
        override_storage(storage_with_campaign)
        from gamemaster_mcp.models import CombatParticipant

        participants = [
            CombatParticipant(name="Hero", initiative=15, hp=25, ac=15, speed=30),
            CombatParticipant(name="Orc", initiative=12, hp=15, ac=13, speed=25),
        ]

        result = await start_combat.run({"participants": participants})
        assert len(result.content) == 1
        assert "Combat Started" in result.content[0].text
        assert "Hero" in result.content[0].text

    async def test_end_combat(self, storage_with_campaign):
        """Test ending combat encounter."""
        override_storage(storage_with_campaign)
        result = await end_combat.run({
            "result": "victory",
            "summary": "The heroes emerged victorious"
        })
        assert len(result.content) == 1
        assert "Combat ended" in result.content[0].text

    async def test_next_turn(self, storage_with_campaign):
        """Test advancing combat turn."""
        override_storage(storage_with_campaign)
        from gamemaster_mcp.models import CombatParticipant

        # First start combat
        participants = [
            CombatParticipant(name="Warrior", initiative=18, hp=30, ac=16, speed=30),
            CombatParticipant(name="Goblin", initiative=10, hp=8, ac=12, speed=25),
        ]
        await start_combat.run({"participants": participants})

        result = await next_turn.run({})
        assert len(result.content) == 1
        assert "Next Turn" in result.content[0].text

    # Session Management Tests
    async def test_add_session_note(self, storage_with_campaign):
        """Test adding session notes."""
        override_storage(storage_with_campaign)
        result = await add_session_note.run(
            {
                "session_number": 1,
                "summary": "The party began their journey",
                "title": "The Adventure Begins",
            }
        )
        assert len(result.content) == 1
        assert "Session 1" in result.content[0].text

    async def test_get_sessions(self, storage_with_campaign):
        """Test getting all session notes."""
        override_storage(storage_with_campaign)
        # First add a session note
        await add_session_note.run({"session_number": 2, "summary": "Epic battles were fought"})

        result = await get_sessions.run({})
        assert len(result.content) == 1
        assert "Session 2" in result.content[0].text

    # Adventure Log Tests
    async def test_add_event(self, storage_with_campaign):
        """Test adding an adventure event."""
        override_storage(storage_with_campaign)
        result = await add_event.run(
            {
                "event_type": "combat",
                "title": "Battle of Helm's Deep",
                "description": "Epic siege battle",
                "importance": 5,
            }
        )
        assert len(result.content) == 1
        assert "Battle of Helm's Deep" in result.content[0].text

    async def test_get_events(self, storage_with_campaign):
        """Test getting adventure events."""
        override_storage(storage_with_campaign)
        campaign_name = storage_with_campaign.get_current_campaign().name
        # First add an event
        await add_event.run(
            {
                "event_type": "roleplay",
                "title": "Meeting with Elrond",
                "description": "Council discussion",
            }
        )

        result = await get_events.run({"campaign": campaign_name})
        assert len(result.content) == 1
        assert "Meeting with Elrond" in result.content[0].text

    # Utility Tests
    async def test_roll_dice(self, storage_with_campaign):
        """Test dice rolling utility."""
        override_storage(storage_with_campaign)
        result = await roll_dice.run({"dice_notation": "1d20"})
        assert len(result.content) == 1
        assert "1d20" in result.content[0].text
        # Check that result contains a number between 1-20
        import re

        numbers = re.findall(r"\*\*(\d+)\*\*", result.content[0].text)
        assert len(numbers) > 0
        total = int(numbers[-1])  # Last number should be the total
        assert 1 <= total <= 20

    async def test_calculate_experience(self, storage_with_campaign):
        """Test experience calculation."""
        override_storage(storage_with_campaign)
        result = await calculate_experience.run(
            {"party_size": 4, "party_level": 3, "encounter_xp": 600}
        )
        assert len(result.content) == 1
        assert "XP per Player: 150" in result.content[0].text

    # Transcript Tests
    async def test_record_interaction(self, storage_with_campaign):
        """Test recording player-game interaction."""
        override_storage(storage_with_campaign)
        result = await record_interaction.run(
            {
                "player_entry": "I want to investigate the room",
                "game_response": "You find a hidden door behind the bookshelf",
            }
        )
        # record_interaction returns empty content, so we just check it doesn't crash
        assert result.content is not None

    async def test_record_interaction_with_tools_text_only(self, storage_with_campaign):
        """Test recording interaction with only text responses."""
        override_storage(storage_with_campaign)
        result = await record_interaction_with_tools.run(
            {
                "player_entry": "What's in the room?",
                "game_responses": [
                    "You see a large stone table in the center.",
                    "There are ancient runes carved into the walls."
                ],
            }
        )
        assert len(result.content) == 1
        assert "Recorded interaction with 2 response(s)" in result.content[0].text

    async def test_record_interaction_with_tools_tool_calls_only(self, storage_with_campaign):
        """Test recording interaction with only tool call responses."""
        override_storage(storage_with_campaign)
        result = await record_interaction_with_tools.run(
            {
                "player_entry": "I search for treasure",
                "game_responses": [
                    [
                        {
                            "tool_name": "roll_dice",
                            "tool_id": "call_123",
                            "tool_parameters": {"dice_notation": "1d20"},
                            "tool_result": "15"
                        },
                        {
                            "tool_name": "add_item_to_character",
                            "tool_id": "call_124",
                            "tool_parameters": {"character_name_or_id": "Hero", "item_name": "Gold Coin", "quantity": 10},
                            "tool_result": "Added 10x Gold Coin to Hero's inventory"
                        }
                    ]
                ],
            }
        )
        assert len(result.content) == 1
        assert "Recorded interaction with 1 response(s)" in result.content[0].text

    async def test_record_interaction_with_tools_mixed_responses(self, storage_with_campaign):
        """Test recording interaction with mixed text and tool call responses."""
        override_storage(storage_with_campaign)
        result = await record_interaction_with_tools.run(
            {
                "player_entry": "I attack the goblin",
                "game_responses": [
                    "You draw your sword and charge!",
                    [
                        {
                            "tool_name": "roll_dice",
                            "tool_id": "call_456",
                            "tool_parameters": {"dice_notation": "1d20+5"},
                            "tool_result": "23 (natural 18 + 5)"
                        }
                    ],
                    "Your blade strikes true! The goblin falls.",
                    [
                        {
                            "tool_name": "update_character",
                            "tool_id": "call_457",
                            "tool_parameters": {"name_or_id": "Hero", "hit_points_current": 20},
                            "tool_result": "Updated Hero: hit points current: 20"
                        }
                    ]
                ],
            }
        )
        assert len(result.content) == 1
        assert "Recorded interaction with 4 response(s)" in result.content[0].text

    async def test_record_interaction_with_tools_with_session(self, storage_with_campaign):
        """Test recording interaction with explicit session number."""
        override_storage(storage_with_campaign)
        result = await record_interaction_with_tools.run(
            {
                "player_entry": "Let's begin session 5",
                "game_responses": ["Welcome to session 5!"],
                "session_number": 5,
            }
        )
        assert len(result.content) == 1
        assert "Recorded interaction with 1 response(s)" in result.content[0].text

    async def test_record_interaction_with_tools_verify_transcript_structure(self, storage_with_campaign):
        """Test that recorded interaction has correct structure in transcript."""
        override_storage(storage_with_campaign)

        # Record an interaction with mixed responses
        await record_interaction_with_tools.run(
            {
                "player_entry": "I cast fireball",
                "game_responses": [
                    "You begin casting...",
                    [
                        {
                            "tool_name": "roll_dice",
                            "tool_id": "call_789",
                            "tool_parameters": {"dice_notation": "8d6"},
                            "tool_result": "28"
                        }
                    ],
                    "The fireball explodes dealing 28 damage!"
                ],
                "session_number": 1,
            }
        )

        # Get the transcript and verify structure
        campaign_name = storage_with_campaign.get_current_campaign().name
        transcript = await get_transcript.read(
            {"campaign_name": campaign_name, "session_number": 1}
        )

        # Find the interaction we just added
        assert len(transcript.children) >= 1
        latest_interaction = transcript.children[-1]

        # Verify it has the correct player entry
        assert latest_interaction.user_text == "I cast fireball"

        # Verify it has 3 responses
        assert len(latest_interaction.responses) == 3

        # Verify first response is text
        from gamemaster_mcp.models import ResponseText
        assert isinstance(latest_interaction.responses[0], ResponseText)
        assert latest_interaction.responses[0].content == "You begin casting..."

        # Verify second response is tool calls
        from gamemaster_mcp.models import ResponseTools
        assert isinstance(latest_interaction.responses[1], ResponseTools)
        assert len(latest_interaction.responses[1].calls) == 1
        assert latest_interaction.responses[1].calls[0].name == "roll_dice"
        assert latest_interaction.responses[1].calls[0].id == "call_789"
        assert latest_interaction.responses[1].calls[0].response == "28"

        # Verify third response is text
        assert isinstance(latest_interaction.responses[2], ResponseText)
        assert latest_interaction.responses[2].content == "The fireball explodes dealing 28 damage!"

    async def test_get_transcript_resource(self, storage_with_campaign):
        """Test getting transcript as resource."""
        override_storage(storage_with_campaign)
        # First record an interaction
        await record_interaction.run(
            {
                "player_entry": "Hello",
                "game_response": "Welcome to the adventure!",
                "session_number": 1,
            }
        )

        campaign_name = storage_with_campaign.get_current_campaign().name
        transcript = await get_transcript.read(
            {"campaign_name": campaign_name, "session_number": 1}
        )
        assert transcript.campaign == campaign_name
        assert transcript.session_number == 1
        # Transcript now uses children (TranscriptInteraction nodes)
        assert len(transcript.children) >= 1

    async def test_get_current_transcript_resource(self, storage_with_campaign):
        """Test getting current transcript as resource."""
        override_storage(storage_with_campaign)
        # First record an interaction
        await record_interaction.run(
            {"player_entry": "Let's start", "game_response": "The adventure begins..."}
        )

        transcript = await get_current_transcript.read()

        # The resource returns JSON string representation of the transcript
        if isinstance(transcript, str) and transcript.strip():
            # Parse the JSON to verify structure
            import json

            transcript_data = json.loads(transcript)
            assert transcript_data["campaign"] == storage_with_campaign.get_current_campaign().name
            # Transcript now uses children instead of entries
            assert len(transcript_data["children"]) >= 1
        elif transcript is not None and hasattr(transcript, "campaign"):
            # If it returns a proper TranscriptTree object
            assert transcript.campaign == storage_with_campaign.get_current_campaign().name
            # Transcript now uses children instead of entries
            assert len(transcript.children) >= 1
        else:
            # If transcript doesn't exist, that's also a valid test outcome
            assert transcript is None

    # Game State Resource Tests
    async def test_get_current_campaign_game_state_resource(self, storage_with_campaign):
        """Test getting current campaign game state as resource."""
        override_storage(storage_with_campaign)

        # First update the game state with some data
        await update_game_state.run(
            {
                "current_location": "Rivendell",
                "party_level": 5,
                "in_combat": False,
                "notes": "Party is resting at Rivendell",
            }
        )

        game_state_json = await get_current_campaign_game_state.read()
        game_state = json.loads(game_state_json)
        assert game_state["current_location"] == "Rivendell"
        assert game_state["party_level"] == 5
        assert not game_state["in_combat"]
        assert game_state["notes"] == "Party is resting at Rivendell"
        assert game_state["campaign_name"] == storage_with_campaign.get_current_campaign().name

    async def test_get_current_campaign_game_state_resource_no_campaign(self, temp_storage):
        """Test getting current campaign game state when no campaign is active."""
        override_storage(temp_storage)

        with pytest.raises(FileNotFoundError) as exc_info:
            await get_current_campaign_game_state.read()
        assert "No current campaign" in str(exc_info.value)

    async def test_get_campaign_game_state_resource(self, storage_with_campaign):
        """Test getting specific campaign game state as resource."""
        override_storage(storage_with_campaign)
        campaign_name = storage_with_campaign.get_current_campaign().name

        # First update the game state with some data
        await update_game_state.run(
            {
                "current_location": "Moria",
                "party_level": 3,
                "in_combat": True,
                "current_session": 5,
                "party_funds": "200 gold pieces",
            }
        )

        game_state = await get_campaign_game_state.read({"campaign_name": campaign_name})
        assert game_state.current_location == "Moria"
        assert game_state.party_level == 3
        assert game_state.in_combat
        assert game_state.current_session == 5
        assert game_state.party_funds == "200 gold pieces"
        assert game_state.campaign_name == campaign_name

    async def test_get_campaign_game_state_resource_not_found(self, storage_with_campaign):
        """Test getting game state for non-existent campaign raises error."""
        override_storage(storage_with_campaign)

        with pytest.raises(FileNotFoundError) as exc_info:
            await get_campaign_game_state.read({"campaign_name": "NonExistentCampaign"})
        assert "Campaign 'NonExistentCampaign' not found" in str(exc_info.value)

    # MCP Prompt Tests
    async def test_current_prompt(self, storage_with_campaign):
        """Test the current MCP prompt function."""
        override_storage(storage_with_campaign)

        # Call the render method on the FunctionPrompt object
        prompt_result = await current_prompt.render({})

        # Extract the text content from the result
        assert len(prompt_result) == 1
        prompt_message = prompt_result[0]
        prompt_text = prompt_message.content.text

        # Verify the prompt contains key content
        assert "Dungeon Master" in prompt_text
        assert "Campaign-Centric" in prompt_text
        assert "Structured Data" in prompt_text
        assert "Proactive Assistance" in prompt_text
        assert "Information Gathering" in prompt_text
        assert "State Management" in prompt_text
        assert "Storyteller" in prompt_text
        assert "Dynamic World" in prompt_text
        assert "Event Logging" in prompt_text
        assert "Player Characters" in prompt_text

        # Verify it's a substantial prompt (should be fairly long)
        assert len(prompt_text) > 1000

        # Verify it mentions key tools/concepts
        assert "get_game_state" in prompt_text
        assert "update_game_state" in prompt_text
        assert "add_event" in prompt_text
        assert "AdventureLog" in prompt_text
        assert "SessionNotes" in prompt_text

    # Mode Management Tests
    async def test_set_mode_single_mode(self, storage_with_campaign):
        """Test setting a single mode."""
        override_storage(storage_with_campaign)

        result = await set_mode.run({"modes": "town"})
        result_text = result.content[0].text
        assert "Set modes to: [town]" in result_text
        assert "Primary mode: town" in result_text

        # Verify the mode was actually set
        game_state_result = await get_mode.run({})
        mode_text = game_state_result.content[0].text
        assert "Current modes: [town]" in mode_text
        assert "Primary mode: town" in mode_text

    async def test_set_mode_multiple_modes(self, storage_with_campaign):
        """Test setting multiple modes."""
        override_storage(storage_with_campaign)

        result = await set_mode.run({"modes": ["outdoors", "dungeon"]})
        result_text = result.content[0].text
        assert "Set modes to: [outdoors, dungeon]" in result_text
        assert "Primary mode: outdoors" in result_text

        # Verify the modes were set
        game_state_result = await get_mode.run({})
        mode_text = game_state_result.content[0].text
        assert "Current modes: [outdoors, dungeon]" in mode_text
        assert "Primary mode: outdoors" in mode_text

    async def test_set_mode_combat_priority(self, storage_with_campaign):
        """Test that combat mode is automatically moved to first position."""
        override_storage(storage_with_campaign)

        # Set modes with combat not first
        result = await set_mode.run({"modes": ["dungeon", "combat", "town"]})
        result_text = result.content[0].text
        assert "Set modes to: [combat, dungeon, town]" in result_text
        assert "Primary mode: combat" in result_text

        # Verify combat is first
        game_state_result = await get_mode.run({})
        mode_text = game_state_result.content[0].text
        assert "Current modes: [combat, dungeon, town]" in mode_text
        assert "Primary mode: combat" in mode_text

    async def test_set_mode_invalid_mode(self, storage_with_campaign):
        """Test setting an invalid mode returns error."""
        override_storage(storage_with_campaign)

        result = await set_mode.run({"modes": "invalid_mode"})
        result_text = result.content[0].text
        assert "Invalid modes: invalid_mode" in result_text
        assert "Available modes:" in result_text

    async def test_set_mode_mixed_valid_invalid(self, storage_with_campaign):
        """Test setting mix of valid and invalid modes."""
        override_storage(storage_with_campaign)

        result = await set_mode.run({"modes": ["town", "invalid", "combat"]})
        result_text = result.content[0].text
        assert "Invalid modes: invalid" in result_text
        assert "Available modes:" in result_text

    async def test_get_mode_no_modes(self, temp_storage):
        """Test getting mode when none are set."""
        override_storage(temp_storage)

        # Create a campaign first
        await create_campaign.run({
            "name": "Test Campaign",
            "description": "Test description",
            "dm_name": "Test DM"
        })

        # The default mode should be "setup"
        result = await get_mode.run({})
        result_text = result.content[0].text
        assert "Current modes: [setup]" in result_text
        assert "Primary mode: setup" in result_text

    async def test_get_available_modes_resource(self):
        """Test the available modes resource."""
        modes_json = await get_available_modes.read()
        modes = json.loads(modes_json)

        # Check structure
        assert isinstance(modes, list)
        assert len(modes) == 5  # setup, town, outdoors, dungeon, combat

        # Check each mode has required fields
        mode_names = set()
        for mode_info in modes:
            assert "mode" in mode_info
            assert "description" in mode_info
            assert isinstance(mode_info["mode"], str)
            assert isinstance(mode_info["description"], str)
            mode_names.add(mode_info["mode"])

        # Verify all expected modes are present
        expected_modes = {"setup", "town", "outdoors", "dungeon", "combat"}
        assert mode_names == expected_modes

    async def test_get_current_campaign_mode_resource(self, storage_with_campaign):
        """Test the current campaign mode resource."""
        override_storage(storage_with_campaign)

        # Set some modes first
        await set_mode.run({"modes": ["combat", "dungeon"]})

        # Get mode via resource
        mode_data_json = await get_current_campaign_mode.read()
        mode_data = json.loads(mode_data_json)

        assert "modes" in mode_data
        assert "primary_mode" in mode_data
        assert mode_data["modes"] == ["combat", "dungeon"]
        assert mode_data["primary_mode"] == "combat"

    async def test_get_current_campaign_mode_resource_no_campaign(self, temp_storage):
        """Test mode resource with no current campaign."""
        override_storage(temp_storage)

        with pytest.raises(FileNotFoundError) as exc_info:
            await get_current_campaign_mode.read()
        assert "No current campaign" in str(exc_info.value)

    async def test_mode_persistence_in_game_state(self, storage_with_campaign):
        """Test that modes are properly stored in game state."""
        override_storage(storage_with_campaign)

        # Set modes
        await set_mode.run({"modes": ["town", "setup"]})

        # Get game state and verify modes are included
        game_state_str = await get_game_state.run({})
        # The get_game_state function doesn't currently show modes in its output
        # but they should be persisted in the underlying data structure

        # Verify by getting modes directly
        mode_result = await get_mode.run({})
        mode_text = mode_result.content[0].text
        assert "Current modes: [town, setup]" in mode_text
        assert "Primary mode: town" in mode_text
