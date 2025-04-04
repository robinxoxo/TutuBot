# `/unload` Command 🛑

## Description

The `/unload` command unloads a specified cog/module to disable its functionality. This allows administrators to remove features from the bot without restarting it.

## Usage

```
/unload <cog_name>
```

## Parameters

- `cog_name` - The name of the cog to unload (without 'cogs.' prefix)
  - Example: "roles", "birthdays"

## Examples

Unload the roles module:
```
/unload roles
```

Unload the birthdays module:
```
/unload birthdays
```

## Permissions Required

- Server Administrator permissions
- OR Bot Owner status

## Response Messages

- Success: "`roles` unloaded successfully."
- Not Loaded: "`roles` is not loaded."
- Not Found: "`roles` not found."
- Core Module: "Cannot unload core cog `cogmanager`."
- Error: "Error unloading `roles`: [error details]"

## Notes

- Core modules (cogmanager, faq) cannot be unloaded
- Unloading a module removes its commands from the bot
- Use [`/sync`](sync.md) after unloading to update available commands
- Unloaded modules remain available for loading later

## Related Commands

- [`/list`](list.md) - Lists all available and loaded cogs
- [`/load`](load.md) - Loads a specified cog
- [`/reload`](reload.md) - Reloads a specified cog
- [`/sync`](sync.md) - Syncs commands to update the UI 