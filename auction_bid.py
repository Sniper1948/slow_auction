import os
import json
import time
import logging
import datetime
import sys
import requests
import uuid # Make sure uuid is imported
import random
from math import ceil
import threading # Added
import copy # Added
import asyncio

from typing import Tuple, Dict, List, Any, Optional
from web3 import Web3
from web3.contract import Contract # Explicitly import Contract
from web3.datastructures import AttributeDict
from web3.exceptions import BlockNotFound, ContractLogicError # Make sure ContractLogicError is imported
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data
from eth_abi.codec import ABICodec
from dotenv import load_dotenv
from threading import Lock

# Script version
SCRIPT_VERSION = "1.6.0" # Integrated PoolBidder.sol contract and refined logic
logging.basicConfig(
    level=logging.INFO, # Changed to INFO for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logger.info(f"Script version: {SCRIPT_VERSION}")

# Load environment variables
load_dotenv()
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS') # Address of the EOA that owns PoolBidder.sol

# Validate wallet
if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY is not set in .env file")
if not WALLET_ADDRESS or not Web3.is_address(WALLET_ADDRESS):
    raise ValueError("WALLET_ADDRESS is not set or invalid in .env file")
WALLET_ADDRESS = Web3.to_checksum_address(WALLET_ADDRESS)
logger.info(f"Operator Wallet Address (owns PoolBidder): {WALLET_ADDRESS}")


AG_TOKEN = Web3.to_checksum_address("0x005851f943ee2957b1748957f26319e4f9edebc1")

# RPCs
SONIC_RPC_URLS = [
    "https://rpc.soniclabs.com",
    "https://rpc.ankr.com/sonic",
    "https://sonic.drpc.org",
    "https://sonic-rpc.publicnode.com:443"
]

# Addresses
SILVER_FEES_CONTRACT_ADDRESS = Web3.to_checksum_address("0xfeE899CF3Ef6FCf338Da86453c334973e015c236")
NFT_POSITION_MANAGER_ADDRESS = Web3.to_checksum_address("0x5084E9fDF9264489A14E77C011073D757E572bB4")
POOL_BIDDER_CONTRACT_ADDRESS = Web3.to_checksum_address("0xC3e38729d53E3830Ab7365589A0A28cD73522BAE") # Your deployed PoolBidder address

# Pool Addresses
WS_ZUPA_POOL = Web3.to_checksum_address("0xd4988f9b3438a620d07f41b1415859aba038158a")
WS_ECO_POOL = Web3.to_checksum_address("0x3dbf257817866ee785edd0329daf36b5c198c3fd")
WS_JOINT_POOL = Web3.to_checksum_address("0x741146bbd931aa7799979206df1ab61905512bed")
WS_GOGLZ_POOL = Web3.to_checksum_address("0x72d158eeed476b875ec4e50bd56834c1dbfd372d")
WS_RACKS_POOL = Web3.to_checksum_address("0x0139666fddd275d08353b248e42eea096d61d78f")
WS_USDC_POOL = Web3.to_checksum_address("0x9f46dd8f2a4016c26c1cf1f4ef90e5e1928d756b")
WS_AG_POOL = Web3.to_checksum_address("0x54e533E8d101f7C1660a5Cc62f841f2673c638BE")
WS_ANON_POOL = Web3.to_checksum_address("0x6671c0684b54e0a6f6ee2f878f2b217bca1f8291")
WS_SDIGGA_POOL = Web3.to_checksum_address("0xd451a16d7d5414abe8c883ed98aa3c47d00435ea")
WS_SCETH_POOL = Web3.to_checksum_address("0x2d0ae637493bd895fde19b55e665e7dfbaebfc8d")
WS_WETH_POOL = Web3.to_checksum_address("0x9208db26a52b7046a94d1771dc629452c6c2fa20")
WS_EGGS_POOL = Web3.to_checksum_address("0x23802c542a5af9f09c31ce28ba669dcf641aa1f8")
WS_WHALE_POOL = Web3.to_checksum_address("0x899fa124768994e5788f63d1b8bff0261a819bcf")
WS_DERP_POOL = Web3.to_checksum_address("0x86193d8058d9b80b9e0bf69de3279c7d7a9644ed")
WS_THC_POOL = Web3.to_checksum_address("0x5188885473bc80d7e2c8389b2ccda2b69e5d78e2")
WS_PHANIC_POOL = Web3.to_checksum_address("0x1b7d76d8ba70ec6d5cc7c1c4e38b591c9e4c2397")
AG_SCETH_POOL = Web3.to_checksum_address("0x6c9b8827c7fecd8e19d504d57308a50269343aad")
USDC_ANON_POOL = Web3.to_checksum_address("0xcfaecabcb3ea73acc94202458cb4fcc0d077e894")
USDC_SCUSD_POOL = Web3.to_checksum_address("0xa741c001e7d37b4e312ab60374c869a89bf894c4") 
USDC_FRXUSD_POOL = Web3.to_checksum_address("0x9107c409838f09d487421bfdac2c45c1ab320eae")
SCETH_WETH_POOL = Web3.to_checksum_address("0xcc3d28191e8567dfae1ea280dadb798cf3b4172c")
HEDGY_ANON_POOL = Web3.to_checksum_address("0xbc9726639897b4cdbdd97d6b8e067140e6de9403")
USDC_AUR_POOL= Web3.to_checksum_address("0xa08851a8D67E26BBddF8c55cc0Dc649fb50164a5")
WS_SONIC_POOL = Web3.to_checksum_address("0xd455bc762cd8606788516ab11f3116f8712db2d5") 
frxETH_WETH_POOL = Web3.to_checksum_address("0x697aaBd91B48ee8066Ff46318D50ad361880Ef49")
WS_INDI_POOL = Web3.to_checksum_address("0x55eD5A63a5e833DC6FCDf5B3e009963e1B473b50")
WS_SCUSD_POOL = Web3.to_checksum_address("0x12c83F2615939b543E369F2b9D0230D574150E06")
AG_USDC_POOL    = Web3.to_checksum_address("0x8e788A87bEf84Be47fEa007868281Af3160F96e6")
WS_HEDGY_POOL = Web3.to_checksum_address("0x581ea7d19DD893858abC7AcbB31Ea83c261A18F5")  # wS-HEDGY pool
WS_WOOF_POOL = Web3.to_checksum_address("0xD4B18Acd107874e446bC7e3f4f3d277Cb6c1523d")  # wS-WOOF pool

# Pool configuration
POOLS = {
    WS_USDC_POOL: "WS-USDC", WS_AG_POOL: "AG-WS", WS_ANON_POOL: "WS-ANON",
    WS_SDIGGA_POOL: "WS-SDIGGA", WS_SCETH_POOL: "WS-SCETH", WS_WETH_POOL: "WS-WETH",
    WS_EGGS_POOL: "WS-EGGS", WS_WHALE_POOL: "WS-WHALE", WS_DERP_POOL: "WS-DERP",
    WS_PHANIC_POOL: "WS-PHANIC", WS_THC_POOL: "WS-THC", WS_ZUPA_POOL: "WS-ZUPA",
    WS_ECO_POOL: "WS-ECO", WS_JOINT_POOL: "WS-JOINT", WS_GOGLZ_POOL: "WS-GOOGLZ",
    WS_RACKS_POOL: "WS-RACKS", AG_SCETH_POOL: "AG-SCETH", USDC_ANON_POOL: "USDC-ANON",
    USDC_SCUSD_POOL: "USDC-SCUSD", USDC_FRXUSD_POOL: "USDC-FRXUSD",
    SCETH_WETH_POOL: "SCETH-WETH", HEDGY_ANON_POOL: "HEDGY-ANON",
    USDC_AUR_POOL: "USDC-AUR", WS_SONIC_POOL: "WS-SONIC",
    frxETH_WETH_POOL: "frxETH-WETH", WS_INDI_POOL: "WS-INDI",
    WS_SCUSD_POOL: "WS-SCUSD", AG_USDC_POOL: "AG-USDC",
    WS_HEDGY_POOL: "WS-HEDGY", WS_WOOF_POOL: "WS-WOOF"
}

HEADERS = {
    "authority": "silverswap.io", "accept": "*/*", "accept-language": "en-GB,en;q=0.8",
    "content-type": "text/plain;charset=UTF-8", "origin": "https://silverswap.io",
    "referer": "https://silverswap.io/auctions/snatch",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "sec-gpc": "1", "cache-control": "no-cache", "pragma": "no-cache"
}

# Global state
GLOBAL_AVG_BLOCK_TIME: float = 2.0 # Default average block time for Sonic (in seconds)
CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK: Optional[int] = None # Used to set the start block for event scanner for a new cycle
AUCTION_END_TIME: Optional[float] = None
highest_bids: Dict[str, Dict[str, Any]] = {} # Key: pool_id, Value: {"amount", "user", "tx_hash"}
pool_locks: Dict[str, Lock] = {} # Will be initialized after POOLS_ORIGINAL is set
last_rewards: Dict[str, Optional[float]] = {} # Key: pool_id
event_scanner_failed: bool = False
POOLS_ORIGINAL: Dict[str, str] = {} # Populated at startup
hot_list_created: bool = False
last_bids: Dict[str, float] = {} # Tracks last attempted bid amount for a pool if it failed low
EARLY_BID_TIMES_CONFIG = sorted([13000, 8008, 6008, 808, 308], reverse=True) # Original config
early_bid_times_queue: List[int] = [] # Mutable queue for current auction cycle
early_bids_processed_for_threshold: Dict[int, bool] = {} # Tracks if a threshold time has been processed
last_reward_check_time: float = 0
current_auction_log_file: Optional[str] = None # Added for async logging

# --- REPORTING DATA STRUCTURES ---
bid_log_data: List[Dict[str, Any]] = []
reward_summary_data: List[Dict[str, Any]] = []
# Wallet statistics will be derived from reward_summary_data

# --- BIDDING STRATEGY PARAMETERS ---
EARLY_BID_MIN_REWARD_FOR_0_1_AG_BID = 0.1
EARLY_BID_MAX_REWARD_FOR_0_1_AG_BID = 0.2 
EARLY_BID_FIXED_AMOUNT = 0.1
CONTRACT_DEFAULT_INCREMENT_AMOUNT = 0.1 # Standard increment your contract uses when bid amount 0 is passed

HOT_LIST_CREATION_START_TTE = 45  # Start creating hot list 45s before end
HOT_LIST_CREATION_END_TTE = 25    # Aim to have it done by 25s before end
HOT_LIST_MIN_POTENTIAL_PROFIT = 0.01 # Reward > (current_bid + CONTRACT_DEFAULT_INCREMENT_AMOUNT) + THIS

FINAL_BID_WINDOW_START_TTE = 0.9 # Start final aggressive bidding window shortly before end - USER WILL TUNE THIS
FINAL_BATCH_AUTO_INCREMENT_PROFIT_MARGIN = 0.02

# --- Hyper-Reactive Bidding Parameters ---
MINIMUM_TTE_FOR_REACTION = 0.15  # Minimum TTE (seconds) to continue reactive bidding. Below this, likely too late.
HYPER_REACTIVE_CHECK_INTERVAL = 0.02 # Sleep interval (seconds) between full check cycles of reactive pools.
GET_CURRENT_BID_TIMEOUT_HYPER = 0.05 # Timeout (seconds) for get_current_bid in hyper-reactive mode (50ms).

# --- Task Skipping TTE Thresholds (to ensure responsiveness for final window) ---
TTE_THRESHOLD_BALANCE_CHECK = 5.0 # Skip balance check if TTE < 5.0s
TTE_THRESHOLD_BID_UPDATE = 1.8    # Skip bid updates if TTE < 1.8s
TTE_THRESHOLD_EVENT_SCAN = 2.0    # Skip event scanning if TTE < 2.0s
# Note: Periodic Reward Fetch is already governed by MIN_TTE_FOR_GENERAL_REWARD_FETCH = 45s

# --- Simulation Mode Parameters ---
SIMULATE_FINAL_WINDOW_MODE = False  # Set to True to activate simulation
SIMULATE_TTE_START = 20.0          # TTE (seconds) at which simulation will begin
simulated_auction_end_time_override: Optional[float] = None # Internal state for simulation TTE
simulation_has_run: bool = False # Ensures simulation runs only once if desired

# --- Event Scan Control Parameters ---
MAX_BLOCKS_PER_SCAN_LOW_TTE = 100    # Max blocks to scan in one go if TTE is low
TTE_FOR_REDUCED_SCAN_RANGE = 30.0  # TTE below which scan range is reduced
MAX_INITIAL_CATCHUP_SCAN_BLOCKS = 2000 # Max blocks for the very first catch-up scan in a cycle

# --- Dumb Bidding Mode Parameters ---
#DUMB_BIDDING_MODE: bool = os.getenv('DUMB_BIDDING_MODE', 'False').lower() == 'true'
DUMB_BIDDING_MODE = True
DUMB_BID_REPEATS: int = int(os.getenv('DUMB_BID_REPEATS', '3'))
DUMB_BID_REPEAT_DELAY: float = float(os.getenv('DUMB_BID_REPEAT_DELAY', '0.1'))
DUMB_BID_PROFIT_MARGIN_ASSUMPTION: float = float(os.getenv('DUMB_BID_PROFIT_MARGIN_ASSUMPTION', '0.01'))
MINIMUM_TTE_FOR_DUMB_BID: float = float(os.getenv('MINIMUM_TTE_FOR_DUMB_BID', '0.05'))


MIN_TTE_FOR_GENERAL_REWARD_FETCH = 45 # No general reward HTTP calls if TTE < 45s
PERIODIC_REWARD_FETCH_INTERVAL = 40 # How often to fetch rewards when safe
EARLY_BID_REWARD_FETCH_INTERVAL = 3   # How often to fetch for early bids if needed


# Load ABIs
try:
    with open('SilverFees.abi', 'r') as f:
        SILVER_FEES_ABI = json.load(f)
    logger.debug("Loaded SilverFees.abi")
except FileNotFoundError:
    logger.critical("SilverFees.abi not found in current directory! Exiting.")
    raise
except json.JSONDecodeError as e:
    logger.critical(f"Failed to decode JSON in SilverFees.abi: {e}. Exiting.")
    raise

try:
    with open('PoolBidder.abi', 'r') as f:
        POOL_BIDDER_ABI = json.load(f)
    logger.info("Loaded PoolBidder.abi")
except FileNotFoundError:
    logger.critical("PoolBidder.abi not found. Make sure it's in the same directory as auto_bidder.py. Exiting.")
    raise
except json.JSONDecodeError as e:
    logger.critical(f"Failed to decode JSON in PoolBidder.abi: {e}. Exiting.")
    raise

class InMemoryState:
    def __init__(self): 
        self.events: List[Dict[str, Any]] = []
        self.highest_block_scanned_successfully: int = 0

    def get_last_scanned_block(self) -> int: 
        return self.highest_block_scanned_successfully

    def start_chunk(self, bn: int, cs: int): 
        logger.debug(f"State: Start chunk bn={bn}, cs={cs}")

    def end_chunk(self, bn: int): 
        self.highest_block_scanned_successfully = max(self.highest_block_scanned_successfully, bn)

    def process_event(self, bw: datetime.datetime, evt: AttributeDict) -> Dict:
        block_number = evt.get("blockNumber")
        
        p = {
            "event": evt.get("event"), 
            "bn": block_number, 
            "tx_hash": evt.get("transactionHash", b'').hex(), 
            "timestamp": bw.isoformat(), 
            "args": dict(evt.get("args", {})) 
        }
        self.events.append(p)
        
        if block_number is not None:
             self.highest_block_scanned_successfully = max(self.highest_block_scanned_successfully, block_number)
        
        return p

    def delete_data(self, sb: int) -> int: 
        self.events = [e for e in self.events if e.get("bn", 0) < sb]; 
        return len(self.events)

    def reset(self): 
        self.events = []
        self.highest_block_scanned_successfully = 0 
        logger.info("InMemoryState reset (events and highest_block_scanned_successfully).")

class EventScanner:
    def __init__(self, w3: Web3, contract_to_scan: Contract, state: InMemoryState, event_types: List,
                 max_chunk_scan_size: int = 30, max_req_retries: int = 2, req_retry_secs: float = 0.3):
        self.logger, self.w3, self.contract, self.state, self.event_types = logger, w3, contract_to_scan, state, event_types
        self.min_scan_chunk, self.max_chunk_scan, self.max_req_retries, self.req_retry_secs = 10, max_chunk_scan_size, max_req_retries, req_retry_secs
        self.chunk_decrease, self.chunk_increase = 0.6, 1.3 

    def get_block_ts(self, bn: int) -> datetime.datetime:
        try: return datetime.datetime.fromtimestamp(self.w3.eth.get_block(bn)["timestamp"], tz=datetime.timezone.utc)
        except BlockNotFound: logger.warning(f"Block {bn} not found for TS, using now."); return datetime.datetime.now(tz=datetime.timezone.utc)

    async def scan_single_chunk(self, start_bn: int, end_bn: int, timeout: float) -> Tuple[int, List[Dict]]:
        processed_in_chunk, highest_bn_in_chunk = [], start_bn -1 
        for evt_type in self.event_types:
            def fetch_logic(s, e): 
                return _fetch_events_for_contract(self.w3, evt_type, {}, s, e, timeout, self.contract.address)
            
            _, events_found = await _retry_web3_call(fetch_logic, start_bn, end_bn, self.max_req_retries, self.req_retry_secs, self.logger)

            if events_found is None: 
                self.logger.error(f"Event fetching failed persistently for chunk {start_bn}-{end_bn}. This chunk will be marked as scanned up to {end_bn} to prevent getting stuck, but no events processed from it.")
                return end_bn, [] 

            for evt_data in events_found: 
                if evt_data.get("blockNumber") is None: 
                    self.logger.warning(f"Event data missing blockNumber: {evt_data}. Skipping.")
                    continue
                highest_bn_in_chunk = max(highest_bn_in_chunk, evt_data["blockNumber"])
                block_ts = self.get_block_ts(evt_data["blockNumber"])
                processed_in_chunk.append(self.state.process_event(block_ts, evt_data))
        
        return end_bn, processed_in_chunk

    def estimate_chunk_size(self, current_cs: int, events_found_ct: int) -> int:
        if events_found_ct > 0: new_cs = max(self.min_scan_chunk, int(current_cs * self.chunk_decrease))
        else: new_cs = min(self.max_chunk_scan, int(current_cs * self.chunk_increase))
        return new_cs

    async def scan(self, start_bn: int, end_bn: int, timeout: float, start_cs: int = 20) -> Tuple[List[Dict[str, Any]], int]:
        if start_bn > end_bn: return [], 0
        current_bn, cs, total_chunks, all_processed = start_bn, max(self.min_scan_chunk, start_cs), 0, []
        
        self.logger.debug(f"EventScanner.scan: Initial range {start_bn}-{end_bn}. Initial state.highest_block_scanned_successfully: {self.state.get_last_scanned_block()}")

        while current_bn <= end_bn:
            self.state.start_chunk(current_bn, cs) 
            chunk_end_bn = min(current_bn + cs - 1, end_bn)
            
            scanned_up_to_bn_for_chunk, new_evts = await self.scan_single_chunk(current_bn, chunk_end_bn, timeout)
            
            all_processed.extend(new_evts)
            self.state.end_chunk(scanned_up_to_bn_for_chunk) # This should be chunk_end_bn or the actual highest block scanned in the chunk
            
            current_bn = scanned_up_to_bn_for_chunk + 1 
            cs = self.estimate_chunk_size(cs, len(new_evts))
            total_chunks +=1
            
        self.logger.info(f"Event scan finished for range {start_bn}-{end_bn}: {len(all_processed)} events, {total_chunks} chunks. State's highest scanned block now: {self.state.get_last_scanned_block()}")
        return all_processed, total_chunks

def _fetch_events_for_contract(w3: Web3, event_type: Any, filters: Dict[str, Any], from_bn: int, to_bn: int, timeout: float, contract_addr: str) -> Optional[List[AttributeDict]]:
    evt_name = event_type.event_name if hasattr(event_type, 'event_name') else 'UnknownEvent'
    logger.debug(f"Fetching {evt_name} events from {contract_addr} (blocks {from_bn}-{to_bn})")
    
    try:
        abi = event_type._get_event_abi()
        codec: ABICodec = w3.codec
        argument_filters = filters.get("args", {})
        if argument_filters is None: argument_filters = {}

        _, event_filter_params = construct_event_filter_params(
            abi, codec, address=contract_addr, argument_filters=argument_filters, 
            from_block=from_bn, to_block=to_bn
        )
        
        logs = w3.eth.get_logs(event_filter_params)
        
        decoded_events = []
        for log_entry in logs:
            try:
                decoded_events.append(get_event_data(codec, abi, log_entry))
            except Exception as e_decode:
                logger.warning(f"Could not decode log entry for {evt_name} from {contract_addr}: {log_entry}, Error: {e_decode}")
        return decoded_events
        
    except Exception as e: 
        logger.error(f"Event fetch for {evt_name} on {contract_addr} (blocks {from_bn}-{to_bn}) failed: {e}", exc_info=False) 
        global event_scanner_failed 
        event_scanner_failed = True 
        return None 

async def _retry_web3_call(func: callable, start_bn: int, end_bn: int, retries: int, delay: float, logger_instance: logging.Logger) -> Tuple[int, Optional[List[AttributeDict]]]:
    for attempt in range(retries + 1):
        try:
            result = func(start_bn, end_bn)
            return end_bn, result 
        except Exception as e:
            logger_instance.warning(f"Retry {attempt+1}/{retries+1} for event fetch ({start_bn}-{end_bn}) failed: {e}")
            if attempt == retries:
                logger_instance.error(f"Event fetch failed after {retries+1} retries for blocks {start_bn}-{end_bn}.")
                return end_bn, None 
            await asyncio.sleep(delay * (attempt + 1)) 
    return end_bn, None 

def connect_to_blockchain(rpc_urls: List[str]) -> Web3:
    for url in rpc_urls:
        logger.info(f"Attempting connection to {url}")
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 20})) 
            w3.eth.exception_retry_configuration = {} 
            if w3.is_connected() and w3.eth.chain_id == 146:
                logger.info(f"Connected to {url}, Chain ID: 146")
                return w3
            elif w3.is_connected(): 
                logger.warning(f"Connected to {url} but wrong Chain ID: {w3.eth.chain_id} (expected 146)")
            else: 
                logger.warning(f"Connection to {url} failed: Not connected")
        except Exception as e: 
            logger.error(f"Failed to connect to {url}: {e}")
    raise ConnectionError("No valid RPC available after multiple attempts.")

