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

# Contract Addresses
SILVER_FEES_CONTRACT_ADDRESS = Web3.to_checksum_address("0xfeE899CF3Ef6FCf338Da86453c334973e015c236")
QUOTER_CONTRACT_ADDRESS = Web3.to_checksum_address("0xe1181313a39d850d3A20F11FF1A6a94a29A09404")

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

try:
    with open('quoter.abi.json', 'r') as f:
        QUOTER_ABI = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading quoter.abi.json: {e}")
    sys.exit(1)


def get_quote(w3, quoter_contract, token_in_address, token_out_address, amount_in_wei):
    """
    Gets a quote for swapping a token to another using the Quoter contract.
    The quoter contract is expected to revert with the quoted amount.
    """
    if amount_in_wei == 0:
        return 0
    try:
        # This call is expected to fail with a revert containing the quote data
        amount_out, _ = quoter_contract.functions.quoteExactInputSingle(
            token_in_address,
            token_out_address,
            amount_in_wei,
            0  # limitSqrtPrice (0 means no limit)
        ).call()
        # This part should ideally not be reached if the quoter works as expected
        return amount_out
    except Exception as e:
        # The revert reason should be encoded in the exception's data.
        # This logic attempts to parse the data from the error.
        if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict) and 'data' in e.args[0]:
            revert_data = e.args[0]['data']
            if isinstance(revert_data, str) and revert_data.startswith('0x'):
                hex_data = revert_data[2:]
                # The quoter returns (uint256 amountOut, uint16 fee), which is 64 bytes
                if len(hex_data) == 128:
                    try:
                        # Decode the data as (uint256, uint16)
                        decoded_data = w3.codec.decode(['uint256', 'uint16'], bytes.fromhex(hex_data))
                        return decoded_data[0]  # Return the amountOut
                    except Exception:
                        # Failed to decode, likely not a valid quote revert
                        pass
    # If any of the above fails, it means we couldn't get a quote
    return 0


# From auction_bid.py
AG_TOKEN = Web3.to_checksum_address("0x005851f943ee2957b1748957f26319e4f9edebc1")
POOLS = {
    "0xd4988f9b3438a620d07f41b1415859aba038158a": "WS-ZUPA",
    "0x3dbf257817866ee785edd0329daf36b5c198c3fd": "WS-ECO",
    "0x741146bbd931aa7799979206df1ab61905512bed": "WS-JOINT",
    "0x72d158eeed476b875ec4e50bd56834c1dbfd372d": "WS-GOGLZ",
    "0x0139666fddd275d08353b248e42eea096d61d78f": "WS-RACKS",
    "0x9f46dd8f2a4016c26c1cf1f4ef90e5e1928d756b": "WS-USDC",
    "0x54e533E8d101f7C1660a5Cc62f841f2673c638BE": "AG-WS",
    "0x6671c0684b54e0a6f6ee2f878f2b217bca1f8291": "WS-ANON",
    "0xd451a16d7d5414abe8c883ed98aa3c47d00435ea": "WS-SDIGGA",
    "0x2d0ae637493bd895fde19b55e665e7dfbaebfc8d": "WS-SCETH",
    "0x9208db26a52b7046a94d1771dc629452c6c2fa20": "WS-WETH",
    "0x23802c542a5af9f09c31ce28ba669dcf641aa1f8": "WS-EGGS",
    "0x899fa124768994e5788f63d1b8bff0261a819bcf": "WS-WHALE",
    "0x86193d8058d9b80b9e0bf69de3279c7d7a9644ed": "WS-DERP",
    "0x5188885473bc80d7e2c8389b2ccda2b69e5d78e2": "WS-THC",
    "0x1b7d76d8ba70ec6d5cc7c1c4e38b591c9e4c2397": "WS-PHANIC",
    "0x6c9b8827c7fecd8e19d504d57308a50269343aad": "AG-SCETH",
    "0xcfaecabcb3ea73acc94202458cb4fcc0d077e894": "USDC-ANON",
    "0xa741c001e7d37b4e312ab60374c869a89bf894c4": "USDC-SCUSD",
    "0x9107c409838f09d487421bfdac2c45c1ab320eae": "USDC-FRXUSD",
    "0xcc3d28191e8567dfae1ea280dadb798cf3b4172c": "SCETH-WETH",
    "0xbc9726639897b4cdbdd97d6b8e067140e6de9403": "HEDGY-ANON",
    "0xa08851a8D67E26BBddF8c55cc0Dc649fb50164a5": "USDC-AUR",
    "0xd455bc762cd8606788516ab11f3116f8712db2d5": "WS-SONIC",
    "0x697aaBd91B48ee8066Ff46318D50ad361880Ef49": "frxETH-WETH",
    "0x55eD5A63a5e833DC6FCDf5B3e009963e1B473b50": "WS-INDI",
    "0x12c83F2615939b543E369F2b9D0230D574150E06": "WS-SCUSD",
    "0x8e788A87bEf84Be47fEa007868281Af3160F96e6": "AG-USDC",
    "0x581ea7d19DD893858abC7AcbB31Ea83c261A18F5": "WS-HEDGY",
    "0xD4B18Acd107874e446bC7e3f4f3d277Cb6c1523d": "WS-WOOF"
}
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
        # Don't print error, just return it
        return {"error": str(he)}
    except Exception as e:
        # Don't print error, just return it
        return {"error": str(e)}


