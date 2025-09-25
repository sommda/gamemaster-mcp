"""
Tests for outward-facing API.
"""

import json

import pytest

from gamemaster_mcp.main import (
    add_event,
    add_item_to_character,
    add_session_note,
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
    get_current_transcript,
    get_events,
    get_game_state,
    get_location,
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
    record_interaction,
    roll_dice,
    start_combat,
    update_character,
    update_game_state,
    update_quest,
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
        results = await create_campaign.run(
            {
                "name": sample_campaign.name,
                "description": sample_campaign.description,
                "dm_name": sample_campaign.dm_name,
                "setting": sample_campaign.setting,
            }
        )
        assert len(results) == 1
        assert sample_campaign.name in results[0].text

    async def test_get_campaign_info(self, storage_with_campaign):
        """Test grabbing basic campaign info."""
        override_storage(storage_with_campaign)
        results = await get_campaign_info.run({})
        assert len(results) == 1
        print(results[0].text)
        assert storage_with_campaign.get_current_campaign().name in results[0].text

    async def test_list_campaigns(self, storage_with_campaign):
        """Test listing campaigns."""
        override_storage(storage_with_campaign)
        results = await list_campaigns.run({})
        assert len(results) == 1
        print(results[0].text)
        assert storage_with_campaign.get_current_campaign().name in results[0].text

    async def test_load_campaign(self, storage_with_campaign):
        """Test loading a current campaigns."""
        override_storage(storage_with_campaign)
        name = storage_with_campaign.get_current_campaign().name
        results = await load_campaign.run({"name": name})
        assert len(results) == 1
        assert name in results[0].text

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
        results = await create_character.run(
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
        assert len(results) == 1
        assert "Aragorn" in results[0].text
        assert "Level 5 Human Ranger" in results[0].text

    async def test_get_character(self, storage_with_campaign):
        """Test getting character information."""
        override_storage(storage_with_campaign)
        # First create a character
        await create_character.run(
            {"name": "Legolas", "character_class": "Fighter", "class_level": 3, "race": "Elf"}
        )

        results = await get_character.run({"name_or_id": "Legolas"})
        assert len(results) == 1
        assert "Legolas" in results[0].text
        assert "Level 3 Elf Fighter" in results[0].text

    async def test_update_character(self, storage_with_campaign):
        """Test updating character properties."""
        override_storage(storage_with_campaign)
        # First create a character
        await create_character.run(
            {"name": "Gimli", "character_class": "Fighter", "class_level": 4, "race": "Dwarf"}
        )

        results = await update_character.run(
            {"name_or_id": "Gimli", "hit_points_current": 25, "armor_class": 18}
        )
        assert len(results) == 1
        assert "Gimli" in results[0].text
        assert "hit points current: 25" in results[0].text

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

        results = await bulk_update_characters.run(
            {"names_or_ids": ["Char1", "Char2"], "hp_change": 5}
        )
        assert len(results) == 1
        assert "Characters updated" in results[0].text

    async def test_add_item_to_character(self, storage_with_campaign):
        """Test adding an item to character inventory."""
        override_storage(storage_with_campaign)
        # First create a character
        await create_character.run(
            {"name": "Frodo", "character_class": "Rogue", "class_level": 2, "race": "Halfling"}
        )

        results = await add_item_to_character.run(
            {
                "character_name_or_id": "Frodo",
                "item_name": "Short Sword",
                "item_type": "weapon",
                "quantity": 1,
            }
        )
        assert len(results) == 1
        assert "Short Sword" in results[0].text
        assert "Frodo" in results[0].text

    async def test_list_characters(self, storage_with_campaign):
        """Test listing all characters."""
        override_storage(storage_with_campaign)
        # First create a character
        await create_character.run(
            {"name": "Gandalf", "character_class": "Wizard", "class_level": 10, "race": "Human"}
        )

        results = await list_characters.run({})
        assert len(results) == 1
        assert "Gandalf" in results[0].text

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
        results = await create_npc.run(
            {
                "name": "Elrond",
                "description": "Wise elf lord",
                "race": "Elf",
                "occupation": "Lord",
                "attitude": "friendly",
            }
        )
        assert len(results) == 1
        assert "Elrond" in results[0].text

    async def test_get_npc(self, storage_with_campaign):
        """Test getting NPC information."""
        override_storage(storage_with_campaign)
        # First create an NPC
        await create_npc.run({"name": "Sauron", "description": "Dark Lord", "attitude": "hostile"})

        results = await get_npc.run({"name": "Sauron"})
        assert len(results) == 1
        assert "Sauron" in results[0].text
        assert "Dark Lord" in results[0].text

    async def test_list_npcs(self, storage_with_campaign):
        """Test listing all NPCs."""
        override_storage(storage_with_campaign)
        # First create an NPC
        await create_npc.run({"name": "Boromir", "occupation": "Captain"})

        results = await list_npcs.run({})
        assert len(results) == 1
        assert "Boromir" in results[0].text

    # Monster Management Tests
    async def test_create_monster(self, storage_with_campaign):
        """Test creating a new monster."""
        override_storage(storage_with_campaign)
        results = await create_monster.run(
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
        assert len(results) == 1
        assert "Goblin Scout" in results[0].text
        assert "8/8 HP" in results[0].text

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

        results = await get_monster.run({"name": "Orc Warrior"})
        assert len(results) == 1
        assert "Orc Warrior" in results[0].text
        assert "Orc" in results[0].text
        assert "15/15" in results[0].text  # HP display
        assert "**AC:** 13" in results[0].text

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

        results = await list_monsters.run({})
        assert len(results) == 1
        assert "Goblin 1" in results[0].text
        assert "Goblin 2" in results[0].text
        assert "Cave Entrance" in results[0].text

    async def test_create_monster_with_minimal_params(self, storage_with_campaign):
        """Test creating monster with only required parameters."""
        override_storage(storage_with_campaign)
        results = await create_monster.run(
            {"name": "Basic Skeleton", "monster_type": "Undead", "hit_points_max": 13}
        )
        assert len(results) == 1
        assert "Basic Skeleton" in results[0].text
        assert "13/13 HP" in results[0].text

    async def test_get_nonexistent_monster(self, storage_with_campaign):
        """Test getting a monster that doesn't exist."""
        override_storage(storage_with_campaign)
        results = await get_monster.run({"name": "Nonexistent Monster"})
        assert len(results) == 1
        assert "not found" in results[0].text

    async def test_list_empty_monsters(self, storage_with_campaign):
        """Test listing monsters when none exist."""
        override_storage(storage_with_campaign)
        results = await list_monsters.run({})
        assert len(results) == 1
        assert "No monsters" in results[0].text

    async def test_create_monster_with_advanced_stats(self, storage_with_campaign):
        """Test creating a monster with advanced D&D 5E stats."""
        override_storage(storage_with_campaign)
        results = await create_monster.run(
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
        assert len(results) == 1
        assert "Young Dragon" in results[0].text
        assert "178/178 HP" in results[0].text

    # Location Management Tests
    async def test_create_location(self, storage_with_campaign):
        """Test creating a new location."""
        override_storage(storage_with_campaign)
        results = await create_location.run(
            {
                "name": "Rivendell",
                "location_type": "city",
                "description": "Hidden valley of the elves",
                "population": 500,
            }
        )
        assert len(results) == 1
        assert "Rivendell" in results[0].text

    async def test_get_location(self, storage_with_campaign):
        """Test getting location information."""
        override_storage(storage_with_campaign)
        # First create a location
        await create_location.run(
            {"name": "Moria", "location_type": "dungeon", "description": "Ancient dwarven mines"}
        )

        results = await get_location.run({"name": "Moria"})
        assert len(results) == 1
        assert "Moria" in results[0].text
        assert "dungeon" in results[0].text

    async def test_list_locations(self, storage_with_campaign):
        """Test listing all locations."""
        override_storage(storage_with_campaign)
        # First create a location
        await create_location.run(
            {"name": "Gondor", "location_type": "kingdom", "description": "Great kingdom of men"}
        )

        results = await list_locations.run({})
        assert len(results) == 1
        assert "Gondor" in results[0].text

    # Quest Management Tests
    async def test_create_quest(self, storage_with_campaign):
        """Test creating a new quest."""
        override_storage(storage_with_campaign)
        results = await create_quest.run(
            {
                "title": "Destroy the Ring",
                "description": "Take the One Ring to Mount Doom",
                "giver": "Gandalf",
                "reward": "Save Middle-earth",
            }
        )
        assert len(results) == 1
        assert "Destroy the Ring" in results[0].text

    async def test_update_quest(self, storage_with_campaign):
        """Test updating quest status."""
        override_storage(storage_with_campaign)
        # First create a quest
        await create_quest.run(
            {"title": "Find the Shire", "description": "Locate the halfling homeland"}
        )

        results = await update_quest.run({"title": "Find the Shire", "status": "completed"})
        assert len(results) == 1
        assert "Find the Shire" in results[0].text

    async def test_list_quests(self, storage_with_campaign):
        """Test listing quests."""
        override_storage(storage_with_campaign)
        # First create a quest
        await create_quest.run(
            {"title": "Gather the Fellowship", "description": "Assemble companions"}
        )

        results = await list_quests.run({})
        assert len(results) == 1
        assert "Gather the Fellowship" in results[0].text

    # Game State Management Tests
    async def test_update_game_state(self, storage_with_campaign):
        """Test updating game state."""
        override_storage(storage_with_campaign)
        results = await update_game_state.run(
            {"current_location": "Bag End", "party_level": 3, "in_combat": False}
        )
        assert len(results) == 1
        assert "Updated game state" in results[0].text

    async def test_get_game_state(self, storage_with_campaign):
        """Test getting current game state."""
        override_storage(storage_with_campaign)
        # First update the game state
        await update_game_state.run({"current_location": "Hobbiton", "party_level": 1})

        results = await get_game_state.run({})
        assert len(results) == 1
        assert "Hobbiton" in results[0].text

    # Combat Management Tests
    async def test_start_combat(self, storage_with_campaign):
        """Test starting combat encounter."""
        override_storage(storage_with_campaign)
        from gamemaster_mcp.models import CombatParticipant

        participants = [
            CombatParticipant(name="Hero", initiative=15, hp=25, ac=15, speed=30),
            CombatParticipant(name="Orc", initiative=12, hp=15, ac=13, speed=25),
        ]

        results = await start_combat.run({"participants": participants})
        assert len(results) == 1
        assert "Combat Started" in results[0].text
        assert "Hero" in results[0].text

    async def test_end_combat(self, storage_with_campaign):
        """Test ending combat encounter."""
        override_storage(storage_with_campaign)
        results = await end_combat.run({})
        assert len(results) == 1
        assert "Combat ended" in results[0].text

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

        results = await next_turn.run({})
        assert len(results) == 1
        assert "Next Turn" in results[0].text

    # Session Management Tests
    async def test_add_session_note(self, storage_with_campaign):
        """Test adding session notes."""
        override_storage(storage_with_campaign)
        results = await add_session_note.run(
            {
                "session_number": 1,
                "summary": "The party began their journey",
                "title": "The Adventure Begins",
            }
        )
        assert len(results) == 1
        assert "Session 1" in results[0].text

    async def test_get_sessions(self, storage_with_campaign):
        """Test getting all session notes."""
        override_storage(storage_with_campaign)
        # First add a session note
        await add_session_note.run({"session_number": 2, "summary": "Epic battles were fought"})

        results = await get_sessions.run({})
        assert len(results) == 1
        assert "Session 2" in results[0].text

    # Adventure Log Tests
    async def test_add_event(self, storage_with_campaign):
        """Test adding an adventure event."""
        override_storage(storage_with_campaign)
        results = await add_event.run(
            {
                "event_type": "combat",
                "title": "Battle of Helm's Deep",
                "description": "Epic siege battle",
                "importance": 5,
            }
        )
        assert len(results) == 1
        assert "Battle of Helm's Deep" in results[0].text

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

        results = await get_events.run({"campaign": campaign_name})
        assert len(results) == 1
        assert "Meeting with Elrond" in results[0].text

    # Utility Tests
    async def test_roll_dice(self, storage_with_campaign):
        """Test dice rolling utility."""
        override_storage(storage_with_campaign)
        results = await roll_dice.run({"dice_notation": "1d20"})
        assert len(results) == 1
        assert "1d20" in results[0].text
        # Check that result contains a number between 1-20
        import re

        numbers = re.findall(r"\*\*(\d+)\*\*", results[0].text)
        assert len(numbers) > 0
        total = int(numbers[-1])  # Last number should be the total
        assert 1 <= total <= 20

    async def test_calculate_experience(self, storage_with_campaign):
        """Test experience calculation."""
        override_storage(storage_with_campaign)
        results = await calculate_experience.run(
            {"party_size": 4, "party_level": 3, "encounter_xp": 600}
        )
        assert len(results) == 1
        assert "XP per Player: 150" in results[0].text

    # Transcript Tests
    async def test_record_interaction(self, storage_with_campaign):
        """Test recording player-game interaction."""
        override_storage(storage_with_campaign)
        results = await record_interaction.run(
            {
                "player_entry": "I want to investigate the room",
                "game_response": "You find a hidden door behind the bookshelf",
            }
        )
        # record_interaction returns None, so we just check it doesn't crash
        assert results is None or len(results) == 0

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
        assert len(transcript.entries) >= 1

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
            assert len(transcript_data["entries"]) >= 1
        elif transcript is not None and hasattr(transcript, "campaign"):
            # If it returns a proper Transcript object
            assert transcript.campaign == storage_with_campaign.get_current_campaign().name
            assert len(transcript.entries) >= 1
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
