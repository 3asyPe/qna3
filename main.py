import asyncio
import random
import sys
from questionary import Choice
import questionary
from config import PRIVATE_KEYS, PROXIES
from modules.generate_wallets import generate_wallets
from modules.invite_wallets import invite_wallets
from modules.claim_wallets import claim_wallets
from itertools import cycle
from modules.withdraw_from_binance import withdraw_from_binance

from settings import USER_AGENTS


def get_module():
    choices = [
        Choice(f"{i}) {key}", value)
        for i, (key, value) in enumerate(
            {
                "Generate wallets": generate_wallets,
                "Withdraw BNB from Binance": withdraw_from_binance,
                "Invite wallets (max 20 wallets per link)": invite_wallets,
                "Claim wallets": claim_wallets,
                "Exit": "exit",
            }.items(),
            start=1,
        )
    ]
    result = questionary.select(
        "Select a method to get started",
        choices=choices,
        qmark="🛠 ",
        pointer="✅ ",
    ).ask()
    if result == "exit":
        sys.exit()
    return result


def main():
    random.shuffle(USER_AGENTS)
    accounts = [
        {"private_key": pk, "proxy": proxy, "user_agent": user_agent}
        for pk, proxy, user_agent in zip(PRIVATE_KEYS, PROXIES, cycle(USER_AGENTS))
    ]

    module = get_module()
    asyncio.run(module(accounts))


if __name__ == "__main__":
    main()
