import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
import typing
import os
import aiohttp
import asyncio
import json
from datetime import datetime, timedelta

# For type hinting only
if typing.TYPE_CHECKING:
    from main import TutuBot

# Configure logging
log = logging.getLogger(__name__)

class TwitchCog(commands.Cog, name="Twitch"):
    """Handles Twitch stream notifications."""

    def __init__(self, bot: 'TutuBot'):
        """Initialize the Twitch cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.access_token = None
        self.token_expires_at = None
        
        # Dictionary to store streamer data
        # Key: streamer login name, Value: {"user_id": id, "is_live": bool, "last_stream_id": id}
        self.streamers = {}
        
        # Load streamers from file
        self.data_file = "data/twitch_streamers.json"
        self.load_streamers()
        
        # Start background tasks
        self.check_streams.start()

    def cog_unload(self):
        """Called when the cog is unloaded."""
        self.check_streams.cancel()

    def load_streamers(self):
        """Load streamers from file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    if "streamers" in data:
                        self.streamers = data["streamers"]
                        log.info(f"Loaded {len(self.streamers)} Twitch streamers from file")
            else:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
                # Save empty streamers dictionary
                self.save_streamers()
        except Exception as e:
            log.error(f"Error loading Twitch streamers: {e}")

    def save_streamers(self):
        """Save streamers to file."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump({"streamers": self.streamers}, f, indent=4)
            log.info(f"Saved {len(self.streamers)} Twitch streamers to file")
        except Exception as e:
            log.error(f"Error saving Twitch streamers: {e}")

    async def get_access_token(self):
        """Get or refresh Twitch API access token."""
        if (not self.access_token or 
           (self.token_expires_at and datetime.now() >= self.token_expires_at)):
            if not self.client_id or not self.client_secret:
                log.error("Twitch Client ID or Client Secret not set in environment variables")
                return None
                
            try:
                async with aiohttp.ClientSession() as session:
                    url = "https://id.twitch.tv/oauth2/token"
                    payload = {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "client_credentials"
                    }
                    
                    async with session.post(url, data=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.access_token = data["access_token"]
                            # Set expiration time (usually 60 days, but subtract 1 day to be safe)
                            expires_in = data.get("expires_in", 86400)
                            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 86400)
                            log.info("Successfully obtained Twitch API access token")
                        else:
                            log.error(f"Failed to get Twitch access token: {response.status}")
                            return None
            except Exception as e:
                log.error(f"Error getting Twitch access token: {e}")
                return None
                
        return self.access_token

    async def get_user_id(self, username):
        """Get Twitch user ID from username."""
        token = await self.get_access_token()
        if not token:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.twitch.tv/helix/users?login={username}"
                headers = {
                    "Client-ID": self.client_id,
                    "Authorization": f"Bearer {token}"
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["data"]:
                            return data["data"][0]["id"]
                    else:
                        log.error(f"Failed to get user ID for {username}: {response.status}")
        except Exception as e:
            log.error(f"Error getting user ID for {username}: {e}")
            
        return None

    @tasks.loop(minutes=2)
    async def check_streams(self):
        """Check if tracked streamers are live and send notifications."""
        if not self.streamers:
            return
            
        token = await self.get_access_token()
        if not token:
            return
            
        user_ids = [data["user_id"] for data in self.streamers.values() if "user_id" in data]
        if not user_ids:
            return
            
        # Twitch API limits to 100 IDs per request
        for i in range(0, len(user_ids), 100):
            batch = user_ids[i:i+100]
            await self._check_stream_batch(batch, token)
            
    async def _check_stream_batch(self, user_ids, token):
        """Check a batch of streamers (up to 100)."""
        try:
            async with aiohttp.ClientSession() as session:
                # Build query string for multiple user_ids
                user_id_query = "&".join([f"user_id={uid}" for uid in user_ids])
                url = f"https://api.twitch.tv/helix/streams?{user_id_query}"
                headers = {
                    "Client-ID": self.client_id,
                    "Authorization": f"Bearer {token}"
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        live_streams = {stream["user_id"]: stream for stream in data.get("data", [])}
                        
                        # Check each streamer in our list
                        for username, streamer_data in self.streamers.items():
                            user_id = streamer_data.get("user_id")
                            if not user_id or user_id not in user_ids:
                                continue
                                
                            # Streamer is currently live
                            if user_id in live_streams:
                                stream_data = live_streams[user_id]
                                
                                # Check if this is a new stream
                                if (not streamer_data.get("is_live") or 
                                    streamer_data.get("last_stream_id") != stream_data["id"]):
                                    
                                    # Update streamer data
                                    self.streamers[username]["is_live"] = True
                                    self.streamers[username]["last_stream_id"] = stream_data["id"]
                                    self.save_streamers()
                                    
                                    # Send notification
                                    await self._send_live_notification(username, stream_data)
                            
                            # Streamer was live before but is now offline
                            elif streamer_data.get("is_live"):
                                self.streamers[username]["is_live"] = False
                                self.save_streamers()
                    else:
                        log.error(f"Failed to check streams: {response.status}")
        except Exception as e:
            log.error(f"Error checking streams: {e}")

    async def _send_live_notification(self, username, stream_data):
        """Send a notification that a streamer is live."""
        announce_channel_id = self.streamers[username].get("announce_channel_id")
        if not announce_channel_id:
            return
            
        try:
            channel = self.bot.get_channel(int(announce_channel_id))
            if not channel:
                log.error(f"Could not find channel with ID {announce_channel_id}")
                return
                
            # Create embed
            embed = discord.Embed(
                title=f"🔴 {stream_data['user_name']} is now live on Twitch!",
                description=stream_data["title"],
                url=f"https://twitch.tv/{username}",
                color=discord.Color.purple()
            )
            
            # Add game info if available
            if stream_data.get("game_name"):
                embed.add_field(name="Playing", value=stream_data["game_name"], inline=True)
                
            # Add viewer count
            embed.add_field(name="Viewers", value=str(stream_data["viewer_count"]), inline=True)
            
            # Add stream thumbnail
            thumbnail = stream_data["thumbnail_url"].replace("{width}", "640").replace("{height}", "360")
            embed.set_image(url=f"{thumbnail}?{datetime.now().timestamp()}")
            
            # Add streamer profile as thumbnail
            embed.set_thumbnail(url=f"https://static-cdn.jtvnw.net/jtv_user_pictures/{username}-profile_image-300x300.png")
            
            # Add footer with timestamp
            embed.set_footer(text=f"Stream started at {stream_data['started_at']}")
            
            await channel.send(embed=embed)
            log.info(f"Sent live notification for {username}")
        except Exception as e:
            log.error(f"Error sending live notification for {username}: {e}")

    @check_streams.before_loop
    async def before_check_streams(self):
        """Wait for bot to be ready before starting the stream check loop."""
        await self.bot.wait_until_ready()
        # Wait additional 30 seconds to ensure all connections are established
        await asyncio.sleep(30)

    @app_commands.command(name="twitch-add", description="[Admin] Add a Twitch streamer to track")
    @app_commands.describe(
        username="Twitch username to track",
        channel="Discord channel to post notifications in"
    )
    async def twitch_add(self, interaction: discord.Interaction, username: str, channel: discord.TextChannel = None):
        """Add a Twitch streamer to track.
        
        Args:
            interaction: The Discord interaction
            username: Twitch username to track
            channel: Discord channel to post notifications in
        """
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Error",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Normalize username
        username = username.lower()
        
        # Check if streamer is already being tracked
        if username in self.streamers:
            embed = discord.Embed(
                title="❓ Streamer Already Tracked",
                description=f"The streamer `{username}` is already being tracked.",
                color=discord.Color.yellow()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Get user_id from Twitch API
        user_id = await self.get_user_id(username)
        if not user_id:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Could not find Twitch user `{username}`. Please check the spelling and try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Use current channel if not specified
        if not channel:
            channel = interaction.channel
            
        # Add streamer to tracking list
        self.streamers[username] = {
            "user_id": user_id,
            "is_live": False,
            "last_stream_id": None,
            "announce_channel_id": str(channel.id)
        }
        
        # Save streamers list
        self.save_streamers()
        
        embed = discord.Embed(
            title="✓ Streamer Added",
            description=f"Now tracking Twitch streamer `{username}`.\nLive notifications will be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="twitch-remove", description="[Admin] Remove a Twitch streamer from tracking")
    @app_commands.describe(username="Twitch username to stop tracking")
    async def twitch_remove(self, interaction: discord.Interaction, username: str):
        """Remove a Twitch streamer from tracking.
        
        Args:
            interaction: The Discord interaction
            username: Twitch username to stop tracking
        """
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Error",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Normalize username
        username = username.lower()
        
        # Check if streamer is being tracked
        if username not in self.streamers:
            embed = discord.Embed(
                title="❌ Error",
                description=f"The streamer `{username}` is not being tracked.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Remove streamer from tracking list
        del self.streamers[username]
        
        # Save streamers list
        self.save_streamers()
        
        embed = discord.Embed(
            title="✓ Streamer Removed",
            description=f"No longer tracking Twitch streamer `{username}`.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="twitch-list", description="List all tracked Twitch streamers")
    async def twitch_list(self, interaction: discord.Interaction):
        """List all tracked Twitch streamers.
        
        Args:
            interaction: The Discord interaction
        """
        if not self.streamers:
            embed = discord.Embed(
                title="📋 Tracked Streamers",
                description="No streamers are currently being tracked.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
            return
            
        embed = discord.Embed(
            title="📋 Tracked Streamers",
            description=f"Currently tracking {len(self.streamers)} Twitch streamers:",
            color=discord.Color.blue()
        )
        
        for username, data in self.streamers.items():
            channel_id = data.get("announce_channel_id")
            channel = self.bot.get_channel(int(channel_id)) if channel_id else None
            channel_mention = channel.mention if channel else "Unknown channel"
            
            status = "🔴 Live now" if data.get("is_live") else "⚫ Offline"
            
            embed.add_field(
                name=f"{username}",
                value=f"• Status: {status}\n• Notifications: {channel_mention}",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

async def setup(bot: 'TutuBot'):
    """Sets up the TwitchCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(TwitchCog(bot))
    log.info("TwitchCog loaded.") 