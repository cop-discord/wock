from contextlib import suppress
import asyncpg
import logging
import discord
import asyncio
import os

from typing import List, Optional, cast
from datetime import datetime

from discord import (
    Interaction,
    Message,
    AllowedMentions,
    Intents,
    ActivityType,
    TextChannel,
    VoiceChannel,
    Forbidden,
)
from discord.ext.commands import (
    AutoShardedBot,
    NotOwner,
    CheckFailure,
    CommandError,
    MissingRequiredArgument,
    ConversionError,
    MissingPermissions,
    CommandNotFound,
    BadColourArgument,
    RoleNotFound,
    ChannelNotFound,
    DisabledCommand,
    ThreadNotFound,
    BadUnionArgument,
    MissingRequiredAttachment,
    BadLiteralArgument,
    UserNotFound,
    MemberNotFound,
    GuildNotFound,
    BadInviteArgument,
    NoPrivateMessage,
    UserInputError,
    CommandOnCooldown,
)
from aiohttp import ClientSession
from wavelink import Node, Pool

from system.base import Help, Context

from cashews import cache

cache.setup("mem://")


class Wock(AutoShardedBot):
    pool: asyncpg.Pool
    session: ClientSession

    def __init__(self) -> None:
        super().__init__(
            command_prefix="-",
            strip_after_prefix=True,
            help_command=Help(),
            case_insensitive=True,
            intents=Intents.all(),
            allowed_mentions=AllowedMentions(
                everyone=False,
                users=True,
                roles=False,
                replied_user=False,
            ),
            activity=discord.Streaming(
                name="music and voice channel app",
                url="https://twitch.tv/wock",
                type=ActivityType.streaming,
            ),
            owner_ids=[474206995214368779, 1300970029730234418, 345462882902867969],
        )

    @property
    def node(self) -> Node:
        return Pool.get_node()

    async def load_cogs_from_dir(self, base_dir: str):
        for entry in os.scandir(base_dir):
            if entry.is_dir() and os.path.isfile(
                os.path.join(entry.path, "__init__.py")
            ):
                module_path = f"{base_dir}.{entry.name}"
                try:
                    await self.load_extension(module_path)
                    print(f"Successfully loaded cog: {module_path}")
                except Exception as e:
                    print(f"Failed to load cog {module_path}: {e}")

    async def setup_hook(self) -> None:
        self.session = ClientSession()
        self.tree.interaction_check = self.blacklist_check
        await self.load_extension("jishaku")
        await self.load_cogs_from_dir("extensions")

    async def is_blacklisted(self, target_ids: List[int]) -> bool:
        query = """
        SELECT EXISTS(
            SELECT 1
            FROM blacklist
            WHERE target_id = ANY($1::BIGINT[])
        )
        """
        return cast(bool, await self.pool.fetchval(query, target_ids))

    async def blacklist_check(self, interaction: Interaction) -> bool:
        blacklisted = await self.is_blacklisted(
            [interaction.guild_id, interaction.user.id]
        )
        if blacklisted:
            return await interaction.response.send_message(
                "You are blacklisted from using this bot", ephemeral=True
            )

        return True

    async def on_ready(self) -> None:
        logging.info("wock is now online")

    async def get_context(self, message: Message, *, cls=Context):
        return await super().get_context(message, cls=cls)

    async def process_commands(self, message: Message) -> None:
        if not message.guild or message.author.bot:
            return

        channel = message.channel
        if not (
            channel.permissions_for(message.guild.me).send_messages
            and channel.permissions_for(message.guild.me).embed_links
        ):
            return

        if await self.is_blacklisted([message.guild.id, message.author.id]):
            return

        return await super().process_commands(message)

    async def on_command_error(
        self,
        ctx: Context,
        exception: CommandError,
    ) -> Optional[Message]:
        raise exception
        if not (
            ctx.channel.permissions_for(ctx.guild.me).send_messages
            and ctx.channel.permissions_for(ctx.guild.me).embed_links
        ):
            return

        if isinstance(
            exception,
            (
                CommandNotFound,
                DisabledCommand,
                NotOwner,
            ),
        ):
            return

        elif isinstance(
            exception,
            (
                MissingRequiredArgument,
                MissingRequiredAttachment,
                BadLiteralArgument,
            ),
        ):
            return await ctx.send_help(ctx.command)

        elif isinstance(exception, TypeError):
            return await ctx.warn(str(exception))
        
        elif isinstance(exception, MissingRequiredArgument):
            return await ctx.send_help(ctx.command.qualified_name)
        
        elif isinstance(exception, ConversionError):
            return await ctx.warn(str(exception.original))
        
        elif isinstance(exception, MissingPermissions):
            return await ctx.warn(
                f"You're **missing** the required permission: **{' '.join([word.capitalize() for word in exception.missing_permissions[0].split('_')])}**"
            )
        
        elif isinstance(exception, BadColourArgument):
            return await ctx.warn("I was **unable** to find that **color**")
       
        elif isinstance(exception, RoleNotFound):
            return await ctx.warn(
                f"I was unable to find the role **{exception.argument}**"
            )
        
        elif isinstance(exception, ChannelNotFound):
            return await ctx.send(
                "The requested **channel** does not exist or could not be found"
            )
        
        elif isinstance(exception, ThreadNotFound):
            return await ctx.send(
                "The requested **thread** does not exist or could not be found"
            )
        
        elif isinstance(exception, BadUnionArgument):
            return await ctx.send(str(exception))
        
        elif isinstance(exception, UserNotFound):
            return await ctx.warn("The requested **user** could not be found")
        
        elif isinstance(exception, MemberNotFound):
            return await ctx.warn("The requested **member** could not be found")
        
        elif isinstance(exception, GuildNotFound):
            return await ctx.warn("The requested **guild** could not be found")
        
        elif isinstance(exception, BadInviteArgument):
            return await ctx.warn("The **invite code** you've provided is invalid")
        
        elif isinstance(exception, UserInputError):
            return await ctx.warn(str(exception))
        
        elif isinstance(exception, CommandOnCooldown):
            return await ctx.warn(
                f"Please wait **{exception.retry_after:.2f} seconds** before using any command again",
                delete_after=2,
            )
        
        elif isinstance(exception, Forbidden):
            return await ctx.warn(
                "**wock** did not has permission to fulfill this command. This could be due to role hierachy or channel permissions"
            )

        elif isinstance(exception, CommandError):
            if isinstance(exception, CheckFailure):
                origin = getattr(exception, "original", exception)
                with suppress(TypeError):
                    if any(
                        forbidden in origin.args[-1]
                        for forbidden in (
                            "global check",
                            "check functions",
                            "Unknown Channel",
                            "Us",
                        )
                    ):
                        return

            arguments: List[str] = []
            for argument in exception.args:
                if isinstance(argument, str):
                    arguments.append(argument)

                elif isinstance(argument, (TypeError, ValueError)):
                    arguments.extend(argument.args)

            if arguments:
                return await ctx.warn("\n".join(arguments).split("Error:")[-1])
        
        await ctx.warn("Something went wrong, please contact a developer")
        raise
    
    @property
    def members(self):
        return list(self.get_all_members())

    @property
    def channels(self):
        return list(self.get_all_channels())

    @property
    def text_channels(self):
        return list(
            filter(
                lambda channel: isinstance(channel, TextChannel),
                self.get_all_channels(),
            )
        )

    @property
    def voice_channels(self):
        return list(
            filter(
                lambda channel: isinstance(channel, VoiceChannel),
                self.get_all_channels(),
            )
        )

    @property
    def chunked_guilds(self) -> int:
        return len([g for g in self.guilds if g.chunked])

    @property
    def ping(self) -> int:
        return round(self.latency * 1000)

    @property
    def uptime(self) -> datetime:
        return datetime.now()

    @property
    def public_cogs(self) -> list:
        return [
            cog.qualified_name
            for cog in self.cogs.values()
            if cog.qualified_name not in ("Jishaku", "dev")
        ]
