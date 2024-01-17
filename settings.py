# Referal link to qna3.ai
REF_LINK = "https://qna3.ai/?code=dD9p7HHZ"

SHUFFLE_WALLETS = True

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:114.0) Gecko/20100101 Firefox/114.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:113.0) Gecko/20100101 Firefox/113.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:112.0) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:111.0) Gecko/20100101 Firefox/111.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

MIN_SLEEP = 20
MAX_SLEEP = 30

MAX_RETRIES = 2

NETWORK = "OPBNB"  # BNB or OPBNB

BNB_RPC = "https://bsc.publicnode.com"
OPBNB_RPC = "https://opbnb.publicnode.com"

# Top up balance and get an API key on https://2captcha.com/?from=21563026
TWO_CAPTCHA_API_KEY = ""


# ___________________________________________
# |             CLAIM POINTS                |

CLAIM_ONLY_IF_POINTS_GREATER_THAN = 200

# ___________________________________________
# |             BINANCE WITHDRAW            |

BINANCE_API_KEY = ""
BINANCE_SECRET_KEY = ""

MIN_WITHDRAW = 0.00025
MAX_WITHDRAW = 0.0004

USE_PROXY_FOR_BINANCE = (
    False  # If True, you need to whitelist your proxies IPs in Binance API settings
)
