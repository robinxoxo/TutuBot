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

class BirthdayMenuView(discord.ui.View):
    """Main menu view for birthdays with button options."""
    
    def __init__(self, cog: 'BirthdayCog'):
        """Initialize the birthday menu.
        
        Args:
            cog: The BirthdayCog instance
        """
        super().__init__(timeout=180)  # 3 minute timeout
        self.cog = cog
    
    @discord.ui.button(label="Set My Birthday", style=discord.ButtonStyle.secondary, emoji="🎂")
    async def set_birthday_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open a modal to set birthday."""
        await interaction.response.send_modal(BirthdayModal(self.cog))
    
    @discord.ui.button(label="Server Birthdays", style=discord.ButtonStyle.secondary, emoji="📊")
    async def server_birthdays_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show upcoming birthdays in the server."""
        await self.cog.show_server_birthdays(interaction)

class BirthdayModal(discord.ui.Modal, title="Set Your Birthday"):
    """Modal for entering birthday information."""
    
    date_input = discord.ui.TextInput(
        label="Enter your birthday (MM-DD)",
        placeholder="Example: 12-25 for December 25th",
        min_length=3,
        max_length=5,
        required=True
    )
    
    def __init__(self, cog: 'BirthdayCog', user_to_set: Optional[discord.Member] = None):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_to_set = user_to_set
        
    async def on_submit(self, interaction: discord.Interaction):
        """Process the birthday submission."""
        date_str = self.date_input.value
        
        try:
            # Parse the birthday string
            success, result = self.cog.parse_birthday(date_str)
            
            if not success:
                error_message = typing.cast(str, result)
                error_embed = discord.Embed(
                    title="✗ Format Error",
                    description=error_message,
                    color=discord.Color.red()
                )
                error_embed.add_field(
                    name="Correct Format", 
                    value="Please use MM-DD format\nExample: `12-25` for December 25th", 
                    inline=False
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
                
            # Type assertion to help the linter
            birthday_data = typing.cast(Dict[str, int], result)
            
            # Determine the user to set birthday for
            target_user = self.user_to_set if self.user_to_set else interaction.user
            
            if not isinstance(target_user, discord.Member):
                error_embed = discord.Embed(
                    title="✗ Error",
                    description="Could not set birthday. User is not a valid server member.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
                
            # Set the birthday
            result_embed = await self.cog.set_birthday(interaction, target_user, birthday_data)
            await interaction.response.send_message(embed=result_embed, ephemeral=True)
        except Exception as e:
            log.error(f"Error in birthday modal: {e}")
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
                            
                        embed.set_footer(text=f"Use /birthdays to add your own birthday!")
                        
                        await announcement_channel.send(embed=embed)
                        log.info(f"Sent birthday announcement in {guild.name} for {len(birthday_users)} users")
            except Exception as e:
                log.error(f"Error checking birthdays for guild {guild_id}: {e}")
    
    @birthday_check.before_loop
    async def before_birthday_check(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()
    
    def parse_birthday(self, date_str: str) -> Tuple[bool, Union[Dict[str, int], str]]:
        """Parse the birthday string into a structured format.
        
        Args:
            date_str: Birthday date in MM-DD format
            
        Returns:
            Tuple of (success, result)
                If success is True, result is a dict with month and day
                If success is False, result is an error message
        """
        # Check for MM-DD format
        date_patterns = [
            r'^(\d{1,2})-(\d{1,2})$',     # MM-DD
            r'^(\d{1,2})\/(\d{1,2})$',    # MM/DD
            r'^(\d{1,2})\.(\d{1,2})$',    # MM.DD
        ]
        
        for pattern in date_patterns:
            match = re.match(pattern, date_str)
            if match:
                try:
                    month = int(match.group(1))
                    day = int(match.group(2))
                    
                    # Validate month and day
                    if month < 1 or month > 12:
                        return False, "Month must be between 1 and 12"
                    
                    # Check days per month
                    days_in_month = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # Accounting for leap years
                    if day < 1 or day > days_in_month[month]:
                        return False, f"Day must be between 1 and {days_in_month[month]} for this month"
                    
                    # Build result
                    result = {"month": month, "day": day}
                    return True, result
                    
                except ValueError:
                    return False, "Invalid date format. Use MM-DD."
        
        return False, "Invalid date format. Please use MM-DD (month-day)."
    
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

    async def show_user_birthday(self, interaction: discord.Interaction, user: discord.Member):
        """Show a user's birthday in an embed.
        
        Args:
            interaction: The Discord interaction
            user: The user to show birthday for
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
            
        user_id = str(user.id)
        is_self = user.id == interaction.user.id
        
        if user_id in self.birthdays[guild_id]:
            birthday = self.birthdays[guild_id][user_id]
            formatted_date = self.format_birthday(birthday)
            next_birthday = self.get_next_birthday(birthday)
            time_until = self.format_time_until(next_birthday)
            
            if is_self:
                embed = discord.Embed(
                    title="🎂 Your Birthday",
                    description=f"Your birthday is set to **{formatted_date}**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Next Birthday", value=f"• In {time_until}", inline=False)
                
                # Create a button to change the birthday
                class ChangeButton(discord.ui.View):
                    def __init__(self, cog):
                        super().__init__(timeout=180)
                        self.cog = cog
                        
                    @discord.ui.button(label="Change Birthday", style=discord.ButtonStyle.secondary)
                    async def change_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        await button_interaction.response.send_modal(BirthdayModal(self.cog))
                
                await interaction.response.send_message(embed=embed, view=ChangeButton(self), ephemeral=True)
            else:
                embed = discord.Embed(
                    title=f"🎂 {user.display_name}'s Birthday",
                    description=f"Their birthday is on **{formatted_date}**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Coming up", value=f"• In {time_until}", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            if is_self:
                embed = discord.Embed(
                    title="🎂 Your Birthday",
                    description="You haven't set your birthday yet!",
                    color=discord.Color.blue()
                )
                
                # Create button to set birthday
                class SetButton(discord.ui.View):
                    def __init__(self, cog):
                        super().__init__(timeout=180)
                        self.cog = cog
                        
                    @discord.ui.button(label="Set Birthday", style=discord.ButtonStyle.secondary)
                    async def set_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        await button_interaction.response.send_modal(BirthdayModal(self.cog))
                
                await interaction.response.send_message(embed=embed, view=SetButton(self), ephemeral=True)
            else:
                embed = discord.Embed(
                    title=f"🎂 {user.display_name}'s Birthday",
                    description=f"They haven't set their birthday yet!",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_server_birthdays(self, interaction: discord.Interaction):
        """Show upcoming birthdays in the server.
        
        Args:
            interaction: The Discord interaction
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
            
            # Add button to set birthday
            class SetButton(discord.ui.View):
                def __init__(self, cog):
                    super().__init__(timeout=180)
                    self.cog = cog
                    
                @discord.ui.button(label="Set Your Birthday", style=discord.ButtonStyle.secondary)
                async def set_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    await button_interaction.response.send_modal(BirthdayModal(self.cog))
            
            await interaction.response.send_message(embed=embed, view=SetButton(self), ephemeral=True)
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
        
        embed.set_footer(text="Use /birthdays to set or view birthdays")
        
        # Add button to set birthday
        class BirthdayButton(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=180)
                self.cog = cog
                
            @discord.ui.button(label="Set Your Birthday", style=discord.ButtonStyle.secondary)
            async def set_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.send_modal(BirthdayModal(self.cog))
        
        await interaction.response.send_message(embed=embed, view=BirthdayButton(self), ephemeral=True)

    @app_commands.command(name="birthdays", description="Birthday management commands")
    async def birthdays_command(self, interaction: discord.Interaction):
        """Main birthday command showing a menu of options.
        
        Args:
            interaction: The Discord interaction
        """
        if not interaction.guild:
            error_embed = discord.Embed(
                title="✗ Command Error",
                description="This command can only be used in a server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎂 Birthday Menu",
            description="Choose an option below:",
            color=discord.Color.blue()
        )
        
        view = BirthdayMenuView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="setbirthdays", description="[Admin] Set a birthday for another user")
    @app_commands.describe(user="The user to set the birthday for")
    async def birthday_admin_command(self, interaction: discord.Interaction, user: discord.Member):
        """Admin command to set birthdays for other users.
        
        Args:
            interaction: The Discord interaction
            user: The user to set birthday for
        """
        if not interaction.guild:
            error_embed = discord.Embed(
                title="✗ Command Error",
                description="This command can only be used in a server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
            
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
            
        # Use a modal for the birthday input - sending modal directly
        await interaction.response.send_modal(BirthdayModal(self, user_to_set=user))

async def setup(bot: 'TutuBot'):
    """Sets up the BirthdayCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(BirthdayCog(bot))
    log.info("BirthdayCog loaded.")
