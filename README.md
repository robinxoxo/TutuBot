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
| Permissions            | `/permissions`           | Permission checks & decorators for admin/owner-only commands                                 |
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

## Getting Started

### Prerequisites

- Python 3.8 or higher
- A Discord application with bot token and required permissions
- Git (for cloning the repository)

### Installation

1. **Create a Discord Bot Application**:
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application and add a bot user
   - Enable necessary Privileged Gateway Intents (Server Members, Message Content, Presence)
   - Copy your bot token for the next steps

2. **Clone the repository**:
   ```powershell
   git clone https://github.com/robinxoxo/TutuBot.git
   cd TutuBot
   ```

3. **Set up a virtual environment** (recommended):
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

5. **Configure environment variables**:
   Create a `.env` file in the root directory with the following:
   ```env
   ADMIN_TOKEN=your-bot-token-here
   BOT_OWNER_ID=your-discord-user-id
   GUILD_ID=your-target-guild-id
   ```
   
   - `ADMIN_TOKEN`: Your Discord bot token
   - `BOT_OWNER_ID`: Your Discord user ID (right-click on your name → Copy ID with developer mode enabled)
   - `GUILD_ID`: The ID of the guild where you want to use the bot

### Running the Bot

1. **Start the bot**:
   ```powershell
   python main.py
   ```

2. **Invite the bot to your server**:
   - Go to OAuth2 → URL Generator in the Discord Developer Portal
   - Select the `bot` and `applications.commands` scopes
   - Select appropriate bot permissions
   - Use the generated URL to invite the bot to your server

3. **Using the bot**:
   - Once the bot is running and connected, you can use `/help` to see available commands
   - The bot will automatically register all slash commands to the guild specified in your `.env` file

### Troubleshooting

- If commands aren't appearing, ensure the bot has the `applications.commands` scope permission
- Verify that all required environment variables are set correctly
- Check the console output for any error messages
- Make sure all required intents are enabled in the Discord Developer Portal

## Configuration

All configuration is handled via environment variables in `.env`:

- `ADMIN_TOKEN`: Bot token used to authenticate with Discord.
- `BOT_OWNER_ID`: Discord user ID permitted to use owner-only commands.
- `GUILD_ID`: Single guild where slash commands are synced.

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
