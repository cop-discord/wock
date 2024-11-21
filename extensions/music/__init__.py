from contextlib import suppress
import math
from typing import Literal, Optional, Union, cast


from wavelink import QueueMode, TrackEndEventPayload, TrackStartEventPayload

from system.pagination import Paginator
from system.base import Context as BaseContext

from .player import Player, Panel
from discord import HTTPException, Message, Attachment, VoiceChannel
from discord.ext.commands import Cog, hybrid_group, hybrid_command, command

from wavelink import (
    Playable as Track,
    TrackSource,
    Search,
    LavalinkLoadException,
    Playlist,
    Pool,
    Node,
)
from system.utils import format_duration, pluralize
from wock import Wock


class Context(BaseContext):
    voice_client: Player

def required_votes(command: str, channel: VoiceChannel):
    """Method which returns required votes based on amount of members in a channel."""

    required = math.ceil((len(channel.members) - 1) / 2.5)
    if command == "stop":
        if len(channel.members) == 3:
            required = 2

    return required or 1
    
class Music(Cog):
    def __init__(self, bot: Wock):
        self.bot = bot

    async def cog_load(self) -> None:
        nodes = [
            Node(
                uri=f"http://127.0.0.1:1337",
                password="youshallnotpass",
                resume_timeout=180,
            )
        ]

        await Pool.connect(nodes=nodes, client=self.bot)

    async def cog_check(self, ctx: Context) -> None:
        c = await Player.from_context(ctx)
        return not isinstance(c, Message)

        
    @Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload):
        client = cast(Player, payload.player)
        if not client:
            return

        if client.queue:
            await client.play(client.queue.get())

    def is_privileged(self, ctx: Context):
        """Check whether the user is an Admin or DJ."""

        return (
            ctx.author in (ctx.voice_client.dj, ctx.voice_client.requester)
            or ctx.author.guild_permissions.kick_members
        )

    @Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload) -> None:
        client = cast(Player, payload.player)
        track = payload.track

        if not client:
            return

        if client.context and track.source != "local":
            with suppress(HTTPException):
                await client.send_panel(track)

    @hybrid_command(aliases=("p",))
    async def play(
        self,
        ctx: Context,
        *,
        query: Optional[str] = None,
        file: Optional[Attachment] = None,
    ) -> Optional[Message]:
        """Play the requested song in your current voice channel.
        Usage:
        /play <song name>
        /play <file attachment>
        """

        tts = query.startswith("tts:") if query else False
        if query:
            query = query.replace("tts:", "/tmp/wock/")

        elif ctx.message.attachments:
            file = ctx.message.attachments[0]

        if file and not query:
            query = file.url

        if not query and not file:
            return await ctx.warn(
                "Please provide a song name or attach a valid audio file."
            )

        result: Optional[Search] = None
        with suppress(LavalinkLoadException):
            result = await Track.search(
                query,
                source=TrackSource.YouTube if not tts else "",  # type: ignore
            )

        if not result:
            return await ctx.warn(f"Couldn't find any results for **{query}**")

        if isinstance(result, Playlist):
            for track in result.tracks:
                track.extras = {"requester_id": ctx.author.id}

            await ctx.voice_client.queue.put_wait(result)
            await ctx.approve(
                f"-# *Added [**{result.name}**]({result.url}) with {len(result.tracks)} {pluralize('track', len(result.tracks))} to the queue*"
            )
        else:
            track = result[0]
            track.extras = {"requester_id": ctx.author.id}
            if tts:
                ctx.voice_client.synthesize = True
                ctx.voice_client.queue.put_at(0, track)
            else:
                await ctx.voice_client.queue.put_wait(track)

            if track.source != "local":
                await ctx.approve(
                    f"-# *Queued [**{track.title}**]({track.uri}) by **{track.author}***",
                )

        if not ctx.voice_client.playing:
            await ctx.voice_client.play(ctx.voice_client.queue.get())

    @hybrid_command(aliases=("stop", "dc"))
    async def disconnect(self, ctx: Context) -> Message:
        """Stop the player and clear the queue."""

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to stop the player")

        await ctx.voice_client.disconnect()
        return await ctx.approve("Stopped the **player** and cleared the **queue**")

    @hybrid_command()
    async def skip(self, ctx: Context) -> Message:
        """Skip the current track."""

        if ctx.voice_client.queue.mode == QueueMode.loop:
            return await ctx.warn("Cannot skip track while looping track")
        
        elif not ctx.voice_client.current:
            return await ctx.warn("There isn't a track being played")

        votes = ctx.voice_client.skip_votes
        required = required_votes("skip", ctx.voice_client.channel)
        if ctx.author in votes:
            return await ctx.warn("You have already voted to skip this track")

        votes.append(ctx.author)
        if self.is_privileged(ctx) or len(votes) >= required:
            votes.clear()
            await ctx.voice_client.skip(force=True)
            return await ctx.approve("-# *Skipping to the next track*")

        return await ctx.approve(
            f"{ctx.author.mention} has voted to skip the current track (`{len(votes)}`/`{required}` required)"
        )

    @hybrid_command(aliases=("vol", "v"))
    async def volume(self, ctx: Context, volume: int) -> Message:
        """Change the volume of the player."""

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to change the volume")

        if not 0 <= volume <= 100:
            return await ctx.warn("Volume must be between 0 and 100")

        await ctx.voice_client.set_volume(volume)
        return await ctx.approve(f"Set volume to **{volume}%**")

    @hybrid_command()
    async def pause(self, ctx: Context) -> Message:
        """Pause the current track."""

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to pause the player")
        
        elif not ctx.voice_client.playing:
            return await ctx.warn("There isn't a track being played")
        
        await ctx.voice_client.pause(True)
        return await ctx.approve("Paused the player")

    @hybrid_command()
    async def resume(self, ctx: Context) -> Message:
        """Resume the current track."""

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to resume the player")
        
        elif not ctx.voice_client.paused:
            return await ctx.warn("The player is not paused")
        
        await ctx.voice_client.pause(False)
        return await ctx.approve("Resumed the player")

    @hybrid_command()
    async def shuffle(self, ctx: Context) -> Message:
        """Shuffle the queue."""

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to shuffle the queue")
        
        elif not ctx.voice_client.queue:
            return await ctx.warn("There are no tracks in the queue to shuffle")

        ctx.voice_client.queue.shuffle()
        return await ctx.approve("Shuffled the queue")

    @hybrid_command(aliases=("loop",))
    async def repeat(
        self,
        ctx: Context,
        option: Literal["queue", "track", "off"],
    ) -> Message:
        """Set the loop mode of the player."""

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to change the loop mode")

        if option == "track":
            ctx.voice_client.queue.mode = QueueMode.loop

        elif option == "queue":
            ctx.voice_client.queue.mode = QueueMode.loop_all

        else:
            ctx.voice_client.queue.mode = QueueMode.normal

        await ctx.voice_client.refresh_panel()
        return await ctx.approve(f"Set loop mode to **{option}**")

    @hybrid_command(aliases=("np",))
    async def nowplaying(self, ctx: Context) -> Message:
        """View the current track."""

        if not (track := ctx.voice_client.current):
            return await ctx.warn("There isn't a track being played")

        embed = await ctx.voice_client.embed(track)
        return await ctx.reply(embed=embed, view=Panel(self))

    @hybrid_group(invoke_without_command=True)
    async def queue(self, ctx: Context) -> Union[Message, Paginator]:
        """View all tracks in the queue."""

        if not (tracks := ctx.voice_client.queue):
            return await ctx.warn("There are no tracks in the queue")

        return await Paginator(
            ctx=ctx,
            entries=[
                f"**{index + 1}.** [{track.title}]({track.uri}) by **{track.author}** {f'[{requester.mention}]'}"
                for index, track in enumerate(tracks)
                if (
                    requester := ctx.guild.get_member(
                        getattr(track.extras, "requester_id") or 0
                    )
                )
            ],
            embed=ctx.create(
                title="Queue",
                footer={
                    "text": f"{len(tracks)} {pluralize('track', len(tracks))} • {format_duration(sum(track.length for track in tracks))}",
                },
            )["embed"],
        )

    @queue.command(name="view", with_app_command=True)
    async def queue_view(self, ctx: Context) -> Union[Message, Paginator]:
        """Alias for the `queue` command."""

        return await self.queue(ctx)

    @queue.command(name="clear", aliases=("empty",))
    async def queue_clear(self, ctx: Context) -> Message:
        """Remove all tracks from the queue."""

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to clear the queue")

        ctx.voice_client.queue.clear()
        return await ctx.approve("Cleared the queue")

    @queue.command(name="remove")
    async def queue_remove(self, ctx: Context, index: int) -> Message:
        """Remove a track from the queue."""

        if not self.is_privileged(ctx):
            return await ctx.warn(
                "You do not have permission to remove tracks from the queue."
            )

        if not (track := ctx.voice_client.queue[index]):
            return await ctx.warn(f"Track at index **{index}** doesn't exist")

        ctx.voice_client.queue.remove(track)
        return await ctx.approve(f"Removed **{track.title}** from the queue")

    @queue.command(name="move")
    async def queue_move(
        self, ctx: Context, position: int, new_position: int,
    ) -> Message:
        """Move a track in the queue to a new index."""

        if not self.is_privileged(ctx):
            return await ctx.warn(
                "You do not have permission to move tracks in the queue."
            )

        queue = ctx.voice_client.queue
        if not queue:
            return await ctx.warn("No tracks are in the queue")

        elif not 0 < position <= len(queue):
            return await ctx.warn(
                f"Invalid position - must be between `1` and `{len(queue)}`"
            )

        elif not 0 < new_position <= len(queue):
            return await ctx.warn(
                f"Invalid new position - must be between `1` and `{len(queue)}`"
            )

        track = queue[position - 1]
        queue.remove(track)
        queue.put_at(new_position - 1, track)
        return await ctx.approve(
            f"Moved [**{track.title}**]({track.uri}) to `{new_position}` in the queue"
        )
    
    @command(aliases=("remv", "rmv"), hidden=True)
    async def remove(self, ctx: Context, index: int) -> Message:
        """Remove a track from the queue."""

        return await self.queue_remove(ctx, index=index)
    
    @command(aliases=("mv",), hidden=True)
    async def move(self, ctx: Context, position: int, new_position: int) -> Message:
        """Move a track in the queue to a new index."""

        return await self.queue_move(ctx, position=position, new_position=new_position)
    
    # @hybrid_group(name="preset")
    # async def preset(self, ctx: Context) -> Optional[Message]:
    #     """Apply a preset to the player."""

    #     return await ctx.group()

    # @preset.command(name="vaporwave")
    # async def preset_vaporwave(self, ctx: Context) -> Message:
    #     """
    #     Timescale preset which slows down the currently playing track,
    #     matching up to vaporwave, a slowed-down genre of music.
    #     """

    #     await ctx.voice_client.reset_filters()
    #     await ctx.voice_client.add_filter(Timescale.vaporwave())
    #     return await ctx.approve("Set preset to **Vaporwave**")

    # @preset.command(name="nightcore")
    # async def preset_nightcore(self, ctx: Context) -> Message:
    #     """
    #     Timescale preset which speeds up the currently playing track,
    #     matching up to nightcore, a genre of sped-up music.
    #     """

    #     await ctx.voice_client.reset_filters()
    #     await ctx.voice_client.add_filter(Timescale.nightcore())
    #     return await ctx.approve("Set preset to **Nightcore**")

    # @preset.command(name="remove")
    # async def preset_remove(self, ctx: Context) -> Message:
    #     """Remove all filters from the player."""

    #     await ctx.voice_client.reset_filters()
    #     return await ctx.approve("Removed all filters from the player")


async def setup(bot: Wock) -> None:
    await bot.add_cog(Music(bot))
