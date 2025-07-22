# Raindrop.io MCP Server

Model Context Protocol server for Raindrop.io bookmark management. Works with Claude Code and other MCP clients.

## Quick Setup for Claude Code

### 1. Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Clone and initialize
```bash
git clone <repository-url>
cd raindrop-io-mcp
uv sync
```

### 3. Get Raindrop.io API token
- Go to [Raindrop.io Settings > Integrations](https://app.raindrop.io/settings/integrations)
- Create new app or use existing
- Copy API token

### 4. Add to Claude Code
```bash
claude mcp add raindrop-io --scope project -e RAINDROP_API_TOKEN=your_token_here -- uv --directory /absolute/path/to/raindrop-io-mcp run python -m src.main
```

### 5. Restart Claude Code
Server provides these 7 tools:
- `search_bookmarks` - Search bookmarks with filters
- `create_bookmark` - Create new bookmarks
- `get_bookmark` - Get bookmark details
- `update_bookmark` - Update existing bookmarks  
- `delete_bookmark` - Remove bookmarks
- `list_collections` - List all collections
- `create_collection` - Create new collections

## Manual Configuration

Add to `.mcp.json`:
```json
{
  "mcpServers": {
    "raindrop-io": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory", 
        "/absolute/path/to/raindrop-io-mcp",
        "run", 
        "python", 
        "-m", 
        "src.main"
      ],
      "env": {
        "RAINDROP_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Troubleshooting

**Server shows "Failed" in Claude Code:**
- Check `uv --version` works
- Verify absolute path is correct
- Restart Claude Code after changes

**Tools not available:**
```bash
claude mcp list  # Should show raindrop-io
claude mcp remove raindrop-io
# Re-add with correct settings
```

**Test manually:**
```bash
cd /path/to/raindrop-io-mcp
uv run python -m src.main
# Should start and wait for MCP input
```

## Development

```bash
# Install deps
uv sync

# Run tests
uv run python -m pytest tests/

# Format code
uv run python -m black src/

# Type check
uv run python -m mypy src/
```

## Requirements

- Python 3.11+
- uv package manager
- Raindrop.io API token

## License

MIT