import os
import requests
from datetime import datetime, timedelta

BEP20_WALLET = "0x6212905759a270a5860fc09f3f7c84c54470a89b"
USDT_CONTRACT = "0x55d398326f99059ff775485246999027b3197955"  # USDT BEP20 oficial

BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")

PLAN_PRICES = {
    "starter": 9.99,
    "pro": 19.99,
    "ultimate": 29.99
}

MARGIN = 0.05  # 5% margen por fees

def is_valid_payment(tx_hash: str, plan: str) -> bool:
    url = f"https://api.bscscan.com/api?module=account&action=tokentx&contractaddress={USDT_CONTRACT}&address={BEP20_WALLET}&sort=desc&apikey={BSCSCAN_API_KEY}"
    response = requests.get(url)

    if not response.ok:
        return False

    data = response.json().get("result", [])
    
    for tx in data:
        if tx["hash"].lower() == tx_hash.lower():
            if tx["to"].lower() != BEP20_WALLET.lower():
                return False

            amount = float(tx["value"]) / 1e18
            expected = PLAN_PRICES.get(plan, 9.99)
            min_acceptable = expected * (1 - MARGIN)

            timestamp = datetime.utcfromtimestamp(int(tx["timeStamp"]))
            recent = datetime.utcnow() - timedelta(hours=2)

            return amount >= min_acceptable and timestamp > recent

    return False
