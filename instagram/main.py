import asyncio
import aiohttp
import discord
import typing

from datetime import datetime
from discord.ext import tasks
from redbot.core import Config, commands
from asyncio_throttle import Throttler


class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=327423749328423, force_registration=True
        )
        self.headers = {
            "x-rapidapi-key": "e4689f1a29msh3aae6700af40a7fp16cbc9jsn9569a4434102",
            "x-rapidapi-host": "instagram-unofficial.p.rapidapi.com",
        }
        self.throttler = Throttler(1, 1.0, 1.0)
        default_guild = {
            "igaccount": {"name": None, "password": None, "sessionkey": None},
            "channel": None,
            "account": {},
        }
        self.config.register_guild(**default_guild)
        self.check.start()

    def cog_unload(self):
        self.check.cancel()

    async def _get_session_key(self, username, password):
        async with self.throttler:
            connector = aiohttp.TCPConnector(limit=1)
            async with aiohttp.ClientSession(
                headers=self.headers, connector=connector
            ) as session:
                async with session.get(
                    f"https://instagram-unofficial.p.rapidapi.com/login?username={username}&password={password}"
                ) as r:
                    if r.status != 200:
                        return
                    return await r.json()

    async def _get_user_info(self, sessionkey, username: typing.Union[str, int]):
        async with self.throttler:
            connector = aiohttp.TCPConnector(limit=1)
            async with aiohttp.ClientSession(
                headers=self.headers, connector=connector
            ) as session:
                if isinstance(username, str):
                    async with session.get(
                        f"https://instagram-unofficial.p.rapidapi.com/get-user?session_key={sessionkey}&username={username}"
                    ) as r:
                        if r.status != 200:
                            return
                        return await r.json()
                elif isinstance(username, int):
                    async with session.get(
                        f"https://instagram-unofficial.p.rapidapi.com/get-user?session_key={sessionkey}&user_id={username}"
                    ) as r:
                        if r.status != 200:
                            return
                        return await r.json()

    async def _get_user_post(self, sessionkey, userid):
        async with self.throttler:
            connector = aiohttp.TCPConnector(limit=1)
            async with aiohttp.ClientSession(
                headers=self.headers, connector=connector
            ) as session:
                async with session.get(
                    f"https://instagram-unofficial.p.rapidapi.com/user-posts?session_key={sessionkey}&user_id={userid}"
                ) as r:
                    if r.status != 200:
                        return
                    return await r.json()

    async def _check_logged(self, ctx):
        return await self.config.guild(ctx.guild).igaccount()

    @tasks.loop(seconds=30)
    async def check(self):
        guilds = await self.config.all_guilds()
        for guild in guilds:
            sessionkey = guilds[guild]["igaccount"]["sessionkey"]
            if not (guildd := self.bot.get_guild(guild)):
                continue
            if not (channel := guildd.get_channel(guilds[guild]["channel"])):
                continue
            for accountid in guilds[guild]["account"]:
                storedpost = await self.config.guild(guildd).account.get_raw(
                    f"{accountid}", "lastpost"
                )
                if not (acc := await self._get_user_info(sessionkey, int(accountid))):
                    continue
                await asyncio.sleep(1)

                if not (
                    lastpost := await self._get_user_post(sessionkey, int(accountid))
                ):
                    continue
                if "data" not in lastpost:
                    continue
                if lastpost["data"]["num_results"] == 0:
                    continue
                if lastpost["data"]["items"][0]["code"] != storedpost:
                    await self.config.guild(guildd).account.set_raw(
                        accountid,
                        value={"lastpost": lastpost["data"]["items"][0]["code"]},
                    )

                    em = discord.Embed(
                        color=discord.Color(await self.bot._config.color()),
                        timestamp=datetime.fromtimestamp(
                            lastpost["data"]["items"][0]["taken_at"]
                        ),
                    )
                    em.set_author(
                        name=f"{acc['data']['user']['username']}",
                        url=f"https://instagram.com/{acc['data']['user']['username']}",
                        icon_url=acc["data"]["user"]["profile_pic_url"],
                    )
                    if lastpost["data"]["items"][0]["media_type"] == 1:
                        em.set_thumbnail(
                            url=acc["data"]["user"]["hd_profile_pic_url_info"]["url"]
                        )
                        em.description = f"New Post\nClick [HERE](https://instagram.com/p/{lastpost['data']['items'][0]['code']}) to see it.\n\n{lastpost['data']['items'][0]['caption']['text']}"
                        em.set_image(
                            url=lastpost["data"]["items"][0]["image_versions2"][
                                "candidates"
                            ][0]["url"]
                        )
                    elif lastpost["data"]["items"][0]["media_type"] == 2:
                        em.set_thumbnail(
                            url=acc["data"]["user"]["hd_profile_pic_url_info"]["url"]
                        )
                        em.description = f"New Video Post\nClick [HERE](https://instagram.com/p/{lastpost['data']['items'][0]['code']}) to see it.\n\n{lastpost['data']['items'][0]['caption']['text']}"
                        em.add_field(
                            name="Views Count",
                            value=f'`{int(lastpost["data"]["items"][0]["view_count"]):,}`',
                        )
                        em.set_image(
                            url=lastpost["data"]["items"][0]["image_versions2"][
                                "candidates"
                            ][0]["url"]
                        )
                    elif lastpost["data"]["items"][0]["media_type"] == 8:
                        em.description = f"New Carousel Post\nClick [HERE](https://instagram.com/p/{lastpost['data']['items'][0]['code']}) to see it.\n\n{lastpost['data']['items'][0]['caption']['text']}"
                        em.set_image(
                            url=lastpost["data"]["items"][0]["carousel_media"][0][
                                "image_versions2"
                            ]["candidates"][0]["url"]
                        )
                        em.set_thumbnail(
                            url=lastpost["data"]["items"][0]["carousel_media"][1][
                                "image_versions2"
                            ]["candidates"][0]["url"]
                        )
                    em.add_field(
                        name="Likes",
                        value=f'`{lastpost["data"]["items"][0]["like_count"]:,}`',
                    )
                    em.add_field(
                        name="Comments",
                        value=f'`{lastpost["data"]["items"][0]["comment_count"]:,}`',
                    )
                    em.set_footer(
                        text=f"{acc['data']['user']['media_count']:,} posts | {acc['data']['user']['follower_count']:,} followers",
                        icon_url="https://i.imgur.com/91N2xRx.png",
                    )

                    await channel.send(embed=em)

    @commands.group()
    @commands.guild_only()
    async def ig(self, ctx):
        """Instagram commands."""
        pass

    @ig.command()
    @commands.guildowner()
    async def login(self, ctx, username: str, password: str):
        """Login to your Instagram account to perform the other commands."""
        sessionkey = await self._get_session_key(username, password)
        if (
            "error" in sessionkey
            and sessionkey["error"] == "invalid_user"
            or "error" in sessionkey
            and sessionkey["error"] == "bad_password"
        ):
            return await ctx.send("Wrong credentials, please verify and retry.")

        await self.config.guild(ctx.guild).igaccount.set_raw(
            value={
                "name": username,
                "password": password,
                "sessionkey": sessionkey["session_key"],
            }
        )
        await ctx.send("You have successfully set a logged in account.")

    @ig.command()
    @commands.guildowner()
    async def setchan(self, ctx, channel: discord.TextChannel = None):
        """Set the channel that will receive the new posts notifications."""
        channel = ctx.channel if not channel else channel
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"`{channel}` has been set as the listening channel.")

    @ig.command()
    @commands.mod()
    async def add(self, ctx, *, username: str):
        """Add an account to keep tracking on."""
        sessionkey = await self.config.guild(ctx.guild).igaccount.sessionkey()
        account = await self._get_user_info(sessionkey, username)

        if "error" in account and account["error"] == "Invalid session key":
            try:
                acc = await self.config.guild(ctx.guild).igaccount.name()
                pw = await self.config.guild(ctx.guild).igaccount.password()
                sessionkey = await self._get_session_key(acc, pw)
            except:
                return await ctx.send("Error: Please try to re-enter your credentials.")

        if (
            str(account["data"]["user"]["pk"])
            in await self.config.guild(ctx.guild).account()
        ):
            return await ctx.send("That user is already in the database.")

        lastpost = await self._get_user_post(sessionkey, account["data"]["user"]["pk"])
        if (
            "error" in lastpost
            and lastpost["error"] == "Bad Request: Not authorized to view user"
        ):
            return await ctx.send("That user is private, I will not add it.")
        if lastpost["data"]["num_results"] == 0:
            await self.config.guild(ctx.guild).account.set_raw(
                account["data"]["user"]["pk"], value={"lastpost": 0}
            )
        else:
            await self.config.guild(ctx.guild).account.set_raw(
                account["data"]["user"]["pk"],
                value={"lastpost": lastpost["data"]["items"][0]["code"]},
            )
        await ctx.send(
            f"Account `{username} (id: {account['data']['user']['pk']})` has been successfully added."
        )

    @ig.command()
    @commands.mod()
    async def remove(self, ctx, *, username: str):
        """Remove an account."""
        sessionkey = await self.config.guild(ctx.guild).igaccount.sessionkey()
        accid = await self._get_user_info(sessionkey, username)
        if "error" in accid and accid["error"] == "Invalid session key":
            try:
                acc = await self.config.guild(ctx.guild).igaccount.name()
                pw = await self.config.guild(ctx.guild).igaccount.password()
                sessionkey = await self._get_session_key(acc, pw)
            except:
                return await ctx.send("Error: Please try to re-enter your credentials.")
        if (
            str(accid["data"]["user"]["pk"])
            not in await self.config.guild(ctx.guild).account()
        ):
            return await ctx.send("That user isn't in the database.")

        await self.config.guild(ctx.guild).account.clear_raw(
            accid["data"]["user"]["pk"]
        )
        await ctx.send(f"`{username}` has been deleted.")