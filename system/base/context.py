from __future__ import annotations

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TYPE_CHECKING,
    Self,
    Tuple,
    Unpack,
    TypedDict,
    cast,
)

from discord import (
    AllowedMentions,
    ButtonStyle,
    Color,
    Guild,
    Member,
    Message,
    MessageReference,
    Role,
)
import discord
from discord.ui import View, Button
from discord.ext.commands import Context as BaseContext
from discord.ext.commands import CommandError
from discord.ext.commands.core import Command

from system.utils import hierachy, manageable

if TYPE_CHECKING:
    from wock import Wock


class MessageKwargs(TypedDict, total=False):
    content: Optional[str]
    tts: Optional[bool]
    allowed_mentions: Optional[AllowedMentions]
    reference: Optional[MessageReference]
    mention_author: Optional[bool]
    delete_after: Optional[float]

    # Embed Related
    url: Optional[str]
    title: Optional[str]
    color: Optional[Color]
    image: Optional[str]
    description: Optional[str]
    thumbnail: Optional[str]
    footer: Optional[FooterDict]
    author: Optional[AuthorDict]
    fields: Optional[List[FieldDict]]
    timestamp: Optional[datetime]
    view: Optional[View]
    buttons: Optional[List[ButtonDict]]


class FieldDict(TypedDict, total=False):
    name: str
    value: str
    inline: bool


class FooterDict(TypedDict, total=False):
    text: Optional[str]
    icon_url: Optional[str]


class AuthorDict(TypedDict, total=False):
    name: Optional[str]
    icon_url: Optional[str]


class ButtonDict(TypedDict, total=False):
    url: Optional[str]
    emoji: Optional[str]
    style: Optional[ButtonStyle]
    label: Optional[str]


def get_index(iterable: Optional[Tuple[Any, Any]], index: int) -> Optional[Any]:
    if not iterable or (type(iterable) is not tuple and index != 0):
        return None

    if type(iterable) is not tuple and index == 0:
        return iterable

    return iterable[index] if len(iterable) > index else None


class Context(BaseContext):
    bot: "Wock"
    guild: Guild  # type: ignore
    author: Member
    command: Command

    async def manage(self, role: Role) -> None:
        """Check if the role is manageable by the author or the bot."""
        if manageable(role, self) and hierachy(role, self):
            return

        raise CommandError(f"{role} is not **manageable** by either yourself or me.")

    async def group(self) -> Optional[Message]:
        if not self.invoked_subcommand:
            return await self.send_help(self.command)
        return

    async def embed(self, **kwargs: Unpack[MessageKwargs]) -> Message:
        return await self.send(**self.create(**kwargs))

    def create(self, **kwargs: Unpack[MessageKwargs]) -> Dict[str, Any]:
        """Create a message with the given keword arguments.

        Returns:
            Dict[str, Any]: The message content, embed, view and delete_after.
        """
        view = View()

        for button in kwargs.get("buttons") or []:
            if not button or not button.get("label"):
                continue

            view.add_item(
                Button(
                    label=button.get("label"),
                    style=button.get("style") or ButtonStyle.secondary,
                    emoji=button.get("emoji"),
                    url=button.get("url"),
                )
            )

        embed = (
            Embed(
                url=kwargs.get("url"),
                description=kwargs.get("description"),
                title=kwargs.get("title"),
                color=kwargs.get("color") or Color.dark_embed(),
                timestamp=kwargs.get("timestamp"),
            )
            .set_image(url=kwargs.get("image"))
            .set_thumbnail(url=kwargs.get("thumbnail"))
            .set_footer(
                text=cast(dict, kwargs.get("footer", {})).get("text"),
                icon_url=cast(dict, kwargs.get("footer", {})).get("icon_url"),
            )
            .set_author(
                name=cast(dict, kwargs.get("author", {})).get("name", ""),
                icon_url=cast(dict, kwargs.get("author", {})).get("icon_url", ""),
            )
        )

        for field in kwargs.get("fields") or []:
            if not field:
                continue

            embed.add_field(
                name=field.get("name"),
                value=field.get("value"),
                inline=field.get("inline", False),
            )

        return {
            "content": kwargs.get("content"),
            "embed": embed,
            "view": kwargs.get("view") or view,
            "delete_after": kwargs.get("delete_after"),
        }

    async def approve(self, message: str, **kwargs: Unpack[MessageKwargs]) -> Message:
        kwargs["description"] = (
            f"{message}"
        )
        return await self.embed(
            **kwargs,
        )

    async def warn(self, message: str, **kwargs: Unpack[MessageKwargs]) -> Message:
        kwargs["description"] = (
            f"{message}"
        )
        return await self.embed(
            **kwargs,
        )

    async def deny(self, message: str, **kwargs: Unpack[MessageKwargs]) -> Message:
        kwargs["description"] = (
            f"{message}"
        )
        return await self.embed(
            **kwargs,
        )


class Embed(discord.Embed):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.color in (None, Color.default()):
            self.color = Color.dark_embed()
            
    def add_field(self, *, name: Any, value: Any, inline: bool = True) -> Self:
        return super().add_field(name=f"**{name}**", value=value, inline=inline)

discord.Embed = Embed
