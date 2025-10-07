import os
import json
import time
import logging
import datetime
import sys
import threading
from typing import Tuple, List, Dict, Optional, Any

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError
from dotenv import load_dotenv
from threading import Lock

# --- Basic Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

load_dotenv()
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')

if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY is not set in .env file")
if not WALLET_ADDRESS or not Web3.is_address(WALLET_ADDRESS):
    raise ValueError("WALLET_ADDRESS is not set or invalid in .env file")
WALLET_ADDRESS = Web3.to_checksum_address(WALLET_ADDRESS)

# --- Constants ---
SONIC_RPC_URLS = [
    "https://rpc.soniclabs.com",
    "https://rpc.ankr.com/sonic",
    "https://sonic.drpc.org",
    "https://sonic-rpc.publicnode.com:443"
]
SILVER_FEES_CONTRACT_ADDRESS = Web3.to_checksum_address("0xfeE899CF3Ef6FCf338Da86453c334973e015c236")
POOL_BIDDER_CONTRACT_ADDRESS = Web3.to_checksum_address("0xC3e38729d53E3830Ab7365589A0A28cD73522BAE")

# Specific pools for blind bidding
WS_EGGS_POOL = Web3.to_checksum_address("0x23802c542a5af9f09c31ce28ba669dcf641aa1f8")
WS_USDC_POOL = Web3.to_checksum_address("0x9f46dd8f2a4016c26c1cf1f4ef90e5e1928d756b")
WS_AG_POOL = Web3.to_checksum_address("0x54e533E8d101f7C1660a5Cc62f841f2673c638BE")

# --- Global State ---
nonce_lock = Lock()
AUCTION_END_TIME: Optional[float] = None
early_bird_bid_placed: bool = False

# --- ABIs ---
try:
    with open('SilverFees.abi', 'r') as f:
        SILVER_FEES_ABI = json.load(f)
    with open('PoolBidder.abi', 'r') as f:
        POOL_BIDDER_ABI = json.load(f)
except FileNotFoundError as e:
    logger.critical(f"ABI file not found: {e}. Make sure SilverFees.abi and PoolBidder.abi are present.")
    sys.exit(1)

# --- Core Functions ---
def connect_to_blockchain(rpc_urls: List[str]) -> Web3:
    for url in rpc_urls:
        logger.info(f"Attempting connection to {url}")
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 20}))
            if w3.is_connected() and w3.eth.chain_id == 146:
                logger.info(f"Connected to {url}, Chain ID: 146")
                return w3
        except Exception as e:
            logger.error(f"Failed to connect to {url}: {e}")
    raise ConnectionError("No valid RPC available.")

def get_current_bid(w3: Web3, sf_contract: Contract, pool_id: str) -> Tuple[str, float]:
    try:
        data = sf_contract.functions.snatchData(pool_id).call()
        if not data or data[0][0] == '0x0000000000000000000000000000000000000000':
            return "NO BIDDER", 0.0
        user, bid_wei = Web3.to_checksum_address(data[0][0]), int(data[0][1])
        bid_eth = float(w3.from_wei(bid_wei, 'ether'))
        return user, bid_eth
    except Exception as e:
        logger.error(f"Error in get_current_bid for pool {pool_id}: {e}")
        return "NO BIDDER", 0.0

def place_bid_with_poolbidder(w3: Web3, pb_contract: Contract, bid_amount_eth: float, pool_id: str) -> Tuple[bool, Optional[str]]:
    pname = f"Pool({pool_id[:6]}..)"
    rounded_bid = round(bid_amount_eth, 8)
    try:
        bid_wei = w3.to_wei(rounded_bid, 'ether')
        with nonce_lock:
            tx_params = {
                'from': WALLET_ADDRESS,
                'nonce': w3.eth.get_transaction_count(WALLET_ADDRESS, 'pending'),
                'gasPrice': int(w3.eth.gas_price * 1.5),
                'chainId': 146
            }
            tx_params['gas'] = int(pb_contract.functions.bidOnPool(pool_id, bid_wei).estimate_gas(tx_params) * 1.4)
            txn = pb_contract.functions.bidOnPool(pool_id, bid_wei).build_transaction(tx_params)
            signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
        logger.info(f"SUCCESS: Bid for {pname}: {rounded_bid:.4f} $AG. Tx: {tx_hash_hex}")
        return True, tx_hash_hex
    except Exception as e:
        logger.error(f"FAILED to bid for {pname} ({rounded_bid:.4f} $AG): {e}")
        return False, str(e)

