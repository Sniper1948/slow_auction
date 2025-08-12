import os
import json
import time
import uuid
from math import ceil
import requests
from typing import List, Dict, Any
from web3 import Web3
from web3.contract import Contract
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()

# RPC Configuration
SONIC_RPC_URLS = [
    "https://rpc.soniclabs.com",
    "https://rpc.ankr.com/sonic",
    "https://sonic.drpc.org",
    "https://sonic-rpc.publicnode.com:443"
]

# Contract Addresses
SILVER_FEES_CONTRACT_ADDRESS = Web3.to_checksum_address("0xfeE899CF3Ef6FCf338Da86453c334973e015c236")
AG_TOKEN = Web3.to_checksum_address("0x005851f943ee2957b1748957f26319e4f9edebc1")

# Pool Addresses & Names
POOLS = {
    Web3.to_checksum_address("0xd4988f9b3438a620d07f41b1415859aba038158a"): "WS-ZUPA",
    Web3.to_checksum_address("0x3dbf257817866ee785edd0329daf36b5c198c3fd"): "WS-ECO",
    Web3.to_checksum_address("0x741146bbd931aa7799979206df1ab61905512bed"): "WS-JOINT",
    Web3.to_checksum_address("0x72d158eeed476b875ec4e50bd56834c1dbfd372d"): "WS-GOGLZ",
    Web3.to_checksum_address("0x0139666fddd275d08353b248e42eea096d61d78f"): "WS-RACKS",
    Web3.to_checksum_address("0x9f46dd8f2a4016c26c1cf1f4ef90e5e1928d756b"): "WS-USDC",
    Web3.to_checksum_address("0x54e533E8d101f7C1660a5Cc62f841f2673c638BE"): "WS-AG",
    Web3.to_checksum_address("0x6671c0684b54e0a6f6ee2f878f2b217bca1f8291"): "WS-ANON",
    Web3.to_checksum_address("0xd451a16d7d5414abe8c883ed98aa3c47d00435ea"): "WS-SDIGGA",
    Web3.to_checksum_address("0x2d0ae637493bd895fde19b55e665e7dfbaebfc8d"): "WS-SCETH",
    Web3.to_checksum_address("0x9208db26a52b7046a94d1771dc629452c6c2fa20"): "WS-WETH",
    Web3.to_checksum_address("0x23802c542a5af9f09c31ce28ba669dcf641aa1f8"): "WS-EGGS",
    Web3.to_checksum_address("0x899fa124768994e5788f63d1b8bff0261a819bcf"): "WS-WHALE",
    Web3.to_checksum_address("0x86193d8058d9b80b9e0bf69de3279c7d7a9644ed"): "WS-DERP",
    Web3.to_checksum_address("0x5188885473bc80d7e2c8389b2ccda2b69e5d78e2"): "WS-THC",
    Web3.to_checksum_address("0x1b7d76d8ba70ec6d5cc7c1c4e38b591c9e4c2397"): "WS-PHANIC",
    Web3.to_checksum_address("0x6c9b8827c7fecd8e19d504d57308a50269343aad"): "AG-SCETH",
    Web3.to_checksum_address("0xcfaecabcb3ea73acc94202458cb4fcc0d077e894"): "USDC-ANON",
    Web3.to_checksum_address("0xa741c001e7d37b4e312ab60374c869a89bf894c4"): "USDC-SCUSD",
    Web3.to_checksum_address("0x9107c409838f09d487421bfdac2c45c1ab320eae"): "USDC-FRXUSD",
    Web3.to_checksum_address("0xcc3d28191e8567dfae1ea280dadb798cf3b4172c"): "SCETH-WETH",
    Web3.to_checksum_address("0xbc9726639897b4cdbdd97d6b8e067140e6de9403"): "HEDGY-ANON",
    Web3.to_checksum_address("0xa08851a8D67E26BBddF8c55cc0Dc649fb50164a5"): "USDC-AUR",
    Web3.to_checksum_address("0xd455bc762cd8606788516ab11f3116f8712db2d5"): "WS-SONIC",
    Web3.to_checksum_address("0x697aaBd91B48ee8066Ff46318D50ad361880Ef49"): "frxETH-WETH",
    Web3.to_checksum_address("0x55eD5A63a5e833DC6FCDf5B3e009963e1B473b50"): "WS-INDI",
    Web3.to_checksum_address("0x12c83F2615939b543E369F2b9D0230D574150E06"): "WS-SCUSD",
    Web3.to_checksum_address("0x8e788A87bEf84Be47fEa007868281Af3160F96e6"): "AG-USDC",
    Web3.to_checksum_address("0x581ea7d19DD893858abC7AcbB31Ea83c261A18F5"): "WS-HEDGY",
    Web3.to_checksum_address("0xD4B18Acd107874e446bC7e3f4f3d277Cb6c1523d"): "WS-WOOF"
}

