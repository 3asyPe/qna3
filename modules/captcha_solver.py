from loguru import logger
from twocaptcha import TwoCaptcha

from settings import TWO_CAPTCHA_API_KEY


class CaptchaSolver:
    def __init__(self, proxy: str = None):
        if TWO_CAPTCHA_API_KEY == "":
            raise Exception("2captcha API key is missing. Set it in settings.py")

        self.config = {
            "apiKey": TWO_CAPTCHA_API_KEY,
        }

        self.proxy = proxy
        self.solver = TwoCaptcha(**self.config)

    def get_balance(self):
        return self.solver.balance()

    def solve(self, action: str = None):
        logger.info("Solving captcha...")

        params = {
            "sitekey": "6Lcq80spAAAAADGCu_fvSx3EG46UubsLeaXczBat",
            "url": "https://qna3.ai",
            "version": "v3",
            "enterprise": 1,
        }

        if self.proxy:
            params["proxy"] = {"type": "HTTP", "uri": self.proxy}

        if action:
            params["action"] = action

        return self.solver.recaptcha(**params)


async def get_2captcha_balance(*args, **kwargs):
    logger.info(f"2captcha Balance: {CaptchaSolver().get_balance()}$")
