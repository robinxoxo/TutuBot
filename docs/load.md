# `/load` Command ⚡

## Description

The `/load` command loads a specified cog/module to enable its functionality. This allows administrators to dynamically add features to the bot without restarting it.

## Usage

```
/load <cog_name>
```

## Parameters

- `cog_name` - The name of the cog to load (without 'cogs.' prefix)
  - Example: "roles", "birthdays"

## Examples

Load the roles module:
```
/load roles
```

Load the birthdays module:
```
/load birthdays
```

## Permissions Required

- Server Administrator permissions
- OR Bot Owner status

## Response Messages

- Success: "`roles` loaded successfully."
- Already Loaded: "`roles` is already loaded."
- Not Found: "`roles` could not be found."
- Error: "Error loading `roles`: [error details]"

## Notes

- Only non-core modules can be loaded with this command
- The module must exist in the cogs directory
- Loading a module makes its commands immediately available (after syncing)
- Use [`/sync`](sync.md) after loading to make new commands available

## Related Commands

- [`/list`](list.md) - Lists all available and loaded cogs
- [`/unload`](unload.md) - Unloads a specified cog
- [`/reload`](reload.md) - Reloads a specified cog
- [`/sync`](sync.md) - Syncs commands to make them available 