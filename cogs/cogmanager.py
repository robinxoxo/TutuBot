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
from typing import List, Dict, Any, Optional, Union

from utils.permission_checks import admin_check_with_response
from utils.embed_builder import EmbedBuilder

# For type hinting only
if typing.TYPE_CHECKING:
    # Need to import the bot class for type hints
    from main import TutuBot

# Configure logging
log = logging.getLogger(__name__)

def get_available_cogs(core_cogs=None):
    """Returns a list of available cogs in the cogs directory.
    
    Args:
        core_cogs: Optional list of core cog names to exclude from the result
    """
    core_cogs = core_cogs or []
    cogs_dir = './cogs'
    if not os.path.isdir(cogs_dir):
        log.warning(f"Cogs directory '{cogs_dir}' not found.")
        return []
    
    cogs_list = []
    for filename in os.listdir(cogs_dir):
        if filename.endswith('.py'):
            cog_name = f'cogs.{filename[:-3]}'
            # Only add if not in core_cogs list
            if cog_name not in core_cogs:
                cogs_list.append(cog_name)
    
    return cogs_list

class CogManager(commands.Cog):
    """Provides slash commands to manage the bot's cogs."""

    def __init__(self, bot: 'TutuBot'):
        self.bot = bot
        self.core_cogs = getattr(self.bot, 'initial_cogs', [])
        # Ensure only cogmanager and faq are treated as core
        self.actual_core_cogs = ['cogs.cogmanager']

    async def _check_permission(self, interaction: discord.Interaction) -> bool:
        """Check if the user has permission to use admin commands.
        
        Returns True if the user is the bot owner or has administrator permission.
        """
        # Always allow bot owner
        if interaction.user.id == self.bot.owner_id:
            return True
            
        # Check for admin permission if in a guild
        if interaction.guild and isinstance(interaction.user, discord.Member):
            return interaction.user.guild_permissions.administrator
            
        # Default to False if not owner and not admin
        return False

    @app_commands.command(name="sync", description="[Admin] Sync slash commands to the server.")
    async def sync_commands(self, interaction: discord.Interaction, target: str = "guild"):
        """Syncs slash commands to the guild or globally.
        
        Args:
            interaction: The interaction object
            target: Where to sync commands ("guild" or "global")
        """
        # Permission check
        if not await admin_check_with_response(interaction):
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            if target.lower() == "guild":
                if interaction.guild is None:
                    await interaction.followup.send("This command must be used in a server for guild syncing.", ephemeral=True)
                    return
                 
                # Sync to the current guild
                self.bot.tree.copy_global_to(guild=interaction.guild)
                commands = await self.bot.tree.sync(guild=interaction.guild)
                count = len(commands)
                
                embed = EmbedBuilder.success(
                    title="🔄 Commands Synced",
                    description=f"Successfully synced {count} commands to this server.\nThey should be available immediately."
                )
  
                await interaction.followup.send(embed=embed, ephemeral=True)
                log.info(f"Synced {count} commands to guild {interaction.guild.id} ({interaction.guild.name})")
            else:
                # Global sync - takes longer to propagate
                commands = await self.bot.tree.sync()
                count = len(commands)
                
                embed = EmbedBuilder.success(
                    title="🔄 Commands Synced",
                    description=f"Successfully synced {count} commands globally."
                )
                
                embed.add_field(
                    name="Note",
                    value="This may take up to an hour to propagate to all servers.",
                    inline=False
                )
                    
                await interaction.followup.send(embed=embed, ephemeral=True)
                log.info(f"Synced {count} commands globally")
                
        except Exception as e:
            log.exception(f"Error syncing commands: {e}")
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"An error occurred while syncing commands: {str(e)}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="load", description="[Admin] Loads a specified cog.")
    async def load_cog(self, interaction: discord.Interaction, cog_name: str):
        """Loads a non-core cog. Provide the name without 'cogs.' prefix."""
        # Permission check
        if not await self._check_permission(interaction):
            embed = EmbedBuilder.error(
                title="🚫 Access Denied",
                description="You need administrator permissions to use this command."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        actual_cog_name = f"cogs.{cog_name}"
        available_cogs = get_available_cogs(self.actual_core_cogs)
        if actual_cog_name not in available_cogs:
            embed = EmbedBuilder.error(
                title="✗ Cog Not Found",
                description=f"`{cog_name}` not found in available cogs."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await self.bot.load_extension(actual_cog_name)
            log.info(f"Cog '{actual_cog_name}' loaded by {interaction.user}.")
            
            embed = EmbedBuilder.success(
                title="✓ Cog Loaded",
                description=f"`{cog_name}` loaded successfully."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except commands.ExtensionAlreadyLoaded:
            log.warning(f"Attempted to load already loaded cog '{actual_cog_name}' by {interaction.user}.")
            
            embed = EmbedBuilder.warning(
                title="⚠️ Already Loaded",
                description=f"`{cog_name}` is already loaded."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except commands.ExtensionNotFound:
            log.error(f"Cog '{actual_cog_name}' not found during load attempt by {interaction.user}.")
            
            embed = EmbedBuilder.error(
                title="✗ Cog Not Found",
                description=f"`{cog_name}` could not be found."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.exception(f"Error loading cog '{actual_cog_name}' by {interaction.user}: {e}")
            
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Error loading `{cog_name}`: {str(e)}"
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="unload", description="[Admin] Unloads a specified cog.")
    async def unload_cog(self, interaction: discord.Interaction, cog_name: str):
        """Unloads a non-core cog. Provide the name without 'cogs.' prefix."""
        # Permission check
        if not await self._check_permission(interaction):
            embed = EmbedBuilder.error(
                title="🚫 Access Denied",
                description="You need administrator permissions to use this command."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        actual_cog_name = f"cogs.{cog_name}"
        # Prevent unloading core cogs
        if actual_cog_name in self.actual_core_cogs:
            embed = EmbedBuilder.error(
                title="✗ Core Cog",
                description=f"Cannot unload core cog `{cog_name}`."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Check if the cog exists based on loaded extensions
        if actual_cog_name not in self.bot.extensions:
            embed = EmbedBuilder.warning(
                title="⚠️ Cog Not Loaded",
                description=(f"`{cog_name}` not found." if actual_cog_name not in get_available_cogs(self.actual_core_cogs) 
                             else f"`{cog_name}` exists but is not loaded.")
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await self.bot.unload_extension(actual_cog_name)
            log.info(f"Cog '{actual_cog_name}' unloaded by {interaction.user}.")
            
            embed = EmbedBuilder.success(
                title="✓ Cog Unloaded",
                description=f"`{cog_name}` unloaded successfully."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except commands.ExtensionNotLoaded:
            log.warning(f"Attempted to unload not loaded cog '{actual_cog_name}' by {interaction.user}.")
            
            embed = EmbedBuilder.warning(
                title="⚠️ Not Loaded",
                description=f"`{cog_name}` is not loaded."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.exception(f"Error unloading cog '{actual_cog_name}' by {interaction.user}: {e}")
            
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Error unloading `{cog_name}`: {str(e)}"
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="reload", description="[Admin] Reloads a specified cog.")
    async def reload_cog(self, interaction: discord.Interaction, cog_name: str):
        """Reloads a cog. Provide the name without 'cogs.' prefix."""
        # Permission check
        if not await self._check_permission(interaction):
            embed = EmbedBuilder.error(
                title="🚫 Access Denied",
                description="You need administrator permissions to use this command."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        actual_cog_name = f"cogs.{cog_name}"
        
        # Check if the cog exists at all (either on disk or loaded)
        available_cogs = get_available_cogs()
        is_loaded = actual_cog_name in self.bot.extensions
        cog_exists = actual_cog_name in available_cogs or is_loaded
        
        if not cog_exists:
            embed = EmbedBuilder.error(
                title="✗ Cog Not Found",
                description=f"`{cog_name}` not found."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        if not is_loaded:
            embed = EmbedBuilder.warning(
                title="⚠️ Not Loaded",
                description=f"`{cog_name}` exists but is not currently loaded."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        try:
            await self.bot.reload_extension(actual_cog_name)
            log.info(f"Cog '{actual_cog_name}' reloaded by {interaction.user}.")
            
            embed = EmbedBuilder.success(
                title="✓ Cog Reloaded",
                description=f"`{cog_name}` reloaded successfully."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except commands.ExtensionNotLoaded:
            # Unlikely to hit this but handle just in case
            log.warning(f"Attempted to reload not loaded cog '{actual_cog_name}' by {interaction.user}.")
            
            embed = EmbedBuilder.warning(
                title="⚠️ Not Loaded",
                description=f"`{cog_name}` is not loaded."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except commands.ExtensionNotFound:
            log.error(f"Cog '{actual_cog_name}' not found during reload attempt by {interaction.user}.")
            
            embed = EmbedBuilder.error(
                title="✗ Cog Not Found",
                description=f"`{cog_name}` could not be found."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.exception(f"Error reloading cog '{actual_cog_name}' by {interaction.user}: {e}")
            
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"Error reloading `{cog_name}`: {str(e)}"
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="list", description="[Admin] Lists available and loaded cogs.")
    async def list_cogs(self, interaction: discord.Interaction):
        """Lists all available and currently loaded cogs."""
        # Permission check
        if not await self._check_permission(interaction):
            embed = EmbedBuilder.error(
                title="🚫 Access Denied",
                description="You need administrator permissions to use this command."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Get all available cogs
        all_cogs = []
        
        # Add core cogs first
        core_cogs = []
        for cog_name in self.actual_core_cogs:
            if cog_name not in core_cogs:
                core_cogs.append(cog_name)
                if cog_name not in all_cogs:
                    all_cogs.append(cog_name)
        
        # Add other available cogs
        non_core_cogs = []
        for cog_name in get_available_cogs():
            if cog_name not in core_cogs:
                non_core_cogs.append(cog_name)
                if cog_name not in all_cogs:
                    all_cogs.append(cog_name)
                    
        # Also check for any cogs that might be loaded but not in the directory
        for cog_name in self.bot.extensions.keys():
            if cog_name not in all_cogs:
                if cog_name in core_cogs:
                    core_cogs.append(cog_name)
                else:
                    non_core_cogs.append(cog_name)
                all_cogs.append(cog_name)
        
        # Get loaded cogs from the bot's extensions
        loaded_cogs = list(self.bot.extensions.keys())
        
        # Create embed
        embed = EmbedBuilder.info(
            title="📦 Cogs Status",
            description="✓ Active | ✗ Inactive"
        )
        
        # Add core cogs section
        core_section = ""
        for cog_name in sorted(core_cogs):
            display_name = cog_name.replace('cogs.', '')
            status = "✓" if cog_name in loaded_cogs else "✗"
            core_section += f"{status} **{display_name}**\n"
            
        if core_section:
            embed.add_field(
                name="⚙️ Core Modules",
                value=core_section,
                inline=False
            )
            
        # Add non-core cogs section
        non_core_section = ""
        for cog_name in sorted(non_core_cogs):
            display_name = cog_name.replace('cogs.', '')
            status = "✓" if cog_name in loaded_cogs else "✗"
            non_core_section += f"{status} **{display_name}**\n"
            
        if non_core_section:
            embed.add_field(
                name="📦 Optional Modules",
                value=non_core_section,
                inline=False
            )
        
        embed.set_footer(text="Core modules cannot be unloaded")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Simplified setup function
async def setup(bot: 'TutuBot'):
    """Sets up the CogManager cog."""
    await bot.add_cog(CogManager(bot))
    log.info("CogManager loaded.") 