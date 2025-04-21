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

from cogs.permissions import is_owner_or_administrator, admin_check_with_response
from utils.embed_builder import EmbedBuilder

# For type hinting only
if typing.TYPE_CHECKING:
    # Need to import the bot class for type hints
    from main import TutuBot

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
    """
    Provides slash commands to manage the bot's cogs (load, unload, reload, sync, list, info).
    Includes robust error handling, type hints, DRY helpers, and improved user feedback.
    """
    def __init__(self, bot: 'TutuBot') -> None:
        self.bot = bot
        self.core_cogs = getattr(self.bot, 'initial_cogs', [])
        self.actual_core_cogs = ['cogs.cogmanager']

    async def _send_embed(self, interaction: discord.Interaction, embed: discord.Embed) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    def _normalize_cog_name(self, cog_name: str) -> str:
        return cog_name if cog_name.startswith("cogs.") else f"cogs.{cog_name}"

    def _is_core_cog(self, cog_name: str) -> bool:
        return cog_name in self.actual_core_cogs

    def _get_loaded_cogs(self) -> set[str]:
        return set(self.bot.extensions.keys())

    @app_commands.command(name="sync", description="[Admin] Sync slash commands to the server or globally.")
    @is_owner_or_administrator()
    async def sync_commands(self, interaction: discord.Interaction, scope: str) -> None:
        """
        Sync slash commands to Discord with a choice of guild or global sync.
        Args:
            scope: The type of sync to perform (guild or global).
        """
        scope = scope.lower()
        if scope not in ["guild", "global"]:
            embed = EmbedBuilder.error(
                title="✗ Invalid Sync Type",
                description="Invalid sync type. Please use 'guild' or 'global'."
            )
            await self._send_embed(interaction, embed)
            return
        try:
            if scope == "global":
                synced_commands = await self.bot.tree.sync()
                embed = EmbedBuilder.success(
                    title="✓ Global Commands Synced",
                    description=f"Successfully synced {len(synced_commands)} slash command(s) globally.\nNote: Global sync may take up to an hour to propagate."
                )
            else:
                if not interaction.guild:
                    await self._send_embed(interaction, EmbedBuilder.error(
                        title="✗ Guild Sync Error",
                        description="Guild sync must be used in a server."
                    ))
                    return
                self.bot.tree.copy_global_to(guild=interaction.guild)
                synced_commands = await self.bot.tree.sync(guild=interaction.guild)
                embed = EmbedBuilder.success(
                    title="✓ Guild Commands Synced",
                    description=f"Successfully synced {len(synced_commands)} slash command(s) to this server."
                )
        except Exception as e:
            log.error(f"Error syncing commands ({scope}): {e}")
            embed = EmbedBuilder.error(
                title="✗ Sync Failed",
                description=f"Failed to sync commands: {str(e)}"
            )
        await self._send_embed(interaction, embed)

    @sync_commands.autocomplete("scope")
    async def sync_commands_autocomplete(self, interaction: discord.Interaction, current: str) -> list:
        choices = ["global", "guild"]
        return [app_commands.Choice(name=choice, value=choice) for choice in choices if current.lower() in choice.lower()]

    @app_commands.command(name="load", description="[Admin] Loads a specified cog.")
    @is_owner_or_administrator()
    async def load_cog(self, interaction: discord.Interaction, cog_name: str) -> None:
        """
        Load a cog by name.
        """
        cog_name = self._normalize_cog_name(cog_name)
        if cog_name in self.bot.extensions:
            embed = EmbedBuilder.error(
                title="✗ Already Loaded",
                description=f"The cog `{cog_name}` is already loaded."
            )
            await self._send_embed(interaction, embed)
            return
        try:
            await self.bot.load_extension(cog_name)
            log.info(f"Successfully loaded cog: {cog_name}")
            embed = EmbedBuilder.success(
                title="✓ Cog Loaded",
                description=f"Successfully loaded `{cog_name}`."
            )
        except Exception as e:
            log.error(f"Error loading cog {cog_name}: {e}")
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to load `{cog_name}`: {str(e)}"
            )
        await self._send_embed(interaction, embed)

    @load_cog.autocomplete("cog_name")
    async def load_cog_autocomplete(self, interaction: discord.Interaction, current: str) -> list:
        all_cogs = get_available_cogs()
        loaded = self._get_loaded_cogs()
        options = [cog for cog in all_cogs if current.lower() in cog.lower() and cog not in loaded]
        return [app_commands.Choice(name=cog.split(".")[-1], value=cog.split(".")[-1]) for cog in sorted(options)]

    @app_commands.command(name="unload", description="[Admin] Unloads a specified cog.")
    @is_owner_or_administrator()
    async def unload_cog(self, interaction: discord.Interaction, cog_name: str) -> None:
        """
        Unload a cog by name.
        """
        cog_name = self._normalize_cog_name(cog_name)
        if self._is_core_cog(cog_name):
            embed = EmbedBuilder.error(
                title="✗ Core Cog",
                description=f"`{cog_name}` is a core cog and cannot be unloaded."
            )
            await self._send_embed(interaction, embed)
            return
        if cog_name not in self.bot.extensions:
            embed = EmbedBuilder.error(
                title="✗ Not Loaded",
                description=f"The cog `{cog_name}` is not loaded."
            )
            await self._send_embed(interaction, embed)
            return
        try:
            await self.bot.unload_extension(cog_name)
            log.info(f"Successfully unloaded cog: {cog_name}")
            embed = EmbedBuilder.success(
                title="✓ Cog Unloaded",
                description=f"Successfully unloaded `{cog_name}`."
            )
        except Exception as e:
            log.error(f"Error unloading cog {cog_name}: {e}")
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to unload `{cog_name}`: {str(e)}"
            )
        await self._send_embed(interaction, embed)

    @unload_cog.autocomplete("cog_name")
    async def unload_cog_autocomplete(self, interaction: discord.Interaction, current: str) -> list:
        loaded = self._get_loaded_cogs()
        options = [cog for cog in loaded if current.lower() in cog.lower() and not self._is_core_cog(cog)]
        return [app_commands.Choice(name=cog.split(".")[-1], value=cog.split(".")[-1]) for cog in sorted(options)]

    @app_commands.command(name="reload", description="[Admin] Reloads a specified cog.")
    @is_owner_or_administrator()
    async def reload_cog(self, interaction: discord.Interaction, cog_name: str) -> None:
        """
        Reload a cog by name.
        """
        cog_name = self._normalize_cog_name(cog_name)
        if cog_name not in self.bot.extensions:
            embed = EmbedBuilder.error(
                title="✗ Not Loaded",
                description=f"The cog `{cog_name}` is not loaded."
            )
            await self._send_embed(interaction, embed)
            return
        try:
            await self.bot.reload_extension(cog_name)
            log.info(f"Successfully reloaded cog: {cog_name}")
            embed = EmbedBuilder.success(
                title="✓ Cog Reloaded",
                description=f"Successfully reloaded `{cog_name}`."
            )
        except Exception as e:
            log.error(f"Error reloading cog {cog_name}: {e}")
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to reload `{cog_name}`: {str(e)}"
            )
        await self._send_embed(interaction, embed)

    @reload_cog.autocomplete("cog_name")
    async def reload_cog_autocomplete(self, interaction: discord.Interaction, current: str) -> list:
        loaded = self._get_loaded_cogs()
        options = [cog for cog in loaded if current.lower() in cog.lower()]
        return [app_commands.Choice(name=cog.split(".")[-1], value=cog.split(".")[-1]) for cog in sorted(options)]

    @app_commands.command(name="list", description="[Admin] List all loaded and available cogs.")
    @is_owner_or_administrator()
    async def list_cogs(self, interaction: discord.Interaction) -> None:
        """
        List all loaded and available cogs.
        """
        loaded = self._get_loaded_cogs()
        available = get_available_cogs()
        unloaded = available - loaded
        embed = EmbedBuilder.info(
            title="📦 Cogs List",
            description="Current status of all cogs."
        )
        embed.add_field(
            name=f"✓ Loaded Cogs ({len(loaded)})",
            value="\n".join(f"• {cog}" for cog in sorted(loaded)) or "None",
            inline=False
        )
        embed.add_field(
            name=f"✗ Unloaded Cogs ({len(unloaded)})",
            value="\n".join(f"• {cog}" for cog in sorted(unloaded)) or "None",
            inline=False
        )
        embed.add_field(
            name="Commands",
            value=(
                "• Use `/load [name]` to load a cog\n"
                "• Use `/unload [name]` to unload a cog\n"
                "• Use `/reload [name]` to reload a cog"
            ),
            inline=False
        )
        await self._send_embed(interaction, embed)

    @app_commands.command(name="info", description="[Admin] Get information about a cog.")
    @is_owner_or_administrator()
    async def info_cog(self, interaction: discord.Interaction, cog_name: str) -> None:
        """
        Get detailed information about a cog.
        """
        import importlib.util, inspect
        cog_name_full = self._normalize_cog_name(cog_name)
        try:
            spec = importlib.util.find_spec(cog_name_full)
            if spec is None:
                available_raw = sorted(get_available_cogs())
                available_names = ", ".join(cog.split('.')[-1] for cog in available_raw) if available_raw else "None"
                embed = EmbedBuilder.error(
                    title="✗ Cog Not Found",
                    description=f"The cog `{cog_name}` does not exist.\nAvailable cogs: {available_names}"
                )
                await self._send_embed(interaction, embed)
                return
            module = importlib.import_module(cog_name_full)
            cog_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, commands.Cog) and obj.__module__ == module.__name__:
                    cog_class = obj
                    break
            description = inspect.getdoc(cog_class) if cog_class else "No description available."
            cog_instance = self.bot.get_cog(cog_class.__name__) if cog_class else None
            if cog_instance:
                if hasattr(cog_instance, "__cog_app_commands__"):
                    cmds = [cmd.name for cmd in getattr(cog_instance, "__cog_app_commands__") if hasattr(cmd, "name")]
                else:
                    cmds = [cmd.name for cmd in self.bot.tree.get_commands() if getattr(cmd, 'cog', None) == cog_instance]
                cmds_display = ", ".join(sorted(cmds)) if cmds else "None"
            else:
                cmds_display = "Not loaded."
            embed = EmbedBuilder.info(
                title=f"📑 Cog Info: {cog_name}",
                description=(
                    f"• **Module:** `{spec.origin}`\n"
                    f"• **Description:** {description}\n"
                    f"• **Commands:** {cmds_display}"
                )
            )
        except Exception as e:
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Failed to get cog info for `{cog_name}`: {str(e)}"
            )
        await self._send_embed(interaction, embed)

    @info_cog.autocomplete("cog_name")
    async def info_cog_autocomplete(self, interaction: discord.Interaction, current: str) -> list:
        available = sorted(get_available_cogs())
        options = [cog for cog in available if current.lower() in cog.lower()]
        return [app_commands.Choice(name=cog.split('.')[-1], value=cog.split('.')[-1]) for cog in options]

# Simplified setup function
async def setup(bot: 'TutuBot') -> None:
    """
    Sets up the CogManager cog.
    """
    await bot.add_cog(CogManager(bot))
    log.info("CogManager loaded.")