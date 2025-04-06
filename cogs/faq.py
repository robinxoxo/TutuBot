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

        # Get all commands from the bot's command tree
        command_list = []
        for cmd in self.bot.tree.get_commands():
            command_list.append(cmd)
            
        # Sort commands alphabetically
        command_list.sort(key=lambda x: x.name)
        
        # Filter out the help command itself
        command_list = [cmd for cmd in command_list if cmd.name != "help"]

        if not command_list:
            embed.description = "No commands seem to be registered currently."
        else:
            # Group commands into admin and regular categories
            admin_commands = []
            regular_commands = []
            
            for command in command_list:
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
            
            # Add admin commands only if user has admin permissions or is bot owner
            is_admin = False
            is_owner = False
            
            # Check if user is bot owner
            if hasattr(self.bot, 'owner_id') and interaction.user.id == self.bot.owner_id:
                is_owner = True
                is_admin = True  # Owner is treated as admin
            # Check admin permissions
            elif interaction.guild and isinstance(interaction.user, discord.Member):
                is_admin = interaction.user.guild_permissions.administrator
                
            if admin_commands and (is_admin or is_owner):
                # Special title for bot owner if that's why they can see these commands
                title = "🛡️ Admin Commands"
                if is_owner and not is_admin:
                    title = "🛡️ Admin Commands (visible as bot owner)"
                    
                embed.add_field(name=title, value="Commands restricted to administrators:", inline=False)
                for command, description in admin_commands:
                    embed.add_field(
                        name=f"`/{command.name}`",
                        value=description,
                        inline=False
                    )

        embed.set_footer(text="Use the slash (/) to invoke commands")
        
        # Add creator info as a field instead of in footer
        embed.add_field(
            name="🤖 Bot Creator",
            value="<@148682563861479425>",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: 'TutuBot'):
    """Sets up the FaqCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(FaqCog(bot))
    log.info("FaqCog loaded.") 