import asyncio
import random
import time
import aiohttp
from loguru import logger

from web3 import AsyncWeb3
from modules.captcha_solver import CaptchaSolver
from modules.utils import sleep
from web3.exceptions import TransactionNotFound

from settings import (
    BNB_RPC,
    CLAIM_ONLY_IF_POINTS_GREATER_THAN,
    MAX_RETRIES,
)
from modules.daily_check_in import login, get_signature


web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BNB_RPC))


async def claim_points(accounts):
    for i, acc in enumerate(accounts, start=1):
        account = web3.eth.account.from_key(acc["private_key"])
        signature = get_signature(acc["private_key"])

        cur_retry = 0
        while True:
            try:
                captcha_token = CaptchaSolver(acc["proxy"]).solve()["code"]
                auth_token, user_id = await login(
                    signature,
                    account.address,
                    acc["user_agent"],
                    acc["proxy"],
                    captcha_token,
                )
                break
            except Exception as e:
                logger.error(f"[{account.address}] Raised an error | {e}")
                cur_retry += 1
                if cur_retry < MAX_RETRIES:
                    logger.info(f"[{account.address}] Retrying...")
                    await sleep(account.address)
                else:
                    break

        try:
            if not auth_token:
                raise Exception("Failed to login")
        except Exception as e:
            continue

        cur_retry = 0
        while True:
            try:
                captcha_token = CaptchaSolver(acc["proxy"]).solve()["code"]
                data = await _get_claim_points(
                    auth_token,
                    user_id,
                    acc["user_agent"],
                    acc["proxy"],
                    captcha_token,
                )

                if data["statusCode"] == 200 and "amount" not in data.get("data", {}):
                    amount = 0
                else:
                    amount = int(data["data"]["amount"])

                if amount < CLAIM_ONLY_IF_POINTS_GREATER_THAN:
                    logger.info(
                        f"[{account.address}] Not enough points ({amount}). Skipping..."
                    )
                    break

                tx = await send_claim_tx(
                    acc["private_key"],
                    account.address,
                    amount,
                    data["data"]["signature"]["signature"],
                    data["data"]["signature"]["nonce"],
                )
                if not tx:
                    raise Exception("Failed to send tx")

                resp = await send_hash(
                    auth_token,
                    user_id,
                    tx,
                    acc["user_agent"],
                    acc["proxy"],
                    data["data"]["history_id"],
                )

                if resp.get("statusCode") == 200:
                    logger.success(f"[{account.address}] | Claimed {amount} points")
                else:
                    raise Exception(f"[{account.address}] | Claim error | {resp}")

                break
            except Exception as e:
                logger.error(f"[{account.address}] Raised an error | {e}")
                cur_retry += 1
                if cur_retry < MAX_RETRIES:
                    logger.info(f"[{account.address}] Retrying...")
                    await sleep(account.address)
                else:
                    break

        if i != len(accounts):
            await sleep(account.address)


async def send_hash(auth_token, user_id, hash, user_agent, proxy, history_id):
    req_json = {"hash": hash}

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Origin": "https://qna3.ai",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": user_agent,
        "X-Id": user_id,
        "X-Lang": "english",
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(
            url=f"https://api.qna3.ai/api/v2/my/claim/{history_id}",
            headers=headers,
            json=req_json,
            proxy=f"http://{proxy}",
        ) as response:
            if response.status not in (200, 201):
                raise Exception(f"{await response.text()}")
            return await response.json()


