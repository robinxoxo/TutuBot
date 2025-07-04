import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
import logging
import typing
import asyncio
import random
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, TYPE_CHECKING

# Import permission checks and UI utilities
from cogs.permissions import is_owner_or_administrator, check_owner_or_admin
from utils.embed_builder import EmbedBuilder

# For type hinting only
if typing.TYPE_CHECKING:
    from main import TutuBot

# Configure logging
log = logging.getLogger(__name__)

# File path for storing active giveaways
GIVEAWAYS_FILE = 'data/giveaways.json'

class GiveawayModal(ui.Modal, title="Create Giveaway"):
    """Modal for creating a new giveaway."""
    
    prize = ui.TextInput(
        label="Prize",
        placeholder="What are you giving away?",
        required=True,
        max_length=100
    )
    
    description = ui.TextInput(
        label="Description (Optional)",
        placeholder="Any additional details about the giveaway.",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    winners = ui.TextInput(
        label="Number of Winners",
        placeholder="(default: 1)",
        required=False,
        max_length=2,
        default="1"
    )
    
    duration = ui.TextInput(
        label="Duration",
        placeholder="Examples: 1d 12h 30m, 1day, 30min, 2hours, 1week, etc.",
        required=True,
        default="1d"
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the form submission."""
        # Validate winners field
        try:
            winners = int(self.winners.value or "1")
            if winners < 1 or winners > 20:
                raise ValueError("Number of winners must be between 1 and 20")
        except ValueError as e:
            embed = EmbedBuilder.error(
                title="✗ Invalid Input",
                description=f"Invalid number of winners: {str(e)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Parse duration
        try:
            seconds = parse_duration(self.duration.value)
            if seconds < 60:  # Minimum duration is 1 minute
                raise ValueError("Duration must be at least 1 minute")
        except ValueError as e:
            embed = EmbedBuilder.error(
                title="✗ Invalid Duration",
                description=str(e)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create the giveaway
        await self.view.cog.create_giveaway(
            interaction=interaction,
            prize=self.prize.value,
            description=self.description.value,
            winners_count=winners,
            duration_seconds=seconds
        )

class GiveawayView(ui.View):
    """View for the giveaway embed with join button."""
    
    def __init__(self, cog: 'GiveawayCog', giveaway_id: str, ends_at: datetime):
        # Set a timeout matching when the giveaway ends
        timeout = (ends_at - datetime.now()).total_seconds()
        super().__init__(timeout=timeout)
        self.cog = cog
        self.giveaway_id = giveaway_id
        self.ends_at = ends_at
        
    @ui.button(label="Enter Giveaway", emoji="🎉", style=discord.ButtonStyle.secondary)
    async def enter_giveaway(self, interaction: discord.Interaction, button: ui.Button):
        """Allow a user to enter the giveaway."""
        # Check if giveaway exists
        giveaway = self.cog.get_giveaway(self.giveaway_id)
        if not giveaway:
            await interaction.response.send_message(content="This giveaway is no longer active!", ephemeral=True)
            return
            
        # Check if giveaway has ended
        if datetime.now() >= self.ends_at:
            await interaction.response.send_message(content="This giveaway has ended!", ephemeral=True)
            return
            
        # Check if user already entered
        user_id = str(interaction.user.id)
        if user_id in giveaway["participants"]:
            await interaction.response.send_message(content="You have already entered this giveaway!", ephemeral=True)
            return
            
        # Add user to participants
        success = await self.cog.add_participant(self.giveaway_id, user_id)
        if success:
            embed = EmbedBuilder.success(
                title="✓ Entry Confirmed",
                description=f"You have entered the giveaway for **{giveaway['prize']}**!"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(content="There was an error entering the giveaway.", ephemeral=True)

class GiveawayManagementView(ui.View):
    """View for creating and managing giveaways."""
    
    def __init__(self, cog: 'GiveawayCog', is_admin: bool = False):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
    
    @ui.button(label="Create Giveaway", emoji="🎁", style=discord.ButtonStyle.secondary, row=0)
    async def create_giveaway(self, interaction: discord.Interaction, button: ui.Button):
        """Open modal to create a new giveaway."""
        modal = GiveawayModal()
        modal.view = self
        await interaction.response.send_modal(modal)
    
    @ui.button(label="List Active Giveaways", emoji="📋", style=discord.ButtonStyle.secondary, row=0)
    async def list_giveaways(self, interaction: discord.Interaction, button: ui.Button):
        """List all active giveaways."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        active_giveaways = self.cog.get_active_giveaways(guild_id)
        
        if not active_giveaways:
            embed = EmbedBuilder.info(
                title="📋 Active Giveaways",
                description="There are no active giveaways in this server."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
            
        # Create embed
        embed = EmbedBuilder.info(
            title="📋 Active Giveaways",
            description=f"There are **{len(active_giveaways)}** active giveaways in this server."
        )
        
        for giveaway_id, giveaway in active_giveaways.items():
            # Add a field for each giveaway
            channel_link = f"<#{giveaway['channel_id']}>"
            ends_timestamp = int(datetime.fromisoformat(giveaway["ends_at"]).timestamp())
            participants_count = len(giveaway["participants"])
            
            field_value = (
                f"• Prize: **{giveaway['prize']}**\n"
                f"• Channel: {channel_link}\n"
                f"• Host: <@{giveaway['host_id']}>\n"
                f"• Ends: <t:{ends_timestamp}:R>\n"
                f"• Entries: {participants_count}\n"
                f"• Winners: {giveaway['winners_count']}"
            )
            
            embed.add_field(
                name=f"Giveaway #{len(embed.fields) + 1}",
                value=field_value,
                inline=False
            )
            
        # Send the response
        await interaction.followup.send(embed=embed, ephemeral=True)

class GiveawayCog(commands.Cog, name="Giveaways"):
    """Commands for managing and participating in giveaways."""
    
    def __init__(self, bot: 'TutuBot'):
        self.bot = bot
        self.giveaways = {}  # Dictionary to store active giveaways
        self.load_giveaways()
        self.check_giveaways.start()
        
    def cog_unload(self):
        """Handle cleanup when cog is unloaded."""
        self.check_giveaways.cancel()
        self.save_giveaways()
    
    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        """Periodic task to check if any giveaways have ended."""
        now = datetime.now()
        ended_giveaways = []
        
        # Find ended giveaways
        for giveaway_id, giveaway in self.giveaways.items():
            if giveaway["status"] == "active" and datetime.fromisoformat(giveaway["ends_at"]) <= now:
                ended_giveaways.append(giveaway_id)
                
        # Process each ended giveaway
        for giveaway_id in ended_giveaways:
            await self.end_giveaway_task(giveaway_id)
    
    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Wait for the bot to be ready before starting the task."""
        await self.bot.wait_until_ready()
    
    def load_giveaways(self):
        """Load giveaways from file."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(GIVEAWAYS_FILE), exist_ok=True)
        
        try:
            if os.path.exists(GIVEAWAYS_FILE):
                with open(GIVEAWAYS_FILE, 'r') as f:
                    self.giveaways = json.load(f)
                log.info(f"Loaded {len(self.giveaways)} giveaways from file")
            else:
                self.giveaways = {}
                log.info("No giveaways file found, starting with empty state")
        except Exception as e:
            log.error(f"Error loading giveaways: {e}")
            self.giveaways = {}
    
    def save_giveaways(self):
        """Save giveaways to file."""
        try:
            os.makedirs(os.path.dirname(GIVEAWAYS_FILE), exist_ok=True)
            with open(GIVEAWAYS_FILE, 'w') as f:
                json.dump(self.giveaways, f, indent=2)
            log.info(f"Saved {len(self.giveaways)} giveaways to file")
        except Exception as e:
            log.error(f"Error saving giveaways: {e}")
    
    def get_giveaway(self, giveaway_id: str) -> Optional[Dict[str, Any]]:
        """Get a giveaway by ID."""
        return self.giveaways.get(giveaway_id)
    
    def get_active_giveaways(self, guild_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get all active giveaways, optionally filtered by guild."""
        active = {}
        for giveaway_id, giveaway in self.giveaways.items():
            if giveaway["status"] == "active":
                if guild_id is None or giveaway["guild_id"] == guild_id:
                    active[giveaway_id] = giveaway
        return active
    
    def get_completed_giveaways(self, guild_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get all completed giveaways, optionally filtered by guild."""
        completed = {}
        for giveaway_id, giveaway in self.giveaways.items():
            if giveaway["status"] == "completed":
                if guild_id is None or giveaway["guild_id"] == guild_id:
                    completed[giveaway_id] = giveaway
        return completed
    
    async def add_participant(self, giveaway_id: str, user_id: str) -> bool:
        """Add a participant to a giveaway."""
        if giveaway_id not in self.giveaways:
            return False
            
        giveaway = self.giveaways[giveaway_id]
        if giveaway["status"] != "active":
            return False
            
        if user_id not in giveaway["participants"]:
            giveaway["participants"].append(user_id)
            self.save_giveaways()
            
            # Update the giveaway message with new participant count
            try:
                channel = self.bot.get_channel(int(giveaway["channel_id"]))
                if channel:
                    message = await channel.fetch_message(int(giveaway["message_id"]))
                    if message:
                        embed = message.embeds[0]
                        # Update the participants field
                        for i, field in enumerate(embed.fields):
                            if field.name == "👥 Entries":
                                embed.set_field_at(
                                    i, 
                                    name="👥 Entries",
                                    value=str(len(giveaway["participants"])),
                                    inline=True
                                )
                                break
                        await message.edit(embed=embed)
            except Exception as e:
                log.error(f"Error updating giveaway message: {e}")
                
        return True
    
    async def create_giveaway(self, interaction: discord.Interaction, prize: str, description: str, 
                              winners_count: int, duration_seconds: int):
        """Create a new giveaway."""
        # Generate a unique ID
        giveaway_id = f"giveaway_{int(datetime.now().timestamp())}_{interaction.guild_id}"
        
        # Calculate end time
        ends_at = datetime.now() + timedelta(seconds=duration_seconds)
        
        # Create giveaway data
        giveaway = {
            "id": giveaway_id,
            "prize": prize,
            "description": description,
            "winners_count": winners_count,
            "created_at": datetime.now().isoformat(),
            "ends_at": ends_at.isoformat(),
            "host_id": str(interaction.user.id),
            "guild_id": str(interaction.guild_id),
            "channel_id": str(interaction.channel_id),
            "participants": [],
            "winners": [],
            "status": "active",
            "message_id": None  # Will be set after message is sent
        }
        
        # Create embed for giveaway
        embed = discord.Embed(
            title="🎉 Giveaway",
            description=f"**{prize}**",
            color=discord.Color.gold()
        )
        
        if description:
            embed.add_field(name="Description", value=description, inline=False)
        
        # Add winner and entries information in a more compact layout
        embed.add_field(name="🏆 Winners", value=str(winners_count), inline=True)
        embed.add_field(name="👥 Entries", value="0", inline=True)
        
        # Add end time with better formatting
        embed.add_field(name="⏰ Ends", value=f"<t:{int(ends_at.timestamp())}:R>", inline=True)
        
        # Add hosted by information to the footer instead
        embed.set_footer(text=f"Hosted by {interaction.user.name} • Click the button below to enter!")
        
        # Add thumbnail if user has avatar
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        # Create view with enter button
        view = GiveawayView(self, giveaway_id, ends_at)
        
        # Send a response to acknowledge the modal submission
        # The modal submission already used interaction.response, so we need to use followup
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            # Send in the current channel
            message = await interaction.channel.send(embed=embed, view=view)
            giveaway["message_id"] = str(message.id)
            
            # Save the giveaway
            self.giveaways[giveaway_id] = giveaway
            self.save_giveaways()
            
            # Notify the user
            success_embed = EmbedBuilder.success(
                title="✓ Giveaway Created",
                description=f"Your giveaway for **{prize}** has been created and will end <t:{int(ends_at.timestamp())}:R>."
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)
        
        except Exception as e:
            log.error(f"Error creating giveaway: {e}")
            error_embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"There was an error creating the giveaway: {str(e)}"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    async def end_giveaway_task(self, giveaway_id: str):
        """End a giveaway and select winners."""
        giveaway = self.giveaways.get(giveaway_id)
        if not giveaway or giveaway["status"] != "active":
            return
            
        # Mark as completed
        giveaway["status"] = "completed"
        giveaway["ended_at"] = datetime.now().isoformat()
        
        # Select winners
        participants = giveaway["participants"]
        winners_count = min(giveaway["winners_count"], len(participants))
        winners = []
        
        if participants and winners_count > 0:
            # Select random winners
            winners = random.sample(participants, winners_count)
            giveaway["winners"] = winners
            
        # Save changes
        self.save_giveaways()
        
        # Update or send winner announcement
        try:
            channel = self.bot.get_channel(int(giveaway["channel_id"]))
            if not channel:
                log.error(f"Channel not found for giveaway {giveaway_id}")
                return
                
            try:
                # Try to get the original message
                message = await channel.fetch_message(int(giveaway["message_id"]))
                
                # Update the original embed
                if message:
                    embed = message.embeds[0]
                    embed.color = discord.Color.dark_gray()
                    
                    # Find and update fields
                    for i, field in enumerate(embed.fields):
                        # Update the Ends field
                        if field.name == "⏰ Ends":
                            embed.set_field_at(
                                i,
                                name="⏳ Ended",
                                value=f"<t:{int(datetime.now().timestamp())}:R>",
                                inline=field.inline
                            )
                    
                    # Update the title
                    embed.title = "🎉 Giveaway Ended"
                    
                    await message.edit(embed=embed, view=None)
            except discord.NotFound:
                log.warning(f"Original giveaway message not found for {giveaway_id}")
                # Continue with winner announcement even if original message is gone
            
            # Create winner announcement
            winner_text = ""
            if winners:
                winner_text = "\n".join([f"• <@{winner}>" for winner in winners])
                
                winner_embed = discord.Embed(
                    title="🎉 Giveaway Winners",
                    description=f"The giveaway for **{giveaway['prize']}** has ended!",
                    color=discord.Color.brand_green()
                )
                
                winner_embed.add_field(
                    name=f"🏆 Winner{'s' if len(winners) > 1 else ''}",
                    value=winner_text,
                    inline=False
                )
                
                if giveaway["description"]:
                    winner_embed.add_field(
                        name="📝 Description",
                        value=giveaway["description"],
                        inline=False
                    )
                
                # Add original message link if available
                if giveaway["message_id"]:
                    message_link = f"https://discord.com/channels/{giveaway['guild_id']}/{giveaway['channel_id']}/{giveaway['message_id']}"
                    winner_embed.add_field(
                        name="Link to Giveaway",
                        value=f"[via Message]({message_link})",
                        inline=False
                    )
                    
                # Get host user for thumbnail
                host = self.bot.get_user(int(giveaway["host_id"]))
                if host and host.avatar:
                    winner_embed.set_thumbnail(url=host.avatar.url)
                    
                await channel.send(
                    content=f"🎊 Congratulations {', '.join([f'<@{winner}>' for winner in winners])}! You won the giveaway!",
                    embed=winner_embed
                )
            else:
                # No winners (no participants)
                no_winner_embed = discord.Embed(
                    title="🎉 Giveaway Ended 🎉",
                    description=f"The giveaway for **{giveaway['prize']}** has ended, but there were no participants!",
                    color=discord.Color.brand_red()
                )
                
                if giveaway["description"]:
                    no_winner_embed.add_field(
                        name="📝 Description",
                        value=giveaway["description"],
                        inline=False
                    )
                
                # Get host user for thumbnail
                host = self.bot.get_user(int(giveaway["host_id"]))
                if host and host.avatar:
                    no_winner_embed.set_thumbnail(url=host.avatar.url)
                
                await channel.send(embed=no_winner_embed)
                
        except Exception as e:
            log.error(f"Error ending giveaway {giveaway_id}: {e}")
    
    @app_commands.command(name="giveaways", description="[Admin] Manage and start giveaways!")
    @is_owner_or_administrator()
    async def giveaway_command(self, interaction: discord.Interaction):
        """Command to manage giveaways."""
        # Check if this is a guild interaction
        if not interaction.guild:
            await interaction.response.send_message(content="This command can only be used in a server.", ephemeral=True)
            return
        
        # Create embed and view for giveaway management
        embed = EmbedBuilder.info(
            title="🎉 Giveaway Management",
            description="Select an action to manage giveaways."
        )
        view = GiveawayManagementView(self, True)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @giveaway_command.error
    async def giveaway_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for the giveaway command."""
        if isinstance(error, app_commands.errors.CheckFailure):
            embed = EmbedBuilder.error(
                title="✗ Access Denied",
                description="You need administrator permissions to use this command."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"An error occurred: {str(error)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            log.error(f"Error in giveaway command: {error}")

async def setup(bot: commands.Bot):
    """Add the giveaway cog to the bot."""
    await bot.add_cog(GiveawayCog(bot))

# Utility functions for time parsing

def parse_duration(duration_str: str) -> int:
    """Parse a duration string into seconds.
    
    Supports flexible formats like:
    - 1d 2h 3m (days, hours, minutes)
    - 1day 2hours 3minutes
    - 1 (assumes minutes if no unit)
    - 30min
    - 1week
    - 1month
    - 1year
    """
    if not duration_str.strip():
        raise ValueError("Duration cannot be empty")
        
    # If it's just a number, assume minutes
    if duration_str.strip().isdigit():
        return int(duration_str.strip()) * 60
    
    # Map of time units to seconds
    time_units = {
        # Days
        'd': 86400,
        'day': 86400,
        'days': 86400,
        # Hours
        'h': 3600,
        'hour': 3600,
        'hours': 3600,
        'hr': 3600,
        'hrs': 3600,
        # Minutes
        'm': 60,
        'min': 60,
        'mins': 60,
        'minute': 60,
        'minutes': 60,
        # Weeks
        'w': 604800,
        'week': 604800,
        'weeks': 604800,
        # Months (approximated)
        'month': 2592000,  # 30 days
        'months': 2592000,
        # Years (approximated)
        'y': 31536000,  # 365 days
        'year': 31536000,
        'years': 31536000
    }
    
    total_seconds = 0
    current_number = ""
    current_unit = ""
    
    # Add a space at the end to process the last token
    duration_str = duration_str.lower().strip() + " "
    
    for char in duration_str:
        if char.isdigit():
            # If we had a unit before, process it with the previous number
            if current_unit and current_number:
                for unit, seconds in time_units.items():
                    if current_unit == unit:
                        total_seconds += int(current_number) * seconds
                        break
                current_unit = ""
                current_number = char
            else:
                current_number += char
        elif char.isalpha():
            current_unit += char
        elif char.isspace():
            # Process the current number and unit
            if current_number:
                # If there's no unit, assume it's the start of a new value
                if not current_unit:
                    current_unit = "m"  # Default to minutes if no unit specified
                
                # Check if the current unit matches any known unit
                unit_match = False
                for unit, seconds in time_units.items():
                    if current_unit == unit:
                        total_seconds += int(current_number) * seconds
                        unit_match = True
                        break
                
                if not unit_match:
                    # Try partial matching for longer unit names
                    for unit, seconds in time_units.items():
                        if unit.startswith(current_unit):
                            total_seconds += int(current_number) * seconds
                            unit_match = True
                            break
                
                # If still no match, raise an error
                if not unit_match:
                    raise ValueError(f"Unknown time unit: {current_unit}")
                    
                current_number = ""
                current_unit = ""
    
    if total_seconds <= 0:
        raise ValueError("Invalid duration format. Examples: 1d, 30min, 2hours, 1week")
        
    return total_seconds

def format_time_remaining(timestamp_str: str) -> str:
    """Format the time remaining for a giveaway in a human-readable form."""
    now = datetime.now()
    end_time = datetime.fromisoformat(timestamp_str)
    remaining = end_time - now
    
    if remaining.total_seconds() <= 0:
        return "Ended"
        
    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    
    return " ".join(parts)

def format_time_ago(timestamp_str: str) -> str:
    """Format how long ago a giveaway ended."""
    try:
        end_time = datetime.fromisoformat(timestamp_str)
        return f"<t:{int(end_time.timestamp())}:R>"
    except (ValueError, TypeError):
        return "Unknown" 