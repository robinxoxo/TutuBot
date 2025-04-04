import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
import typing
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, List, Union, Tuple

# For type hinting only
if typing.TYPE_CHECKING:
    from main import TutuBot

# Configure logging
log = logging.getLogger(__name__)

# Birthday data file
BIRTHDAY_FILE = "data/birthdays.json"

class BirthdayDropdown(discord.ui.View):
    """View for birthday selection dropdowns."""
    
    def __init__(self, user_to_set: Optional[discord.Member] = None):
        """Initialize the dropdown view.
        
        Args:
            user_to_set: The user to set the birthday for (if admin setting for someone else)
        """
        super().__init__(timeout=300)  # 5 minute timeout
        self.month = None
        self.day = None
        self.user_to_set = user_to_set
        
        # Add month selector
        month_select = discord.ui.Select(
            placeholder="Select month",
            options=[
                discord.SelectOption(label="January", value="1"),
                discord.SelectOption(label="February", value="2"),
                discord.SelectOption(label="March", value="3"),
                discord.SelectOption(label="April", value="4"),
                discord.SelectOption(label="May", value="5"),
                discord.SelectOption(label="June", value="6"),
                discord.SelectOption(label="July", value="7"),
                discord.SelectOption(label="August", value="8"),
                discord.SelectOption(label="September", value="9"),
                discord.SelectOption(label="October", value="10"),
                discord.SelectOption(label="November", value="11"),
                discord.SelectOption(label="December", value="12"),
            ]
        )
        
        # Month selection callback
        async def month_callback(interaction: discord.Interaction):
            self.month = int(month_select.values[0])
            await interaction.response.defer()
            # Update day dropdown based on month selection
            self.update_day_options()
        
        month_select.callback = month_callback
        self.add_item(month_select)
        self.month_select = month_select
        
        # Add day selector with placeholder options
        # Will be updated when month is selected
        day_select = discord.ui.Select(
            placeholder="Select day (select month first)",
            disabled=True,
            options=[discord.SelectOption(label="Select month first", value="0")]
        )
        
        # Day selection callback
        async def day_callback(interaction: discord.Interaction):
            self.day = int(day_select.values[0])
            await interaction.response.defer()
        
        day_select.callback = day_callback
        self.add_item(day_select)
        self.day_select = day_select
    
    def update_day_options(self):
        """Update the day options based on the selected month."""
        if not self.month:
            return
            
        # Set days based on month
        days_in_month = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # Accounting for leap years
        max_days = days_in_month[self.month]
        
        # Create day options
        day_options = [
            discord.SelectOption(label=str(day), value=str(day))
            for day in range(1, max_days + 1)
        ]
        
        # Update the day select menu
        self.day_select.options = day_options
        self.day_select.placeholder = f"Select day (1-{max_days})"
        self.day_select.disabled = False
    
    @discord.ui.button(label="Submit", style=discord.ButtonStyle.secondary)
    async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle submission of the birthday."""
        if not self.month or not self.day:
            error_embed = discord.Embed(
                title="✗ Selection Error",
                description="Please select both month and day first!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
            
        try:
            # Get the cog instance
            cog = interaction.client.get_cog("Birthdays")  # type: ignore
            if not cog:
                error_embed = discord.Embed(
                    title="✗ System Error",
                    description="An error occurred. Please try again later.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
                
            # Determine the user to set birthday for
            target_user = self.user_to_set if self.user_to_set else interaction.user
            
            # Set the birthday
            result = await cog.set_birthday(interaction, target_user, {"month": self.month, "day": self.day})
            await interaction.response.send_message(embed=result, ephemeral=True)
            self.stop()
        except Exception as e:
            log.error(f"Error in submit_button: {e}")
            error_embed = discord.Embed(
                title="✗ System Error",
                description="An error occurred while processing your birthday. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

class BirthdayCog(commands.Cog, name="Birthdays"):
    """Handles birthday tracking and notifications."""

    def __init__(self, bot: 'TutuBot'):
        """Initialize the Birthday cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.birthdays = {}  # Format: {guild_id: {user_id: {"month": m, "day": d}}}
        self.load_birthdays()
        
        # Create the data directory if it doesn't exist
        os.makedirs(os.path.dirname(BIRTHDAY_FILE), exist_ok=True)
        
        # Start birthday check loop
        self.birthday_check.start()
    
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.birthday_check.cancel()
    
    def load_birthdays(self):
        """Load birthdays from the JSON file."""
        try:
            if os.path.exists(BIRTHDAY_FILE):
                with open(BIRTHDAY_FILE, 'r') as f:
                    self.birthdays = json.load(f)
        except Exception as e:
            log.error(f"Error loading birthdays: {e}")
            self.birthdays = {}
    
    def save_birthdays(self):
        """Save birthdays to the JSON file."""
        try:
            with open(BIRTHDAY_FILE, 'w') as f:
                json.dump(self.birthdays, f, indent=4)
        except Exception as e:
            log.error(f"Error saving birthdays: {e}")
    
    @tasks.loop(hours=1)
    async def birthday_check(self):
        """Check for birthdays every hour and send announcements."""
        now = datetime.now()
        # Only check once per day, at the first hour
        if now.hour != 0:
            return
            
        today_month = now.month
        today_day = now.day
        
        for guild_id, guild_birthdays in self.birthdays.items():
            try:
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    continue
                    
                # Find birthdays for today
                birthday_users = []
                for user_id, birthday in guild_birthdays.items():
                    if birthday["month"] == today_month and birthday["day"] == today_day:
                        member = guild.get_member(int(user_id))
                        if member:
                            birthday_users.append(member)
                
                if birthday_users:
                    # Try to find a general or birthday channel
                    announcement_channel = None
                    for channel_name in ["birthdays", "birthday", "general", "chat"]:
                        channel = discord.utils.get(guild.text_channels, name=channel_name)
                        if channel:
                            announcement_channel = channel
                            break
                    
                    if not announcement_channel:
                        # Just use the first text channel we can send to
                        for channel in guild.text_channels:
                            if channel.permissions_for(guild.me).send_messages:
                                announcement_channel = channel
                                break
                    
                    if announcement_channel:
                        # Create mentions list
                        mentions = [user.mention for user in birthday_users]
                        users_text = ", ".join(mentions)
                        
                        # Create fancy birthday embed
                        embed = discord.Embed(
                            title="🎂 Happy Birthday!",
                            description=f"Everyone please join us in wishing a fantastic birthday to:\n\n**{users_text}**!",
                            color=discord.Color.gold()
                        )
                        
                        # Add individual fields for each birthday user
                        for user in birthday_users:
                            embed.add_field(
                                name=f"🎉 {user.display_name}",
                                value=f"• Have an amazing day!\n• May all your wishes come true!",
                                inline=True
                            )
                            
                        embed.set_footer(text=f"Use /birthdays set to add your own birthday!")
                        
                        await announcement_channel.send(embed=embed)
                        log.info(f"Sent birthday announcement in {guild.name} for {len(birthday_users)} users")
            except Exception as e:
                log.error(f"Error checking birthdays for guild {guild_id}: {e}")
    
    @birthday_check.before_loop
    async def before_birthday_check(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()
    
    def format_birthday(self, birthday: Dict[str, int]) -> str:
        """Format a birthday dict into a readable string."""
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        month_str = month_names[birthday["month"] - 1]
        return f"{birthday['day']} {month_str}"
    
    def get_next_birthday(self, birthday: Dict[str, int]) -> datetime:
        """Calculate the next occurrence of this birthday."""
        now = datetime.now()
        this_year = now.year
        
        # Create datetime for this year's birthday
        birthday_this_year = datetime(this_year, birthday["month"], birthday["day"])
        
        # If the birthday has already passed this year, use next year
        if birthday_this_year < now:
            return datetime(this_year + 1, birthday["month"], birthday["day"])
        else:
            return birthday_this_year
    
    def format_time_until(self, target_date: datetime) -> str:
        """Format the time until the next birthday."""
        now = datetime.now()
        delta = target_date - now
        
        if delta.days == 0:
            return "Today!"
        elif delta.days == 1:
            return "Tomorrow!"
        elif delta.days < 7:
            return f"{delta.days} days"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''}"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months != 1 else ''}"
        else:
            return "Over a year"
        
    async def set_birthday(self, interaction: discord.Interaction, user: discord.Member, birthday_data: Dict[str, int]) -> discord.Embed:
        """Set a birthday for a user and generate response embed.
        
        Args:
            interaction: The Discord interaction
            user: The user to set birthday for
            birthday_data: Dict with month and day
            
        Returns:
            Embed with response message
        """
        guild_id = str(interaction.guild_id) if interaction.guild_id is not None else "0"
        user_id = str(user.id)
        
        # Save the birthday
        if guild_id not in self.birthdays:
            self.birthdays[guild_id] = {}
            
        self.birthdays[guild_id][user_id] = birthday_data
        self.save_birthdays()
        
        formatted_date = self.format_birthday(birthday_data)
        next_birthday = self.get_next_birthday(birthday_data)
        time_until = self.format_time_until(next_birthday)
        
        if user.id == interaction.user.id:
            # User setting their own birthday
            embed = discord.Embed(
                title="✓ Birthday Set!",
                description=f"Your birthday has been set to **{formatted_date}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Next Birthday", value=f"• In {time_until}", inline=False)
        else:
            # Admin setting someone else's birthday
            embed = discord.Embed(
                title="✓ Birthday Set!",
                description=f"{user.display_name}'s birthday has been set to **{formatted_date}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Next Birthday", value=f"• In {time_until}", inline=False)
            
        return embed

    @app_commands.command(name="birthdays", description="Set or view birthdays in the server.")
    @app_commands.describe(action="Action to perform", user="User to view or set birthday for (admin only)")
    @app_commands.choices(action=[
        app_commands.Choice(name="Set birthday", value="set"),
        app_commands.Choice(name="View your birthday", value="view_self"),
        app_commands.Choice(name="View server birthdays", value="view_all"),
        app_commands.Choice(name="View someone's birthday", value="view_user"),
        app_commands.Choice(name="Set birthday for user (admin)", value="set_admin")
    ])
    async def birthdays_command(self, interaction: discord.Interaction, 
                               action: str,
                               user: Optional[discord.Member] = None):
        """Manage birthdays with an interactive dropdown UI.
        
        Args:
            interaction: The Discord interaction
            action: Action to perform (set, view_self, view_all, view_user, set_admin)
            user: User to view birthday of or set for (only needed for certain actions)
        """
        if not interaction.guild:
            error_embed = discord.Embed(
                title="✗ Command Error",
                description="This command can only be used in a server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
            
        guild_id = str(interaction.guild.id)
        
        # Initialize guild data if not exists
        if guild_id not in self.birthdays:
            self.birthdays[guild_id] = {}
        
        # Handle different actions
        if action == "set":
            # User wants to set their own birthday with dropdowns
            embed = discord.Embed(
                title="🎂 Set Your Birthday",
                description="Please select your birthday month and day using the dropdowns below.",
                color=discord.Color.blue()
            )
            view = BirthdayDropdown()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return
            
        elif action == "set_admin":
            # Admin wants to set someone else's birthday
            # Check permissions
            is_admin = False
            if interaction.guild:
                permissions = interaction.permissions
                is_admin = permissions.administrator
                
            if not is_admin:
                error_embed = discord.Embed(
                    title="✗ Permission Denied",
                    description="You need administrator permissions to set birthdays for others.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
                
            if not user:
                error_embed = discord.Embed(
                    title="✗ Missing Information",
                    description="Please specify a user to set the birthday for.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
                
            embed = discord.Embed(
                title="🎂 Admin Birthday Setup",
                description=f"Setting birthday for **{user.display_name}**. Please select month and day using the dropdowns below.",
                color=discord.Color.blue()
            )
            view = BirthdayDropdown(user_to_set=user)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return
            
        elif action == "view_self":
            # View own birthday
            user_id = str(interaction.user.id)
            
            if user_id in self.birthdays[guild_id]:
                birthday = self.birthdays[guild_id][user_id]
                formatted_date = self.format_birthday(birthday)
                next_birthday = self.get_next_birthday(birthday)
                time_until = self.format_time_until(next_birthday)
                
                embed = discord.Embed(
                    title="🎂 Your Birthday",
                    description=f"Your birthday is set to **{formatted_date}**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Next Birthday", value=f"In {time_until}", inline=False)
                embed.add_field(
                    name="Reset Birthday", 
                    value="• Use `/birthdays set` to change your birthday", 
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="🎂 Your Birthday",
                    description="You haven't set your birthday yet!",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Set Your Birthday", 
                    value="• Use `/birthdays set` to set your birthday with a dropdown menu", 
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        elif action == "view_user":
            # View someone else's birthday
            if not user:
                error_embed = discord.Embed(
                    title="✗ Missing Information",
                    description="Please specify a user to view their birthday.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
                
            user_id = str(user.id)
            if user_id in self.birthdays[guild_id]:
                birthday = self.birthdays[guild_id][user_id]
                formatted_date = self.format_birthday(birthday)
                next_birthday = self.get_next_birthday(birthday)
                time_until = self.format_time_until(next_birthday)
                
                embed = discord.Embed(
                    title=f"🎂 {user.display_name}'s Birthday",
                    description=f"Their birthday is on **{formatted_date}**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Coming up", value=f"In {time_until}", inline=False)
            else:
                embed = discord.Embed(
                    title=f"🎂 {user.display_name}'s Birthday",
                    description=f"They haven't set their birthday yet!",
                    color=discord.Color.blue()
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        elif action == "view_all":
            # List all upcoming birthdays
            # Get all birthdays with their next occurrence
            upcoming_birthdays = []
            for user_id, birthday in self.birthdays[guild_id].items():
                member = interaction.guild.get_member(int(user_id))
                if not member:
                    continue
                    
                next_date = self.get_next_birthday(birthday)
                upcoming_birthdays.append({
                    "member": member,
                    "birthday": birthday,
                    "next_date": next_date
                })
            
            # Sort by upcoming date
            upcoming_birthdays.sort(key=lambda x: x["next_date"])
            
            if not upcoming_birthdays:
                embed = discord.Embed(
                    title="📅 Server Birthdays",
                    description="No birthdays have been set in this server yet!",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Set Your Birthday", 
                    value="• Use `/birthdays set` to set your birthday with a dropdown menu", 
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)
                return
            
            # Show upcoming birthdays    
            embed = discord.Embed(
                title="📅 Upcoming Birthdays",
                description=f"The next {min(5, len(upcoming_birthdays))} birthdays in {interaction.guild.name}",
                color=discord.Color.blue()
            )
            
            # Add fields for each upcoming birthday
            for i, entry in enumerate(upcoming_birthdays[:5]):
                member = entry["member"]
                birthday = entry["birthday"]
                next_date = entry["next_date"]
                
                formatted_date = self.format_birthday(birthday)
                time_until = self.format_time_until(next_date)
                
                embed.add_field(
                    name=f"{member.display_name}",
                    value=f"• **{formatted_date}** (in {time_until})",
                    inline=False
                )
            
            embed.set_footer(text="Use /birthdays set to set your own birthday!")
            
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return


async def setup(bot: 'TutuBot'):
    """Sets up the BirthdayCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(BirthdayCog(bot))
    log.info("BirthdayCog loaded.")
