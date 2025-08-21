// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/utils/Strings.sol";
import "contracts/Libraries/TransferHelper.sol";

import "contracts/Integrations/Gelato/AutomateTaskCreator.sol";

import "contracts/SilverFees/SilverFeesGiveaway.sol";

struct ExactInputParams {
	bytes path;
	address recipient;
	uint256 deadline;
	uint256 amountIn;
	uint256 amountOutMinimum;
}

interface IAlgebraSwapRouter {
	function exactInput(ExactInputParams memory data) external payable returns (uint256);
}

interface IAlgebraCommunityVault {
	function withdraw(address token, uint256 amount) external;
	function algebraFee() external view returns (uint16);
}

interface IAlgebraPool {
	function communityVault() external view returns (address);
}

interface IAlgebraNFTPositionManager {
	function balanceOf(address owner) external view returns (uint256);
}

// Fees redistribution data
struct FeesRedistributionData {
	uint256 agWeeklyGiveawayAmount;
	uint256 wrappedTokenWeeklyGiveawayAmount;
	uint256 agFlareAmount;
	uint256 wrappedTokenFlareAmount;
	uint256 agSnatchAmount;
	uint256 wrappedTokenSnatchAmount;
}

// Fees management
struct FeesManagementData {
	uint256 teamFees;
	uint256 weeklyGiveawayFees;
	uint256 buybackFees;
	FeesRedistributionData redistributionData;
	mapping (address => bool) flareWhitelistedTokens;
	address[] flareTokenToUnwhitelist;
	uint256 flareProgramPercentage;
	address bannedFlareUser;
	bool flareEnded;
	bool snatchEnded;
	string flareCID;
	string snatchCID;
	bool swapChanged;
	bool swapToWrappedToken;
	uint256 firstExecution;
	uint256 lastExecution;
	bytes32 taskId;
}

// Sync fees management
struct SyncFeesManagementData {
	uint256 time;
	uint256 lastSync;
	uint256 nextSync;
	bytes32 taskId;
}

// Fees converter
struct FeesTokenData {
	mapping(address => bytes32) taskId;
	string scriptCID;
}

// Bid data
struct BidData {
	uint256 amount;
	uint256 timestamp;
}

// Flare datas
struct FlareData {
	address user;
	uint256 bidAmount;
	address buybackToken;
	mapping (address=>BidData) lastBid;
	bytes32 taskId;
}

// Snatch datas
struct SnatchPerPoolData {
	address user;
	uint256 bidAmount;
}

struct SnatchData {
	SnatchPerPoolData perPoolData;
	mapping (address=>BidData) lastBid;
	uint256 lastExecution;
	address bannedUser;
	bytes32 taskId;
}

