import asyncio
import json
import aiohttp
import random
from loguru import logger
from web3 import AsyncWeb3
from modules.utils import sleep
from settings import MAX_SLEEP, MIN_SLEEP, NETWORK, REF_LINK
from eth_account.messages import encode_defunct
from settings import BNB_RPC, OPBNB_RPC


if NETWORK == "BNB":
    web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BNB_RPC))
else:
    web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(OPBNB_RPC))


async def claim_wallets(accounts):
    for i, acc in enumerate(accounts, start=1):
        account = web3.eth.account.from_key(acc["private_key"])
        signature = await get_signature(acc["private_key"])
        auth_token, user_id = await login(
            signature, account.address, acc["user_agent"], acc["proxy"]
        )

        if await check_today_claim(
            auth_token, user_id, acc["user_agent"], acc["proxy"]
        ):
            logger.warning(
                f"[{account.address}] Points already claimed today. Skipping..."
            )
            await sleep(account.address)
            continue

        tx = await send_claim_tx(acc["private_key"], account.address)
        if not tx:
            continue

        resp_text = await send_hash(
            auth_token, user_id, tx, acc["user_agent"], acc["proxy"]
        )
        if resp_text == '{"statusCode":422,"message":"user already signed in today"}':
            logger.warning(
                f"[{account.address}] Points already claimed today. Skipping..."
            )
        elif json.loads(resp_text)["statusCode"] != 200:
            logger.error(
                f"[{account.address}] | An error occured while sending hash to qna3.ai | {resp_text}"
            )
        else:
            logger.success(f"[{account.address}] | Claimed points")

        if i != len(accounts):
            await sleep(account.address)


async def check_today_claim(auth_token, user_id, user_agent, proxy):
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

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://api.qna3.ai/api/v2/graphql",
            headers=headers,
            json=req_json,
            proxy=f"http://{proxy}",
        ) as response:
            # text = response.text()
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

    try:
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=private_key)
        send_tx = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = await web3.eth.wait_for_transaction_receipt(send_tx)

        return tx_receipt["transactionHash"].hex()
    except Exception as error:
        logger.error(f"[{address}] | Claim tx error | {error}")
        return False


async def get_signature(private_key):
    message = encode_defunct(text="AI + DYOR = Ultimate Answer to Unlock Web3 Universe")
    signed_message = web3.eth.account.sign_message(message, private_key=private_key)
    signature = signed_message.signature.hex()

    return signature


async def login(signature, address, user_agent, proxy):
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
    }

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


async def send_hash(auth_token, user_id, hash, user_agent, proxy):
    via = NETWORK.lower()

    req_json = {"hash": hash, "via": via}

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
        async with session.post(
            url="https://api.qna3.ai/api/v2/my/check-in",
            headers=headers,
            json=req_json,
            proxy=f"http://{proxy}",
        ) as response:
            return await response.text()
