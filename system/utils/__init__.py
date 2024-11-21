from __future__ import annotations

from typing import Any, Union, List, TYPE_CHECKING

from discord import Interaction, Member, Role

from discord.ui import Button as OriginalButton
from discord.ui import View as OriginalView

from config import Emojis

if TYPE_CHECKING:
    from system.base import Context


def shorten(texts: Union[str, List[str]], length: int = 2000) -> str:
    """
    Shorten a string or a shortened list that appends '...' at the end if it exceeds the length.
    Return the shortened string or a comma-seperated list of strings shortened to a max length of a specified length.
    """
    if isinstance(texts, str):
        return texts if len(texts) <= length else texts[:length] + "..."
    elif isinstance(texts, list):
        if len(texts) <= length:
            return conjoin(texts)
        else:
            return conjoin(texts) + "..."

    raise TypeError("Input must be a string or a list of strings")


def concatenate(*texts: str, seperator: str = "\n") -> str:
    """
    Concatenate a list of strings with a provided separator.
    """
    return seperator.join(texts)


def conjoin(texts: List[str]) -> str:
    """
    Joins a list of strings with commas, and adds 'and' before the last item.

    Args:
        texts (List[str]): A list of strings to join.

    Returns:
        str: The formatted string with commas and 'and' before the last element.
    """
    return ", ".join(texts[:-1]) + (" and " + texts[-1] if len(texts) > 1 else texts[0])


def pluralize(text: str, count: int) -> str:
    """
    Pluralize a string based on the count.

    Args:
        text (str): The string to pluralize.
        count (int): The count to determine if the string should be pluralized.

    Returns:
        str: The pluralized string.
    """
    return text + ("s" if count != 1 else "")


def hierachy(role: Role, ctx: "Context") -> bool:
    """Check if the role is below the author's top role and the bot's top role.

    Args:
        role (Role): The role to check.
        ctx (Context): The context to check.

    Returns:
        bool: True if the role is below the author's top role and the bot's top role.
    """
    assert isinstance(ctx.author, Member), "Guild must be a guild"

    return (
        role.position < ctx.author.top_role.position
        or ctx.guild.owner_id == ctx.author.id
    ) and role.position < ctx.guild.me.top_role.position


def manageable(role: Role, ctx: "Context") -> bool:
    """Check if the role is the default guild role, or managed"""
    assert isinstance(ctx.author, Member), "Guild must be a guild"

    return not (role.managed or role == ctx.guild.default_role)


def format_duration(time_input: Union[int, float], is_milliseconds: bool = True) -> str:
    """
    Convert a given duration (in seconds or milliseconds) into a formatted duration string.

    Args:
        time_input (Union[int, float]): The total duration, either in seconds or milliseconds.
        is_milliseconds (bool): Specifies if the input is in milliseconds (default is True).

    Returns:
        str: The formatted duration in hours, minutes, seconds, and milliseconds.
    """
    if is_milliseconds:
        total_seconds = time_input / 1000
    else:
        total_seconds = time_input

    seconds = int(total_seconds)

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"


class View(OriginalView):
    ctx: "Context"

    async def callback(self, interaction: Interaction, button: Button):
        raise NotImplementedError

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Check if the interaction is from the author of the embed.
        """

        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                **self.ctx.create(
                    description=f"{Emojis.Default.WARN} {interaction.user}: You're not the **author** of this embed!"
                ),
                ephemeral=True,
            )
        return interaction.user.id == self.ctx.author.id


class Button(OriginalButton):
    view: View  # type: ignore

    async def callback(self, interaction: Interaction) -> Any:
        return await self.view.callback(interaction, self)
