import discord
from typing import Optional, Any, List
from utils.embed_colors import get_color

class EmbedBuilder:
    """Utility class for building Discord embeds with consistent colors."""
    
    @staticmethod
    def success(title: str, description: Optional[str] = None, **kwargs) -> discord.Embed:
        """Create a success embed with green color."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_color("success"),
            **kwargs
        )
        return embed
    
    @staticmethod
    def info(title: str, description: Optional[str] = None, **kwargs) -> discord.Embed:
        """Create an info embed with blurple color."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_color("info"),
            **kwargs
        )
        return embed
    
    @staticmethod
    def error(title: str, description: Optional[str] = None, **kwargs) -> discord.Embed:
        """Create an error embed with red color."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_color("error"),
            **kwargs
        )
        return embed
    
    @staticmethod
    def warning(title: str, description: Optional[str] = None, **kwargs) -> discord.Embed:
        """Create a warning embed with gold color."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_color("warning"),
            **kwargs
        )
        return embed
    
    @staticmethod
    def custom(title: str, description: Optional[str] = None, color: Optional[discord.Color] = None, **kwargs) -> discord.Embed:
        """Create an embed with a custom color."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or get_color("info"),  # Default to info color if none provided
            **kwargs
        )
        return embed 