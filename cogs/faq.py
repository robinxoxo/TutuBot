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
            title="📚 Command Help",
            description="Here are the available commands:",
            color=discord.Color.blurple()
        )

        command_list = self.bot.tree.get_commands()
        
        # Filter out the help command itself
        command_list = [cmd for cmd in command_list if cmd.name != "help"]

        if not command_list:
            embed.description = "No commands seem to be registered currently."
        else:
            # Group commands into admin and regular categories
            admin_commands = []
            regular_commands = []
            
            for command in sorted(command_list, key=lambda c: c.name):
                description = getattr(command, 'description', "No description available.")
                if not description:
                    description = "No description provided."
                
                if "[Admin]" in description:
                    admin_commands.append((command, description))
                else:
                    regular_commands.append((command, description))
            
            # Add regular commands
            if regular_commands:
                embed.add_field(name="👥 Regular Commands", value="Commands available to all users:", inline=False)
                for command, description in regular_commands:
                    embed.add_field(
                        name=f"`/{command.name}`",
                        value=description,
                        inline=False
                    )
            
            # Add admin commands only if user has admin permissions
            is_admin = False
            if interaction.guild:
                # Get member permissions
                permissions = interaction.permissions
                is_admin = permissions.administrator if hasattr(permissions, 'administrator') else False
                
            if admin_commands and is_admin:
                embed.add_field(name="🛡️ Admin Commands", value="Commands restricted to administrators:", inline=False)
                for command, description in admin_commands:
                    embed.add_field(
                        name=f"`/{command.name}`",
                        value=description,
                        inline=False
                    )

        embed.set_footer(text=f"Use the slash (/) to invoke commands. | Bot created by <@254017258929791006>")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: 'TutuBot'):
    """Sets up the FaqCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(FaqCog(bot))
    log.info("FaqCog loaded.") 