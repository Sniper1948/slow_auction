pragma solidity ^0.8.20;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {ERC721Utils} from "@openzeppelin/contracts/token/ERC721/utils/ERC721Utils.sol";

interface ISilverFees {
    struct SnatchPerPoolData {
        address user;
        uint256 bidAmount;
    }

    function snatchData(address pool) external view returns (
        SnatchPerPoolData memory perPoolData,
        uint256 lastExecution,
        address bannedUser,
        bytes32 taskId
    );

    function snatch(uint256 _amountToBurn, address poolToSteal) external;
}

contract PoolBidder is Ownable {
    using ERC721Utils for IERC721;

    ISilverFees public immutable silverFees;
    IERC20 public immutable agToken;
    IERC20 public immutable wSToken;
    IERC721 public immutable nftPositionManager;
    uint256 private constant BID_INCREMENT = 0.1 ether; // 0.1 $AG
    uint256 private constant BID_INCREMENT_BIG = 0.2 ether; // 0.2 $AG
    uint256 private constant HIGH_VALUE_BID_SENTINEL = 5000; // Sentinel value for +0.2 $AG

    event BidFailed(address indexed pool, uint256 amount, address indexed bidder);
    event TokensWithdrawn(address indexed token, address indexed to, uint256 amount);
    event AllTokensWithdrawn(address indexed to, uint256 agAmount, uint256 wsAmount);
    event NFTTransferred(address indexed nftContract, uint256 indexed tokenId, address indexed to);
    event NFTReceived(address indexed nftContract, uint256 indexed tokenId, address indexed from);

    constructor(address _silverFees, address _agToken, address _wSToken, address _nftPositionManager) Ownable(msg.sender) {
        silverFees = ISilverFees(_silverFees);
        agToken = IERC20(_agToken);
        wSToken = IERC20(_wSToken);
        nftPositionManager = IERC721(_nftPositionManager);
    }

    modifier onlyOwnerOrSelf() {
        require(msg.sender == owner() || msg.sender == address(this), "Unauthorized caller");
        _;
    }

    function bidOnPool(address pool, uint256 specificAmount) external onlyOwnerOrSelf {
        _bidOnPool(pool, specificAmount);
    }

    function bidOnMultiplePools(address[] calldata pools, uint256[] calldata specificAmounts) external onlyOwner {
        require(pools.length == specificAmounts.length, "Arrays length mismatch");
        for (uint256 i = 0; i < pools.length; i++) {
            try this.bidOnPool(pools[i], specificAmounts[i]) {
                // Bid successful, continue to next pool
            } catch {
                emit BidFailed(pools[i], specificAmounts[i], owner());
                continue;
            }
        }
    }

    function _bidOnPool(address pool, uint256 specificAmount) internal {
        (ISilverFees.SnatchPerPoolData memory data,,,) = silverFees.snatchData(pool);

        uint256 bidAmount;
        if (specificAmount == HIGH_VALUE_BID_SENTINEL) {
            if (data.user != address(this)) {
                bidAmount = data.bidAmount + BID_INCREMENT_BIG;
            } else {
                return; // Skip if owner is highest bidder
            }
        } else if (specificAmount == 0) {
            if (data.user != address(this)) {
                bidAmount = data.bidAmount + BID_INCREMENT;
            } else {
                return; // Skip if owner is highest bidder
            }
        } else {
            bidAmount = specificAmount;
        }

        require(bidAmount > data.bidAmount, "Bid not higher");
        silverFees.snatch{gas: 120000}(bidAmount, pool);
    }

    function safeTransferNFT(address nftContract, uint256 tokenId, address from) external onlyOwner {
        require(nftContract == address(nftPositionManager), "Invalid NFT contract");
        IERC721(nftContract).safeTransferFrom(from, address(this), tokenId);
        emit NFTReceived(nftContract, tokenId, from);
    }

    function withdrawNFT(address nftContract, uint256 tokenId, address to) external onlyOwner {
        require(nftContract == address(nftPositionManager), "Invalid NFT contract");
        require(to != address(0), "Invalid recipient");
        IERC721(nftContract).safeTransferFrom(address(this), to, tokenId);
        emit NFTTransferred(nftContract, tokenId, to);
    }

    function withdrawTokens(address token, uint256 amount, address to) external onlyOwner {
        require(to != address(0), "Invalid recipient");
        IERC20(token).transfer(to, amount);
        emit TokensWithdrawn(token, to, amount);
    }

    function withdrawAGTokens(uint256 amount, address to) external onlyOwner {
        require(to != address(0), "Invalid recipient");
        agToken.transfer(to, amount);
        emit TokensWithdrawn(address(agToken), to, amount);
    }

    function withdrawWSTokens(uint256 amount, address to) external onlyOwner {
        require(to != address(0), "Invalid recipient");
        wSToken.transfer(to, amount);
        emit TokensWithdrawn(address(wSToken), to, amount);
    }

    function withdrawAllTokens(address to) external onlyOwner {
        require(to != address(0), "Invalid recipient");
        uint256 agBalance = agToken.balanceOf(address(this));
        uint256 wsBalance = wSToken.balanceOf(address(this));
        if (agBalance > 0) {
            agToken.transfer(to, agBalance);
        }
        if (wsBalance > 0) {
            wSToken.transfer(to, wsBalance);
        }
        emit AllTokensWithdrawn(to, agBalance, wsBalance);
    }

    function approveSilverFees(uint256 amount) external onlyOwner {
        agToken.approve(address(silverFees), amount);
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return this.onERC721Received.selector;
    }
}