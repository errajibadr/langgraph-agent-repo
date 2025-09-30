# Namespace Matching for Token Streaming

## Overview

The streaming processor supports flexible namespace pattern matching to control which graph nodes stream their LLM tokens. This allows fine-grained control over what gets streamed in complex multi-agent graphs with subgraphs.

## Namespace Structure

Namespaces follow a pattern of alternating **type** and **runtime ID** components:

```
type:id:type:id:type:id...
```

### Examples

- `main` - Root namespace
- `clarifynode:12345` - Single level: clarifynode with runtime ID 12345
- `clarifynode:12345:subgraphnode:345346` - Two levels: clarifynode → subgraphnode
- `graph_node:abc:research:def:analyzer:ghi` - Three levels deep

## Pattern Extraction (Modulo 2)

The system extracts type-based patterns by taking every other component (indices 0, 2, 4, ...):

| Full Namespace | Extracted Pattern |
|---------------|-------------------|
| `clarifynode:12345` | `clarifynode` |
| `clarifynode:12345:subgraphnode:345346` | `clarifynode:subgraphnode` |
| `graph_node:67890` | `graph_node` |
| `deep_search:t1:researcher:t2` | `deep_search:researcher` |

## Pattern Matching Syntax

### Exact Match
Matches namespaces whose extracted pattern exactly matches:

```python
enabled_namespaces=["clarifynode"]
# Matches:
#   clarifynode:12345 → pattern: "clarifynode" ✓
# Doesn't match:
#   clarifynode:12345:subgraph:111 → pattern: "clarifynode:subgraph" ✗
```

### Wildcard Match (`:*`)
Matches namespaces whose extracted pattern starts with the prefix:

```python
enabled_namespaces=["clarifynode:*"]
# Matches:
#   clarifynode:12345 → pattern: "clarifynode" ✓
#   clarifynode:12345:subgraph:111 → pattern: "clarifynode:subgraph" ✓
#   clarifynode:12345:deep:222:analyzer:333 → pattern: "clarifynode:deep:analyzer" ✓
# Doesn't match:
#   graph_node:12345 → pattern: "graph_node" ✗
```

### Nested Type Match
Matches namespaces with specific nested types:

```python
enabled_namespaces=["clarifynode:subgraphnode"]
# Matches:
#   clarifynode:12345:subgraphnode:111 → pattern: "clarifynode:subgraphnode" ✓
# Doesn't match:
#   clarifynode:12345 → pattern: "clarifynode" ✗
#   clarifynode:12345:othernode:111 → pattern: "clarifynode:othernode" ✗
```

### Match All
Special keyword to match all namespaces:

```python
enabled_namespaces=["all"]
# Matches everything (unless excluded)
```

## Exclusion Logic

Exclusions **always override** enabled namespaces. If a namespace matches an exclusion pattern, it will not stream even if it matches an enabled pattern.

### Example 1: Exclude Specific Nested Type

```python
TokenStreamingConfig(
    enabled_namespaces=["clarifynode:*"],
    exclude_namespaces=["clarifynode:subgraphnode"]
)

# Matches:
#   clarifynode:12345 ✓
#   clarifynode:12345:othernode:111 ✓

# Excluded:
#   clarifynode:12345:subgraphnode:111 ✗ (matches exclusion)
```

### Example 2: Enable All, Exclude Some

```python
TokenStreamingConfig(
    enabled_namespaces=["all"],
    exclude_namespaces=["clarifynode:subgraphnode", "graph_node"]
)

# Matches:
#   main ✓
#   clarifynode:12345 ✓
#   other_node:12345 ✓

# Excluded:
#   clarifynode:12345:subgraphnode:111 ✗
#   graph_node:12345 ✗
```

### Example 3: Exclude with Wildcard

```python
TokenStreamingConfig(
    enabled_namespaces=["all"],
    exclude_namespaces=["deep_search:*"]
)

# Matches:
#   main ✓
#   clarifynode:12345 ✓
#   graph_node:12345 ✓

# Excluded:
#   deep_search:t1 ✗
#   deep_search:t1:researcher:t2 ✗
#   deep_search:t1:planner:t2 ✗
```

## Real-World Use Cases

### Use Case 1: Stream Only Clarify Agent

```python
TokenStreamingConfig(
    enabled_namespaces=["clarifynode:*"]
)
# Stream all levels of the clarify agent subgraph
```

### Use Case 2: Stream Main Agent, Exclude Internal Tools

```python
TokenStreamingConfig(
    enabled_namespaces=["all"],
    exclude_namespaces=["toolnode", "validation_node"]
)
# Stream everything except internal tool nodes
```

### Use Case 3: Stream Only Specific Researcher

```python
TokenStreamingConfig(
    enabled_namespaces=["deep_search:researcher"]
)
# Only stream the researcher node within deep_search agent
```

### Use Case 4: Stream All Except Specific Nested Subgraphs

```python
TokenStreamingConfig(
    enabled_namespaces=["all"],
    exclude_namespaces=["clarifynode:reflection", "planner:validator"]
)
# Stream everything except specific internal subgraphs
```

## Configuration Example

```python
from ai_engine.streaming.config import TokenStreamingConfig, ChannelConfig, ChannelType
from ai_engine.streaming.processor import ChannelStreamingProcessor

# Create processor with namespace filtering
processor = ChannelStreamingProcessor(
    channels=[
        ChannelConfig(key="messages", channel_type=ChannelType.MESSAGE),
    ],
    token_streaming=TokenStreamingConfig(
        enabled_namespaces=["clarifynode:*", "deep_search:researcher"],
        exclude_namespaces=["clarifynode:internal_validation"],
        include_tool_calls=True
    )
)

# Use in streaming
async for event in processor.stream(graph, input_data, config):
    # Process events...
    pass
```

## Performance Considerations

- Pattern extraction is O(n) where n is the number of colon-separated parts in the namespace
- Pattern matching is O(m) where m is the number of enabled/excluded patterns
- The matching is performed for every message chunk, so keep pattern lists reasonably small
- Using `"all"` with exclusions is efficient as it short-circuits after checking exclusions

## Testing

Comprehensive tests are available in `tests/test_namespace_matching.py` covering:
- Pattern extraction logic
- Exact matching
- Wildcard matching
- Nested type matching
- Exclusion logic
- Edge cases

Run tests:
```bash
uv run pytest tests/test_namespace_matching.py -v
```
