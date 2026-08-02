import csv
import hashlib
import json
import statistics
import time
from pathlib import Path


# Số lần băm cho mỗi thuật toán
ITERATIONS = 10_000

# Thư mục lưu kết quả
OUTPUT_DIRECTORY = Path("benchmark_results")

# Danh sách thuật toán dùng để so sánh
HASH_ALGORITHMS = {
    "MD5": hashlib.md5,
    "SHA-1": hashlib.sha1,
    "SHA-224": hashlib.sha224,
    "SHA-256": hashlib.sha256,
    "SHA-384": hashlib.sha384,
    "SHA-512": hashlib.sha512,
    "BLAKE2b": hashlib.blake2b,
}


def create_rental_payload() -> str:
    """
    Tạo payload dựa trên giao dịch thuê NFT của hệ thống.
    Tất cả thuật toán đều băm cùng một dữ liệu này.
    """
    payload = {
        "ma_giao_dich": "GD-DEMO-001",
        "ma_hop_dong": "HD-DEMO-001",
        "ma_nft": "NFT-DEMO-001",
        "ma_nguoi_thue": "USER-DEMO-001",
        "dia_chi_nguoi_thue": "14a5FLUB5j-demo-renter",
        "dia_chi_chu_so_huu": "1OwnerWallet-demo",
        "loai_giao_dich": "thanh_toan_thue",
        "so_tien_giao_dich": 10.5,
        "tien_thue": 10,
        "phi_dich_vu": 0.5,
        "so_ngay_thue": 1,
        "trang_thai_thanh_toan": "da_thanh_toan",
        "thoi_gian_tao": "2026-08-01T17:00:00Z",
    }

    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def hash_payload(
    hash_function,
    payload_bytes: bytes,
) -> str:
    """
    Băm payload và trả về chuỗi hexadecimal.
    """
    return hash_function(payload_bytes).hexdigest()


def benchmark_algorithm(
    algorithm_name: str,
    hash_function,
    payload_bytes: bytes,
) -> dict:
    """
    Chạy một thuật toán nhiều lần và thu thập số liệu.
    """
    durations_ms = []

    start_total = time.perf_counter()

    for _ in range(ITERATIONS):
        start = time.perf_counter()

        hash_payload(
            hash_function,
            payload_bytes,
        )

        end = time.perf_counter()

        durations_ms.append(
            (end - start) * 1000
        )

    end_total = time.perf_counter()

    total_seconds = end_total - start_total
    average_ms = statistics.mean(durations_ms)

    hashes_per_second = (
        ITERATIONS / total_seconds
        if total_seconds > 0
        else 0
    )

    sample_hash = hash_payload(
        hash_function,
        payload_bytes,
    )

    return {
        "thuat_toan": algorithm_name,
        "so_lan": ITERATIONS,
        "thoi_gian_trung_binh_ms": average_ms,
        "tong_thoi_gian_s": total_seconds,
        "nho_nhat_ms": min(durations_ms),
        "lon_nhat_ms": max(durations_ms),
        "do_lech_chuan_ms": (
            statistics.stdev(durations_ms)
            if len(durations_ms) > 1
            else 0
        ),
        "so_lan_bam_moi_giay": hashes_per_second,
        "do_dai_hash_bit": len(sample_hash) * 4,
        "do_dai_hash_hex": len(sample_hash),
        "hash_mau": sample_hash,
    }


def save_json(results: list[dict]) -> Path:
    """
    Lưu kết quả dạng JSON.
    """
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)

    output_path = (
        OUTPUT_DIRECTORY
        / "benchmark_hash_algorithm_results.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def save_csv(results: list[dict]) -> Path:
    """
    Lưu kết quả dạng CSV.
    """
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)

    output_path = (
        OUTPUT_DIRECTORY
        / "benchmark_hash_algorithm_results.csv"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "Thuật toán",
            "Số lần",
            "Thời gian TB (ms)",
            "Tổng thời gian (s)",
            "Nhỏ nhất (ms)",
            "Lớn nhất (ms)",
            "Độ lệch chuẩn (ms)",
            "Số lần băm/giây",
            "Độ dài hash (bit)",
            "Độ dài hash (ký tự hex)",
        ])

        for result in results:
            writer.writerow([
                result["thuat_toan"],
                result["so_lan"],
                f'{result["thoi_gian_trung_binh_ms"]:.9f}',
                f'{result["tong_thoi_gian_s"]:.6f}',
                f'{result["nho_nhat_ms"]:.9f}',
                f'{result["lon_nhat_ms"]:.9f}',
                f'{result["do_lech_chuan_ms"]:.9f}',
                f'{result["so_lan_bam_moi_giay"]:.2f}',
                result["do_dai_hash_bit"],
                result["do_dai_hash_hex"],
            ])

    return output_path


