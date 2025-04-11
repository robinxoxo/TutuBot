import discord
import json
import os
import logging
from typing import Dict, Any

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
COLORS_FILE = "data/embed_colors.json"

# Ensure directory exists
os.makedirs(os.path.dirname(COLORS_FILE), exist_ok=True)

def load_colors() -> Dict[str, int]:
    """Load custom colors from file or return defaults if file doesn't exist."""
    try:
        if os.path.exists(COLORS_FILE):
            with open(COLORS_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default file if it doesn't exist
            save_colors(DEFAULT_COLORS)
            return DEFAULT_COLORS
    except Exception as e:
        log.error(f"Error loading embed colors: {e}")
        return DEFAULT_COLORS

def save_colors(colors: Dict[str, int]) -> bool:
    """Save colors to file."""
    try:
        with open(COLORS_FILE, 'w') as f:
            json.dump(colors, f, indent=4)
        return True
    except Exception as e:
        log.error(f"Error saving embed colors: {e}")
        return False

def get_color(color_type: str) -> discord.Color:
    """Get a color by type."""
    colors = load_colors()
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