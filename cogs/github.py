import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
import logging
import typing
from typing import Dict, Optional, TYPE_CHECKING
import os
import json
from datetime import datetime
import aiohttp

from utils.permission_checks import is_owner_or_administrator
from utils.embed_builder import EmbedBuilder

# For type hinting only
if TYPE_CHECKING:
    from main import TutuBot
else:
    # Import at runtime to prevent circular imports
    from utils.interaction_utils import send_ephemeral_message

# Configure logging
log = logging.getLogger(__name__)

class GitHubView(discord.ui.View):
    def __init__(self, cog, timeout=180):
        super().__init__(timeout=timeout)
        self.cog = cog
        
    @discord.ui.button(label="Set as Update Channel", style=discord.ButtonStyle.secondary)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Set the current channel as the update channel
        await self.cog.set_update_channel(interaction.channel.id)
        
        embed = EmbedBuilder.success(
            title="✓ Channel Set",
            description="This channel has been set as the GitHub update channel!"
        )
        await send_ephemeral_message(interaction, embed=embed)

class GitHubCog(commands.Cog, name="GitHub"):
    """GitHub integration for bot updates and changelog."""

    def __init__(self, bot: 'TutuBot'):
        """Initialize the GitHub cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        
        # Settings file
        self.settings_file = "data/github_settings.json"
        self.settings = self.load_settings()
        
        # Track the latest commit
        self.latest_commit_sha = self.settings.get("latest_commit_sha", "")
        
        # Check for GitHub token
        self.github_token = os.getenv("GITHUB_TOKEN")
        if not self.github_token:
            log.warning("No GITHUB_TOKEN found in environment variables. GitHub API rate limits will be strict.")
        
        # Start the background task once the bot is ready
        self.check_github_updates.start()
        
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.check_github_updates.cancel()
        
    def load_settings(self) -> Dict:
        """Load settings from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            else:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
                # Return empty settings
                return {"update_channel": None, "latest_commit_sha": ""}
        except Exception as e:
            log.error(f"Error loading GitHub settings: {e}")
            return {"update_channel": None, "latest_commit_sha": ""}
            
    def save_settings(self, settings=None) -> None:
        """Save settings to file."""
        if settings is None:
            settings = self.settings
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            log.error(f"Error saving GitHub settings: {e}")
            
    def get_guild_settings(self, guild_id: str) -> Dict:
        """Get settings for a specific guild."""
        return self.settings.get(guild_id, {})
        
    def update_settings(self, guild_id: str, update_data: Dict) -> None:
        """Update settings for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
            
        self.settings[guild_id].update(update_data)
        self.save_settings()
        
    async def set_update_channel(self, channel_id):
        """Set the channel for GitHub updates"""
        self.settings["update_channel"] = channel_id
        self.save_settings()
        
    async def fetch_github_commits(self, repo="robinxoxo/TutuBot", limit=5):
        """Fetch recent commits from GitHub"""
        url = f"https://api.github.com/repos/{repo}/commits"
        
        # Add GitHub API token from environment if available
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data[:limit]
                else:
                    error_data = await response.text()
                    log.error(f"Failed to fetch GitHub commits: {response.status} - {error_data}")
                    return None
    
    async def send_commit_update(self, commit):
        """Send a commit update to the designated channel."""
        channel_id = self.settings.get("update_channel")
        if not channel_id:
            log.warning("No update channel set for GitHub updates")
            return
            
        channel = self.bot.get_channel(channel_id)
        if not channel:
            log.warning(f"Could not find channel with ID {channel_id}")
            return
            
        # Create embed for the commit
        commit_hash = commit["sha"][:7]
        commit_message_full = commit["commit"]["message"]
        commit_lines = commit_message_full.split("\n")
        
        # Split title and description
        commit_title = commit_lines[0].strip()
        commit_description = "\n".join(commit_lines[1:]).strip() if len(commit_lines) > 1 else ""
        
        author = commit["commit"]["author"]["name"]
        date = datetime.fromisoformat(commit["commit"]["author"]["date"].replace("Z", "+00:00"))
        timestamp = int(date.timestamp())
        
        embed = EmbedBuilder.info(
            title="<:bot:1360373720954441939> TutuBot Update",
            description=f"• Updates have been pushed to the bot."
        )
        
        embed.add_field(
            name="Commit:",
            value=f"`{commit_hash}` by **{author}** <t:{timestamp}:R>",
            inline=False
        )
        
        embed.add_field(
            name="Title:",
            value=commit_title,
            inline=False
        )
        
        # Only add description if it's not empty
        if commit_description:
            embed.add_field(
                name="Description:",
                value=commit_description,
                inline=False
            )
        
        # Add link to the commit
        commit_url = commit["html_url"]
        embed.add_field(
            name="See Changes:",
            value=f"[via GitHub]({commit_url})",
            inline=False
        )
        
        await channel.send(embed=embed)
        
    @tasks.loop(minutes=2)
    async def check_github_updates(self):
        """Check for GitHub updates periodically."""
        try:
            # Check if update channel is configured
            if not self.settings.get("update_channel"):
                return
                
            commits = await self.fetch_github_commits(limit=5)
            if not commits:
                log.warning("No commits retrieved or API error occurred")
                return
                
            newest_commit = commits[0]
            newest_sha = newest_commit["sha"]
            
            # If this is our first run and we have no saved SHA, just save it without notifications
            if not self.latest_commit_sha:
                self.latest_commit_sha = newest_sha
                self.settings["latest_commit_sha"] = newest_sha
                self.save_settings()
                log.info(f"Initialized with latest commit: {newest_sha[:7]}")
                return
                
            # If we have a new commit and we've seen at least one commit before
            if newest_sha != self.latest_commit_sha:
                log.info(f"New commits found. Latest: {newest_sha[:7]}, Previous: {self.latest_commit_sha[:7]}")
                
                # Find all new commits (those that come before our last known commit)
                new_commits = []
                for commit in commits:
                    if commit["sha"] == self.latest_commit_sha:
                        break
                    new_commits.append(commit)
                
                # Send updates for new commits (most recent last)
                for commit in reversed(new_commits):
                    try:
                        await self.send_commit_update(commit)
                        log.info(f"Sent update for commit: {commit['sha'][:7]}")
                    except Exception as e:
                        log.error(f"Error sending commit update: {e}")
                    
                # Update the latest commit SHA
                self.latest_commit_sha = newest_sha
                self.settings["latest_commit_sha"] = newest_sha
                self.save_settings()
            
        except Exception as e:
            log.error(f"Error checking GitHub updates: {e}")
    
    @check_github_updates.before_loop
    async def before_check_github_updates(self):
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()
        
        # Log GitHub integration status
        log.info("Starting GitHub integration...")
        
        if not self.github_token:
            log.warning("GitHub API token not found. Add GITHUB_TOKEN to your environment variables for better API access.")
        
        update_channel_id = self.settings.get("update_channel")
        if update_channel_id:
            channel = self.bot.get_channel(update_channel_id)
            if channel:
                log.info(f"GitHub updates will be sent to channel: #{channel.name} ({update_channel_id})")
            else:
                log.warning(f"Configured update channel {update_channel_id} not found")
        else:
            log.info("No GitHub update channel configured. Use the /github command to set one.")
        
        # Fetch the latest commit SHA on startup if we don't have one
        if not self.latest_commit_sha:
            log.info("Fetching initial commit data...")
            commits = await self.fetch_github_commits(limit=1)
            if commits:
                self.latest_commit_sha = commits[0]["sha"]
                self.settings["latest_commit_sha"] = self.latest_commit_sha
                self.save_settings()
                log.info(f"Initial commit SHA set to: {self.latest_commit_sha[:7]}")
            else:
                log.warning("Failed to fetch initial commit data")
    
    @app_commands.command(name="github", description="[Admin] Manage GitHub integration settings")
    @is_owner_or_administrator()
    async def github_settings(self, interaction: discord.Interaction):
        """Manage GitHub integration settings."""
        # Create info embed
        embed = EmbedBuilder.info(
            title="<:github:1361388522517950555> GitHub Integration",
            description="• Use this command to manage GitHub integration settings."
        )
        
        # Add current settings
        update_channel_id = self.settings.get("update_channel")
        update_channel = None
        
        if update_channel_id:
            update_channel = self.bot.get_channel(update_channel_id)
            
        if update_channel:
            embed.add_field(
                name="Current Update Channel:",
                value=f"{update_channel.mention} (`{update_channel.id}`)",
                inline=False
            )
        else:
            embed.add_field(
                name="Current Update Channel:",
                value="No channel set",
                inline=False
            )
        
        # Create view
        view = GitHubView(self)
        
        # Send the message
        await send_ephemeral_message(interaction, embed=embed, view=view)

    @github_settings.error
    async def github_settings_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors for the github_settings command."""
        if isinstance(error, app_commands.errors.CheckFailure):
            embed = EmbedBuilder.error(
                title="✗ Access Denied",
                description="You need administrator permissions to use this command."
            )
            await send_ephemeral_message(interaction, embed=embed)
        else:
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"An error occurred: {str(error)}"
            )
            await send_ephemeral_message(interaction, embed=embed)
            log.error(f"Error in github_settings command: {error}")

async def setup(bot: 'TutuBot'):
    """Sets up the GitHubCog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(GitHubCog(bot))
    log.info("GitHubCog loaded.") 