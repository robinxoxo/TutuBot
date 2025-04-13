import discord
import json
import os
import logging
from typing import Dict, Any, Optional

# Configure logging
log = logging.getLogger(__name__)

# Default embed colors
DEFAULT_COLORS = {
    "success": discord.Color.green().value,
    "info": discord.Color.blurple().value,
    "error": discord.Color.red().value,
    "warning": discord.Color.gold().value
}

# File to store custom colors
COLORS_DIR = "data/embed_colors"

# Ensure directories exist
os.makedirs(COLORS_DIR, exist_ok=True)

def get_colors_file(guild_id: Optional[str] = None) -> str:
    """Get the appropriate colors file path based on guild ID.
    
    Args:
        guild_id: The guild ID or None for global settings
        
    Returns:
        str: The path to the colors file
    """
    if guild_id:
        return os.path.join(COLORS_DIR, f"{guild_id}.json")
    else:
        return os.path.join(COLORS_DIR, "global.json")

def load_colors(guild_id: Optional[str] = None) -> Dict[str, int]:
    """Load custom colors from file or return defaults if file doesn't exist.
    
    Args:
        guild_id: The guild ID to load colors for, or None for global settings
        
    Returns:
        Dict[str, int]: The color settings
    """
    colors_file = get_colors_file(guild_id)
    
    try:
        if os.path.exists(colors_file):
            try:
                with open(colors_file, 'r') as f:
                    data = f.read().strip()
                    # Check if file is empty or has invalid content
                    if not data:
                        log.warning(f"Colors file for guild {guild_id} exists but is empty, using defaults")
                        save_colors(DEFAULT_COLORS, guild_id)
                        return DEFAULT_COLORS
                    return json.loads(data)
            except json.JSONDecodeError as e:
                log.error(f"Error parsing embed colors JSON for guild {guild_id}: {e}")
                log.info(f"Resetting guild {guild_id} to default colors due to corrupted file")
                save_colors(DEFAULT_COLORS, guild_id)
                return DEFAULT_COLORS
        else:
            # Create default file if it doesn't exist
            save_colors(DEFAULT_COLORS, guild_id)
            return DEFAULT_COLORS
    except Exception as e:
        log.error(f"Error loading embed colors for guild {guild_id}: {e}")
        return DEFAULT_COLORS

def save_colors(colors: Dict[str, int], guild_id: Optional[str] = None) -> bool:
    """Save colors to file.
    
    Args:
        colors: The color settings to save
        guild_id: The guild ID to save colors for, or None for global settings
        
    Returns:
        bool: True if successful, False otherwise
    """
    colors_file = get_colors_file(guild_id)
    
    try:
        with open(colors_file, 'w') as f:
            json.dump(colors, f, indent=4)
        return True
    except Exception as e:
        log.error(f"Error saving embed colors for guild {guild_id}: {e}")
        return False

def get_color(color_type: str, guild_id: Optional[str] = None) -> discord.Color:
    """Get a color by type.
    
    Args:
        color_type: The type of color to get (success, error, etc.)
        guild_id: The guild ID to get colors for, or None for global settings
        
    Returns:
        discord.Color: The requested color
    """
    colors = load_colors(guild_id)
    color_value = colors.get(color_type.lower(), DEFAULT_COLORS.get(color_type.lower(), 0))
    return discord.Color(color_value)

def hex_to_color(hex_color: str) -> int:
    """Convert hex color string to int value."""
    # Remove '#' if present
    hex_color = hex_color.lstrip('#')
    # Convert hex to int
    return int(hex_color, 16)

def color_to_hex(color: int) -> str:
    """Convert int color value to hex string."""
    return f"#{color:06x}" 