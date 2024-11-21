import math

from contextlib import suppress
from discord import Embed, HTTPException, Interaction, Message, ButtonStyle, TextStyle
from discord.ui import TextInput, Modal


from typing import TYPE_CHECKING, Any, List, Optional, Self, Union

from discord.ui.item import Item

from config import Emojis

from system.utils import View, Button

if TYPE_CHECKING:
    from system.base import Context


class Paginator(View):
    """
    Paginator View, used to paginate a list of strings, or embeds.
    """

    entries: Union[List[str], List[Embed]]
    message: Message
    current: int = 0

    def __init__(
        self,
        ctx: "Context",
        entries: List[str],
        embed: Optional[Embed] = None,
        beginning: Optional[Embed] = None,
        timeout: int = 60,
        split: int = 10,
        fields: bool = False,
    ):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.embed = embed
        self.beginning = beginning
        self.split = split
        self.fields = fields
        self.entries = self.format_pages(entries)

        self.add_item(
            Button(
                style=ButtonStyle.primary,
                emoji=Emojis.Paginator.PREVIOUS,
                custom_id="previous",
            )
        )

        self.add_item(
            Button(
                style=ButtonStyle.primary,
                emoji=Emojis.Paginator.NEXT,
                custom_id="next",
            )
        )

        self.add_item(
            Button(
                style=ButtonStyle.secondary,
                emoji=Emojis.Paginator.PAGES,
                custom_id="pages",
            )
        )

        self.add_item(
            Button(
                style=ButtonStyle.red,
                emoji=Emojis.Paginator.EXIT,
                custom_id="cancel",
            )
        )

    async def __new__(cls, *args, **kwargs) -> Self:
        paginator = super().__new__(cls)
        paginator.__init__(*args, **kwargs)
        await paginator.send_message()
        return paginator

    async def send_message(self) -> None:
        self.message = (
            await self.ctx.send(
                content=self.entries[0],
                view=len(self.entries) == 1 and None or self,
            )
            if isinstance(self.entries[0], str)
            else await self.ctx.send(
                embed=self.beginning or self.entries[0],
                view=len(self.entries) == 1 and None or self,
            )
        )

    async def callback(self, interaction: Interaction, button: Button):
        """
        Callback for the paginator buttons.
        """

        if button.custom_id == "previous":
            return await self.previous(interaction)
        elif button.custom_id == "next":
            return await self.next(interaction)
        elif button.custom_id == "pages":
            return await self.pages(interaction)
        elif button.custom_id == "cancel":
            return await self.cancel(interaction)

    async def previous(self, interaction: Interaction):
        if self.current == 0:
            self.current = len(self.entries) - 1
        else:
            self.current -= 1
        await interaction.response.defer()
        return await self.update_message()

    async def next(self, interaction: Interaction):
        if self.current == len(self.entries) - 1:
            self.current = 0
        else:
            self.current += 1
        await interaction.response.defer()
        return await self.update_message()

    async def cancel(self, interaction: Interaction):
        await interaction.response.defer()
        self.stop()
        return await self.message.delete()

    async def pages(self, interaction: Interaction):
        """
        Open a modal to select a page.
        """
        return await interaction.response.send_modal(PagesModal(self))

    async def update_message(self):
        """
        Update the message with the current page.
        """

        content = self.entries[self.current]
        if isinstance(content, Embed):
            return await self.message.edit(embed=content)
        else:
            return await self.message.edit(content=content)

    def format_pages(self, entries: List[str]) -> Union[List[str], List[Embed]]:
        """
        Automatically paginate a list of strings into embeds
        """

        if not self.embed:
            return entries

        embed = self.embed

        embeds = [
            Embed(
                title=embed.title,
                color=embed.color,
                description="\n".join(chunk),
                timestamp=embed.timestamp,
            )
            .set_author(
                name=getattr(embed.author, "name", None),
                icon_url=getattr(embed.author, "icon_url", None),
            )
            .set_thumbnail(url=getattr(embed.thumbnail, "url", None))
            .set_image(url=getattr(embed.image, "url", None))
            .set_footer(
                text=f"Page {index + 1}/{math.ceil(len(entries) / self.split)} ({len(entries)} Entries) {getattr(embed.footer, 'text', None) and f'• {embed.footer.text}'}",
                icon_url=getattr(embed.footer, "icon_url", None),
            )
            for index, chunk in enumerate(
                [
                    entries[index : index + self.split]
                    for index in range(0, len(entries), self.split)
                ]
            )
        ]

        if self.beginning:
            embeds.insert(0, self.beginning)

        return embeds

    async def on_timeout(self) -> None:
        with suppress(HTTPException):
            await self.message.delete()
        return await super().on_timeout()

    async def on_error(self, _: Interaction, __: Exception, ___: Item[Any]) -> None: ...


class PagesModal(Modal, title="Select Page"):
    """
    PagesModal class to select a page.
    """

    def __init__(self, view: Paginator):
        super().__init__()
        self.view = view
        self.selector = TextInput(
            label="Page",
            placeholder="5",
            custom_id="pages",
            style=TextStyle.short,
            min_length=1,
            max_length=3,
            required=True,
            row=0,
        )
        self.add_item(self.selector)

    async def on_submit(self, interaction: Interaction):
        try:
            page = int(self.selector.value)
        except ValueError:
            return await interaction.response.send_message(
                "Please provide a valid page number", ephemeral=True
            )
        if page < 1 or page > len(self.view.entries):
            return await interaction.response.send_message(
                "Please provide a valid page number", ephemeral=True
            )
        self.view.current = page - 1

        if isinstance(self.view.entries[self.view.current], Embed):
            return await interaction.response.edit_message(
                embed=self.view.entries[self.view.current]  # type: ignore
            )

        return await interaction.response.edit_message(
            content=self.view.entries[self.view.current]
        )
