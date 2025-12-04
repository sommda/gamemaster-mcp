"""
D&D MCP Server
A comprehensive D&D campaign management server built with modern FastMCP framework.
"""

import argparse
import logging
import os
import random
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.prompts.prompt import Message
from pydantic import Field

from .models import (
    AVAILABLE_MODES,
    MODE_PROMPTS,
    NPC,
    AbilityScore,
    AdventureEvent,
    Campaign,
    Character,
    CharacterClass,
    CombatParticipant,
    EventType,
    Hex,
    HexCoordinate,
    HexMap,
    HexSide,
    Item,
    Location,
    LocationScale,
    LocationType,
    Monster,
    PointOfInterest,
    POIType,
    Quest,
    Race,
    River,
    Road,
    SessionNote,
    Spell,
    TerrainType,
    Transcript,
    TranscriptAdventure,
    TranscriptCombat,
    TranscriptInteraction,
)
from .prompts import core_prompt, setup_prompt
from .storage import DnDStorage
from .tool_with_logging import tool_with_logging

logger = logging.getLogger("gamemaster-mcp")

# Set root logger to WARNING to suppress most library logs
logging.basicConfig(
    level=logging.WARNING,
)

# Keep gamemaster-mcp logs at INFO level
logger.setLevel(logging.INFO)

# Explicitly suppress verbose libraries
logging.getLogger("mcp").setLevel(logging.ERROR)
logging.getLogger("fastmcp").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("uvicorn").setLevel(logging.ERROR)
logging.getLogger("starlette").setLevel(logging.ERROR)
logging.getLogger("sse_starlette").setLevel(logging.ERROR)

if not load_dotenv():
    logger.warning(
        "❌ .env file invalid or not found! Please see README.md for instructions. Using project root instead."
    )

data_path = Path(os.getenv("GAMEMASTER_STORAGE_DIR", "")).resolve()
logger.debug(f"📂 Data path: {data_path}")


# Initialize storage and FastMCP server
storage = DnDStorage(data_dir=data_path)
logger.debug("✅ Storage layer initialized")

mcp: FastMCP = FastMCP(name="D&D Campaign Manager")
logger.debug("✅ Server initialized, registering tools")


# Storage override for tests
def override_storage(ovr_storage: DnDStorage) -> None:
    global storage
    storage = ovr_storage


# ----------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------


# Helper Functions
def _strip_tools_from_nodes(
    nodes: list[TranscriptInteraction | TranscriptCombat | TranscriptAdventure]
) -> list[dict[str, Any]]:
    """Convert transcript nodes to JSON dict, keeping only text responses."""
    result = []

    for node in nodes:
        if isinstance(node, TranscriptInteraction):
            # Extract only text responses
            text_responses = []
            for resp in node.responses:
                if resp.type == "text":
                    text_responses.append(resp.content)

            result.append({
                "type": "interaction",
                "user_text": node.user_text,
                "responses": text_responses
            })

    return result


# Campaign management tools
@tool_with_logging(mcp, tags=["mode:setup"])
def create_campaign(
    name: Annotated[str, Field(description="Campaign name")],
    description: Annotated[
        str, Field(description="Brief decription of the campaign, or a tagline")
    ],
    dm_name: Annotated[str | None, Field(description="Dungeon Master name")] = None,
    setting: Annotated[
        str | Path | None,
        Field(
            description="""
        Campaign setting - a full description of the setting of the campaign in markdown format, or the path to a `.txt` or `.md` file containing the same.
        """
        ),
    ] = None,
) -> str:
    """Create a new D&D campaign."""
    campaign = storage.create_campaign(
        name=name, description=description, dm_name=dm_name, setting=setting
    )
    return f"🌟 Created campaign: '{campaign.name} and set as active 🌟'"


@tool_with_logging(mcp, tags=["mode:any"])
def get_campaign_info() -> str:
    """Get information about the current campaign."""
    campaign = storage.get_current_campaign()
    if not campaign:
        return "No active campaign."

    info = {
        "name": campaign.name,
        "description": campaign.description,
        "dm_name": campaign.dm_name,
        "setting": campaign.get_setting(),
        "character_count": len(campaign.characters),
        "npc_count": len(campaign.npcs),
        "location_count": len(campaign.locations),
        "quest_count": len(campaign.quests),
        "session_count": len(campaign.sessions),
        "current_session": campaign.game_state.current_session,
        "current_location": campaign.game_state.current_location,
        "party_level": campaign.game_state.party_level,
        "in_combat": campaign.game_state.in_combat,
    }

    return f"**Campaign: {campaign.name}**\n\n" + "\n".join(
        [f"**{k.replace('_', ' ').title()}:** {v}" for k, v in info.items()]
    )


@tool_with_logging(mcp, tags=["mode:setup"])
def list_campaigns() -> str:
    """List all available campaigns."""
    campaigns = storage.list_campaigns()
    if not campaigns:
        return f"❌ No campaigns found in {storage.data_dir}!"

    current = storage.get_current_campaign()
    current_name = current.name if current else None

    campaign_list = []
    for campaign in campaigns:
        marker = " (current)" if campaign == current_name else ""
        campaign_list.append(f"• {campaign}{marker}")

    return "**Available Campaigns:**\n" + "\n".join(campaign_list)


@tool_with_logging(mcp, tags=["mode:setup"])
def load_campaign(name: Annotated[str, Field(description="Campaign name to load")]) -> str:
    """Load a specific campaign."""
    campaign = storage.load_campaign(name)
    return f"📖 Loaded campaign: '{campaign.name}'. Campaign is now active!"


# Campaign resources
@mcp.resource("resource://campaigns/{campaign_name}")
def get_campaign(campaign_name: str) -> Campaign:
    return storage.get_campaign(campaign_name)


@mcp.resource("resource://campaigns")
def get_campaigns() -> list[str]:
    return storage.list_campaigns()


@mcp.resource("resource://current_campaign")
def get_current_campaign() -> str:
    return storage.get_current_campaign().name


# Character resources
@mcp.resource("resource://characters/{character_name}")
def get_character_resource(character_name: str) -> Character:
    character = storage.get_character(character_name)
    if not character:
        raise FileNotFoundError(f"Character '{character_name}' not found")
    return character


@mcp.resource("resource://campaigns/{campaign_name}/characters")
def get_campaign_characters(campaign_name: str) -> list[Character]:
    try:
        campaign = storage.get_campaign(campaign_name)
        return list(campaign.characters.values())
    except FileNotFoundError:
        raise FileNotFoundError(f"Campaign '{campaign_name}' not found")


@mcp.resource("resource://current_campaign/characters")
def get_current_campaign_characters() -> list[Character]:
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        return []
    return list(current_campaign.characters.values())


# Character Management Tools
@tool_with_logging(mcp, tags=["mode:setup"])
def create_character(
    name: Annotated[str, Field(description="Character name")],
    character_class: Annotated[str, Field(description="Character class")],
    class_level: Annotated[int, Field(description="Class level", ge=1, le=20)],
    race: Annotated[str, Field(description="Character race")],
    player_name: Annotated[
        str | None, Field(description="The name of the player in control of this character")
    ] = None,
    description: Annotated[
        str | None,
        Field(description="A brief description of the character's appearance and demeanor."),
    ] = None,
    bio: Annotated[
        str | None, Field(description="The character's backstory, personality, and motivations.")
    ] = None,
    background: Annotated[str | None, Field(description="Character background")] = None,
    alignment: Annotated[str | None, Field(description="Character alignment")] = None,
    strength: Annotated[int, Field(description="Strength score", ge=1, le=30)] = 10,
    dexterity: Annotated[int, Field(description="Dexterity score", ge=1, le=30)] = 10,
    constitution: Annotated[int, Field(description="Constitution score", ge=1, le=30)] = 10,
    intelligence: Annotated[int, Field(description="Intelligence score", ge=1, le=30)] = 10,
    wisdom: Annotated[int, Field(description="Wisdom score", ge=1, le=30)] = 10,
    charisma: Annotated[int, Field(description="Charisma score", ge=1, le=30)] = 10,
) -> str:
    """Create a new player character."""
    # Build ability scores
    abilities = {
        "strength": AbilityScore(score=strength),
        "dexterity": AbilityScore(score=dexterity),
        "constitution": AbilityScore(score=constitution),
        "intelligence": AbilityScore(score=intelligence),
        "wisdom": AbilityScore(score=wisdom),
        "charisma": AbilityScore(score=charisma),
    }

    character = Character(
        name=name,
        player_name=player_name,
        character_class=CharacterClass(name=character_class, level=class_level),
        race=Race(name=race),
        background=background,
        alignment=alignment,
        abilities=abilities,
        description=description,
        bio=bio,
    )

    storage.add_character(character)
    return f"Created character '{character.name}' (Level {character.character_class.level} {character.race.name} {character.character_class.name})"


@tool_with_logging(mcp, tags=["mode:any"])
def get_character(name_or_id: Annotated[str, Field(description="Character name or ID")]) -> str:
    """Get detailed character information."""
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    char_info = f"""**{character.name}** (`{character.id}`)
Level {character.character_class.level} {character.race.name} {character.character_class.name}
**Player:** {character.player_name or "N/A"}
**Background:** {character.background or "N/A"}
**Alignment:** {character.alignment or "N/A"}

**Description:** {character.description or "No description provided."}
**Bio:** {character.bio or "No bio provided."}

**Ability Scores:**
• STR: {character.abilities["strength"].score} ({character.abilities["strength"].mod:+d})
• DEX: {character.abilities["dexterity"].score} ({character.abilities["dexterity"].mod:+d})
• CON: {character.abilities["constitution"].score} ({character.abilities["constitution"].mod:+d})
• INT: {character.abilities["intelligence"].score} ({character.abilities["intelligence"].mod:+d})
• WIS: {character.abilities["wisdom"].score} ({character.abilities["wisdom"].mod:+d})
• CHA: {character.abilities["charisma"].score} ({character.abilities["charisma"].mod:+d})

**Combat Stats:**
• AC: {character.armor_class}
• HP: {character.hit_points_current}/{character.hit_points_max}
• Temp HP: {character.temporary_hit_points}
• Proficiency Bonus: +{character.proficiency_bonus}

**Saving Throws:**
"""

    # Add saving throws
    for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
        save = character.saving_throws.get(ability)
        if save:
            prof_marker = "✓" if save.proficiency.value == "proficient" else " "
            char_info += f"• [{prof_marker}] {ability.upper()[:3]}: {save.modifier:+d}\n"

    char_info += "\n**Skills:**\n"

    # Group and display skills
    proficient_skills = []
    expertise_skills = []
    other_skills = []

    for skill_name, skill in character.skills.items():
        skill_display = f"{skill_name.replace('_', ' ').title()}: {skill.modifier:+d}"
        if skill.proficiency.value == "expertise":
            expertise_skills.append(skill_display)
        elif skill.proficiency.value == "proficient":
            proficient_skills.append(skill_display)
        else:
            other_skills.append(skill_display)

    if expertise_skills:
        for skill_display in sorted(expertise_skills):
            char_info += f"• [E] {skill_display}\n"
    if proficient_skills:
        for skill_display in sorted(proficient_skills):
            char_info += f"• [✓] {skill_display}\n"
    if other_skills:
        for skill_display in sorted(other_skills):
            char_info += f"• [ ] {skill_display}\n"

    char_info += f"\n**Inventory:** {len(character.inventory)} items\n"

    # Add detailed inventory list
    if character.inventory:
        char_info += "\n"
        for item in character.inventory:
            char_info += f"• {item.name} (x{item.quantity}) - {item.item_type}\n"

    # Add spell slots section
    if character.spell_slots:
        char_info += "\n**Spell Slots:**\n"
        for level in sorted(character.spell_slots.keys()):
            max_slots = character.spell_slots[level]
            used_slots = character.spell_slots_used.get(level, 0)
            char_info += f"• Level {level}: {max_slots} ({used_slots} used)\n"

    # Add spells section
    if character.spells_known:
        char_info += f"\n**Spells Known:** {len(character.spells_known)} spells\n"
        for spell in character.spells_known:
            prepared_marker = "✓" if spell.prepared else " "
            char_info += f"• [{prepared_marker}] {spell.name} (Level {spell.level})\n"

    # Add special abilities section
    if character.special_abilities:
        char_info += f"\n**Special Abilities:** {len(character.special_abilities)} abilities\n"
        for ability in character.special_abilities:
            uses_info = ""
            if ability.uses:
                uses_info = f" ({ability.uses}"
                if ability.uses_remaining is not None:
                    uses_info += f", {ability.uses_remaining} remaining"
                uses_info += ")"
            char_info += f"• **{ability.name}**{uses_info}\n"
            char_info += f"  {ability.description}\n"

    return char_info


@tool_with_logging(mcp, tags=["mode:any"])
def update_skills(
    character_name_or_id: Annotated[str, Field(description="Name or ID of the character to update skills for.")],
    add_proficiency: Annotated[
        list[str] | None,
        Field(
            description="List of skill names to make the character proficient in. Skill names are case-insensitive. Valid skills: acrobatics, animal_handling, arcana, athletics, deception, history, insight, intimidation, investigation, medicine, nature, perception, performance, persuasion, religion, sleight_of_hand, stealth, survival."
        )
    ] = None,
    add_expertise: Annotated[
        list[str] | None,
        Field(
            description="List of skill names to give the character expertise in (double proficiency bonus). Skill names are case-insensitive. Valid skills: acrobatics, animal_handling, arcana, athletics, deception, history, insight, intimidation, investigation, medicine, nature, perception, performance, persuasion, religion, sleight_of_hand, stealth, survival."
        )
    ] = None,
    remove: Annotated[
        list[str] | None,
        Field(
            description="List of skill names to remove all proficiency from. Skill names are case-insensitive. Valid skills: acrobatics, animal_handling, arcana, athletics, deception, history, insight, intimidation, investigation, medicine, nature, perception, performance, persuasion, religion, sleight_of_hand, stealth, survival."
        )
    ] = None,
) -> str:
    """Update a character's skill proficiencies.

    This tool allows you to add proficiency, add expertise, or remove proficiency from skills.
    If a skill appears in multiple lists, the highest proficiency level wins:
    - Expertise (double proficiency) > Proficiency > Remove

    The tool will automatically calculate the correct modifier based on:
    - The skill's base ability (e.g., Stealth uses Dexterity)
    - The character's ability score modifier
    - The proficiency level (none, proficient, or expertise)

    Example usage:
    - Make a rogue proficient in Stealth and Sleight of Hand:
      add_proficiency=["stealth", "sleight_of_hand"]

    - Give a rogue expertise in Stealth:
      add_expertise=["stealth"]

    - Remove proficiency from Perception:
      remove=["perception"]
    """
    from gamemaster_mcp.models import STANDARD_SKILLS, SkillProficiency

    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found."

    # Normalize and validate skill names
    def normalize_skill_name(name: str) -> str:
        """Convert skill name to lowercase with underscores."""
        return name.lower().replace(" ", "_").replace("-", "_")

    # Collect all skill names and validate
    all_skill_names = []
    if add_proficiency:
        all_skill_names.extend(add_proficiency)
    if add_expertise:
        all_skill_names.extend(add_expertise)
    if remove:
        all_skill_names.extend(remove)

    # Validate skill names
    invalid_skills = []
    normalized_map = {}
    for skill_name in all_skill_names:
        normalized = normalize_skill_name(skill_name)
        if normalized not in STANDARD_SKILLS:
            invalid_skills.append(skill_name)
        else:
            normalized_map[skill_name] = normalized

    if invalid_skills:
        valid_skills_list = ", ".join(sorted(STANDARD_SKILLS.keys()))
        return f"❌ Invalid skill name(s): {', '.join(invalid_skills)}\n\nValid skills are: {valid_skills_list}"

    # Build skill changes with precedence: expertise > proficiency > remove
    skill_changes = {}

    # Process remove first (lowest priority)
    if remove:
        for skill_name in remove:
            normalized = normalized_map[skill_name]
            skill_changes[normalized] = ("remove", SkillProficiency.NONE)

    # Process proficiency (medium priority)
    if add_proficiency:
        for skill_name in add_proficiency:
            normalized = normalized_map[skill_name]
            skill_changes[normalized] = ("proficient", SkillProficiency.PROFICIENT)

    # Process expertise (highest priority)
    if add_expertise:
        for skill_name in add_expertise:
            normalized = normalized_map[skill_name]
            skill_changes[normalized] = ("expertise", SkillProficiency.EXPERTISE)

    # Apply changes and calculate modifiers
    changes_made = []
    for skill_name, (change_type, proficiency) in skill_changes.items():
        skill = character.skills[skill_name]
        old_proficiency = skill.proficiency.value
        skill.proficiency = proficiency

        # Calculate new modifier
        ability_name = STANDARD_SKILLS[skill_name]
        ability_mod = character.abilities[ability_name].mod

        if proficiency == SkillProficiency.EXPERTISE:
            skill.modifier = ability_mod + (character.proficiency_bonus * 2)
        elif proficiency == SkillProficiency.PROFICIENT:
            skill.modifier = ability_mod + character.proficiency_bonus
        else:  # NONE
            skill.modifier = ability_mod

        # Track changes for output
        skill_display_name = skill_name.replace("_", " ").title()
        if change_type == "expertise":
            changes_made.append(f"  • {skill_display_name}: {old_proficiency} → expertise (modifier: {skill.modifier:+d})")
        elif change_type == "proficient":
            changes_made.append(f"  • {skill_display_name}: {old_proficiency} → proficient (modifier: {skill.modifier:+d})")
        else:  # remove
            changes_made.append(f"  • {skill_display_name}: {old_proficiency} → none (modifier: {skill.modifier:+d})")

    # Save changes
    storage.update_character(character_name_or_id, skills=character.skills)

    if changes_made:
        return f"✅ Updated skills for '{character.name}':\n" + "\n".join(changes_made)
    else:
        return f"ℹ️ No skill changes made for '{character.name}'."


