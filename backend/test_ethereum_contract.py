from blockchain.ethereum_contract import get_ethereum_rental_contract

try:
    ethereum = get_ethereum_rental_contract()

    print("✅ Kết nối Sepolia:", ethereum.is_connected())
    print("✅ Chain ID:", ethereum.get_chain_id())
    print("✅ Latest block:", ethereum.get_latest_block_number())
    print("✅ Rental counter:", ethereum.get_rental_counter())

    rental = ethereum.get_rental(1)
    print("✅ Rental #1:")
    print(rental)

    verified = ethereum.verify_rental_transaction(
        "0x19f86838c66816895823358619029782f650108c7c8a1d7da813b62be6f83ede"
    )

    print("✅ Verify transaction:")
    print(verified)

except Exception as e:
    print("❌ Lỗi:", e)