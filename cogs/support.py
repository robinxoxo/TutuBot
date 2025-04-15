import discord
from discord import app_commands, ui
from discord.ext import commands
from utils.embed_builder import EmbedBuilder
from cogs.permissions import is_owner_or_administrator, get_allowed_admin_roles, check_owner_or_admin, get_allowed_command_roles
import os
import json
import asyncio
import re

TICKETS_FILE = os.path.join("data", "tickets.json")

def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        return {}
    with open(TICKETS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_tickets(tickets):
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(tickets, f, indent=4)

class SupportCog(commands.Cog, name="Support"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tickets = load_tickets()

    async def cog_unload(self):
        save_tickets(self.tickets)

    async def cog_load(self):
        self.tickets = load_tickets()

    @app_commands.command(name="support", description="[Admin] Get support or open a ticket.")
    async def support_menu(self, interaction: discord.Interaction):
        embed = EmbedBuilder.info(
            title="🎫 Support Menu",
            description="Need help? Click the button below to open a support ticket. Our team will assist you as soon as possible."
        )
        view = SupportMenuView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    def get_admin_overwrites(self, guild, include_creator=None):
        # Get global and per-command admin roles for 'support'
        allowed_role_ids = set(get_allowed_admin_roles(guild.id))
        allowed_role_ids.update(get_allowed_command_roles(guild.id, 'support'))
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
        }
        # Allow all admin roles from permissions.py (global and per-command)
        for role_id in allowed_role_ids:
            role = guild.get_role(int(role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        # Allow all roles with administrator permission
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        # Allow the bot owner if present in the guild
        bot_owner_id = getattr(self.bot, 'owner_id', None)
        if bot_owner_id:
            owner_member = guild.get_member(bot_owner_id)
            if owner_member:
                overwrites[owner_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        if include_creator:
            overwrites[include_creator] = discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True)
        return overwrites

    def get_ticket_by_user(self, guild_id, user_id, status=None):
        # Return ticket by status (open/closed) or any if status is None
        for ticket_id, ticket in self.tickets.items():
            if ticket['guild_id'] == guild_id and ticket['creator_id'] == user_id:
                if status is None or ticket['status'] == status:
                    return ticket
        return None

    def save_ticket(self, channel_id, guild_id, creator_id, status):
        self.tickets[str(channel_id)] = {
            'channel_id': channel_id,
            'guild_id': guild_id,
            'creator_id': creator_id,
            'status': status
        }
        save_tickets(self.tickets)

    def update_ticket_status(self, channel_id, status):
        if str(channel_id) in self.tickets:
            self.tickets[str(channel_id)]['status'] = status
            save_tickets(self.tickets)

    def close_ticket(self, channel_id, closed_by):
        import datetime
        if str(channel_id) in self.tickets:
            ticket = self.tickets[str(channel_id)]
            ticket['status'] = 'closed'
            ticket['closed_by'] = closed_by
            ticket['closed_at'] = datetime.datetime.utcnow().isoformat()
            save_tickets(self.tickets)

    def reopen_ticket(self, channel_id):
        if str(channel_id) in self.tickets:
            ticket = self.tickets[str(channel_id)]
            ticket['status'] = 'open'
            ticket.pop('closed_by', None)
            ticket.pop('closed_at', None)
            save_tickets(self.tickets)

class SupportMenuView(ui.View):
    def __init__(self, cog: SupportCog):
        super().__init__(timeout=120)
        self.cog = cog
        self.add_item(OpenTicketButton(cog))

class OpenTicketButton(ui.Button):
    def __init__(self, cog: SupportCog):
        super().__init__(
            label="Open Ticket",
            style=discord.ButtonStyle.secondary,
            emoji="🎫"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        if not guild:
            await interaction.response.send_message(
                embed=EmbedBuilder.error(
                    title="✗ Error",
                    description="Tickets can only be opened in a server."
                ),
                ephemeral=True
            )
            return
        # Sanitize username for channel name
        base_name = re.sub(r'[^a-zA-Z0-9]', '-', user.name.lower())
        base_name = re.sub(r'-+', '-', base_name).strip('-')
        channel_name = f"ticket-{base_name}"
        closed_channel_name = f"closed-ticket-{base_name}"
        # Check for open or closed ticket
        open_ticket = self.cog.get_ticket_by_user(guild.id, user.id, status='open')
        closed_ticket = self.cog.get_ticket_by_user(guild.id, user.id, status='closed')
        if open_ticket:
            channel = guild.get_channel(open_ticket['channel_id'])
            if channel:
                await interaction.response.send_message(
                    embed=EmbedBuilder.info(
                        title="🎫 Ticket Exists",
                        description=f"You already have an open ticket: {channel.mention}"
                    ),
                    ephemeral=True
                )
                return
        elif closed_ticket:
            # Re-open the closed ticket
            channel = guild.get_channel(closed_ticket['channel_id'])
            if channel:
                # Restore user permissions
                overwrites = channel.overwrites
                overwrites[user] = discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True)
                # Rename channel and update topic
                await channel.edit(
                    name=channel_name,
                    topic=f"Support ticket for {user} ({user.id}) | Status: Open",
                    overwrites=overwrites,
                    reason="Ticket re-opened for user"
                )
                self.cog.reopen_ticket(channel.id)
                embed = EmbedBuilder.info(
                    title="🎫 Ticket Re-Opened",
                    description=f"Welcome back {user.mention}, your ticket has been re-opened. A member of our team will be with you shortly."
                )
                view = TicketView(self.cog, user.id)
                await channel.send(content=user.mention, embed=embed, view=view)
                await interaction.response.send_message(
                    embed=EmbedBuilder.success(
                        title="✓ Ticket Re-Opened",
                        description=f"Your previous ticket has been re-opened: {channel.mention}"
                    ),
                    ephemeral=True
                )
                return
        # Find or create the Support category at the top
        category = discord.utils.get(guild.categories, name="Support")
        if not category:
            cat_overwrites = self.cog.get_admin_overwrites(guild)
            category = await guild.create_category_channel("Support", position=0, overwrites=cat_overwrites, reason="Support ticket system setup")
        # Create the channel in the Support category
        overwrites = self.cog.get_admin_overwrites(guild, include_creator=user)
        channel = await guild.create_text_channel(
            name=channel_name,
            topic=f"Support ticket for {user} ({user.id}) | Status: Open",
            overwrites=overwrites,
            category=category,
            reason=f"Support ticket opened by {user}"
        )
        self.cog.save_ticket(channel.id, guild.id, user.id, 'open')
        embed = EmbedBuilder.info(
            title="🎫 Ticket Opened",
            description=f"Hello {user.mention}, a member of our team will be with you shortly. Use the button below to close this ticket when your issue is resolved."
        )
        view = TicketView(self.cog, user.id)
        await channel.send(content=user.mention, embed=embed, view=view)
        await interaction.response.send_message(
            embed=EmbedBuilder.success(
                title="✓ Ticket Created",
                description=f"Your ticket has been created: {channel.mention}"
            ),
            ephemeral=True
        )

class TicketView(ui.View):
    def __init__(self, cog: SupportCog, opener_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.opener_id = opener_id
        self.add_item(CloseTicketButton(cog, opener_id))

class CloseTicketButton(ui.Button):
    def __init__(self, cog: SupportCog, opener_id: int):
        super().__init__(
            label="Close Ticket",
            style=discord.ButtonStyle.secondary,
            emoji="🔒"
        )
        self.cog = cog
        self.opener_id = opener_id

    async def callback(self, interaction: discord.Interaction):
        # Only ticket opener or admin can close
        is_admin = await check_owner_or_admin(interaction, command_name="support")
        if interaction.user.id != self.opener_id and not is_admin:
            await interaction.response.send_message(
                embed=EmbedBuilder.error(
                    title="✗ Access Denied",
                    description="Only the ticket creator or an admin can close this ticket."
                ),
                ephemeral=True
            )
            return
        channel = interaction.channel
        # Remove the ticket creator's permissions
        overwrites = channel.overwrites
        member = channel.guild.get_member(self.opener_id)
        if member and member in overwrites:
            overwrites[member] = discord.PermissionOverwrite(view_channel=False)
            # Rename channel and update topic
            base_name = re.sub(r'[^a-zA-Z0-9]', '-', member.name.lower())
            base_name = re.sub(r'-+', '-', base_name).strip('-')
            closed_channel_name = f"closed-ticket-{base_name}"
            await channel.edit(
                name=closed_channel_name,
                topic=f"Support ticket for {member} ({member.id}) | Status: Closed",
                overwrites=overwrites,
                reason="Ticket closed for user"
            )
        self.cog.close_ticket(channel.id, interaction.user.id)
        await interaction.response.send_message(
            embed=EmbedBuilder.success(
                title="✓ Ticket Closed",
                description="Your access to this ticket has been removed. If you need further help, you can open a new ticket."
            ),
            ephemeral=True
        )
        # Optionally, delete the category if empty (as before)
        category = channel.category
        if category and category.name == "Support":
            if not any(isinstance(c, discord.TextChannel) and c.permissions_for(member).view_channel for c in category.channels for member in category.guild.members):
                await category.delete(reason="No more tickets in Support category.")

async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot)) 