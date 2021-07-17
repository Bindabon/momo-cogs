import discord
from discord.ext import tasks
from redbot.core import commands, Config, checks
from datetime import datetime
import asyncio
import tweepy


class Twitter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = Config.get_conf(
            self, identifier=352305325230, force_registration=True
        )
        self.BASE_URL = "https://twitter.com"

        api_key = ""
        api_secret = ""
        access_token = ""
        access_token_secret = ""

        auth = tweepy.OAuthHandler(api_key, api_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(
            auth, wait_on_rate_limit=False, wait_on_rate_limit_notify=False
        )

        default_guild = {"channels": {}}
        self.data.register_guild(**default_guild)
        self._notification_loop.start()

    def cog_unload(self):
        self._notification_loop.cancel()

    @tasks.loop(minutes=3)
    async def _notification_loop(self):
        await self.bot.wait_until_red_ready()
        self.log.debug("Booting up Twitter service..")        
        data = await self.data.all_guilds()
        if not data:
            return
        for guild_id in data:
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue

            channels = await self.data.guild(guild).channels()

            if not channels:
                continue

            for channel in channels:
                for twitch_page in channels[channel]:
                    await self._fetch_data(
                        guild,
                        channel,
                        twitch_page,
                        channels[channel][twitch_page]["latest_tweet"],
                        channels[channel][twitch_page]["role"],
                    )
                    await asyncio.sleep(3)

    async def _fetch_data(self, guild, channel, username: str, latest_tweet: str, role):
        username = username.lower()
        try:
            user = self.api.user_timeline(username, count=1)
        except:
            return

        if not user:
            return

        _id = user[0].id_str

        if _id == latest_tweet:
            return

        await self.data.guild(guild).channels.set_raw(
            channel, username, "latest_tweet", value=_id
        )

        link = f"{self.BASE_URL}/{username}/status/{_id}"

        role = guild.get_role(role).mention if role else None
        channel = guild.get_channel(int(channel)) if channel else None
        content = f"{role} " if role else ""
        content += link

        if channel:
            await channel.send(
                content=content, allowed_mentions=discord.AllowedMentions(roles=True)
            )

    @commands.guild_only()
    @commands.group()
    async def twitter(self, ctx):
        """Twitter commands."""
        pass

    @twitter.command(name="channel")
    async def _channel(self, ctx, username: str):
        "View the latest tweets from a twitter account."
        username = username.lower()
        try:
            user = self.api.user_timeline(username, count=1)
        except:
            return await ctx.send("No twitter page was found with that name.")
        if not user:
            return await ctx.send("Error: That account has no post.")
        _id = user[0].id_str
        await ctx.send(f"{self.BASE_URL}/{username}/status/{_id}")

    @twitter.command(name="add")
    @checks.mod_or_permissions(manage_channels=True)
    async def _add(
        self,
        ctx,
        channel: discord.TextChannel,
        username: str,
        role: discord.Role = None,
    ):
        """Set notifications for a twitter channel in a Text Channel."""
        username = username.lower()
        try:
            user = self.api.user_timeline(username, count=1)
        except:
            return await ctx.send("No twitter page was found with that name.")
        if not user:
            return await ctx.send("Error: That account has no post.")
        _id = user[0].id_str

        await self.data.guild(ctx.guild).channels.set_raw(
            channel.id,
            username,
            value={"role": role.id if role else None, "latest_tweet": _id},
        )
        if role:
            await ctx.send(
                f"Users with **{role.name}** role will be notified in {channel.mention} everytime **{username}** posts a tweet."
            )
        else:
            await ctx.send(
                f"A notification will be sent in {channel.mention} everytime **{username}** posts a tweet."
            )

    @twitter.command(name="remove", aliases=["delete"])
    @checks.mod_or_permissions(manage_channels=True)
    async def _remove(self, ctx, channel: discord.TextChannel, username: str):
        """Remove a channel from the list."""
        data = await self.data.guild(ctx.guild).channels()
        if str(channel.id) not in data:
            return await ctx.send(
                f"No notifications for any of the twitter page were set in {channel.mention}."
            )

        if username.lower() not in data[str(channel.id)]:
            return await ctx.send(
                f"No notifications were set for **{username.lower()}** in {channel.mention}."
            )

        await self.data.guild(ctx.guild).channels.clear_raw(
            channel.id, username.lower()
        )
        await ctx.send(
            f"Removed notifications for **{username}** from {channel.mention}."
        )

    @twitter.command(name="list")
    @checks.mod_or_permissions(manage_channels=True)
    async def _list(self, ctx, channel: discord.TextChannel):
        """View a list of all the notifications set in a channel."""
        data = await self.data.guild(ctx.guild).channels()
        if str(channel.id) not in data:
            return await ctx.send(
                f"No notifications for any of the twitter pages were set in {channel.mention}."
            )

        if not data[str(channel.id)]:
            return await ctx.send(
                f"No notifications for any of the twitter channels were set in {channel.mention}."
            )

        channels_list = [
            f"{self.BASE_URL}/{channel}" for channel in data[str(channel.id)]
        ]
        embed = discord.Embed(
            description=", ".join(channels_list),
            title="List of Twitter Pages",
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(icon_url="https://i.imgur.com/b4Nmq13.png", text="Twitter")
        await ctx.send(embed=embed)
