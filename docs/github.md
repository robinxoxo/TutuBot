# `/github` Command 🐙

## Description

The `/github` command manages the GitHub integration for TutuBot, allowing administrators to configure settings for receiving automated updates when new code changes are pushed to the repository.

## Usage

```
/github
```

## Parameters

None - This command opens an interactive menu with buttons.

## Functionality

Upon running the command, an interactive menu will appear with:
- Current GitHub integration settings
- Options to modify these settings

The main functions include:
- Setting the current channel as the GitHub update channel
- Viewing the currently configured update channel

## GitHub Integration Features

- **Automated Updates**: Bot monitors the GitHub repository for new commits
- **Commit Notifications**: Sends detailed embed messages about new commits
- **Changelog Display**: Shows commit title, description, author, and timestamp
- **Update Tracking**: Remembers the latest commit to avoid duplicate notifications

## Permissions Required

- Server Administrator permissions
- OR Bot Owner status

## Notes

- GitHub updates are checked every 2 minutes
- For optimal performance, a GitHub API token should be set as `GITHUB_TOKEN` in environment variables
- Without a token, the bot will still function but with stricter API rate limits
- Updates include commit details with links to view changes on GitHub

## Related Commands

- [`/sync`](sync.md) - Synchronizes slash commands
- [`/list`](list.md) - Lists all available and loaded cogs 