with open("data/private_keys.txt", "r") as f:
    PRIVATE_KEYS = f.read().splitlines()


with open("data/proxies.txt", "r") as f:
    PROXIES = f.read().splitlines()
