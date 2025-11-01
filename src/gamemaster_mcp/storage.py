"""
Storage layer for the D&D MCP Server.
Handles persistence of campaign data to JSON files.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import shortuuid

from .models import (
    NPC,
    AdventureEvent,
    Campaign,
    Character,
    GameState,
    Location,
    Quest,
    SessionNote,
    Transcript,
    TranscriptEntry,
    # New transcript tree models
    TranscriptTree,
    TranscriptInteraction,
    TranscriptCombat,
    TranscriptAdventure,
    ResponseText,
    ResponseTools,
)

logger = logging.getLogger("gamemaster-mcp")

logging.basicConfig(
    level=logging.DEBUG,
)


# UUID Helper function
def new_uuid() -> str:
    """Generate a new random 8-character UUID."""
    return shortuuid.random(length=8)


class DnDStorage:
    """Handles storage and retrieval of D&D campaign data."""

    def __init__(self, data_dir: str | Path = "dnd_data"):
        self.data_dir = Path(data_dir)
        logger.debug(f"📂 Initializing DnDStorage with data_dir: {self.data_dir.resolve()}")
        self.data_dir.mkdir(exist_ok=True)

        # Create subdirectories if necessary
        (self.data_dir / "campaigns").mkdir(exist_ok=True)
        (self.data_dir / "events").mkdir(exist_ok=True)
        (self.data_dir / "transcripts").mkdir(exist_ok=True)
        logger.debug("📂 Storage subdirectories ensured.")

        self._current_campaign: Campaign | None = None
        self._events: list[AdventureEvent] = []

        # Track current parent node for transcript tree manipulation
        self._transcript_current_parent: dict[str, str] = {}  # campaign -> parent_node_id
        # Track parent stack for nested structures (combat within adventure, etc.)
        self._parent_stack: dict[str, list[str]] = {}  # campaign -> list of parent IDs

        # Load existing data
        logger.debug("📂 Loading initial data...")
        self._load_current_campaign()
        self._load_events()
        logger.debug("✅ Initial data loaded.")

    def _get_campaign_file(self, campaign_name: str | None = None) -> Path:
        """Get the file path for a campaign."""
        if campaign_name is None and self._current_campaign:
            campaign_name = self._current_campaign.name
        if campaign_name is None:
            raise ValueError("No campaign name provided and no current campaign")

        safe_name = "".join(
            c for c in campaign_name if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        return self.data_dir / "campaigns" / f"{safe_name}.json"

    def _get_events_file(self) -> Path:
        """Get the file path for adventure events."""
        return self.data_dir / "events" / "adventure_log.json"

    def _get_transcript_dir(self, campaign_name: str) -> Path:
        return self.data_dir / "transcripts" / campaign_name

    def _get_transcript_file(self, campaign_name: str, session_number: int) -> Path:
        return self.data_dir / "transcripts" / campaign_name / f"session_{session_number}.json"

    def _save_campaign(self) -> None:
        """Save the current campaign to disk."""
        if not self._current_campaign:
            logger.debug("❌ No current campaign to save.")
            return

        campaign_file = self._get_campaign_file()
        logger.debug(f"💾 Saving campaign '{self._current_campaign.name}' to {campaign_file}")
        logger.info(f"💾 Autosaving '{self._current_campaign.name}'")
        campaign_data = self._current_campaign.model_dump(mode="json")

        with open(campaign_file, "w", encoding="utf-8") as f:
            json.dump(campaign_data, f, default=str)
        logger.debug(f"✅ Campaign '{self._current_campaign.name}' saved successfully.")

    def _load_current_campaign(self):
        """Load the most recently used campaign."""
        logger.debug("📂 Attempting to load the most recent campaign...")
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            logger.debug("❌ Campaigns directory does not exist. No campaign loaded.")
            return

        # Find the most recent campaign file
        campaign_files = list(campaigns_dir.glob("*.json"))
        if not campaign_files:
            logger.debug("❌ No campaign files found.")
            return

        # Sort by modification time and load the most recent
        latest_file = max(campaign_files, key=lambda f: f.stat().st_mtime)
        logger.debug(f"📂 Most recent campaign file is '{latest_file.name}'.")

        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._current_campaign = Campaign.model_validate(data)
            logger.info(f"✅ Successfully loaded campaign: {self._current_campaign.name}")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Error loading campaign from {latest_file}: {e}")

    def _save_events(self) -> None:
        """Save adventure events to disk."""
        events_file = self._get_events_file()
        logger.debug(f"💾 Saving {len(self._events)} events to {events_file}...")
        events_data = [event.model_dump(mode="json") for event in self._events]

        with open(events_file, "w", encoding="utf-8") as f:
            json.dump(events_data, f, default=str)
        logger.debug("✅ Events saved successfully.")

    def _load_events(self) -> None:
        """Load adventure events from disk."""
        logger.debug("📂 Attempting to load adventure events...")
        events_file = self._get_events_file()
        if not events_file.exists():
            logger.debug("❌ Adventure log file does not exist. No events loaded.")
            return

        try:
            with open(events_file, "r", encoding="utf-8") as f:
                events_data = json.load(f)
            self._events = [AdventureEvent.model_validate(event) for event in events_data]
            logger.info(f"✅ Successfully loaded {len(self._events)} events.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Error loading events: {e}")

    def _load_transcript(self, campaign_name: str, session_number: int) -> TranscriptTree | None:
        """Load a transcript, migrating from old format if necessary."""
        transcript_file = self._get_transcript_file(campaign_name, session_number)
        if not transcript_file.exists():
            return None

        try:
            with open(transcript_file, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)

            # Detect format: old format has 'entries', new format has 'children'
            if "entries" in transcript_data:
                logger.info(f"🔄 Migrating old transcript format to new tree format...")

                # Create backup
                backup_file = transcript_file.with_suffix(".json.old")
                import shutil
                shutil.copy2(transcript_file, backup_file)
                logger.info(f"💾 Created backup at {backup_file}")

                # Migrate: convert each old entry to TranscriptInteraction
                children = []
                for entry in transcript_data.get("entries", []):
                    interaction = TranscriptInteraction(
                        user_text=entry.get("player_entry", ""),
                        responses=[ResponseText(content=entry.get("game_response", ""))]
                    )
                    children.append(interaction)

                # Create new TranscriptTree
                transcript = TranscriptTree(
                    campaign=transcript_data["campaign"],
                    session_number=transcript_data["session_number"],
                    children=children,
                    current_parent_id=None
                )

                # Save in new format
                self._save_transcript(transcript)
                logger.info(f"✅ Migration complete. Transcript now uses tree format.")
                return transcript

            else:
                # New format - load as TranscriptTree
                transcript = TranscriptTree.model_validate(transcript_data)
                logger.info(
                    f"✅ Successfully loaded transcript for {campaign_name}, session {session_number}"
                )

                # Restore current parent from transcript metadata
                if transcript.current_parent_id:
                    self._transcript_current_parent[campaign_name] = transcript.current_parent_id
                else:
                    # Default to transcript root
                    self._transcript_current_parent[campaign_name] = transcript.id

                return transcript

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Error loading transcript: {e}")
            return None

    def _save_transcript(self, transcript: TranscriptTree) -> None:
        """Save a transcript tree to disk."""
        transcript_dir = self._get_transcript_dir(transcript.campaign)
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = self._get_transcript_file(transcript.campaign, transcript.session_number)

        # Update current_parent_id in transcript before saving
        current_parent = self._transcript_current_parent.get(transcript.campaign)
        if current_parent:
            transcript.current_parent_id = current_parent

        # Write transcript to the file
        transcript_data = transcript.model_dump(mode="json")
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, default=str, indent=4)
        logger.debug("✅ Transcript saved successfully.")

    # Current Parent Tracking
    def get_current_parent_id(self, campaign_name: str) -> str | None:
        """Get the current parent node ID for a campaign."""
        return self._transcript_current_parent.get(campaign_name)

    def set_current_parent_id(self, campaign_name: str, node_id: str) -> None:
        """Set the current parent node ID for a campaign."""
        self._transcript_current_parent[campaign_name] = node_id
        logger.debug(f"📍 Set current parent for '{campaign_name}' to node {node_id}")

    def _find_node_in_tree(
        self, node: TranscriptTree | TranscriptCombat | TranscriptAdventure, target_id: str
    ) -> TranscriptTree | TranscriptCombat | TranscriptAdventure | None:
        """Recursively find a node by ID in the tree."""
        if node.id == target_id:
            return node

        # Check children/actions depending on node type
        children = []
        if isinstance(node, TranscriptTree):
            children = node.children
        elif isinstance(node, (TranscriptCombat, TranscriptAdventure)):
            children = node.actions

        for child in children:
            if child.id == target_id:
                return child
            # Recursively search in combat and adventure nodes
            if isinstance(child, (TranscriptCombat, TranscriptAdventure)):
                result = self._find_node_in_tree(child, target_id)
                if result:
                    return result

        return None

    # Transcript Tree Manipulation
    def add_transcript_interaction(
        self,
        user_text: str,
        responses: list[dict],
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptInteraction:
        """Add an interaction to the current parent node."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load or create transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            transcript = TranscriptTree(
                campaign=campaign_name,
                session_number=session_number,
                children=[]
            )
            # Set transcript root as current parent
            self.set_current_parent_id(campaign_name, transcript.id)

        # Convert response dicts to proper response objects
        response_objects = []
        for resp in responses:
            if resp["type"] == "text":
                response_objects.append(ResponseText(content=resp["content"]))
            elif resp["type"] == "tools":
                # Convert tool calls
                from .models import InteractionToolCall
                tool_calls = []
                for call in resp.get("calls", []):
                    tool_calls.append(InteractionToolCall(
                        name=call["name"],
                        id=call["id"],
                        input=call["input"],
                        response=call.get("response", "")
                    ))
                response_objects.append(ResponseTools(calls=tool_calls))

        # Create interaction
        interaction = TranscriptInteraction(
            user_text=user_text,
            responses=response_objects
        )

        # Find current parent and add interaction
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id or current_parent_id == transcript.id:
            # Add to transcript root
            transcript.children.append(interaction)
        else:
            # Find parent node and add to its actions
            parent_node = self._find_node_in_tree(transcript, current_parent_id)
            if parent_node and isinstance(parent_node, (TranscriptCombat, TranscriptAdventure)):
                parent_node.actions.append(interaction)
            else:
                # Fallback to root if parent not found
                logger.warning(f"⚠️ Parent node {current_parent_id} not found, adding to root")
                transcript.children.append(interaction)

        self._save_transcript(transcript)
        logger.info(f"✅ Added interaction to transcript")
        return interaction

    def start_transcript_combat(
        self,
        participants: list[str],
        location: str | None = None,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptCombat:
        """Start a combat encounter, creating a Combat node and setting it as current parent."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load or create transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            transcript = TranscriptTree(
                campaign=campaign_name,
                session_number=session_number,
                children=[]
            )
            self.set_current_parent_id(campaign_name, transcript.id)

        # Create combat node (summary and result will be set when ending combat)
        combat = TranscriptCombat(
            participants=participants,
            result="",  # Will be set when ending
            summary="",  # Will be set when ending
            actions=[],
            location=location
        )

        # Add combat to current parent
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id or current_parent_id == transcript.id:
            # Add to transcript root
            transcript.children.append(combat)
        else:
            # Find parent node and add to its actions
            parent_node = self._find_node_in_tree(transcript, current_parent_id)
            if parent_node and isinstance(parent_node, TranscriptAdventure):
                parent_node.actions.append(combat)
            else:
                # Fallback to root
                logger.warning(f"⚠️ Parent node {current_parent_id} not found, adding to root")
                transcript.children.append(combat)

        # Push current parent onto stack and set combat as new current parent
        if campaign_name not in self._parent_stack:
            self._parent_stack[campaign_name] = []
        self._parent_stack[campaign_name].append(current_parent_id)
        self.set_current_parent_id(campaign_name, combat.id)

        self._save_transcript(transcript)
        logger.info(f"✅ Started combat with participants: {participants}")
        return combat

    def end_transcript_combat(
        self,
        result: str,
        summary: str,
        casualties: list[str] | None = None,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptCombat:
        """End a combat encounter, setting result/summary and restoring previous parent."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            raise ValueError("No transcript found")

        # Find combat node
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id:
            raise ValueError("No current parent set")

        combat_node = self._find_node_in_tree(transcript, current_parent_id)
        if not combat_node or not isinstance(combat_node, TranscriptCombat):
            raise ValueError("Current parent is not a combat node")

        # Update combat with results
        combat_node.result = result
        combat_node.summary = summary
        if casualties:
            combat_node.casualties = casualties
        combat_node.rounds = len([a for a in combat_node.actions if isinstance(a, TranscriptInteraction)])

        # Pop previous parent from stack and restore
        if campaign_name in self._parent_stack and self._parent_stack[campaign_name]:
            previous_parent = self._parent_stack[campaign_name].pop()
        else:
            previous_parent = transcript.id
        self.set_current_parent_id(campaign_name, previous_parent)

        self._save_transcript(transcript)
        logger.info(f"✅ Ended combat with result: {result}")
        return combat_node

    def start_transcript_adventure(
        self,
        title: str,
        quest_id: str | None = None,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptAdventure:
        """Start an adventure, creating an Adventure node and setting it as current parent."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load or create transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            transcript = TranscriptTree(
                campaign=campaign_name,
                session_number=session_number,
                children=[]
            )
            self.set_current_parent_id(campaign_name, transcript.id)

        # Create adventure node (summary will be set when ending)
        adventure = TranscriptAdventure(
            title=title,
            summary="",  # Will be set when ending
            actions=[],
            quest_id=quest_id
        )

        # Add adventure to current parent
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id or current_parent_id == transcript.id:
            # Add to transcript root
            transcript.children.append(adventure)
        else:
            # Find parent node and add to its actions
            parent_node = self._find_node_in_tree(transcript, current_parent_id)
            if parent_node and isinstance(parent_node, TranscriptAdventure):
                parent_node.actions.append(adventure)
            else:
                # Fallback to root
                logger.warning(f"⚠️ Parent node {current_parent_id} not found, adding to root")
                transcript.children.append(adventure)

        # Push current parent onto stack and set adventure as new current parent
        if campaign_name not in self._parent_stack:
            self._parent_stack[campaign_name] = []
        self._parent_stack[campaign_name].append(current_parent_id)
        self.set_current_parent_id(campaign_name, adventure.id)

        self._save_transcript(transcript)
        logger.info(f"✅ Started adventure: {title}")
        return adventure

    def end_transcript_adventure(
        self,
        summary: str,
        rewards: list[str] | None = None,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptAdventure:
        """End an adventure, setting summary and restoring previous parent."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            raise ValueError("No transcript found")

        # Find adventure node
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id:
            raise ValueError("No current parent set")

        adventure_node = self._find_node_in_tree(transcript, current_parent_id)
        if not adventure_node or not isinstance(adventure_node, TranscriptAdventure):
            raise ValueError("Current parent is not an adventure node")

        # Update adventure with summary
        adventure_node.summary = summary
        if rewards:
            adventure_node.rewards = rewards

        # Pop previous parent from stack and restore
        if campaign_name in self._parent_stack and self._parent_stack[campaign_name]:
            previous_parent = self._parent_stack[campaign_name].pop()
        else:
            previous_parent = transcript.id
        self.set_current_parent_id(campaign_name, previous_parent)

        self._save_transcript(transcript)
        logger.info(f"✅ Ended adventure: {adventure_node.title}")
        return adventure_node

    def get_ungrouped_transcript_nodes(
        self,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> list[TranscriptInteraction | TranscriptCombat | TranscriptAdventure]:
        """Get all transcript nodes that haven't been grouped into an adventure yet.

        Returns all nodes after the last TranscriptAdventure in the transcript's children.
        """
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            return []

        # Find the index of the last TranscriptAdventure in children
        last_adventure_index = -1
        for i, child in enumerate(transcript.children):
            if isinstance(child, TranscriptAdventure):
                last_adventure_index = i

        # Get all nodes after the last adventure (or all nodes if no adventure exists)
        return transcript.children[last_adventure_index + 1:]

    def complete_transcript_adventure(
        self,
        title: str,
        summary: str,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptAdventure:
        """Complete an adventure by grouping all interactions since the last adventure.

        Takes all nodes that have been added to the transcript root since the last
        TranscriptAdventure node (or since the start) and groups them into a new
        TranscriptAdventure node at the same level.
        """
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load or create transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            # No transcript exists, nothing to complete
            raise ValueError("No transcript found for this session")

        # Find the index of the last TranscriptAdventure in children
        last_adventure_index = -1
        for i, child in enumerate(transcript.children):
            if isinstance(child, TranscriptAdventure):
                last_adventure_index = i

        # Get all nodes after the last adventure (or all nodes if no adventure exists)
        nodes_to_group = transcript.children[last_adventure_index + 1:]

        if not nodes_to_group:
            raise ValueError("No interactions to group into an adventure")

        # Create new adventure node with these interactions
        adventure = TranscriptAdventure(
            title=title,
            summary=summary,
            actions=nodes_to_group,
        )

        # Replace the grouped nodes with the single adventure node
        transcript.children = transcript.children[:last_adventure_index + 1] + [adventure]

        # Save transcript
        self._save_transcript(transcript)
        logger.info(f"✅ Completed adventure: '{title}' with {len(nodes_to_group)} node(s)")
        return adventure

    # Campaign Management
    def create_campaign(
        self,
        name: str,
        description: str,
        dm_name: str | None = None,
        setting: str | Path | None = None,
    ) -> Campaign:
        """Create a new campaign."""
        logger.info(f"✨ Creating new campaign: '{name}'")
        game_state = GameState(campaign_name=name)

        campaign = Campaign(
            name=name,
            description=description,
            dm_name=dm_name,
            setting=setting,
            game_state=game_state,
        )

        self._current_campaign = campaign
        self._save_campaign()
        logger.info(f"✅ Campaign '{name}' created and set as active.")
        return campaign

    def get_current_campaign(self) -> Campaign | None:
        """Get the current campaign."""
        return self._current_campaign

    def list_campaigns(self) -> list[str]:
        """List all available campaigns."""
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            return []

        return [f.stem for f in campaigns_dir.glob("*.json")]

    def get_campaign(self, name: str) -> Campaign:
        logger.info(f"📂 Attempting to load campaign: '{name}'")
        campaign_file = self._get_campaign_file(name)
        logger.debug(f"📂 Campaign file path: {campaign_file}")

        if not campaign_file.exists():
            logger.error(f"❌ Campaign file not found for '{name}'")
            raise FileNotFoundError(f"Campaign '{name}' not found")

        with open(campaign_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Campaign.model_validate(data)

    def load_campaign(self, name: str) -> Campaign:
        self._current_campaign = self.get_campaign(name)
        logger.info(f"✅ Successfully loaded campaign '{name}'.")
        return self._current_campaign

    def update_campaign(self, **kwargs):
        """Update campaign metadata."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(f"📝 Updating campaign '{self._current_campaign.name}' with data: {kwargs}")
        for key, value in kwargs.items():
            if hasattr(self._current_campaign, key):
                logger.debug(f"📝 Updating {key} to {value}")
                setattr(self._current_campaign, key, value)

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Campaign '{self._current_campaign.name}' updated.")

    # Character Management
    def add_character(self, character: Character) -> None:
        """Add a character to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(
            f"➕ Adding character '{character.name}' to campaign '{self._current_campaign.name}'."
        )
        self._current_campaign.characters[character.name] = character
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.debug(
            f"✅ Character '{character.name}' added to campaign: '{self._current_campaign.name}'."
        )

    def _find_character(self, name_or_id: str) -> Character | None:
        """Find a character by name or ID."""
        if not self._current_campaign:
            e = ValueError("No current campaign")
            logger.error(e)
            raise e

        character: Character | None = None
        logger.info(f"_find_character: current campaign: {self._current_campaign.name}")
        logger.info(
            f"_find_character: current campaign characters: {self._current_campaign.characters}"
        )

        # Try searching by ID first if appropriate
        if len(name_or_id) == 8:
            try:
                char_id = name_or_id
                for char in self._current_campaign.characters.values():
                    if char.id == char_id:
                        character = char
            except (ValueError, TypeError):
                # Not a UUID, so it's a name
                logger.warning(f"⚠️ Character not found by ID: {name_or_id}, trying name")
                pass

        # Search by name
        if not character:
            try:
                character = self._current_campaign.characters.get(name_or_id)
            except (ValueError, TypeError) as e:
                logger.error(e)
                return None

        return character

    def get_character(self, name_or_id: str) -> Character | None:
        """Get a character by name or ID."""
        if not name_or_id:
            raise ValueError("Empty character name or id")

        char = self._find_character(name_or_id)
        if not char:
            logger.error(f"❌ Character '{name_or_id}' not found!")
            return None
        logger.debug(f"✅ Found character '{char.name}'")
        return char

    def update_character(self, name_or_id: str, **kwargs) -> None:
        """Update a character's data."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(f"📝 Attempting to update character '{name_or_id}' with data: {kwargs}")
        character = self._find_character(name_or_id)
        if not character:
            e = ValueError(f"❌ Character '{name_or_id}' not found!")
            logger.error(e)
            raise e

        original_name = character.name
        new_name = kwargs.get("name")

        for key, value in kwargs.items():
            if key == 'level':
                character.character_class.level = value
            elif hasattr(character, key):
                logger.debug(f"📝 Updating character '{original_name}': {key} -> {value}")
                setattr(character, key, value)

        character.updated_at = datetime.now()

        if new_name and new_name != original_name:
            # If name changed, update the dictionary key
            logger.debug(
                f"🏷️ Character name changed from '{original_name}' to '{new_name}'. Updating dictionary key."
            )
            self._current_campaign.characters[new_name] = self._current_campaign.characters.pop(
                original_name
            )

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Character '{new_name or original_name}' updated successfully.")

    def remove_character(self, name_or_id: str) -> None:
        """Remove a character from the campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.debug(f"🗑️ Attempting to remove character '{name_or_id}'.")
        character_to_remove = self._find_character(name_or_id)
        if character_to_remove:
            char_name = character_to_remove.name
            logger.debug(f"🗑️ Found character '{char_name}' to remove.")
            # We need the name to delete from the dict
            del self._current_campaign.characters[char_name]
            self._current_campaign.updated_at = datetime.now()
            self._save_campaign()
            logger.info(f"✅ Character '{char_name}' removed successfully.")
        else:
            logger.warning(f"⚠️ Character '{name_or_id}' not found for removal.")

    def list_characters(self) -> list[str]:
        """List all character names in the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        return list(self._current_campaign.characters.keys())

    # NPC Management
    def add_npc(self, npc: NPC) -> None:
        """Add an NPC to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.npcs[npc.name] = npc
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_npc(self, name: str) -> NPC | None:
        """Get an NPC by name."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        if not name:
            raise ValueError("Empty npc name")
        return self._current_campaign.npcs.get(name)

    def list_npcs(self) -> list[str]:
        """List all NPC names."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        return list(self._current_campaign.npcs.keys())

    # Location Management
    def add_location(self, location: Location) -> None:
        """Add a location to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.locations[location.name] = location
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_location(self, name: str) -> Location | None:
        """Get a location by name."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        if not name:
            raise ValueError("Empty location name")
        return self._current_campaign.locations.get(name)

    def list_locations(self) -> list[str]:
        """List all location names."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        return list(self._current_campaign.locations.keys())

    # Quest Management
    def add_quest(self, quest: Quest) -> None:
        """Add a quest to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.quests[quest.title] = quest
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_quest(self, title: str) -> Quest | None:
        """Get a quest by title."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        if not title:
            raise ValueError("Empty quest title")
        return self._current_campaign.quests.get(title)

    def update_quest_status(self, title: str, status: str) -> None:
        """Update a quest's status."""
        quest = self.get_quest(title)
        if quest:
            quest.status = status
            self._current_campaign.updated_at = datetime.now()  # type: ignore
            self._save_campaign()
        else:
            raise ValueError(f"No such quest {title}")

    def list_quests(self, status: str | None = None) -> list[str]:
        """List quest titles, optionally filtered by status."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        quests = self._current_campaign.quests
        if status:
            return [title for title, quest in quests.items() if quest.status == status]
        return list(quests.keys())

    # Game State Management
    def update_game_state(self, **kwargs) -> None:
        """Update the game state."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        game_state = self._current_campaign.game_state
        for key, value in kwargs.items():
            if hasattr(game_state, key):
                setattr(game_state, key, value)

        game_state.updated_at = datetime.now()
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_game_state(self) -> GameState | None:
        """Get the current game state."""
        if not self._current_campaign:
            return None
        return self._current_campaign.game_state

    # Session Management
    def add_session_note(self, session_note: SessionNote) -> None:
        """Add a session note."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.sessions.append(session_note)
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_sessions(self) -> list[SessionNote]:
        """Get all session notes."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        return self._current_campaign.sessions

    # Adventure Log / Events
    def add_event(self, event: AdventureEvent) -> None:
        """Add an event to the adventure log."""
        logger.info(f"➕ Adding event: '{event.title}' ({event.event_type})")
        self._events.append(event)
        self._save_events()
        logger.debug("✅ Event added and log saved.")

    def get_events(
        self, limit: int | None = None, event_type: str | None = None, campaign: str | None = None
    ) -> list[AdventureEvent]:
        """Get adventure events, optionally filtered."""
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if campaign:
            events = [e for e in events if e.campaign == campaign]

        # Sort by timestamp (newest first)
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        if limit:
            events = events[:limit]

        return events

    def search_events(self, query: str) -> list[AdventureEvent]:
        """Search events by title or description."""
        query_lower = query.lower()
        return [
            event
            for event in self._events
            if query_lower in event.title.lower() or query_lower in event.description.lower()
        ]

    # Transcripts (backward compatibility methods)
    def get_transcript(
        self, campaign_name: str | None = None, session_number: int | None = None
    ) -> TranscriptTree | None:
        """Get a transcript tree. Now returns TranscriptTree (new format)."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
        else:
            campaign = self.get_campaign(campaign_name)

        if session_number is None:
            session_number = campaign.game_state.current_session if campaign and campaign.game_state else 1

        return self._load_transcript(campaign.name, session_number)

    def add_transcript_entry(
        self,
        player_entry: str,
        game_response: str,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptTree:
        """Add a transcript entry. Now uses new TranscriptTree format internally."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name
        else:
            campaign = self.get_campaign(campaign_name)
            campaign_name = campaign.name

        if session_number is None:
            campaign_obj = self.get_current_campaign()
            session_number = campaign_obj.game_state.current_session if campaign_obj else 0

        # Add the interaction using new API
        self.add_transcript_interaction(
            user_text=player_entry,
            responses=[{"type": "text", "content": game_response}],
            campaign_name=campaign_name,
            session_number=session_number
        )

        # Return the updated transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            raise ValueError("Failed to load transcript after adding entry")
        return transcript
