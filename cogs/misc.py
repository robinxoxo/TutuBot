import discord
from discord import app_commands
from discord.ext import commands
import logging
import typing
from typing import Optional, List, Dict, Any

from utils.permission_checks import admin_check_with_response
from utils.embed_colors import load_colors, save_colors, hex_to_color, color_to_hex, DEFAULT_COLORS
from utils.embed_builder import EmbedBuilder

# For type hinting only
if typing.TYPE_CHECKING:
    from main import TutuBot

# Configure logging
log = logging.getLogger(__name__)

class MiscCog(commands.Cog, name="Misc"):
    """Miscellaneous utility commands."""

    def __init__(self, bot: 'TutuBot'):
        """Initialize the Misc cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @app_commands.command(name="embedcolors", description="[Admin] Manage the colors used in bot embeds")
    @app_commands.describe(
        action="Action to perform (view, reset, set)",
        color_type="Type of message (success, info, error, warning)",
        hex_color="Hex color code (e.g. #00FF00 for green)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="View all colors", value="view"),
            app_commands.Choice(name="Reset all colors to default", value="reset"),
            app_commands.Choice(name="Set a specific color", value="set")
        ],
        color_type=[
            app_commands.Choice(name="Success", value="success"),
            app_commands.Choice(name="Info", value="info"),
            app_commands.Choice(name="Error", value="error"),
            app_commands.Choice(name="Warning", value="warning")
        ]
    )
    async def manage_colors(self, interaction: discord.Interaction, action: str, color_type: Optional[str] = None, hex_color: Optional[str] = None):
        """Manage the colors used in bot embed messages.
        
        Args:
            interaction: The interaction object
            action: The action to perform (view, reset, set)
            color_type: Type of message (success, info, error, warning)
            hex_color: Hex color code (e.g. #00FF00 for green)
        """
        # Permission check
        if not await admin_check_with_response(interaction):
            return
            
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Load current colors
            current_colors = load_colors()
            
            if action == "view":
                # Display current colors
                embed = EmbedBuilder.info(
                    title="🎨 Embed Colors",
                    description="Current embed colors used by the bot"
                )
                
                for name, value in current_colors.items():
                    hex_value = color_to_hex(value)
                    embed.add_field(
                        name=f"{name.capitalize()}",
                        value=f"Hex: `{hex_value}`\nPreview: ■■■■■",
                        inline=True
                    )
                    
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            elif action == "reset":
                # Reset to defaults
                save_colors(DEFAULT_COLORS)
                
                embed = EmbedBuilder.success(
                    title="✓ Colors Reset",
                    description="All embed colors have been reset to default values."
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            elif action == "set":
                # Check if required parameters are provided
                if not color_type or not hex_color:
                    embed = EmbedBuilder.error(
                        title="✗ Missing Parameters",
                        description="Please provide both a color type and hex color."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Validate hex color
                try:
                    # Remove '#' if present and validate format
                    hex_color = hex_color.lstrip('#')
                    if not (len(hex_color) == 6 and all(c in '0123456789ABCDEFabcdef' for c in hex_color)):
                        raise ValueError("Invalid hex color format")
                        
                    # Convert hex to color value
                    color_value = hex_to_color(hex_color)
                    
                    # Update the color
                    current_colors[color_type] = color_value
                    save_colors(current_colors)
                    
                    # Create embed with the new color
                    embed = EmbedBuilder.success(
                        title="✓ Color Updated",
                        description=f"The {color_type} color has been updated to `#{hex_color}`."
                    )
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
                except ValueError:
                    embed = EmbedBuilder.error(
                        title="✗ Invalid Color",
                        description="Please provide a valid hex color (e.g. `#00FF00`)."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
        except Exception as e:
            log.exception(f"Error managing colors: {e}")
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"An error occurred: {str(e)}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: 'TutuBot'):
    """Sets up the MiscCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(MiscCog(bot))
    log.info("MiscCog loaded.") 