import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import os
import aiohttp
from dotenv import load_dotenv
import json
from utils.embed_builder import EmbedBuilder
from cogs.permissions import is_owner_or_administrator

load_dotenv()

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_CHANNELS = os.getenv("TWITCH_CHANNELS", "").split(",")  # Comma-separated list

class TwitchCog(commands.Cog):
    """Twitch integration: notifications, info, and more."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.access_token = None
        self.settings = {}
        self.settings_file = "data/twitch_settings.json"
        self.load_settings()
        self.check_streams.start()

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    if "settings" in data:
                        self.settings = data["settings"]
            else:
                os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
                self.save_settings()
        except Exception as e:
            print(f"Error loading twitch settings: {e}")

    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump({"settings": self.settings}, f, indent=4)
        except Exception as e:
            print(f"Error saving twitch settings: {e}")

    def get_guild_streamers(self, guild_id: int):
        return self.settings.get(str(guild_id), {}).get("streamers", [])

    def add_guild_streamer(self, guild_id: int, streamer: str):
        gid = str(guild_id)
        if gid not in self.settings:
            self.settings[gid] = {"streamers": []}
        if streamer.lower() not in [s.lower() for s in self.settings[gid]["streamers"]]:
            self.settings[gid]["streamers"].append(streamer)
            self.save_settings()

    def remove_guild_streamer(self, guild_id: int, streamer: str):
        gid = str(guild_id)
        if gid in self.settings and streamer in self.settings[gid]["streamers"]:
            self.settings[gid]["streamers"].remove(streamer)
            self.save_settings()

    def get_notification_channel(self, guild_id: int):
        return self.settings.get(str(guild_id), {}).get("notification_channel")

    def set_notification_channel(self, guild_id: int, channel_id: int):
        gid = str(guild_id)
        if gid not in self.settings:
            self.settings[gid] = {"streamers": []}
        self.settings[gid]["notification_channel"] = channel_id
        self.save_settings()

    def get_notification_template(self, guild_id: int):
        return self.settings.get(str(guild_id), {}).get("notification_template", "")

    def set_notification_template(self, guild_id: int, template: str):
        gid = str(guild_id)
        if gid not in self.settings:
            self.settings[gid] = {"streamers": []}
        self.settings[gid]["notification_template"] = template
        self.save_settings()

    async def cog_unload(self):
        await self.session.close()
        self.check_streams.cancel()

    async def get_access_token(self):
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            return None
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        async with self.session.post(url, params=params) as resp:
            data = await resp.json()
            self.access_token = data.get("access_token")
            return self.access_token

    @tasks.loop(minutes=2)
    async def check_streams(self):
        # Poll Twitch API for each guild's tracked streamers
        for guild in self.bot.guilds:
            guild_id = str(guild.id)
            streamers = self.get_guild_streamers(guild_id)
            channel_id = self.get_notification_channel(guild_id)
            if not streamers or not channel_id:
                continue
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            if not hasattr(self, 'currently_live'):
                self.currently_live = {}
            if guild_id not in self.currently_live:
                self.currently_live[guild_id] = set()
            token = self.access_token or await self.get_access_token()
            if not token:
                continue
            headers = {
                "Client-ID": TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {token}"
            }
            streamer_logins = [s.lower() for s in streamers]
            for i in range(0, len(streamer_logins), 100):
                batch = streamer_logins[i:i+100]
                params = [("user_login", login) for login in batch]
                async with self.session.get("https://api.twitch.tv/helix/streams", headers=headers, params=params) as resp:
                    data = await resp.json()
                    live_logins = set()
                    for stream in data.get("data", []):
                        login = stream["user_login"].lower()
                        live_logins.add(login)
                        if login not in self.currently_live[guild_id]:
                            template = self.get_notification_template(guild_id)
                            msg = template.format(
                                streamer=stream['user_name'],
                                title=stream['title'],
                                game=stream.get('game_name', 'Unknown'),
                                url=f"https://twitch.tv/{login}",
                                viewers=stream.get('viewer_count', '?')
                            )
                            # Fetch Twitch user info for avatar
                            user_params = [("login", login)]
                            async with self.session.get("https://api.twitch.tv/helix/users", headers=headers, params=user_params) as user_resp:
                                user_data = await user_resp.json()
                                profile_image_url = None
                                if user_data.get("data") and len(user_data["data"]) > 0:
                                    profile_image_url = user_data["data"][0].get("profile_image_url")
                            # Further improved embed formatting: viewers and watch live on the same line, plain description
                            stream_title = stream['title']
                            game_name = stream.get('game_name', 'Unknown')
                            stream_url = f"https://twitch.tv/{login}"
                            description = f"``{stream_title}``\n\n🎮 Now Playing: {game_name}"
                            embed = EmbedBuilder.custom(
                                title=f"🔴 {stream['user_name']} is LIVE!",
                                description=description,
                                color=discord.Color.purple()
                            )
                            if profile_image_url:
                                embed.set_thumbnail(url=profile_image_url)
                            stream_thumb = stream.get("thumbnail_url", "").replace("{width}", "1280").replace("{height}", "720")
                            if stream_thumb:
                                embed.set_image(url=stream_thumb)
                            embed.add_field(
                                name="👁️ Viewers",
                                value=str(stream.get("viewer_count", "?")),
                                inline=True
                            )
                            embed.add_field(
                                name="📺 Watch Live",
                                value=f"[Click here to watch on Twitch!]({stream_url})",
                                inline=True
                            )
                            embed.set_footer(text="Twitch Notification ✓")
                            view = discord.ui.View()
                            view.add_item(discord.ui.Button(label="Watch Live on Twitch", url=stream_url, style=discord.ButtonStyle.link))
                            await channel.send(msg, embed=embed, view=view)
                    self.currently_live[guild_id].update(live_logins)
                    no_longer_live = self.currently_live[guild_id] - set(streamer_logins)
                    self.currently_live[guild_id] -= no_longer_live

    @app_commands.command(name="twitch", description="[Admin] Manage twitch notifications.")
    @is_owner_or_administrator()
    async def twitch_menu(self, interaction: discord.Interaction):
        """Show Twitch integration options."""
        guild_id = interaction.guild.id if interaction.guild else None
        streamers = self.get_guild_streamers(guild_id) if guild_id else []
        notification_channel_id = self.get_notification_channel(guild_id) if guild_id else None
        embed = discord.Embed(
            title="Twitch Integration ✓",
            description="• Manage Twitch notifications and info.\n• Use the buttons below to add or remove streamers.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png")
        if streamers:
            embed.add_field(name="Tracked Streamers", value="\n".join(f"• `{s}`" for s in streamers), inline=False)
        else:
            embed.add_field(name="Tracked Streamers", value="*(none)*", inline=False)
        if notification_channel_id:
            channel_mention = f"<#{notification_channel_id}>"
        else:
            channel_mention = "*(not set)*"
        embed.add_field(name="Notification Channel", value=channel_mention, inline=False)
        template = self.get_notification_template(guild_id)
        embed.add_field(name="Notification Template", value=f"```{template or '(disabled)'}```", inline=False)
        view = TwitchMenuView(self, guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @twitch_menu.error
    async def twitch_menu_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.CheckFailure):
            embed = EmbedBuilder.error(
                title="✗ Access Denied",
                description="You need administrator permissions or an allowed admin role to use this command."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = EmbedBuilder.error(
                title="✗ Error",
                description=f"An error occurred: {str(error)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class TwitchMenuView(ui.View):
    def __init__(self, cog: TwitchCog, guild_id: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.guild_id = guild_id

    @ui.button(label="Add Streamer", style=discord.ButtonStyle.secondary, custom_id="add_streamer")
    async def add_streamer(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AddStreamerModal(self.cog, self.guild_id))

    @ui.button(label="Remove Streamer", style=discord.ButtonStyle.secondary, custom_id="remove_streamer")
    async def remove_streamer(self, interaction: discord.Interaction, button: ui.Button):
        streamers = self.cog.get_guild_streamers(self.guild_id)
        if not streamers:
            notification_channel_id = self.cog.get_notification_channel(self.guild_id)
            embed = discord.Embed(
                title="Twitch Integration ✓",
                description="• Manage Twitch notifications and info.\n• Use the buttons below to add or remove streamers.",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png")
            embed.add_field(name="Tracked Streamers", value="*(none)*", inline=False)
            if notification_channel_id:
                channel_mention = f"<#{notification_channel_id}>"
            else:
                channel_mention = "*(not set)*"
            embed.add_field(name="Notification Channel", value=channel_mention, inline=False)
            view = TwitchMenuView(self.cog, self.guild_id)
            await interaction.response.edit_message(embed=embed, view=view)
            return
        await interaction.response.send_modal(RemoveStreamerModal(self.cog, self.guild_id, streamers))

    @ui.button(label="Set Notification Channel (This Channel)", style=discord.ButtonStyle.secondary, custom_id="set_channel", row=1)
    async def set_channel(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.guild or not interaction.channel:
            await interaction.response.send_message("✗ Error: Must be used in a server channel.", ephemeral=True)
            return
        self.cog.set_notification_channel(interaction.guild.id, interaction.channel.id)
        guild_id = interaction.guild.id
        streamers = self.cog.get_guild_streamers(guild_id)
        notification_channel_id = self.cog.get_notification_channel(guild_id)
        embed = discord.Embed(
            title="Twitch Integration ✓",
            description="• Manage Twitch notifications and info.\n• Use the buttons below to add or remove streamers.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png")
        if streamers:
            embed.add_field(name="Tracked Streamers", value="\n".join(f"• `{s}`" for s in streamers), inline=False)
        else:
            embed.add_field(name="Tracked Streamers", value="*(none)*", inline=False)
        if notification_channel_id:
            channel_mention = f"<#{notification_channel_id}>"
        else:
            channel_mention = "*(not set)*"
        embed.add_field(name="Notification Channel", value=channel_mention, inline=False)
        view = TwitchMenuView(self.cog, guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @ui.button(label="Customize Notification Message", style=discord.ButtonStyle.secondary, custom_id="customize_message", row=1)
    async def customize_message(self, interaction: discord.Interaction, button: ui.Button):
        current = self.cog.get_notification_template(self.guild_id)
        await interaction.response.send_modal(CustomizeMessageModal(self.cog, self.guild_id, current))

class AddStreamerModal(ui.Modal, title="Add Twitch Streamer"):
    streamer = ui.TextInput(label="Twitch Username", placeholder="e.g. pokimane", required=True)
    def __init__(self, cog: TwitchCog, guild_id: int):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
    async def on_submit(self, interaction: discord.Interaction):
        self.cog.add_guild_streamer(self.guild_id, self.streamer.value)
        # Rebuild the embed with updated streamer list
        streamers = self.cog.get_guild_streamers(self.guild_id)
        notification_channel_id = self.cog.get_notification_channel(self.guild_id)
        embed = discord.Embed(
            title="Twitch Integration ✓",
            description="• Manage Twitch notifications and info.\n• Use the buttons below to add or remove streamers.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png")
        if streamers:
            embed.add_field(name="Tracked Streamers", value="\n".join(f"• `{s}`" for s in streamers), inline=False)
        else:
            embed.add_field(name="Tracked Streamers", value="*(none)*", inline=False)
        if notification_channel_id:
            channel_mention = f"<#{notification_channel_id}>"
        else:
            channel_mention = "*(not set)*"
        embed.add_field(name="Notification Channel", value=channel_mention, inline=False)
        view = TwitchMenuView(self.cog, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

class RemoveStreamerModal(ui.Modal, title="Remove Twitch Streamer"):
    streamer = ui.TextInput(label="Twitch Username", placeholder="e.g. pokimane", required=True)
    def __init__(self, cog: TwitchCog, guild_id: int, streamers: list):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.streamers = streamers
    async def on_submit(self, interaction: discord.Interaction):
        if self.streamer.value not in self.streamers:
            await interaction.response.send_message(f"✗ `{self.streamer.value}` is not being tracked.", ephemeral=True)
            return
        self.cog.remove_guild_streamer(self.guild_id, self.streamer.value)
        # Rebuild the embed with updated streamer list
        streamers = self.cog.get_guild_streamers(self.guild_id)
        notification_channel_id = self.cog.get_notification_channel(self.guild_id)
        embed = discord.Embed(
            title="Twitch Integration ✓",
            description="• Manage Twitch notifications and info.\n• Use the buttons below to add or remove streamers.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png")
        if streamers:
            embed.add_field(name="Tracked Streamers", value="\n".join(f"• `{s}`" for s in streamers), inline=False)
        else:
            embed.add_field(name="Tracked Streamers", value="*(none)*", inline=False)
        if notification_channel_id:
            channel_mention = f"<#{notification_channel_id}>"
        else:
            channel_mention = "*(not set)*"
        embed.add_field(name="Notification Channel", value=channel_mention, inline=False)
        view = TwitchMenuView(self.cog, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

class CustomizeMessageModal(ui.Modal, title="Customize Twitch Notification Message"):
    template = ui.TextInput(
        label="Message Template",
        placeholder="@everyone {streamer} is now live! {url}",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=200
    )
    def __init__(self, cog: TwitchCog, guild_id: int, current: str):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.template.default = current
    async def on_submit(self, interaction: discord.Interaction):
        template_value = self.template.value.strip() or ""
        self.cog.set_notification_template(self.guild_id, template_value)
        # Rebuild the embed with updated info
        streamers = self.cog.get_guild_streamers(self.guild_id)
        notification_channel_id = self.cog.get_notification_channel(self.guild_id)
        embed = discord.Embed(
            title="Twitch Integration ✓",
            description="• Manage Twitch notifications and info.\n• Use the buttons below to add or remove streamers.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png")
        if streamers:
            embed.add_field(name="Tracked Streamers", value="\n".join(f"• `{s}`" for s in streamers), inline=False)
        else:
            embed.add_field(name="Tracked Streamers", value="*(none)*", inline=False)
        if notification_channel_id:
            channel_mention = f"<#{notification_channel_id}>"
        else:
            channel_mention = "*(not set)*"
        embed.add_field(name="Notification Channel", value=channel_mention, inline=False)
        embed.add_field(name="Notification Template", value=f"```{template_value or '(disabled)'}```", inline=False)
        view = TwitchMenuView(self.cog, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(TwitchCog(bot)) 