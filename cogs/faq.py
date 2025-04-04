import discord
from discord import app_commands
from discord.ext import commands
import logging
import typing

# For type hinting only
if typing.TYPE_CHECKING:
    from main import TutuBot

# Configure logging
log = logging.getLogger(__name__)

class FaqCog(commands.Cog, name="FAQ"):
    """Handles informational commands like help."""

    def __init__(self, bot: 'TutuBot'):
        """Initialize the FAQ cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    # --- Help Command ---
    @app_commands.command(name="help", description="Shows information about available commands.")
    async def help_command(self, interaction: discord.Interaction):
        """Displays a list of available commands and their descriptions.
        
        Args:
            interaction: The Discord interaction
        """
        embed = discord.Embed(
            title="Command Help",
            description="Here are the available commands:",
            color=discord.Color.blurple()
        )

        command_list = self.bot.tree.get_commands()

        if not command_list:
            embed.description = "No commands seem to be registered currently."
        else:
            for command in sorted(command_list, key=lambda c: c.name):
                description = getattr(command, 'description', "No description available.")
                if not description:
                    description = "No description provided."
                embed.add_field(
                    name=f"`/{command.name}`",
                    value=description,
                    inline=False
                )

        embed.set_footer(text="Use the slash (/) to invoke commands. | Bot created by <@robinxoxo>")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: 'TutuBot'):
    """Sets up the FaqCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(FaqCog(bot))
    log.info("FaqCog loaded.") 