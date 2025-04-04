# `/list` Command 📋

## Description

The `/list` command displays all available and currently loaded cogs/modules in the bot. It provides a status overview of which components are active and inactive.

## Usage

```
/list
```

## Parameters

None

## Example Output

```
Core Modules:
✓ cogmanager
✓ faq

Optional Modules:
✓ roles
✓ birthdays
✗ moderation
```

In this output:
- ✓ indicates an active (loaded) module
- ✗ indicates an inactive (unloaded) module

## Permissions Required

- Server Administrator permissions
- OR Bot Owner status

## Notes

- Core modules cannot be unloaded and will always show as active
- Optional modules can be dynamically loaded/unloaded
- This command is useful for checking what features are currently available

## Related Commands

- [`/load`](load.md) - Loads a specified cog
- [`/unload`](unload.md) - Unloads a specified cog
- [`/reload`](reload.md) - Reloads a specified cog 