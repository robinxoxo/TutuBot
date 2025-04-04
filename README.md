# 🤖 TutuBot

A feature-rich Discord bot built with discord.py that uses modern Discord features like slash commands, buttons, and embedded messages.

## ✨ Features

TutuBot comes with several modules (cogs) that provide different functionality:

• **CogManager**: Administrative commands to load, unload, and manage bot modules
• **FAQ**: Create and manage frequently asked questions for your server
• **Birthdays**: Track member birthdays and send automatic birthday announcements
• **Roles**: Manage server roles and provide self-assign role capabilities

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
CORE_COGS=cogs.cogmanager,cogs.faq
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
• `CORE_COGS`: Comma-separated list of essential cogs that cannot be unloaded

## 📚 Commands

TutuBot uses Discord's slash commands. Here are some key commands:

• `/sync`: Synchronize commands to your server or globally
• `/load`: Load a cog module
• `/unload`: Unload a non-core cog module
• `/birthday`: Manage birthday settings
• `/roles`: Manage and self-assign roles

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

## 📜 License

[MIT License](LICENSE)

## 🙏 Acknowledgements

Built with [discord.py](https://github.com/Rapptz/discord.py) 