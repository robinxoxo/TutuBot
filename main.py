import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
log = logging.getLogger(__name__)

# Load and validate environment variables
load_dotenv()
TOKEN = os.getenv("ADMIN_TOKEN") or os.getenv("DISCORD_TOKEN")
owner_id_env = os.getenv("BOT_OWNER_ID")
if not TOKEN or not owner_id_env:
    raise ValueError("Environment variables ADMIN_TOKEN and BOT_OWNER_ID must be set.")
try:
    OWNER_ID = int(owner_id_env)
except ValueError:
    raise ValueError("BOT_OWNER_ID environment variable must be an integer.")
guild_id_env = os.getenv("GUILD_ID", "0")
try:
    GUILD_ID = int(guild_id_env)
except ValueError:
    raise ValueError("GUILD_ID environment variable must be an integer.")

class TutuBot(commands.Bot):
    """Discord bot with slash command support."""
    
    def __init__(self, *args, initial_cogs: list[str], owner_id: int, guild_id: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_cogs = initial_cogs
        self.owner_id = owner_id
        self.guild_id = guild_id
        self.log = logging.getLogger("TutuBot")
        self.launch_time = time.time()  # Record launch time

    async def setup_hook(self) -> None:
        """Load extensions and sync slash commands."""
        for ext in self.initial_cogs:
            try:
                await self.load_extension(ext)
                self.log.info(f"Loaded extension {ext}")
            except Exception:
                self.log.exception(f"Failed to load extension {ext}")
        # Sync slash commands
        self.log.info("Syncing application commands...")
        if self.guild_id:
            await self.tree.sync(guild=discord.Object(id=self.guild_id))
        else:
            await self.tree.sync()
        self.log.info("Application commands synced.")

    async def on_message(self, message: discord.Message) -> None:
        """Process prefix commands and ignore the bot's own messages."""
        if message.author.id == self.user.id:
            return
        await self.process_commands(message)

    async def on_ready(self):
        """Log bot readiness and set presence."""
        self.log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.log.info(f"Connected to {len(self.guilds)} guild(s). Uptime: {time.time() - self.launch_time:.2f}s")
        activity = discord.Activity(type=discord.ActivityType.listening, name="/help")
        await self.change_presence(status=discord.Status.online, activity=activity)
        self.log.info("Presence set to listening to /help.")

# Define intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.presences = True  # Required for activity/streaming status tracking

# All cogs to load at startup
DEFAULT_COGS = [
    "cogs.permissions", "cogs.roles", "cogs.info", "cogs.reminders",
    "cogs.faq", "cogs.events", "cogs.misc", "cogs.github",
    "cogs.giveaways", "cogs.logging", "cogs.support", "cogs.twitch"
]
"""
Only core cog is cogmanager; combine with DEFAULT_COGS
"""
initial_cogs = ["cogs.cogmanager"] + DEFAULT_COGS

bot = TutuBot(
    command_prefix="!",  # Prefix for test commands
    intents=intents,
    initial_cogs=initial_cogs,
    owner_id=OWNER_ID,
    guild_id=GUILD_ID,
    status=discord.Status.idle
)

def main():
    """Entry point for running the bot."""
    if not TOKEN:
        log.critical("ADMIN_TOKEN not set. Exiting.")
        return
    log.info("Starting bot...")
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        log.critical("Failed to log in: invalid token.")
    except KeyboardInterrupt:
        log.info("Shutdown requested. Exiting.")
    except Exception:
        log.exception("Unexpected error running bot.")

if __name__ == "__main__":
    main()
