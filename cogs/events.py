import discord
import datetime
import json
import os
import re
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select

class EventCreateModal(Modal, title="Create Event"):
    event_name = TextInput(label="Event Name", placeholder="Enter event name", required=True)
    event_date = TextInput(label="Date (MM-DD-YYYY)", placeholder="12-31-2023", required=True)
    event_time = TextInput(label="Time (HH:MM AM/PM)", placeholder="8:00pm", required=True)
    event_description = TextInput(label="Description", placeholder="Event details...", required=True, style=discord.TextStyle.paragraph)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # More flexible parsing for time with AM/PM
            time_input = self.event_time.value.strip().lower()
            
            # Extract AM/PM
            if "am" in time_input:
                am_pm_value = "AM"
                time_value = time_input.replace("am", "").strip()
            elif "pm" in time_input:
                am_pm_value = "PM"
                time_value = time_input.replace("pm", "").strip()
            else:
                await interaction.response.send_message("Please specify AM or PM in your time input.", ephemeral=True)
                return
                
            # Clean up any remaining spaces or other characters
            time_value = time_value.strip()
            
            # Convert 12-hour time to 24-hour time
            hour, minute = map(int, time_value.split(':'))
            if am_pm_value == "PM" and hour < 12:
                hour += 12
            elif am_pm_value == "AM" and hour == 12:
                hour = 0
                
            time_str = f"{hour:02d}:{minute:02d}"
            
            # Flexible date parsing
            date_input = self.event_date.value.strip()
            
            # Detect separator (-, /, .)
            separator = None
            for sep in ['-', '/', '.']:
                if sep in date_input:
                    separator = sep
                    break
                    
            if not separator:
                await interaction.response.send_message("Invalid date format! Please use a separator like - or / between date parts.", ephemeral=True)
                return
                
            # Split date parts
            date_parts = date_input.split(separator)
            if len(date_parts) != 3:
                await interaction.response.send_message("Date must have 3 parts: day, month, and year!", ephemeral=True)
                return
                
            # Try to determine format and convert to DD, MM, YYYY
            if len(date_parts[0]) == 4:  # YYYY-MM-DD format
                year, month, day = date_parts
            elif len(date_parts[2]) == 4:  # MM-DD-YYYY or DD-MM-YYYY format
                # If first number > 12, it's likely DD-MM-YYYY
                first_num = int(date_parts[0])
                second_num = int(date_parts[1])
                
                if first_num > 12:  # Must be a day
                    day, month, year = date_parts
                elif second_num > 12:  # First must be month, second must be day
                    month, day, year = date_parts
                else:  # Ambiguous, assume MM-DD-YYYY as default format
                    month, day, year = date_parts
            else:
                await interaction.response.send_message("Year must be 4 digits (YYYY)!", ephemeral=True)
                return
                
            # Standardize to DD-MM-YYYY for datetime parsing
            standard_date = f"{int(day):02d}-{int(month):02d}-{year}"
            
            # Parse the datetime
            date_obj = datetime.datetime.strptime(f"{standard_date} {time_str}", "%d-%m-%Y %H:%M")
            await interaction.response.defer()
        except ValueError as e:
            await interaction.response.send_message(f"Invalid date or time format! Please check your input. Error: {str(e)}", ephemeral=True)
            return
            
        await self.callback(interaction, self.event_name.value, date_obj, self.event_description.value)

