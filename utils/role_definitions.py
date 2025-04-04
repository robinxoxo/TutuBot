from enum import Enum
from typing import Dict, Any
import discord

# Role categories and their emoji+name mappings
class RoleCategory(Enum):
    """Categories for organizing roles in the selection UI."""
    CREATIVE = "Creative Roles"
    MMO = "MMO Games"
    MULTIPLAYER = "Multiplayer Games"  
    NINTENDO = "Nintendo Games"
    PARTY = "Party Games & Social"

# Role definitions with emoji and category
# Format: 
# "role_id": {
#     "name": "Display Name", 
#     "emoji": "Emoji", 
#     "category": RoleCategory.CATEGORY, 
#     "description": "Optional description",
#     "color": discord.Color (optional)
# }
ROLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # Creative roles - Each with a distinct color
    "content_creator": {"name": "Content Creator", "emoji": "🎤", "category": RoleCategory.CREATIVE, "description": "Twitch, YouTube, podcast, etc.", "color": discord.Color.red()},
    "artist": {"name": "Artist", "emoji": "🎨", "category": RoleCategory.CREATIVE, "description": "GFX design, digital art, traditional art, etc.", "color": discord.Color.purple()},
    "developer": {"name": "Developer", "emoji": "👨‍💻", "category": RoleCategory.CREATIVE, "description": "Video game, mobile, web, etc.", "color": discord.Color.blue()},
    "photographer": {"name": "Photographer", "emoji": "📸", "category": RoleCategory.CREATIVE, "description": "IRL and virtual", "color": discord.Color.teal()},
    "tech_expert": {"name": "Tech Expert", "emoji": "👨‍🔧", "category": RoleCategory.CREATIVE, "description": "Hardware, software, troubleshooting", "color": discord.Color.dark_gold()},
    
    # MMO Games - Default color (no color specified)
    "wow": {"name": "World of Warcraft", "emoji": "🧙‍♂️", "category": RoleCategory.MMO, "description": ""},
    "eso": {"name": "The Elder Scrolls Online", "emoji": "📜", "category": RoleCategory.MMO, "description": ""},
    "gw2": {"name": "Guild Wars 2", "emoji": "🐉", "category": RoleCategory.MMO, "description": ""},
    "bdo": {"name": "Black Desert Online", "emoji": "⚔️", "category": RoleCategory.MMO, "description": ""},
    "lost_ark": {"name": "Lost Ark", "emoji": "🔮", "category": RoleCategory.MMO, "description": ""},
    
    # Multiplayer Games - Default color (no color specified)
    "minecraft": {"name": "Minecraft", "emoji": "⛏️", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "cod": {"name": "Call of Duty", "emoji": "🔫", "category": RoleCategory.MULTIPLAYER, "description": "Franchise"},
    "cod_zombies": {"name": "CoD Zombies", "emoji": "🧟", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "dbd": {"name": "Dead By Daylight", "emoji": "💀", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "fortnite": {"name": "Fortnite", "emoji": "🧱", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "destiny2": {"name": "Destiny 2", "emoji": "🪐", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "warframe": {"name": "Warframe", "emoji": "🚀", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "sea_of_thieves": {"name": "Sea of Thieves", "emoji": "☠️", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "halo": {"name": "Halo", "emoji": "🌌", "category": RoleCategory.MULTIPLAYER, "description": "Franchise"},
    "apex": {"name": "Apex Legends", "emoji": "🅰️", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "valorant": {"name": "Valorant", "emoji": "🔥", "category": RoleCategory.MULTIPLAYER, "description": ""},
    
    # Nintendo Games - Default color (no color specified)
    "animal_crossing": {"name": "Animal Crossing", "emoji": "🍃", "category": RoleCategory.NINTENDO, "description": "New Horizons"},
    "smash": {"name": "Super Smash Bros", "emoji": "🥊", "category": RoleCategory.NINTENDO, "description": "Ultimate"},
    "pokemon": {"name": "Pokémon", "emoji": "🐹", "category": RoleCategory.NINTENDO, "description": "Franchise"},
    "splatoon": {"name": "Splatoon", "emoji": "🖌️", "category": RoleCategory.NINTENDO, "description": "Franchise"},
    
    # Party Games & Social - Default color (no color specified)
    "among_us": {"name": "Among Us", "emoji": "🌘", "category": RoleCategory.PARTY, "description": ""},
    "fall_guys": {"name": "Fall Guys", "emoji": "👑", "category": RoleCategory.PARTY, "description": ""},
    "phasmophobia": {"name": "Phasmophobia", "emoji": "👻", "category": RoleCategory.PARTY, "description": ""},
    "jackbox": {"name": "Jackbox Party Pack", "emoji": "🥳", "category": RoleCategory.PARTY, "description": "Games"},
    "watch_party": {"name": "Watch Party", "emoji": "🍿", "category": RoleCategory.PARTY, "description": "Movies & TV"},
    "multiversus": {"name": "MultiVersus", "emoji": "🆚", "category": RoleCategory.PARTY, "description": ""}
}

# To add a new role:
# 1. Add a new entry to ROLE_DEFINITIONS with a unique key
# 2. Include "name", "emoji", "category", and optional "description"
# 3. Use an existing category or add a new one to RoleCategory enum above
# 4. Optionally add "color" using discord.Color for colored roles
# Example:
# "new_game": {"name": "New Game", "emoji": "🎮", "category": RoleCategory.MULTIPLAYER, "description": "Game description"}
# "new_creative": {"name": "Creative Role", "emoji": "🎨", "category": RoleCategory.CREATIVE, "description": "Description", "color": discord.Color.green()} 