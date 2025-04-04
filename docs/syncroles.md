# `/syncroles` Command 🏷️

## Description

The `/syncroles` command synchronizes server roles with the bot's configuration. It creates missing roles defined in the configuration and updates the colors of existing roles if needed.

## Usage

```
/syncroles
```

## Parameters

None

## Examples

```
/syncroles
```

## Permissions Required

- Server Administrator permissions
- OR Bot Owner status

## Features

The `/syncroles` command performs the following operations:

1. **Creates Missing Roles:**
   - Creates any roles defined in `utils/role_definitions.py` that don't exist in the server
   - Assigns the proper color defined in the configuration
   - Groups roles by their defined categories

2. **Updates Existing Roles:**
   - Checks if existing roles have the correct color as defined in the configuration
   - Updates role colors if they differ from the configuration

3. **Provides Detailed Reports:**
   - Lists created roles with confirmation marks
   - Lists updated roles with what fields were updated
   - Lists any failed operations with error indicators

## Example Output

```
Created 3 Roles:
✓ Content Creator
✓ Artist
✓ Developer

Updated 2 Roles:
✓ Minecraft (color)
✓ Fortnite (color)

Failed Operations (1):
✗ Call of Duty (update)
```

## Notes

- This command is useful when first setting up the bot in a new server
- It can also be used to restore any accidentally deleted roles
- The command requires the "Manage Roles" permission in Discord
- Roles with higher positions than the bot's highest role cannot be modified

## Configuration

The roles are defined in `utils/role_definitions.py` with the following format:

```python
ROLE_DEFINITIONS = {
    "role_id": {
        "name": "Display Name", 
        "emoji": "Emoji", 
        "category": RoleCategory.CATEGORY, 
        "description": "Optional description",
        "color": discord.Color (optional)
    },
    # More roles...
}
```

## Related Commands

- [`/roles`](../user/roles.md) - User command to manage their own roles 