def get_onchain_rewards(w3: Web3, quoter_contract, silver_fees_contract, wrapped_token_address, pool_address: str) -> dict:
    """
    Calculates the total on-chain rewards for a given pool and provides detailed diagnostic data.
    """
    try:
        pool_contract = w3.eth.contract(address=pool_address, abi=ALGEBRA_POOL_ABI)

        # Get pool tokens and their details
        token0_address = pool_contract.functions.token0().call()
        token1_address = pool_contract.functions.token1().call()

        token0_contract = w3.eth.contract(address=token0_address, abi=ERC20_ABI)
        token1_contract = w3.eth.contract(address=token1_address, abi=ERC20_ABI)

        token0_symbol = token0_contract.functions.symbol().call()
        token1_symbol = token1_contract.functions.symbol().call()
        token0_decimals = token0_contract.functions.decimals().call()
        token1_decimals = token1_contract.functions.decimals().call()

        # Get accumulated fees
        pending_fees0, pending_fees1 = pool_contract.functions.getCommunityFeePending().call()
        vault_fees0 = silver_fees_contract.functions.tokenAmountVault(token0_address).call()
        vault_fees1 = silver_fees_contract.functions.tokenAmountVault(token1_address).call()
        total_rewards0_wei = pending_fees0 + vault_fees0
        total_rewards1_wei = pending_fees1 + vault_fees1

        # Get exchange rates against wS
        unit_token0 = 10**token0_decimals
        unit_token1 = 10**token1_decimals

        rate0_in_ws_wei = get_quote(w3, quoter_contract, token0_address, wrapped_token_address, unit_token0) if token0_address != wrapped_token_address else unit_token0
        rate1_in_ws_wei = get_quote(w3, quoter_contract, token1_address, wrapped_token_address, unit_token1) if token1_address != wrapped_token_address else unit_token1

        wrapped_token_contract = w3.eth.contract(address=wrapped_token_address, abi=ERC20_ABI)
        wrapped_token_decimals = wrapped_token_contract.functions.decimals().call()

        rate0_in_ws = rate0_in_ws_wei / (10**wrapped_token_decimals)
        rate1_in_ws = rate1_in_ws_wei / (10**wrapped_token_decimals)

        # Calculate total reward value in wS
        token0_value_in_ws_wei = (total_rewards0_wei * rate0_in_ws_wei) / unit_token0 if unit_token0 > 0 else 0
        token1_value_in_ws_wei = (total_rewards1_wei * rate1_in_ws_wei) / unit_token1 if unit_token1 > 0 else 0
        total_reward_in_ws_wei = token0_value_in_ws_wei + token1_value_in_ws_wei

        # Apply the 42.5% multiplier
        final_reward_wei = total_reward_in_ws_wei * 0.425
        final_reward_formatted = final_reward_wei / (10**wrapped_token_decimals)

        return {
            "total_onchain_reward": final_reward_formatted,
            "details": {
                "token0": {
                    "symbol": token0_symbol,
                    "amount": total_rewards0_wei / (10**token0_decimals),
                    "rate_in_ws": rate0_in_ws
                },
                "token1": {
                    "symbol": token1_symbol,
                    "amount": total_rewards1_wei / (10**token1_decimals),
                    "rate_in_ws": rate1_in_ws
                }
            }
        }

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print(f"Connecting to Sonic RPC at {SONIC_RPC_URL}...")
    w3_instance = Web3(Web3.HTTPProvider(SONIC_RPC_URL))

    if not w3_instance.is_connected():
        print("Failed to connect to the RPC endpoint.")
        sys.exit(1)

    print("Connection successful.")

    # Instantiate contracts
    silver_fees_contract = w3_instance.eth.contract(address=SILVER_FEES_CONTRACT_ADDRESS, abi=SILVER_FEES_ABI)
    quoter_contract = w3_instance.eth.contract(address=QUOTER_CONTRACT_ADDRESS, abi=QUOTER_ABI)

    # Determine the reward token (wS)
    try:
        wrapped_token_address = silver_fees_contract.functions.wrappedToken().call()
        print(f"\nReward token (wS) address: {wrapped_token_address}")
    except Exception as e:
        print(f"Could not determine wrapped token address. Error: {e}")
        sys.exit(1)

    for pool_address, pool_name in POOLS.items():
        pool_address = Web3.to_checksum_address(pool_address)
        print(f"\n{'='*20} Verifying: {pool_name} ({pool_address}) {'='*20}")

        # --- Fetch Data ---
        onchain_data = get_onchain_rewards(w3_instance, quoter_contract, silver_fees_contract, wrapped_token_address, pool_address)
        api_data = get_api_rewards(w3_instance, silver_fees_contract, pool_address)

        # --- Process and Compare ---
        api_reward_val = api_data.get('api_rewards', {}).get('reward_agency', 0.0)
        onchain_reward_val = onchain_data.get('total_onchain_reward')
        details = onchain_data.get('details', {})
        token0 = details.get('token0', {})
        token1 = details.get('token1', {})

        if onchain_reward_val is None:
            if onchain_data.get('error'): print(f"  On-Chain Error: {onchain_data.get('error')}")
            continue

        # --- Display Results ---
        print(f"  On-Chain Details:")
        print(f"    - Token 0: {token0.get('amount', 0):.6f} {token0.get('symbol', 'N/A')} (Rate: 1 {token0.get('symbol', 'N/A')} = {token0.get('rate_in_ws', 0):.6f} wS)")
        print(f"    - Token 1: {token1.get('amount', 0):.6f} {token1.get('symbol', 'N/A')} (Rate: 1 {token1.get('symbol', 'N/A')} = {token1.get('rate_in_ws', 0):.6f} wS)")

        print(f"  Comparison:")
        print(f"    - API Result:      {api_reward_val:.18f} wS")
        print(f"    - On-Chain Result: {onchain_reward_val:.18f} wS")

        difference = abs(api_reward_val - onchain_reward_val)
        print(f"    - Difference:      {difference:.18f} wS")

    print(f"\n{'='*20} Verification Complete {'='*20}\n")
    print("Note: A small difference is expected due to fee accumulation over time and potential timing differences between API and on-chain queries.")
    print("Large differences may indicate that the API data is stale or incorrect.")
