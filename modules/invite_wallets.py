import aiohttp
from loguru import logger
from web3.auto import w3
from eth_account.messages import encode_defunct
from modules.utils import sleep

from settings import MAX_RETRIES, REF_LINK


def get_signature(private_key):
    message = encode_defunct(text="AI + DYOR = Ultimate Answer to Unlock Web3 Universe")
    signed_message = w3.eth.account.sign_message(message, private_key=private_key)
    signature = signed_message.signature.hex()

    return signature


async def send_request(signature, address, user_agent, proxy, ref_code):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ua-UA,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Host": "api.qna3.ai",
        "Origin": "https://qna3.ai",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "TE": "trailers",
        "User-Agent": user_agent,
        "x-lang": "english",
    }

    logger.info("Inviting...")

    cur_retry = 0
    while True:
        try:
            json = {
                "invite_code": ref_code,
                "signature": signature,
                "wallet_address": address,
            }
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    "https://api.qna3.ai/api/v2/auth/login?via=wallet",
                    json=json,
                    headers=headers,
                    proxy=f"http://{proxy}",
                )
                return resp
            break
        except Exception as e:
            logger.error(f"[{address}] Raised an error | {e}")
            cur_retry += 1
            if cur_retry < MAX_RETRIES:
                logger.info(f"[{address}] Retrying...")
                await sleep(address)
            else:
                break


async def invite_wallets(accounts, *args, **kwargs):
    if len(accounts) > 20:
        logger.error("You can't invite more than 20 wallets on single ref link")
        return

    for i, acc in enumerate(accounts, start=1):
        logger.info(f"Inviting #{i}")
        account = w3.eth.account.from_key(acc["private_key"])
        signature = get_signature(acc["private_key"])
        resp = await send_request(
            signature=signature,
            address=account.address,
            proxy=acc["proxy"],
            user_agent=acc["user_agent"],
            ref_code=REF_LINK.split("=")[1],
        )
        if resp.status in (200, 201):
            logger.info(f"Successfully invited #{i} {account.address}")
        else:
            logger.error(f"Error inviting #{i} {account.address} {await resp.text()}")

        if i != len(accounts):
            await sleep(account.address)

    logger.success("Done inviting!")
