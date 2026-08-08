import os
import json
import csv
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

RPC_URL = os.getenv("SEPOLIA_RPC_URL")
CONTRACT_ADDRESS = os.getenv("NFT_CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("BENCHMARK_PRIVATE_KEY")

TOTAL_TRANSACTIONS = 100
DURATION_SECONDS = 60
RECEIPT_TIMEOUT = 300
GAS_BUFFER = 1.20

if not RPC_URL:
    raise ValueError("Thiếu SEPOLIA_RPC_URL trong file .env")
if not CONTRACT_ADDRESS:
    raise ValueError("Thiếu NFT_CONTRACT_ADDRESS trong file .env")
if not PRIVATE_KEY:
    raise ValueError("Thiếu BENCHMARK_PRIVATE_KEY trong file .env")

web3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 60}))
if not web3.is_connected():
    raise ConnectionError("Không thể kết nối Ethereum Sepolia")

abi_path = Path(__file__).parent / "blockchain" / "NFTRentalABI.json"
with open(abi_path, "r", encoding="utf-8") as f:
    contract_abi = json.load(f)

contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi,
)

account = Account.from_key(PRIVATE_KEY)
sender_address = Web3.to_checksum_address(account.address)
balance_eth = web3.from_wei(web3.eth.get_balance(sender_address), "ether")

print("=" * 78)
print("BENCHMARK HÀNG LOẠT GIAO DỊCH BLOCKCHAIN")
print("=" * 78)
print("Kết nối Sepolia:", web3.is_connected())
print("Chain ID:", web3.eth.chain_id)
print("Contract:", CONTRACT_ADDRESS)
print("Tài khoản test:", sender_address)
print("Số dư:", balance_eth, "SepoliaETH")
print("Số giao dịch:", TOTAL_TRANSACTIONS)
print("=" * 78)

benchmark_start = time.perf_counter()
base_nonce = web3.eth.get_transaction_count(sender_address, "pending")
gas_price = web3.eth.gas_price

print("Nonce bắt đầu:", base_nonce)
print("Gas Price:", web3.from_wei(gas_price, "gwei"), "Gwei")
print("=" * 78)

pending_transactions = []
send_failed_results = []

print()
print("GIAI ĐOẠN 1: GỬI TRANSACTION")
print("-" * 78)

batch_send_start = time.perf_counter()
run_id = int(time.time())

for i in range(1, TOTAL_TRANSACTIONS + 1):
    nft_id = f"BENCHMARK-NFT-{run_id}-{i}"
    nonce = base_nonce + (i - 1)
    send_start = time.perf_counter()

    try:
        function_call = contract.functions.createRental(
            nft_id,
            sender_address,
            DURATION_SECONDS,
        )

        estimated_gas = function_call.estimate_gas({"from": sender_address})

        transaction = function_call.build_transaction({
            "from": sender_address,
            "nonce": nonce,
            "chainId": web3.eth.chain_id,
            "gas": int(estimated_gas * GAS_BUFFER),
            "gasPrice": gas_price,
        })

        signed_transaction = account.sign_transaction(transaction)
        tx_hash = web3.eth.send_raw_transaction(signed_transaction.raw_transaction)
        send_elapsed = time.perf_counter() - send_start
        tx_hash_hex = tx_hash.hex()

        pending_transactions.append({
            "stt": i,
            "nft_id": nft_id,
            "nonce": nonce,
            "transaction_hash": tx_hash_hex,
            "send_time_seconds": round(send_elapsed, 3),
            "sent_at": time.perf_counter(),
        })

        print(
            f"[SEND {i:03d}/{TOTAL_TRANSACTIONS}] "
            f"nonce={nonce} | {tx_hash_hex}"
        )

    except Exception as e:
        send_elapsed = time.perf_counter() - send_start
        send_failed_results.append({
            "stt": i,
            "nft_id": nft_id,
            "nonce": nonce,
            "transaction_hash": "",
            "block_number": "",
            "gas_used": "",
            "send_time_seconds": round(send_elapsed, 3),
            "confirm_time_seconds": "",
            "total_time_seconds": round(send_elapsed, 3),
            "status": "SEND_FAILED",
            "error": str(e),
        })
        print(f"[SEND {i:03d}/{TOTAL_TRANSACTIONS}] LỖI: {e}")

batch_send_time = time.perf_counter() - batch_send_start

print()
print("-" * 78)
print("Đã gửi thành công:", len(pending_transactions), "/", TOTAL_TRANSACTIONS)
print("Gửi thất bại:", len(send_failed_results))
print("Thời gian gửi toàn bộ batch:", round(batch_send_time, 3), "giây")

print()
print("GIAI ĐOẠN 2: CHỜ BLOCKCHAIN XÁC NHẬN")
print("-" * 78)

results = []

