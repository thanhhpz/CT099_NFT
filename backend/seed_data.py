from database.connection import db
import datetime
import uuid
import hashlib
import bcrypt
from ecdsa import SigningKey, SECP256k1
import base58

# ============================================================
# HÀM TẠO VÍ BLOCKCHAIN (CÓ PRIVATE KEY, PUBLIC KEY, ADDRESS)
# ============================================================
def generate_wallet():
    """Tạo ví blockchain với Private Key, Public Key, Address"""
    # 1. Tạo Private Key bằng ECDSA trên đường cong SECP256k1
    private_key = SigningKey.generate(curve=SECP256k1)
    private_key_hex = private_key.to_string().hex()
    
    # 2. Lấy Public Key từ Private Key
    public_key = private_key.get_verifying_key()
    public_key_hex = public_key.to_string().hex()
    
    # 3. Tạo địa chỉ ví từ Public Key (SHA-256 + RIPEMD-160)
    # Bước 1: SHA-256 của public key
    sha256_hash = hashlib.sha256(public_key.to_string()).hexdigest()
    # Bước 2: RIPEMD-160 (mô phỏng bằng SHA-256)
    ripe_hash = hashlib.sha256(sha256_hash.encode()).hexdigest()[:40]
    # Bước 3: Thêm version byte (0x00 cho mainnet)
    versioned = '00' + ripe_hash
    # Bước 4: Double SHA-256 checksum
    checksum = hashlib.sha256(hashlib.sha256(versioned.encode()).hexdigest().encode()).hexdigest()[:8]
    # Bước 5: Base58 encode
    address = base58.b58encode(bytes.fromhex(versioned + checksum)).decode()
    
    return {
        'private_key': private_key_hex,
        'public_key': public_key_hex,
        'address': address
    }


