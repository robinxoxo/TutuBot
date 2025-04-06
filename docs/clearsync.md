# `/clearsync` Command 🔄

## Description

The `/clearsync` command completely clears all registered slash commands without resyncing them. This removes outdated or stale commands without needing to kick and reinvite the bot. After clearing, you can use the `/sync` command separately to register commands back.

## Usage

```
/clearsync [target]
```

## Parameters

- `target` - Where to clear commands (default: "guild")
  - `guild` - Clears commands for the current server only (immediate effect)
  - `global` - Clears commands globally for all servers (can take up to an hour to propagate)

## Examples

Clear commands for the current server:
```
/clearsync guild
```

Clear commands globally:
```
/clearsync global
```

## Permissions Required

- Server Administrator permissions
- OR Bot Owner status

## How It Works

1. The command clears all registered slash commands from Discord's system
2. To restore commands, you must use the `/sync` command separately
3. This two-step process gives you more control when removing "stale" commands

## When to Use

Use this command when:
- You see "Unknown Application" errors on slash commands
- Old commands are still appearing in the slash command menu after they've been removed from the bot
- You've unloaded several cogs and want to clean up the command list
- You've made major changes to the bot's command structure and want to start fresh

## Notes

- Guild clearing will immediately remove commands for that specific server
- Global clearing affects all servers but takes longer to propagate (up to an hour)
- This is a safer alternative to kicking and reinviting the bot to refresh commands
- After running this command, you must use `/sync` to restore your commands
- Without syncing after clearing, users will not see any slash commands for the bot

## Related Commands

- [`/sync`](sync.md) - Syncs commands to restore functionality after clearing
- [`/list`](list.md) - Lists all available and loaded cogs
- [`/load`](load.md) - Loads a specified cog
- [`/unload`](unload.md) - Unloads a specified cog 