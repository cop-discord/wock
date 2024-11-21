from typing import TYPE_CHECKING
from discord.ext.commands import Cog

if TYPE_CHECKING:
    from wock import Wock


class CogMeta(Cog):
    bot: "Wock"

    def __init__(self, bot: "Wock") -> None:
        self.bot = bot
        super().__init__()
