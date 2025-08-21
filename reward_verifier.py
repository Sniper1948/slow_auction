import json
import sys
from web3 import Web3
import time
import requests
import uuid
from math import ceil

# --- CONFIGURATION ---

# RPC endpoint for the Sonic blockchain
SONIC_RPC_URL = "https://rpc.soniclabs.com"

# SilverFees contract address
SILVER_FEES_CONTRACT_ADDRESS = Web3.to_checksum_address("0xfeE899CF3Ef6FCf338Da86453c334973e015c236")

# ABIs
SILVER_FEES_ABI = [{"inputs":[{"internalType":"address","name":"_silver","type":"address"},{"internalType":"address","name":"_silverFeesGiveaway","type":"address"},{"internalType":"address","name":"_burnAddress","type":"address"},{"internalType":"address","name":"_flareProgramAddress","type":"address"},{"internalType":"address","name":"_swapRouter","type":"address"},{"internalType":"address","name":"_nftPositionManager","type":"address"},{"internalType":"address","name":"_communityVault","type":"address"},{"internalType":"address","name":"_teamMultisig","type":"address"},{"internalType":"address","name":"_automate","type":"address"},{"internalType":"address","name":"_wrappedToken","type":"address"},{"internalType":"string","name":"_flareCID","type":"string"},{"internalType":"string","name":"_snatchCID","type":"string"},{"internalType":"string","name":"_feesTokenCID","type":"string"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"internalType":"address","name":"target","type":"address"}],"name":"AddressEmptyCode","type":"error"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"AddressInsufficientBalance","type":"error"},{"inputs":[],"name":"FailedInnerCall","type":"error"},{"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"OwnableInvalidOwner","type":"error"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"OwnableUnauthorizedAccount","type":"error"},{"inputs":[{"internalType":"address","name":"token","type":"address"}],"name":"SafeERC20FailedOperation","type":"error"},{"inputs":[{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"length","type":"uint256"}],"name":"StringsInsufficientHexLength","type":"error"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint256","name":"teamFees","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"weeklyGiveawayFees","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"buybackFees","type":"uint256"}],"name":"EditedFees","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"teamMultisig","type":"address"}],"name":"EditedTeamMultisig","type":"event"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint256","name":"forTeam","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"forWeeklyGiveaway","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"forBuyback","type":"uint256"}],"name":"FeesManagementExecuted","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"token","type":"address"},{"indexed":False,"internalType":"bytes32","name":"taskId","type":"bytes32"}],"name":"FeesTokenAdded","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"token","type":"address"}],"name":"FeesTokenRemoved","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"token","type":"address"},{"indexed":False,"internalType":"uint256","name":"amountIn","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"amountOut","type":"uint256"}],"name":"FeesTokenSwapped","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"user","type":"address"},{"indexed":False,"internalType":"uint256","name":"auctionAmount","type":"uint256"}],"name":"FlareAuction","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"token","type":"address"},{"indexed":False,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"FlareBuyback","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"user","type":"address"},{"indexed":False,"internalType":"uint256","name":"buybackAmount","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"programAmount","type":"uint256"}],"name":"FlareExecution","type":"event"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint256","name":"fees","type":"uint256"},{"indexed":False,"internalType":"address","name":"token","type":"address"}],"name":"GelatoFeesCheck","type":"event"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"bytes32","name":"id","type":"bytes32"}],"name":"GelatoTaskCancelFailed","type":"event"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"bytes32","name":"id","type":"bytes32"}],"name":"GelatoTaskCanceled","type":"event"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"bytes32","name":"id","type":"bytes32"}],"name":"GelatoTaskCreated","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":True,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferStarted","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":True,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"user","type":"address"},{"indexed":True,"internalType":"address","name":"poolToSteal","type":"address"},{"indexed":False,"internalType":"uint256","name":"auctionAmount","type":"uint256"}],"name":"SnatchAuction","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"user","type":"address"},{"indexed":True,"internalType":"address","name":"poolToSteal","type":"address"}],"name":"SnatchExecution","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"user","type":"address"},{"indexed":True,"internalType":"address","name":"rewardsPool","type":"address"},{"indexed":False,"internalType":"address","name":"rewardsToken","type":"address"},{"indexed":False,"internalType":"uint256","name":"rewardsAmount","type":"uint256"}],"name":"SnatchSteal","type":"event"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"bool","name":"swapToWrappedToken","type":"bool"}],"name":"SwapToWrappedToken","type":"event"},{"anonymous":False,"inputs":[],"name":"SwapTypeChanged","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"timestamp","type":"uint256"}],"name":"SyncFeesManagement","type":"event"},{"anonymous":False,"inputs":[],"name":"SyncFeesStarted","type":"event"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"TokensBurned","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"to","type":"address"},{"indexed":False,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"WithdrawnNative","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"token","type":"address"},{"indexed":False,"internalType":"address","name":"to","type":"address"},{"indexed":False,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"WithdrawnToken","type":"event"},{"inputs":[],"name":"acceptOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"tokenAddress","type":"address"}],"name":"addFeesToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"automate","outputs":[{"internalType":"contract IAutomate","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"burnAddress","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_amount","type":"uint256"}],"name":"buyTickets","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_user","type":"address"},{"internalType":"uint256","name":"_amount","type":"uint256"}],"name":"buyTicketsBurn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"taskId","type":"bytes32"}],"name":"cancelTask","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"taskId","type":"bytes32"}],"name":"cancelTaskCall","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"pool","type":"address"}],"name":"cancelTaskSnatch","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"communityVault","outputs":[{"internalType":"contract IAlgebraCommunityVault","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"dedicatedMsgSender","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"drawWinner","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_swapRouter","type":"address"}],"name":"editAlgebraSwapRouter","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_communityVault","type":"address"}],"name":"editCommunityVault","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"teamFees","type":"uint256"},{"internalType":"uint256","name":"weeklyGiveawayFees","type":"uint256"},{"internalType":"uint256","name":"buybackFees","type":"uint256"}],"name":"editFees","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"string","name":"scriptCID","type":"string"}],"name":"editFeesTokenCID","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"string","name":"flareCID","type":"string"}],"name":"editFlareCID","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_flareProgramAddress","type":"address"}],"name":"editFlareProgramAddress","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"flareProgramPercentage","type":"uint256"}],"name":"editFlareProgramPercentage","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_teamMultisig","type":"address"}],"name":"editMultisig","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_nftPositionManager","type":"address"}],"name":"editNftPositionManager","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_silver","type":"address"}],"name":"editSilver","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_silverFeesGiveaway","type":"address"}],"name":"editSilverFeesGiveaway","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"string","name":"snatchCID","type":"string"}],"name":"editSnatchCID","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_wrappedToken","type":"address"}],"name":"editwrappedToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"executeFeesManagement","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"executeFlare","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"poolToSteal","type":"address"}],"name":"executeSnatch","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"feesManagementData","outputs":[{"internalType":"uint256","name":"teamFees","type":"uint256"},{"internalType":"uint256","name":"weeklyGiveawayFees","type":"uint256"},{"internalType":"uint256","name":"buybackFees","type":"uint256"},{"components":[{"internalType":"uint256","name":"agWeeklyGiveawayAmount","type":"uint256"},{"internalType":"uint256","name":"wrappedTokenWeeklyGiveawayAmount","type":"uint256"},{"internalType":"uint256","name":"agFlareAmount","type":"uint256"},{"internalType":"uint256","name":"wrappedTokenFlareAmount","type":"uint256"},{"internalType":"uint256","name":"agSnatchAmount","type":"uint256"},{"internalType":"uint256","name":"wrappedTokenSnatchAmount","type":"uint256"}],"internalType":"struct FeesRedistributionData","name":"redistributionData","type":"tuple"},{"internalType":"uint256","name":"flareProgramPercentage","type":"uint256"},{"internalType":"address","name":"bannedFlareUser","type":"address"},{"internalType":"bool","name":"flareEnded","type":"bool"},{"internalType":"bool","name":"snatchEnded","type":"bool"},{"internalType":"string","name":"flareCID","type":"string"},{"internalType":"string","name":"snatchCID","type":"string"},{"internalType":"bool","name":"swapChanged","type":"bool"},{"internalType":"bool","name":"swapToWrappedToken","type":"bool"},{"internalType":"uint256","name":"firstExecution","type":"uint256"},{"internalType":"uint256","name":"lastExecution","type":"uint256"},{"internalType":"bytes32","name":"taskId","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"feesTokenData","outputs":[{"internalType":"string","name":"scriptCID","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenAddress","type":"address"}],"name":"feesTokenTaskId","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_amountToBurn","type":"uint256"},{"internalType":"address","name":"buybackToken","type":"address"}],"name":"flare","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"}],"name":"flareAddWhitelistedToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"tokenToSwap","type":"address"},{"internalType":"address","name":"tokenAddress","type":"address"},{"components":[{"internalType":"bytes","name":"path","type":"bytes"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"}],"internalType":"struct ExactInputParams","name":"swapArgs","type":"tuple"}],"name":"flareBuyback","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"flareData","outputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint256","name":"bidAmount","type":"uint256"},{"internalType":"address","name":"buybackToken","type":"address"},{"internalType":"bytes32","name":"taskId","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"}],"name":"flareIsWhitelistedToken","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"flareLastBid","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"flareProgramAddress","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"}],"name":"flareRemoveWhitelistedToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"gelato1Balance","outputs":[{"internalType":"contract IGelato1Balance","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getAllBids","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"isSwapToWrappedToken","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"nftPositionManager","outputs":[{"internalType":"contract IAlgebraNFTPositionManager","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"pendingOwner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenAddress","type":"address"}],"name":"removeFeesToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bool","name":"swapToWrappedToken","type":"bool"}],"name":"setSwapToWrappedToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"silverFeesGiveaway","outputs":[{"internalType":"contract SilverFeesGiveaway","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"silverToken","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_amountToBurn","type":"uint256"},{"internalType":"address","name":"poolToSteal","type":"address"}],"name":"snatch","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"snatchData","outputs":[{"components":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint256","name":"bidAmount","type":"uint256"}],"internalType":"struct SnatchPerPoolData","name":"perPoolData","type":"tuple"},{"internalType":"uint256","name":"lastExecution","type":"uint256"},{"internalType":"address","name":"bannedUser","type":"address"},{"internalType":"bytes32","name":"taskId","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"snatchIsPoolBided","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"address","name":"pool","type":"address"}],"name":"snatchLastBid","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"snatchPoolsBids","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"address","name":"rewardsPool","type":"address"},{"internalType":"address","name":"rewardsToken","type":"address"},{"internalType":"uint256","name":"rewardsAmount","type":"uint256"}],"name":"snatchSteal","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"time","type":"uint256"}],"name":"startSyncSystem","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"tokenAddress","type":"address"},{"components":[{"internalType":"bytes","name":"path","type":"bytes"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"}],"internalType":"struct ExactInputParams","name":"swapArgs","type":"tuple"}],"name":"swapFeesToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"swapRouter","outputs":[{"internalType":"contract IAlgebraSwapRouter","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"syncFeesLastSync","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"syncFeesManagement","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"syncFeesManagementData","outputs":[{"internalType":"uint256","name":"time","type":"uint256"},{"internalType":"uint256","name":"lastSync","type":"uint256"},{"internalType":"uint256","name":"nextSync","type":"uint256"},{"internalType":"bytes32","name":"taskId","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"syncFeesTime","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"teamMultisig","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenAddress","type":"address"}],"name":"tokenAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenAddress","type":"address"}],"name":"tokenAmountVault","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_to","type":"address"}],"name":"withdrawNative","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"address","name":"_to","type":"address"}],"name":"withdrawToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"wrappedToken","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"stateMutability":"payable","type":"receive"}]