def get_current_bid(w3: Web3, sf_contract: Contract, pool_id: str, timeout: float = 1.0) -> Tuple[str, float]:
    pool_name = POOLS_ORIGINAL.get(pool_id, pool_id)
    try:
        data = sf_contract.functions.snatchData(pool_id).call()
        if not data or data[0][0] == '0x0000000000000000000000000000000000000000':
            return "NO BIDDER", 0.0
        user, bid_wei = Web3.to_checksum_address(data[0][0]), int(data[0][1])
        bid_eth = float(w3.from_wei(bid_wei, 'ether'))
        return user, bid_eth
    except ContractLogicError as e:
        logger.error(f"snatchData ContractLogicError for {pool_name} ({pool_id}): {e}")
        return "NO BIDDER", 0.0
    except Exception as e:
        if "timeout" not in str(e).lower() and "connection aborted" not in str(e).lower() :
            logger.error(f"Generic error in get_current_bid for {pool_name} ({pool_id}): {e}", exc_info=False)
        else:
            logger.debug(f"Timeout/Connection error in get_current_bid for {pool_name} ({pool_id}): {e}")
        return "NO BIDDER", 0.0

def initialize_bids_state(w3: Web3, sf_contract: Contract):
    global highest_bids, pool_locks
    logger.info("Initializing highest_bids and pool_locks from on-chain data.")
    pool_locks = {pid: Lock() for pid in POOLS_ORIGINAL.keys()}
    for pid, pname in POOLS_ORIGINAL.items():
        user, bid_amt = get_current_bid(w3, sf_contract, pid)
        highest_bids[pid] = {"amount": bid_amt, "user": user, "tx_hash": "on-chain-init" if bid_amt > 0 else None}
        if bid_amt > 0: logger.info(f"Init bid for {pname}: {bid_amt:.4f} $AG by {user}")
    logger.debug(f"Initialized highest_bids: {len(highest_bids)} entries.")

async def update_bids_from_chain(w3: Web3, sf_contract: Contract, pools_to_check: Dict[str, str]):
    pool_count = len(pools_to_check)
    logger.debug(f"Updating bids from chain for {pool_count} pool(s)...")
    
    checked_count = 0
    for pid, pname in pools_to_check.items():
        if pool_count > 10 and checked_count > 0 and checked_count % 5 == 0: 
            await asyncio.sleep(0.05) 
            
        user, bid_amt = get_current_bid(w3, sf_contract, pid, timeout=0.4) 
        current_local = highest_bids.get(pid, {"amount": 0.0, "user": "NO BIDDER"})
        
        bid_changed = False
        if abs(bid_amt - current_local["amount"]) > 1e-9: 
            bid_changed = True
        elif bid_amt > 0 and user != current_local["user"]: 
            bid_changed = True
        elif bid_amt == 0 and current_local["amount"] > 0: 
            bid_changed = True

        if bid_changed:
            highest_bids[pid] = {"amount": bid_amt, "user": user, "tx_hash": "on-chain-update" if bid_amt > 0 else None}
            logger.info(f"Updated bid for {pname} ({pid[:6]}..): {bid_amt:.4f} $AG by {user if user != 'NO BIDDER' else 'N/A'}" if bid_amt > 0 else f"Cleared/No bid for {pname} ({pid[:6]}..)")
        checked_count += 1


def fetch_pool_rewards_data(sf_contract: Contract) -> List[Dict[str, Any]]:
    logger.debug(f"Fetching pool rewards for {len(POOLS_ORIGINAL)} pools")
    results = []
    with requests.Session() as session:
        for pid, pname in POOLS_ORIGINAL.items():
            try:
                snatch_data_tuple = sf_contract.functions.snatchData(pid).call()
                last_exec = snatch_data_tuple[1]
                period_hrs = ceil((time.time() - last_exec) / 3600) if last_exec > 0 else 12
                if period_hrs <= 0: period_hrs = 1

                payload = {"chainId": 146, "poolId": pid, "tokenGiven": AG_TOKEN, "periodInHours": period_hrs, "id": str(uuid.uuid4())}
                api_url = f"https://silverswap.io/api/getLiquidityPoolInterests?t={int(time.time()*1000)}"
                resp = session.post(api_url, headers=HEADERS, json=payload, timeout=15)
                resp.raise_for_status(); data = resp.json()
                reward_val = data.get("totalInGiven", 0) * 0.425
                results.append({
                    "pool_id": pid, 
                    "pool_name": pname, 
                    "reward_agency": reward_val, 
                    "total_value_raw": data.get("totalInGiven",0),
                    "api_period_hours_sent": period_hrs,
                    "api_last_execution_used": last_exec
                })
            except requests.exceptions.RequestException as he: 
                logger.error(f"Reward HTTP error for {pname} ({pid}) URL {api_url}: {he}")
                results.append({"pool_id": pid, "pool_name": pname, "reward_agency": 0.0, "error": str(he)})
            except Exception as e: 
                logger.error(f"Reward fetch general error for {pname} ({pid}): {e}", exc_info=False)
                results.append({"pool_id": pid, "pool_name": pname, "reward_agency": 0.0, "error": str(e)})
    return results