for index, item in enumerate(pending_transactions, start=1):
    confirm_start = time.perf_counter()

    try:
        receipt = web3.eth.wait_for_transaction_receipt(
            item["transaction_hash"],
            timeout=RECEIPT_TIMEOUT,
            poll_latency=1,
        )

        confirm_elapsed = time.perf_counter() - confirm_start
        total_elapsed = time.perf_counter() - item["sent_at"]
        status = "SUCCESS" if receipt.status == 1 else "FAILED"

        results.append({
            "stt": item["stt"],
            "nft_id": item["nft_id"],
            "nonce": item["nonce"],
            "transaction_hash": item["transaction_hash"],
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "send_time_seconds": item["send_time_seconds"],
            "confirm_time_seconds": round(confirm_elapsed, 3),
            "total_time_seconds": round(total_elapsed, 3),
            "status": status,
            "error": "",
        })

        print(
            f"[CONFIRM {index:03d}/{len(pending_transactions)}] "
            f"{status} | Block {receipt.blockNumber} | Gas {receipt.gasUsed}"
        )

    except Exception as e:
        confirm_elapsed = time.perf_counter() - confirm_start
        total_elapsed = time.perf_counter() - item["sent_at"]

        results.append({
            "stt": item["stt"],
            "nft_id": item["nft_id"],
            "nonce": item["nonce"],
            "transaction_hash": item["transaction_hash"],
            "block_number": "",
            "gas_used": "",
            "send_time_seconds": item["send_time_seconds"],
            "confirm_time_seconds": round(confirm_elapsed, 3),
            "total_time_seconds": round(total_elapsed, 3),
            "status": "TIMEOUT_OR_ERROR",
            "error": str(e),
        })

        print(
            f"[CONFIRM {index:03d}/{len(pending_transactions)}] "
            f"LỖI: {e}"
        )

results.extend(send_failed_results)
results.sort(key=lambda row: row["stt"])

total_time = time.perf_counter() - benchmark_start
success_rows = [row for row in results if row["status"] == "SUCCESS"]
failed_rows = [row for row in results if row["status"] != "SUCCESS"]

success_count = len(success_rows)
failed_count = len(failed_rows)
success_rate = success_count / TOTAL_TRANSACTIONS * 100

average_total_time = (
    sum(row["total_time_seconds"] for row in success_rows) / success_count
    if success_count > 0 else 0
)
average_send_time = (
    sum(row["send_time_seconds"] for row in success_rows) / success_count
    if success_count > 0 else 0
)
average_gas = (
    sum(row["gas_used"] for row in success_rows) / success_count
    if success_count > 0 else 0
)
throughput = success_count / total_time if total_time > 0 else 0
send_throughput = (
    len(pending_transactions) / batch_send_time
    if batch_send_time > 0 else 0
)

print()
print("=" * 78)
print("KẾT QUẢ BENCHMARK")
print("=" * 78)
print("Tổng giao dịch:", TOTAL_TRANSACTIONS)
print("Gửi thành công lên node:", len(pending_transactions))
print("Blockchain xác nhận thành công:", success_count)
print("Thất bại / timeout:", failed_count)
print("Tỷ lệ thành công:", round(success_rate, 2), "%")
print("Thời gian gửi batch:", round(batch_send_time, 3), "giây")
print("Tổng thời gian benchmark:", round(total_time, 3), "giây")
print("Thời gian trung bình / giao dịch:", round(average_total_time, 3), "giây")
print("Thời gian gửi trung bình:", round(average_send_time, 3), "giây")
print("Gas Used trung bình:", round(average_gas, 2))
print("Throughput gửi transaction:", round(send_throughput, 3), "giao dịch/giây")
print("Throughput xác nhận:", round(throughput, 3), "giao dịch/giây")
print("=" * 78)

results_dir = Path(__file__).parent / "benchmark_results"
results_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path = results_dir / f"sepolia_batch_{TOTAL_TRANSACTIONS}_{timestamp}.csv"

with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
    fieldnames = [
        "stt",
        "nft_id",
        "nonce",
        "transaction_hash",
        "block_number",
        "gas_used",
        "send_time_seconds",
        "confirm_time_seconds",
        "total_time_seconds",
        "status",
        "error",
    ]

    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

summary_path = results_dir / f"sepolia_batch_{TOTAL_TRANSACTIONS}_{timestamp}_summary.txt"

with open(summary_path, "w", encoding="utf-8") as summary_file:
    summary_file.write("BENCHMARK HÀNG LOẠT GIAO DỊCH BLOCKCHAIN\n")
    summary_file.write("=" * 60 + "\n")
    summary_file.write(f"Tổng giao dịch: {TOTAL_TRANSACTIONS}\n")
    summary_file.write(f"Gửi thành công lên node: {len(pending_transactions)}\n")
    summary_file.write(f"Blockchain xác nhận thành công: {success_count}\n")
    summary_file.write(f"Thất bại / timeout: {failed_count}\n")
    summary_file.write(f"Tỷ lệ thành công: {round(success_rate, 2)}%\n")
    summary_file.write(f"Thời gian gửi batch: {round(batch_send_time, 3)} giây\n")
    summary_file.write(f"Tổng thời gian benchmark: {round(total_time, 3)} giây\n")
    summary_file.write(
        f"Thời gian trung bình / giao dịch: {round(average_total_time, 3)} giây\n"
    )
    summary_file.write(f"Gas Used trung bình: {round(average_gas, 2)}\n")
    summary_file.write(
        f"Throughput gửi transaction: {round(send_throughput, 3)} giao dịch/giây\n"
    )
    summary_file.write(
        f"Throughput xác nhận: {round(throughput, 3)} giao dịch/giây\n"
    )

print()
print("Đã lưu dữ liệu chi tiết:")
print(csv_path)
print()
print("Đã lưu kết quả tổng kết:")
print(summary_path)
