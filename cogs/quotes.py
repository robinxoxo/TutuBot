import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
import typing
import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

# For type hinting only
if typing.TYPE_CHECKING:
    from main import TutuBot

# Configure logging
log = logging.getLogger(__name__)

# Quotes data file
QUOTES_FILE = "data/quotes.json"

class AddQuoteModal(ui.Modal, title="Add New Quote"):
    """Modal for adding a new quote."""
    
    quote_text = ui.TextInput(
        label="Quote",
        placeholder="Enter the quote text here",
        min_length=1,
        max_length=1000,
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    quote_author = ui.TextInput(
        label="Author",
        placeholder="Who said this? (optional)",
        required=False,
        max_length=100
    )
    
    quote_context = ui.TextInput(
        label="Context",
        placeholder="Add context for this quote (optional)",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, cog: 'QuoteCog'):
        super().__init__(timeout=300)
        self.cog = cog
        
    async def on_submit(self, interaction: discord.Interaction):
        """Process the quote submission."""
        try:
            # Extract values from form
            quote_text = self.quote_text.value
            quote_author = self.quote_author.value or "Anonymous"
            quote_context = self.quote_context.value or ""
            
            # Ensure we have a guild ID
            if not interaction.guild_id:
                await interaction.response.send_message(
                    "Quotes can only be added in servers.", 
                    ephemeral=True
                )
                return
                
            # Add the quote
            result_embed = await self.cog.add_quote(
                interaction=interaction,
                text=quote_text,
                author=quote_author,
                context=quote_context,
                added_by=interaction.user
            )
            
            await interaction.response.send_message(embed=result_embed, ephemeral=True)
            
        except Exception as e:
            log.exception(f"Error in quote modal: {e}")
            error_embed = discord.Embed(
                title="✗ Error",
                description="An error occurred while processing your quote. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

class QuoteView(ui.View):
    """View for navigating quotes."""
    
    def __init__(self, cog: 'QuoteCog', guild_id: str, current_index: int = 0):
        super().__init__(timeout=180)
        self.cog = cog
        self.guild_id = guild_id
        self.current_index = current_index
        self.total_quotes = len(self.cog.get_guild_quotes(guild_id))

        # Disable buttons if needed
        self.update_button_states()
        
    def update_button_states(self):
        """Update the enabled/disabled state of navigation buttons."""
        self.previous_button.disabled = self.current_index <= 0
        self.next_button.disabled = self.current_index >= self.total_quotes - 1
        self.random_button.disabled = self.total_quotes <= 1
    
    @ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
        """Go to the previous quote."""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_button_states()
            
            embed = self.cog.create_quote_embed(
                self.guild_id, 
                self.current_index, 
                self.total_quotes
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @ui.button(label="Random", style=discord.ButtonStyle.secondary, emoji="🔀")
    async def random_button(self, interaction: discord.Interaction, button: ui.Button):
        """Show a random quote."""
        # Get a random index different from current
        if self.total_quotes > 1:
            available_indices = list(range(self.total_quotes))
            available_indices.remove(self.current_index)
            self.current_index = random.choice(available_indices)
        else:
            self.current_index = 0
            
        self.update_button_states()
        
        embed = self.cog.create_quote_embed(
            self.guild_id, 
            self.current_index, 
            self.total_quotes
        )
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        """Go to the next quote."""
        if self.current_index < self.total_quotes - 1:
            self.current_index += 1
            self.update_button_states()
            
            embed = self.cog.create_quote_embed(
                self.guild_id, 
                self.current_index, 
                self.total_quotes
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @ui.button(label="Add Quote", style=discord.ButtonStyle.secondary, emoji="➕", row=1)
    async def add_button(self, interaction: discord.Interaction, button: ui.Button):
        """Open the modal to add a new quote."""
        await interaction.response.send_modal(AddQuoteModal(self.cog))
            
    async def on_timeout(self):
        """Disable buttons when view times out."""
        for child in self.children:
            if isinstance(child, ui.Button):
                child.disabled = True

class QuoteCog(commands.Cog, name="Quotes"):
    """Manages and displays community quotes."""

    def __init__(self, bot: 'TutuBot'):
        """Initialize the Quote cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.quotes = {}  # Format: {guild_id: [{"text": str, "author": str, "context": str, "added_by": user_id, "timestamp": str}]}
        
        # Create the data directory if it doesn't exist
        os.makedirs(os.path.dirname(QUOTES_FILE), exist_ok=True)
        
        # Load existing quotes
        self.load_quotes()
        
    def load_quotes(self):
        """Load quotes from the JSON file."""
        try:
            if os.path.exists(QUOTES_FILE):
                with open(QUOTES_FILE, 'r') as f:
                    self.quotes = json.load(f)
            else:
                # If file doesn't exist, initialize with empty dict
                self.quotes = {}
                # Create the file
                self.save_quotes()
        except Exception as e:
            log.error(f"Error loading quotes: {e}")
            self.quotes = {}
    
    def save_quotes(self):
        """Save quotes to the JSON file."""
        try:
            with open(QUOTES_FILE, 'w') as f:
                json.dump(self.quotes, f, indent=4)
        except Exception as e:
            log.error(f"Error saving quotes: {e}")
    
    def get_guild_quotes(self, guild_id: str) -> List[Dict[str, Any]]:
        """Get all quotes for a specific guild.
        
        Args:
            guild_id: The guild ID as a string
            
        Returns:
            A list of quote dictionaries
        """
        return self.quotes.get(guild_id, [])
    
    def create_quote_embed(self, guild_id: str, index: int, total: int) -> discord.Embed:
        """Create an embed for a quote.
        
        Args:
            guild_id: The guild ID as a string
            index: The index of the quote to display
            total: The total number of quotes
            
        Returns:
            A formatted Discord embed
        """
        guild_quotes = self.get_guild_quotes(guild_id)
        
        if not guild_quotes or index >= len(guild_quotes):
            # No quotes or invalid index
            embed = discord.Embed(
                title="📜 Quotes",
                description="No quotes found in this server.",
                color=discord.Color.blue()
            )
            return embed
        
        # Get the quote at the specified index
        quote = guild_quotes[index]
        
        # Create the embed
        embed = discord.Embed(
            title=f"📜 Quote #{index + 1}",
            description=f"\"{quote['text']}\"",
            color=discord.Color.gold()
        )
        
        # Add author and context
        embed.add_field(
            name="Author",
            value=quote['author'],
            inline=True
        )
        
        if quote.get('context'):
            embed.add_field(
                name="Context",
                value=quote['context'],
                inline=True
            )
        
        # Add metadata
        added_by_id = quote.get('added_by')
        timestamp = quote.get('timestamp', 'Unknown date')
        
        footer_text = f"Quote {index + 1} of {total}"
        
        if added_by_id:
            footer_text += f" • Added by user ID: {added_by_id}"
        
        embed.set_footer(text=footer_text)
        embed.timestamp = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else discord.utils.utcnow()
        
        return embed
        
    async def add_quote(self, interaction: discord.Interaction, text: str, author: str,
                        context: str, added_by: Union[discord.User, discord.Member]) -> discord.Embed:
        """Add a new quote to the database.
        
        Args:
            interaction: The Discord interaction
            text: The quote text
            author: Who said the quote
            context: Optional context for the quote
            added_by: The user who added the quote
            
        Returns:
            An embed with the result of the operation
        """
        # Ensure we have a guild ID
        if not interaction.guild_id:
            embed = discord.Embed(
                title="✗ Error",
                description="Quotes can only be added in servers.",
                color=discord.Color.red()
            )
            return embed
        
        guild_id = str(interaction.guild_id)
        
        # Initialize guild quotes if needed
        if guild_id not in self.quotes:
            self.quotes[guild_id] = []
        
        # Create the quote object
        quote = {
            "text": text,
            "author": author,
            "context": context,
            "added_by": str(added_by.id),
            "timestamp": discord.utils.utcnow().isoformat()
        }
        
        # Add to the list
        self.quotes[guild_id].append(quote)
        
        # Save to file
        self.save_quotes()
        
        # Get the index of the new quote
        new_index = len(self.quotes[guild_id]) - 1
        total_quotes = len(self.quotes[guild_id])
        
        # Create success embed
        embed = discord.Embed(
            title="✓ Quote Added",
            description=f"Successfully added quote #{new_index + 1}:",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Quote",
            value=f"\"{text}\"",
            inline=False
        )
        
        embed.add_field(
            name="Author",
            value=author,
            inline=True
        )
        
        if context:
            embed.add_field(
                name="Context",
                value=context,
                inline=True
            )
        
        embed.set_footer(text=f"Quote {new_index + 1} of {total_quotes}")
        
        return embed
    
    @app_commands.command(name="quote", description="Display and manage quotes")
    @app_commands.describe(action="Action to perform with quotes")
    @app_commands.choices(action=[
        app_commands.Choice(name="Show random quote", value="random"),
        app_commands.Choice(name="Browse quotes", value="browse"),
        app_commands.Choice(name="Add quote", value="add")
    ])
    async def quote_command(self, interaction: discord.Interaction, action: str = "random"):
        """Main command for interacting with quotes.
        
        Args:
            interaction: The Discord interaction
            action: The action to perform (random, browse, add)
        """
        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command can only be used in servers.", 
                ephemeral=True
            )
            return
        
        guild_id = str(interaction.guild_id)
        
        if action == "add":
            # Open modal to add a quote
            await interaction.response.send_modal(AddQuoteModal(self))
            return
        
        # Get quotes for this guild
        guild_quotes = self.get_guild_quotes(guild_id)
        
        if not guild_quotes:
            # No quotes found
            embed = discord.Embed(
                title="📜 Quotes",
                description="No quotes have been added to this server yet.",
                color=discord.Color.blue()
            )
            
            # Add a button to add quotes
            view = discord.ui.View(timeout=180)
            add_button = discord.ui.Button(
                label="Add Quote", 
                style=discord.ButtonStyle.secondary,
                emoji="➕"
            )
            
            async def add_quote_callback(button_interaction: discord.Interaction):
                await button_interaction.response.send_modal(AddQuoteModal(self))
            
            add_button.callback = add_quote_callback
            view.add_item(add_button)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
            return
        
        # Determine which quote to show
        if action == "random":
            index = random.randint(0, len(guild_quotes) - 1)
        else:  # browse
            index = 0
        
        total_quotes = len(guild_quotes)
        
        # Create and send the quote embed
        embed = self.create_quote_embed(guild_id, index, total_quotes)
        view = QuoteView(self, guild_id, index)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
    
    @app_commands.command(name="quotesearch", description="Search through quotes")
    @app_commands.describe(search_term="Enter a term to search for in quotes")
    async def quote_search_command(self, interaction: discord.Interaction, search_term: str):
        """Search through quotes in the server.
        
        Args:
            interaction: The Discord interaction
            search_term: The term to search for
        """
        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command can only be used in servers.", 
                ephemeral=True
            )
            return
        
        guild_id = str(interaction.guild_id)
        guild_quotes = self.get_guild_quotes(guild_id)
        
        if not guild_quotes:
            await interaction.response.send_message(
                "No quotes have been added to this server yet.",
                ephemeral=True
            )
            return
        
        # Search through quotes
        search_term = search_term.lower()
        matching_indices = []
        
        for i, quote in enumerate(guild_quotes):
            # Search in text, author, and context
            if (search_term in quote["text"].lower() or
                search_term in quote["author"].lower() or
                search_term in quote.get("context", "").lower()):
                matching_indices.append(i)
        
        if not matching_indices:
            # No matches found
            await interaction.response.send_message(
                f"No quotes found matching '{search_term}'.",
                ephemeral=True
            )
            return
        
        # Pick a random match to display
        index = random.choice(matching_indices)
        total_matches = len(matching_indices)
        
        # Create embed
        embed = self.create_quote_embed(guild_id, index, len(guild_quotes))
        
        # Add search result info
        embed.title = f"🔍 Quote Search Result"
        embed.set_footer(text=f"Found {total_matches} matching quotes • Quote {index + 1} of {len(guild_quotes)}")
        
        # Create a view
        view = QuoteView(self, guild_id, index)
        
        await interaction.response.send_message(
            content=f"Found {total_matches} quotes matching '{search_term}':",
            embed=embed, 
            view=view,
            ephemeral=False
        )

async def setup(bot: 'TutuBot'):
    """Sets up the QuoteCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(QuoteCog(bot))
    log.info("QuoteCog loaded.") 