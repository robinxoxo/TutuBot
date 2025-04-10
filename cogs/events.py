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
        # Set a custom ID for the view to make it persistent
        self.custom_id = f"event_signup_{event_id}"
        
        # Add buttons for different statuses with emojis but keep secondary color
        statuses = [
            ("👍 Attending", discord.ButtonStyle.secondary, "Attending"),
            ("🕒 Late", discord.ButtonStyle.secondary, "Late"),
            ("🤔 Tentative", discord.ButtonStyle.secondary, "Tentative"),
            ("🚫 Absence", discord.ButtonStyle.secondary, "Absence")
        ]
        
        for button_label, style, status in statuses:
            # Create a custom_id for the button for persistence
            custom_id = f"event_{event_id}_{status.lower()}"
            button = StatusButton(button_label, style, status, self.cog, self.event_id, custom_id=custom_id)
            self.add_item(button)

class StatusButton(Button):
    def __init__(self, label, style, status, cog, event_id, custom_id=None):
        super().__init__(label=label, style=style, custom_id=custom_id)
        self.status = status
        self.cog = cog
        self.event_id = event_id
        
    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        
        # Verify that the event still exists
        if self.event_id not in self.cog.events:
            await interaction.response.send_message("This event no longer exists.", ephemeral=True)
            return
        
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

class EventPostSelect(Select):
    def __init__(self, cog):
        self.cog = cog
        options = []
        
        if not cog.events:
            options = [discord.SelectOption(label="No events scheduled", value="none")]
        else:
            for event_id, event_data in cog.events.items():
                unix_timestamp = int(event_data["date"].timestamp())
                event_time_display = f"{event_data['name']} (<t:{unix_timestamp}:R>)"
                options.append(
                    discord.SelectOption(
                        label=event_time_display[:100],  # Discord has a 100 char limit for labels
                        value=str(event_id),
                        description=event_data["description"][:50] + "..." if len(event_data["description"]) > 50 else event_data["description"]
                    )
                )
        
        super().__init__(placeholder="Select an event to post", options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No events are currently scheduled.", ephemeral=True)
            return
            
        event_id = int(self.values[0])
        await self.cog.post_event(interaction, event_id)

class EventPostView(View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        self.add_item(EventPostSelect(cog))

class EventSchedulerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events = {}  # Dictionary to store event data
        # Format: {event_id: {"name": str, "date": datetime, "description": str, "signups": {"status": [user_ids]}, "posted": {channel_id: message_id}}}
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
                "signups": event_data["signups"],
                "posted": event_data.get("posted", {})  # Store posted messages info
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
                    "signups": event_data["signups"],
                    "posted": event_data.get("posted", {})  # Load posted messages info
                }
        except Exception as e:
            print(f"Error loading events data: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        print("EventSchedulerCog is ready.")
        # Register persistent views for events when the bot starts
        self.register_persistent_views()
        
    def register_persistent_views(self):
        """Register persistent views for all existing events"""
        for event_id in self.events.keys():
            # Create a persistent view for each event
            view = EventSignupView(self, event_id)
            self.bot.add_view(view)
            print(f"Registered persistent view for event {event_id}")

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
            description="• Create new events\n• Post events to current channel\n• Sign up for events",
            color=discord.Color.blurple()
        )
        
        # Create buttons for event management
        view = View()
        
        create_button = Button(label="Create Event", style=discord.ButtonStyle.secondary)
        post_button = Button(label="Post Event", style=discord.ButtonStyle.secondary)
        
        async def create_callback(interaction):
            # Check if user is admin or bot owner
            if not interaction.user.guild_permissions.administrator and interaction.user.id != self.bot.owner_id:
                await interaction.response.send_message("You don't have permission to create events.", ephemeral=True)
                return
                
            modal = EventCreateModal()
            modal.callback = self.create_event_callback
            await interaction.response.send_modal(modal)
            
        async def post_callback(interaction):
            # Check if user is admin or bot owner
            if not interaction.user.guild_permissions.administrator and interaction.user.id != self.bot.owner_id:
                await interaction.response.send_message("You don't have permission to post events.", ephemeral=True)
                return
                
            if not self.events:
                await interaction.response.send_message("There are no events to post.", ephemeral=True)
                return
                
            view = EventPostView(self)
            await interaction.response.send_message("Select an event to post in this channel:", view=view, ephemeral=True)
            
        create_button.callback = create_callback
        post_button.callback = post_callback
        
        view.add_item(create_button)
        view.add_item(post_button)
        
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
            },
            "posted": {}  # Initialize empty posted messages tracking
        }
        
        # Save updated events data
        self.save_events()
        
        embed = self.create_event_embed(event_id)
        view = EventSignupView(self, event_id)
        
        # Register the view for persistence
        self.bot.add_view(view)
        
        # Send the message
        event_message = await interaction.followup.send(embed=embed, view=view)
        
        # Store the initial message in the posted tracking
        channel_id = str(interaction.channel_id)
        self.events[event_id]["posted"][channel_id] = event_message.id
        
        # Save again with the message ID
        self.save_events()
    
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

    async def post_event(self, interaction, event_id):
        """Post an event to the current channel"""
        if event_id not in self.events:
            await interaction.response.send_message("This event no longer exists.", ephemeral=True)
            return
            
        # Check if the event is already posted in this channel
        channel_id = str(interaction.channel_id)
        event_data = self.events[event_id]
        posted_info = event_data.get("posted", {})
        
        # Initialize posted data if it doesn't exist
        if "posted" not in event_data:
            event_data["posted"] = {}
            
        # Try to delete the previous message if it exists
        if channel_id in posted_info:
            try:
                prev_message = await interaction.channel.fetch_message(int(posted_info[channel_id]))
                await prev_message.delete()
                print(f"Deleted previous event post: {posted_info[channel_id]}")
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                print(f"Could not delete previous event message: {e}")
        
        # Create the embed and view for the event
        embed = self.create_event_embed(event_id)
        view = EventSignupView(self, event_id)
        
        # Register the view for persistence
        self.bot.add_view(view)
        
        # Post the event
        event_message = await interaction.channel.send(embed=embed, view=view)
        
        # Store the message ID
        event_data["posted"][channel_id] = event_message.id
        self.save_events()
        
        await interaction.response.send_message(f"Event posted successfully!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EventSchedulerCog(bot))