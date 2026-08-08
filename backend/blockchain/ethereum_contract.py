import json
import os

from web3 import Web3

from config import Config


class EthereumRentalContract:
    def __init__(self):
        self.rpc_url = Config.SEPOLIA_RPC_URL
        self.contract_address = Config.NFT_CONTRACT_ADDRESS

        if not self.rpc_url:
            raise ValueError(
                "Thiếu SEPOLIA_RPC_URL trong file .env"
            )

        if not self.contract_address:
            raise ValueError(
                "Thiếu NFT_CONTRACT_ADDRESS trong file .env"
            )

        self.web3 = Web3(
            Web3.HTTPProvider(self.rpc_url)
        )

        if not self.web3.is_connected():
            raise ConnectionError(
                "Không thể kết nối tới Ethereum Sepolia"
            )

        abi_path = os.path.join(
            os.path.dirname(__file__),
            "NFTRentalABI.json",
        )

        with open(
            abi_path,
            "r",
            encoding="utf-8",
        ) as file:
            contract_abi = json.load(file)

        checksum_address = (
            Web3.to_checksum_address(
                self.contract_address
            )
        )

        self.contract = self.web3.eth.contract(
            address=checksum_address,
            abi=contract_abi,
        )

    def is_connected(self):
        return self.web3.is_connected()

    def get_chain_id(self):
        return self.web3.eth.chain_id

    def get_latest_block_number(self):
        return self.web3.eth.block_number

    def get_rental_counter(self):
        return self.contract.functions \
            .rentalCounter() \
            .call()

    def get_rental(self, rental_id):
        rental = self.contract.functions \
            .rentals(int(rental_id)) \
            .call()

        return {
            "rental_id": rental[0],
            "nft_id": rental[1],
            "owner": rental[2],
            "renter": rental[3],
            "start_time": rental[4],
            "end_time": rental[5],
            "active": rental[6],
        }

    def is_rental_active(self, rental_id):
        return self.contract.functions \
            .isActive(int(rental_id)) \
            .call()

    def is_rental_expired(self, rental_id):
        return self.contract.functions \
            .isExpired(int(rental_id)) \
            .call()
        
    def verify_rental_transaction(self, tx_hash):
        receipt = self.web3.eth.get_transaction_receipt(tx_hash)

        if receipt is None:
            raise ValueError(
                "Không tìm thấy giao dịch trên Sepolia"
            )

        if receipt.status != 1:
            raise ValueError(
                "Giao dịch blockchain không thành công"
            )

        contract_address = self.contract.address.lower()

        if (
            not receipt.to
            or receipt.to.lower() != contract_address
        ):
            raise ValueError(
                "Giao dịch không gửi tới NFTRental contract"
            )

        events = (
            self.contract.events
            .RentalCreated()
            .process_receipt(receipt)
        )

        if not events:
            raise ValueError(
                "Không tìm thấy sự kiện RentalCreated"
            )

        args = events[0]["args"]

        return {
            "transaction_hash": tx_hash,
            "rental_id": int(args["rentalId"]),
            "nft_id": args["nftId"],
            "owner": args["owner"],
            "renter": args["renter"],
            "start_time": int(args["startTime"]),
            "end_time": int(args["endTime"])
        }


ethereum_rental_contract = None


def get_ethereum_rental_contract():
    global ethereum_rental_contract

    if ethereum_rental_contract is None:
        ethereum_rental_contract = (
            EthereumRentalContract()
        )

    return ethereum_rental_contract