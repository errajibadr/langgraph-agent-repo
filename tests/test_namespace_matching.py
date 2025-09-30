"""Tests for namespace pattern matching in ChannelStreamingProcessor."""

import pytest
from ai_engine.streaming.config import TokenStreamingConfig
from ai_engine.streaming.processor import ChannelStreamingProcessor


class TestNamespacePatternExtraction:
    """Test namespace pattern extraction (modulo 2 logic)."""

    def test_extract_pattern_main(self):
        """Test extraction for main namespace."""
        processor = ChannelStreamingProcessor(channels=[])
        assert processor._extract_namespace_pattern("main") == "main"

    def test_extract_pattern_single_level(self):
        """Test extraction for single-level namespaces (type:id)."""
        processor = ChannelStreamingProcessor(channels=[])

        assert processor._extract_namespace_pattern("clarifynode:12345") == "clarifynode"
        assert processor._extract_namespace_pattern("graph_node:67890") == "graph_node"

    def test_extract_pattern_two_levels(self):
        """Test extraction for two-level namespaces (type:id:type:id)."""
        processor = ChannelStreamingProcessor(channels=[])

        assert (
            processor._extract_namespace_pattern("clarifynode:12345:subgraphnode:345346") == "clarifynode:subgraphnode"
        )
        assert processor._extract_namespace_pattern("graph_node:12345:subgraphnode:123345") == "graph_node:subgraphnode"

    def test_extract_pattern_three_levels(self):
        """Test extraction for three-level namespaces (type:id:type:id:type:id)."""
        processor = ChannelStreamingProcessor(channels=[])

        pattern = processor._extract_namespace_pattern("clarifynode:abc:subgraph:def:deepnode:ghi")
        assert pattern == "clarifynode:subgraph:deepnode"


