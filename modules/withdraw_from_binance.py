import random
import ccxt
from loguru import logger

from settings import (
    BINANCE_API_KEY,
    BINANCE_SECRET_KEY,
    MAX_WITHDRAW,
    MIN_WITHDRAW,
    NETWORK,
    USE_PROXY_FOR_BINANCE,
)
from modules.utils import sleep
from web3.auto import w3


async def withdraw_from_binance(accounts):
    client_params = {
        "apiKey": BINANCE_API_KEY,
        "secret": BINANCE_SECRET_KEY,
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    }

    if NETWORK == "OPBNB":
        params = {"network": "OPBNB"}
    else:
        params = {"network": "BEP20"}

    for i, acc in enumerate(accounts, start=1):
        amount = round(random.uniform(MIN_WITHDRAW, MAX_WITHDRAW), 6)

        if USE_PROXY_FOR_BINANCE:
            client_params["proxies"] = {
                "http": f"http://{acc['proxy']}",
            }

        ccxt_client = ccxt.binance(client_params)
        account = w3.eth.account.from_key(acc["private_key"])

        try:
            withdraw = ccxt_client.withdraw(
                code="BNB",
                amount=amount,
                address=account.address,
                tag=None,
                params=params,
            )
            logger.success(
                f"{ccxt_client.name} - {account.address} | withdraw {amount} BNB ({NETWORK})"
            )

        except Exception as error:
            logger.error(
                f"{ccxt_client.name} - {account.address} | withdraw error : {error}"
            )

        if i != len(accounts):
            await sleep(account.address)
