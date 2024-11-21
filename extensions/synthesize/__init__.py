from contextlib import suppress
from copy import copy
from typing import Optional, cast
from discord import Member, Message
from discord.ext.commands import (
    Cog,
    Author,
    hybrid_command,
    cooldown,
    BucketType,
    CooldownMapping,
)
from discord.app_commands import describe, choices, Choice
from discord.utils import escape_markdown
from extensions.music import Context as MusicContext, Player
from wock import Wock, Context
from start import cache
from .shared import escape_text, has_excessive_repetition, is_spam, synthesize
from .shared.constants import replace_slang, SUPPORTED_LANGUAGES, SUPPORTED_ACCENTS


class Synthesize(Cog):
    def __init__(self, bot: Wock) -> None:
        self.bot = bot
        self._speak_cooldown = CooldownMapping.from_cooldown(2, 6, BucketType.user)

    async def cog_check(self, ctx: MusicContext) -> None:
        c = await Player.from_context(ctx)
        return not isinstance(c, Message)

    @Cog.listener("on_message")
    async def speak_channel(self, message: Message):
        """Automatically synthesize text from a voice channel."""

        if message.author.bot or not message.clean_content:
            return

        ctx = cast(Optional[MusicContext], await self.bot.get_context(message))
        if not ctx or ctx.command:
            return

        if not ctx.voice_client or message.channel != ctx.voice_client.channel:
            return

        if not ctx.voice_client.synthesize:
            return

        bucket = self._speak_cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return

        await self.speak(ctx, text="i:" + message.clean_content[:100])

    @hybrid_command(aliases=("tts",))
    @cooldown(3, 7, BucketType.user)
    async def speak(self, ctx: MusicContext, *, text: str) -> Optional[Message]:
        """Synthesize text into speech in the voice channel."""

        from_event = "i:" in text
        if from_event:
            text = text[2:]

        text = escape_text(replace_slang(text))
        if is_spam(text):
            return await ctx.reply("fuck off idiot")
        
        elif not text:
            return

        track = ctx.voice_client.current
        if ctx.voice_client.playing and track and track.source != "local":
            if from_event:
                return

            return await ctx.warn(
                "Another user is currently using the [music player](https://wock.app)\n"
                "-# tip: *Only one user can use this wock at a time*"
            )

        command = self.bot.get_command("play")
        if not command:
            return await ctx.warn(
                "This command isn't available right now, please try again later"
            )

        elif await self.bot.is_blacklisted([ctx.author.id]):
            return

        query = """
        SELECT language, accent
        FROM tts_preferences
        WHERE user_id = $1;
        """
        record = await self.bot.pool.fetchrow(query, ctx.author.id)
        language: str = "en"
        accent: str = "us"
        if record:
            language, accent = record["language"], record["accent"]

        buffer = await synthesize(text, language, accent)
        file = cache / f"tts{ctx.author.id}.mp3"
        await file.write_bytes(buffer.getbuffer())

        await command(ctx, query=f"tts:{file.name}")
        if from_event:
            return await ctx.message.add_reaction("🗣")

        return await ctx.approve(
            "Synthesizing text into speech...\n"
            f"-# important: *Messages sent in {ctx.voice_client.channel.mention} will now be [synthesized](https://wock.app)*"
        )

    @hybrid_command()
    @describe(
        language="Choose your preferred language",
        accent="Choose your preferred accent",
    )
    @choices(
        language=[
            Choice(name=name, value=short_code)
            for short_code, name in SUPPORTED_LANGUAGES.items()
        ],
        accent=[
            Choice(name=name, value=short_code)
            for short_code, name in SUPPORTED_ACCENTS.items()
        ],
    )
    async def dialect(
        self,
        ctx: Context,
        language: Choice[str],
        accent: Choice[str],
    ) -> None:
        """Set your TTS language and accent preferences."""

        language_code, accent_code = language.value, accent.value

        query = """
        INSERT INTO tts_preferences (
            user_id,
            language,
            accent
        ) VALUES ($1, $2, $3)
        ON CONFLICT (user_id)
        DO UPDATE SET
            language = EXCLUDED.language,
            accent = EXCLUDED.accent;
        """
        await self.bot.pool.execute(
            query,
            ctx.author.id,
            language_code,
            accent_code,
        )

        await ctx.approve(
            f"Your **language** has been set to `{SUPPORTED_LANGUAGES[language_code]}` "
            f"and your **accent** to `{SUPPORTED_ACCENTS[accent_code]}`.\n"
            "-# tip: *You can reset your [dialect](https://wock.app) with `/reset`*"
        )

    @hybrid_command(name="reset")
    async def dialect_reset(self, ctx: Context) -> Message:
        """Reset your TTS language and accent preferences."""

        query = """
        INSERT INTO tts_preferences (
            user_id,
            language,
            accent
        ) VALUES ($1, 'en', 'us')
        ON CONFLICT (user_id)
        DO UPDATE SET
            language = EXCLUDED.language,
            accent = EXCLUDED.accent;
        """
        await self.bot.pool.execute(query, ctx.author.id)

        return await ctx.approve(
            "Your **language** has been reset to `English` and your **accent** to `United States`.\n"
            "-# tip: *You can set it again using [/dialect](https://wock.app)*"
        )

    @hybrid_command(aliases=("personality",))
    async def preference(self, ctx: Context, user: Member = Author) -> Message:
        """View your TTS language and accent preferences."""

        query = """
        SELECT language, accent
        FROM tts_preferences
        WHERE user_id = $1;
        """
        record = await self.bot.pool.fetchrow(query, user.id)
        if not record:
            return await ctx.warn(
                f"{user.mention} has not set any **dialect preferences** yet"
                "\n*use the [dialect](<https://wock.app>) command to set your preference!*"
            )

        language = SUPPORTED_LANGUAGES.get(record["language"], "Unknown")
        accent = SUPPORTED_ACCENTS.get(record["accent"], "Unknown")
        return await ctx.approve(
            f"Speech Preferences for {user.mention}"
            f"\n**Language:** `{language}`"
            f"\n**Accent:** `{accent}`"
            "\n-# *You can use `/dialect reset` to reset your [preferences](<https://wock.app>)*"
        )


async def setup(bot: Wock) -> None:
    await bot.add_cog(Synthesize(bot))
