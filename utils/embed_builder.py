import discord
from typing import Optional, Any, List, Union
from utils.embed_colors import get_color

class EmbedBuilder:
    """Utility class for building Discord embeds with consistent colors."""
    
    @staticmethod
    def success(title: str, description: Optional[str] = None, guild_id: Optional[str] = None, **kwargs) -> discord.Embed:
        """Create a success embed with green color.
        
        Args:
            title: The embed title
            description: The embed description
            guild_id: The guild ID for guild-specific colors
            **kwargs: Additional embed parameters
            
        Returns:
            discord.Embed: The created embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_color("success", guild_id),
            **kwargs
        )
        return embed
    
    @staticmethod
    def info(title: str, description: Optional[str] = None, guild_id: Optional[str] = None, **kwargs) -> discord.Embed:
        """Create an info embed with blurple color.
        
        Args:
            title: The embed title
            description: The embed description
            guild_id: The guild ID for guild-specific colors
            **kwargs: Additional embed parameters
            
        Returns:
            discord.Embed: The created embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_color("info", guild_id),
            **kwargs
        )
        return embed
    
    @staticmethod
    def error(title: str, description: Optional[str] = None, guild_id: Optional[str] = None, **kwargs) -> discord.Embed:
        """Create an error embed with red color.
        
        Args:
            title: The embed title
            description: The embed description
            guild_id: The guild ID for guild-specific colors
            **kwargs: Additional embed parameters
            
        Returns:
            discord.Embed: The created embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_color("error", guild_id),
            **kwargs
        )
        return embed
    
    @staticmethod
    def warning(title: str, description: Optional[str] = None, guild_id: Optional[str] = None, **kwargs) -> discord.Embed:
        """Create a warning embed with gold color.
        
        Args:
            title: The embed title
            description: The embed description
            guild_id: The guild ID for guild-specific colors
            **kwargs: Additional embed parameters
            
        Returns:
            discord.Embed: The created embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_color("warning", guild_id),
            **kwargs
        )
        return embed
    
    @staticmethod
    def custom(title: str, description: Optional[str] = None, color: Optional[discord.Color] = None, guild_id: Optional[str] = None, **kwargs) -> discord.Embed:
        """Create an embed with a custom color.
        
        Args:
            title: The embed title
            description: The embed description
            color: A custom color override
            guild_id: The guild ID for guild-specific colors
            **kwargs: Additional embed parameters
            
        Returns:
            discord.Embed: The created embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or get_color("info", guild_id),  # Default to info color if none provided
            **kwargs
        )
        return embed 