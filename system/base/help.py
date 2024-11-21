from typing import Any

from discord.ext.commands import MinimalHelpCommand


class Help(MinimalHelpCommand):
    def __init__(self, **options: Any) -> None:
        options["command_attrs"] = {"hidden": True, "aliases": ["h", "cmds"]}
        super().__init__(**options, verify_checks=False)

    # async def send_bot_help(self, mapping: Mapping[Optional[Any], List[Any]]) -> None:
    #     pass
