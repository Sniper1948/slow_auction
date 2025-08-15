import unittest
import time
from unittest.mock import MagicMock, patch, call
from auction_bid import (
    place_multiple_bids_with_poolbidder,
    execute_final_bidding_strategy,
    w3_instance,
    pool_bidder_contract_instance,
    WALLET_ADDRESS,
    PRIVATE_KEY,
    POOL_BIDDER_CONTRACT_ADDRESS,
    POOLS_ORIGINAL,
    WS_USDC_POOL,
    WS_AG_POOL,
    HIGH_VALUE_BID_SENTINEL,
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

class MockThread:
    def __init__(self, target=None, args=(), kwargs=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
    def start(self):
        if self.target:
            self.target(*self.args, **self.kwargs)

@patch('auction_bid.threading.Thread', new=MockThread)
class TestFinalBiddingStrategy(unittest.TestCase):
    @patch('auction_bid.place_multiple_bids_with_poolbidder')
    def test_single_transaction_with_mixed_bids(self, mock_place_bids):
        # Arrange
        auction_bid.hot_list_bids = {
            '0xpool1': HIGH_VALUE_BID_SENTINEL,
            '0xpool2': 0,
            '0xpool3': HIGH_VALUE_BID_SENTINEL,
        }
        mock_w3 = MagicMock()
        mock_pb_contract = MagicMock()

        # Act
        execute_final_bidding_strategy(mock_w3, mock_pb_contract)

        # Assert
        mock_place_bids.assert_called_once()

        args, kwargs = mock_place_bids.call_args

        self.assertEqual(args[0], mock_w3)
        self.assertEqual(args[1], mock_pb_contract)

        # Keys and values can be in any order, so we check them separately
        self.assertCountEqual(args[2], ['0xpool1', '0xpool2', '0xpool3'])
        self.assertCountEqual(args[3], [HIGH_VALUE_BID_SENTINEL, 0, HIGH_VALUE_BID_SENTINEL])

        # Also check if the mapping is correct
        sent_bids = dict(zip(args[2], args[3]))
        self.assertDictEqual(sent_bids, auction_bid.hot_list_bids)

        self.assertEqual(args[4], "URGENT")


if __name__ == '__main__':
    unittest.main()
