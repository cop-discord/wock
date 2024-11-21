from itertools import chain
from traceback import format_exception
from typing import Annotated, Optional, cast
from discord import Embed, Guild, Message, User
from discord.ext.commands import Cog, command, group
from discord.utils import as_chunks, format_dt
from jishaku.modules import ExtensionConverter
from wavelink import Pool
from extensions.music.player import Player
from system.pagination import Paginator
from system.utils import pluralize
from wock import Wock, Context


class Developer(Cog, command_attrs=dict(hidden=False)):
    def __init__(self, bot: Wock) -> None:
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @command(aliases=("rl",))
    async def reload(
        self,
        ctx: Context,
        *extensions: Annotated[str, ExtensionConverter],
    ) -> Message:
        """Reload extensions."""

        result: list[str] = []
        for extension in chain(*extensions):
            extension = "extensions." + extension.replace("extensions.", "")
            method, icon = (
                (
                    self.bot.reload_extension,
                    "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                )
                if extension in self.bot.extensions
                else (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                await method(extension)
            except Exception as exc:
                traceback_data = "".join(
                    format_exception(type(exc), exc, exc.__traceback__, 1)
                )

                result.append(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```"
                )
            else:
                result.append(f"{icon} `{extension}`")

        return await ctx.send("\n".join(result))

    @group(aliases=("servers", "server", "guild"), invoke_without_command=True)
    async def guilds(self, ctx: Context) -> Message:
        """View all servers the bot is in."""

        def get_player(guild_id: int) -> Player:
            return cast(Player, self.bot.node.get_player(guild_id))

        embeds: list[Embed] = []
        sorted_guilds = sorted(
            self.bot.guilds,
            key=lambda guild: get_player(guild.id) is not None,
            reverse=True,
        )
        for guilds in as_chunks(sorted_guilds, 6):
            embed = Embed(title="Servers")
            for guild in guilds:
                player = get_player(guild.id)
                _id = f"`{guild.id}`"
                if guild.vanity_url:
                    _id = f"[{_id}]({guild.vanity_url})"

                embed.add_field(
                    name=guild.name,
                    value="\n".join(
                        [
                            _id,
                            f"Owner: {guild.owner or guild.owner_id}",
                            f"Music Session: {'✅' if player else '❌'}",
                            f"Synthesizing Text: {'✅' if player and player.synthesize else '❌'}",
                        ]
                    ),
                )

            embeds.append(embed)

        return await Paginator(ctx, entries=embeds)

    @guilds.command(
        name="view",
        aliases=(
            "search",
            "info",
        ),
    )
    async def guilds_view(self, ctx: Context, *, guild: Guild) -> Message:
        """View more information about a server."""

        player = cast(Player, self.bot.node.get_player(guild.id))
        embed = Embed()
        embed.description = (
            f"{format_dt(guild.created_at)} ({format_dt(guild.created_at, 'R')})"
        )
        embed.set_author(name=guild.name, url=guild.vanity_url, icon_url=guild.icon)
        embed.add_field(
            name="General",
            value=(
                "\n".join(
                    [
                        f"Owner: {guild.owner or guild.owner_id}",
                        f"Verification: {guild.verification_level.name.title()}",
                        f"Nitro Boosts: {guild.premium_subscription_count:,} (`Level {guild.premium_tier}`)",
                    ]
                )
            ),
        )
        embed.add_field(
            name="Metrics",
            value=(
                "\n".join(
                    [
                        f"Members: {guild.member_count:,}",
                        f"Text Channels: {len(guild.text_channels):,}",
                        f"Voice Channels: {len(guild.voice_channels):,}",
                    ]
                )
            ),
        )
        if player:
            value: list[str] = []
            if track := player.current:
                value.append(
                    f"Listening to [**{track.title}**]({track.uri}) by **{track.author}**"
                )

            if player.queue or player.queue.history:
                value.append(
                    f"Queued `{len(player.queue):,}` {pluralize('track', len(player.queue))}"
                    + (
                        f" (history of `{len(player.queue.history)}` {pluralize('track', len(player.queue.history))})"
                        if player.queue.history
                        else ""
                    )
                )

            if player.synthesize:
                value.append(f"Synthesizing text inside the voice channel")

            embed.add_field(
                name="Music",
                value="\n".join(value),
                inline=False,
            )

        return await ctx.send(embed=embed)

    @group(aliases=("bl",), invoke_without_command=True)
    async def blacklist(
        self,
        ctx: Context,
        target: Guild | User | int,
        *,
        reason: Optional[str] = None,
    ) -> Message:
        """Blacklist a user or server from using the bot."""

        target_id = target.id if isinstance(target, (Guild, User)) else target

        query = "DELETE FROM blacklist WHERE target_id = $1"
        status = await self.bot.pool.execute(query, target_id)
        if status == "DELETE 1":
            return await ctx.approve(f"Now allowing `{target_id}` to use the bot")

        query = "INSERT INTO blacklist (target_id, reason) VALUES ($1, $2)"
        await self.bot.pool.execute(query, target_id, reason)
        async with ctx.typing():
            if isinstance(target, User):
                for guild in target.mutual_guilds:
                    if guild.owner_id == target.id:
                        await guild.leave()

            elif isinstance(target, Guild):
                await target.leave()

        return await ctx.warn(f"No longer allowing `{target}` to use the bot")

    @blacklist.command(name="view", aliases=("search", "info"))
    async def blacklist_view(self, ctx: Context, *, target: User | int) -> Message:
        """View the blacklist status of a user or server."""

        target_id = target.id if isinstance(target, User) else target
        query = "SELECT reason, created_at FROM blacklist WHERE target_id = $1"
        record = await self.bot.pool.fetchrow(query, target_id)
        if not record:
            return await ctx.send(f"`{target_id}` is not blacklisted")

        return await ctx.send(
            f"`{target_id}` was blacklisted on {format_dt(record['created_at'])}"
            + (f" for {record['reason']}" if record["reason"] else "")
        )

    @blacklist.command(name="list")
    async def blacklist_list(self, ctx: Context) -> Message:
        """View all blacklisted users and servers."""

        query = "SELECT * FROM blacklist"
        records = await self.bot.pool.fetch(query)
        if not records:
            return await ctx.send("No blacklisted users or servers")

        embed = Embed(title="Blacklist")
        entries: list[str] = []
        for record in records:
            target = self.bot.get_user(record["target_id"])
            entries.append(
                f"{target or f'`{record["target_id"]}'} {record['reason'] or ''} ({format_dt(record['created_at'])})"
            )

        return await Paginator(ctx, entries=entries, embed=embed)


async def setup(bot: Wock) -> None:
    await bot.add_cog(Developer(bot))
