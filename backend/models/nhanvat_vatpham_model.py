from database.connection import nhanvat_vatpham_collection


class NhanVatVatPham:
    @staticmethod
    def create(ma_nhan_vat, ma_vat_pham):
        existing = nhanvat_vatpham_collection.find_one({
            'ma_nhan_vat': ma_nhan_vat,
            'ma_vat_pham': ma_vat_pham
        })

        if existing:
            return existing

        relation = {
            'ma_nhan_vat': ma_nhan_vat,
            'ma_vat_pham': ma_vat_pham
        }

        nhanvat_vatpham_collection.insert_one(relation)
        relation.pop('_id', None)

        return relation

    @staticmethod
    def find_by_vat_pham(ma_vat_pham):
        return list(
            nhanvat_vatpham_collection.find(
                {'ma_vat_pham': ma_vat_pham},
                {'_id': 0}
            )
        )

    @staticmethod
    def find_by_nhan_vat(ma_nhan_vat):
        return list(
            nhanvat_vatpham_collection.find(
                {'ma_nhan_vat': ma_nhan_vat},
                {'_id': 0}
            )
        )

    @staticmethod
    def is_compatible(ma_nhan_vat, ma_vat_pham):
        relation = nhanvat_vatpham_collection.find_one({
            'ma_nhan_vat': ma_nhan_vat,
            'ma_vat_pham': ma_vat_pham
        })

        return relation is not None

    @staticmethod
    def delete_by_vat_pham(ma_vat_pham):
        return nhanvat_vatpham_collection.delete_many({
            'ma_vat_pham': ma_vat_pham
        })

    @staticmethod
    def delete_by_nhan_vat(ma_nhan_vat):
        return nhanvat_vatpham_collection.delete_many({
            'ma_nhan_vat': ma_nhan_vat
        })