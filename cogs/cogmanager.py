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

    @app_commands.command(name="sync", description="[Admin] Sync slash commands to the server or globally.")
    @is_owner_or_administrator()
    async def sync_commands(self, interaction: discord.Interaction, scope: str):
        """Sync slash commands to Discord with a choice of guild or global sync.
        
        Args:
            scope: The type of sync to perform (guild or global).
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Validate sync_type input
        scope = scope.lower()
        if scope not in ["guild", "global"]:
            embed = EmbedBuilder.error(
                title="✗ Invalid Sync Type",
                description="Invalid sync type. Please use 'guild' or 'global'."
            )
            await send_ephemeral_message(interaction, embed=embed)
            return
        
        try:
            if scope == "global":
                # Sync global commands
                synced_commands = await self.bot.tree.sync()
                command_count = len(synced_commands)
                embed = EmbedBuilder.success(
                    title="✓ Global Commands Synced",
                    description=f"Successfully synced {command_count} slash command(s) globally to all servers.\n• Note: Global sync may take up to an hour to fully update across all servers."
                )
            else:
                # Check if in guild
                if not interaction.guild:
                    await send_ephemeral_message(interaction, content="Guild sync must be used in a server.")
                    return
                # Sync guild-specific commands
                self.bot.tree.copy_global_to(guild=interaction.guild)
                synced_commands = await self.bot.tree.sync(guild=interaction.guild)
                command_count = len(synced_commands)
                embed = EmbedBuilder.success(
                    title="✓ Guild Commands Synced",
                    description=f"Successfully synced {command_count} slash command(s) to this server."
                )
        except Exception as e:
            log.error(f"Error syncing commands ({scope}): {e}")
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
        
        # Add prefix if needed
        if not cog_name.startswith("cogs."):
            cog_name = f"cogs.{cog_name}"
        
        # Check if cog is already loaded
        if cog_name in self.bot.extensions:
            embed = EmbedBuilder.error(
                title="✗ Already Loaded",
                description=f"The cog `{cog_name}` is already loaded."
            )
            await send_ephemeral_message(interaction, embed=embed)
            return
        
        # Try to load the cog
        try:
            await self.bot.load_extension(cog_name)
            log.info(f"Successfully loaded cog: {cog_name}")
            
            embed = EmbedBuilder.success(
                title="✓ Cog Loaded",
                description=f"Successfully loaded `{cog_name}`."
            )
        except Exception as e:
            log.error(f"Error loading cog {cog_name}: {str(e)}")
            
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to load `{cog_name}`: {str(e)}"
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
        
        # Check if the cog exists and is loaded
        if not cog_name.startswith("cogs."):
            cog_name = f"cogs.{cog_name}"
        
        if cog_name not in self.bot.extensions:
            embed = EmbedBuilder.error(
                title="✗ Cog Not Loaded",
                description=f"The cog `{cog_name}` is not currently loaded."
            )
            await send_ephemeral_message(interaction, embed=embed)
            return
        
        # Try to unload the cog
        try:
            await self.bot.unload_extension(cog_name)
            log.info(f"Successfully unloaded cog: {cog_name}")
            
            embed = EmbedBuilder.success(
                title="✓ Cog Unloaded",
                description=f"Successfully unloaded `{cog_name}`."
            )
        except Exception as e:
            log.error(f"Error unloading cog {cog_name}: {str(e)}")
            
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to unload `{cog_name}`: {str(e)}"
            )
        
        await send_ephemeral_message(interaction, embed=embed)

    @app_commands.command(name="reload", description="[Admin] Reloads a specified cog.")
    @is_owner_or_administrator()
    async def reload_cog(self, interaction: discord.Interaction, cog_name: str):
        """Reload a cog by name."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Add prefix if needed
        if not cog_name.startswith("cogs."):
            cog_name = f"cogs.{cog_name}"
        
        # Check if the cog is loaded
        if cog_name not in self.bot.extensions:
            embed = EmbedBuilder.error(
                title="✗ Not Loaded",
                description=f"The cog `{cog_name}` is not currently loaded and cannot be reloaded."
            )
            await send_ephemeral_message(interaction, embed=embed)
            return
        
        # Try to reload the cog
        try:
            await self.bot.reload_extension(cog_name)
            log.info(f"Successfully reloaded cog: {cog_name}")
            
            embed = EmbedBuilder.success(
                title="✓ Cog Reloaded",
                description=f"Successfully reloaded `{cog_name}`."
            )
        except Exception as e:
            log.error(f"Error reloading cog {cog_name}: {str(e)}")
            
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to reload `{cog_name}`: {str(e)}"
            )
        
        await send_ephemeral_message(interaction, embed=embed)

    @app_commands.command(name="list", description="[Admin] Lists available and loaded cogs.")
    @is_owner_or_administrator()
    async def list_cogs(self, interaction: discord.Interaction):
        """List all loaded and available cogs."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        embed = EmbedBuilder.info(
            title="⚙️ Cog Management",
            description="Overview of loaded and available cogs."
        )
        
        # Get loaded cogs
        loaded_cog_names = sorted(self.bot.cogs.keys())
        loaded_cogs_text = "\n".join(f"• {cog}" for cog in loaded_cog_names) or "None"
        embed.add_field(name=f"✓ Loaded Cogs ({len(loaded_cog_names)})", value=loaded_cogs_text, inline=False)
        
        # Get all available cogs - use global function
        available_cogs = get_available_cogs()
        
        # Get the list of loaded modules (fully qualified names)
        loaded_modules = list(self.bot.extensions.keys())
        
        # Find unloaded cogs by checking which available modules aren't loaded
        unloaded_cogs = [cog for cog in available_cogs if cog not in loaded_modules]
        
        # Add unloaded cogs field if any
        if unloaded_cogs:
            unloaded_cogs_text = "\n".join(f"• {cog}" for cog in sorted(unloaded_cogs))
            embed.add_field(name=f"✗ Unloaded Cogs ({len(unloaded_cogs)})", value=unloaded_cogs_text, inline=False)
        
        # Add usage instructions
        embed.add_field(
            name="Commands",
            value=(
                "• Use `/load [name]` to load a cog\n"
                "• Use `/unload [name]` to unload a cog\n"
                "• Use `/reload [name]` to reload a cog"
            ),
            inline=False
        )
        
        await send_ephemeral_message(interaction, embed=embed)


# Simplified setup function
async def setup(bot: 'TutuBot'):
    """Sets up the CogManager cog."""
    await bot.add_cog(CogManager(bot))
    log.info("CogManager loaded.") 