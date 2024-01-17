import json
import time
import aiohttp
import asyncio
from loguru import logger
from web3 import AsyncWeb3
from modules.captcha_solver import CaptchaSolver
from modules.utils import sleep
from settings import MAX_RETRIES, NETWORK
from eth_account.messages import encode_defunct
from settings import BNB_RPC, OPBNB_RPC
from web3.exceptions import TransactionNotFound


if NETWORK == "BNB":
    web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BNB_RPC))
else:
    web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(OPBNB_RPC))


async def daily_check_in(accounts):
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
                if await check_today_claim(
                    auth_token, user_id, acc["user_agent"], acc["proxy"]
                ):
                    logger.warning(
                        f"[{account.address}] Already checked in today. Skipping..."
                    )
                    break

                tx = await send_claim_tx(acc["private_key"], account.address)
                if not tx:
                    raise Exception("Failed to send tx")

                captcha_token = CaptchaSolver(acc["proxy"]).solve("checkin")["code"]
                await asyncio.sleep(3)
                if not await validate_check_in(
                    auth_token,
                    user_id,
                    acc["user_agent"],
                    acc["proxy"],
                    captcha_token,
                ):
                    raise Exception("Failed to validate check in")
                await asyncio.sleep(5)
                resp_text = await send_hash(
                    auth_token,
                    user_id,
                    tx,
                    acc["user_agent"],
                    acc["proxy"],
                    recaptcha_token=captcha_token,
                )

                if (
                    resp_text
                    == '{"statusCode":422,"message":"user already signed in today"}'
                ):
                    logger.warning(
                        f"[{account.address}] Already checked in today. Skipping..."
                    )
                elif json.loads(resp_text)["statusCode"] != 200:
                    logger.error(
                        f"[{account.address}] | An error occured while sending hash to qna3.ai | {resp_text}"
                    )
                    raise Exception("Failed to send hash")
                else:
                    logger.success(f"[{account.address}] | Successfully checked in!")

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


async def validate_check_in(auth_token, user_id, user_agent, proxy, recaptcha_token):
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Origin": "https://qna3.ai",
        "User-Agent": user_agent,
        "X-Id": user_id,
        "X-Lang": "english",
    }

    req_json = {
        "action": "checkin",
        "recaptcha": recaptcha_token,
    }

    logger.info("Validating check in...")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://api.qna3.ai/api/v2/my/validate",
            headers=headers,
            json=req_json,
            proxy=f"http://{proxy}",
        ) as response:
            resp_txt = await response.text()
            if resp_txt == '{"statusCode":200}':
                return True
            else:
                logger.error(f"An error occured while validating check in | {resp_txt}")
                return False


async def check_today_claim(auth_token, user_id, user_agent, proxy):
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Origin": "https://qna3.ai",
        "User-Agent": user_agent,
        "Sec-Ch-Ua": '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "X-Id": user_id,
        "X-Lang": "english",
    }

    req_json = {
        "query": "query loadUserDetail($cursored: CursoredRequestInput!) {\n  userDetail {\n    checkInStatus {\n      checkInDays\n      todayCount\n    }\n    credit\n    creditHistories(cursored: $cursored) {\n      cursorInfo {\n        endCursor\n        hasNextPage\n      }\n      items {\n        claimed\n        extra\n        id\n        score\n        signDay\n        signInId\n        txHash\n        typ\n      }\n      total\n    }\n    invitation {\n      code\n      inviteeCount\n      leftCount\n    }\n    origin {\n      email\n      id\n      internalAddress\n      userWalletAddress\n    }\n    externalCredit\n    voteHistoryOfCurrentActivity {\n      created_at\n      query\n    }\n    ambassadorProgram {\n      bonus\n      claimed\n      family {\n        checkedInUsers\n        totalUsers\n      }\n    }\n  }\n}",
        "variables": {
            "cursored": {"after": "", "first": 20},
            "headersMapping": {
                "Authorization": auth_token,
                "x-id": f"{user_id}",
                "x-lang": "english",
            },
        },
    }

    logger.info("Checking if there is something to claim...")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://api.qna3.ai/api/v2/graphql",
            headers=headers,
            json=req_json,
            proxy=f"http://{proxy}",
        ) as response:
            resp_txt = await response.json()

            try:
                ret = resp_txt["data"]["userDetail"]["checkInStatus"]["todayCount"]
            except:
                ret = False
            return ret


async def send_claim_tx(private_key, address):
    contract_address = "0xB342e7D33b806544609370271A8D074313B7bc30"
    data = "0xe95a644f0000000000000000000000000000000000000000000000000000000000000001"
    chain_id = 56 if NETWORK == "BNB" else 204

    gas_price = (
        web3.to_wei("3", "gwei") if NETWORK == "BNB" else web3.to_wei("0.00002", "gwei")
    )

    tx = {
        "chainId": chain_id,
        "data": data,
        "from": address,
        "to": contract_address,
        "nonce": await web3.eth.get_transaction_count(address),
        "gasPrice": gas_price,
        "gas": 35000,
    }

    signed_tx = web3.eth.account.sign_transaction(tx, private_key=private_key)
    try:
        send_tx = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = await wait_until_tx_finished(address, send_tx, max_wait_time=960)
        if tx_receipt is None:
            raise Exception("Tx failed")

        return tx_receipt
    except Exception as error:
        logger.error(f"[{address}] | Claim tx error | {error}")
    return False


def get_signature(private_key):
    message = encode_defunct(text="AI + DYOR = Ultimate Answer to Unlock Web3 Universe")
    signed_message = web3.eth.account.sign_message(message, private_key=private_key)
    signature = signed_message.signature.hex()

    return signature


async def login(signature, address, user_agent, proxy, recaptcha_token):
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

    req_json = {
        "signature": signature,
        "wallet_address": address,
        "recaptcha": recaptcha_token,
    }

    logger.info("Logging in...")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://api.qna3.ai/api/v2/auth/login?via=wallet",
            headers=headers,
            json=req_json,
            proxy=f"http://{proxy}",
        ) as response:
            resp_txt = await response.json()

            auth_token = "Bearer " + resp_txt["data"]["accessToken"]
            user_id = resp_txt["data"]["user"]["id"]

            return auth_token, user_id


async def send_hash(auth_token, user_id, hash, user_agent, proxy, recaptcha_token):
    via = NETWORK.lower()

    req_json = {"hash": hash, "recaptcha": recaptcha_token, "via": via}

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
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

    logger.info("Sending hash...")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://api.qna3.ai/api/v2/my/check-in",
            headers=headers,
            json=req_json,
            proxy=f"http://{proxy}",
        ) as response:
            resp = await response.text()
            return resp


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