@tool_with_logging(mcp, tags=["mode:any"])
def update_saving_throw_proficiencies(
    character_name_or_id: Annotated[str, Field(description="Name or ID of the character to update saving throw proficiencies for.")],
    add: Annotated[
        list[str] | None,
        Field(
            description="List of ability names to make the character proficient in for saving throws. Ability names are case-insensitive. Valid abilities: strength, dexterity, constitution, intelligence, wisdom, charisma."
        )
    ] = None,
    remove: Annotated[
        list[str] | None,
        Field(
            description="List of ability names to remove saving throw proficiency from. Ability names are case-insensitive. Valid abilities: strength, dexterity, constitution, intelligence, wisdom, charisma."
        )
    ] = None,
) -> str:
    """Update a character's saving throw proficiencies.

    This tool allows you to add or remove proficiency from saving throws.
    If an ability appears in both lists, add takes precedence over remove.

    The tool will automatically calculate the correct modifier based on:
    - The character's ability score modifier
    - Whether the character is proficient in that save

    Example usage:
    - Make a fighter proficient in Strength and Constitution saves:
      add=["strength", "constitution"]

    - Make a wizard proficient in Intelligence and Wisdom saves:
      add=["intelligence", "wisdom"]

    - Remove proficiency from Dexterity saves:
      remove=["dexterity"]
    """
    from gamemaster_mcp.models import STANDARD_SAVING_THROWS, SavingThrowProficiency

    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found."

    # Normalize and validate ability names
    def normalize_ability_name(name: str) -> str:
        """Convert ability name to lowercase."""
        return name.lower().strip()

    # Collect all ability names and validate
    all_ability_names = []
    if add:
        all_ability_names.extend(add)
    if remove:
        all_ability_names.extend(remove)

    # Validate ability names
    invalid_abilities = []
    normalized_map = {}
    for ability_name in all_ability_names:
        normalized = normalize_ability_name(ability_name)
        if normalized not in STANDARD_SAVING_THROWS:
            invalid_abilities.append(ability_name)
        else:
            normalized_map[ability_name] = normalized

    if invalid_abilities:
        valid_abilities_list = ", ".join(STANDARD_SAVING_THROWS)
        return f"❌ Invalid ability name(s): {', '.join(invalid_abilities)}\n\nValid abilities are: {valid_abilities_list}"

    # Build saving throw changes with precedence: add > remove
    save_changes = {}

    # Process remove first (lower priority)
    if remove:
        for ability_name in remove:
            normalized = normalized_map[ability_name]
            save_changes[normalized] = ("remove", SavingThrowProficiency.NONE)

    # Process add (higher priority)
    if add:
        for ability_name in add:
            normalized = normalized_map[ability_name]
            save_changes[normalized] = ("add", SavingThrowProficiency.PROFICIENT)

    # Apply changes and calculate modifiers
    changes_made = []
    for ability_name, (change_type, proficiency) in save_changes.items():
        save = character.saving_throws[ability_name]
        old_proficiency = save.proficiency.value
        save.proficiency = proficiency

        # Calculate new modifier
        ability_mod = character.abilities[ability_name].mod

        if proficiency == SavingThrowProficiency.PROFICIENT:
            save.modifier = ability_mod + character.proficiency_bonus
        else:  # NONE
            save.modifier = ability_mod

        # Track changes for output
        ability_display_name = ability_name.upper()[:3]
        if change_type == "add":
            changes_made.append(f"  • {ability_display_name}: {old_proficiency} → proficient (modifier: {save.modifier:+d})")
        else:  # remove
            changes_made.append(f"  • {ability_display_name}: {old_proficiency} → none (modifier: {save.modifier:+d})")

    # Save changes
    storage.update_character(character_name_or_id, saving_throws=character.saving_throws)

    if changes_made:
        return f"✅ Updated saving throws for '{character.name}':\n" + "\n".join(changes_made)
    else:
        return f"ℹ️ No saving throw changes made for '{character.name}'."


@tool_with_logging(mcp, tags=["mode:any"])
def update_character(
    name_or_id: Annotated[str, Field(description="The name or ID of the character to update.")],
    name: Annotated[
        str,
        Field(
            description="New character name. If you change this, you must use the character's ID to identify them."
        ),
    ] | None = None,
    player_name: Annotated[str, Field(description="The name of the player in control of this character")] | None = None,
    description: Annotated[
        str,
        Field(description="A brief description of the character's appearance and demeanor."),
    ] | None = None,
    bio: Annotated[
        str, Field(description="The character's backstory, personality, and motivations.")
    ] | None = None,
    background: Annotated[str, Field(description="Character background")] | None = None,
    alignment: Annotated[str, Field(description="Character alignment")] | None = None,
    hit_points_current: int | str | None = None,
    hit_points_max: int | str | None = None,
    temporary_hit_points: int | str | None = None,
    armor_class: int | str | None = None,
    inspiration: bool | str | None = None,
    notes: Annotated[str, Field(description="Additional notes about the character")] | None = None,
    strength: int | str | None = None,
    dexterity: int | str | None = None,
    constitution: int | str | None = None,
    intelligence: int | str | None = None,
    wisdom: int | str | None = None,
    charisma: int | str | None = None,
    level: int | str | None = None,
) -> str:
    """Update a character's properties."""
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    updates = {
        k: v for k, v in locals().items() if v is not None and k not in ["name_or_id", "character"]
    }

    # Manual type conversion for int parameters (FastMCP bug workaround)
    int_fields = {
        "hit_points_current": (0, None),
        "hit_points_max": (1, None),
        "temporary_hit_points": (0, None),
        "armor_class": (0, None),
        "strength": (1, 30),
        "dexterity": (1, 30),
        "constitution": (1, 30),
        "intelligence": (1, 30),
        "wisdom": (1, 30),
        "charisma": (1, 30),
        "level": (1, 20),
    }

    for field, (min_val, max_val) in int_fields.items():
        if field in updates:
            value = updates[field]
            if isinstance(value, str):
                try:
                    value = int(value)
                    updates[field] = value
                except ValueError:
                    return f"❌ Invalid value for {field}: '{value}' is not a valid integer."

            # Validate range
            if value < min_val:
                return f"❌ Invalid value for {field}: {value} is less than minimum {min_val}."
            if max_val is not None and value > max_val:
                return f"❌ Invalid value for {field}: {value} is greater than maximum {max_val}."

    # Handle bool conversion
    if "inspiration" in updates:
        value = updates["inspiration"]
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes"):
                updates["inspiration"] = True
            elif value.lower() in ("false", "0", "no"):
                updates["inspiration"] = False
            else:
                return f"❌ Invalid value for inspiration: '{value}' is not a valid boolean."

    updated_fields = [f"{key.replace('_', ' ')}: {value}" for key, value in updates.items()]

    if not updates:
        return f"No updates provided for {character.name}."

    storage.update_character(str(character.id), **updates)

    return f"Updated {character.name}'s properties: {'; '.join(updated_fields)}."


@tool_with_logging(mcp, tags=["mode:any"])
def damage_character(
    name_or_id: Annotated[str, Field(description="The name or ID of the character taking damage.")],
    damage: Annotated[int, Field(description="Amount of damage taken", ge=0)],
) -> str:
    """Apply damage to a character, reducing their current hit points.

    This is a convenience tool that automatically calculates the new HP value.
    Use this instead of update_character when a character takes damage.

    The character's HP will be reduced by the damage amount, but cannot go below 0.
    Temporary hit points are automatically applied first if present.
    """
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    if damage == 0:
        return f"{character.name} takes no damage."

    # Apply temporary HP first
    damage_remaining = damage
    temp_hp_lost = 0
    if character.temporary_hit_points > 0:
        temp_hp_lost = min(character.temporary_hit_points, damage_remaining)
        damage_remaining -= temp_hp_lost
        new_temp_hp = character.temporary_hit_points - temp_hp_lost
    else:
        new_temp_hp = 0

    # Apply remaining damage to actual HP
    old_hp = character.hit_points_current
    new_hp = max(0, old_hp - damage_remaining)
    actual_damage = old_hp - new_hp

    # Update character
    storage.update_character(
        str(character.id),
        hit_points_current=new_hp,
        temporary_hit_points=new_temp_hp
    )

    # Build response message
    msg_parts = []
    if temp_hp_lost > 0:
        msg_parts.append(f"{temp_hp_lost} absorbed by temporary HP")
    if actual_damage > 0:
        msg_parts.append(f"{actual_damage} HP damage")

    damage_desc = " + ".join(msg_parts) if msg_parts else "no damage"

    if new_hp == 0:
        return f"💀 {character.name} takes {damage} damage ({damage_desc}) and drops to 0 HP!"
    else:
        return f"⚔️ {character.name} takes {damage} damage ({damage_desc}). HP: {new_hp}/{character.hit_points_max}"


@tool_with_logging(mcp, tags=["mode:any"])
def heal_character(
    name_or_id: Annotated[str, Field(description="The name or ID of the character being healed.")],
    healing: Annotated[int, Field(description="Amount of hit points restored", ge=0)],
) -> str:
    """Restore hit points to a character.

    This is a convenience tool that automatically calculates the new HP value.
    Use this instead of update_character when a character is healed.

    The character's HP will be increased by the healing amount, but cannot exceed their maximum HP.
    """
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    if healing == 0:
        return f"{character.name} receives no healing."

    old_hp = character.hit_points_current
    new_hp = min(character.hit_points_max, old_hp + healing)
    actual_healing = new_hp - old_hp

    if actual_healing == 0:
        return f"{character.name} is already at full health ({character.hit_points_max} HP)."

    # Update character
    storage.update_character(str(character.id), hit_points_current=new_hp)

    if new_hp == character.hit_points_max:
        return f"✨ {character.name} is healed for {actual_healing} HP and restored to full health! HP: {new_hp}/{character.hit_points_max}"
    else:
        return f"✨ {character.name} is healed for {actual_healing} HP. HP: {new_hp}/{character.hit_points_max}"


@tool_with_logging(mcp, tags=["mode:setup"])
def bulk_update_characters(
    names_or_ids: Annotated[
        list[str], Field(description="List of character names or IDs to update.")
    ],
    hp_change: Annotated[
        int | None, Field(description="Amount to change current HP by (positive or negative).")
    ] = None,
    temp_hp_change: Annotated[
        int | None, Field(description="Amount to change temporary HP by (positive or negative).")
    ] = None,
    strength_change: Annotated[
        int | None, Field(description="Amount to change strength by.")
    ] = None,
    dexterity_change: Annotated[
        int | None, Field(description="Amount to change dexterity by.")
    ] = None,
    constitution_change: Annotated[
        int | None, Field(description="Amount to change constitution by.")
    ] = None,
    intelligence_change: Annotated[
        int | None, Field(description="Amount to change intelligence by.")
    ] = None,
    wisdom_change: Annotated[int | None, Field(description="Amount to change wisdom by.")] = None,
    charisma_change: Annotated[
        int | None, Field(description="Amount to change charisma by.")
    ] = None,
) -> str:
    """Update properties for multiple characters at once by a given amount."""
    updates_log = []
    not_found_log = []

    changes = {
        "hp_change": hp_change,
        "temp_hp_change": temp_hp_change,
        "strength_change": strength_change,
        "dexterity_change": dexterity_change,
        "constitution_change": constitution_change,
        "intelligence_change": intelligence_change,
        "wisdom_change": wisdom_change,
        "charisma_change": charisma_change,
    }

    # Filter out None changes
    active_changes = {k: v for k, v in changes.items() if v is not None}
    if not active_changes:
        return "No changes specified."

    for name_or_id in names_or_ids:
        character = storage.get_character(name_or_id)
        if not character:
            not_found_log.append(name_or_id)
            continue

        char_updates = {}
        char_log = [f"{character.name}:"]

        if hp_change is not None:
            new_hp = character.hit_points_current + hp_change
            # Clamp HP between 0 and max HP
            new_hp = max(0, min(new_hp, character.hit_points_max))
            char_updates["hit_points_current"] = new_hp
            char_log.append(f"HP -> {new_hp}")

        if temp_hp_change is not None:
            new_temp_hp = character.temporary_hit_points + temp_hp_change
            # Temp HP cannot be negative
            new_temp_hp = max(0, new_temp_hp)
            char_updates["temporary_hit_points"] = new_temp_hp
            char_log.append(f"Temp HP -> {new_temp_hp}")

        ability_changes = {
            "strength": strength_change,
            "dexterity": dexterity_change,
            "constitution": constitution_change,
            "intelligence": intelligence_change,
            "wisdom": wisdom_change,
            "charisma": charisma_change,
        }
        abilities_modified = False
        for ability, change in ability_changes.items():
            if change is not None:
                new_score = character.abilities[ability].score + change
                new_score = max(1, min(new_score, 30))  # Clamp score
                character.abilities[ability].score = new_score
                char_log.append(f"{ability.capitalize()} -> {new_score}")
                abilities_modified = True

        if char_updates or abilities_modified:
            if char_updates:
                storage.update_character(str(character.id), **char_updates)
            elif abilities_modified:
                # Abilities are modified in place, just need to trigger a save
                storage._save_campaign()
            updates_log.append(" ".join(char_log))

    response_parts = []
    if updates_log:
        response_parts.append("Characters updated:\n" + "\n".join(updates_log))
    if not_found_log:
        response_parts.append(f"Characters not found: {', '.join(not_found_log)}")

    return "\n".join(response_parts) if response_parts else "No characters found to update."


@tool_with_logging(mcp, tags=["mode:any"])
def add_item_to_character(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character to receive the item.")
    ],
    item_name: Annotated[str, Field(description="Item name")],
    description: Annotated[str | None, Field(description="Item description")] = None,
    quantity: Annotated[int, Field(description="Quantity", ge=1)] = 1,
    item_type: Annotated[
        Literal["weapon", "armor", "consumable", "misc"], Field(description="Item type")
    ] = "misc",
    weight: Annotated[float | None, Field(description="Item weight", ge=0)] = None,
    value: Annotated[str | None, Field(description="Item value (e.g., '50 gp')")] = None,
) -> str:
    """Add an item to a character's inventory."""
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    item = Item(
        name=item_name,
        description=description,
        quantity=quantity,
        item_type=item_type,
        weight=weight,
        value=value,
    )

    character.inventory.append(item)
    storage.update_character(str(character.id), inventory=character.inventory)

    return f"Added {item.quantity}x {item.name} to {character.name}'s inventory"


@tool_with_logging(mcp, tags=["mode:any"])
def remove_item_from_character(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character to remove the item from.")
    ],
    item_name: Annotated[str, Field(description="Name of the item to remove")],
    quantity: Annotated[int | None, Field(description="Quantity to remove (removes all if not specified)", ge=1)] = None,
) -> str:
    """Remove an item from a character's inventory."""
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    # Find the item in inventory
    item_to_remove = None
    item_index = None
    for idx, item in enumerate(character.inventory):
        if item.name.lower() == item_name.lower():
            item_to_remove = item
            item_index = idx
            break

    if not item_to_remove:
        return f"❌ Item '{item_name}' not found in {character.name}'s inventory!"

    # Determine how much to remove
    remove_quantity = quantity if quantity is not None else item_to_remove.quantity

    if remove_quantity >= item_to_remove.quantity:
        # Remove the entire item
        character.inventory.pop(item_index)
        storage.update_character(str(character.id), inventory=character.inventory)
        return f"Removed {item_to_remove.quantity}x {item_to_remove.name} from {character.name}'s inventory"
    else:
        # Reduce the quantity
        item_to_remove.quantity -= remove_quantity
        storage.update_character(str(character.id), inventory=character.inventory)
        return f"Removed {remove_quantity}x {item_to_remove.name} from {character.name}'s inventory ({item_to_remove.quantity} remaining)"


@tool_with_logging(mcp, tags=["mode:any"])
def add_spell_to_character(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character to add the spell to.")
    ],
    spell_name: Annotated[str, Field(description="Name of the spell to add")],
    spell_level: Annotated[int, Field(description="Spell level (0-9)", ge=0, le=9)],
) -> str:
    """Add a spell to a character's known spells list.

    The spell is added as unprepared. If a spell with the same name already exists,
    it will not be added again (duplicates are ignored).
    """
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    # Check if spell already exists (case-insensitive)
    for existing_spell in character.spells_known:
        if existing_spell.name.lower() == spell_name.lower():
            return f"⚠️ {character.name} already knows '{spell_name}'"

    # Create minimal spell (other properties can be set later)
    new_spell = Spell(
        name=spell_name,
        level=spell_level,
        school="",  # Default, can be updated later
        casting_time="",  # Default, can be updated later
        duration="",  # Default, can be updated later
        components=[],  # Default, can be updated later
        description="",  # Default, can be updated later
        prepared=False,
    )

    character.spells_known.append(new_spell)
    storage.update_character(str(character.id), spells_known=character.spells_known)

    return f"Added '{spell_name}' (Level {spell_level}) to {character.name}'s known spells (unprepared)"


