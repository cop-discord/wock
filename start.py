import asyncio
import shutil
from anyio import Path
import asyncpg
import logging

from os import environ
from wock import Wock
from dotenv import load_dotenv
from rich.logging import RichHandler

load_dotenv(verbose=True)

cache = Path("/tmp/wock")

async def clear_cache():
    shutil.rmtree(cache, ignore_errors=True)
    await cache.mkdir(exist_ok=True)
    
def setup_logging():
    """Setup logging for the bot by adding an intercept handler which will intercept standard logging messages
    and redirect them to the loguru logging.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
        force=True,
    )


async def write_schema_to_database(pool: asyncpg.Pool) -> bool:
    """Write the schema to the database from the schema file

    Returns:
        bool: True if the schema is successfully written to the database, otherwise False.

    Args:
        pool (asyncpg.Pool): The database connection pool.
    """
    try:
        with open("system/schema/schema.sql") as file:
            await pool.execute(file.read())
            file.close()
    except FileNotFoundError:
        logging.error("Failed to open schema file.")
        return False
    except Exception as e:
        logging.error(f"Failed to write schema to database: {e}")
        return False

    logging.info("Schema written to database successfully.")
    return True


async def initialize_database() -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        user=environ.get("DATABASE_USER", "postgres"),
        password=environ.get("DATABASE_PASSWORD", "local"),
        database=environ.get("DATABASE_NAME", "felony"),
        host=environ.get("DATABASE_HOST", "localhost"),
        port=environ.get("DATABASE_PORT", 5432),
    )

    if not pool:
        raise Exception("Failed to connect to the database.")

    with open("system/schema/schema.sql", "r") as file:
        await pool.execute(file.read())

    return pool


async def main():
    await clear_cache()
    async with Wock() as bot:
        bot.pool = await initialize_database()
        await write_schema_to_database(bot.pool)
        await bot.start(environ.get("TOKEN", ""))


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
