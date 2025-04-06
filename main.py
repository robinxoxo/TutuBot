import discord
import os
# import asyncio # No longer needed for running bots concurrently
from discord.ext import commands
from dotenv import load_dotenv
import logging
import time # Import time module for timestamp
import discord.utils # Import discord.utils

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
BOT_OWNER_ID = os.getenv("BOT_OWNER_ID")
CORE_COGS = os.getenv("CORE_COGS", "cogs.cogmanager").split(",")
GUILD_ID = os.getenv("GUILD_ID", 0)  # Default to the specified guild ID

# Validate variables
if not all([ADMIN_TOKEN, BOT_OWNER_ID]):
    raise ValueError("One or more essential environment variables (ADMIN_TOKEN, BOT_OWNER_ID) are missing.")

# Ensure BOT_OWNER_ID is not None before conversion
assert BOT_OWNER_ID is not None

# Convert owner ID to int
try:
    BOT_OWNER_ID_INT = int(BOT_OWNER_ID)
    GUILD_ID_INT = int(GUILD_ID)
except ValueError:
     raise ValueError("BOT_OWNER_ID or GUILD_ID environment variable must be an integer.")

class TutuBot(commands.Bot):
    """Discord bot with slash command support."""
    
    def __init__(self, *args, initial_cogs: list[str], owner_id: int, guild_id: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_cogs = initial_cogs
        self.owner_id = owner_id
        self.guild_id = guild_id
        self.log = logging.getLogger("TutuBot")

    async def setup_hook(self) -> None:
        """Loads initial cogs and syncs commands to guild only."""
        self.log.info(f"Attempting to load initial cogs: {self.initial_cogs}")
        for cog_path in self.initial_cogs:
            try:
                await self.load_extension(cog_path)
                self.log.info(f"Successfully loaded cog: {cog_path}")
            except Exception as e:
                self.log.exception(f"Failed to load cog {cog_path}: {e}")

    async def on_message(self, message: discord.Message) -> None:
        """Event triggered when a message is received.
        
        This overrides the default on_message handler to prevent automatic command processing,
        since we're using slash commands exclusively.
        """
        # Make sure we have a valid message and author
        if message.author is None or self.user is None:
            return
            
        # Don't process commands from this bot
        if message.author.id == self.user.id:
            return
            
        # We're not using traditional command processing, so don't call process_commands
        # Uncomment below line if you want to support both slash and traditional commands
        # await self.process_commands(message)
        
        # This prevents type errors because we properly handle the message here
        # but don't do anything with it since we're using slash commands
        
    async def on_ready(self):
        """Event triggered when the bot is ready."""
        assert self.user is not None
        self.log.info(f'Logged in as {self.user.name} ({self.user.id})')
        self.log.info(f'Currently in {len(self.guilds)} servers.')
        self.log.info('------')

        # Set presence
        try:
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name="to /help"
            )
            await self.change_presence(status=discord.Status.online, activity=activity)
            self.log.info("Presence set successfully.")
        except Exception as e:
            self.log.exception(f"Failed to set presence: {e}")

# Define intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.presences = True  # Required for activity/streaming status tracking

# All cogs to load at startup
initial_cogs = CORE_COGS.copy()
if "cogs.birthdays" not in initial_cogs:
    initial_cogs.append("cogs.birthdays")
if "cogs.roles" not in initial_cogs:
    initial_cogs.append("cogs.roles")
if "cogs.streaming" not in initial_cogs:
    initial_cogs.append("cogs.streaming")
if "cogs.info" not in initial_cogs:
    initial_cogs.append("cogs.info")
if "cogs.faq" not in initial_cogs:
    initial_cogs.append("cogs.faq")

# Create bot
bot = TutuBot(
    command_prefix="!",  # Set a prefix even if not used to prevent errors
    intents=intents,
    initial_cogs=initial_cogs,
    owner_id=BOT_OWNER_ID_INT,
    guild_id=GUILD_ID_INT,
    activity=None,
    status=discord.Status.idle
)

# Main execution
if __name__ == "__main__":
    if not ADMIN_TOKEN:
        log.critical("ADMIN_TOKEN not found in environment variables. Bot cannot start.")
    else:
        try:
            log.info("Starting bot...")
            bot.run(ADMIN_TOKEN)
        except discord.LoginFailure:
            log.critical("Failed to log in: Improper token provided.")
        except KeyboardInterrupt:
            log.info("Received exit signal, shutting down...")
        except Exception as e:
            log.exception(f"An error occurred during bot execution: {e}")