@tool_with_logging(mcp, tags=["mode:any"])
def prepare_spells(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character to prepare spells for.")
    ],
    spell_names: Annotated[
        list[str],
        Field(description="List of spell names to mark as prepared. Any spells NOT in this list will be marked as unprepared.")
    ],
) -> str:
    """Prepare specific spells for a character.

    This tool sets which spells are prepared for use. IMPORTANT: Any spells NOT included in the
    spell_names list will be marked as UNPREPARED. This completely replaces the current prepared
    spell selection.

    Example: If a character knows 10 spells and you pass 3 spell names, those 3 will be prepared
    and the other 7 will become unprepared.
    """
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    if not character.spells_known:
        return f"❌ {character.name} doesn't know any spells yet!"

    # Create case-insensitive lookup of spell names to prepare
    spells_to_prepare = {name.lower() for name in spell_names}

    # Track changes
    prepared_count = 0
    unprepared_count = 0
    not_found = []

    # Update prepared status for all spells
    for spell in character.spells_known:
        if spell.name.lower() in spells_to_prepare:
            if not spell.prepared:
                spell.prepared = True
                prepared_count += 1
            spells_to_prepare.remove(spell.name.lower())  # Mark as found
        else:
            if spell.prepared:
                spell.prepared = False
                unprepared_count += 1

    # Any remaining names in spells_to_prepare weren't found
    not_found = list(spells_to_prepare)

    storage.update_character(str(character.id), spells_known=character.spells_known)

    # Build response message
    parts = []
    if prepared_count > 0:
        parts.append(f"Prepared {prepared_count} spell(s)")
    if unprepared_count > 0:
        parts.append(f"Unprepared {unprepared_count} spell(s)")

    result = f"{character.name}: {', '.join(parts)}" if parts else f"{character.name}: No changes to prepared spells"

    if not_found:
        result += f"\n⚠️ Warning: Could not find these spells: {', '.join(not_found)}"

    return result


@tool_with_logging(mcp, tags=["mode:any"])
def update_spell_slot(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character to update spell slots for.")
    ],
    spell_level: Annotated[int, Field(description="Spell level (1-9)", ge=1, le=9)],
    max_slots: Annotated[int, Field(description="Maximum number of spell slots for this level", ge=0)],
    slots_used: Annotated[int, Field(description="Number of slots currently used", ge=0)],
) -> str:
    """Update spell slot information for a specific spell level.

    This tool is used for both initial setup of spell slots and ongoing management during gameplay:
    - **Initial Setup**: Set max_slots to the character's maximum for each spell level, slots_used to 0
    - **Casting Spells**: Increment slots_used when a spell is cast
    - **Recovery (Short/Long Rest)**: Set slots_used to 0 or reduce it based on recovery rules

    Example uses:
    - Setup: spell_level=1, max_slots=4, slots_used=0 (character has 4 level 1 slots, all available)
    - After casting: spell_level=1, max_slots=4, slots_used=2 (2 slots used, 2 remaining)
    - After rest: spell_level=1, max_slots=4, slots_used=0 (all slots recovered)
    """
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    # Validate slots_used doesn't exceed max_slots
    if slots_used > max_slots:
        return f"❌ Error: slots_used ({slots_used}) cannot exceed max_slots ({max_slots})"

    # Update spell slot dictionaries
    character.spell_slots[spell_level] = max_slots
    character.spell_slots_used[spell_level] = slots_used

    storage.update_character(
        str(character.id),
        spell_slots=character.spell_slots,
        spell_slots_used=character.spell_slots_used
    )

    remaining = max_slots - slots_used
    return f"Updated {character.name}'s level {spell_level} spell slots: {max_slots} total ({slots_used} used, {remaining} remaining)"


@tool_with_logging(mcp, tags=["mode:any"])
def use_spell_slot(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character casting the spell.")
    ],
    spell_level: Annotated[int, Field(description="Spell level (1-9)", ge=1, le=9)],
) -> str:
    """Mark a spell slot as used when a spell is cast.

    This is a convenience tool that automatically increments the slots_used counter.
    Use this instead of update_spell_slot when a character casts a spell.

    The tool validates that an available slot exists before marking it as used.
    """
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    # Check if character has spell slots at this level
    if spell_level not in character.spell_slots or character.spell_slots[spell_level] == 0:
        return f"❌ {character.name} has no level {spell_level} spell slots!"

    # Get current slot usage
    max_slots = character.spell_slots[spell_level]
    slots_used = character.spell_slots_used.get(spell_level, 0)

    # Check if slots are available
    if slots_used >= max_slots:
        return f"❌ {character.name} has no remaining level {spell_level} spell slots! ({slots_used}/{max_slots} used)"

    # Increment slots used
    new_slots_used = slots_used + 1
    character.spell_slots_used[spell_level] = new_slots_used

    storage.update_character(
        str(character.id),
        spell_slots_used=character.spell_slots_used
    )

    remaining = max_slots - new_slots_used
    return f"🔮 {character.name} uses a level {spell_level} spell slot. Slots remaining: {remaining}/{max_slots}"


@tool_with_logging(mcp, tags=["mode:any"])
def restore_spell_slots(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character recovering spell slots.")
    ],
    levels: Annotated[
        list[int] | None,
        Field(description="Spell levels to restore (1-9). If not specified, restores all levels (long rest).")
    ] = None,
) -> str:
    """Restore spell slots after a rest.

    This is a convenience tool for recovering spell slots.
    - Long rest: Don't specify levels (restores all slots)
    - Short rest/partial recovery: Specify which levels to restore

    Examples:
    - After long rest: restore_spell_slots("Wizard")
    - After short rest (Warlock): restore_spell_slots("Warlock", levels=[1, 2])
    """
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    if not character.spell_slots:
        return f"❌ {character.name} has no spell slots to restore!"

    # Determine which levels to restore
    if levels is None:
        # Long rest - restore all levels
        levels_to_restore = list(character.spell_slots.keys())
        rest_type = "long rest"
    else:
        # Validate levels
        for level in levels:
            if level < 1 or level > 9:
                return f"❌ Invalid spell level: {level}. Must be between 1 and 9."
        levels_to_restore = levels
        rest_type = "rest"

    # Restore slots
    restored_levels = []
    for level in levels_to_restore:
        if level in character.spell_slots and character.spell_slots[level] > 0:
            character.spell_slots_used[level] = 0
            restored_levels.append(level)

    if not restored_levels:
        return f"{character.name} has no spell slots at the specified levels."

    storage.update_character(
        str(character.id),
        spell_slots_used=character.spell_slots_used
    )

    if len(restored_levels) == len(character.spell_slots):
        return f"✨ {character.name} takes a {rest_type} and recovers all spell slots!"
    else:
        levels_str = ", ".join(str(l) for l in sorted(restored_levels))
        return f"✨ {character.name} takes a {rest_type} and recovers spell slots for levels: {levels_str}"


@tool_with_logging(mcp, tags=["mode:any"])
def add_special_ability(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character to add the special ability to.")
    ],
    ability_name: Annotated[str, Field(description="Name of the special ability")],
    description: Annotated[
        str, Field(description="Description of the ability, including its effects")
    ],
    uses: Annotated[
        str | None,
        Field(description="Description of usage limitations (e.g., '3/day', 'Recharges on short rest', 'Unlimited')")
    ] = None,
    uses_remaining: Annotated[
        int | None,
        Field(description="Number of uses remaining if the ability has limited uses", ge=0)
    ] = None,
) -> str:
    """Add a special ability to a character.

    Special abilities can include racial features, class features, feats, magical items effects,
    or any other unique capabilities the character possesses.

    If the ability has limited uses per day/rest, specify both 'uses' (describing the limitation)
    and 'uses_remaining' (the current count).
    """
    from gamemaster_mcp.models import SpecialAbility

    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    # Check if ability with same name already exists (case-insensitive)
    for existing_ability in character.special_abilities:
        if existing_ability.name.lower() == ability_name.lower():
            return f"⚠️ {character.name} already has a special ability named '{ability_name}'. Use update_special_ability to modify it."

    # Create new special ability
    new_ability = SpecialAbility(
        name=ability_name,
        description=description,
        uses=uses,
        uses_remaining=uses_remaining,
    )

    character.special_abilities.append(new_ability)
    storage.update_character(str(character.id), special_abilities=character.special_abilities)

    uses_info = ""
    if uses:
        uses_info = f" ({uses}"
        if uses_remaining is not None:
            uses_info += f", {uses_remaining} remaining"
        uses_info += ")"

    return f"✅ Added special ability '{ability_name}' to {character.name}{uses_info}"


@tool_with_logging(mcp, tags=["mode:any"])
def remove_special_ability(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character to remove the special ability from.")
    ],
    ability_name: Annotated[str, Field(description="Name of the special ability to remove")],
) -> str:
    """Remove a special ability from a character.

    The ability is identified by name (case-insensitive match).
    """
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    # Find and remove the ability (case-insensitive)
    ability_to_remove = None
    for ability in character.special_abilities:
        if ability.name.lower() == ability_name.lower():
            ability_to_remove = ability
            break

    if not ability_to_remove:
        return f"❌ Special ability '{ability_name}' not found for {character.name}"

    character.special_abilities.remove(ability_to_remove)
    storage.update_character(str(character.id), special_abilities=character.special_abilities)

    return f"✅ Removed special ability '{ability_to_remove.name}' from {character.name}"


@tool_with_logging(mcp, tags=["mode:any"])
def update_special_ability(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character whose special ability to update.")
    ],
    ability_name: Annotated[str, Field(description="Name of the special ability to update")],
    new_name: Annotated[
        str | None,
        Field(description="New name for the ability (optional)")
    ] = None,
    new_description: Annotated[
        str | None,
        Field(description="New description for the ability (optional)")
    ] = None,
    new_uses: Annotated[
        str | None,
        Field(description="New usage limitations description (optional)")
    ] = None,
    new_uses_remaining: Annotated[
        int | None,
        Field(description="New number of uses remaining (optional)", ge=0)
    ] = None,
) -> str:
    """Update an existing special ability for a character.

    The ability is identified by its current name (case-insensitive match).
    Any field that is provided will be updated; fields not provided will remain unchanged.

    Common use cases:
    - Decrease uses_remaining when an ability is used
    - Restore uses_remaining after a rest
    - Update the description if the ability evolves
    - Rename an ability
    """
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    # Find the ability (case-insensitive)
    ability_to_update = None
    for ability in character.special_abilities:
        if ability.name.lower() == ability_name.lower():
            ability_to_update = ability
            break

    if not ability_to_update:
        return f"❌ Special ability '{ability_name}' not found for {character.name}"

    # Track changes for output
    changes = []

    if new_name is not None and new_name != ability_to_update.name:
        old_name = ability_to_update.name
        ability_to_update.name = new_name
        changes.append(f"name: '{old_name}' → '{new_name}'")

    if new_description is not None and new_description != ability_to_update.description:
        ability_to_update.description = new_description
        changes.append("description updated")

    if new_uses is not None and new_uses != ability_to_update.uses:
        old_uses = ability_to_update.uses or "None"
        ability_to_update.uses = new_uses
        changes.append(f"uses: {old_uses} → {new_uses}")

    if new_uses_remaining is not None and new_uses_remaining != ability_to_update.uses_remaining:
        old_remaining = ability_to_update.uses_remaining
        ability_to_update.uses_remaining = new_uses_remaining
        changes.append(f"uses remaining: {old_remaining} → {new_uses_remaining}")

    if not changes:
        return f"ℹ️ No changes made to '{ability_to_update.name}' for {character.name}"

    storage.update_character(str(character.id), special_abilities=character.special_abilities)

    return f"✅ Updated special ability '{ability_name}' for {character.name}:\n  • " + "\n  • ".join(changes)


@tool_with_logging(mcp, tags=["mode:any"])
def list_characters() -> str:
    """List all characters in the current campaign."""
    characters = storage.list_characters()
    if not characters:
        return "No characters in the current campaign."

    char_list = []
    for char_name in characters:
        char = storage.get_character(char_name)
        if char:
            char_list.append(
                f"• {char.name} (Level {char.character_class.level} {char.race.name} {char.character_class.name})"
            )

    return "**Characters:**\n" + "\n".join(char_list)


# NPC Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def create_npc(
    name: Annotated[str, Field(description="NPC name")],
    description: Annotated[
        str | None, Field(description="A brief, public description of the NPC.")
    ] = None,
    bio: Annotated[
        str | None, Field(description="A detailed, private bio for the NPC, including secrets.")
    ] = None,
    race: Annotated[str | None, Field(description="NPC race")] = None,
    occupation: Annotated[str | None, Field(description="NPC occupation")] = None,
    location: Annotated[str | None, Field(description="Current location")] = None,
    attitude: Annotated[
        Literal["friendly", "neutral", "hostile", "unknown"] | None,
        Field(description="Attitude towards party"),
    ] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a new NPC."""
    npc = NPC(
        name=name,
        description=description,
        bio=bio,
        race=race,
        occupation=occupation,
        location=location,
        attitude=attitude,
        notes=notes,
    )

    storage.add_npc(npc)
    return f"Created NPC '{npc.name}'"


@tool_with_logging(mcp, tags=["mode:any"])
def get_npc(name: Annotated[str, Field(description="NPC name")]) -> str:
    """Get NPC information."""
    npc = storage.get_npc(name)
    if not npc:
        return f"NPC '{name}' not found."

    npc_info = f"""**{npc.name}** (`{npc.id}`)
**Race:** {npc.race or "Unknown"}
**Occupation:** {npc.occupation or "Unknown"}
**Location:** {npc.location or "Unknown"}
**Attitude:** {npc.attitude or "Neutral"}

**Description:** {npc.description or "No description available."}
**Bio:** {npc.bio or "No bio available."}

**Notes:** {npc.notes or "No additional notes."}
"""

    return npc_info


@tool_with_logging(mcp, tags=["mode:any"])
def list_npcs() -> str:
    """List all NPCs in the current campaign."""
    npcs = storage.list_npcs()
    if not npcs:
        return "No NPCs in the current campaign."

    npc_list = []
    for npc_name in npcs:
        npc = storage.get_npc(npc_name)
        if npc:
            location = f" ({npc.location})" if npc.location else ""
            npc_list.append(f"• {npc.name}{location}")

    return "**NPCs:**\n" + "\n".join(npc_list)


# Monster Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def create_monster(
    name: Annotated[str, Field(description="Instance name for this specific monster")],
    monster_type: Annotated[
        str, Field(description="The type/species of monster (e.g., 'Goblin', 'Dragon')")
    ],
    hit_points_max: Annotated[int, Field(description="Maximum hit points", ge=1)],
    hit_points_current: Annotated[int | None, Field(description="Current hit points")] = None,
    armor_class: Annotated[int, Field(description="Armor class", ge=1)] = 10,
    size: Annotated[str, Field(description="Monster size")] = "Medium",
    creature_type: Annotated[str, Field(description="Creature type")] = "humanoid",
    alignment: Annotated[str, Field(description="Monster alignment")] = "neutral",
    speed: Annotated[int, Field(description="Speed in feet per round")] = 30,
    challenge_rating: Annotated[
        str, Field(description="Challenge rating (e.g., '1/4', '2', '15')")
    ] = "1/8",
    experience_value: Annotated[int, Field(description="Experience points awarded", ge=0)] = 25,
    description: Annotated[str | None, Field(description="Monster description")] = None,
    location: Annotated[str | None, Field(description="Where this monster is located")] = None,
    strength: Annotated[int, Field(description="Strength score", ge=1, le=30)] = 10,
    dexterity: Annotated[int, Field(description="Dexterity score", ge=1, le=30)] = 10,
    constitution: Annotated[int, Field(description="Constitution score", ge=1, le=30)] = 10,
    intelligence: Annotated[int, Field(description="Intelligence score", ge=1, le=30)] = 10,
    wisdom: Annotated[int, Field(description="Wisdom score", ge=1, le=30)] = 10,
    charisma: Annotated[int, Field(description="Charisma score", ge=1, le=30)] = 10,
) -> str:
    """Create a new monster and add it to the current game state."""
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        return "No active campaign. Please create or load a campaign first."

    # Build ability scores
    abilities = {
        "strength": AbilityScore(score=strength),
        "dexterity": AbilityScore(score=dexterity),
        "constitution": AbilityScore(score=constitution),
        "intelligence": AbilityScore(score=intelligence),
        "wisdom": AbilityScore(score=wisdom),
        "charisma": AbilityScore(score=charisma),
    }

    # Set current HP to max if not provided
    if hit_points_current is None:
        hit_points_current = hit_points_max

    monster = Monster(
        name=name,
        monster_type=monster_type,
        hit_points_max=hit_points_max,
        hit_points_current=hit_points_current,
        armor_class=armor_class,
        size=size,
        creature_type=creature_type,
        alignment=alignment,
        speed=speed,
        challenge_rating=challenge_rating,
        experience_value=experience_value,
        description=description,
        location=location,
        abilities=abilities,
    )

    # Add monster to game state
    current_campaign.game_state.monsters.append(monster)
    storage._save_campaign()

    return f"Created monster '{monster.name}' ({monster.monster_type}) with {monster.hit_points_current}/{monster.hit_points_max} HP"


@tool_with_logging(mcp, tags=["mode:any"])
def get_monster(name: Annotated[str, Field(description="Monster name")]) -> str:
    """Get monster information."""
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        return "No active campaign. Please create or load a campaign first."

    monster = None
    for m in current_campaign.game_state.monsters:
        if m.name.lower() == name.lower():
            monster = m
            break

    if not monster:
        return f"Monster '{name}' not found in current game state."

    # Format attacks
    attacks_info = ""
    if monster.attacks:
        attacks_list = []
        for attack in monster.attacks:
            attacks_list.append(
                f"  • {attack.weapon}: +{attack.attack_roll_modifier} to hit, {attack.damage_roll} damage"
            )
        attacks_info = "\n**Attacks:**\n" + "\n".join(attacks_list)

    # Format special abilities
    abilities_info = ""
    if monster.special_abilities:
        abilities_info = f"\n**Special Abilities:** {', '.join(monster.special_abilities)}"

    # Format resistances/immunities
    resist_info = ""
    if monster.damage_resistances:
        resist_info += f"\n**Damage Resistances:** {', '.join(monster.damage_resistances)}"
    if monster.damage_immunities:
        resist_info += f"\n**Damage Immunities:** {', '.join(monster.damage_immunities)}"
    if monster.condition_immunities:
        resist_info += f"\n**Condition Immunities:** {', '.join(monster.condition_immunities)}"

    monster_info = f"""**{monster.name}** ({monster.monster_type}) - `{monster.id}`