class TestNamespaceMatching:
    """Test namespace pattern matching logic."""

    def test_all_wildcard(self):
        """Test 'all' wildcard matches everything."""
        processor = ChannelStreamingProcessor(
            channels=[], token_streaming=TokenStreamingConfig(enabled_namespaces=["all"])
        )

        assert processor._should_stream_tokens_from_namespace("main")
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345")
        assert processor._should_stream_tokens_from_namespace("graph_node:67890:subgraphnode:111")

    def test_exact_pattern_match(self):
        """Test exact pattern matching."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(enabled_namespaces=["clarifynode"]),
        )

        # Should match: clarifynode:12345 extracts to "clarifynode"
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345")
        assert processor._should_stream_tokens_from_namespace("clarifynode:67890")

        # Should NOT match: clarifynode:12345:subgraphnode:111 extracts to "clarifynode:subgraphnode"
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345:subgraphnode:111")
        assert not processor._should_stream_tokens_from_namespace("graph_node:12345")
        assert not processor._should_stream_tokens_from_namespace("main")

    def test_wildcard_pattern(self):
        """Test wildcard pattern (e.g., 'clarifynode:*')."""
        processor = ChannelStreamingProcessor(
            channels=[], token_streaming=TokenStreamingConfig(enabled_namespaces=["clarifynode:*"])
        )

        # Should match: all patterns starting with "clarifynode"
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345")
        assert processor._should_stream_tokens_from_namespace("clarifynode:67890")
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345:subgraphnode:111")

        # Should NOT match: different root type
        assert not processor._should_stream_tokens_from_namespace("graph_node:12345")

    def test_nested_type_matching(self):
        """Test nested type pattern matching."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(enabled_namespaces=["clarifynode:subgraphnode"]),
        )

        # Should match: pattern extracts to "clarifynode:subgraphnode"
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345:subgraphnode:111")
        assert processor._should_stream_tokens_from_namespace("clarifynode:67890:subgraphnode:999")

        # Should NOT match: different patterns
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345")
        assert not processor._should_stream_tokens_from_namespace("graph_node:12345:subgraphnode:111")
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345:othernode:111")

    def test_multiple_patterns(self):
        """Test multiple patterns in enabled_namespaces."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(enabled_namespaces=["clarifynode:*", "graph_node:subgraphnode"]),
        )

        # Should match clarifynode:* pattern
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345")
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345:anything:111")

        # Should match graph_node:subgraphnode pattern
        assert processor._should_stream_tokens_from_namespace("graph_node:12345:subgraphnode:111")

        # Should NOT match: graph_node alone
        assert not processor._should_stream_tokens_from_namespace("graph_node:12345")
        assert not processor._should_stream_tokens_from_namespace("other_node:12345")

    def test_real_world_examples(self):
        """Test real-world namespace examples."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(enabled_namespaces=["clarifynode:*", "deep_search:researcher"]),
        )

        # Clarify node examples (wildcard)
        assert processor._should_stream_tokens_from_namespace("clarifynode:abc123")
        assert processor._should_stream_tokens_from_namespace("clarifynode:abc123:reflection:def456")

        # Deep search researcher examples (exact nested match)
        assert processor._should_stream_tokens_from_namespace("deep_search:task1:researcher:task2")

        # Should not match
        assert not processor._should_stream_tokens_from_namespace("deep_search:task1")
        assert not processor._should_stream_tokens_from_namespace("deep_search:task1:planner:task2")

    def test_main_namespace(self):
        """Test main namespace handling."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(enabled_namespaces=["main"]),
        )

        assert processor._should_stream_tokens_from_namespace("main")
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345")


class TestNamespaceExclusions:
    """Test namespace exclusion logic."""

    def test_exclude_overrides_enable(self):
        """Test that exclusions override enabled namespaces."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(
                enabled_namespaces=["clarifynode:*"], exclude_namespaces=["clarifynode:subgraphnode"]
            ),
        )

        # Should match: clarifynode:12345 is enabled and not excluded
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345")

        # Should NOT match: clarifynode:12345:subgraphnode:111 is excluded
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345:subgraphnode:111")

    def test_exclude_with_all(self):
        """Test exclusions work even with 'all' enabled."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(
                enabled_namespaces=["all"], exclude_namespaces=["clarifynode:subgraphnode", "graph_node"]
            ),
        )

        # Should match: enabled by "all" and not excluded
        assert processor._should_stream_tokens_from_namespace("main")
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345")
        assert processor._should_stream_tokens_from_namespace("other_node:12345")

        # Should NOT match: explicitly excluded
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345:subgraphnode:111")
        assert not processor._should_stream_tokens_from_namespace("graph_node:12345")

    def test_exclude_wildcard(self):
        """Test wildcard exclusion patterns."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(enabled_namespaces=["all"], exclude_namespaces=["clarifynode:*"]),
        )

        # Should match: not excluded
        assert processor._should_stream_tokens_from_namespace("main")
        assert processor._should_stream_tokens_from_namespace("graph_node:12345")

        # Should NOT match: excluded by clarifynode:* pattern
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345")
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345:subgraphnode:111")

    def test_exclude_exact_match(self):
        """Test exact match exclusions."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(
                enabled_namespaces=["clarifynode:*"], exclude_namespaces=["clarifynode"]
            ),
        )

        # Should match: clarifynode:12345:subgraphnode:111 pattern is "clarifynode:subgraphnode"
        assert processor._should_stream_tokens_from_namespace("clarifynode:12345:subgraphnode:111")

        # Should NOT match: clarifynode:12345 pattern is "clarifynode" (excluded)
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345")

    def test_multiple_exclusions(self):
        """Test multiple exclusion patterns."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(
                enabled_namespaces=["all"],
                exclude_namespaces=["clarifynode", "graph_node:subgraphnode", "deep_search:*"],
            ),
        )

        # Should match
        assert processor._should_stream_tokens_from_namespace("main")
        assert processor._should_stream_tokens_from_namespace("graph_node:12345")

        # Should NOT match: various exclusions
        assert not processor._should_stream_tokens_from_namespace("clarifynode:12345")
        assert not processor._should_stream_tokens_from_namespace("graph_node:12345:subgraphnode:111")
        assert not processor._should_stream_tokens_from_namespace("deep_search:task1")
        assert not processor._should_stream_tokens_from_namespace("deep_search:task1:researcher:task2")

    def test_no_exclusions(self):
        """Test that empty exclusions don't affect matching."""
        processor = ChannelStreamingProcessor(
            channels=[],
            token_streaming=TokenStreamingConfig(enabled_namespaces=["clarifynode"], exclude_namespaces=set()),
        )

        assert processor._should_stream_tokens_from_namespace("clarifynode:12345")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