async def reset_auction_cycle_state(w3: Web3, sf_contract: Contract):
    global AUCTION_END_TIME, highest_bids, last_rewards, hot_list_created, early_bid_times_queue, early_bids_processed_for_threshold
    global last_reward_check_time, POOLS, pool_locks, GLOBAL_AVG_BLOCK_TIME, CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK
    logger.info("Resetting state for new auction cycle...")
    
    CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK = None 

    last_rewards.clear(); highest_bids.clear(); last_bids.clear()
    hot_list_created = False
    
    POOLS.clear(); POOLS.update(POOLS_ORIGINAL)
    pool_locks = {pid: Lock() for pid in POOLS_ORIGINAL.keys()}

    early_bid_times_queue = list(EARLY_BID_TIMES_CONFIG)
    early_bids_processed_for_threshold = {t: False for t in EARLY_BID_TIMES_CONFIG}

    for attempt in range(5):
        try:
            sync_data = sf_contract.functions.syncFeesManagementData().call()
            now_ts, last_sync_ts, next_sync_ts = time.time(), sync_data[1], sync_data[2]
            logger.info(f"Sync data: Last @ {datetime.datetime.fromtimestamp(last_sync_ts, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}, Next @ {datetime.datetime.fromtimestamp(next_sync_ts, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            if next_sync_ts > now_ts and (next_sync_ts - now_ts < 20 * 3600):
                AUCTION_END_TIME = datetime.datetime.fromtimestamp(next_sync_ts, tz=datetime.timezone.utc)
            elif last_sync_ts > 0:
                AUCTION_END_TIME = datetime.datetime.fromtimestamp(last_sync_ts + (12 * 3600), tz=datetime.timezone.utc)
                logger.warning(f"next_sync invalid or too far, using fallback end time based on last_sync: {AUCTION_END_TIME.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            else:
                logger.error("Cannot determine valid auction end time from sync data after multiple attempts. Will retry state reset.")
                raise ValueError("Invalid sync data for auction end time.")

            logger.info(f"New AUCTION_END_TIME: {AUCTION_END_TIME.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            initialize_bids_state(w3, sf_contract) 
            rewards_data = fetch_pool_rewards_data(sf_contract) 
            for r_info in rewards_data: 
                if "error" not in r_info: last_rewards[r_info["pool_id"]] = r_info["reward_agency"]
            
            current_cycle_start_approx_ts = 0.0 
            if AUCTION_END_TIME == next_sync_ts and next_sync_ts > 0: 
                 current_cycle_start_approx_ts = float(next_sync_ts - (12 * 3600)) 
            elif AUCTION_END_TIME and last_sync_ts > 0 : 
                 current_cycle_start_approx_ts = float(last_sync_ts) 

            if current_cycle_start_approx_ts > 0:
                scan_target_timestamp = current_cycle_start_approx_ts + (16 * 60) 
                logger.info(f"Calculating smart start block for event scan. Approx cycle start: {datetime.datetime.fromtimestamp(current_cycle_start_approx_ts, tz=datetime.timezone.utc).isoformat()}, Target scan time: {datetime.datetime.fromtimestamp(scan_target_timestamp, tz=datetime.timezone.utc).isoformat()}")
                try:
                    latest_block_num_for_est = w3.eth.block_number
                    block = w3.eth.get_block(latest_block_num_for_est)
                    if not isinstance(block, AttributeDict) or 'timestamp' not in block:
                        logger.warning(f"Block data for {latest_block_num_for_est} is not as expected or missing timestamp. Proceeding with block estimation without current_block_data.")
                        current_block_data_for_func = None
                    else:
                        latest_block_ts_for_est = block['timestamp']
                        current_block_data_for_func = (latest_block_num_for_est, latest_block_ts_for_est)

                    calculated_start_block = get_block_number_for_target_timestamp(
                        w3, 
                        scan_target_timestamp, 
                        GLOBAL_AVG_BLOCK_TIME,
                        current_block_data=current_block_data_for_func
                    )
                    if calculated_start_block:
                        CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK = calculated_start_block
                        logger.info(f"Set CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK to: {CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK} for SnatchAuction events this cycle.")
                    else:
                        logger.warning("Failed to calculate a specific start block for event scanning. Scanner will use its default state or last known block.")
                except Exception as e_calc_block:
                    logger.error(f"Error calculating smart start block for event scan: {e_calc_block}", exc_info=True)
            else:
                logger.warning("Could not determine current_cycle_start_approx_ts; cannot set specific event scan start block.")

            logger.info("Auction cycle state reset complete.")
            return 
        except Exception as e:
            logger.warning(f"Auction reset attempt {attempt+1} failed: {e}")
            if attempt < 4: 
                await asyncio.sleep((attempt + 1) * 2)
            else:
                logger.critical("All attempts to reset auction state failed. Exiting.")
                sys.exit(1) 

def attempt_pool_supremacy_bids(w3: Web3, sf_contract: Contract, pb_contract: Contract):
    global highest_bids, last_rewards, last_bids 
    function_start_time = time.perf_counter() 

    logger.info("--- Attempting Pool Supremacy Bids (Multi-Bid Test) ---")

    logger.info("Supremacy: Fetching current rewards...")
    rewards_data = fetch_pool_rewards_data(sf_contract)
    current_rewards: Dict[str, float] = {}
    for r_info in rewards_data:
        if "error" not in r_info and r_info.get("pool_id"):
            current_rewards[r_info["pool_id"]] = r_info["reward_agency"]
    logger.info(f"Supremacy: Rewards fetched for {len(current_rewards)} pools.")

    pools_to_target_ids: List[str] = []
    bid_amounts_for_target_pools: List[float] = []
    required_profit_margin = 0.005 

    logger.info("Supremacy: Analyzing pools for potential outbids...")
    for pool_id, pool_name in POOLS_ORIGINAL.items(): 
        current_bidder_str, onchain_bid_amount = get_current_bid(w3, sf_contract, pool_id, timeout=20)
        
        highest_bids[pool_id] = {"amount": onchain_bid_amount, "user": current_bidder_str, "tx_hash": "on-chain-supremacy-check"}
        reward = current_rewards.get(pool_id)

        is_pool_bidder_the_current_bidder = False
        if current_bidder_str != "NO BIDDER":
            try:
                if Web3.to_checksum_address(current_bidder_str) == POOL_BIDDER_CONTRACT_ADDRESS:
                    is_pool_bidder_the_current_bidder = True
            except ValueError:
                logger.warning(f"Supremacy: Could not convert current_bidder_str '{current_bidder_str}' to checksum address for pool {pool_name}. Assuming not our bidder.")

        if is_pool_bidder_the_current_bidder:
            logger.debug(f"Supremacy: Skipping {pool_name} - PoolBidder is already highest bidder with {onchain_bid_amount:.4f} $AG.")
            continue

        if reward is None:
            logger.warning(f"Supremacy: No reward data for {pool_name}, cannot assess for supremacy bid.")
            continue

        target_bid_amount = round(onchain_bid_amount + 0.1, 8) if onchain_bid_amount > 0 else 0.1

        if reward > target_bid_amount + required_profit_margin:
            if pool_id in last_bids and target_bid_amount <= round(last_bids[pool_id], 8):
                logger.info(f"Supremacy: Skipping {pool_name} for multi-bid test: target {target_bid_amount:.4f} is at/below last known failing bid {last_bids[pool_id]:.4f}")
                continue
            
            logger.info(f"Supremacy: Adding {pool_name} to batch. Current bid: {onchain_bid_amount:.4f} by {current_bidder_str}. Reward: {reward:.4f}. Target bid: {target_bid_amount:.4f}")
            pools_to_target_ids.append(pool_id)
            bid_amounts_for_target_pools.append(target_bid_amount)
        else:
            logger.debug(f"Supremacy: Skipping {pool_name}. Reward {reward:.4f} not sufficient for target bid {target_bid_amount:.4f} + margin {required_profit_margin:.3f}")

    if pools_to_target_ids:
        logger.info(f"Supremacy: Preparing multi-bid for {len(pools_to_target_ids)} pools.")
        
        multi_bid_tx_start_time = time.perf_counter()
        success, tx_hash_or_error = place_multiple_bids_with_poolbidder(
            w3, 
            pb_contract, 
            pools_to_target_ids, 
            bid_amounts_for_target_pools, 
            urgency="LOW"
        )
        multi_bid_tx_end_time = time.perf_counter()
        multi_bid_duration = multi_bid_tx_end_time - multi_bid_tx_start_time

        if success:
            logger.info(f"Supremacy: Multi-bid transaction SUCCEEDED. Tx: {tx_hash_or_error}. Execution time: {multi_bid_duration:.4f} seconds.")
            for i, p_id_succeeded in enumerate(pools_to_target_ids):
                highest_bids[p_id_succeeded] = {
                    "amount": bid_amounts_for_target_pools[i],
                    "user": POOL_BIDDER_CONTRACT_ADDRESS,
                    "tx_hash": tx_hash_or_error
                }
                last_bids.pop(p_id_succeeded, None) 
        else:
            logger.error(f"Supremacy: Multi-bid transaction FAILED. Details: {tx_hash_or_error}. Execution time: {multi_bid_duration:.4f} seconds.")
    else:
        logger.info("Supremacy: No pools met criteria for supremacy bids.")
    
    function_end_time = time.perf_counter()
    total_function_duration = function_end_time - function_start_time
    logger.info(f"--- Pool Supremacy Bids Test COMPLETE. Total function time: {total_function_duration:.4f} seconds. ---")


def place_bid_with_poolbidder(w3: Web3, pb_contract: Contract, bid_amount_eth: float, pool_id: str, urgency: str = "NORMAL") -> Tuple[bool, Optional[str]]:
    global last_bids, bid_log_data, SIMULATE_FINAL_WINDOW_MODE
    pname = POOLS_ORIGINAL.get(pool_id, pool_id)
    rounded_bid = round(bid_amount_eth, 8)

    if SIMULATE_FINAL_WINDOW_MODE:
        logger.info(f"[SIMULATION] Attempting bid via PoolBidder: {rounded_bid:.4f} $AG for {pname}, Urgency: {urgency}")
        if pool_id in last_bids and rounded_bid <= round(last_bids[pool_id], 8):
            logger.info(f"[SIMULATION] Skipping bid for {pname}: {rounded_bid:.4f} is same or lower than last known failing/low bid {last_bids[pool_id]:.4f}")
            return False, "SIMULATED_DUPLICATE_OR_LOW_BID"

        # Simulate successful bid for logging and state update
        sim_tx_hash = f"SIM_TX_{uuid.uuid4().hex[:10]}"
        logger.info(f"[SIMULATION] SUCCESS: Bid for {pname}: {rounded_bid:.4f} $AG. Simulated Tx: {sim_tx_hash}")
        bid_log_data.append({
            "Wallet Address": POOL_BIDDER_CONTRACT_ADDRESS, "Pool Name": pname,
            "Bid Time (UTC)": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Bid Amount ($AG)": rounded_bid, "Tx Hash (Short)": sim_tx_hash[:12] + ".."
        })
        last_bids.pop(pool_id, None)
        # Update highest_bids as if the bid was successful on-chain for simulation purposes
        highest_bids[pool_id] = {"amount": rounded_bid, "user": POOL_BIDDER_CONTRACT_ADDRESS, "tx_hash": sim_tx_hash}
        return True, sim_tx_hash

    logger.debug(f"Attempting bid via PoolBidder: {bid_amount_eth:.4f} $AG for {pname}, Urgency: {urgency}")
    
    if pool_id in last_bids and rounded_bid <= round(last_bids[pool_id], 8):
        logger.info(f"Skipping bid for {pname}: {rounded_bid:.4f} is same or lower than last known failing/low bid {last_bids[pool_id]:.4f}")
        return False, "Duplicate or already known low/failed bid"

    lock = pool_locks.get(pool_id)
    if not lock: 
        logger.error(f"No lock for {pname}!")
        return False, "Internal lock error"
    if not lock.acquire(blocking=False): 
        logger.debug(f"{pname} locked, bid attempt skipped.")
        return False, "Pool locked"
    
    tx_hash_hex = None 
    try:
        bid_wei = w3.to_wei(rounded_bid, 'ether')
        # gas_mult = 1.4 if urgency == "URGENT" else 1.25
        gas_mult = {"URGENT": 1.5, "NORMAL": 1, "LOW": 1}.get(urgency, 1)# We don't want to spend much as we want to be last in the block
        current_gas_price = w3.eth.gas_price
        tx_params = {
            'from': WALLET_ADDRESS, 
            'nonce': w3.eth.get_transaction_count(WALLET_ADDRESS, 'pending'),
            'gasPrice': int(current_gas_price * gas_mult), 
            'chainId': 146
        }
        try:
            estimated_gas = pb_contract.functions.bidOnPool(pool_id, bid_wei).estimate_gas({'from': WALLET_ADDRESS, 'gasPrice': tx_params['gasPrice']})
            tx_params['gas'] = int(estimated_gas * 1.35) 
            logger.info(f"Estimated gas for PoolBidder.bidOnPool on {pname}: {tx_params['gas']} (price: {tx_params['gasPrice'] / 1e9:.2f} Gwei)")
        except Exception as e_gas_est:
            logger.warning(f"Gas estimation failed for PoolBidder.bidOnPool on {pname}: {e_gas_est}. Using default 480k gas.")
            tx_params['gas'] = 480000 

        txn = pb_contract.functions.bidOnPool(pool_id, bid_wei).build_transaction(tx_params)
        signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_hash_hex = tx_hash.hex() 
        logger.info(f"SUCCESS: Bid via PoolBidder for {pname}: {rounded_bid:.4f} $AG. Tx: {tx_hash_hex}")
        
        bid_log_data.append({
            "Wallet Address": POOL_BIDDER_CONTRACT_ADDRESS,
            "Pool Name": pname,
            "Bid Time (UTC)": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Bid Amount ($AG)": rounded_bid, 
            "Tx Hash (Short)": tx_hash_hex[:12] + ".." if tx_hash_hex else "N/A"
        })

        last_bids.pop(pool_id, None) 
        return True, tx_hash_hex
    except ContractLogicError as e_logic:
        err_msg = str(e_logic)
        logger.error(f"PoolBidder.bidOnPool for {pname} ({rounded_bid:.4f} $AG) FAILED ContractLogic: {err_msg}")
        if "bid not higher" in err_msg.lower() or "bid too low" in err_msg.lower(): 
            last_bids[pool_id] = rounded_bid
        elif "insufficient $ag balance" in err_msg.lower(): 
            logger.critical(f"PoolBidder has insufficient $AG! Check contract {POOL_BIDDER_CONTRACT_ADDRESS}")
        elif "insufficient $ag allowance" in err_msg.lower(): 
            logger.critical(f"PoolBidder $AG allowance to SilverFees insufficient! Check contract {POOL_BIDDER_CONTRACT_ADDRESS}")
        return False, err_msg
    except Exception as e_general:
        logger.error(f"General place_bid_with_poolbidder error for {pname} ({rounded_bid:.4f} $AG): {e_general}", exc_info=True)
        last_bids[pool_id] = rounded_bid 
        return False, str(e_general)
    finally: 
        if lock.locked(): 
            lock.release()
            logger.debug(f"Released lock for {pname}")

def place_multiple_bids_with_poolbidder(w3: Web3, pb_contract: Contract, pool_ids: List[str], bid_amounts_eth: List[float], urgency: str = "NORMAL") -> Tuple[bool, Optional[str]]:
    global last_bids, bid_log_data, SIMULATE_FINAL_WINDOW_MODE
    
    if SIMULATE_FINAL_WINDOW_MODE:
        logger.info(f"[SIMULATION] Attempting MULTI-BID via PoolBidder for {len(pool_ids)} pools. Urgency: {urgency}")
        if not pool_ids or not bid_amounts_eth or len(pool_ids) != len(bid_amounts_eth):
            logger.error("[SIMULATION] Error in multi-bid: pool_ids and bid_amounts_eth mismatch or empty.")
            return False, "SIMULATED_INVALID_INPUT_MULTI_BID"

        for i, pool_id_log in enumerate(pool_ids):
            logger.info(f"  - [SIMULATION] Pool: {POOLS_ORIGINAL.get(pool_id_log, pool_id_log)}, Amount: {bid_amounts_eth[i]:.4f} $AG")

        sim_multi_tx_hash = f"SIM_MULTI_TX_{uuid.uuid4().hex[:10]}"
        logger.info(f"[SIMULATION] SUCCESS: Multi-bid for {len(pool_ids)} pools. Simulated Tx: {sim_multi_tx_hash}")

        current_time_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        tx_hash_short = sim_multi_tx_hash[:12] + ".."

        for i, pool_id in enumerate(pool_ids):
            pname = POOLS_ORIGINAL.get(pool_id, pool_id)
            # Assuming 0.0 means auto-increment by contract, otherwise use the specified amount
            # This logic should mirror the optimistic amount calculation in the main loop's final bidding part
            # For simplicity here, we'll record the bid_amounts_eth[i] or an estimated incremented value if it's 0.0
            # This part needs careful thought if we want to perfectly simulate the outcome for `initial_batch_optimistic_bids`
            # Let's assume for now that if bid_amounts_eth[i] is 0.0, it implies an increment over current highest_bids[pool_id]['amount']

            simulated_bid_amount = 0.0
            if bid_amounts_eth[i] == 0.0:
                # This is a simplification. Real logic would need current on-chain (or simulated on-chain)
                # highest bid for pool_id to correctly calculate the auto-incremented amount.
                # For now, let's record it as 0.0 (auto) or fetch from highest_bids and add increment.
                # This ensures that initial_batch_optimistic_bids can be populated correctly.
                current_simulated_onchain_bid = highest_bids.get(pool_id, {}).get("amount", 0.0)
                simulated_bid_amount = round(current_simulated_onchain_bid + CONTRACT_DEFAULT_INCREMENT_AMOUNT, 8)
                logger.info(f"  - [SIMULATION] For {pname}, 0.0 amount implies auto-increment. Current simulated on-chain: {current_simulated_onchain_bid:.4f}, new simulated target: {simulated_bid_amount:.4f}")

            else:
                simulated_bid_amount = round(bid_amounts_eth[i], 8)

            bid_log_data.append({
                "Wallet Address": POOL_BIDDER_CONTRACT_ADDRESS, "Pool Name": pname,
                "Bid Time (UTC)": current_time_utc, "Bid Amount ($AG)": simulated_bid_amount,
                "Tx Hash (Short)": tx_hash_short
            })
            last_bids.pop(pool_id, None)
            # Update highest_bids to reflect this simulated successful multi-bid component
            highest_bids[pool_id] = {"amount": simulated_bid_amount, "user": POOL_BIDDER_CONTRACT_ADDRESS, "tx_hash": sim_multi_tx_hash}

        return True, sim_multi_tx_hash

    if not pool_ids or not bid_amounts_eth or len(pool_ids) != len(bid_amounts_eth):
        logger.error("Error in multi-bid: pool_ids and bid_amounts_eth mismatch or empty.")
        return False, "Invalid input for multi-bid"

    logger.info(f"Attempting MULTI-BID via PoolBidder for {len(pool_ids)} pools. Urgency: {urgency}")
    for i, pool_id_log in enumerate(pool_ids):
        logger.info(f"  - Pool: {POOLS_ORIGINAL.get(pool_id_log, pool_id_log)}, Amount: {bid_amounts_eth[i]:.4f} $AG")

    tx_hash_hex = None 
    try:
        bid_amounts_wei = [w3.to_wei(round(amount, 8), 'ether') if amount != 0.0 else 0 for amount in bid_amounts_eth]
        
        #gas_mult = 1.45 if urgency == "URGENT" else 1.3 
        gas_mult = {"URGENT": 1.5, "NORMAL": 1, "LOW": 1}.get(urgency, 1) # We don't want to spend much as we want to be last in the block
        current_gas_price = w3.eth.gas_price
        tx_params = {
            'from': WALLET_ADDRESS, 
            'nonce': w3.eth.get_transaction_count(WALLET_ADDRESS, 'pending'),
            'gasPrice': int(current_gas_price * gas_mult), 
            'chainId': 146
        }

        base_gas_for_multibid = 150000 
        gas_per_internal_bid = 150000    
        estimated_gas_dynamic = base_gas_for_multibid + (len(pool_ids) * gas_per_internal_bid)
        
        try:
            estimated_gas_call = pb_contract.functions.bidOnMultiplePools(pool_ids, bid_amounts_wei).estimate_gas({'from': WALLET_ADDRESS, 'gasPrice': tx_params['gasPrice']})
            tx_params['gas'] = int(estimated_gas_call * 1) 
            logger.info(f"Estimated gas for PoolBidder.bidOnMultiplePools ({len(pool_ids)} pools): {tx_params['gas']} (price: {tx_params['gasPrice'] / 1e9:.2f} Gwei)")
        except Exception as e_gas_est:
            logger.warning(f"Gas estimation failed for bidOnMultiplePools: {e_gas_est}. Using dynamic estimate: {estimated_gas_dynamic}")
            tx_params['gas'] = int(estimated_gas_dynamic * 1) 
            if len(pool_ids) > 5: 
                 tx_params['gas'] = max(tx_params['gas'], 2000000)

        txn = pb_contract.functions.bidOnMultiplePools(pool_ids, bid_amounts_wei).build_transaction(tx_params)
        signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_hash_hex = tx_hash.hex() 
        
        logger.info(f"SUCCESS: Multi-bid via PoolBidder for {len(pool_ids)} pools. Tx: {tx_hash_hex}")
        
        current_time_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        tx_hash_short = tx_hash_hex[:12] + ".." if tx_hash_hex else "N/A"
        for i, pool_id in enumerate(pool_ids):
            pname = POOLS_ORIGINAL.get(pool_id, pool_id)
            logged_bid_amount = bid_amounts_eth[i] 
            
            bid_log_data.append({
                "Wallet Address": POOL_BIDDER_CONTRACT_ADDRESS,
                "Pool Name": pname,
                "Bid Time (UTC)": current_time_utc, 
                "Bid Amount ($AG)": logged_bid_amount, 
                "Tx Hash (Short)": tx_hash_short 
            })
            last_bids.pop(pool_id, None) 
        return True, tx_hash_hex
        
    except ContractLogicError as e_logic:
        err_msg = str(e_logic)
        logger.error(f"PoolBidder.bidOnMultiplePools FAILED ContractLogic: {err_msg}")
        return False, err_msg
    except Exception as e_general:
        logger.error(f"General place_multiple_bids_with_poolbidder error: {e_general}", exc_info=True)
        return False, str(e_general)

# --- BLOCK NUMBER ESTIMATION ---

def get_block_number_for_target_timestamp(
    w3: Web3, 
    target_timestamp: float, 
    avg_block_time_seconds: float, 
    current_block_data: Optional[Tuple[int, int]] = None
) -> Optional[int]:
    """
    Estimates and iteratively finds a block number near a target_timestamp.
    Aims for a block whose timestamp is >= target_timestamp and <= target_timestamp + accepted_window_seconds.
    """
    logger.info(f"Attempting to find block near timestamp: {datetime.datetime.fromtimestamp(target_timestamp, tz=datetime.timezone.utc).isoformat()}")
    
    try:
        if current_block_data:
            latest_block_num, latest_block_ts = current_block_data
        else:
            latest_block_num = w3.eth.block_number
            latest_block_ts = w3.eth.get_block(latest_block_num)['timestamp']
        logger.debug(f"Current latest block: {latest_block_num} @ TS: {latest_block_ts}")

        if target_timestamp > latest_block_ts:
            logger.warning(f"Target timestamp {target_timestamp} is in the future compared to latest block timestamp {latest_block_ts}. Returning latest block {latest_block_num}.")
            return latest_block_num

        if avg_block_time_seconds <= 0: 
            avg_block_time_seconds = 2.0 
            logger.warning(f"Invalid avg_block_time_seconds ({avg_block_time_seconds}), using default 2.0s for estimation.")

        time_diff = latest_block_ts - target_timestamp
        block_diff_estimate = int(time_diff / avg_block_time_seconds)
        estimated_target_block = latest_block_num - block_diff_estimate
        current_search_block = max(1, estimated_target_block) 

        logger.debug(f"Initial estimate for target block: {current_search_block} (latest: {latest_block_num}, time_diff: {time_diff:.2f}s, block_diff_est: {block_diff_estimate})")

        MAX_ITERATIONS = 15 
        ACCEPTED_WINDOW_SECONDS = 120  

        for i in range(MAX_ITERATIONS):
            try:
                block_to_check = w3.eth.get_block(current_search_block)
                ts_of_search_block = block_to_check['timestamp']
                logger.debug(f"Iteration {i+1}/{MAX_ITERATIONS}: Checking block {current_search_block}, TS: {ts_of_search_block} (Target window: [{target_timestamp}, {target_timestamp + ACCEPTED_WINDOW_SECONDS}])")

                if target_timestamp <= ts_of_search_block <= target_timestamp + ACCEPTED_WINDOW_SECONDS:
                    logger.info(f"Found suitable block {current_search_block} with timestamp {ts_of_search_block} within target window.")
                    return current_search_block
                
                search_time_diff_from_window_start = ts_of_search_block - target_timestamp
                blocks_to_jump = max(1, int(abs(search_time_diff_from_window_start) / avg_block_time_seconds))

                if ts_of_search_block < target_timestamp: 
                    current_search_block += blocks_to_jump
                    logger.debug(f"Block too old. Jumping forward by {blocks_to_jump} blocks to ~{current_search_block}")
                else: 
                    current_search_block -= blocks_to_jump
                    logger.debug(f"Block too new. Jumping backward by {blocks_to_jump} blocks to ~{current_search_block}")
                
                current_search_block = max(1, current_search_block) 
                if current_search_block > latest_block_num : 
                    logger.warning(f"Search jumped past latest block ({current_search_block} > {latest_block_num}). Capping at {latest_block_num} and stopping search.")
                    return latest_block_num
            except BlockNotFound:
                logger.warning(f"Block {current_search_block} not found during search. Adjusting search.")
                if current_search_block < estimated_target_block: 
                    current_search_block = int((current_search_block + estimated_target_block) / 2) 
                else: 
                    current_search_block = int((current_search_block + latest_block_num) / 2) 
                current_search_block = max(1, current_search_block)
            except Exception as e_iter:
                logger.error(f"Error in get_block_number_for_target_timestamp iteration {i+1}: {e_iter}", exc_info=True)
                break 

        logger.warning(f"Could not find block in target window [{target_timestamp}, {target_timestamp + ACCEPTED_WINDOW_SECONDS}] after {MAX_ITERATIONS} iterations. Returning last searched block: {current_search_block}")
        return current_search_block

    except Exception as e:
        logger.error(f"Error in get_block_number_for_target_timestamp: {e}", exc_info=True)
        return None

# --- END BLOCK NUMBER ESTIMATION ---

# --- REPORT GENERATION FUNCTIONS ---

def format_report_row(row_data: List[str], column_widths: List[int]) -> str:
    """Helper function to format a single row of a text-based table."""
    formatted_cells = []
    for i, cell_content in enumerate(row_data):
        content_str = str(cell_content)
        try:
            float(content_str) 
            is_numeric_type = not isinstance(cell_content, str) or cell_content.replace('.', '', 1).isdigit()
        except ValueError:
            is_numeric_type = False
        
        if is_numeric_type and not (isinstance(cell_content, str) and "(auto)" in cell_content):
            formatted_cells.append(content_str.rjust(column_widths[i]))
        else:
            formatted_cells.append(content_str.ljust(column_widths[i]))
    return "| " + " | ".join(formatted_cells) + " |"

def generate_bid_log_report(data: List[Dict[str, Any]]) -> str:
    """Generates the Bid Log report string."""
    if not data:
        return "Bid Log:\nNo bid data to report for this cycle.\n"

    headers = ["Wallet Address", "Pool Name", "Bid Time (UTC)", "Bid Amount ($AG)", "Tx Hash (Short)"]
    col_widths = [44, 13, 26, 18, 19] 

    report_lines = ["Bid Log:"]
    
    unique_bids_list = []
    seen_bid_keys = set()

    try:
        sorted_input_data = sorted(data, key=lambda x: x.get("Bid Time (UTC)", "0000-00-00T00:00:00.000000+00:00")) 
    except TypeError as e:
        logger.warning(f"TypeError during bid_log_data pre-sorting for de-duplication: {e}. Proceeding without pre-sort.")
        sorted_input_data = data 

    for entry in sorted_input_data:
        wallet_address = str(entry.get("Wallet Address", "")).lower() 
        pool_name = str(entry.get("Pool Name", ""))
        
        tx_hash_short = entry.get("Tx Hash (Short)", "")
        tx_hash_prefix_for_key = tx_hash_short.split('..')[0] if tx_hash_short and ".." in tx_hash_short else tx_hash_short
            
        bid_amount_val = entry.get("Bid Amount ($AG)", 0.0)
        try:
            bid_amount_key_part = f"{float(bid_amount_val):.4f}" 
        except ValueError:
            bid_amount_key_part = str(bid_amount_val) 

        bid_key = (tx_hash_prefix_for_key, pool_name, wallet_address, bid_amount_key_part, str(entry.get("Bid Time (UTC)", ""))[:19])

        if bid_key not in seen_bid_keys:
            seen_bid_keys.add(bid_key)
            unique_bids_list.append(entry) 
    
    try:
        final_sorted_bids = sorted(unique_bids_list, key=lambda x: (x.get("Bid Time (UTC)", "0"), x.get("Pool Name", "")))
    except TypeError as e:
        logger.warning(f"TypeError during final bid_log sorting: {e}. Report may not be perfectly sorted.")
        final_sorted_bids = unique_bids_list 
    
    report_lines.append("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")
    report_lines.append(format_report_row(headers, col_widths))
    report_lines.append("+" + "+".join(["=" * (w + 2) for w in col_widths]) + "+")

    for entry in final_sorted_bids: 
        bid_amount_val = entry.get("Bid Amount ($AG)", 0.0)
        bid_amount_display_str = f"{float(bid_amount_val):.1f}" 
        
        if str(entry.get("Wallet Address", "")).lower() == POOL_BIDDER_CONTRACT_ADDRESS.lower() and float(bid_amount_val) == 0.0:
             bid_amount_display_str += " (auto)"

        row_values = [
            str(entry.get("Wallet Address", "")),
            str(entry.get("Pool Name", "")),
            str(entry.get("Bid Time (UTC)", "")), 
            bid_amount_display_str,
            str(entry.get("Tx Hash (Short)", ""))
        ]
        report_lines.append(format_report_row(row_values, col_widths))
        report_lines.append("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")
        
    return "\n".join(report_lines) + "\n"

def generate_reward_summary_report(data: List[Dict[str, Any]]) -> str:
    """Generates the Reward Summary report string."""
    if not data:
        return "Reward Summary:\nNo reward summary data to report.\n"

    headers = ["Wallet ID", "Pool", "Bid Amount ($AG)", "Reward Amount ($AG)", "Net Gain ($AG)", "Note"]
    col_widths = [44, 12, 18, 21, 16, 10] 

    report_lines = ["Reward Summary:"]
    report_lines.append("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")
    report_lines.append(format_report_row(headers, col_widths))
    report_lines.append("+" + "+".join(["=" * (w + 2) for w in col_widths]) + "+")

    for entry in data:
        row_values = [
            str(entry.get("Wallet ID", "")),
            str(entry.get("Pool", "")),
            f"{entry.get('Bid Amount ($AG)', 0.0):.4f}",
            f"{entry.get('Reward Amount ($AG)', 0.0):.4f}",
            f"{entry.get('Net Gain ($AG)', 0.0):.4f}",
            str(entry.get("Note", "Standard"))
        ]
        report_lines.append(format_report_row(row_values, col_widths))
        report_lines.append("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")
        
    return "\n".join(report_lines) + "\n"

def generate_wallet_statistics_report(reward_data: List[Dict[str, Any]]) -> str:
    """Generates the Wallet Statistics report string from reward summary data."""
    if not reward_data:
        return "Wallet Statistics:\nNo data for wallet statistics.\n"

    stats: Dict[str, Dict[str, Any]] = {}
    for entry in reward_data:
        wallet_id = str(entry.get("Wallet ID"))
        net_gain = float(entry.get("Net Gain ($AG)", 0.0))

        if wallet_id not in stats:
            stats[wallet_id] = {"Auctions Won": 0, "Total Profit ($AG)": 0.0}
        
        stats[wallet_id]["Auctions Won"] += 1
        stats[wallet_id]["Total Profit ($AG)"] += net_gain
    
    for wallet_id in stats:
        stats[wallet_id]["Total Profit ($AG)"] = round(stats[wallet_id]["Total Profit ($AG)"], 4)

    headers = ["Wallet Address", "Auctions Won", "Total Profit ($AG)"]
    col_widths = [44, 16, 22] 

    report_lines = ["Wallet Statistics:"]
    report_lines.append("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")
    report_lines.append(format_report_row(headers, col_widths))
    report_lines.append("+" + "+".join(["=" * (w + 2) for w in col_widths]) + "+")

    sorted_stats = sorted(stats.items(), key=lambda item: item[1]["Total Profit ($AG)"], reverse=True)

    for wallet_id, stat_values in sorted_stats:
        row_values = [
            wallet_id,
            str(stat_values["Auctions Won"]),
            f"{stat_values['Total Profit ($AG)']:.4f}" 
        ]
        report_lines.append(format_report_row(row_values, col_widths))
        report_lines.append("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")
        
    return "\n".join(report_lines) + "\n"

# --- END REPORT GENERATION FUNCTIONS ---

def log_auction_state_to_file():
    """
    Logs the current auction state (rewards, bids, hotlist, etc.) to a file asynchronously.
    The filename is determined by the global `current_auction_log_file`.
    Appends a JSON snapshot to the log file.
    """
    # Access global variables needed for logging state
    global current_auction_log_file, highest_bids, last_rewards, POOLS, POOLS_ORIGINAL, last_bids
    global AUCTION_END_TIME, WALLET_ADDRESS, POOL_BIDDER_CONTRACT_ADDRESS, hot_list_created

    def _write_log_data():
        if not current_auction_log_file:
            logger.warning("Cannot log auction state: `current_auction_log_file` is not set.")
            return

        try:
            # Create deep copies of mutable data structures to capture a snapshot
            copied_highest_bids = copy.deepcopy(highest_bids)
            copied_last_rewards = copy.deepcopy(last_rewards)
            # POOLS reflects the current hotlist if active, otherwise all original pools
            # If hot_list_created is true, POOLS is the hotlist. Otherwise, it's POOLS_ORIGINAL.
            # For clarity in the log, always log what POOLS currently contains.
            copied_current_monitored_pools = copy.deepcopy(POOLS)
            copied_last_bids = copy.deepcopy(last_bids)
            
            log_timestamp_utc = datetime.datetime.now(datetime.timezone.utc)
            
            current_tte_str = "N/A"
            auction_end_time_iso = "N/A"
            if AUCTION_END_TIME is not None:
                current_tte_str = f"{AUCTION_END_TIME - log_timestamp_utc.timestamp():.2f}s"
                auction_end_time_iso = datetime.datetime.fromtimestamp(AUCTION_END_TIME, tz=datetime.timezone.utc).isoformat()

            # Prepare data for JSON serialization
            # Use pool names instead of addresses as keys where it makes sense for readability
            # but keep original addresses if needed for other processing of the log.
            
            highest_bids_log_friendly = {
                POOLS_ORIGINAL.get(pid, str(pid)): {
                    "amount": data.get("amount"),
                    "user": data.get("user"),
                    "tx_hash": data.get("tx_hash")
                } for pid, data in copied_highest_bids.items()
            }
            
            last_rewards_log_friendly = {
                POOLS_ORIGINAL.get(pid, str(pid)): reward
                for pid, reward in copied_last_rewards.items()
            }

            current_monitored_pools_log_friendly = [
                POOLS_ORIGINAL.get(pid, str(pid)) for pid in copied_current_monitored_pools.keys()
            ]

            last_bids_log_friendly = {
                POOLS_ORIGINAL.get(pid, str(pid)): amount
                for pid, amount in copied_last_bids.items()
            }

            log_entry = {
                "log_snapshot_timestamp_utc": log_timestamp_utc.isoformat(),
                "time_to_auction_end_approx": current_tte_str,
                "auction_end_time_utc": auction_end_time_iso,
                "operator_wallet_address": WALLET_ADDRESS,
                "pool_bidder_contract_address": POOL_BIDDER_CONTRACT_ADDRESS,
                "hotlist_active": hot_list_created,
                "current_monitored_pools": current_monitored_pools_log_friendly,
                "highest_bids_snapshot": highest_bids_log_friendly,
                "last_rewards_snapshot": last_rewards_log_friendly,
                "last_failed_or_low_bids_snapshot": last_bids_log_friendly
            }

            with open(current_auction_log_file, 'a') as f:
                f.write(json.dumps(log_entry, indent=4, default=str)) # default=str for any non-serializable types
                f.write("\n,\n") # Add a comma for easier parsing if multiple JSON objects are in the file, though a list of objects would be better
            logger.info(f"Successfully appended auction state snapshot to {current_auction_log_file}")

        except Exception as e:
            logger.error(f"Failed to write auction state to {current_auction_log_file}: {e}", exc_info=True)

    # Run the file writing in a separate daemon thread
    log_thread = threading.Thread(target=_write_log_data)
    log_thread.daemon = True  # Allows main program to exit even if thread is still running
    log_thread.start()


w3_instance = connect_to_blockchain(SONIC_RPC_URLS)
silver_fees_contract_instance = w3_instance.eth.contract(address=SILVER_FEES_CONTRACT_ADDRESS, abi=SILVER_FEES_ABI)
pool_bidder_contract_instance = w3_instance.eth.contract(address=POOL_BIDDER_CONTRACT_ADDRESS, abi=POOL_BIDDER_ABI)

async def handle_auction_end(now_datetime_utc: datetime.datetime, w3: Web3, sf_contract: Contract):
    """
    Handles the end of an auction cycle: logging rewards, generating reports, and resetting state.
    """
    global bid_log_data, reward_summary_data
    
    logger.info(f"REAL AUCTION_END_TIME ({AUCTION_END_TIME.isoformat() if AUCTION_END_TIME else 'N/A'}) is in the past (now: {now_datetime_utc.isoformat()}). Processing rewards and resetting.")
    if SIMULATE_FINAL_WINDOW_MODE and simulation_has_run:
        logger.info("[SIMULATION] Note: Real auction cycle ended. Simulation was completed.")

    # Log rewards for won auctions
    for pool_id, pool_name in POOLS_ORIGINAL.items():
        final_bid_info = highest_bids.get(pool_id)
        if final_bid_info and final_bid_info.get("user") == POOL_BIDDER_CONTRACT_ADDRESS:
            bid_amount = final_bid_info.get("amount", 0.0)
            reward_amount = last_rewards.get(pool_id, 0.0)
            if reward_amount > 0:
                net_gain = round(reward_amount - bid_amount, 4)
                reward_summary_data.append({
                    "Wallet ID": POOL_BIDDER_CONTRACT_ADDRESS, "Pool": pool_name,
                    "Bid Amount ($AG)": bid_amount, "Reward Amount ($AG)": reward_amount,
                    "Net Gain ($AG)": net_gain, "Note": "Standard"
                })
                logger.info(f"Reward Logged for {pool_name}: Bid {bid_amount:.4f}, Reward {reward_amount:.4f}, Net Gain {net_gain:.4f}")

    # Generate and print reports
    logger.info("--- Generating End-of-Cycle Reports ---")
    bid_report_str = generate_bid_log_report(bid_log_data)
    reward_summary_str = generate_reward_summary_report(reward_summary_data)
    wallet_stats_str = generate_wallet_statistics_report(reward_summary_data)
    
    print("\n" + "="*100)
    print("AUCTION CYCLE COMPLETED - REPORTS:")
    print("="*100)
    print(bid_report_str)
    print(reward_summary_str)
    print(wallet_stats_str)
    print("="*100 + "\n")

    # Clear logs and reset state for the next cycle
    bid_log_data.clear()
    logger.info("Bid log for the completed cycle has been cleared. Reward summary is cumulative.")
    
    await reset_auction_cycle_state(w3, sf_contract)
    
    # Log the state after reset to a file
    log_auction_state_to_file()

async def main(force_mode: bool = False):
    global AUCTION_END_TIME, highest_bids, last_rewards, event_scanner_failed
    global hot_list_created, last_bids, early_bid_times_queue, early_bids_processed_for_threshold
    global last_reward_check_time, POOLS, pool_locks, GLOBAL_AVG_BLOCK_TIME, CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK
    global w3_instance, silver_fees_contract_instance, pool_bidder_contract_instance
    global simulated_auction_end_time_override, simulation_has_run # Added for simulation mode

    if not POOLS_ORIGINAL: POOLS_ORIGINAL.update(POOLS); 
    if not pool_locks: pool_locks = {pid: Lock() for pid in POOLS_ORIGINAL.keys()} 

    # --- Dynamic Average Block Time Estimation ---
    BLOCK_TIME_ESTIMATION_SECONDS = 15
    logger.info(f"Estimating average block time over ~{BLOCK_TIME_ESTIMATION_SECONDS} seconds...")
    try:
        startup_block_num = w3_instance.eth.block_number
        startup_time = time.monotonic()
        await asyncio.sleep(BLOCK_TIME_ESTIMATION_SECONDS)
        current_block_num = w3_instance.eth.block_number
        current_time = time.monotonic()

        blocks_passed = current_block_num - startup_block_num
        time_elapsed = current_time - startup_time

        if blocks_passed > 0 and time_elapsed > 0:
            avg_block_time_calc = time_elapsed / blocks_passed
            GLOBAL_AVG_BLOCK_TIME = avg_block_time_calc
            logger.info(f"Estimated average block time: {GLOBAL_AVG_BLOCK_TIME:.2f} seconds ({blocks_passed} blocks in {time_elapsed:.2f}s).")
        elif time_elapsed <=0:
            logger.warning(f"Time elapsed for block time estimation was zero or negative. Defaulting avg block time to {GLOBAL_AVG_BLOCK_TIME}s.")
        else: # blocks_passed was 0 or less
            logger.warning(f"No new blocks observed in {time_elapsed:.2f} seconds. Defaulting avg block time to {GLOBAL_AVG_BLOCK_TIME}s.")
            if blocks_passed == 0:
                 logger.info("Consider increasing BLOCK_TIME_ESTIMATION_SECONDS if no blocks are consistently mined during the estimation period.")

    except Exception as e_bt_est:
        logger.error(f"Error during dynamic block time estimation: {e_bt_est}. Using default {GLOBAL_AVG_BLOCK_TIME}s.", exc_info=True)
    # --- End Dynamic Average Block Time Estimation ---

    event_scan_state = InMemoryState()
    logger.info(f"Operator Wallet: {WALLET_ADDRESS}, PoolBidder Contract: {POOL_BIDDER_CONTRACT_ADDRESS}")

    # --- Configure EventScanner for SnatchAuction events ---
    event_scanner = None 
    try:
        snatch_auction_event_object = silver_fees_contract_instance.events.SnatchAuction
        event_scanner = EventScanner(
            w3=w3_instance,
            contract_to_scan=silver_fees_contract_instance,
            state=event_scan_state,
            event_types=[snatch_auction_event_object],
            max_chunk_scan_size=100 
        )
        logger.info("EventScanner configured for SnatchAuction events.")
    except Exception as e:
        logger.error(f"Failed to configure EventScanner for SnatchAuction: {e}", exc_info=True)
        event_scanner = None 
    # --- End EventScanner Configuration ---
    
    try: 
        account = w3_instance.eth.account.from_key(PRIVATE_KEY)
        if Web3.to_checksum_address(WALLET_ADDRESS) != Web3.to_checksum_address(account.address):
            raise ValueError("Wallet address in .env does not match private key for PoolBidder owner.")
    except Exception as e: logger.critical(f"Private key/Wallet validation error: {e}"); return

    #logger.info("POOL SUPREMACY BID ATTEMPTS STARTED")
    #attempt_pool_supremacy_bids(w3_instance, silver_fees_contract_instance, pool_bidder_contract_instance)

    if force_mode: 
        event_scan_state.reset() 
        logger.info("Force mode activated. EventScanner state reset.")

    last_pb_bal_check_time, last_bid_update_time, last_evt_scan_time = 0.0, 0.0, 0.0
    
    try: await reset_auction_cycle_state(w3_instance, silver_fees_contract_instance)
    except Exception as e: logger.critical(f"Initial auction state setup failed: {e}. Exiting."); sys.exit(1)

    global current_auction_log_file # Ensure we're using the global
    if AUCTION_END_TIME:
        auction_end_dt = AUCTION_END_TIME
        current_auction_log_file = f"auction_state_{auction_end_dt.strftime('%Y%m%d_%H%M%S')}.log"
        logger.info(f"Auction state snapshot will be logged to: {current_auction_log_file}")
    else:
        # This case should ideally not be reached if reset_auction_cycle_state is robust
        current_auction_log_file = f"auction_state_unknown_time_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
        logger.error(f"AUCTION_END_TIME was not set prior to log file naming (after reset_auction_cycle_state). Using fallback: {current_auction_log_file}")
    while True:
        try:
            now_datetime_utc = datetime.datetime.now(datetime.timezone.utc)
            now_timestamp_utc = now_datetime_utc.timestamp()

            if AUCTION_END_TIME is None: 
                logger.error("AUCTION_END_TIME is None mid-loop, attempting reset.")
                await reset_auction_cycle_state(w3_instance, silver_fees_contract_instance)
                continue
            
            if SIMULATE_FINAL_WINDOW_MODE:
                if not simulation_has_run: # Only set up and run the simulation once per script execution
                    if simulated_auction_end_time_override is None: # Initial setup for the single run
                        simulated_auction_end_time_override = now_timestamp_utc + SIMULATE_TTE_START
                        simulation_has_run = True # Mark that we are doing/have done the one simulation run
                        logger.info(f"[SIMULATION] Starting ONE-TIME simulated TTE. Fake end time set to: {datetime.datetime.fromtimestamp(simulated_auction_end_time_override, tz=datetime.timezone.utc).isoformat()}")

                if simulated_auction_end_time_override is not None: # If simulation has been set up (or has run)
                    time_to_auction_end = simulated_auction_end_time_override - now_timestamp_utc
                    # Optional: Log when the single simulation cycle effectively ends
                    if time_to_auction_end < -1.5 and time_to_auction_end > -5.0 : # Log for a brief period after it ends
                         # sausage = True # User had this to prevent log spam, can be removed or kept as a silent placeholder
                         pass
                else: # Simulation mode is on, but has_run is true, and override is None (should not happen with this logic if it ran once)
                      # This case means the simulation finished, and we revert to real TTE for other checks.
                    time_to_auction_end = (AUCTION_END_TIME - now_timestamp_utc) if AUCTION_END_TIME else float('inf')
            else: # Not in simulation mode
                time_to_auction_end = (AUCTION_END_TIME - now_timestamp_utc) if AUCTION_END_TIME else float('inf')


            # Real auction end processing:
            # This should only happen based on the REAL AUCTION_END_TIME, not the simulated one.
            real_tte = (AUCTION_END_TIME - now_timestamp_utc) if AUCTION_END_TIME else float('inf')

            if real_tte < -1.5:
                await handle_auction_end(now_datetime_utc, w3_instance, silver_fees_contract_instance)
                continue

            logger.info(f"TTE: {time_to_auction_end:.2f}s")

            final_bid_window_active = (0 < time_to_auction_end <= FINAL_BID_WINDOW_START_TTE) or \
                                      (force_mode and 0 < time_to_auction_end)      
            
            if final_bid_window_active:
                logger.info(f"Entering Final Bidding Phase (TTE: {time_to_auction_end:.2f}s). Monitored Pools: {list(POOLS.keys())}")
                
                pools_for_initial_batch_ids: List[str] = []
                amounts_for_initial_batch_eth: List[float] = []
                initial_batch_pre_bid_amounts: Dict[str, float] = {} 

                for p_id, p_name in POOLS.items(): 
                    current_tte_for_initial_check = AUCTION_END_TIME - datetime.datetime.now(datetime.timezone.utc).timestamp()
                    if current_tte_for_initial_check <= MINIMUM_TTE_FOR_REACTION: 
                        logger.debug(f"TTE {current_tte_for_initial_check:.3f}s too low, breaking from initial pool iteration for final bidding.")
                        break 
                    try:
                        current_bidder_onchain, onchain_bid_amount = get_current_bid(w3_instance, silver_fees_contract_instance, p_id, timeout=0.2)
                        reward = last_rewards.get(p_id) 
                        if reward is None: 
                            logger.warning(f"No cached reward for {p_name} in final bid (initial batch), skipping.")
                            continue 
                        
                        is_my_contract_leading = (current_bidder_onchain == POOL_BIDDER_CONTRACT_ADDRESS)
                        
                        if is_my_contract_leading:
                            if abs(highest_bids.get(p_id, {}).get("amount", 0.0) - onchain_bid_amount) > 1e-9 :
                                highest_bids[p_id] = {"amount": onchain_bid_amount, "user": POOL_BIDDER_CONTRACT_ADDRESS, "tx_hash": highest_bids.get(p_id, {}).get("tx_hash", "on-chain-update-final")}
                            logger.debug(f"Final Batch Prep: Skipping {p_name}, PoolBidder already leads with {onchain_bid_amount:.4f} $AG.")
                            continue

                        hypothetical_next_bid_by_contract = round(onchain_bid_amount + CONTRACT_DEFAULT_INCREMENT_AMOUNT, 8) if onchain_bid_amount > 0 else CONTRACT_DEFAULT_INCREMENT_AMOUNT
                        if reward > hypothetical_next_bid_by_contract + FINAL_BATCH_AUTO_INCREMENT_PROFIT_MARGIN:
                            logger.info(f"Final Batch Add: {p_name}. Profitable for auto +{CONTRACT_DEFAULT_INCREMENT_AMOUNT}AG (R:{reward:.3f} OnChain:{onchain_bid_amount:.3f})")
                            pools_for_initial_batch_ids.append(p_id)
                            amounts_for_initial_batch_eth.append(0.0) 
                            initial_batch_pre_bid_amounts[p_id] = onchain_bid_amount 
                        else:
                            logger.debug(f"Skipping {p_name} from final batch: Reward {reward:.3f} not sufficient for auto +{CONTRACT_DEFAULT_INCREMENT_AMOUNT}AG (Hypothetical: {hypothetical_next_bid_by_contract:.3f} + margin {FINAL_BATCH_AUTO_INCREMENT_PROFIT_MARGIN:.3f})")
                    except Exception as e_fb_pool_loop:
                        logger.error(f"Error processing pool {p_name} in final bid initial batch prep: {e_fb_pool_loop}", exc_info=False)
                
                my_reactive_bids: Dict[str, float] = {} # For normal hyper-reactive mode
                initial_batch_optimistic_bids: Dict[str, float] = {} # For dumb bidding mode seeding
                batch_success = False # Initialize batch_success

                if pools_for_initial_batch_ids:
                    logger.info(f"Attempting initial final MULTI-BID for {len(pools_for_initial_batch_ids)} pools. Urgency: NORMAL")
                    batch_success, batch_tx_hash = place_multiple_bids_with_poolbidder(
                        w3_instance, pool_bidder_contract_instance,
                        pools_for_initial_batch_ids, amounts_for_initial_batch_eth, # amounts_for_initial_batch_eth contains 0.0 for auto-increment
                        urgency="NORMAL"
                    )
                    if batch_success and batch_tx_hash:
                        logger.info(f"Initial Final MULTI-BID SUBMITTED. Tx: {batch_tx_hash}")
                        for i_optimistic, p_id_succeeded in enumerate(pools_for_initial_batch_ids):
                            pre_bid_amt = initial_batch_pre_bid_amounts.get(p_id_succeeded, 0.0)
                            # If 0.0 was sent, contract aims for pre_bid_amt + increment.
                            # If a specific amount was sent (not current use case for initial batch but for completeness), that's the amount.
                            optimistic_amount_achieved = round(pre_bid_amt + CONTRACT_DEFAULT_INCREMENT_AMOUNT, 8) if amounts_for_initial_batch_eth[i_optimistic] == 0.0 else round(amounts_for_initial_batch_eth[i_optimistic], 8)
                            
                            highest_bids[p_id_succeeded] = {
                                "amount": optimistic_amount_achieved, 
                                "user": POOL_BIDDER_CONTRACT_ADDRESS,
                                "tx_hash": batch_tx_hash
                            }
                            initial_batch_optimistic_bids[p_id_succeeded] = optimistic_amount_achieved
                            # my_reactive_bids is populated later, only if not in DUMB_BIDDING_MODE
                    else:
                        logger.error(f"Initial Final MULTI-BID FAILED. Details: {batch_tx_hash if batch_tx_hash else 'No tx_hash / Pre-flight fail'}")
                
                # --- DUMB BIDDING MODE or HYPER-REACTIVE ---
                if DUMB_BIDDING_MODE and batch_success and initial_batch_optimistic_bids:
                    logger.info(f"DUMB_BIDDING_MODE active. Repeating bids up to {DUMB_BID_REPEATS} times.")
                    current_dumb_bid_targets = dict(initial_batch_optimistic_bids)

                    for i_dumb_repeat in range(DUMB_BID_REPEATS):
                        await asyncio.sleep(DUMB_BID_REPEAT_DELAY)
                        current_tte_dumb = AUCTION_END_TIME - time.time()

                        if current_tte_dumb <= MINIMUM_TTE_FOR_DUMB_BID:
                            logger.info(f"Dumb Bid Repeat {i_dumb_repeat+1}: TTE {current_tte_dumb:.3f}s too low (<= {MINIMUM_TTE_FOR_DUMB_BID}s), stopping dumb bids.")
                            break
                        
                        logger.info(f"--- Dumb Bid Repeat Attempt {i_dumb_repeat+1}/{DUMB_BID_REPEATS} (TTE: {current_tte_dumb:.3f}s) ---")
                        pools_for_this_dumb_repeat: List[str] = []
                        amounts_for_this_dumb_repeat: List[float] = [] # Will be 0.0s
                        next_iteration_optimistic_targets: Dict[str, float] = {}

                        if not current_dumb_bid_targets:
                            logger.info(f"Dumb Bid Repeat {i_dumb_repeat+1}: No targets left from previous iteration. Stopping.")
                            break

                        for p_id_dumb, last_aimed_bid_dumb in current_dumb_bid_targets.items():
                            # Assumption: opponent outbid our last_aimed_bid_dumb by one increment
                            assumed_opponent_bid_dumb = round(last_aimed_bid_dumb + CONTRACT_DEFAULT_INCREMENT_AMOUNT, 8)
                            # Our contract will then aim to bid one increment over that
                            my_next_target_if_dumb_bidding = round(assumed_opponent_bid_dumb + CONTRACT_DEFAULT_INCREMENT_AMOUNT, 8)
                            
                            reward_dumb = last_rewards.get(p_id_dumb)

                            if reward_dumb is not None and reward_dumb > my_next_target_if_dumb_bidding + DUMB_BID_PROFIT_MARGIN_ASSUMPTION:
                                logger.info(f"  Dumb Repeat {i_dumb_repeat+1} for {POOLS_ORIGINAL.get(p_id_dumb, p_id_dumb)}: Profitable to aim for ~{my_next_target_if_dumb_bidding:.4f}. (Last Aim: {last_aimed_bid_dumb:.4f}, Assumed Opponent: {assumed_opponent_bid_dumb:.4f}, Reward: {reward_dumb:.4f})")
                                pools_for_this_dumb_repeat.append(p_id_dumb)
                                amounts_for_this_dumb_repeat.append(0.0) # Send 0.0 for contract to auto-increment
                                next_iteration_optimistic_targets[p_id_dumb] = my_next_target_if_dumb_bidding
                            else:
                                logger.info(f"  Dumb Repeat {i_dumb_repeat+1} for {POOLS_ORIGINAL.get(p_id_dumb, p_id_dumb)}: SKIPPING. Not profitable or no reward. Next Target: {my_next_target_if_dumb_bidding:.4f}, Reward: {reward_dumb}")
                        
                        if not pools_for_this_dumb_repeat:
                            logger.info(f"Dumb Bid Repeat {i_dumb_repeat+1}: No pools left that are profitable for a dumb repeat bid. Stopping.")
                            break

                        dumb_repeat_batch_success, dumb_repeat_tx_hash = place_multiple_bids_with_poolbidder(
                            w3_instance, pool_bidder_contract_instance,
                            pools_for_this_dumb_repeat, amounts_for_this_dumb_repeat, # Sending 0.0s
                            urgency="URGENT"
                        )

                        if dumb_repeat_batch_success and dumb_repeat_tx_hash:
                            logger.info(f"Dumb Bid Repeat {i_dumb_repeat+1} SUCCEEDED. Tx: {dumb_repeat_tx_hash}")
                            current_dumb_bid_targets = dict(next_iteration_optimistic_targets) # Update targets for the next dumb repeat
                            for p_id_succeeded_dumb, new_amount_dumb in next_iteration_optimistic_targets.items():
                                highest_bids[p_id_succeeded_dumb] = {
                                    "amount": new_amount_dumb,
                                    "user": POOL_BIDDER_CONTRACT_ADDRESS,
                                    "tx_hash": dumb_repeat_tx_hash
                                }
                        else:
                            logger.error(f"Dumb Bid Repeat {i_dumb_repeat+1} FAILED. Tx/Error: {dumb_repeat_tx_hash if dumb_repeat_tx_hash else 'Pre-flight fail'}. Stopping dumb bids.")
                            break # Stop dumb bidding if a batch fails
                    logger.info("--- Finished Dumb Bidding Mode sequence ---")

                elif not DUMB_BIDDING_MODE and batch_success and initial_batch_optimistic_bids:
                    # Populate my_reactive_bids only if not in dumb mode and initial batch was successful
                    my_reactive_bids = dict(initial_batch_optimistic_bids)
                    logger.info(f"Entering HYPER-REACTIVE mode for pools: {[POOLS_ORIGINAL.get(p, p) for p in my_reactive_bids.keys()]}")
                    
                    # --- EXISTING HYPER-REACTIVE LOOP (indented under this 'elif') ---
                    while True:
                        now_ts_in_hyper_loop = datetime.datetime.now(datetime.timezone.utc).timestamp()
                        current_tte_hyper = AUCTION_END_TIME - now_ts_in_hyper_loop
                        
                        if current_tte_hyper <= MINIMUM_TTE_FOR_REACTION:
                            logger.info(f"Exiting HYPER-REACTIVE mode: TTE {current_tte_hyper:.3f}s <= {MINIMUM_TTE_FOR_REACTION}s")
                            break
                        
                        if not my_reactive_bids: 
                            logger.info("Exiting HYPER-REACTIVE mode: No more pools to watch.")
                            break

                        for p_id_hyper in list(my_reactive_bids.keys()): 
                            current_tte_for_pool_check = AUCTION_END_TIME - datetime.datetime.now(datetime.timezone.utc).timestamp()
                            if current_tte_for_pool_check <= MINIMUM_TTE_FOR_REACTION:
                                continue 

                            current_bidder_onchain_hyper, onchain_bid_amount_hyper = get_current_bid(
                                w3_instance, silver_fees_contract_instance, p_id_hyper, timeout=GET_CURRENT_BID_TIMEOUT_HYPER
                            )
                            my_last_intended_bid_for_pool = my_reactive_bids.get(p_id_hyper, 0.0)

                            is_outbid = False
                            if current_bidder_onchain_hyper != POOL_BIDDER_CONTRACT_ADDRESS:
                                if onchain_bid_amount_hyper >= my_last_intended_bid_for_pool - 1e-9: 
                                    is_outbid = True
                            elif onchain_bid_amount_hyper > my_last_intended_bid_for_pool + 1e-9: 
                                is_outbid = True 
                            
                            if is_outbid:
                                reward_hyper = last_rewards.get(p_id_hyper)
                                if reward_hyper is not None:
                                    next_bid_target = round(onchain_bid_amount_hyper + CONTRACT_DEFAULT_INCREMENT_AMOUNT, 8)
                                    
                                    is_profitable_to_counter = reward_hyper > next_bid_target + FINAL_BATCH_AUTO_INCREMENT_PROFIT_MARGIN
                                    
                                    should_attempt_reactive_bid = False
                                    if current_bidder_onchain_hyper != POOL_BIDDER_CONTRACT_ADDRESS: 
                                        should_attempt_reactive_bid = True
                                    elif next_bid_target > my_last_intended_bid_for_pool + 1e-9: 
                                        should_attempt_reactive_bid = True

                                    if is_profitable_to_counter and should_attempt_reactive_bid :
                                        logger.info(f"Hyper-Reactive: Condition met for {POOLS_ORIGINAL.get(p_id_hyper, p_id_hyper)}. Onchain: {onchain_bid_amount_hyper:.4f} by {current_bidder_onchain_hyper}. MyLastIntended: {my_last_intended_bid_for_pool:.4f}. Countering for ~{next_bid_target:.4f}. TTE: {current_tte_hyper:.3f}s")
                                        bid_success_reactive, tx_hash_reactive = place_bid_with_poolbidder(
                                            w3_instance, pool_bidder_contract_instance, 0.0, p_id_hyper, "URGENT"
                                        )
                                        if bid_success_reactive:
                                            my_reactive_bids[p_id_hyper] = next_bid_target 
                                            highest_bids[p_id_hyper] = { 
                                                "amount": next_bid_target,
                                                "user": POOL_BIDDER_CONTRACT_ADDRESS,
                                                "tx_hash": tx_hash_reactive 
                                            }
                                    elif not is_profitable_to_counter:
                                        logger.debug(f"Hyper-Reactive: Skipping {POOLS_ORIGINAL.get(p_id_hyper, p_id_hyper)}, not profitable. Reward: {reward_hyper:.4f}, Next Target: {next_bid_target:.4f}")
                                    else: 
                                        logger.debug(f"Hyper-Reactive: We are likely leading {POOLS_ORIGINAL.get(p_id_hyper, p_id_hyper)} and new target {next_bid_target:.4f} isn't a necessary increase over last intended {my_last_intended_bid_for_pool:.4f}, or current onchain {onchain_bid_amount_hyper:.4f} is already good.")
                                        if current_bidder_onchain_hyper == POOL_BIDDER_CONTRACT_ADDRESS and onchain_bid_amount_hyper > my_last_intended_bid_for_pool:
                                            my_reactive_bids[p_id_hyper] = onchain_bid_amount_hyper
                                else: 
                                    logger.warning(f"Hyper-Reactive: No reward data for {POOLS_ORIGINAL.get(p_id_hyper, p_id_hyper)}, cannot counter bid.")
                            elif current_bidder_onchain_hyper == POOL_BIDDER_CONTRACT_ADDRESS and onchain_bid_amount_hyper > my_last_intended_bid_for_pool + 1e-9:
                                my_reactive_bids[p_id_hyper] = onchain_bid_amount_hyper
                                logger.debug(f"Hyper-Reactive: Confirmed our lead on {POOLS_ORIGINAL.get(p_id_hyper, p_id_hyper)} with updated amount {onchain_bid_amount_hyper:.4f}")
                            
                            if len(my_reactive_bids) > 1: await asyncio.sleep(0.001) 

                        await asyncio.sleep(HYPER_REACTIVE_CHECK_INTERVAL) 
                    logger.info("Exited HYPER-REACTIVE mode.")
                else: 
                    logger.info("No pools identified for initial final batch bid, or initial batch failed/no pools to watch. Skipping hyper-reactive mode.")

            if time_to_auction_end > TTE_THRESHOLD_BALANCE_CHECK and \
               (now_timestamp_utc - last_pb_bal_check_time >= 600):
                try:
                    ag_c = w3_instance.eth.contract(address=AG_TOKEN, abi=[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}])
                    pb_ag_bal = float(w3_instance.from_wei(ag_c.functions.balanceOf(POOL_BIDDER_CONTRACT_ADDRESS).call(), 'ether'))
                    logger.info(f"PoolBidder Contract $AG Balance: {pb_ag_bal:.4f} $AG")
                    if pb_ag_bal < 0.5: logger.warning(f"PoolBidder contract $AG balance LOW: {pb_ag_bal:.4f}")
                except Exception as e: logger.error(f"PoolBidder $AG balance check failed: {e}")
                last_pb_bal_check_time = now_timestamp_utc

            if not final_bid_window_active: 
                bid_upd_interval = 0.5 if time_to_auction_end <= 60 else 3.5
                if time_to_auction_end > TTE_THRESHOLD_BID_UPDATE and \
                   (now_timestamp_utc - last_bid_update_time >= bid_upd_interval):
                    pools_for_update = POOLS if hot_list_created and POOLS else POOLS_ORIGINAL
                    logger.info(f"Bid update interval reached. Updating {len(pools_for_update)} pools.")
                    await update_bids_from_chain(w3_instance, silver_fees_contract_instance, pools_for_update)
                    last_bid_update_time = now_timestamp_utc
                
                # Determine if early bids should be processed (not in simulation and conditions met)
                should_process_early_bids = (
                    not SIMULATE_FINAL_WINDOW_MODE and
                    early_bid_times_queue and
                    0 < time_to_auction_end <= early_bid_times_queue[0] and
                    not early_bids_processed_for_threshold.get(early_bid_times_queue[0], False)
                )

                if should_process_early_bids:
                    current_threshold = early_bid_times_queue[0]
                    logger.info(f"Preparing batch for early bids (threshold <= {current_threshold}s, TTE: {time_to_auction_end:.2f}s)")
                    
                    # Fetch rewards specifically for early bids if interval met
                    if now_timestamp_utc - last_reward_check_time >= EARLY_BID_REWARD_FETCH_INTERVAL:
                        logger.info("Fetching rewards for early bird batch...")
                        rewards_data = fetch_pool_rewards_data(silver_fees_contract_instance)
                        for r_info in rewards_data: 
                            if "error" not in r_info and r_info.get("pool_id"):
                                last_rewards[r_info["pool_id"]] = r_info["reward_agency"]
                        last_reward_check_time = now_timestamp_utc
                    
                    pools_to_bid_ids: List[str] = []
                    bid_amounts_for_pools: List[float] = []

                    for p_id, p_name in POOLS_ORIGINAL.items(): 
                        reward = last_rewards.get(p_id)
                        if reward is not None and EARLY_BID_MIN_REWARD_FOR_0_1_AG_BID <= reward < EARLY_BID_MAX_REWARD_FOR_0_1_AG_BID: 
                            current_onchain_bid_amount = highest_bids.get(p_id, {}).get("amount", 0.0)
                            if current_onchain_bid_amount < EARLY_BID_FIXED_AMOUNT: 
                                if p_id in last_bids and EARLY_BID_FIXED_AMOUNT <= round(last_bids[p_id], 8):
                                    logger.debug(f"Skipping {p_name} for early multi-bid: {EARLY_BID_FIXED_AMOUNT} AG is at or below last known failing bid {last_bids[p_id]:.4f}")
                                    continue
                                logger.info(f"Adding to early bird batch: {p_name} (Reward: {reward:.4f}), Bid: {EARLY_BID_FIXED_AMOUNT} $AG")
                                pools_to_bid_ids.append(p_id)
                                bid_amounts_for_pools.append(EARLY_BID_FIXED_AMOUNT)
                    
                    if pools_to_bid_ids: 
                        logger.info(f"Attempting multi-bid for {len(pools_to_bid_ids)} early bird pools.")
                        multi_bid_success, tx_details = place_multiple_bids_with_poolbidder(
                            w3_instance, pool_bidder_contract_instance, 
                            pools_to_bid_ids, bid_amounts_for_pools, urgency="NORMAL"
                        )
                        if multi_bid_success:
                            logger.info(f"Early bird multi-bid SUCCESSFUL. Tx: {tx_details}")
                            for i, pool_id_succeeded in enumerate(pools_to_bid_ids):
                                highest_bids[pool_id_succeeded] = {
                                    "amount": bid_amounts_for_pools[i],
                                    "user": POOL_BIDDER_CONTRACT_ADDRESS, 
                                    "tx_hash": tx_details
                                }
                                last_bids.pop(pool_id_succeeded, None) 
                        else:
                            logger.error(f"Early bird multi-bid FAILED. Details: {tx_details}")
                    else:
                        logger.info("No pools met criteria for early bird batch at this time.")

                    early_bids_processed_for_threshold[current_threshold] = True
                    if early_bid_times_queue and early_bid_times_queue[0] == current_threshold: # Check again in case queue was exhausted
                        early_bid_times_queue.pop(0)
                        logger.info(f"Processed early bid threshold {current_threshold}s. Remaining queue: {early_bid_times_queue}")

                elif SIMULATE_FINAL_WINDOW_MODE and early_bid_times_queue and \
                     0 < time_to_auction_end <= early_bid_times_queue[0] and \
                     not early_bids_processed_for_threshold.get(early_bid_times_queue[0], False):
                    # This log ensures we know why early bids didn't run if it was due to simulation mode
                    # and the TTE would have otherwise triggered it.
                    logger.debug(f"[SIMULATION] Skipping early bids processing block due to SIMULATE_FINAL_WINDOW_MODE active (Simulated TTE: {time_to_auction_end:.2f}s would have met threshold {early_bid_times_queue[0]}s).")

                if not hot_list_created and HOT_LIST_CREATION_END_TTE < time_to_auction_end <= HOT_LIST_CREATION_START_TTE:
                    # Note: time_to_auction_end here will be the simulated TTE if SIMULATE_FINAL_WINDOW_MODE is True.
                    # Hotlist creation might behave unexpectedly if SIMULATE_TTE_START is within its window.
                    # For robust simulation of just the final window, ensure SIMULATE_TTE_START is below HOT_LIST_CREATION_END_TTE (25s).
                    # Current SIMULATE_TTE_START = 20.0s, so this is fine.
                    logger.info(f"Creating Hot List (TTE: {time_to_auction_end:.2f}s). Using cached rewards only.")
                    temp_hot_pools = {}
                    for pid, pname in POOLS_ORIGINAL.items():
                        reward = last_rewards.get(pid)
                        if reward is None: 
                            logger.debug(f"HotList: Skipping {pname}, no cached reward.")
                            continue
                        cb = highest_bids.get(pid, {}).get("amount", 0.0)
                        hypothetical_next_bid_val = cb + CONTRACT_DEFAULT_INCREMENT_AMOUNT if cb > 0 else CONTRACT_DEFAULT_INCREMENT_AMOUNT
                        if reward > hypothetical_next_bid_val + HOT_LIST_MIN_POTENTIAL_PROFIT:
                            temp_hot_pools[pid] = pname
                            logger.info(f"HotList ADD: {pname} (R:{reward:.3f} C:{cb:.3f} ProfitPostContractBid:{(reward - hypothetical_next_bid_val):.3f})")
                    
                    if temp_hot_pools: 
                        POOLS.clear(); POOLS.update(temp_hot_pools)
                        pool_locks = {hpid: Lock() for hpid in POOLS.keys()} 
                        logger.info(f"Hot List ACTIVE with {len(POOLS)} pools: {list(POOLS.values())}")
                    else: 
                        logger.warning("No pools qualified for Hot List. Final bidding will consider all original pools.")
                        if not POOLS: 
                            POOLS.update(POOLS_ORIGINAL)
                            pool_locks = {hpid: Lock() for hpid in POOLS.keys()}
                    hot_list_created = True
                    log_auction_state_to_file() # Log state after hotlist determination
                                                            
                is_early_bid_fetch_time = (early_bid_times_queue and 
                                        (early_bid_times_queue[0] - EARLY_BID_REWARD_FETCH_INTERVAL - 2 < time_to_auction_end <= early_bid_times_queue[0] + 5))
                can_do_periodic_fetch = (time_to_auction_end > MIN_TTE_FOR_GENERAL_REWARD_FETCH and not is_early_bid_fetch_time and (now_timestamp_utc - last_reward_check_time >= PERIODIC_REWARD_FETCH_INTERVAL))

                if can_do_periodic_fetch:
                    logger.info(f"Periodic reward fetch (TTE: {time_to_auction_end:.2f}s)")
                    rewards_data = fetch_pool_rewards_data(silver_fees_contract_instance)
                    for r_info in rewards_data:
                        if "error" not in r_info and r_info.get("pool_id"):
                            last_rewards[r_info["pool_id"]] = r_info["reward_agency"]
                    last_reward_check_time = now_timestamp_utc
                elif time_to_auction_end <= MIN_TTE_FOR_GENERAL_REWARD_FETCH:
                    logger.debug(f"Skipping general periodic reward fetch: TTE {time_to_auction_end:.2f}s <= MIN_TTE_FOR_GENERAL_REWARD_FETCH ({MIN_TTE_FOR_GENERAL_REWARD_FETCH}s).")
                elif is_early_bid_fetch_time:
                    logger.debug(f"Skipping general periodic reward fetch: Early bid window is active/imminent.")
            else: # This else is for 'if not final_bid_window_active:'
                logger.debug(f"Final bidding window is active (TTE: {time_to_auction_end:.2f}s). Skipping regular updates and early bids.")
                
            # --- Periodic SnatchAuction Event Scanning ---
            EVENT_SCAN_INTERVAL = 20 
            if time_to_auction_end > TTE_THRESHOLD_EVENT_SCAN and \
               event_scanner and (now_timestamp_utc - last_evt_scan_time >= EVENT_SCAN_INTERVAL):
                try:
                    current_from_block = 0
                    is_initial_catchup_scan = False
                    if CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK is not None:
                        current_from_block = CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK
                        is_initial_catchup_scan = True
                        # We will reset state and prime highest_block_scanned_successfully later, only if current_from_block <= to_block
                    else:
                        current_from_block = event_scan_state.get_last_scanned_block() + 1

                    to_block_original = w3_instance.eth.block_number
                    to_block = to_block_original

                    if is_initial_catchup_scan:
                        if to_block > current_from_block + MAX_INITIAL_CATCHUP_SCAN_BLOCKS:
                            to_block = current_from_block + MAX_INITIAL_CATCHUP_SCAN_BLOCKS
                            logger.info(f"Initial event scan range very large. Capping to {MAX_INITIAL_CATCHUP_SCAN_BLOCKS} blocks. New to_block: {to_block}")
                    
                    # For regular scans (or capped initial scans), if TTE is low, reduce the range further
                    # Determine the TTE to use for this decision: real TTE if available and not in an active simulation phase, else use the current (possibly simulated) time_to_auction_end
                    actual_tte_for_scan_decision = (AUCTION_END_TIME - now_timestamp_utc) if AUCTION_END_TIME and not (SIMULATE_FINAL_WINDOW_MODE and simulated_auction_end_time_override is not None and (simulated_auction_end_time_override - now_timestamp_utc) > 0) else time_to_auction_end

                    if actual_tte_for_scan_decision < TTE_FOR_REDUCED_SCAN_RANGE:
                        max_permissible_to_block = current_from_block + MAX_BLOCKS_PER_SCAN_LOW_TTE
                        if to_block > max_permissible_to_block: # Only reduce if current to_block is larger
                            to_block = max_permissible_to_block
                            logger.debug(f"Low TTE ({actual_tte_for_scan_decision:.2f}s): Event scan range reduced. New to_block: {to_block} (Original: {to_block_original})")

                    if current_from_block <= to_block:
                        if is_initial_catchup_scan:
                            logger.info(f"Event scan (cycle start): Using calculated start block {current_from_block} up to {to_block}.")
                            event_scan_state.reset()
                            if current_from_block > 0:
                                event_scan_state.highest_block_scanned_successfully = current_from_block - 1
                                logger.debug(f"Primed event_scan_state.highest_block_scanned_successfully to {current_from_block - 1}")
                            CYCLE_SPECIFIC_EVENT_SCAN_START_BLOCK = None  # Consume it

                        logger.info(f"Scanning for SnatchAuction events from block {current_from_block} to {to_block}")
                        processed_event_details, num_chunks = await event_scanner.scan(start_bn=current_from_block, end_bn=to_block, timeout=10)
                        
                        if processed_event_details:
                            logger.info(f"Processing {len(processed_event_details)} SnatchAuction events for bid log.")
                            for evt_detail in processed_event_details:
                                try:
                                    if evt_detail.get("event") == "SnatchAuction":
                                        args = evt_detail.get("args", {})
                                        bidder_address = args.get("user")
                                        pool_address = args.get("poolToSteal")
                                        bid_wei = args.get("auctionAmount")

                                        if not all([bidder_address, pool_address, bid_wei is not None]):
                                            logger.warning(f"Skipping event due to missing args: {evt_detail}")
                                            continue

                                        pool_name = POOLS_ORIGINAL.get(Web3.to_checksum_address(pool_address), str(pool_address))
                                        bid_eth = w3_instance.from_wei(bid_wei, 'ether')

                                        bid_log_data.append({
                                            "Wallet Address": Web3.to_checksum_address(bidder_address),
                                            "Pool Name": pool_name,
                                            "Bid Time (UTC)": evt_detail.get("timestamp"),
                                            "Bid Amount ($AG)": float(bid_eth),
                                            "Tx Hash (Short)": evt_detail.get("tx_hash", "")[:12] + ".."
                                        })
                                except Exception as e_proc:
                                    logger.error(f"Error processing single SnatchAuction event for bid_log: {evt_detail}, Error: {e_proc}", exc_info=True)
                        # Ensure highest_block_scanned_successfully is updated to to_block,
                        # as event_scanner.scan -> state.end_chunk handles chunk ends, but this ensures the overall range is marked.
                        event_scan_state.highest_block_scanned_successfully = max(event_scan_state.highest_block_scanned_successfully, to_block)
                        logger.debug(f"Event scan state: highest_block_scanned_successfully updated to {event_scan_state.highest_block_scanned_successfully} (to_block was {to_block})")
                        
                    else:
                        logger.debug(f"SnatchAuction event scan: No new blocks to scan (from_block: {current_from_block}, to_block: {to_block})")
                    last_evt_scan_time = now_timestamp_utc
                except Exception as e_scan:
                    logger.error(f"Error during periodic SnatchAuction event scan: {e_scan}", exc_info=True)
        except ConnectionError as e_conn_main:
            logger.error(f"Main Loop RPC Connection Error: {e_conn_main}. Attempting to re-initialize...")
            await asyncio.sleep(10)
            try:
                w3_instance = connect_to_blockchain(SONIC_RPC_URLS)
                silver_fees_contract_instance = w3_instance.eth.contract(address=SILVER_FEES_CONTRACT_ADDRESS, abi=SILVER_FEES_ABI)
                pool_bidder_contract_instance = w3_instance.eth.contract(address=POOL_BIDDER_CONTRACT_ADDRESS, abi=POOL_BIDDER_ABI)
                logger.info("Successfully re-initialized Web3 and contract instances after connection error.")
                await reset_auction_cycle_state(w3_instance, silver_fees_contract_instance) 
            except Exception as e_reinit_fail:
                logger.critical(f"Failed to re-initialize after connection error: {e_reinit_fail}. Sleeping for 60s.")
                await asyncio.sleep(60)
        except ContractLogicError as e_cl_main: logger.error(f"Main Loop ContractLogicError: {e_cl_main}"); await asyncio.sleep(3)
        except Exception as e_unhandled_main: logger.exception(f"Unhandled Main Loop Error: {e_unhandled_main}"); await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        if not POOLS_ORIGINAL: POOLS_ORIGINAL.update(POOLS) 
        if not pool_locks: pool_locks = {pid: Lock() for pid in POOLS_ORIGINAL.keys()}
        force_arg = "--force" in sys.argv
        asyncio.run(main(force_mode=force_arg))
    except KeyboardInterrupt: logger.info("Script terminated by user (Ctrl+C).")
    except Exception as e_crit_top:
        logger.critical(f"Critical script error at top level: {e_crit_top}", exc_info=True)
        sys.exit(1)