def place_multiple_bids_with_poolbidder(w3: Web3, pb_contract: Contract, pool_ids: List[str], bid_amounts_eth: List[float]) -> Tuple[bool, Optional[str]]:
    logger.info(f"Attempting MULTI-BID for {len(pool_ids)} pools.")
    try:
        with nonce_lock:
            bid_amounts_wei = [w3.to_wei(round(a, 8), 'ether') for a in bid_amounts_eth]
            tx_params = {
                'from': WALLET_ADDRESS,
                'nonce': w3.eth.get_transaction_count(WALLET_ADDRESS, 'pending'),
                'gasPrice': int(w3.eth.gas_price * 1.5),
                'chainId': 146
            }
            tx_params['gas'] = int(pb_contract.functions.bidOnMultiplePools(pool_ids, bid_amounts_wei).estimate_gas(tx_params) * 1.5)
            txn = pb_contract.functions.bidOnMultiplePools(pool_ids, bid_amounts_wei).build_transaction(tx_params)
            signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
        logger.info(f"SUCCESS: Multi-bid for {len(pool_ids)} pools. Tx: {tx_hash_hex}")
        return True, tx_hash_hex
    except Exception as e:
        logger.error(f"FAILED to multi-bid: {e}")
        return False, str(e)

def reset_auction_cycle_state(sf_contract: Contract):
    global AUCTION_END_TIME, early_bird_bid_placed
    logger.info("Resetting state for new auction cycle...")
    try:
        sync_data = sf_contract.functions.syncFeesManagementData().call()
        next_sync_ts = sync_data[2]
        now_ts = time.time()
        if next_sync_ts > now_ts and (next_sync_ts - now_ts < 20 * 3600):
            AUCTION_END_TIME = float(next_sync_ts)
        else:
            AUCTION_END_TIME = float(sync_data[1] + (12 * 3600))

        end_time_str = datetime.datetime.fromtimestamp(AUCTION_END_TIME, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
        logger.info(f"New auction end time: {end_time_str}")
        early_bird_bid_placed = False
    except Exception as e:
        logger.critical(f"Failed to reset auction state: {e}. Exiting.")
        sys.exit(1)

def main():
    global AUCTION_END_TIME, early_bird_bid_placed
    w3 = connect_to_blockchain(SONIC_RPC_URLS)
    sf_contract = w3.eth.contract(address=SILVER_FEES_CONTRACT_ADDRESS, abi=SILVER_FEES_ABI)
    pb_contract = w3.eth.contract(address=POOL_BIDDER_CONTRACT_ADDRESS, abi=POOL_BIDDER_ABI)

    reset_auction_cycle_state(sf_contract)

    while True:
        try:
            now = time.time()
            if now > AUCTION_END_TIME:
                logger.info("Auction ended. Resetting for next cycle.")
                time.sleep(10) # Wait a bit before checking for the new cycle
                reset_auction_cycle_state(sf_contract)
                continue

            time_to_end = AUCTION_END_TIME - now

            # 1. Early Bird Bidding
            # Window: between ~13.5 mins (808s) and 10 mins (600s) to go
            if not early_bird_bid_placed and 600 < time_to_end <= 808:
                logger.info(f"Checking for early bird bid on WS-EGGS (TTE: {time_to_end:.2f}s)")
                _, bid_amt = get_current_bid(w3, sf_contract, WS_EGGS_POOL)
                if bid_amt == 0:
                    logger.info("WS-EGGS has no bids. Placing 0.1 AG early bird bid.")
                    place_bid_with_poolbidder(w3, pb_contract, 0.1, WS_EGGS_POOL)
                else:
                    logger.info(f"WS-EGGS already has a bid of {bid_amt}. Skipping.")
                early_bird_bid_placed = True

            # 2. Final Window Bidding
            # Window: last 5 seconds
            if 0 < time_to_end <= 5.0:
                logger.info(f"Entering Final Bidding Phase (TTE: {time_to_end:.2f}s).")
                final_pools = [WS_USDC_POOL, WS_AG_POOL]
                bid_amounts = [0.0] * len(final_pools) # 0.0 relies on contract auto-increment

                threads = []
                for i in range(6):
                    logger.info(f"Kicking off final bid thread {i+1}/6.")
                    thread = threading.Thread(target=place_multiple_bids_with_poolbidder, args=(w3, pb_contract, final_pools, bid_amounts))
                    threads.append(thread)
                    thread.start()
                    time.sleep(0.2) # Stagger the bids slightly

                for thread in threads:
                    thread.join() # Wait for all threads to complete

                logger.info("Final bidding phase complete. Waiting for auction to end.")
                time.sleep(time_to_end + 2) # Sleep past the end time
                continue

            logger.info(f"Time to auction end: {time_to_end:.2f}s. Early bird placed: {early_bird_bid_placed}. Waiting...")
            time.sleep(30) # Check every 30 seconds outside of final window

        except Exception as e:
            logger.error(f"An error occurred in the main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()