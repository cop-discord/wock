from __future__ import annotations
from contextlib import suppress
from typing import TYPE_CHECKING, Optional
from cashews import cache
from discord import ClientException, Embed, Guild, HTTPException, Member, Message
from discord.opus import OpusNotLoaded
from discord.utils import escape_markdown
from wavelink.filters import Filters
from wavelink import Player as BasePlayer
from wavelink import Playable as Track

from yarl import URL
from system.utils import format_duration
from wock import Wock
from .panel import Panel

if TYPE_CHECKING:
    from .. import Context


class Player(BasePlayer):
    bot: Wock
    guild: Guild
    context: Context
    skip_votes: list[Member]
    controller: Optional[Message]
    synthesize: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inactive_timeout = 180
        self.bot = self.client
        self.skip_votes = []
        self.controller = None
        self.synthesize = False

    @property
    def dj(self) -> Member:
        return self.context.author
    
    @property
    def requester(self) -> Optional[Member]:
        track = self.current
        if not track:
            return
        
        return self.guild.get_member(getattr(track.extras, "requester_id") or 0)

    @classmethod
    async def from_context(cls, ctx: Context) -> Optional[Message]:
        if ctx.command.name in ("dialect", "preference"):
            return

        if not (voice := ctx.author.voice) or not voice.channel:
            return await ctx.warn("You are not connected to a voice channel")

        elif (bot_voice := ctx.guild.me.voice) and voice.channel != bot_voice.channel:
            return await ctx.warn("You are not connected to my voice channel")

        elif not bot_voice or not ctx.voice_client:
            if ctx.command.name not in ("speak", "play"):
                return await ctx.warn("I'm not connected to a voice channel")

        if ctx.voice_client:
            return

        try:
            player = await voice.channel.connect(
                cls=cls,
                self_deaf=True,
            )
            player.context = ctx
        except (TimeoutError, ClientException, OpusNotLoaded) as exc:
            return await ctx.warn(
                f"I was not able to connect to {voice.channel.mention}"
            )

    async def play(
        self,
        track: Track,
        *,
        replace: bool = True,
        start: int = 0,
        end: int | None = None,
        volume: int | None = None,
        paused: bool | None = None,
        add_history: bool = True,
        filters: Filters | None = None,
        populate: bool = False,
        max_populate: int = 5,
    ) -> Track:
        self.skip_votes.clear()
        if self.controller:
            with suppress(HTTPException):
                await self.controller.delete()

        return await super().play(
            track,
            replace=replace,
            start=start,
            end=end,
            volume=volume,
            paused=paused,
            add_history=add_history,
            filters=filters,
            populate=populate,
            max_populate=max_populate,
        )

    async def pause(self, value: bool) -> None:
        await super().pause(value)
        await self.refresh_panel()

    async def embed(self, track: Track) -> Embed:
        member = self.requester
        if track.source.startswith("youtube"):
            deserialized = await self.deserialize(track.title)
        else:
            deserialized = track.title

        source, source_icon = self.pretty_source(track)

        footer: list[str] = []
        if source:
            footer.append(source)

        footer.extend(
            [
                (f"Queued by {member.display_name}" if member else "Autoplay"),
                f"{format_duration(track.length)} Remaining",
            ]
        )
        embed = Embed(
            description=f"Now playing [**{escape_markdown(deserialized)}**]({track.uri}) by **{track.author}**"
        )
        embed.set_footer(
            text=" • ".join(footer),
            icon_url=source_icon or member and member.display_avatar,
        )
        return embed

    async def send_panel(self, track: Track) -> Optional[Message]:
        embed = await self.embed(track)

        with suppress(HTTPException):
            self.controller = await self.context.send(embed=embed, view=Panel(self))

    async def refresh_panel(self):
        if not self.controller:
            return

        with suppress(HTTPException):
            await self.controller.edit(view=Panel(self))

    def pretty_source(self, track: Track) -> tuple[str | None, str | None]:
        if track.source == "spotify":
            return (
                "Spotify",
                "https://cdn.discordapp.com/emojis/1307549140858961981.webp",
            )

        elif track.source == "applemusic":
            return (
                "Apple Music",
                "https://cdn.discordapp.com/emojis/1307549141307490376.webp",
            )

        elif track.source == "soundcloud":
            return (
                "SoundCloud",
                "https://cdn.discordapp.com/emojis/1307549138988171348.webp",
            )

        elif track.source.startswith("youtube"):
            return (
                "YouTube",
                "https://cdn.discordapp.com/emojis/1307549137977217045.webp",
            )

        return None, None

    @cache(ttl="30s")
    async def deserialize(self, query: str) -> str:
        response = await self.bot.session.post(
            URL.build(
                scheme="https",
                host="metadata-filter.vercel.app",
                path="/api/youtube",
                query={"track": query},
            ),
        )
        with suppress(Exception):
            data = await response.json()
            return data["data"]["track"]

        return query

    async def disconnect(self):
        with suppress(HTTPException):
            if self.controller:
                await self.controller.delete()

        return await super().disconnect()