**Size/Type:** {monster.size} {monster.creature_type}
**Alignment:** {monster.alignment}
**AC:** {monster.armor_class} **HP:** {monster.hit_points_current}/{monster.hit_points_max}
**Speed:** {monster.speed} ft **Status:** {monster.status}
**Challenge Rating:** {monster.challenge_rating} ({monster.experience_value} XP)

**Ability Scores:**
STR {monster.abilities["strength"].score} ({monster.abilities["strength"].mod:+d})
DEX {monster.abilities["dexterity"].score} ({monster.abilities["dexterity"].mod:+d})
CON {monster.abilities["constitution"].score} ({monster.abilities["constitution"].mod:+d})
INT {monster.abilities["intelligence"].score} ({monster.abilities["intelligence"].mod:+d})
WIS {monster.abilities["wisdom"].score} ({monster.abilities["wisdom"].mod:+d})
CHA {monster.abilities["charisma"].score} ({monster.abilities["charisma"].mod:+d})
{attacks_info}{abilities_info}{resist_info}

**Location:** {monster.location or "Unknown"}
**Description:** {monster.description or "No description available."}
"""

    if monster.notes:
        monster_info += f"\n**Notes:** {monster.notes}"

    return monster_info


@tool_with_logging(mcp, tags=["mode:any"])
def list_monsters() -> str:
    """List all monsters in the current game state."""
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        return "No active campaign. Please create or load a campaign first."

    monsters = current_campaign.game_state.monsters
    if not monsters:
        return "No monsters in the current game state."

    monster_list = []
    for monster in monsters:
        status_info = f" [{monster.status}]" if monster.status != "alive" else ""
        hp_info = f" ({monster.hit_points_current}/{monster.hit_points_max} HP)"
        location_info = f" at {monster.location}" if monster.location else ""
        monster_list.append(
            f"• {monster.name} ({monster.monster_type}){status_info}{hp_info}{location_info}"
        )

    return "**Active Monsters:**\n" + "\n".join(monster_list)


# Location Management Tools
@tool_with_logging(mcp, tags=["mode:setup"])
def create_location(
    name: Annotated[str, Field(description="Location name")],
    location_type: Annotated[
        str, Field(description="Type of location (city, town, village, dungeon, etc.)")
    ],
    description: Annotated[str, Field(description="Location description")],
    population: Annotated[int | None, Field(description="Population (if applicable)", ge=0)] = None,
    government: Annotated[str | None, Field(description="Government type")] = None,
    notable_features: Annotated[list[str] | None, Field(description="Notable features")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
    # NEW: Hierarchy and Map Integration
    parent_location_id: Annotated[str | None, Field(description="ID of parent location in hierarchy")] = None,
    location_scale: Annotated[LocationScale, Field(description="Scale/scope of this location")] = LocationScale.LOCAL,
    primary_map: Annotated[str | None, Field(description="Name of hex map this location appears on")] = None,
    hex_x: Annotated[int | None, Field(description="X coordinate on hex map")] = None,
    hex_y: Annotated[int | None, Field(description="Y coordinate on hex map")] = None,
) -> str:
    """Create a new location with optional hierarchy and map placement."""
    # Build hex coordinate if provided
    hex_coordinate = None
    if hex_x is not None and hex_y is not None:
        hex_coordinate = HexCoordinate(x=hex_x, y=hex_y)

    location = Location(
        name=name,
        location_type=location_type,
        description=description,
        population=population,
        government=government,
        notable_features=notable_features or [],
        notes=notes,
        parent_location_id=parent_location_id,
        location_scale=location_scale,
        primary_map=primary_map,
        hex_coordinate=hex_coordinate,
    )

    storage.add_location(location)

    # Update parent's child_locations if parent specified
    if parent_location_id:
        try:
            storage.set_parent_location(location.id, parent_location_id)
        except ValueError as e:
            logger.warning(f"Could not set parent: {e}")

    result = f"Created location '{location.name}' ({location.location_type}, scale: {location.location_scale})"
    if parent_location_id:
        result += f" as child of location ID {parent_location_id}"
    if primary_map:
        result += f" on map '{primary_map}'"
        if hex_coordinate:
            result += f" at ({hex_coordinate.x}, {hex_coordinate.y})"

    return result


@tool_with_logging(mcp, tags=["mode:any"])
def get_location(name: Annotated[str, Field(description="Location name")]) -> str:
    """Get location information including hierarchy and map placement."""
    location = storage.get_location(name)
    if not location:
        return f"Location '{name}' not found."

    loc_info = f"""**{location.name}** ({location.location_type})
**ID:** {location.id}
**Scale:** {location.location_scale}

**Description:** {location.description}

**Population:** {location.population or "Unknown"}
**Government:** {location.government or "Unknown"}

**Notable Features:**
{chr(10).join(["• " + feature for feature in location.notable_features]) if location.notable_features else "None listed"}
"""

    # Add hierarchy information
    try:
        hierarchy = storage.get_location_hierarchy(location.id)
        if hierarchy["ancestors"]:
            path = " > ".join([a["name"] for a in hierarchy["ancestors"]] + [location.name])
            loc_info += f"\n**Hierarchy Path:** {path}"

        if hierarchy["descendants"]:
            def format_children(children, indent=0):
                result = []
                for child in children:
                    result.append("  " * indent + f"• {child['name']} ({child['scale']})")
                    if child.get("children"):
                        result.extend(format_children(child["children"], indent + 1))
                return result

            children_text = "\n".join(format_children(hierarchy["descendants"]))
            loc_info += f"\n\n**Child Locations:**\n{children_text}"
    except Exception as e:
        logger.warning(f"Could not get hierarchy: {e}")

    # Add map information
    if location.primary_map:
        loc_info += f"\n\n**Map:** {location.primary_map}"
        if location.hex_coordinate:
            loc_info += f" at ({location.hex_coordinate.x}, {location.hex_coordinate.y})"

    loc_info += f"\n\n**Notes:** {location.notes or 'No additional notes.'}"

    return loc_info


@tool_with_logging(mcp, tags=["mode:any"])
def list_locations() -> str:
    """List all locations in the current campaign."""
    locations = storage.list_locations()
    if not locations:
        return "No locations in the current campaign."

    loc_list = []
    for loc_name in locations:
        loc = storage.get_location(loc_name)
        if loc:
            loc_list.append(f"• {loc.name} ({loc.location_type})")

    return "**Locations:**\n" + "\n".join(loc_list)


@tool_with_logging(mcp, tags=["mode:any"])
def delete_location(
    location_id: Annotated[str, Field(description="ID of location to delete")],
    recursive: Annotated[bool, Field(description="If True, delete all child locations. If False, prevent deletion if location has children")] = False,
) -> str:
    """Delete a location from the campaign.

    By default (recursive=False), prevents deletion if location has children.
    Use recursive=True to delete location and ALL descendants (like rm -rf).
    """
    campaign = storage.get_current_campaign()
    if not campaign:
        return "No active campaign."

    # Find location by ID
    location = None
    for loc in campaign.locations.values():
        if loc.id == location_id:
            location = loc
            break

    if not location:
        return f"Location with ID '{location_id}' not found."

    # Check if location has children
    if location.child_locations and not recursive:
        return f"Location '{location.name}' has {len(location.child_locations)} child location(s). Use recursive=True to delete this location and all descendants, or remove child locations first."

    # Recursive deletion
    if recursive and location.child_locations:
        deleted_count = 0
        for child_id in list(location.child_locations):  # Copy list to avoid modification during iteration
            try:
                delete_result = delete_location(child_id, recursive=True)
                if "Deleted" in delete_result:
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Error deleting child {child_id}: {e}")

        logger.info(f"Recursively deleted {deleted_count} child locations of '{location.name}'")

    # Remove from parent's child_locations
    if location.parent_location_id:
        for loc in campaign.locations.values():
            if loc.id == location.parent_location_id and location.id in loc.child_locations:
                loc.child_locations.remove(location.id)
                break

    # Remove location
    del campaign.locations[location.name]
    campaign.updated_at = storage._save_campaign()

    return f"Deleted location '{location.name}' (ID: {location_id})" + (f" and {deleted_count} descendant(s)" if recursive and deleted_count > 0 else "")


# Root Location Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def get_root_location() -> str:
    """Get information about the campaign's root location.

    Returns summary of root location including its direct children.
    """
    root = storage.get_root_location()
    if not root:
        return "No root location set for this campaign. Use create_location to create one, then set_root_location to designate it as the root."

    root_info = f"""**Root Location: {root.name}**
**ID:** {root.id}
**Type:** {root.location_type}
**Scale:** {root.location_scale}
**Description:** {root.description}
"""

    # List direct children
    top_level = storage.get_top_level_locations()
    if top_level:
        children_list = [f"• {loc.name} ({loc.location_scale})" for loc in top_level]
        root_info += f"\n**Top-level Locations ({len(top_level)}):**\n" + "\n".join(children_list)
    else:
        root_info += "\n**Top-level Locations:** None"

    return root_info


@tool_with_logging(mcp, tags=["mode:any"])
def set_root_location(location_id: Annotated[str, Field(description="ID of location to become root")]) -> str:
    """Set an existing location as the campaign root.

    The location must not have a parent. All orphaned locations will
    become children of the new root.
    """
    try:
        storage.set_root_location(location_id)

        root = storage.get_root_location()
        orphans = storage.get_orphaned_locations()

        result = f"Set '{root.name}' as campaign root location."
        if orphans:
            result += f"\n{len(orphans)} orphaned location(s) are now implicitly children of the root."

        return result
    except ValueError as e:
        return f"Error: {e}"


@tool_with_logging(mcp, tags=["mode:any"])
def get_top_level_locations() -> str:
    """List all top-level locations (direct children of root, or orphans if no root)."""
    top_level = storage.get_top_level_locations()

    if not top_level:
        return "No top-level locations found."

    root = storage.get_root_location()
    header = f"**Top-level Locations ({len(top_level)})"
    if root:
        header += f" - children of '{root.name}'"
    header += ":**\n"

    loc_list = [f"• {loc.name} (ID: {loc.id}, scale: {loc.location_scale})" for loc in top_level]

    return header + "\n".join(loc_list)


# Location Hierarchy Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def set_location_parent(
    child_location_id: Annotated[str, Field(description="ID of child location")],
    parent_location_id: Annotated[str | None, Field(description="ID of parent location, or None to make child a top-level location")] = None,
) -> str:
    """Set or clear the parent location for a location.

    Setting parent to None makes the location a child of the campaign root (if root exists).
    """
    try:
        storage.set_parent_location(child_location_id, parent_location_id)

        # Get location names for result message
        campaign = storage.get_current_campaign()
        if not campaign:
            return "No active campaign."

        child = None
        parent = None
        for loc in campaign.locations.values():
            if loc.id == child_location_id:
                child = loc
            if parent_location_id and loc.id == parent_location_id:
                parent = loc

        if parent:
            return f"Set '{child.name}' as child of '{parent.name}'"
        else:
            return f"Set '{child.name}' as top-level location"

    except ValueError as e:
        return f"Error: {e}"


@tool_with_logging(mcp, tags=["mode:any"])
def get_location_hierarchy(
    location_id: Annotated[str, Field(description="ID of location to get hierarchy for")],
    include_children: Annotated[bool, Field(description="Include child locations")] = True,
    include_ancestors: Annotated[bool, Field(description="Include ancestor locations")] = True,
) -> str:
    """Get the hierarchical context for a location."""
    try:
        hierarchy = storage.get_location_hierarchy(location_id)

        # Find location name
        campaign = storage.get_current_campaign()
        if not campaign:
            return "No active campaign."

        location = None
        for loc in campaign.locations.values():
            if loc.id == location_id:
                location = loc
                break

        if not location:
            return f"Location with ID '{location_id}' not found."

        result = f"**Hierarchy for '{location.name}':**\n\n"

        # Ancestors
        if include_ancestors and hierarchy["ancestors"]:
            path = " > ".join([a["name"] for a in hierarchy["ancestors"]] + [location.name])
            result += f"**Path from Root:** {path}\n"

        # Current location
        result += f"\n**Current Location:** {location.name} (scale: {location.location_scale})\n"

        # Descendants
        if include_children and hierarchy["descendants"]:
            def format_tree(children, indent=0):
                lines = []
                for child in children:
                    lines.append("  " * indent + f"• {child['name']} ({child['scale']})")
                    if child.get("children"):
                        lines.extend(format_tree(child["children"], indent + 1))
                return lines

            result += "\n**Child Locations:**\n" + "\n".join(format_tree(hierarchy["descendants"]))
        elif include_children:
            result += "\n**Child Locations:** None"

        return result

    except ValueError as e:
        return f"Error: {e}"


@tool_with_logging(mcp, tags=["mode:any"])
def list_child_locations(
    parent_location_id: Annotated[str, Field(description="ID of parent location")],
    recursive: Annotated[bool, Field(description="If True, list all descendants recursively")] = False,
) -> str:
    """List all child locations within a parent location."""
    campaign = storage.get_current_campaign()
    if not campaign:
        return "No active campaign."

    # Find parent location
    parent = None
    for loc in campaign.locations.values():
        if loc.id == parent_location_id:
            parent = loc
            break

    if not parent:
        return f"Location with ID '{parent_location_id}' not found."

    if not parent.child_locations:
        return f"'{parent.name}' has no child locations."

    if recursive:
        # Use hierarchy to get all descendants
        try:
            hierarchy = storage.get_location_hierarchy(parent_location_id)

            def format_tree(children, indent=0):
                lines = []
                for child in children:
                    lines.append("  " * indent + f"• {child['name']} (ID: {child['id']}, scale: {child['scale']})")
                    if child.get("children"):
                        lines.extend(format_tree(child["children"], indent + 1))
                return lines

            if hierarchy["descendants"]:
                return f"**All descendants of '{parent.name}':**\n" + "\n".join(format_tree(hierarchy["descendants"]))
            else:
                return f"'{parent.name}' has no descendants."

        except ValueError as e:
            return f"Error: {e}"
    else:
        # Just list direct children
        children = []
        for child_id in parent.child_locations:
            for loc in campaign.locations.values():
                if loc.id == child_id:
                    children.append(f"• {loc.name} (ID: {loc.id}, scale: {loc.location_scale})")
                    break

        return f"**Direct children of '{parent.name}':**\n" + "\n".join(children)


# Map Integration Tools
@tool_with_logging(mcp, tags=["mode:any"])
def place_location_on_map(
    location_id: Annotated[str, Field(description="ID of location to place")],
    map_name: Annotated[str, Field(description="Name of hex map")],
    x: Annotated[int, Field(description="X coordinate on map")],
    y: Annotated[int, Field(description="Y coordinate on map")],
    create_poi: Annotated[bool, Field(description="Automatically create a corresponding PointOfInterest")] = True,
) -> str:
    """Place a location on a hex map at specific coordinates.

    If create_poi is True, automatically creates a corresponding PointOfInterest.
    """
    try:
        coordinate = HexCoordinate(x=x, y=y)
        storage.update_location_coordinate(location_id, map_name, coordinate)

        campaign = storage.get_current_campaign()
        if not campaign:
            return "No active campaign."

        location = None
        for loc in campaign.locations.values():
            if loc.id == location_id:
                location = loc
                break

        result = f"Placed '{location.name}' on map '{map_name}' at ({x}, {y})"

        if create_poi:
            # Create POI if it doesn't exist
            hex_map = storage.get_hex_map(map_name)
            if hex_map:
                hex_obj = hex_map.get_hex(coordinate)
                if not hex_obj:
                    # Create new hex
                    from .models import Hex
                    hex_obj = Hex(coordinate=coordinate, terrain=hex_map.default_terrain)
                    hex_map.set_hex(hex_obj)

                # Check if POI already exists for this location
                poi_exists = any(poi.location_id == location_id for poi in hex_obj.pois)

                if not poi_exists:
                    # Create new POI
                    poi = PointOfInterest(
                        name=location.name,
                        poi_type=POIType.TOWN,  # Default, can be customized
                        description=location.description,
                        location_id=location_id,
                        discovered=False
                    )
                    hex_obj.pois.append(poi)
                    storage._save_campaign()
                    result += f" and created POI '{poi.name}'"

        return result

    except ValueError as e:
        return f"Error: {e}"


@tool_with_logging(mcp, tags=["mode:any"])
def list_locations_on_map(
    map_name: Annotated[str, Field(description="Name of hex map")],
    location_type: Annotated[str | None, Field(description="Filter by location type")] = None,
) -> str:
    """List all locations that appear on a specific map."""
    locations = storage.get_locations_on_map(map_name)

    if not locations:
        return f"No locations found on map '{map_name}'."

    if location_type:
        locations = [loc for loc in locations if loc.location_type == location_type]
        if not locations:
            return f"No locations of type '{location_type}' found on map '{map_name}'."

    loc_list = []
    for loc in locations:
        coord_str = f"({loc.hex_coordinate.x}, {loc.hex_coordinate.y})" if loc.hex_coordinate else "no coords"
        loc_list.append(f"• {loc.name} ({loc.location_type}) at {coord_str}")

    header = f"**Locations on '{map_name}' ({len(locations)}):**\n"
    return header + "\n".join(loc_list)


@tool_with_logging(mcp, tags=["mode:any"])
def sync_location_and_poi(
    location_id: Annotated[str, Field(description="ID of location")],
    poi_id: Annotated[str, Field(description="ID of POI to sync with")],
) -> str:
    """Synchronize a Location with its corresponding PointOfInterest."""
    try:
        storage.sync_location_with_poi(location_id, poi_id)

        campaign = storage.get_current_campaign()
        if not campaign:
            return "No active campaign."

        location = None
        for loc in campaign.locations.values():
            if loc.id == location_id:
                location = loc
                break

        return f"Synced location '{location.name}' with POI (ID: {poi_id})"

    except ValueError as e:
        return f"Error: {e}"


# Migration Tools
@tool_with_logging(mcp, tags=["mode:any"])
def upgrade_location(
    location_id: Annotated[str, Field(description="ID of location to upgrade")],
    location_type: Annotated[LocationType | None, Field(description="Set structured LocationType enum")] = None,
    location_scale: Annotated[LocationScale | None, Field(description="Set scale level")] = None,
    parent_location_id: Annotated[str | None, Field(description="Set parent in hierarchy")] = None,
    primary_map: Annotated[str | None, Field(description="Set primary map reference")] = None,
    hex_x: Annotated[int | None, Field(description="X coordinate on map")] = None,
    hex_y: Annotated[int | None, Field(description="Y coordinate on map")] = None,
    infer_scale_from_type: Annotated[bool, Field(description="Automatically set location_scale based on type")] = False,
) -> str:
    """Upgrade an existing location to use new hierarchy and map fields.

    This tool allows selective migration of locations from old format to new format.
    Only updates fields that are currently None/empty.
    """
    campaign = storage.get_current_campaign()
    if not campaign:
        return "No active campaign."

    # Find location
    location = None
    for loc in campaign.locations.values():
        if loc.id == location_id:
            location = loc
            break

    if not location:
        return f"Location with ID '{location_id}' not found."

    changes = []

    # Update location_type if provided (note: currently location_type is still a string)
    if location_type:
        location.location_type = location_type.value
        changes.append(f"type → {location_type.value}")

    # Infer scale from type if requested
    if infer_scale_from_type and location_type and not location_scale:
        type_to_scale = {
            LocationType.METROPOLIS: LocationScale.SETTLEMENT,
            LocationType.CITY: LocationScale.SETTLEMENT,
            LocationType.TOWN: LocationScale.SETTLEMENT,
            LocationType.VILLAGE: LocationScale.SETTLEMENT,
            LocationType.HAMLET: LocationScale.SETTLEMENT,
            LocationType.TAVERN: LocationScale.BUILDING,
            LocationType.INN: LocationScale.BUILDING,
            LocationType.SHOP: LocationScale.BUILDING,
            LocationType.MANOR: LocationScale.BUILDING,
            LocationType.HOUSE: LocationScale.BUILDING,
            LocationType.DUNGEON: LocationScale.BUILDING,
            LocationType.CAVE: LocationScale.AREA,
            LocationType.FOREST: LocationScale.AREA,
            LocationType.MOUNTAIN: LocationScale.AREA,
            LocationType.DESERT: LocationScale.AREA,
            LocationType.KINGDOM: LocationScale.KINGDOM,
            LocationType.PROVINCE: LocationScale.PROVINCE,
        }
        inferred_scale = type_to_scale.get(location_type)
        if inferred_scale:
            location_scale = inferred_scale

    # Update scale
    if location_scale and location.location_scale == LocationScale.LOCAL:
        location.location_scale = location_scale
        changes.append(f"scale → {location_scale}")

    # Update parent
    if parent_location_id and not location.parent_location_id:
        try:
            storage.set_parent_location(location_id, parent_location_id)
            changes.append("set parent")
        except ValueError as e:
            return f"Error setting parent: {e}"

    # Update map placement
    if primary_map and not location.primary_map:
        location.primary_map = primary_map
        changes.append(f"map → {primary_map}")

    if hex_x is not None and hex_y is not None and not location.hex_coordinate:
        location.hex_coordinate = HexCoordinate(x=hex_x, y=hex_y)
        changes.append(f"coords → ({hex_x}, {hex_y})")

    if changes:
        campaign.updated_at = storage._save_campaign()
        return f"Upgraded '{location.name}': " + ", ".join(changes)
    else:
        return f"'{location.name}' already has all specified fields set. No changes made."


@tool_with_logging(mcp, tags=["mode:any"])
def list_unmigrated_locations() -> str:
    """List locations that haven't been upgraded to new format.

    A location is considered unmigrated if it has:
    - No parent (and it's not the root location)
    - No children
    - No map placement
    """
    unmigrated = storage.get_unmigrated_locations()

    if not unmigrated:
        return "All locations have been migrated to the new format!"

    loc_list = [f"• {loc.name} (ID: {loc.id}, type: {loc.location_type})" for loc in unmigrated]

    return f"**Unmigrated Locations ({len(unmigrated)}):**\n" + "\n".join(loc_list) + "\n\nUse the `upgrade_location` tool to migrate these locations."


# Quest Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def create_quest(
    title: Annotated[str, Field(description="Quest title")],
    description: Annotated[str, Field(description="Quest description")],
    giver: Annotated[str | None, Field(description="Quest giver (NPC name)")] = None,
    objectives: Annotated[list[str] | None, Field(description="Quest objectives")] = None,
    reward: Annotated[str | None, Field(description="Quest reward")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a new quest."""
    quest = Quest(
        title=title,
        description=description,
        giver=giver,
        objectives=objectives or [],
        reward=reward,
        notes=notes,
    )

    storage.add_quest(quest)
    return f"Created quest '{quest.title}'"


@tool_with_logging(mcp, tags=["mode:any"])
def update_quest(
    title: Annotated[str, Field(description="Quest title")],
    status: Annotated[
        Literal["active", "completed", "failed", "on_hold"] | None,
        Field(description="New quest status"),
    ] = None,
    completed_objective: Annotated[
        str | None, Field(description="Objective to mark as completed")
    ] = None,
) -> str:
    """Update quest status or complete objectives."""
    quest = storage.get_quest(title)
    if not quest:
        return f"Quest '{title}' not found."

    if status:
        storage.update_quest_status(title, status)

    if completed_objective:
        if (
            completed_objective in quest.objectives
            and completed_objective not in quest.completed_objectives
        ):
            quest.completed_objectives.append(completed_objective)
            storage._save_campaign()  # Direct save since we modified the object

    return f"Updated quest '{title}'"


@tool_with_logging(mcp, tags=["mode:any"])
def list_quests(
    status: Annotated[
        Literal["active", "completed", "failed", "on_hold"] | None,
        Field(description="Filter by status"),
    ] = None,
) -> str:
    """List quests, optionally filtered by status."""
    quests = storage.list_quests(status)

    if not quests:
        filter_text = f" with status '{status}'" if status else ""
        return f"No quests found{filter_text}."

    quest_list = []
    for quest_title in quests:
        quest = storage.get_quest(quest_title)
        if quest:
            status_text = f" [{quest.status}]"
            quest_list.append(f"• {quest.title}{status_text}")

    return "**Quests:**\n" + "\n".join(quest_list)


# Game State Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def update_game_state(
    current_location: Annotated[str | None, Field(description="Current party location")] = None,
    current_session: Annotated[
        int | None, Field(description="Current session number", ge=1)
    ] = None,
    current_date_in_game: Annotated[str | None, Field(description="Current in-game date")] = None,
    party_level: Annotated[
        int | None, Field(description="Average party level", ge=1, le=20)
    ] = None,
    party_funds: Annotated[str | None, Field(description="Party treasure/funds")] = None,
    in_combat: Annotated[bool | None, Field(description="Whether party is in combat")] = None,
    notes: Annotated[str | None, Field(description="Current situation notes")] = None,
) -> str:
    """Update the current game state."""
    kwargs: dict[str, str | int | bool] = {}
    if current_location is not None:
        kwargs["current_location"] = current_location
    if current_session is not None:
        kwargs["current_session"] = current_session
    if current_date_in_game is not None:
        kwargs["current_date_in_game"] = current_date_in_game
    if party_level is not None:
        kwargs["party_level"] = party_level
    if party_funds is not None:
        kwargs["party_funds"] = party_funds
    if in_combat is not None:
        kwargs["in_combat"] = in_combat
    if notes is not None:
        kwargs["notes"] = notes

    storage.update_game_state(**kwargs)
    return "Updated game state"


