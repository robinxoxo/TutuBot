import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Callable, TypeVar, Optional, Union, Awaitable, cast, TYPE_CHECKING
import asyncio
import json
import os
from utils.embed_builder import EmbedBuilder

# For type hinting
if TYPE_CHECKING:
    from main import TutuBot

T = TypeVar('T')

PERMISSIONS_FILE = os.path.join("data", "permissions.json")

def get_allowed_admin_roles(guild_id: int) -> list:
    if not os.path.exists(PERMISSIONS_FILE):
        return []
    with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data.get(str(guild_id), {}).get("allowed_role_ids", [])
        except Exception:
            return []

def get_allowed_command_roles(guild_id: int, command: str) -> list:
    if not os.path.exists(PERMISSIONS_FILE):
        return []
    with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data.get(str(guild_id), {}).get("commands", {}).get(command, [])
        except Exception:
            return []

def set_allowed_command_roles(guild_id: int, command: str, role_ids: list):
    data = {}
    if os.path.exists(PERMISSIONS_FILE):
        with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {}
    if "commands" not in data[gid]:
        data[gid]["commands"] = {}
    data[gid]["commands"][command] = role_ids
    with open(PERMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def user_has_admin_role(member: discord.Member, command: Optional[str] = None) -> bool:
    allowed_roles = get_allowed_admin_roles(member.guild.id)
    if command:
        allowed_roles += get_allowed_command_roles(member.guild.id, command)
    if not allowed_roles:
        return False
    member_role_ids = [str(role.id) for role in member.roles]
    return any(role_id in allowed_roles for role_id in member_role_ids)

def user_has_command_permission(member: discord.Member, command: str) -> bool:
    """Check if a user has permission to use a specific normal command.
    
    Args:
        member: The Discord member to check
        command: The command name to check permissions for
        
    Returns:
        bool: True if the user can use the command, False otherwise
    """
    # Administrators can always use commands
    if member.guild_permissions.administrator:
        return True
    
    # Check if there are any custom permissions set for this command
    allowed_roles = get_allowed_command_roles(member.guild.id, command)
    
    # If no custom permissions are set, default to allowing @everyone
    if not allowed_roles:
        return True
    
    # Check if user has any of the allowed roles
    member_role_ids = [str(role.id) for role in member.roles]
    return any(role_id in allowed_roles for role_id in member_role_ids)

def require_command_permission(command_name: str):
    """A decorator that checks if the user has permission to use a specific normal command."""
    def decorator(func):
        async def predicate(interaction: discord.Interaction) -> bool:
            # Guild-only check
            if not interaction.guild or not isinstance(interaction.user, discord.Member):
                return False
            
            # Bot owner can always use commands
            bot = cast('TutuBot', interaction.client)
            if hasattr(bot, 'owner_id') and interaction.user.id == bot.owner_id:
                return True
            
            # Check command permission
            return user_has_command_permission(interaction.user, command_name)
        
        return app_commands.check(predicate)(func)
    return decorator

async def command_permission_check_with_response(interaction: discord.Interaction, command_name: str) -> bool:
    """Check command permission and send error response if denied."""
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        embed = EmbedBuilder.error(
            title="✗ Error",
            description="This command can only be used in a server.",
            guild_id=str(interaction.guild_id) if interaction.guild else None
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    
    # Bot owner can always use commands
    bot = cast('TutuBot', interaction.client)
    if hasattr(bot, 'owner_id') and interaction.user.id == bot.owner_id:
        return True
    
    if user_has_command_permission(interaction.user, command_name):
        return True
    
    embed = EmbedBuilder.error(
        title="✗ Access Denied",
        description="You don't have permission to use this command. Contact an administrator if you believe this is an error.",
        guild_id=str(interaction.guild_id) if interaction.guild else None
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
    return False

def is_owner_or_administrator(command_name: Optional[str] = None):
    """A decorator that checks if the user is the bot owner, has administrator permissions, or an allowed admin role (global or per-command)."""
    def decorator(func):
        async def predicate(interaction: discord.Interaction) -> bool:
            bot = cast('TutuBot', interaction.client)
            # Check if user is the bot owner
            if hasattr(bot, 'owner_id') and interaction.user.id == bot.owner_id:
                return True
            # Check for administrator permission or allowed admin role
            if interaction.guild and isinstance(interaction.user, discord.Member):
                if interaction.user.guild_permissions.administrator or user_has_admin_role(interaction.user, command_name):
                    return True
            # Default deny
            return False
        return app_commands.check(predicate)(func)
    return decorator

async def check_owner_or_admin(interaction: discord.Interaction, command_name: Optional[str] = None) -> bool:
    """Check if the user is the bot owner, has administrator permissions, or an allowed admin role (global or per-command)."""
    bot = cast('TutuBot', interaction.client)
    # Check if user is the bot owner
    if hasattr(bot, 'owner_id') and interaction.user.id == bot.owner_id:
        return True
    # Check for administrator permission or allowed admin role
    if interaction.guild and isinstance(interaction.user, discord.Member):
        if interaction.user.guild_permissions.administrator or user_has_admin_role(interaction.user, command_name):
            return True
    # Default deny
    return False

async def admin_check_with_response(interaction: discord.Interaction, command_name: Optional[str] = None) -> bool:
    if await check_owner_or_admin(interaction, command_name):
        return True
    embed = EmbedBuilder.error(
        title="✗ Access Denied",
        description="You need administrator permissions or an allowed admin role to use this command.",
        guild_id=str(interaction.guild_id) if interaction.guild else None
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
    return False

# Add decorator for permission management: only bot owner or guild administrators
def is_owner_or_guild_admin():
    """A decorator that checks if the user is the bot owner or has administrator permissions."""
    def decorator(func):
        async def predicate(interaction: discord.Interaction) -> bool:
            bot = cast('TutuBot', interaction.client)
            # Check for bot owner
            if hasattr(bot, 'owner_id') and interaction.user.id == bot.owner_id:
                return True
            # Check for administrator permission
            if interaction.guild and isinstance(interaction.user, discord.Member):
                if interaction.user.guild_permissions.administrator:
                    return True
            # Default deny
            return False
        return app_commands.check(predicate)(func)
    return decorator

class PermissionsCog(commands.Cog, name="Permissions"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def load_permissions(self):
        if not os.path.exists(PERMISSIONS_FILE):
            return {}
        with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}

    def save_permissions(self, data):
        with open(PERMISSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_allowed_roles(self, guild_id):
        data = self.load_permissions()
        return data.get(str(guild_id), {}).get("allowed_role_ids", [])

    def set_allowed_roles(self, guild_id, role_ids):
        data = self.load_permissions()
        gid = str(guild_id)
        if gid not in data:
            data[gid] = {}
        data[gid]["allowed_role_ids"] = role_ids
        self.save_permissions(data)

    def get_command_list(self, bot):
        # Return a list of (command_name, description, is_admin)
        commands = [("global", "Global (all admin commands)", True)]
        
        # Get all commands from the bot tree
        all_commands = []
        for cog in bot.cogs.values():
            for cmd in getattr(cog, "get_app_commands", lambda: [])():
                all_commands.append(cmd)
        
        # Fallback: if no get_app_commands, use bot tree
        if not all_commands:
            all_commands = list(bot.tree.get_commands())
        
        # Sort commands by type (admin first, then normal) and then alphabetically
        admin_commands = []
        normal_commands = []
        
        for cmd in all_commands:
            description = cmd.description or cmd.name
            if "[Admin]" in description:
                admin_commands.append((cmd.name, description, True))
            else:
                normal_commands.append((cmd.name, description, False))
        
        # Sort each category alphabetically
        admin_commands.sort(key=lambda x: x[0])
        normal_commands.sort(key=lambda x: x[0])
        
        # Add admin commands first
        commands.extend(admin_commands)
        
        # Add normal commands
        commands.extend(normal_commands)
        
        # Ensure /support is included as an admin command if not already present
        support_found = any(c[0] == "support" for c in commands)
        if not support_found:
            for cmd in bot.tree.get_commands():
                if cmd.name == "support":
                    commands.append((cmd.name, cmd.description or cmd.name, True))
                    break
        
        return commands

    @app_commands.command(name="permissions", description="[Admin] Manage roles that can use specific commands.")
    @is_owner_or_guild_admin()
    async def permissions_menu(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                embed=EmbedBuilder.error(
                    title="✗ Error",
                    description="This command can only be used in a server."
                ),
                ephemeral=True
            )
            return
        commands = self.get_command_list(self.bot)
        view = PermissionsCommandSelectView(self, interaction.guild, commands, "global")
        await view.send_embed(interaction, initial=True)

class PermissionsCommandSelectView(ui.View):
    def __init__(self, cog: PermissionsCog, guild: discord.Guild, commands, selected_command):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild = guild
        self.commands = commands
        self.selected_command = selected_command
        self.add_item(PermissionsCommandSelect(self, commands, selected_command))
        self.role_select = PermissionsRoleSelect(self, guild, selected_command)
        self.add_item(self.role_select)
        # Pagination logic removed: only top 25 roles are shown

    async def send_embed(self, interaction, initial=False):
        allowed_role_ids = []
        if self.selected_command == "global":
            allowed_role_ids = self.cog.get_allowed_roles(self.guild.id)
        else:
            allowed_role_ids = get_allowed_command_roles(self.guild.id, self.selected_command)
        allowed_roles = [self.guild.get_role(int(rid)) for rid in allowed_role_ids if self.guild.get_role(int(rid))]
        embed = EmbedBuilder.info(
            title="🔐 Permissions Management",
            description="Select a command and then select roles to allow them to use that command.\n• **Admin commands** (🛡️): Default access = administrators only\n• **Normal commands** (👤): Default access = everyone\n• Note: Only the top 25 roles by position are shown here.\n• Bot owner and administrators can always use all commands."
        )
        if self.selected_command == "global":
            embed.add_field(
                name="Scope",
                value="Global (all admin commands)",
                inline=False
            )
        else:
            embed.add_field(
                name="Scope",
                value=f"/{self.selected_command}",
                inline=False
            )
        if allowed_roles:
            embed.add_field(
                name="Allowed Roles",
                value='\n'.join(f"• {role.mention}" for role in allowed_roles),
                inline=False
            )
        else:
            embed.add_field(
                name="Allowed Roles",
                value="*(none)*",
                inline=False
            )
        if initial:
            await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

class PermissionsCommandSelect(ui.Select):
    def __init__(self, view: PermissionsCommandSelectView, commands, selected_command):
        options = []
        
        # Group commands by type for better organization
        for name, desc, is_admin in commands:
            if name == "global":
                # Special case for global
                options.append(discord.SelectOption(
                    label="Global (All Admin Commands)",
                    value=name,
                    description="Set permissions for all admin commands",
                    emoji="🌐",
                    default=(name == selected_command)
                ))
            else:
                # Regular command
                emoji = "🛡️" if is_admin else "👤"
                command_type = "Admin" if is_admin else "Normal"
                truncated_desc = (desc[:97] + "...") if len(desc) > 100 else desc
                
                options.append(discord.SelectOption(
                    label=f"/{name}",
                    value=name,
                    description=f"[{command_type}] {truncated_desc}",
                    emoji=emoji,
                    default=(name == selected_command)
                ))
        
        super().__init__(
            placeholder="Select command to manage permissions...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.selected_command = self.values[0]
        # Rebuild the view with the new command selected
        new_view = PermissionsCommandSelectView(self.view_ref.cog, self.view_ref.guild, self.view_ref.commands, self.values[0])
        await new_view.send_embed(interaction)

class PermissionsRoleSelect(ui.Select):
    def __init__(self, view: PermissionsCommandSelectView, guild: discord.Guild, selected_command):
        self.view_ref = view
        self.guild = guild
        self.selected_command = selected_command
        # Only show top 25 roles by position, excluding @everyone and managed roles
        if selected_command == "global":
            allowed_role_ids = set(view.cog.get_allowed_roles(guild.id))
        else:
            allowed_role_ids = set(get_allowed_command_roles(guild.id, selected_command))
        all_roles = [role for role in guild.roles if not role.is_default() and not role.managed]
        all_roles.sort(key=lambda r: r.position, reverse=True)
        roles = all_roles[:25]
        options = []
        for role in roles:
            options.append(discord.SelectOption(
                label=role.name,
                value=str(role.id),
                default=(str(role.id) in allowed_role_ids)
            ))
        super().__init__(
            placeholder="Select roles to allow for this command...",
            min_values=0,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # Only allow bot owner or guild administrators to modify permissions
        bot = cast('TutuBot', interaction.client)
        if not ((hasattr(bot, 'owner_id') and interaction.user.id == bot.owner_id)
                or (interaction.guild and isinstance(interaction.user, discord.Member)
                    and interaction.user.guild_permissions.administrator)):
            return
        # Only top 25 roles are shown, so only update those
        all_roles = [role for role in self.guild.roles if not role.is_default() and not role.managed]
        all_roles.sort(key=lambda r: r.position, reverse=True)
        page_roles = all_roles[:25]
        if self.selected_command == "global":
            current = set(self.view_ref.cog.get_allowed_roles(self.guild.id))
        else:
            current = set(get_allowed_command_roles(self.guild.id, self.selected_command))
        page_role_ids = {str(role.id) for role in page_roles}
        current -= page_role_ids
        current |= set(self.values)
        if self.selected_command == "global":
            self.view_ref.cog.set_allowed_roles(self.guild.id, list(current))
        else:
            set_allowed_command_roles(self.guild.id, self.selected_command, list(current))
        # Rebuild the view to reflect changes
        new_view = PermissionsCommandSelectView(self.view_ref.cog, self.guild, self.view_ref.commands, self.selected_command)
        await new_view.send_embed(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(PermissionsCog(bot)) 