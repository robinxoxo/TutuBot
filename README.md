# 🤖 TutuBot

A feature-rich Discord bot built with discord.py that uses modern Discord features like slash commands, buttons, and embedded messages.

## ✨ Features

TutuBot comes with several modules (cogs) that provide different functionality:

• **CogManager**: Administrative commands to load, unload, and manage bot modules
• **FAQ**: Create and manage frequently asked questions for your server
• **Roles**: Manage server roles and provide self-assign role capabilities
• **Streaming**: Track and notify when members go live on streaming platforms
• **Info**: Provides informational commands about the server and bot
• **Events**: Handle various Discord events and automated responses
• **Misc**: Miscellaneous utility commands
• **GitHub**: GitHub integration for tracking repository updates and sending notifications

## 🛠️ Setup

### Prerequisites
• Python 3.8 or higher
• Discord Bot Token
• Discord Server with admin permissions

### Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/TutuBot.git
cd TutuBot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with the following variables:
```
ADMIN_TOKEN=your_discord_bot_token
BOT_OWNER_ID=your_discord_user_id
GUILD_ID=your_primary_server_id
CORE_COGS=cogs.cogmanager
GITHUB_TOKEN=your_github_api_token  # Optional but recommended
```

4. Start the bot:
```bash
python main.py
```

## 📝 Configuration

The bot uses environment variables for configuration:

• `ADMIN_TOKEN`: Your Discord bot token
• `BOT_OWNER_ID`: Discord user ID of the bot owner
• `GUILD_ID`: Primary Discord server ID where commands should sync instantly
• `CORE_COGS`: Comma-separated list of essential cogs that cannot be unloaded (default: cogs.cogmanager)
• `GITHUB_TOKEN`: GitHub API token for repository monitoring (optional but recommended)

## 📚 Commands

TutuBot uses Discord's slash commands. Here are some key commands:

• `/sync`: Synchronize commands to your server or globally
• `/load`: Load a cog module
• `/unload`: Unload a non-core cog module
• `/reload`: Reload a cog module
• `/list`: List all available and loaded cogs
• `/roles`: Manage and self-assign roles
• `/github`: Configure GitHub integration and update notifications

For detailed documentation on commands, see the `docs` directory.

## 🧩 Adding New Cogs

New functionality can be added by creating new cogs in the `cogs` directory. All cogs should:

1. Import required dependencies
2. Create a class that inherits from `commands.Cog`
3. Include a constructor that accepts the bot instance
4. Register slash commands using `@app_commands.command()` decorator
5. Include a setup function to register the cog

Example structure:
```python
def setup(bot):
    bot.add_cog(YourCogName(bot))
```

## 🔄 GitHub Integration

TutuBot includes GitHub integration that:

• Monitors repository for new commits automatically
• Sends detailed notifications about code changes
• Displays commit information in embedded Discord messages
• Provides direct links to view changes on GitHub

To configure:
1. Set your `GITHUB_TOKEN` in the .env file (optional but recommended)
2. Use the `/github` command to set up an update channel

## 📜 License

[MIT License](LICENSE)

## 🙏 Acknowledgements

Built with [discord.py](https://github.com/Rapptz/discord.py) 