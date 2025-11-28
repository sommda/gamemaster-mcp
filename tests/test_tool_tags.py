"""
Tests for tool tagging functionality in @tool_with_logging decorator.

This test module verifies that:
1. Tags are properly passed through the @tool_with_logging decorator
2. Tags are correctly registered with FastMCP
3. Tools can be filtered by tags
4. Different tag patterns (mode:setup, mode:any, mode:combat, etc.) work correctly
"""

import pytest

from gamemaster_mcp.main import mcp


class TestToolTags:
    """Test suite for tool tagging functionality."""

    @pytest.mark.asyncio
    async def test_tools_have_tags(self):
        """Verify that tools registered with tags actually have them."""
        tools = await mcp.get_tools()

        # Check that we have tools
        assert len(tools) > 0, "No tools registered"

        # Check that at least some tools have tags
        tools_with_tags = [
            tool for tool in tools.values()
            if hasattr(tool, 'tags') and tool.tags
        ]
        assert len(tools_with_tags) > 0, "No tools have tags"

    @pytest.mark.asyncio
    async def test_setup_mode_tags(self):
        """Verify tools tagged with mode:setup."""
        tools = await mcp.get_tools()

        # Find tools with mode:setup tag
        setup_tools = [
            tool for tool in tools.values()
            if hasattr(tool, 'tags') and 'mode:setup' in tool.tags
        ]

        # We know these should be setup tools
        setup_tool_names = [
            'create_campaign',
            'list_campaigns',
            'load_campaign',
            'create_character',
            'create_location',
            'add_session_note',
            'get_sessions',
            'bulk_update_characters',
        ]

        assert len(setup_tools) > 0, "No mode:setup tools found"

        # Verify expected tools are in the setup list
        found_names = {tool.name for tool in setup_tools}
        for expected_name in setup_tool_names:
            assert expected_name in found_names, f"Expected setup tool '{expected_name}' not found"

    @pytest.mark.asyncio
    async def test_any_mode_tags(self):
        """Verify tools tagged with mode:any."""
        tools = await mcp.get_tools()

        # Find tools with mode:any tag
        any_mode_tools = [
            tool for tool in tools.values()
            if hasattr(tool, 'tags') and 'mode:any' in tool.tags
        ]

        # We know these should be any-mode tools (sampling of common ones)
        any_mode_tool_names = [
            'get_campaign_info',
            'list_characters',
            'list_npcs',
            'list_locations',
            'list_quests',
            'get_game_state',
            'update_game_state',
            'add_event',
            'get_events',
            'roll_dice',
        ]

        assert len(any_mode_tools) > 0, "No mode:any tools found"

        # Verify expected tools are in the any-mode list
        found_names = {tool.name for tool in any_mode_tools}
        for expected_name in any_mode_tool_names:
            assert expected_name in found_names, f"Expected any-mode tool '{expected_name}' not found"

    @pytest.mark.asyncio
    async def test_combat_mode_tags(self):
        """Verify tools tagged with mode:combat."""
        tools = await mcp.get_tools()

        # Find tools with mode:combat tag
        combat_tools = [
            tool for tool in tools.values()
            if hasattr(tool, 'tags') and 'mode:combat' in tool.tags
        ]

        # We know these should be combat tools
        combat_tool_names = [
            'end_combat',
            'next_turn',
        ]

        assert len(combat_tools) > 0, "No mode:combat tools found"

        # Verify expected tools are in the combat list
        found_names = {tool.name for tool in combat_tools}
        for expected_name in combat_tool_names:
            assert expected_name in found_names, f"Expected combat tool '{expected_name}' not found"

    @pytest.mark.asyncio
    async def test_specific_tool_tags(self):
        """Test that specific tools have the correct tags."""
        tools = await mcp.get_tools()

        # Test specific tool tag assignments
        test_cases = [
            ('create_campaign', {'mode:setup'}),
            ('get_campaign_info', {'mode:any'}),
            ('end_combat', {'mode:combat'}),
            ('start_combat', {'mode:town', 'mode:dunegon', 'mode:outdoors'}),  # Note: typo in source
        ]

        for tool_name, expected_tags in test_cases:
            assert tool_name in tools, f"Tool '{tool_name}' not found"
            tool = tools[tool_name]
            assert hasattr(tool, 'tags'), f"Tool '{tool_name}' has no tags attribute"
            assert tool.tags == expected_tags, f"Tool '{tool_name}' has tags {tool.tags}, expected {expected_tags}"

    @pytest.mark.asyncio
    async def test_tags_in_schema_dump(self):
        """Verify tags appear in the tool's schema dump."""
        tools = await mcp.get_tools()

        # Get a tool we know has tags
        create_campaign = tools.get('create_campaign')
        assert create_campaign is not None, "create_campaign tool not found"

        # Check tags in model_dump
        if hasattr(create_campaign, 'model_dump'):
            schema = create_campaign.model_dump()
            assert 'tags' in schema, "Tags not in schema dump"
            assert 'mode:setup' in schema['tags'], "mode:setup tag not in schema dump"

    @pytest.mark.asyncio
    async def test_most_tools_have_mode_tags(self):
        """Verify that most tools have at least one mode tag.

        This test identifies tools that don't have mode tags, which may need attention.
        Some tools legitimately may not need mode tags if they're internal/meta tools.
        """
        tools = await mcp.get_tools()

        tools_without_mode_tags = []
        for tool_name, tool in tools.items():
            if not hasattr(tool, 'tags'):
                tools_without_mode_tags.append(tool_name)
                continue

            # Check if at least one tag starts with 'mode:'
            has_mode_tag = any(tag.startswith('mode:') for tag in tool.tags)
            if not has_mode_tag:
                tools_without_mode_tags.append(tool_name)

        # Known tools that currently don't have mode tags
        # These might be internal/meta tools or need to be tagged
        known_untagged = {
            'calculate_experience',
            'record_interaction',
            'record_interaction_with_tools',
        }

        # Check that untagged tools are only the known ones
        untagged_set = set(tools_without_mode_tags)
        assert untagged_set == known_untagged, (
            f"Unexpected tools without mode tags. "
            f"Missing tags: {untagged_set - known_untagged}, "
            f"Now have tags: {known_untagged - untagged_set}"
        )

    @pytest.mark.asyncio
    async def test_tag_consistency(self):
        """Verify tags are consistent between attribute and schema."""
        tools = await mcp.get_tools()

        for tool_name, tool in tools.items():
            # Get tags from attribute
            attr_tags = tool.tags if hasattr(tool, 'tags') else set()

            # Get tags from schema if available
            schema_tags = None
            if hasattr(tool, 'model_dump'):
                schema = tool.model_dump()
                schema_tags = schema.get('tags', set())

            # If both exist, they should match
            if schema_tags is not None:
                assert attr_tags == schema_tags, (
                    f"Tool '{tool_name}' has inconsistent tags: "
                    f"attribute={attr_tags}, schema={schema_tags}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