@tool_with_logging(mcp, tags=["mode:any"])
def get_game_state() -> str:
    """Get the current game state."""
    game_state = storage.get_game_state()
    if not game_state:
        return "No game state available."

    state_info = f"""**Game State**
**Campaign:** {game_state.campaign_name}
**Session:** {game_state.current_session}
**Location:** {game_state.current_location or "Unknown"}
**Date (In-Game):** {game_state.current_date_in_game or "Unknown"}
**Party Level:** {game_state.party_level}
**Party Funds:** {game_state.party_funds}
**In Combat:** {"Yes" if game_state.in_combat else "No"}

**Active Quests:** {len(game_state.active_quests)}

**Notes:** {game_state.notes or "No current notes."}
"""

    return state_info


# Mode Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def set_mode(
    modes: Annotated[list[str] | str, Field(description="Mode(s) to set. Can be a single mode string or list of modes")],
) -> str:
    """Set the current game mode(s). Replaces existing modes.

    Available modes: setup, town, outdoors, dungeon, combat
    Combat should be listed first if active.
    """
    # Convert single mode to list
    if isinstance(modes, str):
        modes = [modes]

    # Validate modes
    invalid_modes = [mode for mode in modes if mode not in AVAILABLE_MODES]
    if invalid_modes:
        return f"Invalid modes: {', '.join(invalid_modes)}. Available modes: {', '.join(AVAILABLE_MODES.keys())}"

    # Ensure combat is first if present
    if "combat" in modes and modes[0] != "combat":
        modes = ["combat"] + [mode for mode in modes if mode != "combat"]

    # Update game state
    game_state = storage.get_game_state()
    if not game_state:
        return "No game state available."

    game_state.modes = modes
    storage.update_game_state(modes=modes)

    primary_mode = modes[0] if modes else "none"
    modes_str = ", ".join(modes)
    return f"Set modes to: [{modes_str}]. Primary mode: {primary_mode}"


@tool_with_logging(mcp, tags=["mode:any"])
def get_mode() -> str:
    """Get the current game mode(s)."""
    game_state = storage.get_game_state()
    if not game_state:
        return "No game state available."

    modes = game_state.modes
    if not modes:
        return "No modes set."

    primary_mode = modes[0]
    modes_str = ", ".join(modes)
    return f"Current modes: [{modes_str}]. Primary mode: {primary_mode}"


# Combat Management Tools
@tool_with_logging(mcp, tags=["mode:town", "mode:dunegon", "mode:outdoors"])
def start_combat(
    participants: Annotated[
        list[CombatParticipant], Field(description="Combat participants with initiative order")
    ],
) -> str:
    """Start a combat encounter."""
    # Sort by initiative (highest first)
    initiative_order = sorted(participants, key=lambda x: x.initiative, reverse=True)

    storage.update_game_state(
        in_combat=True,
        initiative_order=initiative_order,
        current_turn=initiative_order[0].name if initiative_order else None,
    )

    order_text = "\n".join(
        [f"{i + 1}. {p.name} (Initiative: {p.initiative})" for i, p in enumerate(initiative_order)]
    )

    return f"**Combat Started!**\n\n**Initiative Order:**\n{order_text}\n\n**Current Turn:** {initiative_order[0].name if initiative_order else 'None'}"


@tool_with_logging(mcp, tags=["mode:combat"])
def end_combat(
    result: Annotated[str, Field(description="Combat result (e.g., 'victory', 'defeat', 'fled')")],
    summary: Annotated[str, Field(description="Brief summary of how the combat ended")],
    casualties: Annotated[
        list[str] | None, Field(description="List of participants who died or were defeated")
    ] = None,
) -> str:
    """End the current combat encounter and record it in the transcript."""
    # Update game state
    storage.update_game_state(in_combat=False, initiative_order=[], current_turn=None)

    # End combat in transcript
    try:
        storage.end_transcript_combat(
            result=result,
            summary=summary,
            casualties=casualties
        )
        return f"Combat ended with result: {result}. Recorded in transcript."
    except Exception as e:
        # If transcript combat doesn't exist, just end combat in game state
        return f"Combat ended. (Note: {str(e)})"


# Adventure Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
async def complete_adventure(
    ctx: Context,
    title: Annotated[str, Field(description="Adventure title (e.g., 'The Temple of Doom')")],
    campaign_name: Annotated[
        str | None, Field(description="Campaign name (uses current campaign if None)")
    ] = None,
    session_number: Annotated[
        int | None, Field(description="Session number (uses current session if None)", ge=1)
    ] = None,
) -> str:
    """Complete an adventure by grouping all interactions since the last adventure into a new adventure node.

    This tool takes all interactions that have occurred since the last call to complete_adventure
    (or since the start of the transcript) and groups them under a new TranscriptAdventure node.
    The adventure node is placed at the same level in the transcript as the original interactions.
    """
    try:
        # Get ungrouped nodes
        nodes = storage.get_ungrouped_transcript_nodes(
            campaign_name=campaign_name,
            session_number=session_number
        )

        if not nodes:
            return "❌ No interactions to group into an adventure."

        # Strip tools and convert to JSON
        import json
        nodes_for_summary = _strip_tools_from_nodes(nodes)
        nodes_json = json.dumps(nodes_for_summary, indent=2)

        # Use sampling to generate a summary
        system_prompt = f"""You are summarizing a D&D adventure titled "{title}".

You will be given a set of interactions that occurred during this adventure (in JSON format).

Please provide a concise but comprehensive summary of what happened during this adventure. Focus on:
- Key events and story developments
- Important NPC interactions
- Combat encounters and their outcomes
- Treasure or items obtained
- Quest progress

Keep the summary to 2-3 paragraphs."""

        summary_result = await ctx.sample(
            messages = nodes_json,
            system_prompt = system_prompt,
            max_tokens=16000
        )

        # Extract text from response
        summary = summary_result.text

        # Complete the adventure with the generated summary
        adventure_node = storage.complete_transcript_adventure(
            title=title,
            summary=summary,
            campaign_name=campaign_name,
            session_number=session_number
        )
        action_count = len(adventure_node.actions)
        return f"✅ Completed adventure: '{adventure_node.title}' with {action_count} interaction(s). Recorded in transcript.\n\nSummary: {summary}"
    except Exception as e:
        return f"❌ Error completing adventure: {str(e)}"


@tool_with_logging(mcp, tags=["mode:combat"])
def next_turn() -> str:
    """Advance to the next turn in combat."""
    game_state = storage.get_game_state()
    if not game_state or not game_state.in_combat:
        return "Not currently in combat."

    if not game_state.initiative_order:
        return "No initiative order set."

    # Find current turn index and advance
    current_index = 0
    if game_state.current_turn:
        for i, participant in enumerate(game_state.initiative_order):
            if participant.name == game_state.current_turn:
                current_index = i
                break

    next_index = (current_index + 1) % len(game_state.initiative_order)
    next_participant = game_state.initiative_order[next_index]

    storage.update_game_state(current_turn=next_participant.name)

    return f"**Next Turn:** {next_participant.name}"