try:
    with open('algebra_pool.abi.json', 'r') as f:
        ALGEBRA_POOL_ABI = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading algebra_pool.abi.json: {e}")
    sys.exit(1)

try:
    with open('erc20.abi.json', 'r') as f:
        ERC20_ABI = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading erc20.abi.json: {e}")
    sys.exit(1)


# From auction_bid.py
AG_TOKEN = Web3.to_checksum_address("0x005851f943ee2957b1748957f26319e4f9edebc1")
HEADERS = {
    "authority": "silverswap.io", "accept": "*/*", "accept-language": "en-GB,en;q=0.8",
    "content-type": "text/plain;charset=UTF-8", "origin": "https://silverswap.io",
    "referer": "https://silverswap.io/auctions/snatch",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "sec-gpc": "1", "cache-control": "no-cache", "pragma": "no-cache"
}


def get_api_rewards(w3: Web3, silver_fees_contract, pool_address: str) -> dict:
    """
    Fetches the rewards for a given pool from the SilverSwap API.
    """
    results = {}
    try:
        snatch_data_tuple = silver_fees_contract.functions.snatchData(pool_address).call()
        last_exec = snatch_data_tuple[1]
        period_hrs = ceil((time.time() - last_exec) / 3600) if last_exec > 0 else 12
        if period_hrs <= 0: period_hrs = 1

        payload = {"chainId": 146, "poolId": pool_address, "tokenGiven": AG_TOKEN, "periodInHours": period_hrs, "id": str(uuid.uuid4())}
        api_url = f"https://silverswap.io/api/getLiquidityPoolInterests?t={int(time.time()*1000)}"

        with requests.Session() as session:
            resp = session.post(api_url, headers=HEADERS, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            reward_val = data.get("totalInGiven", 0) * 0.425
            results['api_rewards'] = {
                "reward_agency": reward_val,
                "total_value_raw": data.get("totalInGiven", 0),
                "api_period_hours_sent": period_hrs,
                "api_last_execution_used": last_exec
            }
            return results

    except requests.exceptions.RequestException as he:
        print(f"API request error: {he}")
        return {"error": str(he)}
    except Exception as e:
        print(f"An error occurred during API reward fetching: {e}")
        return {"error": str(e)}


def get_onchain_rewards(w3: Web3, pool_address: str) -> dict:
    """
    Calculates the total rewards for a given pool by combining pending fees
    from the pool contract and the fees stored in the SilverFees community vault.
    """
    results = {}

    try:
        # Instantiate contracts
        pool_contract = w3.eth.contract(address=pool_address, abi=ALGEBRA_POOL_ABI)
        silver_fees_contract = w3.eth.contract(address=SILVER_FEES_CONTRACT_ADDRESS, abi=SILVER_FEES_ABI)

        # Get pool tokens
        token0_address = pool_contract.functions.token0().call()
        token1_address = pool_contract.functions.token1().call()
        results['token0_address'] = token0_address
        results['token1_address'] = token1_address

        # Get pending community fees from the pool
        pending_fees0, pending_fees1 = pool_contract.functions.getCommunityFeePending().call()

        # Get fees stored in the community vault via SilverFees contract
        vault_fees0 = silver_fees_contract.functions.tokenAmountVault(token0_address).call()
        vault_fees1 = silver_fees_contract.functions.tokenAmountVault(token1_address).call()

        # Calculate total rewards for each token
        total_rewards0_wei = pending_fees0 + vault_fees0
        total_rewards1_wei = pending_fees1 + vault_fees1

        # Get token decimals for formatting
        token0_contract = w3.eth.contract(address=token0_address, abi=ERC20_ABI)
        token1_contract = w3.eth.contract(address=token1_address, abi=ERC20_ABI)
        decimals0 = token0_contract.functions.decimals().call()
        decimals1 = token1_contract.functions.decimals().call()

        # Format rewards
        total_rewards0 = total_rewards0_wei / (10 ** decimals0)
        total_rewards1 = total_rewards1_wei / (10 ** decimals1)

        results['onchain_rewards'] = {
            'token0': {
                'address': token0_address,
                'amount_wei': total_rewards0_wei,
                'amount_formatted': total_rewards0,
                'decimals': decimals0
            },
            'token1': {
                'address': token1_address,
                'amount_wei': total_rewards1_wei,
                'amount_formatted': total_rewards1,
                'decimals': decimals1
            }
        }
        return results

    except Exception as e:
        print(f"An error occurred during on-chain reward calculation: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python reward_verifier.py <pool_address>")
        sys.exit(1)

    pool_to_check = sys.argv[1]
    if not Web3.is_address(pool_to_check):
        print(f"Error: Invalid pool address provided.")
        sys.exit(1)

    pool_to_check = Web3.to_checksum_address(pool_to_check)

    print(f"Connecting to Sonic RPC at {SONIC_RPC_URL}...")
    w3_instance = Web3(Web3.HTTPProvider(SONIC_RPC_URL))

    if not w3_instance.is_connected():
        print("Failed to connect to the RPC endpoint.")
        sys.exit(1)

    print("Connection successful.")
    print(f"\nVerifying rewards for pool: {pool_to_check}")

    # Instantiate SilverFees contract (needed by both functions)
    silver_fees_contract = w3_instance.eth.contract(address=SILVER_FEES_CONTRACT_ADDRESS, abi=SILVER_FEES_ABI)

    # --- Fetch Data ---
    print("\nFetching data from API and On-Chain...")
    onchain_data = get_onchain_rewards(w3_instance, pool_to_check)
    api_data = get_api_rewards(w3_instance, silver_fees_contract, pool_to_check)
    print("...fetch complete.")

    # --- Process and Compare ---
    api_rewards = api_data.get('api_rewards', {})
    onchain_rewards = onchain_data.get('onchain_rewards', {})

    if not api_rewards or not onchain_rewards:
        print("\nCould not retrieve all necessary data. Exiting.")
        if api_data.get('error'): print(f"API Error: {api_data.get('error')}")
        if onchain_data.get('error'): print(f"On-Chain Error: {onchain_data.get('error')}")
        sys.exit(1)

    # Determine the reward token
    is_wrapped = silver_fees_contract.functions.isSwapToWrappedToken().call()
    if is_wrapped:
        reward_token_address = silver_fees_contract.functions.wrappedToken().call()
        reward_token_name = "Wrapped Token"
    else:
        reward_token_address = silver_fees_contract.functions.silverToken().call()
        reward_token_name = "$AG"

    # Find the corresponding on-chain reward
    onchain_reward_to_compare = 0.0
    token0_info = onchain_rewards.get('token0', {})
    token1_info = onchain_rewards.get('token1', {})

    if token0_info.get('address') == reward_token_address:
        onchain_reward_to_compare = token0_info.get('amount_formatted', 0.0)
    elif token1_info.get('address') == reward_token_address:
        onchain_reward_to_compare = token1_info.get('amount_formatted', 0.0)

    # --- Display Results ---
    print("\n--- Reward Verification Results ---")
    print(f"Reward Token: {reward_token_name} ({reward_token_address})")
    print("-" * 35)

    api_reward_val = api_rewards.get('reward_agency', 0.0)
    print(f"API Result:          {api_reward_val:.18f}")
    print(f"On-Chain Result:     {onchain_reward_to_compare:.18f}")

    difference = abs(api_reward_val - onchain_reward_to_compare)
    print(f"Difference:          {difference:.18f}")

    print("-" * 35)
    print("\nNote: A small difference is expected due to fee accumulation over time and potential timing differences between API and on-chain queries.")

    print("\n--- Detailed On-Chain Data ---")
    print(f"  Token 0 ({token0_info.get('address')}): {token0_info.get('amount_formatted', 'N/A'):.18f}")
    print(f"  Token 1 ({token1_info.get('address')}): {token1_info.get('amount_formatted', 'N/A'):.18f}")
    print("--------------------------------\n")