# API Configuration
HEADERS = {
    "authority": "silverswap.io", "accept": "*/*", "accept-language": "en-GB,en;q=0.8",
    "content-type": "text/plain;charset=UTF-8", "origin": "https://silverswap.io",
    "referer": "https://silverswap.io/auctions/snatch",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
}

# Conversion Rate
S_TO_AG_RATE = 1.46

# --- Functions ---

def connect_to_blockchain(rpc_urls: List[str]) -> Web3:
    """Connects to the blockchain using a list of RPC URLs."""
    print("Attempting to connect to the blockchain...")
    for url in rpc_urls:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
            if w3.is_connected() and w3.eth.chain_id == 146:
                print(f"Successfully connected to {url}")
                return w3
        except Exception as e:
            print(f"Failed to connect to {url}: {e}")
    raise ConnectionError("Could not connect to any of the provided RPC URLs.")

def get_api_rewards(sf_contract: Contract) -> Dict[str, float]:
    """Fetches estimated rewards from the SilverSwap API for all pools."""
    print("\nFetching API rewards for all pools...")
    results = {}
    with requests.Session() as session:
        for pool_id, pool_name in POOLS.items():
            try:
                # The API needs the `lastExecution` time to calculate rewards.
                # It's part of the snatchData struct for each pool.
                # snatchData returns a tuple: (perPoolData, lastExecution, bannedUser, taskId)
                snatch_data_tuple = sf_contract.functions.snatchData(pool_id).call()
                last_exec = snatch_data_tuple[1]

                # Calculate period in hours, similar to the auction_bid script
                period_hrs = ceil((time.time() - last_exec) / 3600) if last_exec > 0 else 12
                if period_hrs <= 0: period_hrs = 1

                payload = {
                    "chainId": 146,
                    "poolId": pool_id,
                    "tokenGiven": AG_TOKEN,
                    "periodInHours": period_hrs,
                    "id": str(uuid.uuid4())
                }
                api_url = f"https://silverswap.io/api/getLiquidityPoolInterests?t={int(time.time()*1000)}"

                resp = session.post(api_url, headers=HEADERS, json=payload, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                # The reward is 42.5% of the total interest reported by the API
                reward_val = data.get("totalInGiven", 0) * 0.425
                results[pool_id] = reward_val
                # A small visual confirmation that work is being done
                print(f"  - Fetched for {pool_name}: {reward_val:.4f} $S")

            except requests.exceptions.RequestException as he:
                print(f"  - API Error for {pool_name}: {he}")
                results[pool_id] = 0.0
            except Exception as e:
                print(f"  - General Error for {pool_name}: {e}")
                results[pool_id] = 0.0
    print("Finished fetching API rewards.")
    return results

def get_total_snatch_rewards(sf_contract: Contract, w3: Web3) -> float:
    """Fetches the total amount of wrapped tokens available for snatch rewards."""
    print("\nFetching total snatch reward pot from contract...")
    try:
        # feesManagementData() returns a large tuple.
        # Index 3 corresponds to the FeesRedistributionData struct.
        fees_data = sf_contract.functions.feesManagementData().call()
        redistribution_data = fees_data[3]

        # In the FeesRedistributionData struct, wrappedTokenSnatchAmount is at index 5.
        total_rewards_wei = redistribution_data[5]

        # Convert from wei (assuming 18 decimals for the wrapped token)
        total_rewards = w3.from_wei(total_rewards_wei, 'ether')
        print(f"Successfully fetched total pot: {total_rewards:.4f} $S")
        return float(total_rewards)
    except Exception as e:
        print(f"Error fetching total snatch rewards: {e}")
        return 0.0

def get_onchain_pool_data(sf_contract: Contract, pool_id: str, w3: Web3) -> Dict[str, Any]:
    """Fetches on-chain data for a specific pool (bid, last execution)."""
    try:
        # snatchData returns a tuple: (perPoolData, lastExecution, bannedUser, taskId)
        # perPoolData is a nested tuple: (user, bidAmount)
        data = sf_contract.functions.snatchData(pool_id).call()

        bid_amount_wei = data[0][1]
        bid_amount_ag = w3.from_wei(bid_amount_wei, 'ether')

        last_execution_ts = data[1]

        return {
            "bid_amount": float(bid_amount_ag),
            "last_execution": last_execution_ts
        }
    except Exception as e:
        pool_name = POOLS.get(pool_id, "Unknown Pool")
        print(f"  - Error fetching on-chain data for {pool_name}: {e}")
        return {
            "bid_amount": 0.0,
            "last_execution": 0
        }

def print_results(analysis_data: List[Dict[str, Any]], total_pot: float):
    """Prints the final analysis in a formatted table."""
    print(f"\n\n--- Snatch Analysis ---")
    print(f"Total Snatch Reward Pot: {total_pot:.4f} $S (1 $S = {S_TO_AG_RATE} $AG)")
    print("-" * 100)

    # Header
    print(f"{'Pool Name':<14} | {'API Reward ($S)':>16} | {'API Reward ($AG)':>16} | {'Highest Bid ($AG)':>18} | {'Time Since Payout (H)':>22}")
    print("=" * 100)

    # Sort data by API reward in $AG for better readability
    sorted_data = sorted(analysis_data, key=lambda x: x['api_reward_ag'], reverse=True)

    # Data rows
    for item in sorted_data:
        print(f"{item['pool_name']:<14} | {item['api_reward_s']:>16.4f} | {item['api_reward_ag']:>16.4f} | {item['bid_amount']:>18.4f} | {item['hours_since_payout']:>22.2f}")

    print("-" * 100)

def main():
    """Main function to run the analysis."""
    print("--- SilverSwap Snatch Reward Analyzer ---")

    # Connect and setup contracts
    try:
        w3 = connect_to_blockchain(SONIC_RPC_URLS)
        with open('SilverFees.abi', 'r') as f:
            silver_fees_abi = json.load(f)
        sf_contract = w3.eth.contract(address=SILVER_FEES_CONTRACT_ADDRESS, abi=silver_fees_abi)
        print("Contract instance created.")
    except Exception as e:
        print(f"\nError during setup: {e}")
        return

    # 1. Fetch all data
    api_rewards = get_api_rewards(sf_contract)
    total_snatch_pot = get_total_snatch_rewards(sf_contract, w3)

    print("\nFetching on-chain data for all pools...")
    analysis_results = []
    for pool_id, pool_name in POOLS.items():
        # A small delay to avoid overwhelming the RPC endpoint
        time.sleep(0.1)
        onchain_data = get_onchain_pool_data(sf_contract, pool_id, w3)
        api_reward_s = api_rewards.get(pool_id, 0.0)

        last_exec = onchain_data['last_execution']
        hours_since_payout = (time.time() - last_exec) / 3600 if last_exec > 0 else 0.0

        analysis_results.append({
            "pool_name": pool_name,
            "api_reward_s": api_reward_s,
            "api_reward_ag": api_reward_s * S_TO_AG_RATE,
            "bid_amount": onchain_data['bid_amount'],
            "hours_since_payout": hours_since_payout
        })
    print("Finished fetching on-chain data.")

    # 2. Process and print results
    print_results(analysis_results, total_snatch_pot)

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()
