import unittest
import time
from unittest.mock import MagicMock, patch
from auction_bid import (
    place_multiple_bids_with_poolbidder,
    connect_to_blockchain,
    w3_instance,
    pool_bidder_contract_instance,
    WALLET_ADDRESS,
    PRIVATE_KEY,
    POOL_BIDDER_CONTRACT_ADDRESS,
    POOLS_ORIGINAL,
    WS_USDC_POOL,
    WS_AG_POOL,
)

class TestBidding(unittest.TestCase):
    def test_multi_pool_0_bidding(self):
        with patch('auction_bid.w3_instance.eth') as mock_eth, \
             patch('auction_bid.pool_bidder_contract_instance.functions.bidOnMultiplePools') as mock_bid_on_multiple_pools, \
             patch('auction_bid.w3_instance.eth.account.sign_transaction') as mock_sign_transaction, \
             patch('auction_bid.w3_instance.eth.send_raw_transaction') as mock_send_raw_transaction, \
             patch('auction_bid.get_transaction_details') as mock_get_transaction_details:

            mock_eth.get_transaction_count.return_value = 1
            mock_eth.gas_price = 55 * 10**9
            mock_bid_on_multiple_pools.return_value.estimate_gas.return_value = 100000

            # Set a value for AUCTION_END_TIME
            import auction_bid
            auction_bid.AUCTION_END_TIME = time.time() + 60
            mock_bid_on_multiple_pools.return_value.build_transaction.return_value = {}
            mock_sign_transaction.return_value.rawTransaction = b''
            mock_send_raw_transaction.return_value.hex.return_value = '0x123'
            mock_get_transaction_details.return_value = {
                "tx_hash": "0x123",
                "timestamp": "2025-08-04 10:49:25.373645",
                "gas_used": 21000,
                "gas_price_gwei": 55,
                "tx_cost_eth": 0.001155
            }

            pool_ids = [WS_USDC_POOL, WS_AG_POOL]
            bid_amounts = [0.0, 0.0]
            urgency = "URGENT"

            success, tx_hash = place_multiple_bids_with_poolbidder(
                w3_instance,
                pool_bidder_contract_instance,
                pool_ids,
                bid_amounts,
                urgency
            )

            self.assertTrue(success)
            self.assertEqual(tx_hash, '0x123')
            mock_get_transaction_details.assert_called_once_with(w3_instance, '0x123')

    def test_fetch_historical_bids(self):
        with patch('auction_bid.requests.get') as mock_get, \
             patch('auction_bid.get_transaction_details') as mock_get_transaction_details:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "1",
                "result": [
                    {
                        "to": "0xc3e38729d53e3830ab7365589a0a28cd73522bae",
                        "input": "0x78d13d66",
                        "hash": "0x456"
                    }
                ]
            }
            mock_get.return_value = mock_response
            mock_get_transaction_details.return_value = {
                "tx_hash": "0x456",
                "timestamp": "2025-08-05 02:10:45.727887",
                "gas_used": 21000,
                "gas_price_gwei": 55,
                "tx_cost_eth": 0.001155
            }

            from auction_bid import fetch_historical_bids, gas_usage_data
            gas_usage_data.clear()
            fetch_historical_bids(w3_instance, "0xb46e0226c5cb834ef6fe7492cf37d70f8cee62f2", "0xC3e38729d53E3830Ab7365589A0A28cD73522BAE", "0x78d13d66")
            self.assertEqual(len(gas_usage_data), 1)
            self.assertEqual(gas_usage_data[0]["tx_hash"], "0x456")


if __name__ == '__main__':
    unittest.main()
