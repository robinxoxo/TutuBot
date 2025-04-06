import discord
from discord import app_commands
from discord.ext import commands
import logging
import typing
import platform
from datetime import datetime
from typing import Optional

# For type hinting only
if typing.TYPE_CHECKING:
    from main import TutuBot

# Configure logging
log = logging.getLogger(__name__)

class InfoCog(commands.Cog, name="Info"):
    """Information commands for server, user, and bot details."""

    def __init__(self, bot: 'TutuBot'):
        """Initialize the Info cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
    
    @app_commands.command(name="serverinfo", description="Show information about the server")
    async def server_info(self, interaction: discord.Interaction):
        """Displays information about the current server.
        
        Args:
            interaction: The Discord interaction
        """
        # Ensure this is used in a server
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in servers.",
                ephemeral=True
            )
            return
        
        guild = interaction.guild
        
        # Create embed with server info
        embed = discord.Embed(
            title=f"📊 {guild.name}",
            color=discord.Color.blue()
        )
        
        # Add server icon if available
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # General information
        created_time = int(guild.created_at.timestamp())
        
        # Count channels by type
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        # Member counts
        total_members = guild.member_count or 0
        bot_count = sum(1 for member in guild.members if member.bot)
        human_count = total_members - bot_count
        
        # Premium information
        premium_tier = guild.premium_tier
        premium_subs = guild.premium_subscription_count
        
        # Add fields
        embed.add_field(
            name="ID",
            value=f"`{guild.id}`",
            inline=True
        )
        
        embed.add_field(
            name="Owner",
            value=f"<@{guild.owner_id}>",
            inline=True
        )
        
        embed.add_field(
            name="Created",
            value=f"<t:{created_time}:R> (<t:{created_time}:D>)",
            inline=True
        )
        
        embed.add_field(
            name="Members",
            value=f"👥 {human_count} humans\n🤖 {bot_count} bots\n**Total:** {total_members}",
            inline=True
        )
        
        embed.add_field(
            name="Channels",
            value=f"💬 {text_channels} text\n🔊 {voice_channels} voice\n📁 {categories} categories",
            inline=True
        )
        
        embed.add_field(
            name="Roles",
            value=f"🏷️ {len(guild.roles) - 1} roles", # -1 to exclude @everyone
            inline=True
        )
        
        embed.add_field(
            name="Nitro",
            value=f"Level {premium_tier}\n{premium_subs} boosts",
            inline=True
        )
        
        embed.add_field(
            name="Features",
            value=", ".join(f"`{feature}`" for feature in guild.features) or "None",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
        
    @app_commands.command(name="userinfo", description="Show information about a user")
    @app_commands.describe(user="The user to get information about (defaults to yourself)")
    async def user_info(self, 
                         interaction: discord.Interaction, 
                         user: Optional[discord.User] = None):
        """Displays information about a user.
        
        Args:
            interaction: The Discord interaction
            user: The user to get information about, defaults to the command user
        """
        # Default to command user if not specified
        target_user = user or interaction.user
        
        # Create basic embed
        embed = discord.Embed(
            title=f"👤 User Information",
            color=discord.Color.blue()
        )
        
        # Set user avatar if available
        if target_user.avatar:
            embed.set_thumbnail(url=target_user.avatar.url)
        
        # Add username and basic info
        created_time = int(target_user.created_at.timestamp())
        embed.add_field(
            name="Username",
            value=target_user.name,
            inline=True
        )
        
        embed.add_field(
            name="ID",
            value=f"`{target_user.id}`",
            inline=True
        )
        
        embed.add_field(
            name="Created",
            value=f"<t:{created_time}:R> (<t:{created_time}:D>)",
            inline=True
        )
        
        embed.add_field(
            name="Bot",
            value="Yes" if target_user.bot else "No",
            inline=True
        )
        
        # Add member-specific info if in a guild
        if interaction.guild and isinstance(target_user, discord.Member):
            # Joined time
            joined_time = int(target_user.joined_at.timestamp()) if target_user.joined_at else 0
            
            # Status and activity
            status = str(target_user.status).title() if hasattr(target_user, 'status') else "Unknown"
            activity = ""
            
            for act in target_user.activities:
                if isinstance(act, discord.Game):
                    activity += f"Playing {act.name}\n"
                elif isinstance(act, discord.Streaming):
                    activity += f"Streaming [{act.name}]({act.url})\n"
                elif isinstance(act, discord.Spotify):
                    activity += f"Listening to {act.title} by {act.artist}\n"
                elif isinstance(act, discord.Activity):
                    if act.type == discord.ActivityType.watching:
                        activity += f"Watching {act.name}\n"
                    elif act.type == discord.ActivityType.listening:
                        activity += f"Listening to {act.name}\n"
                    elif act.type == discord.ActivityType.competing:
                        activity += f"Competing in {act.name}\n"
                    else:
                        activity += f"{act.name}\n"
            
            # Count roles (exclude @everyone)
            role_count = len(target_user.roles) - 1
            top_role = target_user.top_role.mention if role_count > 0 else "None"
            
            # Add member fields
            embed.add_field(
                name="Joined Server",
                value=f"<t:{joined_time}:R> (<t:{joined_time}:D>)" if joined_time else "Unknown",
                inline=True
            )
            
            embed.add_field(
                name="Nickname",
                value=target_user.nick or "None",
                inline=True
            )
            
            embed.add_field(
                name="Status",
                value=status,
                inline=True
            )
            
            if activity:
                embed.add_field(
                    name="Activity",
                    value=activity,
                    inline=True
                )
            
            embed.add_field(
                name="Roles",
                value=f"{role_count} roles • Top: {top_role}",
                inline=True
            )
            
            # Check permissions
            if target_user.guild_permissions.administrator:
                embed.add_field(
                    name="Permissions",
                    value="Administrator",
                    inline=True
                )
            elif target_user.guild_permissions.manage_guild:
                embed.add_field(
                    name="Permissions",
                    value="Server Manager",
                    inline=True
                )
            elif target_user.guild_permissions.ban_members:
                embed.add_field(
                    name="Permissions",
                    value="Moderator",
                    inline=True
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    @app_commands.command(name="avatar", description="Show a user's avatar")
    @app_commands.describe(user="The user whose avatar to show (defaults to yourself)")
    async def avatar(self, 
                      interaction: discord.Interaction, 
                      user: Optional[discord.User] = None):
        """Displays a user's avatar.
        
        Args:
            interaction: The Discord interaction
            user: The user whose avatar to show, defaults to the command user
        """
        # Default to command user if not specified
        target_user = user or interaction.user
        
        # Create the embed
        embed = discord.Embed(
            title=f"{target_user.name}'s Avatar",
            color=discord.Color.blue()
        )
        
        # Add the avatar
        if target_user.avatar:
            embed.set_image(url=target_user.avatar.url)
            
            # Add download links for different sizes
            formats = []
            
            # Use proper literals that match discord.py's AssetFormatTypes
            png_url = target_user.avatar.with_static_format('png').url
            jpg_url = target_user.avatar.with_static_format('jpg').url
            webp_url = target_user.avatar.with_static_format('webp').url
            
            formats.append(f"[png]({png_url})")
            formats.append(f"[jpg]({jpg_url})")
            formats.append(f"[webp]({webp_url})")
            
            if target_user.avatar.is_animated():
                gif_url = target_user.avatar.url
                formats.append(f"[gif]({gif_url})")
                
            embed.add_field(
                name="Download",
                value=" • ".join(formats),
                inline=False
            )
        else:
            embed.description = "This user has no custom avatar."
            
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    @app_commands.command(name="roleinfo", description="Show information about a role")
    @app_commands.describe(role="The role to get information about")
    async def role_info(self, interaction: discord.Interaction, role: discord.Role):
        """Displays information about a specific role.
        
        Args:
            interaction: The Discord interaction
            role: The role to get information about
        """
        # Create embed with role info
        embed = discord.Embed(
            title=f"🏷️ Role Information: {role.name}",
            color=role.color if role.color != discord.Color.default() else discord.Color.blue()
        )
        
        # General information
        created_time = int(role.created_at.timestamp())
        member_count = len(role.members)
        
        embed.add_field(
            name="ID",
            value=f"`{role.id}`",
            inline=True
        )
        
        embed.add_field(
            name="Created",
            value=f"<t:{created_time}:R> (<t:{created_time}:D>)",
            inline=True
        )
        
        embed.add_field(
            name="Color",
            value=f"#{role.color.value:06x}" if role.color != discord.Color.default() else "Default",
            inline=True
        )
        
        embed.add_field(
            name="Members",
            value=str(member_count),
            inline=True
        )
        
        embed.add_field(
            name="Position",
            value=str(role.position),
            inline=True
        )
        
        embed.add_field(
            name="Mentionable",
            value="Yes" if role.mentionable else "No",
            inline=True
        )
        
        embed.add_field(
            name="Hoisted",
            value="Yes" if role.hoist else "No",
            inline=True
        )
        
        embed.add_field(
            name="Managed",
            value="Yes" if role.managed else "No",
            inline=True
        )
        
        # Add key permissions
        perms = []
        permissions = role.permissions
        
        permission_map = {
            "administrator": "Administrator",
            "manage_guild": "Manage Server",
            "manage_roles": "Manage Roles",
            "manage_channels": "Manage Channels",
            "kick_members": "Kick Members",
            "ban_members": "Ban Members",
            "manage_messages": "Manage Messages",
            "mention_everyone": "Mention Everyone",
            "manage_webhooks": "Manage Webhooks",
            "manage_emojis": "Manage Emojis"
        }
        
        for perm, display_name in permission_map.items():
            if getattr(permissions, perm):
                perms.append(f"✓ {display_name}")
        
        if perms:
            embed.add_field(
                name="Key Permissions",
                value="\n".join(perms),
                inline=False
            )
        else:
            embed.add_field(
                name="Key Permissions",
                value="None",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    @app_commands.command(name="botinfo", description="Show information about the bot")
    async def bot_info(self, interaction: discord.Interaction):
        """Displays information about the bot.
        
        Args:
            interaction: The Discord interaction
        """
        # Create embed with bot info
        embed = discord.Embed(
            title=f"🤖 Bot Information",
            description=f"Information about {self.bot.user.name if self.bot.user else 'the bot'}",
            color=discord.Color.blue()
        )
        
        # Add bot avatar if available
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        # Calculate uptime
        bot_uptime = discord.utils.utcnow() - self.bot.user.created_at if self.bot.user else None
        uptime_str = str(bot_uptime).split(".")[0] if bot_uptime else "Unknown"
        
        # Count servers, channels, and users
        guild_count = len(self.bot.guilds)
        channel_count = sum(len(guild.channels) for guild in self.bot.guilds)
        user_count = sum(guild.member_count or 0 for guild in self.bot.guilds)
        
        # Get command count
        command_count = len(self.bot.tree.get_commands())
        
        # Add fields
        embed.add_field(
            name="ID",
            value=f"`{self.bot.user.id}`" if self.bot.user else "Unknown",
            inline=True
        )
        
        embed.add_field(
            name="Owner",
            value=f"<@{self.bot.owner_id}>" if hasattr(self.bot, "owner_id") else "Unknown",
            inline=True
        )
        
        embed.add_field(
            name="Created",
            value=f"<t:{int(self.bot.user.created_at.timestamp())}:R>" if self.bot.user else "Unknown",
            inline=True
        )
        
        embed.add_field(
            name="Uptime",
            value=uptime_str,
            inline=True
        )
        
        embed.add_field(
            name="Library",
            value=f"discord.py {discord.__version__}",
            inline=True
        )
        
        embed.add_field(
            name="Python",
            value=platform.python_version(),
            inline=True
        )
        
        embed.add_field(
            name="Servers",
            value=str(guild_count),
            inline=True
        )
        
        embed.add_field(
            name="Channels",
            value=str(channel_count),
            inline=True
        )
        
        embed.add_field(
            name="Users",
            value=str(user_count),
            inline=True
        )
        
        embed.add_field(
            name="Commands",
            value=str(command_count),
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot: 'TutuBot'):
    """Sets up the InfoCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(InfoCog(bot))
    log.info("InfoCog loaded.") 