def print_comparison(results: list[dict]) -> None:
    """
    In kết quả theo dạng gần giống mẫu báo cáo.
    """
    sorted_results = sorted(
        results,
        key=lambda item:
            item["thoi_gian_trung_binh_ms"],
    )

    sha256_result = next(
        result
        for result in results
        if result["thuat_toan"] == "SHA-256"
    )

    sha256_average = (
        sha256_result["thoi_gian_trung_binh_ms"]
    )

    print()
    print("=" * 72)
    print("THỰC NGHIỆM: SO SÁNH THUẬT TOÁN BĂM")
    print("=" * 72)
    print()

    print(
        f"Đã chạy {ITERATIONS:,} lần "
        "cho mỗi thuật toán."
    )

    print()
    print("KẾT QUẢ SO SÁNH (sắp xếp theo tốc độ):")
    print("-" * 94)

    print(
        f'{"Thuật toán":<14}'
        f'{"Thời gian TB (ms)":>20}'
        f'{"Tổng thời gian (s)":>22}'
        f'{"Tỷ lệ với SHA-256":>22}'
    )

    print("-" * 94)

    for result in sorted_results:
        ratio = (
            result["thoi_gian_trung_binh_ms"]
            / sha256_average
        )

        baseline_text = (
            " (baseline)"
            if result["thuat_toan"] == "SHA-256"
            else ""
        )

        print(
            f'{result["thuat_toan"]:<14}'
            f'{result["thoi_gian_trung_binh_ms"]:>20.9f}'
            f'{result["tong_thoi_gian_s"]:>22.6f}'
            f'{ratio:>18.2f}x'
            f'{baseline_text}'
        )

    print("-" * 94)
    print()
    print("TỐC ĐỘ XỬ LÝ (số lần băm/giây):")
    print("-" * 72)

    for result in sorted(
        results,
        key=lambda item:
            item["so_lan_bam_moi_giay"],
        reverse=True,
    ):
        hashes_per_second = (
            result["so_lan_bam_moi_giay"]
        )

        print(
            f'{result["thuat_toan"]:<14}: '
            f'{hashes_per_second / 1000:>12.2f} KHz '
            f'({hashes_per_second:,.2f} lần/giây)'
        )

    print("-" * 72)
    print()
    print("ĐỘ DÀI GIÁ TRỊ BĂM:")
    print("-" * 72)

    for result in results:
        print(
            f'{result["thuat_toan"]:<14}: '
            f'{result["do_dai_hash_bit"]:>4} bit - '
            f'{result["do_dai_hash_hex"]:>3} ký tự hex'
        )

    print("-" * 72)


def main() -> None:
    payload = create_rental_payload()
    payload_bytes = payload.encode("utf-8")

    print("=" * 72)
    print("THỰC NGHIỆM: SO SÁNH THUẬT TOÁN BĂM")
    print("=" * 72)

    print(
        f"\nĐang chạy test với "
        f"{ITERATIONS:,} lần cho mỗi thuật toán...\n"
    )

    results = []

    for algorithm_name, hash_function in (
        HASH_ALGORITHMS.items()
    ):
        print(
            f"Đang test {algorithm_name}..."
        )

        result = benchmark_algorithm(
            algorithm_name,
            hash_function,
            payload_bytes,
        )

        results.append(result)

    print_comparison(results)

    json_path = save_json(results)
    csv_path = save_csv(results)

    print()
    print("Đã lưu kết quả:")
    print(f"- JSON: {json_path}")
    print(f"- CSV:  {csv_path}")


if __name__ == "__main__":
    main()