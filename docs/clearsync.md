# `/clearsync` Command 🔄

## Description

The `/clearsync` command completely clears all registered slash commands and then re-registers the current set of commands. This is the most effective way to remove outdated or stale commands without needing to kick and reinvite the bot.

## Usage

```
/clearsync [target]
```

## Parameters

- `target` - Where to clear and sync commands (default: "guild")
  - `guild` - Clears and syncs commands for the current server only (immediate effect)
  - `global` - Clears and syncs commands globally for all servers (can take up to an hour to propagate)

## Examples

Clear and re-sync commands for the current server:
```
/clearsync guild
```

Clear and re-sync commands globally:
```
/clearsync global
```

## Permissions Required

- Server Administrator permissions
- OR Bot Owner status

## How It Works

1. The command first clears all registered slash commands from Discord's system
2. It then syncs the current set of active commands from the bot
3. This removes any "stale" commands that may appear as "Unknown Application" or commands from removed cogs

## When to Use

Use this command when:
- You see "Unknown Application" errors on slash commands
- Old commands are still appearing in the slash command menu after they've been removed from the bot
- You've unloaded several cogs and want to clean up the command list
- You've made major changes to the bot's command structure

## Notes

- Guild syncing will immediately update commands for that specific server
- Global syncing affects all servers but takes longer to propagate (up to an hour)
- This is a safer alternative to kicking and reinviting the bot to refresh commands
- After running this command, users may need to reopen their Discord client to see the changes

## Related Commands

- [`/sync`](sync.md) - Standard command sync without clearing first
- [`/list`](list.md) - Lists all available and loaded cogs
- [`/load`](load.md) - Loads a specified cog
- [`/unload`](unload.md) - Unloads a specified cog 