# ============================================================
# HÀM SEED DỮ LIỆU
# ============================================================
def seed_database():
    print("=" * 60)
    print("BẮT ĐẦU TẠO DỮ LIỆU MẪU CHO HỆ THỐNG NFT RENTAL")
    print("=" * 60)
    
    # Xóa dữ liệu cũ
    db.nguoidung.delete_many({})
    db.game.delete_many({})
    db.nhanvat.delete_many({})
    db.vatpham.delete_many({})
    db.nft.delete_many({})
    db.vi.delete_many({})
    db.hopdong.delete_many({})
    db.giaodich.delete_many({})
    print("\n🗑️ Đã xóa dữ liệu cũ")
    
    # ============================================================
    # 1. TẠO NGƯỜI DÙNG
    # ============================================================
    print("\n📋 TẠO NGƯỜI DÙNG:")
    
    users_data = [
        {"ten_nguoi_dung": "admin", "mat_khau": "123456", 
         "ho_ten": "Quản trị viên", "email": "admin@email.com", "vai_tro": "quan_tri"},
        {"ten_nguoi_dung": "thanh", "mat_khau": "123456",
         "ho_ten": "Huỳnh Phước Thanh", "email": "thanh@email.com", "vai_tro": "nguoi_dung"},
        {"ten_nguoi_dung": "tran", "mat_khau": "123456",
         "ho_ten": "Lý Khánh Trân", "email": "tran@email.com", "vai_tro": "nguoi_dung"},
        {"ten_nguoi_dung": "han", "mat_khau": "123456",
         "ho_ten": "Nguyễn Thị Ngọc Hân", "email": "han@email.com", "vai_tro": "nguoi_dung"},
        {"ten_nguoi_dung": "huy", "mat_khau": "123456",
         "ho_ten": "Trương Quốc Huy", "email": "huy@email.com", "vai_tro": "nguoi_dung"},
        {"ten_nguoi_dung": "alice", "mat_khau": "123456",
         "ho_ten": "Alice Wonderland", "email": "alice@email.com", "vai_tro": "nguoi_dung"},
        {"ten_nguoi_dung": "bob", "mat_khau": "123456",
         "ho_ten": "Bob Builder", "email": "bob@email.com", "vai_tro": "nguoi_dung"}
    ]
    
    user_ids = {}
    for u in users_data:
        # Mã hóa mật khẩu
        hashed = bcrypt.hashpw(u["mat_khau"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user = {
            "ma_nguoi_dung": str(uuid.uuid4()),
            "ten_nguoi_dung": u["ten_nguoi_dung"],
            "mat_khau": hashed,
            "ho_ten": u["ho_ten"],
            "email": u["email"],
            "so_dien_thoai": "",
            "vai_tro": u["vai_tro"],
            "dia_chi_vi": None,
            "created_at": datetime.datetime.utcnow()
        }
        db.nguoidung.insert_one(user)
        user_ids[u["ten_nguoi_dung"]] = user["ma_nguoi_dung"]
        print(f"  ✅ {u['ten_nguoi_dung']} - {u['ho_ten']}")
    
    # ============================================================
    # 2. TẠO VÍ BLOCKCHAIN CHO NGƯỜI DÙNG
    # ============================================================
    print("\n💰 TẠO VÍ BLOCKCHAIN:")
    
    all_users = list(db.nguoidung.find({}))
    wallet_addresses = {}
    
    for u in all_users:
        # Tạo ví blockchain
        wallet = generate_wallet()
        
        # Lưu ví
        db.vi.insert_one({
            'dia_chi': wallet['address'],
            'ten_nguoi_dung': u['ten_nguoi_dung'],
            'so_du': 1000,
            'private_key': wallet['private_key'],
            'public_key': wallet['public_key'],
            'created_at': datetime.datetime.utcnow()
        })
        
        # Cập nhật địa chỉ ví cho user
        db.nguoidung.update_one(
            {'ma_nguoi_dung': u['ma_nguoi_dung']},
            {'$set': {'dia_chi_vi': wallet['address']}}
        )
        
        wallet_addresses[u['ten_nguoi_dung']] = wallet['address']
        print(f"  ✅ {u['ten_nguoi_dung']} - {wallet['address'][:15]}... (1000 COINS)")
    
    # ============================================================
    # 3. TẠO TRÒ CHƠI
    # ============================================================
    print("\n🎮 TẠO TRÒ CHƠI:")
    
    games_data = [
        {"ten_game": "Tây Du Ký", "mo_ta_game": "Game nhập vai thần thoại Trung Quốc", "nha_phat_hanh": "Tencent"},
        {"ten_game": "Liên Minh Huyền Thoại", "mo_ta_game": "MOBA huyền thoại", "nha_phat_hanh": "Riot Games"},
        {"ten_game": "Genshin Impact", "mo_ta_game": "Open world RPG", "nha_phat_hanh": "miHoYo"},
        {"ten_game": "One Piece", "mo_ta_game": "Game hải tặc", "nha_phat_hanh": "Bandai Namco"},
        {"ten_game": "Naruto", "mo_ta_game": "Game ninja", "nha_phat_hanh": "Bandai Namco"},
        {"ten_game": "Axie Infinity", "mo_ta_game": "Game blockchain breeding", "nha_phat_hanh": "Sky Mavis"},
        {"ten_game": "The Sandbox", "mo_ta_game": "Metaverse game", "nha_phat_hanh": "Animoca Brands"}
    ]
    
    game_ids = {}
    for g in games_data:
        game = {
            "ma_game": str(uuid.uuid4()),
            "ten_game": g["ten_game"],
            "mo_ta_game": g["mo_ta_game"],
            "nha_phat_hanh": g["nha_phat_hanh"],
            "created_at": datetime.datetime.utcnow()
        }
        db.game.insert_one(game)
        game_ids[g["ten_game"]] = game["ma_game"]
        print(f"  ✅ {g['ten_game']}")
    
    # ============================================================
    # 4. TẠO NHÂN VẬT
    # ============================================================
    print("\n👤 TẠO NHÂN VẬT:")
    
    characters_data = [
        # Tây Du Ký
        {"ten_nhan_vat": "Tôn Ngộ Không", "ma_game": game_ids["Tây Du Ký"]},
        {"ten_nhan_vat": "Trư Bát Giới", "ma_game": game_ids["Tây Du Ký"]},
        {"ten_nhan_vat": "Đường Tăng", "ma_game": game_ids["Tây Du Ký"]},
        {"ten_nhan_vat": "Sa Tăng", "ma_game": game_ids["Tây Du Ký"]},
        {"ten_nhan_vat": "Bạch Long Mã", "ma_game": game_ids["Tây Du Ký"]},
        # Liên Minh Huyền Thoại
        {"ten_nhan_vat": "Đấu Sĩ", "ma_game": game_ids["Liên Minh Huyền Thoại"]},
        {"ten_nhan_vat": "Xạ Thủ", "ma_game": game_ids["Liên Minh Huyền Thoại"]},
        {"ten_nhan_vat": "Pháp Sư", "ma_game": game_ids["Liên Minh Huyền Thoại"]},
        {"ten_nhan_vat": "Sát Thủ", "ma_game": game_ids["Liên Minh Huyền Thoại"]},
        {"ten_nhan_vat": "Hỗ Trợ", "ma_game": game_ids["Liên Minh Huyền Thoại"]},
        # Genshin Impact
        {"ten_nhan_vat": "Lữ Khách", "ma_game": game_ids["Genshin Impact"]},
        {"ten_nhan_vat": "Paimon", "ma_game": game_ids["Genshin Impact"]},
        {"ten_nhan_vat": "Diluc", "ma_game": game_ids["Genshin Impact"]},
        {"ten_nhan_vat": "Venti", "ma_game": game_ids["Genshin Impact"]},
        {"ten_nhan_vat": "Zhongli", "ma_game": game_ids["Genshin Impact"]},
        # One Piece
        {"ten_nhan_vat": "Luffy", "ma_game": game_ids["One Piece"]},
        {"ten_nhan_vat": "Zoro", "ma_game": game_ids["One Piece"]},
        {"ten_nhan_vat": "Sanji", "ma_game": game_ids["One Piece"]},
        {"ten_nhan_vat": "Nami", "ma_game": game_ids["One Piece"]},
        {"ten_nhan_vat": "Chopper", "ma_game": game_ids["One Piece"]},
        # Naruto
        {"ten_nhan_vat": "Naruto", "ma_game": game_ids["Naruto"]},
        {"ten_nhan_vat": "Sasuke", "ma_game": game_ids["Naruto"]},
        {"ten_nhan_vat": "Sakura", "ma_game": game_ids["Naruto"]},
        {"ten_nhan_vat": "Kakashi", "ma_game": game_ids["Naruto"]},
        {"ten_nhan_vat": "Gaara", "ma_game": game_ids["Naruto"]},
        # Axie Infinity
        {"ten_nhan_vat": "Axie Plant", "ma_game": game_ids["Axie Infinity"]},
        {"ten_nhan_vat": "Axie Beast", "ma_game": game_ids["Axie Infinity"]},
        {"ten_nhan_vat": "Axie Bird", "ma_game": game_ids["Axie Infinity"]},
        {"ten_nhan_vat": "Axie Bug", "ma_game": game_ids["Axie Infinity"]},
        {"ten_nhan_vat": "Axie Reptile", "ma_game": game_ids["Axie Infinity"]},
        # The Sandbox
        {"ten_nhan_vat": "Avatar", "ma_game": game_ids["The Sandbox"]}
    ]
    
    char_ids = {}
    for c in characters_data:
        char = {
            "ma_nhan_vat": str(uuid.uuid4()),
            "ten_nhan_vat": c["ten_nhan_vat"],
            "ma_game": c["ma_game"],
            "created_at": datetime.datetime.utcnow()
        }
        db.nhanvat.insert_one(char)
        char_ids[c["ten_nhan_vat"]] = char["ma_nhan_vat"]
        print(f"  ✅ {c['ten_nhan_vat']}")
    
    # ============================================================
    # 5. TẠO VẬT PHẨM
    # ============================================================
    print("\n🗡️ TẠO VẬT PHẨM:")
    
    items_data = [
        # Tây Du Ký
        {"ten_vat_pham": "Gậy Như Ý", "mo_ta": "Vũ khí thần thoại của Tôn Ngộ Không", "gia_thue": 10, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 30, "tien_dat_coc": 50, "do_hiem": "huyền thoại", 
         "ma_game": game_ids["Tây Du Ký"], "duoc_dung_cho": char_ids["Tôn Ngộ Không"], "loai": "vũ khí"},
        {"ten_vat_pham": "Áo Giáp Kim Cương", "mo_ta": "Áo giáp bất khả xâm phạm", "gia_thue": 15, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 30, "tien_dat_coc": 75, "do_hiem": "siêu hiếm", 
         "ma_game": game_ids["Tây Du Ký"], "duoc_dung_cho": char_ids["Tôn Ngộ Không"], "loai": "áo giáp"},
        {"ten_vat_pham": "Phân Thân Thuật", "mo_ta": "Kỹ năng đặc biệt của Tôn Ngộ Không", "gia_thue": 20, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 20, "tien_dat_coc": 100, "do_hiem": "siêu hiếm", 
         "ma_game": game_ids["Tây Du Ký"], "duoc_dung_cho": char_ids["Tôn Ngộ Không"], "loai": "kỹ năng"},
        {"ten_vat_pham": "Bửu Bối Cửu Xỉ Đinh Ba", "mo_ta": "Vũ khí của Trư Bát Giới", "gia_thue": 12, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 25, "tien_dat_coc": 60, "do_hiem": "hiếm", 
         "ma_game": game_ids["Tây Du Ký"], "duoc_dung_cho": char_ids["Trư Bát Giới"], "loai": "vũ khí"},
        {"ten_vat_pham": "Kim Cô", "mo_ta": "Vật phẩm của Đường Tăng", "gia_thue": 5, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 15, "tien_dat_coc": 25, "do_hiem": "thường", 
         "ma_game": game_ids["Tây Du Ký"], "duoc_dung_cho": char_ids["Đường Tăng"], "loai": "phụ kiện"},
        {"ten_vat_pham": "Phật Giáp", "mo_ta": "Áo giáp của Đường Tăng", "gia_thue": 8, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 20, "tien_dat_coc": 40, "do_hiem": "thường", 
         "ma_game": game_ids["Tây Du Ký"], "duoc_dung_cho": char_ids["Đường Tăng"], "loai": "áo giáp"},
        {"ten_vat_pham": "Nguyệt Nha Sào", "mo_ta": "Vũ khí của Sa Tăng", "gia_thue": 10, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 25, "tien_dat_coc": 50, "do_hiem": "hiếm", 
         "ma_game": game_ids["Tây Du Ký"], "duoc_dung_cho": char_ids["Sa Tăng"], "loai": "vũ khí"},
        {"ten_vat_pham": "Long Lân Giáp", "mo_ta": "Áo giáp của Bạch Long Mã", "gia_thue": 7, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 20, "tien_dat_coc": 35, "do_hiem": "thường", 
         "ma_game": game_ids["Tây Du Ký"], "duoc_dung_cho": char_ids["Bạch Long Mã"], "loai": "áo giáp"},
        
        # Liên Minh Huyền Thoại
        {"ten_vat_pham": "Kiếm Vô Cực", "mo_ta": "Vũ khí tối thượng", "gia_thue": 25, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 30, "tien_dat_coc": 125, "do_hiem": "huyền thoại", 
         "ma_game": game_ids["Liên Minh Huyền Thoại"], "duoc_dung_cho": char_ids["Đấu Sĩ"], "loai": "vũ khí"},
        {"ten_vat_pham": "Giáp Máu", "mo_ta": "Áo giáp hút máu", "gia_thue": 18, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 25, "tien_dat_coc": 90, "do_hiem": "siêu hiếm", 
         "ma_game": game_ids["Liên Minh Huyền Thoại"], "duoc_dung_cho": char_ids["Đấu Sĩ"], "loai": "áo giáp"},
        {"ten_vat_pham": "Cung Vô Cực", "mo_ta": "Cung tên thần thoại", "gia_thue": 22, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 30, "tien_dat_coc": 110, "do_hiem": "siêu hiếm", 
         "ma_game": game_ids["Liên Minh Huyền Thoại"], "duoc_dung_cho": char_ids["Xạ Thủ"], "loai": "vũ khí"},
        {"ten_vat_pham": "Trượng Phép", "mo_ta": "Trượng phép thuật", "gia_thue": 20, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 25, "tien_dat_coc": 100, "do_hiem": "hiếm", 
         "ma_game": game_ids["Liên Minh Huyền Thoại"], "duoc_dung_cho": char_ids["Pháp Sư"], "loai": "vũ khí"},
        {"ten_vat_pham": "Dao Găm", "mo_ta": "Vũ khí sát thủ", "gia_thue": 15, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 20, "tien_dat_coc": 75, "do_hiem": "hiếm", 
         "ma_game": game_ids["Liên Minh Huyền Thoại"], "duoc_dung_cho": char_ids["Sát Thủ"], "loai": "vũ khí"},
        {"ten_vat_pham": "Khiên Bảo Vệ", "mo_ta": "Khiên bảo vệ đồng đội", "gia_thue": 12, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 20, "tien_dat_coc": 60, "do_hiem": "thường", 
         "ma_game": game_ids["Liên Minh Huyền Thoại"], "duoc_dung_cho": char_ids["Hỗ Trợ"], "loai": "áo giáp"},
        
        # Genshin Impact
        {"ten_vat_pham": "Kiếm Tây Phong", "mo_ta": "Kiếm của Lữ Khách", "gia_thue": 8, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 15, "tien_dat_coc": 40, "do_hiem": "thường", 
         "ma_game": game_ids["Genshin Impact"], "duoc_dung_cho": char_ids["Lữ Khách"], "loai": "vũ khí"},
        {"ten_vat_pham": "Cánh Bay", "mo_ta": "Cánh giúp bay lượn", "gia_thue": 5, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 10, "tien_dat_coc": 25, "do_hiem": "thường", 
         "ma_game": game_ids["Genshin Impact"], "duoc_dung_cho": char_ids["Lữ Khách"], "loai": "phụ kiện"},
        {"ten_vat_pham": "Đại Kiếm Ánh Sáng", "mo_ta": "Kiếm của Diluc", "gia_thue": 30, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 30, "tien_dat_coc": 150, "do_hiem": "huyền thoại", 
         "ma_game": game_ids["Genshin Impact"], "duoc_dung_cho": char_ids["Diluc"], "loai": "vũ khí"},
        {"ten_vat_pham": "Áo Choàng Lửa", "mo_ta": "Áo choàng của Diluc", "gia_thue": 20, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 25, "tien_dat_coc": 100, "do_hiem": "siêu hiếm", 
         "ma_game": game_ids["Genshin Impact"], "duoc_dung_cho": char_ids["Diluc"], "loai": "áo giáp"},
        {"ten_vat_pham": "Cung Gió", "mo_ta": "Cung của Venti", "gia_thue": 25, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 30, "tien_dat_coc": 125, "do_hiem": "siêu hiếm", 
         "ma_game": game_ids["Genshin Impact"], "duoc_dung_cho": char_ids["Venti"], "loai": "vũ khí"},
        {"ten_vat_pham": "Giáo Bảo Vệ", "mo_ta": "Giáo của Zhongli", "gia_thue": 28, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 30, "tien_dat_coc": 140, "do_hiem": "siêu hiếm", 
         "ma_game": game_ids["Genshin Impact"], "duoc_dung_cho": char_ids["Zhongli"], "loai": "vũ khí"},
        {"ten_vat_pham": "Khiên Đá", "mo_ta": "Khiên của Zhongli", "gia_thue": 22, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 25, "tien_dat_coc": 110, "do_hiem": "hiếm", 
         "ma_game": game_ids["Genshin Impact"], "duoc_dung_cho": char_ids["Zhongli"], "loai": "áo giáp"},
        
        # Axie Infinity
        {"ten_vat_pham": "Axie Plant Seed", "mo_ta": "Hạt giống Axie Plant", "gia_thue": 50, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 7, "tien_dat_coc": 250, "do_hiem": "huyền thoại", 
         "ma_game": game_ids["Axie Infinity"], "duoc_dung_cho": char_ids["Axie Plant"], "loai": "vật phẩm"},
        {"ten_vat_pham": "Axie Beast Egg", "mo_ta": "Trứng Axie Beast", "gia_thue": 45, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 7, "tien_dat_coc": 225, "do_hiem": "huyền thoại", 
         "ma_game": game_ids["Axie Infinity"], "duoc_dung_cho": char_ids["Axie Beast"], "loai": "vật phẩm"},
        
        # The Sandbox
        {"ten_vat_pham": "Land NFT", "mo_ta": "Đất trong The Sandbox", "gia_thue": 100, 
         "don_vi_thue": "ngày", "thoi_gian_thue_toi_da": 30, "tien_dat_coc": 500, "do_hiem": "huyền thoại", 
         "ma_game": game_ids["The Sandbox"], "duoc_dung_cho": char_ids["Avatar"], "loai": "bất động sản"}
    ]
    
    item_ids = {}
    for item in items_data:
        item_obj = {
            "ma_vat_pham": str(uuid.uuid4()),
            "ten_vat_pham": item["ten_vat_pham"],
            "mo_ta": item["mo_ta"],
            "gia_thue": item["gia_thue"],
            "don_vi_thue": item["don_vi_thue"],
            "thoi_gian_thue_toi_da": item["thoi_gian_thue_toi_da"],
            "tien_dat_coc": item["tien_dat_coc"],
            "do_hiem": item["do_hiem"],
            "ma_game": item["ma_game"],
            "duoc_dung_cho": item["duoc_dung_cho"],
            "loai": item["loai"],
            "ma_danh_muc": None,
            "trang_thai_thue": "còn trống",
            "ma_bai_dang": str(uuid.uuid4()),
            "ngay_dang": datetime.datetime.utcnow(),
            "created_at": datetime.datetime.utcnow()
        }
        db.vatpham.insert_one(item_obj)
        item_ids[item["ten_vat_pham"]] = item_obj["ma_vat_pham"]
        print(f"  ✅ {item['ten_vat_pham']} - {item['gia_thue']} COINS/ngày")
    
    # ============================================================
    # 6. TẠO NFT TỪ VẬT PHẨM (Chỉ tạo NFT cho 8 vật phẩm đầu)
    # ============================================================
    print("\n🖼️ TẠO NFT:")
    
    # Lấy ví của thanh, alice, bob
    thanh_wallet = db.vi.find_one({'ten_nguoi_dung': 'thanh'})
    alice_wallet = db.vi.find_one({'ten_nguoi_dung': 'alice'})
    bob_wallet = db.vi.find_one({'ten_nguoi_dung': 'bob'})
    
    nft_data = [
        # NFT của Thanh
        {"ten": "Gậy Như Ý", "mo_ta": "NFT đại diện cho Gậy Như Ý", 
         "dia_chi_chu_so_huu": thanh_wallet['dia_chi'], "gia_thue": 10, "ma_vat_pham": item_ids["Gậy Như Ý"]},
        {"ten": "Áo Giáp Kim Cương", "mo_ta": "NFT đại diện cho Áo Giáp Kim Cương",
         "dia_chi_chu_so_huu": thanh_wallet['dia_chi'], "gia_thue": 15, "ma_vat_pham": item_ids["Áo Giáp Kim Cương"]},
        {"ten": "Kiếm Vô Cực", "mo_ta": "NFT đại diện cho Kiếm Vô Cực",
         "dia_chi_chu_so_huu": thanh_wallet['dia_chi'], "gia_thue": 25, "ma_vat_pham": item_ids["Kiếm Vô Cực"]},
        {"ten": "Đại Kiếm Ánh Sáng", "mo_ta": "NFT đại diện cho Đại Kiếm Ánh Sáng",
         "dia_chi_chu_so_huu": thanh_wallet['dia_chi'], "gia_thue": 30, "ma_vat_pham": item_ids["Đại Kiếm Ánh Sáng"]},
        {"ten": "Cung Gió", "mo_ta": "NFT đại diện cho Cung Gió",
         "dia_chi_chu_so_huu": thanh_wallet['dia_chi'], "gia_thue": 25, "ma_vat_pham": item_ids["Cung Gió"]},
        
        # NFT của Alice
        {"ten": "Phân Thân Thuật", "mo_ta": "NFT đại diện cho Phân Thân Thuật",
         "dia_chi_chu_so_huu": alice_wallet['dia_chi'], "gia_thue": 20, "ma_vat_pham": item_ids["Phân Thân Thuật"]},
        {"ten": "Cánh Bay", "mo_ta": "NFT đại diện cho Cánh Bay",
         "dia_chi_chu_so_huu": alice_wallet['dia_chi'], "gia_thue": 5, "ma_vat_pham": item_ids["Cánh Bay"]},
        
        # NFT của Bob
        {"ten": "Axie Plant Seed", "mo_ta": "NFT đại diện cho Axie Plant Seed",
         "dia_chi_chu_so_huu": bob_wallet['dia_chi'], "gia_thue": 50, "ma_vat_pham": item_ids["Axie Plant Seed"]},
    ]
    
    for nft in nft_data:
        nft_obj = {
            "ma_nft": str(uuid.uuid4()),
            "ten": nft["ten"],
            "mo_ta": nft["mo_ta"],
            "dia_chi_chu_so_huu": nft["dia_chi_chu_so_huu"],
            "gia_thue": nft["gia_thue"],
            "ma_vat_pham": nft["ma_vat_pham"],
            "url_hinh_anh": None,
            "trang_thai": "co_san",
            "so_lan_thue": 0,
            "tong_thu_nhap": 0,
            "created_at": datetime.datetime.utcnow()
        }
        db.nft.insert_one(nft_obj)
        print(f"  ✅ {nft['ten']} - {nft['gia_thue']} COINS/ngày")
    
    # ============================================================
    # 7. TẠO HỢP ĐỒNG THUÊ MẪU
    # ============================================================
    print("\n📋 TẠO HỢP ĐỒNG THUÊ MẪU:")
    
    # Tạo 1 hợp đồng thuê mẫu (thanh thuê của alice)
    thanh = db.nguoidung.find_one({'ten_nguoi_dung': 'thanh'})
    alice = db.nguoidung.find_one({'ten_nguoi_dung': 'alice'})
    
    # Lấy vật phẩm của alice
    alice_nft = db.nft.find_one({'dia_chi_chu_so_huu': alice['dia_chi_vi']})
    if alice_nft:
        # Lấy vật phẩm tương ứng
        item = db.vatpham.find_one({'ma_vat_pham': alice_nft['ma_vat_pham']})
        if item:
            hopdong = {
                "ma_hop_dong": str(uuid.uuid4()),
                "ma_bai_dang": item['ma_bai_dang'],
                "ma_nguoi_thue": thanh['ma_nguoi_dung'],
                "ma_nhan_vat": item['duoc_dung_cho'],
                "thoi_gian_bat_dau": datetime.datetime.utcnow(),
                "thoi_gian_ket_thuc": datetime.datetime.utcnow() + datetime.timedelta(days=3),
                "tong_tien": item['gia_thue'] * 3,
                "tien_coc": item['tien_dat_coc'],
                "trang_thai_thue": "dang_thue",
                "danh_gia": None,
                "nhan_xet": None,
                "ngay_tra": None,
                "created_at": datetime.datetime.utcnow()
            }
            db.hopdong.insert_one(hopdong)
            print(f"  ✅ Hợp đồng thuê: {thanh['ten_nguoi_dung']} thuê {item['ten_vat_pham']} của {alice['ten_nguoi_dung']}")
            
            # Cập nhật trạng thái vật phẩm
            db.vatpham.update_one(
                {'ma_vat_pham': item['ma_vat_pham']},
                {'$set': {'trang_thai_thue': 'đang thuê'}}
            )
            
            # Cập nhật trạng thái NFT
            db.nft.update_one(
                {'ma_nft': alice_nft['ma_nft']},
                {'$set': {'trang_thai': 'dang_thue'}}
            )
            
            # Tạo giao dịch thanh toán
            giao_dich = {
                "ma_giao_dich": str(uuid.uuid4()),
                "ma_hop_dong": hopdong["ma_hop_dong"],
                "loai_giao_dich": "thanh_toan_thue",
                "so_tien_giao_dich": hopdong["tong_tien"] + hopdong["tien_coc"],
                "hinh_thuc_thanh_toan": "ví",
                "thoi_gian_thanh_toan": datetime.datetime.utcnow(),
                "created_at": datetime.datetime.utcnow()
            }
            db.giaodich.insert_one(giao_dich)
            print(f"  ✅ Giao dịch thanh toán: {giao_dich['so_tien_giao_dich']} COINS")
    
    # ============================================================
    # 8. THỐNG KÊ DỮ LIỆU
    # ============================================================
    print("\n" + "=" * 60)
    print("📊 THỐNG KÊ DỮ LIỆU ĐÃ TẠO:")
    print("=" * 60)
    print(f"  👤 Người dùng:     {db.nguoidung.count_documents({})}")
    print(f"  💰 Ví:            {db.vi.count_documents({})}")
    print(f"  🎮 Trò chơi:      {db.game.count_documents({})}")
    print(f"  👥 Nhân vật:      {db.nhanvat.count_documents({})}")
    print(f"  🗡️ Vật phẩm:      {db.vatpham.count_documents({})}")
    print(f"  🖼️ NFT:           {db.nft.count_documents({})}")
    print(f"  📋 Hợp đồng thuê: {db.hopdong.count_documents({})}")
    print(f"  💳 Giao dịch:     {db.giaodich.count_documents({})}")
    print("=" * 60)
    print("✅ HOÀN TẤT TẠO DỮ LIỆU MẪU!")
    print("=" * 60)
    
    # In thông tin đăng nhập
    print("\n🔑 THÔNG TIN ĐĂNG NHẬP:")
    print("  Admin:  admin / 123456")
    print("  User:   thanh / 123456")
    print("  User:   alice / 123456")
    print("  User:   bob / 123456")
    print("  User:   tran / 123456")
    print("  User:   han / 123456")
    print("  User:   huy / 123456")


if __name__ == "__main__":
    seed_database()