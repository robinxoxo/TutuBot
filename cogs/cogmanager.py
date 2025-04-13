import discord
from discord import app_commands
from discord.ext import commands
# from discord.utils import MISSING # No longer needed
import os
import logging
import typing
import importlib.util
import inspect
import sys
import importlib
import pkgutil
from typing import List, Dict, Any, Optional, Union, Set, TYPE_CHECKING

from utils.permission_checks import is_owner_or_administrator, admin_check_with_response
from utils.embed_builder import EmbedBuilder

# For type hinting only
if typing.TYPE_CHECKING:
    # Need to import the bot class for type hints
    from main import TutuBot
else:
    # Import at runtime to prevent circular imports
    from utils.interaction_utils import send_ephemeral_message

# Configure logging
log = logging.getLogger(__name__)

def get_available_cogs(exclude_cogs: List[str] = None) -> Set[str]:
    """Get all available cogs in the cogs directory.
    
    Args:
        exclude_cogs: List of cog modules to exclude
        
    Returns:
        Set of cog module names
    """
    if exclude_cogs is None:
        exclude_cogs = []
        
    cogs_dir = 'cogs'
    extension_paths = set()
    
    # Check that the cogs directory exists
    if not os.path.isdir(cogs_dir):
        return extension_paths
    
    # Look for all Python files in the cogs directory
    for filename in os.listdir(cogs_dir):
        if filename.startswith('_'):
            continue  # Skip __pycache__ and other special directories/files
            
        if os.path.isdir(os.path.join(cogs_dir, filename)):
            # This is a subdirectory, check for __init__.py
            if os.path.exists(os.path.join(cogs_dir, filename, '__init__.py')):
                extension_path = f'cogs.{filename}'
                if extension_path not in exclude_cogs:
                    extension_paths.add(extension_path)
        elif filename.endswith('.py'):
            # This is a Python file
            extension_path = f'cogs.{filename[:-3]}'
            if extension_path not in exclude_cogs:
                extension_paths.add(extension_path)
                
    return extension_paths

class CogManager(commands.Cog):
    """Provides slash commands to manage the bot's cogs."""

    def __init__(self, bot: 'TutuBot'):
        self.bot = bot
        self.core_cogs = getattr(self.bot, 'initial_cogs', [])
        # Ensure only cogmanager and faq are treated as core
        self.actual_core_cogs = ['cogs.cogmanager']

    @app_commands.command(name="sync", description="[Admin] Sync slash commands to the server.")
    @is_owner_or_administrator()
    async def sync_commands(self, interaction: discord.Interaction):
        """Sync slash commands to Discord."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Check if in guild
        if not interaction.guild:
            await send_ephemeral_message(interaction, content="This command must be used in a server for guild syncing.")
            return
            
        try:
            # First sync global commands
            await self.bot.tree.sync()
            
            # Then sync guild-specific commands for this guild
            self.bot.tree.copy_global_to(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
            
            embed = EmbedBuilder.success(
                title="✓ Commands Synced",
                description="Successfully synced slash commands to Discord."
            )
            await send_ephemeral_message(interaction, embed=embed)
        except Exception as e:
            log.error(f"Error syncing commands: {e}")
            embed = EmbedBuilder.error(
                title="✗ Sync Failed",
                description=f"Failed to sync commands: {str(e)}"
            )
            await send_ephemeral_message(interaction, embed=embed)

    @app_commands.command(name="load", description="[Admin] Loads a specified cog.")
    @is_owner_or_administrator()
    async def load_cog(self, interaction: discord.Interaction, cog_name: str):
        """Load a cog by name."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        result = await self.bot.load_extension(cog_name)
        if result["success"]:
            embed = EmbedBuilder.success(
                title="✓ Cog Loaded",
                description=f"Successfully loaded `{cog_name}`."
            )
        else:
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to load `{cog_name}`: {result['error']}"
            )
        
        await send_ephemeral_message(interaction, embed=embed)

    @app_commands.command(name="unload", description="[Admin] Unloads a specified cog.")
    @is_owner_or_administrator()
    async def unload_cog(self, interaction: discord.Interaction, cog_name: str):
        """Unload a cog by name."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Don't allow unloading this cog
        if cog_name.lower() in ["cogmanager", "cogs.cogmanager"]:
            embed = EmbedBuilder.error(
                title="✗ Cannot Unload",
                description="You cannot unload the CogManager cog."
            )
            await send_ephemeral_message(interaction, embed=embed)
            return
        
        result = await self.bot.unload_extension(cog_name)
        if result["success"]:
            embed = EmbedBuilder.success(
                title="✓ Cog Unloaded",
                description=f"Successfully unloaded `{cog_name}`."
            )
        else:
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to unload `{cog_name}`: {result['error']}"
            )
        
        await send_ephemeral_message(interaction, embed=embed)

    @app_commands.command(name="reload", description="[Admin] Reloads a specified cog.")
    @is_owner_or_administrator()
    async def reload_cog(self, interaction: discord.Interaction, cog_name: str):
        """Reload a cog by name."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        result = await self.bot.reload_extension(cog_name)
        if result["success"]:
            embed = EmbedBuilder.success(
                title="✓ Cog Reloaded",
                description=f"Successfully reloaded `{cog_name}`."
            )
        else:
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to reload `{cog_name}`: {result['error']}"
            )
        
        await send_ephemeral_message(interaction, embed=embed)

    @app_commands.command(name="list", description="[Admin] Lists available and loaded cogs.")
    @is_owner_or_administrator()
    async def list_cogs(self, interaction: discord.Interaction):
        """List all loaded cogs."""
        cog_list = sorted(self.bot.cogs.keys())
        
        embed = EmbedBuilder.info(
            title="📋 Loaded Cogs",
            description=f"There are {len(cog_list)} cogs currently loaded."
        )
        
        # Add cogs to embed
        cogs_formatted = "\n".join(f"• {cog}" for cog in cog_list)
        embed.add_field(name="Cogs", value=cogs_formatted, inline=False)
        
        await send_ephemeral_message(interaction, embed=embed)

    @app_commands.command(name="cogs", description="[Admin] Manage bot cogs/extensions")
    @is_owner_or_administrator()
    async def manage_cogs(self, interaction: discord.Interaction):
        """Manage cogs loaded in the bot."""
        embed = EmbedBuilder.info(
            title="⚙️ Cog Management",
            description="Manage which cogs are loaded in the bot."
        )
        
        # Add fields for loaded and unloaded cogs
        loaded_cogs = "\n".join(f"• {cog}" for cog in sorted(self.bot.cogs.keys()))
        embed.add_field(name="Loaded Cogs", value=loaded_cogs or "None", inline=False)
        
        # Get list of available cogs from the directory
        available_cogs = self.get_available_cogs()
        unloaded_cogs = "\n".join(
            f"• {cog}" for cog in sorted(available_cogs) 
            if cog not in self.bot.cogs.keys() and not cog.startswith("_")
        )
        embed.add_field(name="Unloaded Cogs", value=unloaded_cogs or "None", inline=False)
        
        # Add usage instructions
        embed.add_field(
            name="Commands",
            value=(
                "• Use `/cogs load [name]` to load a cog\n"
                "• Use `/cogs unload [name]` to unload a cog\n"
                "• Use `/cogs reload [name]` to reload a cog"
            ),
            inline=False
        )
        
        await send_ephemeral_message(interaction, embed=embed)


# Simplified setup function
async def setup(bot: 'TutuBot'):
    """Sets up the CogManager cog."""
    await bot.add_cog(CogManager(bot))
    log.info("CogManager loaded.") 