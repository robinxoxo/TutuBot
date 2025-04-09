import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, Button, View, Select
from datetime import datetime
import json
import os
import asyncio
from discord import app_commands

# File path for storing events data
EVENTS_FILE = "data/events.json"

class EventCreationModal(Modal):
    """Modal for creating a new event"""
    
    def __init__(self, cog):
        super().__init__(title="Create a New Event")
        self.cog = cog

        self.event_name = TextInput(
            label="Event Name", 
            placeholder="Enter the event name", 
            required=True
        )
        self.add_item(self.event_name)

        self.event_date = TextInput(
            label="Event Date (YYYY-MM-DD)", 
            placeholder="Enter the event date", 
            required=True
        )
        self.add_item(self.event_date)

        self.event_time = TextInput(
            label="Event Time (HH:MM)", 
            placeholder="Enter the event time (24-hour format)", 
            required=True
        )
        self.add_item(self.event_time)

        self.event_description = TextInput(
            label="Event Description", 
            placeholder="Enter a brief description", 
            required=False, 
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.event_description)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse the date and time
            event_datetime = f"{self.event_date.value} {self.event_time.value}"
            event_dt = datetime.strptime(event_datetime, "%Y-%m-%d %H:%M")
            
            # Store the event data
            self.cog.events[self.event_name.value] = {
                "date": self.event_date.value,
                "time": self.event_time.value,
                "timestamp": event_dt.timestamp(),
                "description": self.event_description.value or "No description provided.",
                "creator": interaction.user.id,
                "created_at": datetime.now().timestamp(),
                "signups": {}
            }
            
            # Save events to file
            await self.cog.save_events()
            
            # Send confirmation
            embed = discord.Embed(
                title="📅 ✓ Event Created",
                description=f"**{self.event_name.value}** has been scheduled for {self.event_date.value} at {self.event_time.value}.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Description", 
                value=self.event_description.value or "No description provided."
            )
            embed.set_footer(text=f"Created by {interaction.user.display_name}")
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            embed = discord.Embed(
                title="📅 ✗ Invalid Date/Time Format",
                description="Please use the format YYYY-MM-DD for date and HH:MM for time.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class EventSignupView(View):
    """View for signing up to an event"""
    
    def __init__(self, event_name, cog):
        super().__init__(timeout=None)  # No timeout for persistent view
        self.event_name = event_name
        self.cog = cog
        
        # Add status dropdown
        self.add_item(Select(
            custom_id=f"status_select_{event_name}",
            placeholder="Choose your status",
            options=[
                discord.SelectOption(label="Attending", emoji="✅", value="attending"),
                discord.SelectOption(label="Late", emoji="⏰", value="late"),
                discord.SelectOption(label="Tentative", emoji="❓", value="tentative"),
                discord.SelectOption(label="Absent", emoji="❌", value="absent")
            ]
        ))
        
    async def callback(self, interaction: discord.Interaction):
        select = interaction.data["components"][0]
        values = select["values"]
        selected_value = values[0]
        
        if self.event_name not in self.cog.events:
            embed = discord.Embed(
                title="📅 ✗ Event Not Found",
                description=f"The event `{self.event_name}` no longer exists.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Update user status
        event = self.cog.events[self.event_name]
        if "signups" not in event:
            event["signups"] = {}
            
        event["signups"][str(interaction.user.id)] = {
            "status": selected_value,
            "username": interaction.user.display_name,
            "updated_at": datetime.now().timestamp()
        }
        
        # Save the updated events
        await self.cog.save_events()
        
        # Create status emoji mapping
        status_emoji = {
            "attending": "✅",
            "late": "⏰",
            "tentative": "❓",
            "absent": "❌"
        }
        
        # Send confirmation
        embed = discord.Embed(
            title=f"📅 ✓ Status Updated",
            description=f"Your status for **{self.event_name}** has been updated to {status_emoji.get(selected_value, '')} `{selected_value}`.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class EventListSelect(Select):
    """Dropdown for selecting an event to view"""
    
    def __init__(self, cog):
        self.cog = cog
        
        # Create options from events
        options = []
        for event_name, event_data in sorted(
            cog.events.items(), 
            key=lambda x: x[1].get("timestamp", 0)
        ):
            # Format the date/time for the description
            date = event_data.get("date", "Unknown date")
            time = event_data.get("time", "")
            options.append(
                discord.SelectOption(
                    label=event_name,
                    description=f"{date} {time}",
                    value=event_name
                )
            )
            
        # If no events, add a placeholder option
        if not options:
            options = [discord.SelectOption(label="No events available", value="none")]
        
        super().__init__(
            placeholder="Select an event to view",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="event_list_select"
        )
        
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            embed = discord.Embed(
                title="📅 No Events",
                description="There are no scheduled events to view.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Display the selected event
        await self.cog.show_event_details(interaction, self.values[0])

class EventManagementView(View):
    """Main view for managing events"""
    
    def __init__(self, cog, is_admin=False):
        super().__init__(timeout=None)
        self.cog = cog
        
        # Add event list dropdown
        self.add_item(EventListSelect(cog))
        
        # Add admin buttons if user is admin
        if is_admin:
            self.add_item(Button(
                style=discord.ButtonStyle.secondary,
                label="Create New Event",
                custom_id="create_event_button",
                emoji="➕"
            ))
            self.add_item(Button(
                style=discord.ButtonStyle.secondary,
                label="Delete Event",
                custom_id="delete_event_button",
                emoji="🗑️"
            ))
    
    async def callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        
        if custom_id == "create_event_button":
            # Show event creation modal
            modal = EventCreationModal(self.cog)
            await interaction.response.send_modal(modal)
            
        elif custom_id == "delete_event_button":
            # Show event deletion view
            await self.cog.show_delete_event_view(interaction)

class EventSelector(Select):
    """Dropdown for selecting an event for deletion"""
    
    def __init__(self, cog, action_type="delete"):
        self.cog = cog
        self.action_type = action_type
        
        # Create options from events
        options = []
        for event_name in cog.events.keys():
            options.append(discord.SelectOption(label=event_name, value=event_name))
            
        # If no events, add a placeholder option
        if not options:
            options = [discord.SelectOption(label="No events available", value="none")]
        
        super().__init__(
            placeholder=f"Select an event to {action_type}",
            min_values=1,
            max_values=1,
            options=options
        )
        
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            embed = discord.Embed(
                title="📅 No Events",
                description="There are no scheduled events available.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        if self.action_type == "delete":
            await self.cog.delete_event(interaction, self.values[0])
        elif self.action_type == "signup":
            await self.cog.show_signup_view(interaction, self.values[0])

class Events(commands.Cog):
    """Cog for scheduling and managing events"""

    def __init__(self, bot):
        self.bot = bot
        self.events = {}  # Will be loaded from file
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Schedule the loading of events
        asyncio.create_task(self.load_events())
    
    async def load_events(self):
        """Load events from file"""
        try:
            if os.path.exists(EVENTS_FILE):
                with open(EVENTS_FILE, 'r') as f:
                    self.events = json.load(f)
                print(f"Loaded {len(self.events)} events from file.")
            else:
                print("No events file found. Starting with empty events.")
                self.events = {}
        except Exception as e:
            print(f"Error loading events: {e}")
            self.events = {}
    
    async def save_events(self):
        """Save events to file"""
        try:
            with open(EVENTS_FILE, 'w') as f:
                json.dump(self.events, f, indent=4)
        except Exception as e:
            print(f"Error saving events: {e}")
    
    @app_commands.command(name="events", description="Manage and view events")
    async def events_command(self, interaction: discord.Interaction):
        """Command to manage and view events"""
        # Check if user has admin permissions
        is_admin = interaction.user.guild_permissions.administrator
        
        embed = discord.Embed(
            title="📅 Event Manager",
            description="Select an option from below to manage events.",
            color=discord.Color.blue()
        )
        
        if self.events:
            # List upcoming events
            sorted_events = sorted(
                self.events.items(),
                key=lambda x: x[1].get("timestamp", 0)
            )
            
            events_list = []
            for event_name, event_data in sorted_events[:5]:  # Show first 5 events
                date = event_data.get("date", "Unknown date")
                time = event_data.get("time", "")
                events_list.append(f"• **{event_name}** - {date} {time}")
            
            embed.add_field(
                name="Upcoming Events",
                value="\n".join(events_list) if events_list else "No upcoming events",
                inline=False
            )
        else:
            embed.add_field(
                name="No Events",
                value="There are no scheduled events yet.",
                inline=False
            )
        
        # Create view with appropriate permissions
        view = EventManagementView(self, is_admin)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_event_details(self, interaction: discord.Interaction, event_name):
        """Show details for a specific event"""
        if event_name not in self.events:
            embed = discord.Embed(
                title="📅 ✗ Event Not Found",
                description=f"The event `{event_name}` does not exist.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        event = self.events[event_name]
        
        # Create embed with event details
        embed = discord.Embed(
            title=f"📅 {event_name}",
            description=event.get("description", "No description provided."),
            color=discord.Color.blue()
        )
        
        # Add event details
        date = event.get("date", "Unknown date")
        time = event.get("time", "Unknown time")
        embed.add_field(name="Date", value=date, inline=True)
        embed.add_field(name="Time", value=time, inline=True)
        
        # Add creator info if available
        creator_id = event.get("creator")
        if creator_id:
            creator = await self.bot.fetch_user(creator_id)
            embed.add_field(
                name="Created by", 
                value=f"{creator.mention if creator else 'Unknown'}", 
                inline=True
            )
        
        # Add signup information
        signups = event.get("signups", {})
        
        # Group signups by status
        attending = []
        late = []
        tentative = []
        absent = []
        
        for user_id, data in signups.items():
            status = data.get("status", "")
            username = data.get("username", "Unknown")
            user_obj = await self.bot.fetch_user(int(user_id))
            user_mention = user_obj.mention if user_obj else username
            
            if status == "attending":
                attending.append(user_mention)
            elif status == "late":
                late.append(user_mention)
            elif status == "tentative":
                tentative.append(user_mention)
            elif status == "absent":
                absent.append(user_mention)
        
        # Add fields for each status category
        if attending:
            embed.add_field(
                name=f"✅ Attending ({len(attending)})",
                value="\n".join(f"• {user}" for user in attending[:10]) + 
                      (f"\n• ... and {len(attending) - 10} more" if len(attending) > 10 else ""),
                inline=False
            )
            
        if late:
            embed.add_field(
                name=f"⏰ Late ({len(late)})",
                value="\n".join(f"• {user}" for user in late[:10]) + 
                      (f"\n• ... and {len(late) - 10} more" if len(late) > 10 else ""),
                inline=False
            )
            
        if tentative:
            embed.add_field(
                name=f"❓ Tentative ({len(tentative)})",
                value="\n".join(f"• {user}" for user in tentative[:10]) + 
                      (f"\n• ... and {len(tentative) - 10} more" if len(tentative) > 10 else ""),
                inline=False
            )
            
        if absent:
            embed.add_field(
                name=f"❌ Absent ({len(absent)})",
                value="\n".join(f"• {user}" for user in absent[:10]) + 
                      (f"\n• ... and {len(absent) - 10} more" if len(absent) > 10 else ""),
                inline=False
            )
            
        if not (attending or late or tentative or absent):
            embed.add_field(
                name="No Signups",
                value="No one has signed up for this event yet.",
                inline=False
            )
        
        # Create signup button
        view = EventSignupView(event_name, self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_signup_view(self, interaction: discord.Interaction, event_name):
        """Show the signup view for a specific event"""
        if event_name not in self.events:
            embed = discord.Embed(
                title="📅 ✗ Event Not Found",
                description=f"The event `{event_name}` does not exist.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        view = EventSignupView(event_name, self)
        
        embed = discord.Embed(
            title=f"📅 Sign Up: {event_name}",
            description="Choose your status for this event.",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_delete_event_view(self, interaction: discord.Interaction):
        """Show the delete event view"""
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="📅 ✗ Permission Denied",
                description="You need administrator permissions to delete events.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        view = View()
        view.add_item(EventSelector(self, action_type="delete"))
        
        embed = discord.Embed(
            title="📅 Delete Event",
            description="Select an event to delete.",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def delete_event(self, interaction: discord.Interaction, event_name):
        """Delete an event"""
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="📅 ✗ Permission Denied",
                description="You need administrator permissions to delete events.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        if event_name not in self.events:
            embed = discord.Embed(
                title="📅 ✗ Event Not Found",
                description=f"The event `{event_name}` does not exist.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Create confirmation view
        view = View()
        
        # Add confirm button
        confirm_button = Button(
            style=discord.ButtonStyle.danger,
            label="Confirm Delete",
            custom_id="confirm_delete"
        )
        
        # Add cancel button
        cancel_button = Button(
            style=discord.ButtonStyle.secondary,
            label="Cancel",
            custom_id="cancel_delete"
        )
        
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        # Define callbacks
        async def confirm_callback(button_interaction):
            # Delete the event
            del self.events[event_name]
            await self.save_events()
            
            embed = discord.Embed(
                title="📅 ✓ Event Deleted",
                description=f"The event `{event_name}` has been deleted.",
                color=discord.Color.green()
            )
            await button_interaction.response.send_message(embed=embed, ephemeral=True)
        
        async def cancel_callback(button_interaction):
            embed = discord.Embed(
                title="📅 Deletion Cancelled",
                description=f"The event `{event_name}` was not deleted.",
                color=discord.Color.blue()
            )
            await button_interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Attach callbacks
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
        embed = discord.Embed(
            title="📅 Confirm Deletion",
            description=f"Are you sure you want to delete the event `{event_name}`?",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    # Ensure the data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Add the cog
    await bot.add_cog(Events(bot))
