import csv
import json
import statistics
import time
from pathlib import Path

from blockchain.block import Block
from blockchain.crypto import Crypto
from blockchain.transaction import Transaction
from blockchain.wallet import create_wallet


# Số lần chạy cho các phép đo nhanh
FAST_ITERATIONS = 10_000

# Số lần chạy Merkle Root
MERKLE_ITERATIONS = 1_000

# Số lần đào khối. PoW lâu và biến động nên không chạy 10.000 lần.
POW_ITERATIONS = 10

# Số giao dịch dùng để tính Merkle Root và đào khối
TRANSACTION_COUNT = 100

# Độ khó đúng với code hiện tại
POW_DIFFICULTY = 4


def milliseconds(seconds: float) -> float:
    """Đổi giây sang mili-giây."""
    return seconds * 1000


def measure(function, iterations: int) -> dict:
    """
    Chạy một hàm nhiều lần và trả về:
    trung bình, nhỏ nhất, lớn nhất và độ lệch chuẩn.
    """
    durations = []

    for _ in range(iterations):
        start = time.perf_counter()
        function()
        end = time.perf_counter()

        durations.append(milliseconds(end - start))

    return {
        "so_lan": iterations,
        "trung_binh_ms": statistics.mean(durations),
        "nho_nhat_ms": min(durations),
        "lon_nhat_ms": max(durations),
        "do_lech_chuan_ms": (
            statistics.stdev(durations)
            if len(durations) > 1
            else 0
        ),
    }


def create_transaction_payload() -> dict:
    """
    Payload mô phỏng đúng nghiệp vụ thuê NFT của hệ thống.
    """
    return {
        "sender": "14a5FLUB5j_example_renter",
        "receiver": "1OwnerWallet_example",
        "amount": 10.5,
        "action": "rent_nft",
        "data": {
            "nft_id": "NFT-DEMO-001",
            "deposit": 0,
            "rental_start": 1754010000.0,
            "rental_days": 1,
            "service_fee": 0.5,
        },
        "timestamp": 1754010000.0,
    }


def build_signed_transactions(
    count: int,
    wallet: dict,
) -> list[Transaction]:
    """
    Tạo danh sách giao dịch có chữ ký để dùng cho Merkle Root và PoW.
    """
    transactions = []

    for index in range(count):
        transaction = Transaction(
            sender=wallet["address"],
            receiver=f"owner-wallet-{index}",
            amount=10.5,
            action="rent_nft",
            data={
                "nft_id": f"NFT-{index:04d}",
                "deposit": 0,
                "rental_days": 1,
                "service_fee": 0.5,
            },
        )

        transaction.sign(
            wallet["private_key"],
            wallet["public_key"],
        )

        transactions.append(transaction)

    return transactions


def main() -> None:
    print("Đang chuẩn bị dữ liệu benchmark...")

    wallet = create_wallet()
    payload = create_transaction_payload()

    # Chuỗi JSON được băm/ký giống cách project đang chuẩn hóa dữ liệu.
    payload_json = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
    )

    private_key = Crypto.string_to_private_key(
        wallet["private_key"]
    )

    public_key = Crypto.string_to_public_key(
        wallet["public_key"]
    )

    signature = Crypto.sign_message(
        private_key,
        payload_json,
    )

    signed_transactions = build_signed_transactions(
        TRANSACTION_COUNT,
        wallet,
    )

    transaction_dicts = [
        transaction.to_dict()
        for transaction in signed_transactions
    ]

    results = {}

    print("1. Đo SHA-256...")
    results["SHA-256"] = measure(
        lambda: Crypto.sha256(payload_json),
        FAST_ITERATIONS,
    )

    print("2. Đo ký ECDSA...")
    results["Ký ECDSA"] = measure(
        lambda: Crypto.sign_message(
            private_key,
            payload_json,
        ),
        FAST_ITERATIONS,
    )

    print("3. Đo xác minh ECDSA...")
    results["Xác minh ECDSA"] = measure(
        lambda: Crypto.verify_signature(
            public_key,
            payload_json,
            signature,
        ),
        FAST_ITERATIONS,
    )

    print("4. Đo Merkle Root cho 100 giao dịch...")
    results["Merkle Root (100 giao dịch)"] = measure(
        lambda: Crypto.calculate_merkle_root(
            transaction_dicts
        ),
        MERKLE_ITERATIONS,
    )

    print("5. Đo Proof-of-Work difficulty=4...")

    pow_durations = []
    pow_nonces = []

    for index in range(POW_ITERATIONS):
        # Tạo block mới mỗi lần để nonce và timestamp độc lập.
        block = Block(
            index=index + 1,
            previous_hash="0" * 64,
            transactions=signed_transactions,
            difficulty=POW_DIFFICULTY,
        )

        start = time.perf_counter()
        block.mine_block()
        end = time.perf_counter()

        pow_durations.append(milliseconds(end - start))
        pow_nonces.append(block.nonce)

    results["Proof-of-Work difficulty=4"] = {
        "so_lan": POW_ITERATIONS,
        "trung_binh_ms": statistics.mean(
            pow_durations
        ),
        "nho_nhat_ms": min(pow_durations),
        "lon_nhat_ms": max(pow_durations),
        "do_lech_chuan_ms": (
            statistics.stdev(pow_durations)
            if len(pow_durations) > 1
            else 0
        ),
        "nonce_trung_binh": statistics.mean(
            pow_nonces
        ),
    }

    output_directory = Path("benchmark_results")
    output_directory.mkdir(exist_ok=True)

    json_path = (
        output_directory
        / "benchmark_blockchain_results.json"
    )

    csv_path = (
        output_directory
        / "benchmark_blockchain_results.csv"
    )

    with json_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "Thành phần",
            "Số lần",
            "Trung bình (ms)",
            "Nhỏ nhất (ms)",
            "Lớn nhất (ms)",
            "Độ lệch chuẩn (ms)",
            "Nonce trung bình",
        ])

        for name, result in results.items():
            writer.writerow([
                name,
                result["so_lan"],
                f'{result["trung_binh_ms"]:.6f}',
                f'{result["nho_nhat_ms"]:.6f}',
                f'{result["lon_nhat_ms"]:.6f}',
                f'{result["do_lech_chuan_ms"]:.6f}',
                (
                    f'{result.get("nonce_trung_binh", ""):.2f}'
                    if result.get("nonce_trung_binh")
                    is not None
                    else ""
                ),
            ])

    print("\nKẾT QUẢ THỰC NGHIỆM")
    print("-" * 95)

    print(
        f'{"Thành phần":35}'
        f'{"Số lần":>10}'
        f'{"TB (ms)":>15}'
        f'{"Min (ms)":>15}'
        f'{"Max (ms)":>15}'
    )

    print("-" * 95)

    for name, result in results.items():
        print(
            f'{name:35}'
            f'{result["so_lan"]:>10}'
            f'{result["trung_binh_ms"]:>15.6f}'
            f'{result["nho_nhat_ms"]:>15.6f}'
            f'{result["lon_nhat_ms"]:>15.6f}'
        )

    print("-" * 95)
    print(f"\nĐã lưu JSON tại: {json_path}")
    print(f"Đã lưu CSV tại:  {csv_path}")


if __name__ == "__main__":
    main()