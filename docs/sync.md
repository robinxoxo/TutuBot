# `/sync` Command 🔄

## Description

The `/sync` command synchronizes slash commands to make them available in the Discord interface. This is necessary when commands are added, removed, or modified in the bot's code. Commands are automatically synced to the configured guild on startup, but **global syncing must be done manually** with this command.

## Usage

```
/sync [target]
```

## Parameters

- `target` - Where to sync commands (default: "guild")
  - `guild` - Syncs commands to the current server only (immediate effect)
  - `global` - Syncs commands globally to all servers (can take up to an hour to propagate)

## Examples

Sync commands to the current server:
```
/sync guild
```

Sync commands globally:
```
/sync global
```

## Permissions Required

- Server Administrator permissions
- OR Bot Owner status

## Notes

- Commands are automatically synced to the configured guild on bot startup
- **Global syncing** is not done automatically and requires running `/sync global`
- Guild syncing is recommended for testing new commands as changes appear immediately
- Global syncing affects all servers where the bot is installed but takes longer to propagate
- This command is essential after adding new cogs or updating command definitions
- If slash commands aren't working in servers other than the main guild, use `/sync global`

## Related Commands

- [`/list`](list.md) - Lists all available and loaded cogs
- [`/load`](load.md) - Loads a specified cog
- [`/reload`](reload.md) - Reloads a specified cog 