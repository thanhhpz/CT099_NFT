from database.connection import hopdong_collection
import datetime
import uuid

class HopDong:
    def __init__(
        self,
        ma_bai_dang,
        ma_nguoi_thue,
        thoi_gian_bat_dau,
        thoi_gian_ket_thuc,
        ma_nhan_vat=None
    ):
        self.ma_hop_dong = str(uuid.uuid4())
        self.ma_bai_dang = ma_bai_dang
        self.ma_nguoi_thue = ma_nguoi_thue
        self.thoi_gian_bat_dau = thoi_gian_bat_dau
        self.thoi_gian_ket_thuc = thoi_gian_ket_thuc
        self.trang_thai_thue = 'dang_thue'
        self.ma_nhan_vat = ma_nhan_vat
        self.tong_tien = 0
        self.so_ngay_thue = 0
        self.don_vi_thue = 'ngay'
        self.phi_dich_vu = 0
        self.created_at = datetime.datetime.now(
            datetime.timezone.utc
        )
    
    def to_dict(self):
        return {
            'ma_hop_dong': self.ma_hop_dong,
            'ma_bai_dang': self.ma_bai_dang,
            'ma_nguoi_thue': self.ma_nguoi_thue,
            'thoi_gian_bat_dau': self.thoi_gian_bat_dau,
            'thoi_gian_ket_thuc': self.thoi_gian_ket_thuc,
            'trang_thai_thue': self.trang_thai_thue,
            'ma_nhan_vat': self.ma_nhan_vat,
            'tong_tien': self.tong_tien,
            'so_ngay_thue': self.so_ngay_thue,
            'don_vi_thue': self.don_vi_thue,
            'phi_dich_vu': self.phi_dich_vu,
            'created_at': self.created_at
        }
    
    def save(self):
        hopdong_collection.insert_one(self.to_dict())
        return self
    
    @staticmethod
    def find_by_ma(ma_hop_dong):
        return hopdong_collection.find_one({'ma_hop_dong': ma_hop_dong}, {'_id': 0})
    
    @staticmethod
    def find_by_nguoi_thue(ma_nguoi_thue):
        return list(hopdong_collection.find({'ma_nguoi_thue': ma_nguoi_thue}, {'_id': 0}))
    
    @staticmethod
    def find_by_bai_dang(ma_bai_dang):
        return list(hopdong_collection.find({'ma_bai_dang': ma_bai_dang}, {'_id': 0}))
    
    @staticmethod
    def find_all():
        return list(hopdong_collection.find({}, {'_id': 0}))
    
    @staticmethod
    def update_status(ma_hop_dong, trang_thai):
        hopdong_collection.update_one(
            {'ma_hop_dong': ma_hop_dong},
            {'$set': {'trang_thai_thue': trang_thai}}
        )
    
    @staticmethod
    def find_active_by_nft(ma_nft):
        """Tìm hợp đồng đang thuê của một NFT"""
        from models.nft_model import NFT
        from models.vatpham_model import VatPham
        
        # Tìm NFT để lấy ma_vat_pham
        nft = NFT.find_by_ma(ma_nft)
        if not nft:
            return None
        
        # Tìm vật phẩm từ NFT
        item = VatPham.find_by_ma(nft.get('ma_vat_pham'))
        if not item:
            return None
        
        # Tìm hợp đồng đang thuê của vật phẩm này
        hopdong = hopdong_collection.find_one({
            'ma_bai_dang': item.get('ma_bai_dang'),
            'trang_thai_thue': 'dang_thue'
        })
        
        return hopdong