/// @title SilverFees
/// @author github.com/SifexPro
/// @notice Contract for the fees management of Silver
contract SilverFees is AutomateTaskCreator, Ownable2Step {
	SilverFeesGiveaway public silverFeesGiveaway;

	// Utils variables
	IERC20 public silverToken;
	IERC20 public wrappedToken;
	address public burnAddress;
	address public flareProgramAddress;
	address public teamMultisig;
	IAlgebraSwapRouter public swapRouter;
	IAlgebraCommunityVault public communityVault;
	IAlgebraNFTPositionManager public nftPositionManager;

	// All datas structures
	FeesManagementData public feesManagementData;
	SyncFeesManagementData public syncFeesManagementData;
	FeesTokenData public feesTokenData;
	FlareData public flareData;
	mapping (address => SnatchData) public snatchData;
	mapping(address => bool) public snatchIsPoolBided;
	address[] public snatchPoolsBids;

	// Events
	event FeesManagementExecuted(uint256 forTeam, uint256 forWeeklyGiveaway, uint256 forBuyback);
	event SyncFeesStarted();
	event SyncFeesManagement(uint256 indexed timestamp);
	event TokensBurned(uint256 amount);

	event FeesTokenAdded(address indexed token, bytes32 taskId);
	event FeesTokenRemoved(address indexed token);
	event FeesTokenSwapped(address indexed token, uint256 amountIn, uint256 amountOut);

	event FlareAuction(address indexed user, uint256 auctionAmount);
	event FlareExecution(address indexed user, uint256 buybackAmount, uint256 programAmount);
	event FlareBuyback(address indexed token, uint256 amount);

	event SnatchAuction(address indexed user, address indexed poolToSteal, uint256 auctionAmount);
	event SnatchExecution(address indexed user, address indexed poolToSteal);
	event SnatchSteal(address indexed user, address indexed rewardsPool, address rewardsToken, uint256 rewardsAmount);

	// Events for misc
	event SwapToWrappedToken(bool swapToWrappedToken);
	event SwapTypeChanged();
	event WithdrawnNative(address indexed to, uint256 amount);
	event WithdrawnToken(address indexed token, address to, uint256 amount);
	event EditedTeamMultisig(address indexed teamMultisig);
	event EditedFees(uint256 teamFees, uint256 weeklyGiveawayFees, uint256 buybackFees);

	// Gelato events
	event GelatoTaskCreated(bytes32 id);
	event GelatoTaskCanceled(bytes32 id);
	event GelatoTaskCancelFailed(bytes32 id);
	event GelatoFeesCheck(uint256 fees, address token);
	
	// Constructor
	constructor(address _silver, address _silverFeesGiveaway, address _burnAddress, address _flareProgramAddress, address _swapRouter, address _nftPositionManager, address _communityVault, address _teamMultisig, address _automate, address _wrappedToken, string memory _flareCID, string memory _snatchCID, string memory _feesTokenCID) AutomateTaskCreator(_automate) Ownable(msg.sender) {
		silverToken = IERC20(payable(_silver));
		wrappedToken = IERC20(payable(_wrappedToken));
		burnAddress = _burnAddress;
		flareProgramAddress = _flareProgramAddress;
		teamMultisig = _teamMultisig;
		swapRouter = IAlgebraSwapRouter(payable(_swapRouter));
		communityVault = IAlgebraCommunityVault(payable(_communityVault));
		nftPositionManager = IAlgebraNFTPositionManager(payable(_nftPositionManager));

		silverFeesGiveaway = SilverFeesGiveaway(payable(_silverFeesGiveaway));
		
		feesManagementData.teamFees = 12; // 12% for team
		feesManagementData.weeklyGiveawayFees = 3; // 3% for weekly giveaway
		feesManagementData.buybackFees = 85; // 85% for buyback

		feesManagementData.flareProgramPercentage = 0;

		feesManagementData.flareCID = _flareCID;
		feesManagementData.snatchCID = _snatchCID;
		
		feesManagementData.swapToWrappedToken = true;

		feesTokenData.scriptCID = _feesTokenCID;
    }


	// Fees management

	/**
	 * @dev Main function (to manage the fees) scheduled with Gelato by the sync system (10 min after the last sync) 
	 */
	function executeFeesManagement() public onlyDedicatedMsgSender {
		require(block.timestamp >= feesManagementData.lastExecution + syncFeesManagementData.time - 5 minutes, "Too early");

		// Balance
		uint256 balance;
		if (feesManagementData.swapToWrappedToken)
			balance = tokenAmount(address(wrappedToken)) - feesManagementData.redistributionData.wrappedTokenWeeklyGiveawayAmount - feesManagementData.redistributionData.wrappedTokenFlareAmount - feesManagementData.redistributionData.wrappedTokenSnatchAmount;
		else
			balance = tokenAmount(address(silverToken)) - feesManagementData.redistributionData.agWeeklyGiveawayAmount - feesManagementData.redistributionData.agFlareAmount - feesManagementData.redistributionData.agSnatchAmount;

		// Fees
		uint256 teamFees = (balance * feesManagementData.teamFees) / 100;
		uint256 weeklyGiveawayFees = (balance * feesManagementData.weeklyGiveawayFees) / 100;
		uint256 buybackFees = balance - teamFees - weeklyGiveawayFees;

		uint256 flareFees = buybackFees / 2;
		uint256 snatchFees = buybackFees - flareFees;

		// Redistribution
		if (feesManagementData.swapToWrappedToken) {
			SafeERC20.safeTransfer(wrappedToken, teamMultisig, teamFees);
			feesManagementData.redistributionData.wrappedTokenWeeklyGiveawayAmount += weeklyGiveawayFees;
			feesManagementData.redistributionData.wrappedTokenFlareAmount += flareFees;
			feesManagementData.redistributionData.wrappedTokenSnatchAmount += snatchFees;
		} else {
			SafeERC20.safeTransfer(silverToken, teamMultisig, teamFees);
			feesManagementData.redistributionData.agWeeklyGiveawayAmount += weeklyGiveawayFees;
			feesManagementData.redistributionData.agFlareAmount += flareFees;
			feesManagementData.redistributionData.agSnatchAmount += snatchFees;
		}

		// Giveaway
		if (silverFeesGiveaway.checkExecuteGiveaway())
			drawWinner();

		// Flare
		if (feesManagementData.flareEnded && flareData.user != address(0))
			executeFlare();
		feesManagementData.flareEnded = false;

		// Snatch
		if (feesManagementData.snatchEnded && snatchPoolsBids.length > 0)
		{
			for (uint256 i = 0; i < snatchPoolsBids.length; i++)
			{
				executeSnatch(snatchPoolsBids[i]);
				snatchIsPoolBided[snatchPoolsBids[i]] = false;
			}
			delete snatchPoolsBids;
		}
		feesManagementData.snatchEnded = false;

		// Fees management data update
		if (feesManagementData.swapChanged) {
			feesManagementData.swapChanged = false;
			feesManagementData.swapToWrappedToken = !feesManagementData.swapToWrappedToken;
			emit SwapToWrappedToken(feesManagementData.swapToWrappedToken);
		}
		feesManagementData.lastExecution = block.timestamp;

		// Gelato fees
		(uint256 fee, address feeToken) = _getFeeDetails();

		_transfer(fee, feeToken);
		emit GelatoFeesCheck(fee, feeToken);

		feesManagementData.taskId = bytes32("");
		emit FeesManagementExecuted(teamFees, weeklyGiveawayFees, buybackFees);
	}


	// Sync fees management

	/**
	 * @dev Sync the fees management 
	 */
	function syncFeesManagement() public onlyDedicatedMsgSender {
		silverFeesGiveaway.syncGiveaway(); // Sync the giveaway 

		if (flareData.user != address(0))
			feesManagementData.flareEnded = true; // End the flare auction
		if (snatchPoolsBids.length > 0)
			feesManagementData.snatchEnded = true; // End the snatch auction

		syncFeesManagementData.lastSync = block.timestamp;
		syncFeesManagementData.nextSync = block.timestamp + syncFeesManagementData.time;

		createTaskFeesManagement(); // Create the task for executeFeesManagement() (10 min)

		// Gelato fees
		(uint256 fee, address feeToken) = _getFeeDetails();

		_transfer(fee, feeToken);
		emit GelatoFeesCheck(fee, feeToken);

		emit SyncFeesManagement(block.timestamp);
	}

	/**
	 * @dev Start the sync system
	 * @param time Time between each sync
	 * @notice The sync system will execute the syncFeesManagement() function every time seconds (12 hours by default)
	 */
	function startSyncSystem(uint256 time) public onlyOwner {
		require(time == 0 || time >= 1200, "Time too low");

		syncFeesManagementData.time = time;
		syncFeesManagementData.lastSync = block.timestamp;
		syncFeesManagementData.nextSync = block.timestamp + time;

		feesManagementData.firstExecution = block.timestamp;
		feesManagementData.lastExecution = block.timestamp;
		
		cancelTask(flareData.taskId);

		cancelTask(feesManagementData.taskId);
		cancelTask(syncFeesManagementData.taskId);

		delete flareData;
		for (uint256 i = 0; i < snatchPoolsBids.length; i++)
		{
			cancelTaskSnatch(snatchPoolsBids[i]);
			delete snatchData[snatchPoolsBids[i]].perPoolData;
			snatchData[snatchPoolsBids[i]].lastExecution = 0;
			snatchIsPoolBided[snatchPoolsBids[i]] = false;
		}
		delete snatchPoolsBids;

		feesManagementData.flareEnded = false;
		feesManagementData.snatchEnded = false;

		if (time != 0) {
			silverFeesGiveaway.startSyncGiveaway();
			createTaskSyncSystem();
		}

		emit SyncFeesStarted();
	}

	function syncFeesTime() public view returns (uint256) {
		return syncFeesManagementData.time;
	}

	function syncFeesLastSync() public view returns (uint256) {
		return syncFeesManagementData.lastSync;
	}


	// Tokens fees converter

	/**
	 * @dev Swap the fees token to WrappedToken or $AG
	 * @param tokenAddress Token to swap
	 * @param swapArgs Swap arguments
	 * @notice Executed by a gelato task when SyncFeesManagement event is emitted
	 */
	function swapFeesToken(address tokenAddress, ExactInputParams memory swapArgs) public onlyDedicatedMsgSender {
		uint256 amountIn;
		uint256 amountOut;
		uint256 balanceBefore;
		uint256 balanceAfter;

		if (feesManagementData.swapToWrappedToken)
			balanceBefore = tokenAmount(address(wrappedToken));
		else
			balanceBefore = tokenAmount(address(silverToken));

		communityVault.withdraw(tokenAddress, swapArgs.amountIn);

		if (!(feesManagementData.swapToWrappedToken && tokenAddress == address(wrappedToken) || !feesManagementData.swapToWrappedToken && tokenAddress == address(silverToken))) 
		{
			swapArgs.recipient = payable(address(this));
			swapArgs.amountIn = tokenAmount(tokenAddress);

			TransferHelper.safeApprove(address(tokenAddress), address(swapRouter), swapArgs.amountIn);

			swapRouter.exactInput(swapArgs);
		}

		if (feesManagementData.swapToWrappedToken)
			balanceAfter = tokenAmount(address(wrappedToken));
		else
			balanceAfter = tokenAmount(address(silverToken));

		amountIn = swapArgs.amountIn;
		amountOut = balanceAfter - balanceBefore;

		// Gelato fees
		(uint256 fee, address feeToken) = _getFeeDetails();

		_transfer(fee, feeToken);
		emit GelatoFeesCheck(fee, feeToken);

		emit FeesTokenSwapped(tokenAddress, amountIn, amountOut);
	}

	/**
	 * @dev Add a token to the fees converter system 
	 * @param tokenAddress Token to add
	 * @notice The token must be in the community vault
	 */
	function addFeesToken(address tokenAddress) public onlyOwner {
		require(feesTokenData.taskId[tokenAddress] == bytes32(""), "Already added");

		createTaskFeesToken(tokenAddress);

		bytes32 taskId = feesTokenData.taskId[tokenAddress];
		emit FeesTokenAdded(tokenAddress, taskId);
	}

	function removeFeesToken(address tokenAddress) public onlyOwner {
		require(feesTokenData.taskId[tokenAddress] != bytes32(""), "Not added");

		_cancelTask(feesTokenData.taskId[tokenAddress]);
		feesTokenData.taskId[tokenAddress] = bytes32("");

		emit FeesTokenRemoved(tokenAddress);
	}

	function tokenAmountVault(address tokenAddress) public view returns (uint256) {
		IERC20 token = IERC20(tokenAddress);
        uint256 balance = token.balanceOf(address(communityVault));
        
		return (balance);
	}

	function tokenAmount(address tokenAddress) public view returns (uint256) {
		IERC20 token = IERC20(tokenAddress);
        uint256 balance = token.balanceOf(address(this));
        
		return (balance);
	}

	function isSwapToWrappedToken() public view returns (bool) {
		return (feesManagementData.swapToWrappedToken);
	}

	function feesTokenTaskId(address tokenAddress) public view returns (bytes32) {
		return feesTokenData.taskId[tokenAddress];
	}


	// Weekly giveaway

	/**
	 * @dev Buy tickets for the weekly giveaway
	 * @param _amount Amount in $AG of tickets to buy, by default 1 ticket = 1 $AG
	 */
	function buyTickets(uint256 _amount) public onlyLpUser {
		silverFeesGiveaway.buyTickets(_amount, msg.sender);
	}

	/**
	 * @dev Draw the winner of the weekly giveaway
	 * @notice The winner will receive the weekly giveaway amount
	 */
	function drawWinner() public onlyDedicatedMsgSender {
		bool _isSwapToWrappedToken = feesManagementData.swapToWrappedToken;
		uint256 weeklyGiveawayAmount;

		if (_isSwapToWrappedToken) {
			weeklyGiveawayAmount = feesManagementData.redistributionData.wrappedTokenWeeklyGiveawayAmount;
			feesManagementData.redistributionData.wrappedTokenWeeklyGiveawayAmount = 0;
			TransferHelper.safeApprove(address(wrappedToken), address(silverFeesGiveaway), weeklyGiveawayAmount);
		}
		else {
			weeklyGiveawayAmount = feesManagementData.redistributionData.agWeeklyGiveawayAmount;
			feesManagementData.redistributionData.agWeeklyGiveawayAmount = 0;
			TransferHelper.safeApprove(address(silverToken), address(silverFeesGiveaway), weeklyGiveawayAmount);
		}
		silverFeesGiveaway.executeGiveaway(_isSwapToWrappedToken, weeklyGiveawayAmount);
	}
	
	function buyTicketsBurn(address _user, uint256 _amount) external {
		require(msg.sender == address(silverFeesGiveaway), "Only FeesGiveaway");

		bool success = silverToken.transferFrom(_user, address(this), _amount);
		require(success, "Transfer failed");

		burnTokens(_amount);
	}


	// Flare

	/**
	 * @dev Flare auction
	 * @param _amountToBurn Amount of $AG to burn
	 * @param buybackToken Token to buyback
	 */
	function flare(uint256 _amountToBurn, address buybackToken) public onlyLpUser {
		require(!feesManagementData.flareEnded, "Ended");
		require(feesManagementData.bannedFlareUser != msg.sender, "Banned");
		require(flareIsWhitelistedToken(buybackToken), "Not whitelisted token");

		uint256 rounding = 1 ether / 10;
		uint256 roundAmount = _amountToBurn / rounding;
		uint256 amountToBurn = roundAmount * rounding;

		require(amountToBurn > flareData.bidAmount, "Bid too low");
		require(amountToBurn >= rounding, "< 0.1 $AG");

		uint256 balance = silverToken.balanceOf(msg.sender);
		require(balance >= amountToBurn, "Not enough balance");

		uint256 allowance = silverToken.allowance(msg.sender, address(this));
		require(allowance >= amountToBurn, "Not enough allowance");

		flareData.user = msg.sender;
		flareData.bidAmount = amountToBurn;
		flareData.buybackToken = buybackToken;
		flareData.lastBid[msg.sender] = BidData(amountToBurn, block.timestamp);
		
		emit FlareAuction(msg.sender, amountToBurn);
	}

	/**
	 * @dev Flare's execute function
	 */
	function executeFlare() public onlyDedicatedMsgSender {
		require(feesManagementData.flareEnded, "Too early");

		address user = flareData.user;
		uint256 amountToBurn = flareData.bidAmount;

		uint256 balance = silverToken.balanceOf(user);
		uint256 allowance = silverToken.allowance(user, address(this));
		if (balance < amountToBurn || allowance < amountToBurn) {
			feesManagementData.bannedFlareUser = user;
			delete flareData;
			return;
		}

		bool success = silverToken.transferFrom(user, address(this), amountToBurn);
		require(success, "Transfer failed");
		
		burnTokens(amountToBurn);

		uint256 flareAmountBuyback;
		uint256 flareAmountProgram;
		if (feesManagementData.swapToWrappedToken) {
			flareAmountProgram = (feesManagementData.redistributionData.wrappedTokenFlareAmount * feesManagementData.flareProgramPercentage) / 100;
			flareAmountBuyback = feesManagementData.redistributionData.wrappedTokenFlareAmount - flareAmountProgram;
			
			feesManagementData.redistributionData.wrappedTokenFlareAmount = 0;

			if (flareAmountProgram > 0)
				SafeERC20.safeTransfer(wrappedToken, flareProgramAddress, flareAmountProgram);
		} 
		else {
			flareAmountProgram = (feesManagementData.redistributionData.agFlareAmount * feesManagementData.flareProgramPercentage) / 100;
			flareAmountBuyback = feesManagementData.redistributionData.agFlareAmount - flareAmountProgram;
			
			feesManagementData.redistributionData.agFlareAmount = 0;

			if (flareAmountProgram > 0)
				SafeERC20.safeTransfer(silverToken, flareProgramAddress, flareAmountProgram);
		}
		feesManagementData.bannedFlareUser = address(0);

		address buybackToken = flareData.buybackToken;
		delete flareData;

		createTaskFlareBuyback(buybackToken, flareAmountBuyback);

		emit FlareExecution(user, flareAmountBuyback, flareAmountProgram);
	}

	/**
	 * @dev Flare's buyback function (after the auction when executeFeeManagement is called)
	 * @param tokenToSwap Token to swap
	 * @param swapArgs Swap arguments
	 */
	function flareBuyback(address tokenToSwap, address tokenAddress, ExactInputParams memory swapArgs) public onlyDedicatedMsgSender {
		if (swapArgs.amountIn != 0 && tokenToSwap != tokenAddress && flareIsWhitelistedToken(tokenAddress)) {
			swapArgs.recipient = payable(teamMultisig);

			TransferHelper.safeApprove(address(tokenToSwap), address(swapRouter), swapArgs.amountIn);

			swapRouter.exactInput(swapArgs);
		}
		else if (swapArgs.amountIn != 0 && tokenToSwap == tokenAddress && flareIsWhitelistedToken(tokenAddress)) {
			bool success = IERC20(tokenToSwap).transfer(teamMultisig, swapArgs.amountIn);
			require(success, "Transfer failed");
		}

		for (uint256 i = 0; i < feesManagementData.flareTokenToUnwhitelist.length && i < 10; i++)
			feesManagementData.flareWhitelistedTokens[feesManagementData.flareTokenToUnwhitelist[i]] = false;
		delete feesManagementData.flareTokenToUnwhitelist;

		// Gelato fees
		(uint256 fee, address feeToken) = _getFeeDetails();

		_transfer(fee, feeToken);
		emit GelatoFeesCheck(fee, feeToken);

		flareData.taskId = bytes32("");
		emit FlareBuyback(tokenToSwap, swapArgs.amountIn);
	}

	function flareAddWhitelistedToken(address token) public onlyOwner {
		require(!flareIsWhitelistedToken(token), "Already whitelisted");
		feesManagementData.flareWhitelistedTokens[token] = true;
	}

	function flareRemoveWhitelistedToken(address token) public onlyOwner {
		require(flareIsWhitelistedToken(token), "Not whitelisted");
		if (flareData.buybackToken == token)
			feesManagementData.flareTokenToUnwhitelist.push(token);
		else
			feesManagementData.flareWhitelistedTokens[token] = false;
	}

	function flareIsWhitelistedToken(address token) public view returns (bool) {
		return feesManagementData.flareWhitelistedTokens[token];
	}

	function flareLastBid(address user) public view returns (uint256) {
		if (flareData.lastBid[user].timestamp > feesManagementData.lastExecution)
			return flareData.lastBid[user].amount;
		return 0;
	}


	// Snatch 

	/**
	 * @dev Snatch auction
	 * @param _amountToBurn Amount of $AG to burn
	 * @param poolToSteal Pool to steal 50% of swap fees
	 */
	function snatch(uint256 _amountToBurn, address poolToSteal) public onlyLpUser {
		require(!feesManagementData.snatchEnded, "Ended");
		require(snatchData[poolToSteal].bannedUser != msg.sender, "Banned");
		require(IAlgebraPool(poolToSteal).communityVault() == address(communityVault), "Invalid pool");

		uint256 rounding = 1 ether / 10;
		uint256 roundAmount = _amountToBurn / rounding;
		uint256 amountToBurn = roundAmount * rounding;

		require(amountToBurn > snatchData[poolToSteal].perPoolData.bidAmount, "Bid too low");
		require(amountToBurn >= rounding, "< 0.1 $AG");

		uint256 balance = silverToken.balanceOf(msg.sender);
		require(balance >= amountToBurn, "Not enough balance");

		uint256 allowance = silverToken.allowance(msg.sender, address(this));
		require(allowance >= amountToBurn, "Not enough allowance");

		if (!snatchIsPoolBided[poolToSteal])
		{
			snatchPoolsBids.push(poolToSteal);
			snatchIsPoolBided[poolToSteal] = true;
		}

		if (snatchData[poolToSteal].lastExecution == 0)
			snatchData[poolToSteal].lastExecution = feesManagementData.firstExecution;
		snatchData[poolToSteal].perPoolData.user = msg.sender;
		snatchData[poolToSteal].perPoolData.bidAmount = amountToBurn;
		snatchData[poolToSteal].lastBid[msg.sender] = BidData(amountToBurn, block.timestamp);
		
		emit SnatchAuction(msg.sender, poolToSteal, amountToBurn);
	}

	/**
	 * @dev Snatch's execute function
	 */
	function executeSnatch(address poolToSteal) public onlyDedicatedMsgSender {
		require(feesManagementData.snatchEnded, "Too early");

		address user = snatchData[poolToSteal].perPoolData.user;
		uint256 amountToBurn = snatchData[poolToSteal].perPoolData.bidAmount;

		uint256 balance = silverToken.balanceOf(user);
		uint256 allowance = silverToken.allowance(user, address(this));
		if (balance < amountToBurn || allowance < amountToBurn) {
			snatchData[poolToSteal].bannedUser = user;
			delete snatchData[poolToSteal].perPoolData;
			return;
		}

		bool success = silverToken.transferFrom(user, address(this), amountToBurn);
		require(success, "Transfer failed");
		
		burnTokens(amountToBurn);

		snatchData[poolToSteal].bannedUser = address(0);
		delete snatchData[poolToSteal].perPoolData;

		createTaskSnatchSteal(user, poolToSteal);

		emit SnatchExecution(user, poolToSteal);
	}
	
	/**
	 * @dev Snatch's steal function (after the auction when executeFeeManagement is called)
	 * @param user User to send the rewards
	 * @param rewardsPool Pool to steal
	 * @param rewardsToken Token to send
	 * @param rewardsAmount Amount to send
	 */
	function snatchSteal(address user, address rewardsPool, address rewardsToken, uint256 rewardsAmount) public onlyDedicatedMsgSender {
		if (rewardsToken == address(wrappedToken))
		{
			require(wrappedToken.transfer(user, rewardsAmount), "Transfer failed");
			if (rewardsAmount > feesManagementData.redistributionData.wrappedTokenSnatchAmount)
				feesManagementData.redistributionData.wrappedTokenSnatchAmount = 0;
			else
				feesManagementData.redistributionData.wrappedTokenSnatchAmount -= rewardsAmount;
		}
		else if (rewardsToken == address(silverToken))
		{
			require(silverToken.transfer(user, rewardsAmount), "Transfer failed");
			if (rewardsAmount > feesManagementData.redistributionData.agSnatchAmount)
				feesManagementData.redistributionData.agSnatchAmount = 0;
			else
				feesManagementData.redistributionData.agSnatchAmount -= rewardsAmount;
		}

		snatchData[rewardsPool].lastExecution = block.timestamp;
		snatchData[rewardsPool].taskId = bytes32("");

		// Gelato fees
		(uint256 fee, address feeToken) = _getFeeDetails();

		_transfer(fee, feeToken);
		emit GelatoFeesCheck(fee, feeToken);

		emit SnatchSteal(user, rewardsPool, rewardsToken, rewardsAmount);
	}

	function snatchLastBid(address user, address pool) public view returns (uint256) {
		if (snatchData[pool].lastBid[user].timestamp > feesManagementData.lastExecution)
			return snatchData[pool].lastBid[user].amount;
		return 0;
	}


	// Get allowance

	/**
	 * @dev Get all bids of a user
	 * @param user User to check
	 * @return totalBids Total bids of the user
	 * @notice Include Flare and Snatch bids
	 */
	function getAllBids(address user) public view returns (uint256) {
		uint256 totalBids;

		totalBids += flareLastBid(user);
		for (uint256 i = 0; i < snatchPoolsBids.length; i++)
			totalBids += snatchLastBid(user, snatchPoolsBids[i]);

		return totalBids;
	} 


	// Burn function

	/**
	 * @dev Burn the Silver tokens (send to burn contract)
	 * @param _amount Amount of $AG to burn
	 */
	function burnTokens(uint256 _amount) private {
		require(silverToken.transfer(burnAddress, _amount), "Burn failed");
		
		emit TokensBurned(_amount);
	}


	// Gelato functions

	/**
	 * @dev Create a task for the sync system 
	 * @notice The task will be executed every syncFeesManagementData.time seconds
	 */
	function createTaskSyncSystem() private {
		bytes memory execData = abi.encodeCall(this.syncFeesManagement, ());

		ModuleData memory moduleData = ModuleData({
			modules: new Module[](2),
			args: new bytes[](2)
		});

		moduleData.modules[0] = Module.PROXY;
		moduleData.modules[1] = Module.TRIGGER;
	
		moduleData.args[0] = _proxyModuleArg();
		
		moduleData.args[1] = _timeTriggerModuleArg(
			uint128(syncFeesManagementData.nextSync) * 1000,
			uint128(syncFeesManagementData.time) * 1000
		);

		bytes32 taskId = _createTask(address(this), execData, moduleData, ETH);
	
		syncFeesManagementData.taskId = taskId;
		
		emit GelatoTaskCreated(taskId);
	}
	
	/**
	 * @dev Create task for executeFeesManagement function (SINGLE_EXEC)
	 * @notice Created by the sync system
	 * @notice The task will be executed 10 min after the last sync
	 */
	function createTaskFeesManagement() private {
		uint256 execTime = 10 minutes;
		
		bytes memory execData = abi.encodeCall(this.executeFeesManagement, ());

		ModuleData memory moduleData = ModuleData({
			modules: new Module[](3),
			args: new bytes[](3)
		});

		moduleData.modules[0] = Module.PROXY;
		moduleData.modules[1] = Module.SINGLE_EXEC;
		moduleData.modules[2] = Module.TRIGGER;
	
		moduleData.args[0] = _proxyModuleArg();
		moduleData.args[1] = _singleExecModuleArg();
		moduleData.args[2] = _timeTriggerModuleArg(
			uint128(syncFeesManagementData.lastSync + execTime) * 1000, 
			uint128(execTime) * 1000
		);

		bytes32 taskId = _createTask(address(this), execData, moduleData, ETH);
	
		feesManagementData.taskId = taskId;
		
		emit GelatoTaskCreated(taskId);
	}

	/**
	 * @dev Create task for convert fees token to WrappedToken or $AG
	 * @param tokenAddress Token to convert
	 * @notice Executed by a gelato task when SyncFeesManagement event is emitted
	 */
	function createTaskFeesToken(address tokenAddress) private {
		bytes memory execData = abi.encode( 
			Strings.toHexString(uint256(uint160(address(this))), 20),			// contract address
			Strings.toHexString(uint256(uint160(tokenAddress)), 20),			// tokenAddress
			Strings.toString(ERC20(tokenAddress).decimals()),					// tokenDecimals
			Strings.toHexString(uint256(uint160(address(silverToken))), 20),	// agAddress
			Strings.toHexString(uint256(uint160(address(wrappedToken))), 20),	// wrappedTokenAddress
			Strings.toString(block.chainid)										// network
		);

		ModuleData memory moduleData = ModuleData({
			modules: new Module[](3),
			args: new bytes[](3)
		});

		moduleData.modules[0] = Module.PROXY;
		moduleData.modules[1] = Module.WEB3_FUNCTION;
		moduleData.modules[2] = Module.TRIGGER;
	
		moduleData.args[0] = _proxyModuleArg();
		moduleData.args[1] = _web3FunctionModuleArg(
			feesTokenData.scriptCID,
			execData
		);
		bytes32[][] memory topics = new bytes32[][](1);
		topics[0] = new bytes32[](1);
		topics[0][0] = keccak256("SyncFeesManagement(uint256)");

		moduleData.args[2] = _eventTriggerModuleArg(
			address(this),
           	topics,
			7
		);

		bytes32 taskId = _createTask(address(this), execData, moduleData, ETH);
	
		feesTokenData.taskId[tokenAddress] = taskId;
		
		emit GelatoTaskCreated(taskId);
	}

	/**
	 * @dev Create task for buyback function (after the auction)
	 * @param tokenAddress Token to swap
	 * @param buybackAmount Amount to buyback
	 * @notice Task created when executeFlare is called and executed right after
	 */
	function createTaskFlareBuyback(address tokenAddress, uint256 buybackAmount) private {
		address addressToSwap;
		if (feesManagementData.swapToWrappedToken)
			addressToSwap = address(wrappedToken);
		else
			addressToSwap = address(silverToken);
		
		bytes memory execData = abi.encode( 
			Strings.toHexString(uint256(uint160(address(this))), 20),			// contract address
			Strings.toHexString((uint256(uint160(teamMultisig))), 20), 		 	// teamMultisig
			Strings.toHexString((uint256(uint160(tokenAddress))), 20),			// tokenAddress
			Strings.toString(ERC20(tokenAddress).decimals()),					// tokenDecimals
			Strings.toString(buybackAmount),									// buybackAmount
			Strings.toHexString(uint256(uint160(address(addressToSwap))), 20), 	// addressToSwap
			Strings.toString(block.chainid)										// network
		);

		ModuleData memory moduleData = ModuleData({
			modules: new Module[](3),
			args: new bytes[](3)
		});

		moduleData.modules[0] = Module.PROXY;
		moduleData.modules[1] = Module.SINGLE_EXEC;
		moduleData.modules[2] = Module.WEB3_FUNCTION;
	
		moduleData.args[0] = _proxyModuleArg();
		moduleData.args[1] = _singleExecModuleArg();
		moduleData.args[2] = _web3FunctionModuleArg(
			feesManagementData.flareCID,
			execData
		);

		bytes32 taskId = _createTask(address(this), execData, moduleData, ETH);
	
		flareData.taskId = taskId;
		
		emit GelatoTaskCreated(taskId);
	}

	/**
     * @dev Create task for snatchSteal function (after the auction)
     * @param user User that steal the fees
     * @param poolToSteal Pool from which to steal 50% of swap fees
     * @notice Task is executed right after creation
     */
	function createTaskSnatchSteal(address user, address poolToSteal) private {
		address rewardsToken;
		uint256 timeToSteal = block.timestamp - snatchData[poolToSteal].lastExecution;
		
		if (feesManagementData.swapToWrappedToken)
			rewardsToken = address(wrappedToken);
		else
			rewardsToken = address(silverToken);

		bytes memory execData = abi.encode( 
			Strings.toHexString(uint256(uint160(address(this))), 20),			// contract address
			Strings.toHexString((uint256(uint160(user))), 20), 		 			// userAddress
			Strings.toString(timeToSteal),										// timeToSteal
			Strings.toHexString((uint256(uint160(poolToSteal))), 20),			// poolToSteal
			Strings.toHexString(uint256(uint160(address(rewardsToken))), 20), 	// rewardsToken
			Strings.toString(block.chainid)										// network
		);

		ModuleData memory moduleData = ModuleData({
			modules: new Module[](3),
			args: new bytes[](3)
		});

		moduleData.modules[0] = Module.PROXY;
		moduleData.modules[1] = Module.SINGLE_EXEC;
		moduleData.modules[2] = Module.WEB3_FUNCTION;
	
		moduleData.args[0] = _proxyModuleArg();
		moduleData.args[1] = _singleExecModuleArg();
		moduleData.args[2] = _web3FunctionModuleArg(
			feesManagementData.snatchCID,
			execData
		);

		bytes32 taskId = _createTask(address(this), execData, moduleData, ETH);
	
		snatchData[poolToSteal].taskId = taskId;
		
		emit GelatoTaskCreated(taskId);
	}

	function cancelTaskCall(bytes32 taskId) public {
		require(msg.sender == address(this));
		_cancelTask(taskId);
	}

	/**
	 * @dev Cancel a gelato task
	 * @param taskId Task id to cancel
	 */
	function cancelTask(bytes32 taskId) public onlyOwner {
		if (taskId == bytes32(""))
			return;

		(bool success, ) = address(this).call(
            abi.encodeWithSignature("cancelTaskCall(bytes32)", taskId)
        );

		if (success)
			emit GelatoTaskCanceled(taskId);
		else
			emit GelatoTaskCancelFailed(taskId);

		if (taskId == syncFeesManagementData.taskId)
			syncFeesManagementData.taskId = bytes32("");
		else if (taskId == feesManagementData.taskId)
			feesManagementData.taskId = bytes32("");
		else if (taskId == flareData.taskId)
			flareData.taskId = bytes32("");
	}

	/**
	 * @dev Cancel a gelato task
	 * @param pool Pool to cancel
	 */
	function cancelTaskSnatch(address pool) public onlyOwner {
		bytes32 taskId = snatchData[pool].taskId;
		if (taskId == bytes32(""))
			return;

		(bool success, ) = address(this).call(
            abi.encodeWithSignature("cancelTaskCall(bytes32)", taskId)
        );

		if (success)
			emit GelatoTaskCanceled(taskId);
		else
			emit GelatoTaskCancelFailed(taskId);
			
		snatchData[pool].taskId = bytes32("");
	}

	// Internal functions

	/**
	 * @dev Change the swap fees to WrappedToken or $AG
	 * @param swapToWrappedToken True if swap to WrappedToken, false if swap to $AG
	 * @notice The change is not immediate, it will be applied at the next fees management
	 */
	function setSwapToWrappedToken(bool swapToWrappedToken) public onlyOwner {
		if (feesManagementData.swapToWrappedToken == swapToWrappedToken)
			feesManagementData.swapChanged = false;
		else
			feesManagementData.swapChanged = true;
		
		emit SwapTypeChanged();
	}

	function withdrawNative(address _to) public onlyOwner {
		uint256 balance = address(this).balance;
        require(balance > 0, "No Native to withdraw");

		address payable _tresory = payable(_to);
		(bool success, ) = _tresory.call{value:balance}("");
		require(success, "Transaction failed");

		emit WithdrawnNative(_tresory, balance);
	}

	function withdrawToken(address _token, address _to) public onlyOwner {
		IERC20 token = IERC20(_token);
		uint256 balance = token.balanceOf(address(this));

		SafeERC20.safeTransfer(token, _to, balance);

		emit WithdrawnToken(_token, _to, balance);
	}
	
	function editMultisig(address _teamMultisig) public onlyMultisig {
		teamMultisig = _teamMultisig;

		emit EditedTeamMultisig(_teamMultisig);
	}

	function editSilver(address _silver) public onlyOwner {
		silverToken = IERC20(payable(_silver));
	}

	function editSilverFeesGiveaway(address _silverFeesGiveaway) public onlyOwner {
		silverFeesGiveaway = SilverFeesGiveaway(payable(_silverFeesGiveaway));
	}

	function editwrappedToken(address _wrappedToken) public onlyOwner {
		wrappedToken = IERC20(payable(_wrappedToken));
	}

	function editFlareProgramAddress(address _flareProgramAddress) public onlyOwner {
		flareProgramAddress = _flareProgramAddress;
	}

	function editAlgebraSwapRouter(address _swapRouter) public onlyOwner {
		swapRouter = IAlgebraSwapRouter(payable(_swapRouter));
	}

	function editCommunityVault(address _communityVault) public onlyOwner {
		communityVault = IAlgebraCommunityVault(payable(_communityVault));
	}

	function editNftPositionManager(address _nftPositionManager) public onlyOwner {
		nftPositionManager = IAlgebraNFTPositionManager(payable(_nftPositionManager));
	}

	function editFees(uint256 teamFees, uint256 weeklyGiveawayFees, uint256 buybackFees) public onlyOwner {
		require(teamFees + weeklyGiveawayFees + buybackFees == 100, "Invalid fees");

		feesManagementData.teamFees = teamFees;
		feesManagementData.weeklyGiveawayFees = weeklyGiveawayFees;
		feesManagementData.buybackFees = buybackFees;

		emit EditedFees(teamFees, weeklyGiveawayFees, buybackFees);
	}

	function editFlareProgramPercentage(uint256 flareProgramPercentage) public onlyOwner {
		require(flareProgramPercentage <= 100);
		
		feesManagementData.flareProgramPercentage = flareProgramPercentage;
	}

	function editFlareCID(string memory flareCID) public onlyOwner {
		feesManagementData.flareCID = flareCID;
	}

	function editSnatchCID(string memory snatchCID) public onlyOwner {
		feesManagementData.snatchCID = snatchCID;
	}

	function editFeesTokenCID(string memory scriptCID) public onlyOwner {
		feesTokenData.scriptCID = scriptCID;
	}


	// Modifiers 

	modifier onlyLpUser() {
		require(nftPositionManager.balanceOf(msg.sender) > 0, "Not LP user");
		_;
	}

	modifier onlyMultisig() {
		require(msg.sender == teamMultisig, "Not authorized");
		_;
	}


	// Receive function (to receive Native)

	receive() external payable {}
}