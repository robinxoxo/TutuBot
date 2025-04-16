import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional
import logging
import json
import os

from utils.embed_builder import EmbedBuilder
from cogs.permissions import is_owner_or_administrator, check_owner_or_admin

log = logging.getLogger(__name__)

class LoggingCog(commands.Cog, name="Logging"):
    DATA_FILE = os.path.join("data", "log_channels.json")
    LOGGABLE_EVENTS = [
        # Start of Selection
        ("member_join", "🙌", "Member Join"),
        ("member_remove", "🚶", "Member Leave"),
        ("member_ban", "🔨", "Member Ban"),
        ("member_unban", "🔓", "Member Unban"),
        ("member_update", "⚙️", "Member Update"),
        ("message_delete", "✂️", "Message Delete"),
        ("message_edit", "📝", "Message Edit"),
        ("channel_create", "📂", "Channel Create"),
        ("channel_delete", "🗑️", "Channel Delete"),
        ("channel_update", "🔧", "Channel Update"),
        ("role_create", "🌱", "Role Create"),
        ("role_delete", "🔥", "Role Delete"),
        ("role_update", "🔄", "Role Update"),
        ("guild_update", "🏛️", "Server Update"),
        ("emoji_update", "🎭", "Emoji Update"),
        ("webhook_update", "📡", "Webhook Update"),
        ("integration_update", "🔌", "Integration Update"),
        ("invite_create", "✉️", "Invite Create"),
        ("invite_delete", "🚫", "Invite Delete"),
        # End of Selectio
    ]

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channels = self.load_log_channels()

    def load_log_channels(self):
        if not os.path.exists(self.DATA_FILE):
            return {}
        with open(self.DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}

    def save_log_channels(self):
        with open(self.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.log_channels, f, indent=4)

    def get_guild_settings(self, guild_id):
        gid = str(guild_id)
        if gid not in self.log_channels:
            self.log_channels[gid] = {"channel_id": None, "log_events": {}}
        if isinstance(self.log_channels[gid], int):
            # Migrate old format
            self.log_channels[gid] = {"channel_id": self.log_channels[gid], "log_events": {}}
        if "log_events" not in self.log_channels[gid]:
            self.log_channels[gid]["log_events"] = {}
        return self.log_channels[gid]

    def is_event_enabled(self, guild_id, event_key):
        settings = self.get_guild_settings(guild_id)
        # Default to enabled if not set
        return settings["log_events"].get(event_key, True)

    def set_event_enabled(self, guild_id, event_key, enabled):
        settings = self.get_guild_settings(guild_id)
        settings["log_events"][event_key] = enabled
        self.save_log_channels()

    @app_commands.command(name="logging", description="[Admin] Configure server logging.")
    @is_owner_or_administrator()
    async def logs_menu(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                embed=EmbedBuilder.error(
                    title="✗ Error",
                    description="This command can only be used in a server."
                ),
                ephemeral=True
            )
            return
        settings = self.get_guild_settings(interaction.guild.id)
        channel_id = settings["channel_id"]
        channel_mention = f"<#{channel_id}>" if channel_id else "*(not set)*"
        embed = EmbedBuilder.info(
            title="🛠️ Logging Settings",
            description=f"• Log Channel: {channel_mention}\n• Toggle which events are logged below."
        )
        for key, emoji, label in self.LOGGABLE_EVENTS:
            enabled = settings["log_events"].get(key, True)
            status = "✓ Enabled" if enabled else "✗ Disabled"
            embed.add_field(name=f"{emoji} {label}", value=status, inline=True)
        view = LoggingEventsView(self, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.is_event_enabled(member.guild.id, "member_join"):
            return
        channel_id = self.get_guild_settings(member.guild.id)["channel_id"]
        if not channel_id:
            return
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
        embed = EmbedBuilder.info(
            title="👋 Member Joined",
            description=f"{member.mention} has joined the server."
        )
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not self.is_event_enabled(member.guild.id, "member_remove"):
            return
        channel_id = self.get_guild_settings(member.guild.id)["channel_id"]
        if not channel_id:
            return
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
        embed = EmbedBuilder.info(
            title="👋 Member Left",
            description=f"{member.mention} has left the server."
        )
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if not self.is_event_enabled(guild.id, "member_ban"):
            return
        channel_id = self.get_guild_settings(guild.id)["channel_id"]
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        # Try to get audit log entry for who banned
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                moderator = entry.user
                break
        else:
            moderator = None
        embed = EmbedBuilder.error(
            title="✗ Member Banned",
            description=f"{user.mention} was banned from the server."
        )
        if moderator:
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if not self.is_event_enabled(guild.id, "member_unban"):
            return
        channel_id = self.get_guild_settings(guild.id)["channel_id"]
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        # Try to get audit log entry for who unbanned
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
            if entry.target.id == user.id:
                moderator = entry.user
                break
        else:
            moderator = None
        embed = EmbedBuilder.success(
            title="✓ Member Unbanned",
            description=f"{user.mention} was unbanned from the server."
        )
        if moderator:
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not self.is_event_enabled(after.guild.id, "member_update"):
            return
        channel_id = self.get_guild_settings(after.guild.id)["channel_id"]
        if not channel_id:
            return
        channel = after.guild.get_channel(channel_id)
        if not channel:
            return
        changes = []
        if before.nick != after.nick:
            changes.append(f"• Nickname: `{before.nick}` → `{after.nick}`")
        if before.roles != after.roles:
            before_roles = set(before.roles)
            after_roles = set(after.roles)
            added = after_roles - before_roles
            removed = before_roles - after_roles
            if added:
                changes.append(f"• Roles Added: {' '.join(role.mention for role in added)}")
            if removed:
                changes.append(f"• Roles Removed: {' '.join(role.mention for role in removed)}")
        if before.avatar != after.avatar:
            changes.append(f"• Avatar changed.")
        if before.name != after.name:
            changes.append(f"• Username: `{before.name}` → `{after.name}`")
        if not changes:
            return
        embed = EmbedBuilder.info(
            title="📝 Member Updated",
            description=f"{after.mention} was updated.\n" + '\n'.join(changes)
        )
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return
        if not self.is_event_enabled(message.guild.id, "message_delete"):
            return
        channel_id = self.get_guild_settings(message.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = message.guild.get_channel(channel_id)
        if not log_channel:
            return
        # Try to get who deleted the message from audit logs
        deleter = None
        async for entry in message.guild.audit_logs(limit=5, action=discord.AuditLogAction.message_delete):
            if entry.target.id == message.author.id and entry.extra.channel.id == message.channel.id:
                deleter = entry.user
                break
        embed = EmbedBuilder.error(
            title="✗ Message Deleted",
            description=f"A message by {message.author.mention} was deleted in {message.channel.mention}."
        )
        if deleter:
            embed.add_field(name="Deleted by", value=deleter.mention, inline=True)
        embed.add_field(name="Content", value=message.content or "*(no content)*", inline=False)
        if message.attachments:
            files = '\n'.join(f"• [Attachment]({a.url})" for a in message.attachments)
            embed.add_field(name="Attachments", value=files, inline=False)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.guild is None or before.author.bot:
            return
        if before.content == after.content:
            return  # Only log actual content edits
        if not self.is_event_enabled(before.guild.id, "message_edit"):
            return
        channel_id = self.get_guild_settings(before.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = before.guild.get_channel(channel_id)
        if not log_channel:
            return
        embed = EmbedBuilder.warning(
            title="✎ Message Edited",
            description=f"A message by {before.author.mention} was edited in {before.channel.mention}."
        )
        embed.add_field(name="Before", value=before.content or "*(no content)*", inline=False)
        embed.add_field(name="After", value=after.content or "*(no content)*", inline=False)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if not self.is_event_enabled(channel.guild.id, "channel_create"):
            return
        channel_id = self.get_guild_settings(channel.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = channel.guild.get_channel(channel_id)
        if not log_channel:
            return
        # Try to get who created the channel from audit logs
        creator = None
        async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_create):
            if entry.target.id == channel.id:
                creator = entry.user
                break
        embed = EmbedBuilder.success(
            title="✓ Channel Created",
            description=f"{channel.mention} was created."
        )
        if creator:
            embed.add_field(name="Created by", value=creator.mention, inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not self.is_event_enabled(channel.guild.id, "channel_delete"):
            return
        channel_id = self.get_guild_settings(channel.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = channel.guild.get_channel(channel_id)
        if not log_channel:
            return
        # Try to get who deleted the channel from audit logs
        deleter = None
        async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                deleter = entry.user
                break
        embed = EmbedBuilder.error(
            title="✗ Channel Deleted",
            description=f"A channel named `{channel.name}` was deleted."
        )
        if deleter:
            embed.add_field(name="Deleted by", value=deleter.mention, inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if not self.is_event_enabled(after.guild.id, "channel_update"):
            return
        channel_id = self.get_guild_settings(after.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = after.guild.get_channel(channel_id)
        if not log_channel:
            return
        changes = []
        if before.name != after.name:
            changes.append(f"• Name: `{before.name}` → `{after.name}`")
        if hasattr(before, 'topic') and hasattr(after, 'topic') and before.topic != after.topic:
            changes.append(f"• Topic: `{before.topic}` → `{after.topic}`")
        if before.category_id != after.category_id:
            before_cat = before.guild.get_channel(before.category_id).name if before.category_id else "None"
            after_cat = after.guild.get_channel(after.category_id).name if after.category_id else "None"
            changes.append(f"• Category: `{before_cat}` → `{after_cat}`")
        if before.position != after.position:
            changes.append(f"• Position: `{before.position}` → `{after.position}`")
        if hasattr(before, 'slowmode_delay') and hasattr(after, 'slowmode_delay') and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"• Slowmode: `{before.slowmode_delay}`s → `{after.slowmode_delay}`s")
        if not changes:
            return
        # Try to get who updated the channel from audit logs
        updater = None
        async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_update):
            if entry.target.id == after.id:
                updater = entry.user
                break
        embed = EmbedBuilder.info(
            title="📝 Channel Updated",
            description=f"{after.mention} was updated.\n" + '\n'.join(changes)
        )
        if updater:
            embed.add_field(name="Updated by", value=updater.mention, inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        if not self.is_event_enabled(role.guild.id, "role_create"):
            return
        channel_id = self.get_guild_settings(role.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = role.guild.get_channel(channel_id)
        if not log_channel:
            return
        creator = None
        async for entry in role.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_create):
            if entry.target.id == role.id:
                creator = entry.user
                break
        embed = EmbedBuilder.success(
            title="✓ Role Created",
            description=f"{role.mention} was created."
        )
        if creator:
            embed.add_field(name="Created by", value=creator.mention, inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        if not self.is_event_enabled(role.guild.id, "role_delete"):
            return
        channel_id = self.get_guild_settings(role.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = role.guild.get_channel(channel_id)
        if not log_channel:
            return
        deleter = None
        async for entry in role.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                deleter = entry.user
                break
        embed = EmbedBuilder.error(
            title="✗ Role Deleted",
            description=f"A role named `{role.name}` was deleted."
        )
        if deleter:
            embed.add_field(name="Deleted by", value=deleter.mention, inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if not self.is_event_enabled(after.guild.id, "role_update"):
            return
        channel_id = self.get_guild_settings(after.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = after.guild.get_channel(channel_id)
        if not log_channel:
            return
        changes = []
        if before.name != after.name:
            changes.append(f"• Name: `{before.name}` → `{after.name}`")
        if before.color != after.color:
            changes.append(f"• Color: `{before.color}` → `{after.color}`")
        if before.permissions != after.permissions:
            changes.append(f"• Permissions changed.")
        if before.mentionable != after.mentionable:
            changes.append(f"• Mentionable: `{before.mentionable}` → `{after.mentionable}`")
        if before.hoist != after.hoist:
            changes.append(f"• Hoist: `{before.hoist}` → `{after.hoist}`")
        if not changes:
            return
        updater = None
        async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_update):
            if entry.target.id == after.id:
                updater = entry.user
                break
        embed = EmbedBuilder.info(
            title="📝 Role Updated",
            description=f"{after.mention} was updated.\n" + '\n'.join(changes)
        )
        if updater:
            embed.add_field(name="Updated by", value=updater.mention, inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if not self.is_event_enabled(after.id, "guild_update"):
            return
        channel_id = self.get_guild_settings(after.id)["channel_id"]
        if not channel_id:
            return
        log_channel = after.get_channel(channel_id)
        if not log_channel:
            return
        changes = []
        if before.name != after.name:
            changes.append(f"• Name: `{before.name}` → `{after.name}`")
        if before.icon != after.icon:
            changes.append(f"• Icon changed.")
        if before.owner_id != after.owner_id:
            changes.append(f"• Owner: <@{before.owner_id}> → <@{after.owner_id}>")
        if before.region != after.region:
            changes.append(f"• Region: `{before.region}` → `{after.region}`")
        if not changes:
            return
        embed = EmbedBuilder.info(
            title="🛠️ Server Updated",
            description=f"Server was updated.\n" + '\n'.join(changes)
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        if not self.is_event_enabled(guild.id, "emoji_update"):
            return
        channel_id = self.get_guild_settings(guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = guild.get_channel(channel_id)
        if not log_channel:
            return
        added = [e for e in after if e not in before]
        removed = [e for e in before if e not in after]
        changes = []
        if added:
            changes.append(f"• Emojis Added: {' '.join(str(e) for e in added)}")
        if removed:
            changes.append(f"• Emojis Removed: {' '.join(str(e) for e in removed)}")
        if not changes:
            return
        embed = EmbedBuilder.info(
            title="😃 Emojis Updated",
            description='\n'.join(changes)
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        if not self.is_event_enabled(channel.guild.id, "webhook_update"):
            return
        channel_id = self.get_guild_settings(channel.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = channel.guild.get_channel(channel_id)
        if not log_channel:
            return
        embed = EmbedBuilder.info(
            title="🔗 Webhooks Updated",
            description=f"Webhooks were updated in {channel.mention}."
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild):
        if not self.is_event_enabled(guild.id, "integration_update"):
            return
        channel_id = self.get_guild_settings(guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = guild.get_channel(channel_id)
        if not log_channel:
            return
        embed = EmbedBuilder.info(
            title="🔗 Integrations Updated",
            description="Server integrations were updated."
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update_roles(self, member: discord.Member, before_roles, after_roles):
        # This event does not exist in discord.py, handled in on_member_update above
        pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if not self.is_event_enabled(invite.guild.id, "invite_create"):
            return
        channel_id = self.get_guild_settings(invite.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = invite.guild.get_channel(channel_id)
        if not log_channel:
            return
        creator = invite.inviter
        embed = EmbedBuilder.success(
            title="✓ Invite Created",
            description=f"An invite was created for {invite.channel.mention}."
        )
        if creator:
            embed.add_field(name="Created by", value=creator.mention, inline=True)
        embed.add_field(name="Code", value=invite.code, inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if not self.is_event_enabled(invite.guild.id, "invite_delete"):
            return
        channel_id = self.get_guild_settings(invite.guild.id)["channel_id"]
        if not channel_id:
            return
        log_channel = invite.guild.get_channel(channel_id)
        if not log_channel:
            return
        embed = EmbedBuilder.error(
            title="✗ Invite Deleted",
            description=f"An invite for {invite.channel.mention} was deleted."
        )
        embed.add_field(name="Code", value=invite.code, inline=True)
        await log_channel.send(embed=embed)

class LoggingEventsView(ui.View):
    def __init__(self, cog: LoggingCog, guild_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        # Add event toggle buttons
        for key, emoji, label in LoggingCog.LOGGABLE_EVENTS:
            enabled = self.cog.is_event_enabled(guild_id, key)
            button = ui.Button(
                label=label,
                style=discord.ButtonStyle.secondary,
                custom_id=f"toggle_{key}",
                emoji=emoji,
            )
            button.callback = self.make_toggle_callback(key)
            self.add_item(button)
        # Add set log channel button
        set_channel_btn = ui.Button(
            label="Set Log Channel (This Channel)",
            style=discord.ButtonStyle.secondary,
            custom_id="set_log_channel",
            emoji="📢"
        )
        set_channel_btn.callback = self.set_log_channel_callback
        self.add_item(set_channel_btn)

    def make_toggle_callback(self, event_key):
        async def callback(interaction: discord.Interaction):
            if not await check_owner_or_admin(interaction):
                await interaction.response.send_message(
                    embed=EmbedBuilder.error(
                        title="✗ Access Denied",
                        description="You need admin permissions to change logging settings."
                    ),
                    ephemeral=True
                )
                return
            current = self.cog.is_event_enabled(self.guild_id, event_key)
            self.cog.set_event_enabled(self.guild_id, event_key, not current)
            # Refresh the embed and view
            await self.refresh(interaction)
        return callback

    async def set_log_channel_callback(self, interaction: discord.Interaction):
        if not await check_owner_or_admin(interaction):
            await interaction.response.send_message(
                embed=EmbedBuilder.error(
                    title="✗ Access Denied",
                    description="You need admin permissions to set the log channel."
                ),
                ephemeral=True
            )
            return
        # Set the log channel to the current channel
        settings = self.cog.get_guild_settings(interaction.guild.id)
        settings["channel_id"] = interaction.channel_id
        self.cog.save_log_channels()
        await self.refresh(interaction)

    async def refresh(self, interaction: discord.Interaction):
        settings = self.cog.get_guild_settings(self.guild_id)
        channel_id = settings["channel_id"]
        channel_mention = f"<#{channel_id}>" if channel_id else "*(not set)*"
        embed = EmbedBuilder.info(
            title="🛠️ Logging Settings",
            description=f"• Log Channel: {channel_mention}\n• Toggle which events are logged below."
        )
        for key, emoji, label in LoggingCog.LOGGABLE_EVENTS:
            enabled = settings["log_events"].get(key, True)
            status = "✓ Enabled" if enabled else "✗ Disabled"
            embed.add_field(name=f"{emoji} {label}", value=status, inline=True)
        await interaction.response.edit_message(embed=embed, view=LoggingEventsView(self.cog, self.guild_id))

async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingCog(bot)) 