from __future__ import annotations
import math
from typing import TYPE_CHECKING
from discord import Embed, Interaction, ButtonStyle, VoiceChannel
from discord.ui import View, button, Button
from wavelink import QueueEmpty, QueueMode
from config import Emojis
from system.utils import pluralize

if TYPE_CHECKING:
    from .. import Context
    from ..player import Player
    
def required_votes(command: str, channel: VoiceChannel):
    """Method which returns required votes based on amount of members in a channel."""

    required = math.ceil((len(channel.members) - 1) / 2.5)
    if command == "stop":
        if len(channel.members) == 3:
            required = 2

    return required or 1

class Panel(View):
    player: Player

    def __init__(self, player: Player):
        super().__init__(timeout=None)
        self.player = player

    @property
    def ctx(self) -> Context:
        return self.player.context

    def refresh(self) -> None:
        if self.player.paused:
            self.play.emoji = Emojis.Music.PAUSED
        else:
            self.play.emoji = Emojis.Music.UNPAUSED

        if self.player.queue.mode == QueueMode.loop_all:
            self.mode.emoji = Emojis.Music.LOOP_QUEUE
            self.mode.style = ButtonStyle.primary

        elif self.player.queue.mode == QueueMode.loop:
            self.mode.emoji = Emojis.Music.LOOP_TRACK
            self.mode.style = ButtonStyle.primary

        else:
            self.mode.emoji = Emojis.Music.NO_LOOP
            self.mode.style = ButtonStyle.secondary

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user not in self.player.channel.members:
            embed = Embed(
                description=f"{Emojis.Default.WARN} {interaction.user}: You must be in {self.player.channel.mention} to use this **panel**"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        return interaction.user in self.player.channel.members

    def is_privileged(self, interaction: Interaction):
        """Check whether the user is an Admin or DJ."""
        
        return (
            interaction.user in (self.player.dj, self.player.requester)
            or interaction.user.guild_permissions.kick_members
        )
    
    @button(emoji=Emojis.Music.SHUFFLE, style=ButtonStyle.secondary)
    async def shuffle(self, interaction: Interaction, _: Button) -> None:
        self.player.queue.shuffle()
        
        embed = Embed(description="Queue has been shuffled")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    @button(emoji=Emojis.Music.PREVIOUS, style=ButtonStyle.secondary)
    async def previous(self, interaction: Interaction, _: Button) -> None:
        empty_embed = Embed(description="No previous track to play")

        if not self.player.queue.history or len(self.player.queue.history) == 0:
            return await interaction.response.send_message(embed=empty_embed, ephemeral=True)

        try:
            track = self.player.queue.history.get()
        except QueueEmpty:
            return await interaction.response.send_message(embed=empty_embed, ephemeral=True)

        self.player.queue.put_at(0, track)
        await self.player.stop()

        embed = Embed(description=f"{interaction.user.mention} started the previous track")
        return await interaction.response.send_message(embed=embed, delete_after=4)

    @button(emoji=Emojis.Music.UNPAUSED, style=ButtonStyle.primary)
    async def play(self, interaction: Interaction, button: Button) -> None:
        await self.player.pause(not self.player.paused)
        button.emoji = (
            self.player.paused and Emojis.Music.PAUSED or Emojis.Music.UNPAUSED
        )

        embed = Embed(description=f"{interaction.user.mention} has {'paused' if self.player.paused else 'resumed'} the current track")
        await interaction.response.send_message(embed=embed, delete_after=4)
        return await self.player.controller.edit(view=self)
    
    @button(emoji=Emojis.Music.SKIP, style=ButtonStyle.secondary)
    async def skip(self, interaction: Interaction, _: Button) -> None:
        if self.player.queue.mode == QueueMode.loop:
            embed = Embed(description="Cannot skip track while looping track")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif not self.player.current:
            embed = Embed(description="There isn't a track being played")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        votes = self.player.skip_votes
        required = required_votes("skip", self.player.channel)
        if interaction.user in votes:
            embed = Embed(description="You have already voted to skip this track")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        votes.append(interaction.user)
        if self.is_privileged(interaction) or len(votes) >= required:
            votes.clear()
            await self.player.skip(force=True)
            embed = Embed(description=f"{interaction.user.mention} has skipped the current track")
            return await interaction.response.send_message(embed=embed, delete_after=4)
        
        
        embed = Embed(description=f"{interaction.user.mention} has voted to skip the current track (`{len(votes)}`/`{required}` required)")
        return await interaction.response.send_message(embed=embed)

    @button(emoji=Emojis.Music.NO_LOOP, style=ButtonStyle.secondary)
    async def mode(self, interaction: Interaction, button: Button) -> None:
        queue = self.player.queue

        if queue.mode == QueueMode.loop_all:
            queue.mode = QueueMode.loop
            button.emoji = Emojis.Music.LOOP_TRACK
            button.style = ButtonStyle.primary
        elif queue.mode == QueueMode.loop:
            queue.mode = QueueMode.normal
            button.emoji = Emojis.Music.NO_LOOP
            button.style = ButtonStyle.secondary
        else:
            queue.mode = QueueMode.loop_all
            button.emoji = Emojis.Music.LOOP_QUEUE
            button.style = ButtonStyle.primary

        return await interaction.response.edit_message(view=self)

