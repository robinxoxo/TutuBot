import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, Button, View, Select
from datetime import datetime

class EventCreationModal(Modal):
    def __init__(self, cog):
        super().__init__(title="Create a New Event")
        self.cog = cog

        self.event_name = TextInput(
            label="Event Name", 
            placeholder="Enter the event name", 
            required=True)
        
        self.add_item(self.event_name)

        self.event_date = TextInput(
            label="Event Date (YYYY-MM-DD)", 
            placeholder="Enter the event date", 
            required=True)
        
        self.add_item(self.event_date)

        self.event_description = TextInput(
            label="Event Description", 
            placeholder="Enter a brief description", 
            required=False, 
            style=discord.TextStyle.paragraph)
        
        self.add_item(self.event_description)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            event_date = datetime.strptime(self.event_date.value, "%Y-%m-%d")
            self.cog.events[self.event_name.value] = {
                "date": event_date.strftime("%Y-%m-%d"),
                "description": self.event_description.value or "No description provided."
            }
            embed = discord.Embed(
                title="📅 ✓ Event Created",
                description=f"**{self.event_name.value}** has been scheduled for {event_date.strftime('%Y-%m-%d')}.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except ValueError:
            embed = discord.Embed(
                title="📅 ✗ Invalid Date Format",
                description="Please use the format YYYY-MM-DD for the event date.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class EventSignUpView(View):
    def __init__(self, event_name, cog):
        super().__init__()
        self.event_name = event_name
        self.cog = cog

        self.add_item(Select(
            placeholder="Choose your status",
            options=[
                discord.SelectOption(label="Attending", emoji="✅"),
                discord.SelectOption(label="Late", emoji="⏰"),
                discord.SelectOption(label="Tentative", emoji="❓"),
                discord.SelectOption(label="Absent", emoji="❌")
            ],
            custom_id="event_signup_status"
        ))

    async def interaction_check(self, interaction: discord.Interaction):
        selected_option = interaction.data['values'][0]
        user_id = interaction.user.id

        if self.event_name not in self.cog.events:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="📅 ✗ Event Not Found",
                    description=f"The event `{self.event_name}` does not exist.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return False

        event = self.cog.events[self.event_name]
        if "signups" not in event:
            event["signups"] = {}

        event["signups"][user_id] = selected_option
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📅 ✓ Status Updated",
                description=f"Your status for `{self.event_name}` has been updated to `{selected_option}`.",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
        return True

class EventAdminView(View):
    def __init__(self, event_name, cog):
        super().__init__()
        self.event_name = event_name
        self.cog = cog

        self.add_item(Button(
            label="Sign Up",
            style=discord.ButtonStyle.secondary,
            custom_id="event_signup"
        ))
        self.add_item(Button(
            label="View Signups",
            style=discord.ButtonStyle.secondary,
            custom_id="event_view_signups"
        ))
        self.add_item(Button(
            label="Delete Event",
            style=discord.ButtonStyle.secondary,
            custom_id="event_delete"
        ))

    async def interaction_check(self, interaction: discord.Interaction):
        if self.event_name not in self.cog.events:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="📅 ✗ Event Not Found",
                    description=f"The event `{self.event_name}` does not exist.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return False

        custom_id = interaction.data['custom_id']
        if custom_id == "event_signup":
            await self.cog.signup_event(interaction, self.event_name)
        elif custom_id == "event_view_signups":
            await self.cog.view_signups(interaction, self.event_name)
        elif custom_id == "event_delete":
            await self.cog.delete_event(interaction, self.event_name)
        return True

class EventScheduler(commands.Cog):
    """Cog for scheduling and managing events."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.events = {}  # Store events in memory

    @commands.command(name="events")
    @commands.has_permissions(administrator=True)
    async def events(self, ctx: commands.Context):
        """Command to create or list events. Only accessible to admins."""
        if not self.events:
            embed = discord.Embed(
                title="📅 Scheduled Events",
                description="No events have been scheduled yet.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="📅 Scheduled Events",
            description="Select an event to manage or create a new one:",
            color=discord.Color.blue()
        )
        for event_name in self.events.keys():
            embed.add_field(
                name=f"• {event_name}",
                value="Use the buttons below to manage this event.",
                inline=False
            )
        view = EventAdminView(event_name, self)
        await ctx.send(embed=embed, view=view)

        modal = EventCreationModal(self)
        await ctx.send("Opening event creation modal...", ephemeral=True)
        await ctx.send_modal(modal)

    @events.error
    async def events_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="📅 ✗ Permission Denied",
                description="You do not have the required permissions to create an event.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    async def signup_event(self, interaction: discord.Interaction, event_name: str):
        """Sign up for an event."""
        if event_name not in self.events:
            embed = discord.Embed(
                title="📅 ✗ Event Not Found",
                description=f"No event found with the name `{event_name}`.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        view = EventSignUpView(event_name, self)
        embed = discord.Embed(
            title=f"📅 Sign Up for {event_name}",
            description="Choose your status for the event using the dropdown below.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view)

    async def view_signups(self, interaction: discord.Interaction, event_name: str):
        """View signups for an event."""
        if event_name not in self.events:
            embed = discord.Embed(
                title="📅 ✗ Event Not Found",
                description=f"No event found with the name `{event_name}`.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        event = self.events[event_name]
        if "signups" not in event or not event["signups"]:
            embed = discord.Embed(
                title=f"📅 Signups for {event_name}",
                description="No one has signed up for this event yet.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📅 Signups for {event_name}",
            description="Here are the current signups:",
            color=discord.Color.blue()
        )
        for user_id, status in event["signups"].items():
            user = self.bot.get_user(user_id)
            embed.add_field(
                name=f"• {user.name if user else 'Unknown User'}",
                value=f"**Status:** {status}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def delete_event(self, interaction: discord.Interaction, event_name: str):
        """Delete a scheduled event."""
        if event_name not in self.events:
            embed = discord.Embed(
                title="📅 ✗ Event Not Found",
                description=f"No event found with the name `{event_name}`.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        del self.events[event_name]
        embed = discord.Embed(
            title="📅 ✓ Event Deleted",
            description=f"The event `{event_name}` has been successfully deleted.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(EventScheduler(bot))
