from enum import Enum
from typing import Dict, Any
import discord

# Role categories and their emoji+name mappings
class RoleCategory(Enum):
    """Categories for organizing roles in the selection UI."""
    SERVER_PINGS = "Server Pings"
    CREATIVE = "Creative Roles"
    MMO = "MMO Games"
    ACTION_RPG = "Action RPGs"
    MULTIPLAYER = "Multiplayer Games"  
    NINTENDO = "Nintendo Games"
    PARTY = "Party Games & Social"
    PRONOUNS = "Pronouns"

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
    # Server ping roles
    "events": {"name": "Events", "emoji": "🎉", "category": RoleCategory.SERVER_PINGS, "description": "Game Nights, Movie/TV Nights, Contests & Other Events."},
    "news": {"name": "News", "emoji": "📰", "category": RoleCategory.SERVER_PINGS, "description": "Announcements, updates, and important information."},
    "live": {"name": "Live", "emoji": "🔴", "category": RoleCategory.SERVER_PINGS, "description": "Live Streams, Twitch, YouTube, etc."},
    "live2": {"name": "Community Live", "emoji": "🔴", "category": RoleCategory.SERVER_PINGS, "description": "Get notified when community members go is live."},
    "youtube": {"name": "YouTube", "emoji": "📺", "category": RoleCategory.SERVER_PINGS, "description": "YouTube channels and content."},
    "podcast": {"name": "Podcast", "emoji": "🎙️", "category": RoleCategory.SERVER_PINGS, "description": "Notifications for all podcasts featuring CaptainTutu."},
    "ping_me": {"name": "Ping Me", "emoji": "❗", "category": RoleCategory.SERVER_PINGS, "description": "Ping me for anything and everything."},

    # Creative roles - Each with a distinct color
    "content_creator": {"name": "Content Creator", "emoji": "🎤", "category": RoleCategory.CREATIVE, "description": "Twitch, YouTube, podcast, etc.", "color": discord.Color.from_rgb(175, 68, 117)},
    "artist": {"name": "Artist", "emoji": "🎨", "category": RoleCategory.CREATIVE, "description": "GFX design, digital art, traditional art, etc.", "color": discord.Color.from_rgb(161, 255, 178)},
    "developer": {"name": "Developer", "emoji": "👨‍💻", "category": RoleCategory.CREATIVE, "description": "Video game, mobile, web, etc.", "color": discord.Color.from_rgb(238, 107, 107)},
    "photographer": {"name": "Photographer", "emoji": "📸", "category": RoleCategory.CREATIVE, "description": "IRL and virtual", "color": discord.Color.from_rgb(248, 224, 93)},
    "tech_expert": {"name": "Tech Expert", "emoji": "👨‍🔧", "category": RoleCategory.CREATIVE, "description": "Hardware, software, troubleshooting", "color": discord.Color.blue()},
    
    # MMO Games - Default color (no color specified)
    "ffxiv": {"name": "Final Fantasy XIV", "emoji": "💎", "category": RoleCategory.MMO, "description": ""},
    "wow": {"name": "World of Warcraft", "emoji": "🧙‍♂️", "category": RoleCategory.MMO, "description": ""},
    "eso": {"name": "The Elder Scrolls Online", "emoji": "📜", "category": RoleCategory.MMO, "description": ""},
    "gw2": {"name": "Guild Wars 2", "emoji": "🐉", "category": RoleCategory.MMO, "description": ""},
    "bdo": {"name": "Black Desert Online", "emoji": "⚔️", "category": RoleCategory.MMO, "description": ""},

    # Action RPGs - Default color (no color specified)
    "d4": {"name": "Diablo 4", "emoji": "😈", "category": RoleCategory.ACTION_RPG, "description": ""},
    "poe2": {"name": "Path of Exile 2", "emoji": "⚔️", "category": RoleCategory.ACTION_RPG, "description": ""},
    "last_epoch": {"name": "Last Epoch", "emoji": "⏳", "category": RoleCategory.ACTION_RPG, "description": ""},
   
    # Multiplayer Games - Default color (no color specified)
    "minecraft": {"name": "Minecraft", "emoji": "⛏️", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "cod": {"name": "Call of Duty", "emoji": "🔫", "category": RoleCategory.MULTIPLAYER, "description": "MP, Zombies, Warzone"},
    "monster_hunter": {"name": "Monster Hunter", "emoji": "👹", "category": RoleCategory.MULTIPLAYER, "description": "Wilds"},
    "dbd": {"name": "Dead By Daylight", "emoji": "💀", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "fortnite": {"name": "Fortnite", "emoji": "🧱", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "destiny2": {"name": "Destiny 2", "emoji": "🪐", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "warframe": {"name": "Warframe", "emoji": "🚀", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "apex": {"name": "Apex Legends", "emoji": "🅰️", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "valorant": {"name": "Valorant", "emoji": "🔥", "category": RoleCategory.MULTIPLAYER, "description": ""},
    "marvel_rivals": {"name": "Marvel Rivals", "emoji": "🦸", "category": RoleCategory.MULTIPLAYER, "description": "Wolvie baby"},
    
    # Nintendo Games - Default color (no color specified)
    "animal_crossing": {"name": "Animal Crossing", "emoji": "🍃", "category": RoleCategory.NINTENDO, "description": "New Horizons"},
    "mk_world": {"name": "Mario Kart", "emoji": "🏎️", "category": RoleCategory.NINTENDO, "description": "World"},
    "smash": {"name": "Super Smash Bros", "emoji": "🥊", "category": RoleCategory.NINTENDO, "description": "Ultimate"},
    "pokemon": {"name": "Pokémon", "emoji": "🐹", "category": RoleCategory.NINTENDO, "description": "Franchise"},
    "splatoon": {"name": "Splatoon", "emoji": "🖌️", "category": RoleCategory.NINTENDO, "description": "Franchise"},
    
    # Party Games & Social - Default color (no color specified)
    "among_us": {"name": "Among Us", "emoji": "🌘", "category": RoleCategory.PARTY, "description": ""},
    "fall_guys": {"name": "Fall Guys", "emoji": "👑", "category": RoleCategory.PARTY, "description": ""},
    "jackbox": {"name": "Jackbox Party Pack", "emoji": "🥳", "category": RoleCategory.PARTY, "description": "Franchise"},
    "watch_party": {"name": "Watch Party", "emoji": "🍿", "category": RoleCategory.PARTY, "description": "Movies & TV"},

    # Pronouns - Default color (no color specified)
    "he": {"name": "He/Him", "emoji": "🧑", "category": RoleCategory.PRONOUNS, "description": ""},
    "she": {"name": "She/Her", "emoji": "👧", "category": RoleCategory.PRONOUNS, "description": ""},
    "they": {"name": "They/Them", "emoji": "🧑‍🤝‍🧑", "category": RoleCategory.PRONOUNS, "description": ""},
    "any": {"name": "Any Pronouns", "emoji": "🧑‍🤝‍🧑", "category": RoleCategory.PRONOUNS, "description": ""},
    "ask": {"name": "Ask Pronouns", "emoji": "❓", "category": RoleCategory.PRONOUNS, "description": ""},
}

# To add a new role:
# 1. Add a new entry to ROLE_DEFINITIONS with a unique key
# 2. Include "name", "emoji", "category", and optional "description"
# 3. Use an existing category or add a new one to RoleCategory enum above
# 4. Optionally add "color" using discord.Color for colored roles
# Example:
# "new_game": {"name": "New Game", "emoji": "🎮", "category": RoleCategory.MULTIPLAYER, "description": "Game description"}
# "new_creative": {"name": "Creative Role", "emoji": "🎨", "category": RoleCategory.CREATIVE, "description": "Description", "color": discord.Color.green()} 