async def send_claim_tx(private_key, address, amount, signature, nonce):
    data = (
        "0x624f82f5"
        f"{hex(amount).lstrip('0x').rstrip('L').zfill(64)}"
        f"{hex(nonce).lstrip('0x').rstrip('L').zfill(64)}"
        f"00000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000041"
        f"{signature[2:]}"
        "00000000000000000000000000000000000000000000000000000000000000"
    )
    transaction = {
        "to": "0xB342e7D33b806544609370271A8D074313B7bc30",
        "from": address,
        "data": data,
        "gasPrice": web3.to_wei(2, "gwei"),
        "gas": 165000,
        "nonce": await web3.eth.get_transaction_count(address),
        "chainId": 56,
    }

    signed_transaction = web3.eth.account.sign_transaction(transaction, private_key)
    try:
        send_tx = await web3.eth.send_raw_transaction(signed_transaction.rawTransaction)

        tx_receipt = await wait_until_tx_finished(address, send_tx, max_wait_time=480)
        if tx_receipt is None:
            raise Exception("Tx failed")
        return tx_receipt
    except Exception as error:
        logger.error(f"[{address}] | Claim tx error | {error}")

    return False


async def _get_claim_points(auth_token, user_id, user_agent, proxy, captcha_token):
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Origin": "https://qna3.ai",
        "User-Agent": user_agent,
        "X-Id": user_id,
        "X-Lang": "english",
    }

    logger.info("Getting claimable points...")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://api.qna3.ai/api/v2/my/claim-all",
            headers=headers,
            json={"recaptcha": captcha_token},
            proxy=f"http://{proxy}",
        ) as resp:
            if resp.status not in (200, 201):
                raise Exception(f"{await resp.text()}")

            return await resp.json()


async def get_claimable_points(accounts):
    results = []
    for acc in accounts:
        account = web3.eth.account.from_key(acc["private_key"])
        signature = get_signature(acc["private_key"])

        cur_retry = 0
        while True:
            try:
                captcha_token = CaptchaSolver(acc["proxy"]).solve()["code"]
                auth_token, user_id = await login(
                    signature,
                    account.address,
                    acc["user_agent"],
                    acc["proxy"],
                    captcha_token,
                )
                break
            except Exception as e:
                logger.error(f"[{account.address}] Raised an error | {e}")
                cur_retry += 1
                if cur_retry < MAX_RETRIES:
                    logger.info(f"[{account.address}] Retrying...")
                    await sleep(account.address)
                else:
                    break

        try:
            if not auth_token:
                raise Exception("Failed to login")
        except Exception as e:
            continue

        cur_retry = 0
        while True:
            try:
                captcha_token = CaptchaSolver(acc["proxy"]).solve()["code"]
                data = await _get_claim_points(
                    auth_token, user_id, acc["user_agent"], acc["proxy"], captcha_token
                )

                if data["statusCode"] == 200 and "amount" not in data.get("data", {}):
                    amount = 0
                else:
                    amount = data["data"]["amount"]

                string = f"[{account.address}] | Claimable points: {amount}"
                logger.info(string)
                results.append(string)

                break
            except Exception as e:
                logger.error(f"[{account.address}] Raised an error | {e}")
                cur_retry += 1
                if cur_retry < MAX_RETRIES:
                    logger.info(f"[{account.address}] Retrying...")
                    await asyncio.sleep(random.randint(1, 3))
                else:
                    results.append(f"[{account.address}] | Error: {e}")
                    break

        await asyncio.sleep(random.randint(1, 3))

    with open("data/claimable_points.txt", "w") as f:
        f.write("\n".join(results))

    logger.success("Saved to data/claimable_points.txt")


async def wait_until_tx_finished(address, hash: str, max_wait_time=480) -> None:
    start_time = time.time()
    while True:
        try:
            receipts = await web3.eth.get_transaction_receipt(hash)
            status = receipts.get("status")
            if status == 1:
                logger.success(f"[{address}] {hash.hex()} successfully!")
                return receipts["transactionHash"].hex()
            elif status is None:
                await asyncio.sleep(0.3)
            else:
                logger.error(f"[{address}] {hash.hex()} transaction failed! {receipts}")
                return None
        except TransactionNotFound:
            if time.time() - start_time > max_wait_time:
                logger.error(f"[{address}]{hash.hex()} transaction failed!")
                return None
            await asyncio.sleep(1)
