from database.connection import (
    vatpham_collection,
    nhanvat_vatpham_collection
)


def migrate():
    items = vatpham_collection.find({
        'duoc_dung_cho': {
            '$exists': True,
            '$ne': None
        }
    })

    created = 0

    for item in items:
        ma_nhan_vat = item.get('duoc_dung_cho')
        ma_vat_pham = item.get('ma_vat_pham')

        if not ma_nhan_vat or not ma_vat_pham:
            continue

        existing = nhanvat_vatpham_collection.find_one({
            'ma_nhan_vat': ma_nhan_vat,
            'ma_vat_pham': ma_vat_pham
        })

        if existing:
            continue

        nhanvat_vatpham_collection.insert_one({
            'ma_nhan_vat': ma_nhan_vat,
            'ma_vat_pham': ma_vat_pham
        })

        created += 1

    print(
        f'Đã tạo {created} quan hệ '
        'nhân vật - vật phẩm'
    )


if __name__ == '__main__':
    migrate()