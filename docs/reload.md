# `/reload` Command 🔄

## Description

The `/reload` command reloads a specified cog/module to apply code changes without restarting the bot. This is extremely useful during development and when updating features.

## Usage

```
/reload <cog_name>
```

## Parameters

- `cog_name` - The name of the cog to reload (without 'cogs.' prefix)
  - Example: "roles", "birthdays"

## Examples

Reload the roles module:
```
/reload roles
```

Reload the birthdays module:
```
/reload birthdays
```

## Permissions Required

- Server Administrator permissions
- OR Bot Owner status

## Response Messages

- Success: "`roles` reloaded successfully."
- Not Loaded: "`roles` not loaded. Attempting to load instead."
- Loaded Instead: "`roles` was loaded instead."
- Not Found: "`roles` not found."
- Core Module: "Cannot reload core cog `cogmanager`."
- Error: "Error reloading `roles`: [error details]"

## Notes

- Core modules (cogmanager, faq) cannot be reloaded
- If a module is not loaded, the command will attempt to load it
- Reloading applies code changes without affecting the bot's operation
- Unlike `/load` and `/unload`, the `/reload` command is deferred (shows a thinking state) as reloading can take a moment

## Related Commands

- [`/list`](list.md) - Lists all available and loaded cogs
- [`/load`](load.md) - Loads a specified cog
- [`/unload`](unload.md) - Unloads a specified cog
- [`/sync`](sync.md) - Syncs commands if command definitions changed 