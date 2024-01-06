import asyncio
import random

from loguru import logger

from settings import MAX_SLEEP, MIN_SLEEP


async def sleep(address):
    rt = random.randint(MIN_SLEEP, MAX_SLEEP)
    logger.info(f"[{address}] | Sleep {rt}")

    await asyncio.sleep(rt)
