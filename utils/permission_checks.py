import discord
from discord import app_commands
from discord.ext import commands
from typing import Callable, TypeVar, Optional, Union, Awaitable, cast, TYPE_CHECKING
import asyncio

# For type hinting
if TYPE_CHECKING:
    from main import TutuBot

T = TypeVar('T')

def is_owner_or_administrator():
    """A decorator that checks if the user is the bot owner or has administrator permissions.
    
    Usage:
    @app_commands.command()
    @is_owner_or_administrator()
    async def admin_command(self, interaction: discord.Interaction):
        # Command code here
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        bot = cast('TutuBot', interaction.client)
        # Check if user is the bot owner
        if hasattr(bot, 'owner_id') and interaction.user.id == bot.owner_id:
            return True
        
        # Check for administrator permission
        if interaction.guild and isinstance(interaction.user, discord.Member):
            return interaction.user.guild_permissions.administrator
        
        # Default deny
        return False
    
    return app_commands.check(predicate)

async def check_owner_or_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is the bot owner or has administrator permissions.
    
    Args:
        interaction: The Discord interaction
        
    Returns:
        bool: True if user is bot owner or has admin permissions, False otherwise
    """
    bot = cast('TutuBot', interaction.client)
    # Check if user is the bot owner
    if hasattr(bot, 'owner_id') and interaction.user.id == bot.owner_id:
        return True
    
    # Check for administrator permission
    if interaction.guild and isinstance(interaction.user, discord.Member):
        return interaction.user.guild_permissions.administrator
    
    # Default deny
    return False

async def admin_check_with_response(interaction: discord.Interaction) -> bool:
    """Check admin permissions and send error message if permission denied.
    
    Returns True if permitted, False otherwise.
    Also sends an error message to the user if denied.
    
    Args:
        interaction: The Discord interaction
        
    Returns:
        bool: True if permission granted, False otherwise
    """
    if await check_owner_or_admin(interaction):
        return True
    
    # Send error message using the default discord.py ephemeral response
    from utils.embed_builder import EmbedBuilder
    
    embed = EmbedBuilder.error(
        title="✗ Access Denied",
        description="You need administrator permissions to use this command.",
        guild_id=str(interaction.guild_id) if interaction.guild else None
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    return False 