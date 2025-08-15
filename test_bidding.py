import unittest
import time
from unittest.mock import MagicMock, patch, call
from auction_bid import (
    place_multiple_bids_with_poolbidder,
    create_hot_lists,
    main,
    w3_instance,
    pool_bidder_contract_instance,
    WALLET_ADDRESS,
    PRIVATE_KEY,
    POOL_BIDDER_CONTRACT_ADDRESS,
    POOLS_ORIGINAL,
    WS_USDC_POOL,
    WS_AG_POOL,
    HIGH_VALUE_BID_SENTINEL,
    CONTRACT_DEFAULT_INCREMENT_AMOUNT,
    CONTRACT_BIG_INCREMENT_AMOUNT,
    HOT_LIST_MIN_POTENTIAL_PROFIT,
    HOT_LIST_PROFIT_TIERS,
    NUMBER_OF_HOT_LISTS,
)
import auction_bid

class TestBidding(unittest.TestCase):
    def test_multi_pool_0_bidding(self):
        with patch('auction_bid.w3_instance.eth'), \
             patch('auction_bid.pool_bidder_contract_instance.functions.bidOnMultiplePools') as mock_bid_on_multiple_pools, \
             patch('auction_bid.w3_instance.eth.account.sign_transaction'), \
             patch('auction_bid.w3_instance.eth.send_raw_transaction') as mock_send_raw_transaction:

            auction_bid.AUCTION_END_TIME = time.time() + 60
            mock_bid_on_multiple_pools.return_value.build_transaction.return_value = {}
            mock_send_raw_transaction.return_value.hex.return_value = '0x123'

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

class TestNewHotListLogic(unittest.TestCase):
    def setUp(self):
        # This setup will be used by both test methods
        auction_bid.POOLS_ORIGINAL = {
            'pool1': 'P1', # High profit
            'pool2': 'P2', # Standard profit
            'pool3': 'P3', # Low profit
            'pool4': 'P4'  # No reward
        }
        auction_bid.last_rewards = {
            'pool1': 1.0,
            'pool2': 0.15,
            'pool3': 0.05
        }
        auction_bid.highest_bids = {
            'pool1': {'amount': 0.5},
            'pool2': {'amount': 0.0},
            'pool3': {'amount': 0.0}
        }
        auction_bid.HOT_LIST_PROFIT_TIERS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        auction_bid.NUMBER_OF_HOT_LISTS = 6
        auction_bid.CONTRACT_DEFAULT_INCREMENT_AMOUNT = 0.1
        auction_bid.CONTRACT_BIG_INCREMENT_AMOUNT = 0.2
        auction_bid.HOT_LIST_MIN_POTENTIAL_PROFIT = 0.02
        auction_bid.HIGH_VALUE_BID_SENTINEL = 5000

    def test_create_hot_lists(self):
        # Act
        create_hot_lists()

        # Assert
        hot_lists = auction_bid.hot_lists

        # Pool 1: High profit, should be in hotlist[0] with bid 0, and hotlist[1] with bid 5000
        self.assertEqual(hot_lists[0].get('pool1'), 0)
        self.assertEqual(hot_lists[1].get('pool1'), 5000)

        # Pool 2: Standard profit, should be in hotlist[0] with bid 0
        self.assertEqual(hot_lists[0].get('pool2'), 0)
        self.assertNotIn('pool2', hot_lists[1]) # Not profitable enough for tier 2

        # Pool 3: Low profit, should not be in any hotlist
        for i in range(NUMBER_OF_HOT_LISTS):
            self.assertNotIn('pool3', hot_lists[i])

        # Pool 4: No reward, should not be in any hotlist
        for i in range(NUMBER_OF_HOT_LISTS):
            self.assertNotIn('pool4', hot_lists[i])

if __name__ == '__main__':
    unittest.main()
