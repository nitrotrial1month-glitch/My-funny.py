import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import datetime
from utils import load_config, save_config, get_theme_color

class LiveNotifications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_live.start() # ব্যাকগ্রাউন্ড টাস্ক চালু করা

    def cog_unload(self):
        self.check_live.cancel()

    # ================= 1. CONFIGURATION COMMANDS =================
    @app_commands.command(name="live_setup", description="📢 Set the channel for live notifications")
    @app_commands.checks.has_permissions(administrator=True)
    async def live_setup(self, interaction: discord.Interaction, channel: discord.TextChannel, ping_role: discord.Role = None):
        config = load_config()
        if "live_settings" not in config: config["live_settings"] = {"yt_channels": [], "twitch_users": [], "last_notified": {}}
        
        config["live_settings"]["channel_id"] = channel.id
        config["live_settings"]["ping_role"] = ping_role.id if ping_role else None
        save_config(config)
        
        await interaction.response.send_message(f"✅ Live notifications will be sent to {channel.mention}")

    @app_commands.command(name="yt_add", description="➕ Add a YouTube channel to track")
    @app_commands.checks.has_permissions(administrator=True)
    async def yt_add(self, interaction: discord.Interaction, channel_id: str):
        config = load_config()
        if channel_id not in config["live_settings"]["yt_channels"]:
            config["live_settings"]["yt_channels"].append(channel_id)
            save_config(config)
            await interaction.response.send_message(f"✅ Added YouTube Channel ID: `{channel_id}`")
        else:
            await interaction.response.send_message("⚠️ Already tracking this channel.")

    # ================= 2. BACKGROUND CHECKER (টাস্ক লুপ) =================
    @tasks.loop(minutes=5) # প্রতি ৫ মিনিট পরপর চেক করবে
    async def check_live(self):
        config = load_config()
        settings = config.get("live_settings", {})
        target_channel_id = settings.get("channel_id")
        if not target_channel_id: return

        target_channel = self.bot.get_channel(target_channel_id)
        if not target_channel: return

        async with aiohttp.ClientSession() as session:
            # --- YouTube Check Logic ---
            api_key = "YOUR_YOUTUBE_API_KEY" # এখানে আপনার API Key বসান
            for yt_id in settings.get("yt_channels", []):
                url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={yt_id}&type=video&eventType=live&key={api_key}"
                async with session.get(url) as resp:
                    data = await resp.json()
                    if "items" in data and len(data["items"]) > 0:
                        video_id = data["items"][0]["id"]["videoId"]
                        
                        # ডুপ্লিকেট নোটিফিকেশন আটকানো
                        if settings["last_notified"].get(yt_id) != video_id:
                            settings["last_notified"][yt_id] = video_id
                            save_config(config)
                            await self.send_notif(target_channel, data["items"][0]["snippet"], video_id, "YouTube")

    async def send_notif(self, channel, snippet, media_id, platform):
        config = load_config()
        ping = f"<@&{config['live_settings']['ping_role']}>" if config['live_settings'].get('ping_role') else ""
        
        embed = discord.Embed(
            title=f"🔴 {snippet['channelTitle']} is LIVE on {platform}!",
            description=f"**Title:** {snippet['title']}\n\n[Click here to watch](https://www.youtube.com/watch?v={media_id})",
            color=discord.Color.red() if platform == "YouTube" else discord.Color.purple(),
            timestamp=datetime.datetime.now()
        )
        embed.set_image(url=snippet['thumbnails']['high']['url'])
        embed.set_footer(text="Wow Bot Live Tracker", icon_url=self.bot.user.display_avatar.url)
        
        await channel.send(content=ping, embed=embed)

async def setup(bot):
    await bot.add_cog(LiveNotifications(bot))
                      
