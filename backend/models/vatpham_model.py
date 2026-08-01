from database.connection import vatpham_collection
from models.nhanvat_vatpham_model import NhanVatVatPham
import datetime
import uuid

class VatPham:
    def __init__(self, ten_vat_pham, mo_ta, gia_thue, don_vi_thue, 
                 thoi_gian_thue_toi_da, tien_dat_coc, do_hiem,
                 ma_game, duoc_dung_cho=None, ma_danh_muc=None, loai='vat_pham'):
        self.ma_vat_pham = str(uuid.uuid4())
        self.ten_vat_pham = ten_vat_pham
        self.mo_ta = mo_ta
        self.gia_thue = gia_thue
        self.don_vi_thue = don_vi_thue
        self.thoi_gian_thue_toi_da = thoi_gian_thue_toi_da
        self.tien_dat_coc = tien_dat_coc
        self.do_hiem = do_hiem
        self.ma_game = ma_game
        self.duoc_dung_cho = duoc_dung_cho
        self.ma_danh_muc = ma_danh_muc
        self.loai = loai
        self.trang_thai_thue = 'còn trống'
        self.ngay_dang = datetime.datetime.now(datetime.timezone.utc)
        self.ma_bai_dang = str(uuid.uuid4())
        self.created_at = datetime.datetime.now(datetime.timezone.utc)
    
    def to_dict(self):
        return {
            'ma_vat_pham': self.ma_vat_pham,
            'ten_vat_pham': self.ten_vat_pham,
            'mo_ta': self.mo_ta,
            'gia_thue': self.gia_thue,
            'don_vi_thue': self.don_vi_thue,
            'thoi_gian_thue_toi_da': self.thoi_gian_thue_toi_da,
            'tien_dat_coc': self.tien_dat_coc,
            'do_hiem': self.do_hiem,
            'ma_game': self.ma_game,
            'duoc_dung_cho': self.duoc_dung_cho,
            'ma_danh_muc': self.ma_danh_muc,
            'loai': self.loai,
            'trang_thai_thue': self.trang_thai_thue,
            'ngay_dang': self.ngay_dang,
            'ma_bai_dang': self.ma_bai_dang,
            'created_at': self.created_at
        }
    
    def save(self):
        vatpham_collection.insert_one(self.to_dict())
        return self
    
    @staticmethod
    def find_by_ma(ma_vat_pham):
        return vatpham_collection.find_one({'ma_vat_pham': ma_vat_pham}, {'_id': 0})
    
    @staticmethod
    def find_by_game(ma_game):
        return list(vatpham_collection.find({'ma_game': ma_game}, {'_id': 0}))
    
    @staticmethod
    def find_by_character(ma_nhan_vat):
        relations = NhanVatVatPham.find_by_nhan_vat(
            ma_nhan_vat
        )

        ma_vat_pham_list = [
            relation['ma_vat_pham']
            for relation in relations
        ]

        if not ma_vat_pham_list:
            return []

        return list(
            vatpham_collection.find(
                {
                    'ma_vat_pham': {
                        '$in': ma_vat_pham_list
                    }
                },
                {'_id': 0}
            )
        )
    
    @staticmethod
    def find_available():
        return list(vatpham_collection.find({'trang_thai_thue': 'còn trống'}, {'_id': 0}))
    
    @staticmethod
    def find_all():
        return list(vatpham_collection.find({}, {'_id': 0}))
    
    @staticmethod
    def update_status(ma_vat_pham, status):
        vatpham_collection.update_one(
            {'ma_vat_pham': ma_vat_pham},
            {'$set': {'trang_thai_thue': status}}
        )