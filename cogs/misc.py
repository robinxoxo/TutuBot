import discord
from discord import app_commands, ui
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

class ColorSelector(ui.View):
    """Interactive view for selecting embed color actions."""
    
    def __init__(self, cog: 'MiscCog'):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        
    @ui.button(label="View Colors", emoji="🎨", style=discord.ButtonStyle.secondary)
    async def view_colors(self, interaction: discord.Interaction, button: ui.Button):
        """Show all current colors."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.cog.show_colors(interaction)
        
    @ui.button(label="Reset Colors", emoji="🔄", style=discord.ButtonStyle.secondary)
    async def reset_colors(self, interaction: discord.Interaction, button: ui.Button):
        """Reset colors to default."""
        # Create confirmation message
        embed = EmbedBuilder.warning(
            title="⚠️ Confirm Reset",
            description="Are you sure you want to reset all embed colors to default values?"
        )
        
        # Create the view with yes/no buttons
        view = ui.View(timeout=60)
        
        async def yes_callback(yes_interaction: discord.Interaction):
            await yes_interaction.response.defer(ephemeral=True)
            try:
                # Reset colors
                save_colors(DEFAULT_COLORS)
                
                success_embed = EmbedBuilder.success(
                    title="✓ Colors Reset",
                    description="All embed colors have been reset to default values."
                )
                
                await yes_interaction.followup.send(embed=success_embed, ephemeral=True)
                
            except Exception as e:
                log.exception(f"Error resetting colors: {e}")
                error_embed = EmbedBuilder.error(
                    title="✗ Error",
                    description=f"An error occurred while resetting colors: {str(e)}"
                )
                await yes_interaction.followup.send(embed=error_embed, ephemeral=True)
        
        async def no_callback(no_interaction: discord.Interaction):
            cancel_embed = EmbedBuilder.info(
                title="Action Cancelled",
                description="Color reset cancelled."
            )
            await no_interaction.response.edit_message(embed=cancel_embed, view=None)
        
        # Add buttons with callbacks - WITHOUT emojis
        yes_button = ui.Button(label="Yes", style=discord.ButtonStyle.danger)
        yes_button.callback = yes_callback
        view.add_item(yes_button)
        
        no_button = ui.Button(label="No", style=discord.ButtonStyle.secondary)
        no_button.callback = no_callback
        view.add_item(no_button)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    @ui.button(label="Set Color", emoji="🖌️", style=discord.ButtonStyle.secondary)
    async def set_color(self, interaction: discord.Interaction, button: ui.Button):
        """Show UI for setting colors."""
        embed = EmbedBuilder.info(
            title="Select Color Type",
            description="Choose which type of color you want to modify:"
        )
        
        # Create the view with color type buttons
        view = ui.View(timeout=180)
        
        # Define color types and their attributes
        color_types = [
            {"name": "Success", "value": "success"},
            {"name": "Info", "value": "info"},
            {"name": "Error", "value": "error"},
            {"name": "Warning", "value": "warning"}
        ]
        
        # Add a button for each color type
        for color_type in color_types:
            button = ui.Button(
                label=color_type["name"], 
                style=discord.ButtonStyle.secondary
            )
            
            # Create closure for the callback
            async def make_callback(color_value):
                async def button_callback(button_interaction: discord.Interaction):
                    # Get current color
                    colors = load_colors()
                    current_hex = color_to_hex(colors.get(color_value, 0))
                    
                    # Create modal for hex input
                    modal = ui.Modal(title=f"Set {color_value.capitalize()} Color")
                    
                    # Add text input for hex color
                    hex_input = ui.TextInput(
                        label="Hex Color (e.g. #00FF00)",
                        placeholder="#00FF00",
                        default=current_hex,
                        min_length=4,
                        max_length=7,
                        required=True
                    )
                    modal.add_item(hex_input)
                    
                    # Define modal submit callback
                    async def modal_callback(modal_interaction: discord.Interaction):
                        await modal_interaction.response.defer(ephemeral=True)
                        
                        try:
                            # Get and validate hex color
                            hex_color = hex_input.value
                            hex_color = hex_color.lstrip('#')
                            
                            if not (len(hex_color) == 6 and all(c in '0123456789ABCDEFabcdef' for c in hex_color)):
                                raise ValueError("Invalid hex color format")
                            
                            # Convert hex to color value
                            color_value_int = hex_to_color(hex_color)
                            
                            # Update color
                            current_colors = load_colors()
                            current_colors[color_value] = color_value_int
                            save_colors(current_colors)
                            
                            # Show success with preview
                            success_embed = discord.Embed(
                                title="✓ Color Updated",
                                description=f"The {color_value} color has been updated to `#{hex_color}`.",
                                color=discord.Color(color_value_int)
                            )
                            
                            await modal_interaction.followup.send(embed=success_embed, ephemeral=True)
                            
                        except ValueError:
                            error_embed = EmbedBuilder.error(
                                title="✗ Invalid Color",
                                description="Please provide a valid hex color (e.g. `#00FF00`)."
                            )
                            await modal_interaction.followup.send(embed=error_embed, ephemeral=True)
                        except Exception as e:
                            log.exception(f"Error updating color: {e}")
                            error_embed = EmbedBuilder.error(
                                title="✗ Error",
                                description=f"An error occurred: {str(e)}"
                            )
                            await modal_interaction.followup.send(embed=error_embed, ephemeral=True)
                    
                    # Set callback and send modal
                    modal.on_submit = modal_callback
                    await button_interaction.response.send_modal(modal)
                
                return button_callback
            
            # Set the button callback
            button.callback = await make_callback(color_type["value"])
            view.add_item(button)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class MiscCog(commands.Cog, name="Misc"):
    """Miscellaneous utility commands."""

    def __init__(self, bot: 'TutuBot'):
        """Initialize the Misc cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        
    async def show_colors(self, interaction: discord.Interaction):
        """Display current embed colors."""
        try:
            # Load current colors
            current_colors = load_colors()
            
            # Create embeds for each color to show actual color preview
            embeds = []
            
            # Main info embed
            main_embed = EmbedBuilder.info(
                title="🎨 Embed Colors",
                description="Current embed colors used by the bot:"
            )
            embeds.append(main_embed)
            
            # Create an embed for each color to show actual preview
            for name, value in current_colors.items():
                hex_value = color_to_hex(value)
                color_embed = discord.Embed(
                    title=f"{name.capitalize()}",
                    description=f"Hex: `{hex_value}`",
                    color=discord.Color(value)
                )
                embeds.append(color_embed)
                
            await interaction.followup.send(embeds=embeds, ephemeral=True)
        except Exception as e:
            log.exception(f"Error showing colors: {e}")
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"An error occurred: {str(e)}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="embedcolors", description="[Admin] Manage the colors used in bot embeds")
    async def manage_colors(self, interaction: discord.Interaction):
        """Interactive UI for managing embed colors.
        
        Args:
            interaction: The interaction object
        """
        # Permission check
        if not await admin_check_with_response(interaction):
            return
            
        # Create embed for initial message
        embed = EmbedBuilder.info(
            title="🎨 Embed Color Management",
            description="Select an action to manage the colors used in bot embeds."
        )
        
        # Create view with buttons
        view = ColorSelector(self)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: 'TutuBot'):
    """Sets up the MiscCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(MiscCog(bot))
    log.info("MiscCog loaded.") 