class EventSignupView(View):
    def __init__(self, cog, event_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.event_id = event_id
        
        # Add buttons for different statuses without emojis or special colors
        statuses = [
            ("Attending", discord.ButtonStyle.secondary, "Attending"),
            ("Late", discord.ButtonStyle.secondary, "Late"),
            ("Tentative", discord.ButtonStyle.secondary, "Tentative"),
            ("Absence", discord.ButtonStyle.secondary, "Absence")
        ]
        
        for button_label, style, status in statuses:
            self.add_item(StatusButton(button_label, style, status, self.cog, self.event_id))

class StatusButton(Button):
    def __init__(self, label, style, status, cog, event_id):
        super().__init__(label=label, style=style)
        self.status = status
        self.cog = cog
        self.event_id = event_id
        
    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        
        # Remove user from all statuses first
        for status in ["Attending", "Late", "Tentative", "Absence"]:
            if user.id in self.cog.events[self.event_id]["signups"].get(status, []):
                self.cog.events[self.event_id]["signups"][status].remove(user.id)
        
        # Add user to selected status
        self.cog.events[self.event_id]["signups"].setdefault(self.status, []).append(user.id)
        
        # Save the updated events data
        self.cog.save_events()
        
        # Update the embed
        updated_embed = self.cog.create_event_embed(self.event_id)
        await interaction.response.edit_message(embed=updated_embed)

class EventSchedulerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events = {}  # Dictionary to store event data
        # Format: {event_id: {"name": str, "date": datetime, "description": str, "signups": {"status": [user_ids]}}}
        self.data_folder = "data"
        self.events_file = os.path.join(self.data_folder, "events.json")
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        # Load existing events data
        self.load_events()

    def save_events(self):
        """Save events data to JSON file"""
        # Convert events data to a serializable format
        serializable_events = {}
        
        for event_id, event_data in self.events.items():
            serializable_events[str(event_id)] = {
                "name": event_data["name"],
                "date": event_data["date"].timestamp(),  # Store as Unix timestamp
                "description": event_data["description"],
                "signups": event_data["signups"]
            }
        
        # Save to file
        try:
            with open(self.events_file, 'w') as f:
                json.dump(serializable_events, f, indent=4)
        except Exception as e:
            print(f"Error saving events data: {e}")
            
    def load_events(self):
        """Load events data from JSON file"""
        if not os.path.exists(self.events_file):
            return
            
        try:
            with open(self.events_file, 'r') as f:
                serialized_events = json.load(f)
                
            # Convert the serialized data back to the proper format
            for event_id, event_data in serialized_events.items():
                self.events[int(event_id)] = {
                    "name": event_data["name"],
                    "date": datetime.datetime.fromtimestamp(event_data["date"]),
                    "description": event_data["description"],
                    "signups": event_data["signups"]
                }
        except Exception as e:
            print(f"Error loading events data: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        print("EventSchedulerCog is ready.")

    @app_commands.command(name="events", description="[Admin] Manage events and sign-ups")
    @app_commands.checks.has_permissions(administrator=True)
    async def events(self, interaction: discord.Interaction):
        """Command to manage events and sign-ups (Admin only)"""
        # Check if user is admin or bot owner
        if not interaction.user.guild_permissions.administrator and interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="📅 Event Manager",
            description="• Create new events\n• Sign up for events",
            color=discord.Color.blurple()
        )
        
        # Create button for creating events
        view = View()
        
        create_button = Button(label="Create Event", style=discord.ButtonStyle.secondary)
        
        async def create_callback(interaction):
            # Check if user is admin or bot owner
            if not interaction.user.guild_permissions.administrator and interaction.user.id != self.bot.owner_id:
                await interaction.response.send_message("You don't have permission to create events.", ephemeral=True)
                return
                
            modal = EventCreateModal()
            modal.callback = self.create_event_callback
            await interaction.response.send_modal(modal)
            
        create_button.callback = create_callback
        
        view.add_item(create_button)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def create_event_callback(self, interaction, name, date, description):
        """Callback for event creation modal"""
        event_id = int(datetime.datetime.now().timestamp())
        
        # Process role mentions in description
        processed_description = await self.process_role_mentions(interaction.guild, description)
        
        self.events[event_id] = {
            "name": name,
            "date": date,
            "description": processed_description,
            "signups": {
                "Attending": [],
                "Late": [],
                "Tentative": [],
                "Absence": []
            }
        }
        
        # Save updated events data
        self.save_events()
        
        embed = self.create_event_embed(event_id)
        view = EventSignupView(self, event_id)
        
        await interaction.followup.send(embed=embed, view=view)
    
    async def process_role_mentions(self, guild, description):
        """Process @ symbols in description to convert to role mentions"""
        if guild is None:
            return description
            
        # Find all potential role mentions (format: @RoleName)
        role_matches = re.findall(r'@(\w+)', description)
        
        # Replace with actual role mentions if found
        for role_name in role_matches:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                # Replace the mention with the proper role mention format
                description = description.replace(f'@{role_name}', role.mention)
                
        return description
        
    def create_event_embed(self, event_id):
        """Creates an embed for an event with signup information"""
        event_data = self.events[event_id]
        
        embed = discord.Embed(
            title=f"{event_data['name']}",
            description=event_data['description'],
            color=discord.Color.blurple(),
            timestamp=event_data['date']
        )
        
        # Format date for display using Discord's timestamp feature
        unix_timestamp = int(event_data['date'].timestamp())
        embed.add_field(
            name="📆 Date & Time", 
            value=(
                f"• Full: <t:{unix_timestamp}:F>\n"
                f"• Relative: <t:{unix_timestamp}:R>"
            ), 
            inline=False
        )
        
        # List signups by status
        for status, emoji in [
            ("Attending", "👍"), 
            ("Late", "🕒"), 
            ("Tentative", "🤔"), 
            ("Absence", "🚫")
        ]:
            user_list = []
            for user_id in event_data["signups"].get(status, []):
                user = self.bot.get_user(user_id)
                if user:
                    user_list.append(user.mention)
            
            value = "\n".join(user_list) if user_list else ""
            embed.add_field(name=f"{emoji} {status} ({len(user_list)})", value=value, inline=True)
        
        return embed

    @app_commands.command(name="viewevents", description="View upcoming events and sign up")
    async def viewevents(self, interaction: discord.Interaction):
        """Command to view upcoming events (available to all users)"""
        if not self.events:
            await interaction.response.send_message("There are no events scheduled at this time.", ephemeral=True)
            return
            
        # Get the next upcoming event (closest to current time)
        current_time = datetime.datetime.now()
        
        # Filter only future events
        future_events = {
            event_id: event_data for event_id, event_data in self.events.items() 
            if event_data["date"] > current_time
        }
        
        if not future_events:
            await interaction.response.send_message("There are no upcoming events scheduled.", ephemeral=True)
            return
            
        # Sort by closest date
        sorted_events = sorted(future_events.items(), key=lambda x: x[1]["date"])
        
        # Get the closest event
        next_event_id, _ = sorted_events[0]
        
        # Create the embed and view for the event
        event_embed = self.create_event_embed(next_event_id)
        view = EventSignupView(self, next_event_id)
        
        # Add navigation if there's more than one event
        if len(sorted_events) > 1:
            view.add_item(Button(label=f"1/{len(sorted_events)}", style=discord.ButtonStyle.secondary, disabled=True))
        
        await interaction.response.send_message(embed=event_embed, view=view)

async def setup(bot):
    await bot.add_cog(EventSchedulerCog(bot))