import discord
import datetime
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select

class EventCreateModal(Modal, title="Create Event"):
    event_name = TextInput(label="Event Name", placeholder="Enter event name", required=True)
    event_date = TextInput(label="Date (YYYY-MM-DD)", placeholder="2023-12-31", required=True)
    event_time = TextInput(label="Time (HH:MM)", placeholder="20:00", required=True)
    event_description = TextInput(label="Description", placeholder="Event details...", required=True, style=discord.TextStyle.paragraph)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            date_obj = datetime.datetime.strptime(f"{self.event_date.value} {self.event_time.value}", "%Y-%m-%d %H:%M")
            await interaction.response.defer()
        except ValueError:
            await interaction.response.send_message("Invalid date or time format! Please use YYYY-MM-DD and HH:MM.", ephemeral=True)
            return
            
        await self.callback(interaction, self.event_name.value, date_obj, self.event_description.value)

class EventSignupView(View):
    def __init__(self, cog, event_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.event_id = event_id
        
        # Add buttons for different statuses
        statuses = [
            ("✓ Attending", discord.ButtonStyle.success, "Attending"),
            ("⏱️ Late", discord.ButtonStyle.secondary, "Late"),
            ("❓ Tentative", discord.ButtonStyle.secondary, "Tentative"),
            ("✗ Absence", discord.ButtonStyle.danger, "Absence")
        ]
        
        for emoji_label, style, status in statuses:
            self.add_item(StatusButton(emoji_label, style, status, self.cog, self.event_id))

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
        
        # Update the embed
        updated_embed = self.cog.create_event_embed(self.event_id)
        await interaction.response.edit_message(embed=updated_embed)

class EventListSelect(Select):
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
        
        super().__init__(placeholder="Select an event to view", options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No events are currently scheduled.", ephemeral=True)
            return
            
        event_id = int(self.values[0])
        event_embed = self.cog.create_event_embed(event_id)
        view = EventSignupView(self.cog, event_id)
        await interaction.response.send_message(embed=event_embed, view=view)

class EventManageView(View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        self.add_item(EventListSelect(cog))

class EventSchedulerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events = {}  # Dictionary to store event data
        # Format: {event_id: {"name": str, "date": datetime, "description": str, "signups": {"status": [user_ids]}}}

    @commands.Cog.listener()
    async def on_ready(self):
        print("EventSchedulerCog is ready.")

    @app_commands.command(name="events", description="Manage events and sign-ups")
    async def events(self, interaction: discord.Interaction):
        """Command to manage events and sign-ups"""
        embed = discord.Embed(
            title="📅 Event Manager",
            description="• Create new events\n• View existing events\n• Sign up for events",
            color=discord.Color.blue()
        )
        
        # Create buttons for creating and viewing events
        view = View()
        
        create_button = Button(label="Create Event", style=discord.ButtonStyle.secondary)
        view_button = Button(label="View Events", style=discord.ButtonStyle.secondary)
        
        async def create_callback(interaction):
            modal = EventCreateModal()
            modal.callback = self.create_event_callback
            await interaction.response.send_modal(modal)
            
        async def view_callback(interaction):
            view = EventManageView(self)
            await interaction.response.send_message("Select an event to view:", view=view, ephemeral=True)
            
        create_button.callback = create_callback
        view_button.callback = view_callback
        
        view.add_item(create_button)
        view.add_item(view_button)
        
        await interaction.response.send_message(embed=embed, view=view)
    
    async def create_event_callback(self, interaction, name, date, description):
        """Callback for event creation modal"""
        event_id = int(datetime.datetime.now().timestamp())
        
        self.events[event_id] = {
            "name": name,
            "date": date,
            "description": description,
            "signups": {
                "Attending": [],
                "Late": [],
                "Tentative": [],
                "Absence": []
            }
        }
        
        embed = self.create_event_embed(event_id)
        view = EventSignupView(self, event_id)
        
        await interaction.followup.send(embed=embed, view=view)
        
    def create_event_embed(self, event_id):
        """Creates an embed for an event with signup information"""
        event_data = self.events[event_id]
        
        embed = discord.Embed(
            title=f"📅 {event_data['name']}",
            description=event_data['description'],
            color=discord.Color.blue(),
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
            ("Attending", "✓"), 
            ("Late", "⏱️"), 
            ("Tentative", "❓"), 
            ("Absence", "✗")
        ]:
            user_list = []
            for user_id in event_data["signups"].get(status, []):
                user = self.bot.get_user(user_id)
                if user:
                    user_list.append(user.mention)
            
            value = "\n".join(user_list) if user_list else "• No one yet"
            embed.add_field(name=f"{emoji} {status} ({len(user_list)})", value=value, inline=True)
        
        return embed

async def setup(bot):
    await bot.add_cog(EventSchedulerCog(bot))