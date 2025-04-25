# Tutu Bot

Tutu Bot is a modular Discord bot designed to streamline community management for a single guild. It provides a comprehensive suite of features for events, permissions, roles, support, moderation, and more—all accessible via modern Discord slash commands and interactive UI components.

## Purpose & Philosophy

Tutu Bot aims to:
- Simplify server management for admins, mods, and users alike.
- Centralize all core community features in one bot, reducing clutter.
- Use Discord's latest UI (buttons, selects, modals) for a seamless, argument-free experience.
- Enforce clear, consistent, and visually appealing embedded responses for all interactions.

## Features & Commands

| Feature                | Slash Command(s)        | Description                                                                                  |
|------------------------|------------------------|----------------------------------------------------------------------------------------------|
| Event Scheduling       | `/events`              | Manage, create, post, and delete events with interactive buttons (admin only)                |
| Permissions            | (internal)             | Permission checks & decorators for admin/owner-only commands                                 |
| Role Management        | `/roles`               | Interactive role assignment/removal via dropdowns and buttons                                |
| Info & Help            | `/botinfo`, `/serverinfo`, `/help` | Show bot/server info and a list of all commands                                  |
| FAQ                    | `/help`                | Lists commands and answers common questions                                                  |
| Miscellaneous          | `/purge` (admin), `/embedcolors` (admin) | Bulk delete messages, manage embed colors                             |
| GitHub Integration     | `/github` (admin)      | Manage GitHub integration settings                                                          |
| Giveaways              | `/giveaways` (admin)   | Create, manage, and enter giveaways                                                         |
| Moderation & Logging   | `/logging` (admin)     | Configure logging channels/events                                                           |
| Support Tickets        | `/support`             | Open a support ticket or get help                                                           |
| Twitch Integration     | `/twitch` (admin)      | Manage Twitch notifications and tracked streamers                                            |
| Streaming Notifications| `/streaming` (admin)   | Manage streaming notifications for members                                                  |
| Cog Management         | `/load`, `/unload`, `/reload`, `/list`, `/info`, `/sync` (admin/owner) | Manage cogs and sync commands |

- All commands use Discord UI components instead of optional arguments.
- Admin/owner-only commands are permission-protected.

## Interaction & Response Style

- **All responses are embedded messages** with a required header emoji (e.g., ✓ for success, ✗ for error, 📚 for info).
- Uses • for bullet points in embed descriptions and fields.
- Buttons use ButtonStyle.secondary except destructive actions (ButtonStyle.danger).
- Users are mentioned with @ (using `.mention`) even in ephemeral messages.
- Errors are handled with informative embeds, following tutu-rules for emoji and formatting.
- Test commands use the `!` prefix and are not registered as slash commands.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- `pip`
- A Discord application token with bot permissions

### Installation

1. Clone the repository:
   ```powershell
   git clone https://github.com/robinxoxo/TutuBot.git
   ```
2. Install dependencies:
   ```powershell
   cd TutuBot
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with the following variables:
   ```env
   ADMIN_TOKEN=<your-bot-token>
   BOT_OWNER_ID=<your-discord-user-id>
   GUILD_ID=<target-guild-id>
   # Optional: comma-separated list of core cog paths
   CORE_COGS=cogs.cogmanager
   ```
4. (Optional) Edit `CORE_COGS` or adjust `initial_cogs` in `main.py` to enable or disable modules.

5. Start the bot:
   ```powershell
   python main.py
   ```

## Configuration

All configuration is handled via environment variables in `.env`:

- `ADMIN_TOKEN`: Bot token used to authenticate with Discord.
- `BOT_OWNER_ID`: Discord user ID permitted to use owner-only commands.
- `GUILD_ID`: Single guild where slash commands are synced.
- `CORE_COGS`: Base list of cogs to load; additional cogs appended automatically.

## Running Tests

This project uses pytest:

```powershell
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

Please follow existing code patterns and adhere to PEP8.

## License

This project is released under the MIT License. See `LICENSE` file for details.