# Session Management Tools
@tool_with_logging(mcp, tags=["mode:setup"])
def add_session_note(
    session_number: Annotated[int, Field(description="Session number", ge=1)],
    summary: Annotated[str, Field(description="Session summary")],
    title: Annotated[str | None, Field(description="Session title")] = None,
    events: Annotated[list[str] | None, Field(description="Key events that occurred")] = None,
    characters_present: Annotated[
        list[str] | None, Field(description="Characters present in session")
    ] = None,
    experience_gained: Annotated[
        int | None, Field(description="Experience points gained", ge=0)
    ] = None,
    treasure_found: Annotated[
        list[str] | None, Field(description="Treasure or items found")
    ] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Add notes for a game session."""
    session_note = SessionNote(
        session_number=session_number,
        title=title,
        summary=summary,
        events=events or [],
        characters_present=characters_present or [],
        experience_gained=experience_gained,
        treasure_found=treasure_found or [],
        notes=notes,
    )

    storage.add_session_note(session_note)
    return f"Added session note for Session {session_note.session_number}"


@tool_with_logging(mcp, tags=["mode:setup"])
def get_sessions() -> str:
    """Get all session notes."""
    sessions = storage.get_sessions()
    if not sessions:
        return "No session notes recorded."

    session_list = []
    for session in sorted(sessions, key=lambda s: s.session_number):
        title = session.title or "No title"
        date = session.date.strftime("%Y-%m-%d")
        session_list.append(f"**Session {session.session_number}** ({date}): {title}")
        session_list.append(
            f"  {session.summary[:100]}{'...' if len(session.summary) > 100 else ''}"
        )
        session_list.append("")

    return "**Session Notes:**\n\n" + "\n".join(session_list)


# Adventure Log Tools
@tool_with_logging(mcp, tags=["mode:any"])
def add_event(
    event_type: Annotated[
        Literal["combat", "roleplay", "exploration", "quest", "character", "world", "session"],
        Field(description="Type of event"),
    ],
    title: Annotated[str, Field(description="Event title")],
    description: Annotated[str, Field(description="Event description")],
    session_number: Annotated[int | None, Field(description="Session number", ge=1)] = None,
    characters_involved: Annotated[
        list[str] | None, Field(description="Characters involved in the event")
    ] = None,
    location: Annotated[str | None, Field(description="Location where event occurred")] = None,
    importance: Annotated[int, Field(description="Event importance (1-5)", ge=1, le=5)] = 3,
    tags: Annotated[list[str] | None, Field(description="Tags for categorizing the event")] = None,
    campaign_name: Annotated[
        str | None, Field(description="Campaign name (uses current campaign if None)")
    ] = None,
) -> str:
    """Add an event to the adventure log."""
    if campaign_name is None:
        campaign = storage.get_current_campaign()
        if not campaign:
            raise ValueError("No active campaign. Please create or load a campaign first.")
        campaign_name = campaign.name
    else:
        # Validate that the specified campaign exists
        try:
            storage.get_campaign(campaign_name)
        except FileNotFoundError:
            raise ValueError(f"Campaign '{campaign_name}' not found.")

    event = AdventureEvent(
        campaign=campaign_name,
        event_type=EventType(event_type),
        title=title,
        description=description,
        session_number=session_number,
        characters_involved=characters_involved or [],
        location=location,
        importance=importance,
        tags=tags or [],
    )

    storage.add_event(event)
    return f"Added {event_type.lower()} event: '{event.title}'"


@tool_with_logging(mcp, tags=["mode:any"])
def get_events(
    limit: Annotated[
        int | None, Field(description="Maximum number of events to return", ge=1)
    ] = None,
    campaign: Annotated[str | None, "Get events by campaign name"] = None,
    event_type: Annotated[
        Literal["combat", "roleplay", "exploration", "quest", "character", "world", "session"]
        | None,
        Field(description="Filter by event type"),
    ] = None,
    search: Annotated[str | None, Field(description="Search events by title/description")] = None,
) -> str:
    """Get events from the adventure log."""
    if search:
        events = storage.search_events(search)
    else:
        events = storage.get_events(limit=limit, event_type=event_type, campaign=campaign)

    if not events:
        return "No events found."

    event_list = []
    for event in events:
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M")
        session_text = f" (Session {event.session_number})" if event.session_number else ""
        importance_stars = "★" * event.importance

        event_list.append(f"**{event.title}** [{event.event_type}] {importance_stars}")
        event_list.append(f"  {timestamp}{session_text}")
        event_list.append(
            f"  {event.description[:150]}{'...' if len(event.description) > 150 else ''}"
        )
        if event.location:
            event_list.append(f"  📍 {event.location}")
        event_list.append("")

    return "**Adventure Log:**\n\n" + "\n".join(event_list)


# Utility Tools
@tool_with_logging(mcp, tags=["mode:any"])
def roll_dice(
    dice_notation: Annotated[str, Field(description="Dice notation (e.g., '1d20', '3d6+2')")],
    advantage: Annotated[bool, Field(description="Roll with advantage")] = False,
    disadvantage: Annotated[bool, Field(description="Roll with disadvantage")] = False,
) -> str:
    """Roll dice with D&D notation."""
    dice_notation = dice_notation.lower().strip()

    # Parse dice notation (e.g., "1d20", "3d6+2", "2d8-1")
    pattern = r"(\d+)d(\d+)([+-]\d+)?"
    match = re.match(pattern, dice_notation)

    if not match:
        return f"Invalid dice notation: {dice_notation}"

    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    # Roll dice
    if advantage or disadvantage:
        if num_dice != 1 or die_size != 20:
            return "Advantage/disadvantage only applies to single d20 rolls"

        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)

        if advantage:
            result = max(roll1, roll2)
            roll_text = f"Advantage: {roll1}, {roll2} (taking {result})"
        else:
            result = min(roll1, roll2)
            roll_text = f"Disadvantage: {roll1}, {roll2} (taking {result})"

        total = result + modifier
        modifier_text = f" {modifier:+d}" if modifier != 0 else ""

        return f"🎲 **{dice_notation}** {roll_text}{modifier_text} = **{total}**"
    else:
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        roll_sum = sum(rolls)
        total = roll_sum + modifier

        rolls_text = ", ".join(map(str, rolls)) if num_dice > 1 else str(rolls[0])
        modifier_text = f" {modifier:+d}" if modifier != 0 else ""

        return f"🎲 **{dice_notation}** [{rolls_text}]{modifier_text} = **{total}**"


@tool_with_logging(mcp)
def calculate_experience(
    party_size: Annotated[int, Field(description="Number of party members", ge=1)],
    party_level: Annotated[int, Field(description="Average party level", ge=1, le=20)],
    encounter_xp: Annotated[int, Field(description="Total encounter XP value", ge=0)],
) -> str:
    """Calculate experience points for an encounter."""
    # D&D 5e encounter multipliers based on party size
    if party_size < 3:
        multiplier = 1.5
    elif party_size > 5:
        multiplier = 0.5
    else:
        multiplier = 1.0

    adjusted_xp = int(encounter_xp * multiplier)
    xp_per_player = adjusted_xp // party_size

    return f"""**Experience Calculation:**
Base Encounter XP: {encounter_xp}
Party Size Multiplier: {multiplier}x
Adjusted XP: {adjusted_xp}
**XP per Player: {xp_per_player}**"""


# Transcript tools and resources
@tool_with_logging(mcp)
def record_interaction(
    player_entry: Annotated[str, "Text input by the player"],
    game_response: Annotated[str, "Response send by the game"],
    campaign_name: Annotated[
        str | None,
        "Name of campaign to which this interaction applies, or none to use the current campaign",
    ] = None,
    session_number: Annotated[
        int | None,
        "Session number to which this interaction applies, or none to use the latest session",
        Field(description="Session number", ge=1),
    ] = None,
):
    storage.add_transcript_entry(player_entry, game_response, campaign_name, session_number)


@tool_with_logging(mcp)
def record_interaction_with_tools(
    player_entry: Annotated[str, Field(description="Text input by the player")],
    game_responses: Annotated[
        list[str | list[dict[str, Any]]],
        Field(description="List of responses. Each entry is either a text string or a list of tool call dicts. Tool call dicts have: tool_name (str), tool_id (str), tool_parameters (dict), tool_result (str)")
    ],
    campaign_name: Annotated[
        str | None,
        Field(description="Name of campaign to which this interaction applies, or none to use the current campaign")
    ] = None,
    session_number: Annotated[
        int | None,
        Field(description="Session number to which this interaction applies, or none to use the latest session", ge=1)
    ] = None,
) -> str:
    """Record a player-game interaction with tool calls in the transcript.

    This function supports recording interactions that include both text responses and tool calls.
    Use this instead of record_interaction when the LLM's response included tool calls.

    Args:
        player_entry: Text input by the player
        game_responses: List where each entry is either:
            - A string (text response)
            - A list of dicts (tool calls), where each dict has:
                - tool_name (str): Name of the tool called
                - tool_id (str): Unique ID for the tool call
                - tool_parameters (dict): Parameters passed to the tool
                - tool_result (str): Result returned by the tool
        campaign_name: Optional campaign name (uses current if None)
        session_number: Optional session number (uses latest if None)

    Example:
        record_interaction_with_tools(
            player_entry="I attack the goblin",
            game_responses=[
                "Let me roll for your attack...",
                [
                    {
                        "tool_name": "roll_dice",
                        "tool_id": "call_123",
                        "tool_parameters": {"dice_notation": "1d20+5"},
                        "tool_result": "🎲 1d20+5 [18] +5 = 23"
                    }
                ],
                "You hit! Roll for damage..."
            ]
        )
    """
    # Convert the responses into the format expected by storage layer (list of dicts)
    responses = []
    for response in game_responses:
        if isinstance(response, str):
            # Text response
            responses.append({
                "type": "text",
                "content": response
            })
        elif isinstance(response, list):
            # Tool calls
            tool_calls = []
            for tool_call in response:
                tool_calls.append({
                    "name": tool_call["tool_name"],
                    "id": tool_call["tool_id"],
                    "input": tool_call["tool_parameters"],
                    "response": tool_call["tool_result"]
                })
            responses.append({
                "type": "tools",
                "calls": tool_calls
            })
        else:
            raise ValueError(f"Invalid response type: {type(response)}. Must be str or list[dict]")

    # Add to transcript using the storage layer
    storage.add_transcript_interaction(
        user_text=player_entry,
        responses=responses,
        campaign_name=campaign_name,
        session_number=session_number
    )

    return f"Recorded interaction with {len(responses)} response(s) to transcript"


# ========================================
# Hex Mapping Tools
# ========================================

# Helper function for resolving map name
def resolve_map_name(map_name: str | None) -> str:
    """Resolve map name to current map if None, otherwise return provided name.

    Raises ValueError if no map name provided and no current map available.
    """
    if map_name is None:
        current_map = storage.get_current_map_name()
        if not current_map:
            raise ValueError(
                "No map name provided and no current map available. "
                "Either specify a map name or set the current location to a location with a map."
            )
        return current_map
    return map_name


# Map Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def create_hex_map(
    name: Annotated[str, Field(description="Name of the hex map")],
    description: Annotated[str, Field(description="Description of the region this map represents")],
    hex_diameter_km: Annotated[float, Field(description="Diameter of each hex in km")] = 10.0,
    default_terrain: Annotated[TerrainType, Field(description="Default terrain type")] = TerrainType.GRASS,
) -> str:
    """Create a new hex map for outdoor wilderness areas."""
    hex_map = HexMap(
        name=name,
        description=description,
        hex_diameter_km=hex_diameter_km,
        default_terrain=default_terrain
    )

    storage.add_hex_map(hex_map)
    return f"Created hex map '{name}' with {hex_diameter_km}km hexes. Default terrain: {default_terrain.value}"


@tool_with_logging(mcp, tags=["mode:any"])
def list_hex_maps() -> str:
    """List all hex maps in the current campaign."""
    map_names = storage.list_hex_maps()
    if not map_names:
        return "No hex maps found in the current campaign."

    result = "Hex maps in campaign:\n"
    for map_name in map_names:
        hex_map = storage.get_hex_map(map_name)
        if hex_map:
            hex_count = len(hex_map.hexes)
            result += f"- {map_name}: {hex_count} hexes, {hex_map.hex_diameter_km}km per hex\n"

    return result.rstrip()


@tool_with_logging(mcp, tags=["mode:setup"])
def delete_hex_map(
    map_name: Annotated[str, Field(description="Name of the map to delete")],
) -> str:
    """Delete a hex map from the campaign."""
    storage.delete_hex_map(map_name)
    return f"Deleted hex map '{map_name}'"


# Basic Hex Manipulation Tools
@tool_with_logging(mcp, tags=["mode:any"])
def add_or_update_hex(
    x: Annotated[int, Field(description="X coordinate (column, 0=leftmost)")],
    y: Annotated[int, Field(description="Y coordinate (row, 0=topmost)")],
    terrain: Annotated[TerrainType, Field(description="Terrain type for this hex")],
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
    explored: Annotated[bool, Field(description="Whether party has explored this hex")] = False,
    elevation: Annotated[int | None, Field(description="Elevation in meters")] = None,
    notes: Annotated[str | None, Field(description="Notes about this hex")] = None,
) -> str:
    """Add or update a hex on the map. Uses current map if map_name not provided."""
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    coord = HexCoordinate(x=x, y=y)
    hex_obj = Hex(
        coordinate=coord,
        terrain=terrain,
        explored=explored,
        elevation=elevation,
        notes=notes or ""
    )

    hex_map.set_hex(hex_obj)
    storage.add_hex_map(hex_map)  # Save changes

    return f"Set hex [{x},{y}] to {terrain.value} terrain" + (f" (elevation: {elevation}m)" if elevation else "")


@tool_with_logging(mcp, tags=["mode:any"])
def get_hex_info(
    x: Annotated[int, Field(description="X coordinate (column)")],
    y: Annotated[int, Field(description="Y coordinate (row)")],
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
) -> str:
    """Get detailed information about a specific hex. Uses current map if map_name not provided."""
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    coord = HexCoordinate(x=x, y=y)
    hex_obj = hex_map.get_hex(coord)

    if not hex_obj:
        return f"No hex found at [{x},{y}] on map '{map_name}'"

    result = f"Hex [{x},{y}] on map '{map_name}':\n"
    result += f"- Terrain: {hex_obj.terrain.value}\n"
    result += f"- Explored: {'Yes' if hex_obj.explored else 'No'}\n"

    if hex_obj.elevation is not None:
        result += f"- Elevation: {hex_obj.elevation}m\n"

    if hex_obj.roads:
        result += f"- Roads: {len(hex_obj.roads)} road(s)\n"
    if hex_obj.rivers:
        result += f"- Rivers: {len(hex_obj.rivers)} river(s)\n"
    if hex_obj.pois:
        result += f"- Points of Interest: {len(hex_obj.pois)}\n"
        for poi in hex_obj.pois:
            result += f"  - {poi.name} ({poi.poi_type.value})" + (" [discovered]" if poi.discovered else " [undiscovered]") + "\n"

    if hex_obj.notes:
        result += f"- Notes: {hex_obj.notes}\n"

    return result.rstrip()


@tool_with_logging(mcp, tags=["mode:any"])
def mark_hex_explored(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    x: Annotated[int, Field(description="X coordinate (column)")],
    y: Annotated[int, Field(description="Y coordinate (row)")],
) -> str:
    """Mark a hex as explored by the party."""
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    coord = HexCoordinate(x=x, y=y)
    hex_obj = hex_map.get_hex(coord)

    if not hex_obj:
        return f"No hex found at [{x},{y}] on map '{map_name}'"

    hex_obj.explored = True
    hex_map.set_hex(hex_obj)
    storage.add_hex_map(hex_map)

    return f"Marked hex [{x},{y}] as explored"


# Bulk Terrain Tools
@tool_with_logging(mcp, tags=["mode:setup"])
def fill_rectangular_region(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    min_x: Annotated[int, Field(description="Minimum X coordinate (inclusive)")],
    min_y: Annotated[int, Field(description="Minimum Y coordinate (inclusive)")],
    max_x: Annotated[int, Field(description="Maximum X coordinate (inclusive)")],
    max_y: Annotated[int, Field(description="Maximum Y coordinate (inclusive)")],
    terrain: Annotated[TerrainType, Field(description="Terrain type to fill")],
) -> str:
    """Fill a rectangular region with a specific terrain type.

    Useful for quickly initializing a map with a base terrain or making large-scale changes.
    Creates hexes at all coordinates within the specified bounds.
    """
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    count = 0
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            coord = HexCoordinate(x=x, y=y)
            hex_obj = Hex(coordinate=coord, terrain=terrain)
            hex_map.set_hex(hex_obj)
            count += 1

    storage.add_hex_map(hex_map)
    return f"Filled region [{min_x},{min_y}] to [{max_x},{max_y}] with {terrain.value} ({count} hexes)"


@tool_with_logging(mcp, tags=["mode:setup"])
def generate_terrain_region(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    center_x: Annotated[int, Field(description="Center X coordinate (column)")],
    center_y: Annotated[int, Field(description="Center Y coordinate (row)")],
    radius: Annotated[int, Field(description="Radius of the region in hexes")],
    terrain: Annotated[TerrainType, Field(description="Terrain type to fill")],
) -> str:
    """Fill a circular region with a specific terrain type.

    Useful for creating natural features like forests, hills, or lakes. Uses hex distance
    calculation to create a circular pattern.
    """
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    center = HexCoordinate(x=center_x, y=center_y)
    count = 0

    # Search in a rectangular area and filter by distance
    for x in range(center_x - radius, center_x + radius + 1):
        for y in range(center_y - radius, center_y + radius + 1):
            coord = HexCoordinate(x=x, y=y)
            if center.distance_to(coord) <= radius:
                hex_obj = Hex(coordinate=coord, terrain=terrain)
                hex_map.set_hex(hex_obj)
                count += 1

    storage.add_hex_map(hex_map)
    return f"Generated {terrain.value} region centered at [{center_x},{center_y}] with radius {radius} ({count} hexes)"


@tool_with_logging(mcp, tags=["mode:any"])
def import_terrain_from_ascii(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    ascii_map: Annotated[str, Field(description="ASCII representation of the map. Each character represents one hex. Odd rows (1,3,5...) should start with a space to show hex offset.")],
    legend: Annotated[dict[str, str], Field(description="Mapping of ASCII characters to terrain type names. Example: {'G': 'grass', 'F': 'light_forest', 'M': 'mountains'}")],
    start_x: Annotated[int, Field(description="X coordinate for the top-left hex")] = 0,
    start_y: Annotated[int, Field(description="Y coordinate for the top-left hex")] = 0,
) -> str:
    """Import terrain from an ASCII map representation.

    This is the most efficient way to create large maps. Each character in the ASCII map
    represents one hex's terrain type. Rows are separated by newlines. Odd-numbered rows
    should be indented with a space to represent the hex offset.

    Example:
        ascii_map = '''
        G G F F M
         G F F H M
        G F F H H
         W G F H M
        '''
        legend = {
            'G': 'grass',
            'F': 'light_forest',
            'M': 'mountains',
            'H': 'hills',
            'W': 'water'
        }
    """
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    lines = ascii_map.strip().split('\n')
    hex_count = 0

    for row_idx, line in enumerate(lines):
        y = start_y + row_idx

        # Check if this is an odd row (starts with space)
        is_offset_row = line.startswith(' ')
        if is_offset_row:
            line = line[1:]  # Remove leading space

        # Split by spaces to get individual hex characters
        chars = line.split()

        for col_idx, char in enumerate(chars):
            if char in legend:
                # Calculate x coordinate with standard consecutive numbering
                # For odd-q offset coordinates (pointy-top hexes):
                # - Even rows (y=0,2,4...): hexes at x = 0,1,2,3...
                # - Odd rows (y=1,3,5...): hexes at x = 0,1,2,3... (visually offset)
                x = start_x + col_idx
                terrain_name = legend[char]

                try:
                    terrain = TerrainType(terrain_name)
                    coord = HexCoordinate(x=x, y=y)
                    hex_obj = Hex(coordinate=coord, terrain=terrain)
                    hex_map.set_hex(hex_obj)
                    hex_count += 1
                except ValueError:
                    # Invalid terrain type, skip
                    pass

    storage.add_hex_map(hex_map)
    return f"Imported {hex_count} hexes from ASCII map into '{map_name}'"


# Point of Interest Tools
@tool_with_logging(mcp, tags=["mode:any"])
def add_poi_to_hex(
    x: Annotated[int, Field(description="X coordinate (column)")],
    y: Annotated[int, Field(description="Y coordinate (row)")],
    name: Annotated[str, Field(description="Name of the point of interest")],
    poi_type: Annotated[POIType, Field(description="Type of POI")],
    description: Annotated[str, Field(description="Description of the POI")],
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
    location_id: Annotated[str | None, Field(description="ID of associated Location object")] = None,
    discovered: Annotated[bool, Field(description="Has the party discovered this?")] = False,
    position: Annotated[str, Field(description="Position within hex: 'center', 'north', 'northeast', 'southeast', 'south', 'southwest', 'northwest'")] = "center",
) -> str:
    """Add a point of interest to a hex. Uses current map if map_name not provided.

    The position indicates where in the hex the POI is located. Use 'center' for most
    POIs (towns, dungeons at hex center), or a specific side for POIs at hex edges
    (e.g., a tower on the northern edge).
    """
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    coord = HexCoordinate(x=x, y=y)
    hex_obj = hex_map.get_hex(coord)

    if not hex_obj:
        return f"No hex found at [{x},{y}]. Create the hex first using add_or_update_hex."

    # Create POI
    poi = PointOfInterest(
        name=name,
        poi_type=poi_type,
        description=description,
        location_id=location_id,
        discovered=discovered,
        position=HexSide(position)
    )

    hex_obj.pois.append(poi)
    hex_map.set_hex(hex_obj)
    storage.add_hex_map(hex_map)

    return f"Added {poi_type.value} '{name}' to hex [{x},{y}] at position {position}"


@tool_with_logging(mcp, tags=["mode:any"])
def remove_poi_from_hex(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    poi_id: Annotated[str, Field(description="ID of the POI to remove")],
) -> str:
    """Remove a point of interest from the map."""
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    # Search all hexes for the POI
    for hex_obj in hex_map.hexes.values():
        for poi in hex_obj.pois:
            if poi.id == poi_id:
                hex_obj.pois.remove(poi)
                hex_map.set_hex(hex_obj)
                storage.add_hex_map(hex_map)
                return f"Removed POI '{poi.name}' from hex [{hex_obj.coordinate.x},{hex_obj.coordinate.y}]"

    return f"POI with ID '{poi_id}' not found on map '{map_name}'"


@tool_with_logging(mcp, tags=["mode:any"])
def mark_poi_discovered(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    poi_id: Annotated[str, Field(description="ID of the POI")],
) -> str:
    """Mark a POI as discovered by the party."""
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    # Search all hexes for the POI
    for hex_obj in hex_map.hexes.values():
        for poi in hex_obj.pois:
            if poi.id == poi_id:
                poi.discovered = True
                hex_map.set_hex(hex_obj)
                storage.add_hex_map(hex_map)
                return f"Marked POI '{poi.name}' as discovered"

    return f"POI with ID '{poi_id}' not found on map '{map_name}'"


@tool_with_logging(mcp, tags=["mode:any"])
def list_pois_on_map(
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
    discovered_only: Annotated[bool, Field(description="Only show discovered POIs")] = False,
    poi_type: Annotated[POIType | None, Field(description="Filter by POI type")] = None,
) -> str:
    """List all points of interest on a map."""
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    pois = []
    for hex_obj in hex_map.hexes.values():
        for poi in hex_obj.pois:
            # Apply filters
            if discovered_only and not poi.discovered:
                continue
            if poi_type and poi.poi_type != poi_type:
                continue

            pois.append((hex_obj.coordinate, poi))

    if not pois:
        return "No POIs found matching the criteria."

    result = f"Points of Interest on '{map_name}':\n"
    for coord, poi in pois:
        status = "[discovered]" if poi.discovered else "[undiscovered]"
        result += f"- {poi.name} ({poi.poi_type.value}) at [{coord.x},{coord.y}] {status}\n"
        result += f"  {poi.description}\n"

    return result.rstrip()


# Navigation and Exploration Tools
@tool_with_logging(mcp, tags=["mode:any"])
def get_neighboring_hexes(
    x: Annotated[int, Field(description="X coordinate of center hex (column)")],
    y: Annotated[int, Field(description="Y coordinate of center hex (row)")],
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
) -> str:
    """Get information about all hexes adjacent to the specified hex."""
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    coord = HexCoordinate(x=x, y=y)
    neighbors = hex_map.get_neighbors(coord)

    result = f"Neighbors of hex [{x},{y}]:\n"
    for direction, neighbor_hex in neighbors.items():
        if neighbor_hex:
            result += f"- {direction.value}: {neighbor_hex.terrain.value}"
            if neighbor_hex.pois:
                result += f" (POIs: {', '.join([poi.name for poi in neighbor_hex.pois])})"
            result += "\n"
        else:
            result += f"- {direction.value}: (no hex)\n"

    return result.rstrip()


@tool_with_logging(mcp, tags=["mode:any"])
def render_hex_map(
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
    render_mode: Annotated[
        Literal["json", "ascii", "emoji"],
        Field(description="Rendering mode: 'json' for structured data, 'ascii' for text map, 'emoji' for visual display")
    ] = "emoji",
    center_x: Annotated[int | None, Field(description="X coordinate to center the view (optional, shows all if not provided)")] = None,
    center_y: Annotated[int | None, Field(description="Y coordinate to center the view (optional, shows all if not provided)")] = None,
    radius: Annotated[int | None, Field(description="Radius in hexes around center point (only used with center_x/y)", ge=1)] = None,
) -> str:
    """Renders a hex map in the specified format for display or export.

    Supports three render modes:
    - json: Returns structured JSON data suitable for external renderers
    - ascii: Returns text-based map using terrain code letters (same format as map creation)
    - emoji: Returns visually appealing ASCII art with emojis representing terrain
    """
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    # Define terrain character mappings for ASCII mode
    terrain_codes = {
        TerrainType.PLAINS: 'P',
        TerrainType.FOREST: 'F',
        TerrainType.LIGHT_FOREST: 'F',
        TerrainType.DENSE_FOREST: 'F',
        TerrainType.HILLS: 'H',
        TerrainType.MOUNTAINS: 'M',
        TerrainType.SWAMP: 'S',
        TerrainType.DESERT: 'D',
        TerrainType.TUNDRA: 'T',
        TerrainType.WATER: 'W',
        TerrainType.URBAN: 'U',
        TerrainType.COASTAL: 'C',
        TerrainType.JUNGLE: 'J',
        TerrainType.VOLCANIC: 'V',
        TerrainType.WASTELAND: 'X',
        TerrainType.FARMLAND: 'A',
    }

    # Define terrain emoji mappings for emoji mode
    terrain_emojis = {
        TerrainType.PLAINS: '🟢',
        TerrainType.FOREST: '🌲',
        TerrainType.LIGHT_FOREST: '🌲',
        TerrainType.DENSE_FOREST: '🌲',
        TerrainType.HILLS: '⛰️',
        TerrainType.MOUNTAINS: '🏔️',
        TerrainType.SWAMP: '🌿',
        TerrainType.DESERT: '🏜️',
        TerrainType.TUNDRA: '❄️',
        TerrainType.WATER: '🌊',
        TerrainType.URBAN: '🏙️',
        TerrainType.COASTAL: '🏖️',
        TerrainType.JUNGLE: '🌴',
        TerrainType.VOLCANIC: '🌋',
        TerrainType.WASTELAND: '💀',
        TerrainType.FARMLAND: '🌾',
    }

    # Determine which hexes to render
    if center_x is not None and center_y is not None and radius is not None:
        # Render only hexes within radius of center
        center_coord = HexCoordinate(x=center_x, y=center_y)
        hexes_to_render = {}
        for coord_str, hex_obj in hex_map.hexes.items():
            distance = hex_obj.coordinate.distance_to(center_coord)
            if distance <= radius:
                hexes_to_render[coord_str] = hex_obj
    else:
        # Render all hexes
        hexes_to_render = hex_map.hexes

    if not hexes_to_render:
        return f"No hexes to render in map '{map_name}'"

    # Find bounds and create coordinate normalization mapping
    all_coords = [hex_obj.coordinate for hex_obj in hexes_to_render.values()]
    min_x = min(coord.x for coord in all_coords)
    max_x = max(coord.x for coord in all_coords)
    min_y = min(coord.y for coord in all_coords)
    max_y = max(coord.y for coord in all_coords)

    # Create mappings for coordinate normalization (handles non-consecutive coordinates)
    # Collect all unique x and y values, sort them, and map to consecutive integers
    unique_x = sorted(set(coord.x for coord in all_coords))
    unique_y = sorted(set(coord.y for coord in all_coords))
    x_map = {actual: normalized for normalized, actual in enumerate(unique_x)}
    y_map = {actual: normalized for normalized, actual in enumerate(unique_y)}

    if render_mode == "json":
        # JSON mode: return structured data with normalized coordinates
        import json
        json_data = {
            "map_name": hex_map.name,
            "description": hex_map.description,
            "hex_diameter_km": hex_map.hex_diameter_km,
            "default_terrain": hex_map.default_terrain.value,
            "bounds": {
                "min_x": 0,
                "max_x": len(unique_x) - 1,
                "min_y": 0,
                "max_y": len(unique_y) - 1
            },
            "hexes": [
                {
                    "x": x_map[hex_obj.coordinate.x],  # Normalized x (top-level)
                    "y": y_map[hex_obj.coordinate.y],  # Normalized y (top-level)
                    "coordinate": {  # Also provide nested coordinate object
                        "x": x_map[hex_obj.coordinate.x],
                        "y": y_map[hex_obj.coordinate.y]
                    },
                    "terrain": hex_obj.terrain.value,
                    "explored": hex_obj.explored,
                    "elevation": hex_obj.elevation,
                    "notes": hex_obj.notes,
                    "pois": [
                        {
                            "id": poi.id,
                            "name": poi.name,
                            "type": poi.poi_type.value,
                            "description": poi.description,
                            "discovered": poi.discovered,
                            "location_id": poi.location_id
                        }
                        for poi in hex_obj.pois
                    ],
                    "roads": [],
                    "rivers": []
                }
                for hex_obj in hexes_to_render.values()
            ]
        }
        return json.dumps(json_data, indent=2)

    elif render_mode == "ascii":
        # ASCII mode: text-based using terrain codes
        result = f"**Hex Map: {hex_map.name}**\n"
        if hex_map.description:
            result += f"{hex_map.description}\n"
        result += f"Scale: {hex_map.hex_diameter_km} km per hex\n\n"

        # Build legend
        result += "**Terrain Legend:**\n"
        terrain_set = set(hex_obj.terrain for hex_obj in hexes_to_render.values())
        for terrain in sorted(terrain_set, key=lambda t: t.value):
            code = terrain_codes.get(terrain, '?')
            result += f"  {code} = {terrain.value}\n"
        result += "\n"

        # Build ASCII map
        for y in range(min_y, max_y + 1):
            line = ""
            # Odd rows (y is odd) are offset with a leading space
            is_offset_row = (y % 2 == 1)
            if is_offset_row:
                line += " "

            for x in range(min_x, max_x + 1, 2):
                # For offset rows, we shift x by 1
                actual_x = x + (1 if is_offset_row else 0)
                coord = HexCoordinate(x=actual_x, y=y)
                hex_obj = hex_map.get_hex(coord)

                if hex_obj:
                    code = terrain_codes.get(hex_obj.terrain, '?')
                    # Mark POIs with asterisk
                    if hex_obj.pois:
                        code = code + '*'
                    line += code + " "
                else:
                    line += "  "

            result += line.rstrip() + "\n"

        # Add POI list
        pois_in_view = []
        for hex_obj in hexes_to_render.values():
            for poi in hex_obj.pois:
                pois_in_view.append((hex_obj.coordinate, poi))

        if pois_in_view:
            result += "\n**Points of Interest:**\n"
            for coord, poi in pois_in_view:
                discovered = "✓" if poi.discovered else "?"
                result += f"  [{coord.x},{coord.y}] {poi.name} ({poi.poi_type.value}) {discovered}\n"

        return result

    else:  # emoji mode
        # Emoji mode: visual display with emojis
        result = f"**🗺️ {hex_map.name}**\n"
        if hex_map.description:
            result += f"_{hex_map.description}_\n"
        result += f"📏 Scale: {hex_map.hex_diameter_km} km per hex\n\n"

        # Build emoji map
        for y in range(min_y, max_y + 1):
            line = ""
            # Odd rows (y is odd) are offset
            is_offset_row = (y % 2 == 1)
            if is_offset_row:
                line += "  "  # Double space for emoji offset

            for x in range(min_x, max_x + 1, 2):
                actual_x = x + (1 if is_offset_row else 0)
                coord = HexCoordinate(x=actual_x, y=y)
                hex_obj = hex_map.get_hex(coord)

                if hex_obj:
                    emoji = terrain_emojis.get(hex_obj.terrain, '⬡')
                    # Overlay POI marker
                    if hex_obj.pois:
                        # Show number of POIs
                        if len(hex_obj.pois) == 1:
                            emoji = '📍'
                        else:
                            emoji = f'{len(hex_obj.pois)}📍'
                    line += emoji + " "
                else:
                    line += "⬡ "  # Empty hex

            result += line.rstrip() + "\n"

        # Add legend
        result += "\n**🎨 Terrain Legend:**\n"
        terrain_set = set(hex_obj.terrain for hex_obj in hexes_to_render.values())
        for terrain in sorted(terrain_set, key=lambda t: t.value):
            emoji = terrain_emojis.get(terrain, '⬡')
            result += f"  {emoji} = {terrain.value}\n"

        # Add POI list
        pois_in_view = []
        for hex_obj in hexes_to_render.values():
            for poi in hex_obj.pois:
                pois_in_view.append((hex_obj.coordinate, poi))

        if pois_in_view:
            result += "\n**📍 Points of Interest:**\n"
            for coord, poi in sorted(pois_in_view, key=lambda x: (x[0].y, x[0].x)):
                discovered_icon = "✓" if poi.discovered else "❓"
                poi_emoji = terrain_emojis.get(TerrainType.URBAN, '🏛️')
                if poi.poi_type == POIType.CITY:
                    poi_emoji = '🏙️'
                elif poi.poi_type == POIType.TOWN:
                    poi_emoji = '🏘️'
                elif poi.poi_type == POIType.VILLAGE:
                    poi_emoji = '🏡'
                elif poi.poi_type == POIType.DUNGEON:
                    poi_emoji = '⚔️'
                elif poi.poi_type == POIType.RUINS:
                    poi_emoji = '🏚️'
                elif poi.poi_type == POIType.CASTLE:
                    poi_emoji = '🗼'
                elif poi.poi_type == POIType.TEMPLE:
                    poi_emoji = '⛩️'
                elif poi.poi_type == POIType.TOWER:
                    poi_emoji = '🗼'
                elif poi.poi_type == POIType.CAVE:
                    poi_emoji = '🕳️'
                elif poi.poi_type == POIType.INN:
                    poi_emoji = '🍺'
                elif poi.poi_type == POIType.CAMP:
                    poi_emoji = '🏡'
                elif poi.poi_type == POIType.SHRINE:
                    poi_emoji = '⛩️'
                elif poi.poi_type == POIType.LANDMARK:
                    poi_emoji = '🗿'

                result += f"  [{coord.x:2},{coord.y:2}] {poi_emoji} **{poi.name}** ({poi.poi_type.value}) {discovered_icon}\n"

        # Add roads if any intersect view
        '''
        roads_in_view = []
        for road in hex_map.roads:
            for coord in road.path:
                if coord.x >= min_x and coord.x <= max_x and coord.y >= min_y and coord.y <= max_y:
                    roads_in_view.append(road)
                    break

        if roads_in_view:
            result += "\n**🛤️ Roads:**\n"
            for road in roads_in_view:
                road_emoji = "🛣️" if road.road_type == "highway" else "🛤️" if road.road_type == "road" else "🥾"
                name = road.name or "Unnamed road"
                result += f"  {road_emoji} {name} ({road.road_type}, {len(road.path)} hexes)\n"
        '''

        # Add rivers if any intersect view
        '''
        rivers_in_view = []
        for river in hex_map.rivers:
            for seg in river.path:
                coord = seg["hex"]
                if coord.x >= min_x and coord.x <= max_x and coord.y >= min_y and coord.y <= max_y:
                    rivers_in_view.append(river)
                    break

        if rivers_in_view:
            result += "\n**💧 Rivers:**\n"
            for river in rivers_in_view:
                name = river.name or "Unnamed river"
                result += f"  🌊 {name} ({river.river_width}, {len(river.path)} segments)\n"
        '''

        return result


@tool_with_logging(mcp, tags=["mode:any"])
def calculate_distance(
    from_x: Annotated[int, Field(description="Starting X coordinate (column)")],
    from_y: Annotated[int, Field(description="Starting Y coordinate (row)")],
    to_x: Annotated[int, Field(description="Destination X coordinate (column)")],
    to_y: Annotated[int, Field(description="Destination Y coordinate (row)")],
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
) -> str:
    """Calculate the distance in hexes and kilometers between two points."""
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    from_coord = HexCoordinate(x=from_x, y=from_y)
    to_coord = HexCoordinate(x=to_x, y=to_y)

    hex_distance = from_coord.distance_to(to_coord)
    km_distance = hex_distance * hex_map.hex_diameter_km

    return f"Distance from [{from_x},{from_y}] to [{to_x},{to_y}]: {hex_distance} hexes ({km_distance:.1f} km)"


@tool_with_logging(mcp, tags=["mode:any"])
def describe_area(
    center_x: Annotated[int, Field(description="X coordinate of center (column)")],
    center_y: Annotated[int, Field(description="Y coordinate of center (row)")],
    radius: Annotated[int, Field(description="Radius in hexes")] = 1,
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
) -> str:
    """Describe an area of the map centered on a specific hex."""
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    center = HexCoordinate(x=center_x, y=center_y)
    result = f"Area around [{center_x},{center_y}] (radius {radius} hexes):\n\n"

    # Get all hexes in range
    hexes_in_range = []
    for x in range(center_x - radius, center_x + radius + 1):
        for y in range(center_y - radius, center_y + radius + 1):
            coord = HexCoordinate(x=x, y=y)
            if center.distance_to(coord) <= radius:
                hex_obj = hex_map.get_hex(coord)
                if hex_obj:
                    hexes_in_range.append(hex_obj)

    if not hexes_in_range:
        return "No hexes found in this area."

    # Summarize terrain
    terrain_counts: dict[str, int] = {}
    for hex_obj in hexes_in_range:
        terrain_name = hex_obj.terrain.value
        terrain_counts[terrain_name] = terrain_counts.get(terrain_name, 0) + 1

    result += "Terrain:\n"
    for terrain, count in sorted(terrain_counts.items(), key=lambda x: x[1], reverse=True):
        result += f"- {terrain}: {count} hexes\n"

    # List POIs
    pois_found = []
    for hex_obj in hexes_in_range:
        for poi in hex_obj.pois:
            if poi.discovered:
                pois_found.append((hex_obj.coordinate, poi))

    if pois_found:
        result += "\nPoints of Interest:\n"
        for coord, poi in pois_found:
            result += f"- {poi.name} ({poi.poi_type.value}) at [{coord.x},{coord.y}]\n"

    return result.rstrip()


# Helper function for roads and rivers
def _get_direction_between_hexes(from_hex: HexCoordinate, to_hex: HexCoordinate) -> HexSide | None:
    """Determine which side of from_hex leads to to_hex."""
    # Get neighbor offsets for the from_hex
    if from_hex.x % 2 == 0:
        # Even column offsets
        offsets = {
            HexSide.NORTH: (0, -1),
            HexSide.NORTHEAST: (1, -1),
            HexSide.SOUTHEAST: (1, 0),
            HexSide.SOUTH: (0, 1),
            HexSide.SOUTHWEST: (-1, 0),
            HexSide.NORTHWEST: (-1, -1)
        }
    else:
        # Odd column offsets
        offsets = {
            HexSide.NORTH: (0, -1),
            HexSide.NORTHEAST: (1, 0),
            HexSide.SOUTHEAST: (1, 1),
            HexSide.SOUTH: (0, 1),
            HexSide.SOUTHWEST: (-1, 1),
            HexSide.NORTHWEST: (-1, 0)
        }

    dx = to_hex.x - from_hex.x
    dy = to_hex.y - from_hex.y

    for direction, (offset_x, offset_y) in offsets.items():
        if dx == offset_x and dy == offset_y:
            return direction

    return None  # Not adjacent


# Road and River Tools
@tool_with_logging(mcp, tags=["mode:any"])
def add_road(
    path: Annotated[list[tuple[int, int]], Field(description="List of (x, y) coordinates the road passes through, in order from start to end")],
    road_type: Annotated[str, Field(description="Type of road (e.g., 'highway', 'road', 'path', 'trail')")] = "road",
    condition: Annotated[str, Field(description="Road condition (e.g., 'well-maintained', 'fair', 'poor', 'overgrown')")] = "fair",
    start_point: Annotated[str, Field(description="Where the road starts in the first hex: 'center', 'north', 'northeast', 'southeast', 'south', 'southwest', or 'northwest'")] = "center",
    end_point: Annotated[str, Field(description="Where the road ends in the last hex: 'center', 'north', 'northeast', 'southeast', 'south', 'southwest', or 'northwest'")] = "center",
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
) -> str:
    """Add a road that follows a path through multiple hexes.

    The tool automatically calculates which sides the road enters and exits for each hex
    based on the sequence of coordinates. Each consecutive pair of hexes must be adjacent.

    The start_point defines where the road begins in the first hex (defaults to 'center',
    e.g., a town). The end_point defines where the road ends in the last hex.
    """
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    if len(path) < 2:
        return "Road path must contain at least 2 hexes"

    # Convert start/end points to HexSide
    start_side = None if start_point == "center" else HexSide(start_point)
    end_side = None if end_point == "center" else HexSide(end_point)

    roads_added = 0

    for i in range(len(path)):
        x, y = path[i]
        coord = HexCoordinate(x=x, y=y)
        hex_obj = hex_map.get_hex(coord)

        if not hex_obj:
            return f"No hex found at [{x},{y}]. Create all hexes in the path first."

        # Determine entry and exit points for this hex
        if i == 0:
            # First hex
            entry = start_side
            if len(path) > 1:
                next_coord = HexCoordinate(x=path[1][0], y=path[1][1])
                exit_dir = _get_direction_between_hexes(coord, next_coord)
                if exit_dir is None:
                    return f"Hexes at [{x},{y}] and [{path[1][0]},{path[1][1]}] are not adjacent"
            else:
                exit_dir = end_side
        elif i == len(path) - 1:
            # Last hex
            prev_coord = HexCoordinate(x=path[i-1][0], y=path[i-1][1])
            entry_dir = _get_direction_between_hexes(prev_coord, coord)
            if entry_dir is None:
                return f"Hexes at [{path[i-1][0]},{path[i-1][1]}] and [{x},{y}] are not adjacent"
            entry = entry_dir
            exit_dir = end_side
        else:
            # Middle hex
            prev_coord = HexCoordinate(x=path[i-1][0], y=path[i-1][1])
            next_coord = HexCoordinate(x=path[i+1][0], y=path[i+1][1])

            entry_dir = _get_direction_between_hexes(prev_coord, coord)
            exit_dir = _get_direction_between_hexes(coord, next_coord)

            if entry_dir is None:
                return f"Hexes at [{path[i-1][0]},{path[i-1][1]}] and [{x},{y}] are not adjacent"
            if exit_dir is None:
                return f"Hexes at [{x},{y}] and [{path[i+1][0]},{path[i+1][1]}] are not adjacent"

            entry = entry_dir

        # Create road segment
        road = Road(
            start_point=entry,
            end_point=exit_dir,
            road_type=road_type,
            condition=condition
        )

        hex_obj.roads.append(road)
        hex_map.set_hex(hex_obj)
        roads_added += 1

    storage.add_hex_map(hex_map)
    return f"Added {road_type} through {roads_added} hexes (condition: {condition})"


@tool_with_logging(mcp, tags=["mode:any"])
def add_river(
    path: Annotated[list[tuple[int, int]], Field(description="List of (x, y) coordinates the river flows through, from source to mouth")],
    width: Annotated[str, Field(description="River width category (e.g., 'stream', 'river', 'wide river')")] = "river",
    navigable: Annotated[bool, Field(description="Whether the river is navigable by boat")] = False,
    start_point: Annotated[str, Field(description="Where the river starts in the first hex: 'center' (spring/source) or a side (entering from another region)")] = "center",
    end_point: Annotated[str, Field(description="Where the river ends in the last hex: 'center' (lake/ocean) or a side (exiting to another region)")] = "center",
    map_name: Annotated[str | None, Field(description="Name of the hex map (uses current map if not provided)")] = None,
) -> str:
    """Add a river that follows a path through multiple hexes.

    The tool automatically calculates which sides the river enters and exits for each hex
    based on the sequence of coordinates. Each consecutive pair of hexes must be adjacent.

    The start_point defines where the river begins (defaults to 'center' for a spring/source).
    The end_point defines where it ends (defaults to 'center' for emptying into a lake/ocean).
    """
    map_name = resolve_map_name(map_name)
    hex_map = storage.get_hex_map(map_name)
    if not hex_map:
        return f"Hex map '{map_name}' not found"

    if len(path) < 1:
        return "River path must contain at least 1 hex"

    # Convert start/end points to HexSide
    start_side = None if start_point == "center" else HexSide(start_point)
    end_side = None if end_point == "center" else HexSide(end_point)

    rivers_added = 0

    for i in range(len(path)):
        x, y = path[i]
        coord = HexCoordinate(x=x, y=y)
        hex_obj = hex_map.get_hex(coord)

        if not hex_obj:
            return f"No hex found at [{x},{y}]. Create all hexes in the path first."

        # Determine entry and exit points for this hex
        if i == 0:
            # First hex
            entry = start_side
            if len(path) > 1:
                next_coord = HexCoordinate(x=path[1][0], y=path[1][1])
                exit_dir = _get_direction_between_hexes(coord, next_coord)
                if exit_dir is None:
                    return f"Hexes at [{x},{y}] and [{path[1][0]},{path[1][1]}] are not adjacent"
            else:
                exit_dir = end_side
        elif i == len(path) - 1:
            # Last hex
            prev_coord = HexCoordinate(x=path[i-1][0], y=path[i-1][1])
            entry_dir = _get_direction_between_hexes(prev_coord, coord)
            if entry_dir is None:
                return f"Hexes at [{path[i-1][0]},{path[i-1][1]}] and [{x},{y}] are not adjacent"
            entry = entry_dir
            exit_dir = end_side
        else:
            # Middle hex
            prev_coord = HexCoordinate(x=path[i-1][0], y=path[i-1][1])
            next_coord = HexCoordinate(x=path[i+1][0], y=path[i+1][1])

            entry_dir = _get_direction_between_hexes(prev_coord, coord)
            exit_dir = _get_direction_between_hexes(coord, next_coord)

            if entry_dir is None:
                return f"Hexes at [{path[i-1][0]},{path[i-1][1]}] and [{x},{y}] are not adjacent"
            if exit_dir is None:
                return f"Hexes at [{x},{y}] and [{path[i+1][0]},{path[i+1][1]}] are not adjacent"

            entry = entry_dir

        # Create river segment
        river = River(
            start_point=entry,
            end_point=exit_dir,
            width=width,
            navigable=navigable
        )

        hex_obj.rivers.append(river)
        hex_map.set_hex(hex_obj)
        rivers_added += 1

    storage.add_hex_map(hex_map)
    return f"Added {width} through {rivers_added} hexes" + (" (navigable)" if navigable else "")


# LLM-Assisted Map Generation
@tool_with_logging(mcp, tags=["mode:any"])
async def generate_map_for_location(
    ctx: Context,
    location_id: Annotated[str, Field(description="ID of the existing outdoor Location to add a map to")],
    map_description: Annotated[str, Field(description="Description of the terrain and features to generate (e.g., 'a forested valley with a river running north to south and mountains on the eastern edge')")],
    width: Annotated[int, Field(description="Width of the map in hexes", ge=5, le=50)] = 20,
    height: Annotated[int, Field(description="Height of the map in hexes", ge=5, le=50)] = 20,
    hex_diameter_km: Annotated[float, Field(description="Size of each hex in kilometers")] = 10.0,
) -> str:
    """Generate a hex map for an existing outdoor location using LLM sampling.

    This tool uses MCP sampling to ask an LLM to generate a hex map in ASCII format
    based on the provided description. The LLM will create terrain appropriate to the
    description, which is then automatically parsed and converted into a HexMap object
    associated with the specified Location.
    """
    # Get the location
    location = storage.get_location(location_id)
    if not location:
        return f"Location with ID '{location_id}' not found"

    # Build terrain codes legend
    terrain_codes = {
        'G': 'grass',
        'P': 'plains',
        'F': 'farmland',
        'L': 'light_forest',
        'D': 'dense_forest',
        'J': 'jungle',
        'M': 'marsh',
        'S': 'swamp',
        'H': 'hills',
        'N': 'mountains',
        'E': 'desert',
        'B': 'badlands',
        'T': 'tundra',
        'I': 'glacier',
        'V': 'volcanic',
        'C': 'coast',
        'W': 'water',
        'R': 'scrub'
    }

    # Build the prompt for LLM
    prompt = f"""Generate a hex map in ASCII format with the following characteristics:

DESCRIPTION: {map_description}

MAP SIZE: {width} hexes wide by {height} hexes tall

TERRAIN CODES (use single letters):
"""
    for code, terrain in terrain_codes.items():
        prompt += f"  {code} = {terrain}\n"

    prompt += f"""
FORMAT REQUIREMENTS:
1. Each character represents one hex's terrain type
2. Separate hexes with a single space
3. Each row is on its own line
4. ODD-numbered rows (rows 1, 3, 5...) must start with a space to show hex offset
5. EVEN-numbered rows (rows 0, 2, 4...) start directly with a terrain code
6. Create exactly {height} rows
7. Make the map realistic and interesting based on the description

EXAMPLE (5x3 map):
G G L L M
 L L D D H
G L D H H

This creates:
- Row 0 (even): hexes at columns 0,2,4,6,8
- Row 1 (odd, indented): hexes at columns 1,3,5,7,9
- Row 2 (even): hexes at columns 0,2,4,6,8

Now generate a {width}x{height} hex map matching the description. Output ONLY the ASCII map, no explanations.
"""

    # Sample from LLM
    try:
        response = await ctx.sample(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )
    except Exception as e:
        logger.error(f"Error calling LLM for map generation: {e}")
        return f"Error generating map via LLM: {str(e)}. Try using import_terrain_from_ascii manually instead."

    try:
        ascii_map = response.content.strip()

        # Create HexMap
        map_name = f"{location.name} Map"
        hex_map = HexMap(
            name=map_name,
            description=map_description,
            hex_diameter_km=hex_diameter_km
        )

        # Parse the ASCII map
        lines = ascii_map.strip().split('\n')
        hex_count = 0

        for row_idx, line in enumerate(lines):
            y = row_idx

            # Check if this is an odd row (starts with space)
            is_offset_row = line.startswith(' ')
            if is_offset_row:
                line = line[1:]  # Remove leading space

            # Split by spaces to get individual hex characters
            chars = line.split()

            for col_idx, char in enumerate(chars):
                if char in terrain_codes:
                    # Calculate x coordinate with standard consecutive numbering
                    # For odd-q offset coordinates (pointy-top hexes):
                    # - Even rows (y=0,2,4...): hexes at x = 0,1,2,3...
                    # - Odd rows (y=1,3,5...): hexes at x = 0,1,2,3... (visually offset)
                    x = col_idx
                    terrain_name = terrain_codes[char]

                    try:
                        terrain = TerrainType(terrain_name)
                        coord = HexCoordinate(x=x, y=y)
                        hex_obj = Hex(coordinate=coord, terrain=terrain)
                        hex_map.set_hex(hex_obj)
                        hex_count += 1
                    except ValueError:
                        # Invalid terrain type, skip
                        logger.warning(f"Skipping invalid terrain type: {terrain_name}")
                        pass

        # Store the map
        storage.add_hex_map(hex_map)

        return f"Generated {width}x{height} hex map '{map_name}' for '{location.name}'. Total hexes: {hex_count}. Scale: {hex_diameter_km} km per hex."

    except Exception as e:
        logger.error(f"Error parsing generated map: {e}")
        return f"Error parsing generated map: {str(e)}. The LLM response was: {ascii_map[:200]}"


@mcp.resource("resource://transcripts/{campaign_name}/{session_number}")
def get_transcript(campaign_name: str, session_number: int) -> Transcript:
    return storage.get_transcript(campaign_name, session_number)


@mcp.resource("resource://current_transcript")
def get_current_transcript() -> Transcript:
    return storage.get_transcript(None, None)


# Game state resources
@mcp.resource("resource://current_campaign/game_state")
def get_current_campaign_game_state():
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        raise FileNotFoundError("No current campaign")
    return current_campaign.game_state


@mcp.resource("resource://campaigns/{campaign_name}/game_state")
def get_campaign_game_state(campaign_name: str):
    try:
        campaign = storage.get_campaign(campaign_name)
        return campaign.game_state
    except FileNotFoundError:
        raise FileNotFoundError(f"Campaign '{campaign_name}' not found")


# Mode resources
@mcp.resource("resource://current_campaign/mode")
def get_current_campaign_mode() -> dict[str, Any]:
    """Get current campaign mode(s)."""
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        raise FileNotFoundError("No current campaign")
    return {
        "modes": current_campaign.game_state.modes,
        "primary_mode": current_campaign.game_state.modes[0] if current_campaign.game_state.modes else None
    }


@mcp.resource("resource://modes")
def get_available_modes() -> list[dict[str, str]]:
    """Get all available modes with descriptions."""
    return [
        {"mode": mode, "description": description}
        for mode, description in AVAILABLE_MODES.items()
    ]


@mcp.prompt
def current_prompt() -> str:
    """Generates the most appropriate prompt for the current game state."""
    prompt = core_prompt
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        prompt += setup_prompt
    else:
        for mode in current_campaign.game_state.modes:
            if MODE_PROMPTS.get(mode):
                prompt += MODE_PROMPTS.get(mode)

    return Message(prompt)


logger.debug("✅ All tools successfully registered. Gamemaster-MCP server running! 🎲")


def main() -> None:
    """Main entry point for the D&D MCP Server."""
    parser = argparse.ArgumentParser(description="Server configuration")

    parser.add_argument(
        "--transport", type=str, help="Transport type to use with the server (optional)"
    )

    parser.add_argument(
        "--port", type=int, default=8000, help="Port number to run the server on (default: 8000)"
    )

    args = parser.parse_args()
    mcp.include_fastmcp_meta = True

    if args.transport is not None:
        mcp.run(transport=args.transport, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
