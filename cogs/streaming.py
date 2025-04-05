import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
import logging
import typing
from typing import Dict, Optional, Set
import os
import asyncio
import json
from datetime import datetime, timedelta

# Import our custom permission check
from utils.permission_checks import is_owner_or_administrator

# For type hinting only
if typing.TYPE_CHECKING:
    from main import TutuBot

# Configure logging
log = logging.getLogger(__name__)

class StreamingSettingsView(ui.View):
    """View for managing streaming notification settings."""
    
    def __init__(self, cog: 'StreamingCog'):
        super().__init__(timeout=60)
        self.cog = cog
        
    @ui.button(label="Set Notification Channel", style=discord.ButtonStyle.secondary, emoji="📢")
    async def set_channel(self, interaction: discord.Interaction, button: ui.Button):
        """Set the channel for streaming notifications."""
        if interaction.channel is None:
            embed = discord.Embed(
                title="✗ Error",
                description="Cannot determine the current channel.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Update the notification channel for this guild
        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        if not guild_id:
            embed = discord.Embed(
                title="✗ Error",
                description="This command can only be used in a server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        channel_id = interaction.channel_id
        
        self.cog.settings[guild_id] = {
            "notification_channel": channel_id,
            "enabled": True
        }
        self.cog.save_settings()
        
        embed = discord.Embed(
            title="✓ Channel Set",
            description=f"Streaming notifications will now be sent to <#{channel_id}>.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)
        
    @ui.button(label="Toggle Notifications", style=discord.ButtonStyle.secondary, emoji="🔔")
    async def toggle_notifications(self, interaction: discord.Interaction, button: ui.Button):
        """Toggle streaming notifications on/off."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        if not guild_id:
            embed = discord.Embed(
                title="✗ Error", 
                description="This command can only be used in a server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Get current settings for this guild
        guild_settings = self.cog.settings.get(guild_id, {})
        current_state = guild_settings.get("enabled", False)
        
        # Toggle the enabled state
        new_state = not current_state
        
        # Update settings
        if guild_id not in self.cog.settings:
            self.cog.settings[guild_id] = {}
            
        self.cog.settings[guild_id]["enabled"] = new_state
        
        # If enabling and no channel is set, use the current channel
        if new_state and "notification_channel" not in self.cog.settings[guild_id]:
            self.cog.settings[guild_id]["notification_channel"] = interaction.channel_id
            
        self.cog.save_settings()
        
        state_text = "enabled" if new_state else "disabled"
        embed = discord.Embed(
            title=f"✓ Notifications {state_text.title()}",
            description=f"Streaming notifications are now **{state_text}**.",
            color=discord.Color.green() if new_state else discord.Color.red()
        )
        
        # Add channel info if enabled
        if new_state and "notification_channel" in self.cog.settings[guild_id]:
            channel_id = self.cog.settings[guild_id]["notification_channel"]
            embed.add_field(
                name="Notification Channel",
                value=f"<#{channel_id}>",
                inline=False
            )
            
        await interaction.response.edit_message(embed=embed, view=None)
        
    @ui.button(label="Show Current Settings", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def show_settings(self, interaction: discord.Interaction, button: ui.Button):
        """Show current streaming notification settings."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        if not guild_id:
            embed = discord.Embed(
                title="✗ Error",
                description="This command can only be used in a server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Get current settings for this guild
        guild_settings = self.cog.settings.get(guild_id, {})
        enabled = guild_settings.get("enabled", False)
        channel_id = guild_settings.get("notification_channel")
        
        embed = discord.Embed(
            title="⚙️ Streaming Notification Settings",
            color=discord.Color.blue()
        )
        
        status = "Enabled" if enabled else "Disabled"
        embed.add_field(
            name="Status",
            value=f"**{status}**",
            inline=False
        )
        
        if channel_id:
            embed.add_field(
                name="Notification Channel",
                value=f"<#{channel_id}>",
                inline=False
            )
        else:
            embed.add_field(
                name="Notification Channel",
                value="No channel set",
                inline=False
            )
            
        # Show currently streaming members if any
        streaming_members = self.cog.currently_streaming.get(guild_id, set())
        if streaming_members:
            streaming_list = []
            guild = interaction.guild
            
            if guild:
                for member_id in streaming_members:
                    member = guild.get_member(int(member_id))
                    if member:
                        streaming_list.append(f"• {member.mention}")
                        
            if streaming_list:
                embed.add_field(
                    name="Currently Streaming",
                    value="\n".join(streaming_list),
                    inline=False
                )
                
        await interaction.response.edit_message(embed=embed, view=None)
        
    async def on_timeout(self):
        """Clear items when the view times out."""
        self.clear_items()

class StreamingCog(commands.Cog, name="Streaming"):
    """Detects when server members are streaming and sends notifications."""

    def __init__(self, bot: 'TutuBot'):
        """Initialize the Streaming cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        
        # Dictionary to store settings for each guild
        # Key: guild_id, Value: {"notification_channel": channel_id, "enabled": bool}
        self.settings = {}
        
        # Dictionary to track who is currently streaming in each guild
        # Key: guild_id, Value: set of member IDs who are streaming
        self.currently_streaming = {}
        
        # Settings file
        self.settings_file = "data/streaming_settings.json"
        self.load_settings()
        
        # Start background task
        self.check_streaming_status.start()

    def cog_unload(self):
        """Called when the cog is unloaded."""
        self.check_streaming_status.cancel()

    def load_settings(self):
        """Load settings from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    if "settings" in data:
                        self.settings = data["settings"]
                        log.info(f"Loaded streaming settings for {len(self.settings)} guilds")
            else:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
                # Save empty settings dictionary
                self.save_settings()
        except Exception as e:
            log.error(f"Error loading streaming settings: {e}")

    def save_settings(self):
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump({"settings": self.settings}, f, indent=4)
            log.info(f"Saved streaming settings for {len(self.settings)} guilds")
        except Exception as e:
            log.error(f"Error saving streaming settings: {e}")

    @tasks.loop(seconds=30)
    async def check_streaming_status(self):
        """Check if members are streaming and send notifications."""
        for guild in self.bot.guilds:
            guild_id = str(guild.id)
            
            # Skip if notifications are disabled for this guild
            guild_settings = self.settings.get(guild_id, {})
            if not guild_settings.get("enabled", False):
                continue
                
            # Get notification channel
            channel_id = guild_settings.get("notification_channel")
            if not channel_id:
                continue
                
            channel = guild.get_channel(int(channel_id))
            if not channel or not isinstance(channel, (discord.TextChannel, discord.Thread)):
                continue
                
            # Initialize set of currently streaming members for this guild if needed
            if guild_id not in self.currently_streaming:
                self.currently_streaming[guild_id] = set()
                
            # Check each member's status
            currently_streaming_set = set()
            
            for member in guild.members:
                if member.bot:
                    continue
                    
                # Check if member is streaming
                streaming_activity = None
                for activity in member.activities:
                    if isinstance(activity, discord.Streaming):
                        streaming_activity = activity
                        break
                        
                if streaming_activity:
                    member_id = str(member.id)
                    currently_streaming_set.add(member_id)
                    
                    # Send notification if this is a new stream
                    if member_id not in self.currently_streaming[guild_id]:
                        await self._send_streaming_notification(channel, member, streaming_activity)
                        
            # Update the set of currently streaming members
            # and identify those who stopped streaming
            stopped_streaming = self.currently_streaming[guild_id] - currently_streaming_set
            
            # Update the currently streaming set
            self.currently_streaming[guild_id] = currently_streaming_set
            
            # Optional: Send notification when members stop streaming
            # for member_id in stopped_streaming:
            #     member = guild.get_member(int(member_id))
            #     if member:
            #         await self._send_stopped_streaming_notification(channel, member)

    async def _send_streaming_notification(self, channel, member, activity):
        """Send a notification that a member is streaming."""
        try:
            # Create embed
            embed = discord.Embed(
                title=f"🔴 {member.display_name} is now streaming!",
                description=activity.name if activity.name else "Started a stream",
                url=activity.url,
                color=discord.Color.purple()
            )
            
            # Add platform information if available
            if hasattr(activity, 'platform'):
                embed.add_field(
                    name="Platform",
                    value=activity.platform,
                    inline=True
                )
                
            # Add game information if available
            if hasattr(activity, 'game'):
                embed.add_field(
                    name="Playing",
                    value=activity.game,
                    inline=True
                )
                
            # Add member avatar
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
                
            # Set footer with timestamp
            embed.set_footer(text=f"Stream started at {discord.utils.utcnow().strftime('%H:%M:%S UTC')}")
            
            await channel.send(content=f"{member.mention} is now streaming!", embed=embed)
            log.info(f"Sent streaming notification for {member.name}#{member.discriminator} in {channel.guild.name}")
        except Exception as e:
            log.error(f"Error sending streaming notification: {e}")

    @check_streaming_status.before_loop
    async def before_check_streaming_status(self):
        """Wait for bot to be ready before starting the status check loop."""
        await self.bot.wait_until_ready()
        # Wait additional 10 seconds to ensure all connections are established
        await asyncio.sleep(10)

    @app_commands.command(name="streaming", description="[Admin] Manage streaming notifications")
    @is_owner_or_administrator()
    async def streaming(self, interaction: discord.Interaction):
        """Main command for managing streaming notifications.
        
        Args:
            interaction: The Discord interaction
        """
        # Create the embed
        embed = discord.Embed(
            title="🎮 Streaming Notifications",
            description="Configure notifications for when members start streaming.",
            color=discord.Color.purple()
        )
        
        # Add instructions
        embed.add_field(
            name="Available Actions", 
            value=(
                "• **Set Notification Channel** - Choose where notifications are sent\n"
                "• **Toggle Notifications** - Turn notifications on/off\n"
                "• **Show Current Settings** - View your current configuration"
            ),
            inline=False
        )
        
        # Create the view with buttons
        view = StreamingSettingsView(self)
        
        # Send the response
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @streaming.error
    async def streaming_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for the streaming command.
        
        Args:
            interaction: The Discord interaction
            error: The error that occurred
        """
        if isinstance(error, app_commands.errors.CheckFailure):
            embed = discord.Embed(
                title="✗ Error",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="✗ Error",
                description=f"An error occurred: {str(error)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            log.error(f"Error in streaming command: {error}")

async def setup(bot: 'TutuBot'):
    """Sets up the StreamingCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(StreamingCog(bot))
    log.info("StreamingCog loaded.") 