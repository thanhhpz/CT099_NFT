from flask import request, jsonify
from models.wallet_model import Wallet
from models.nguoidung_model import NguoiDung
from models.hopdong_model import HopDong
from models.giaodich_model import GiaoDich
from models.vatpham_model import VatPham
import hashlib
import datetime
import uuid
import jwt
from config import Config
from functools import wraps

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'Vui lòng đăng nhập'}), 401
        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            current_user = NguoiDung.find_by_ten_nguoi_dung(data.get('ten_nguoi_dung'))
            if not current_user:
                return jsonify({'success': False, 'message': 'Người dùng không tồn tại'}), 401
        except Exception:
            return jsonify({'success': False, 'message': 'Token không hợp lệ'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def wallet_routes(app):
    
    # ============================================================
    # TẠO VÍ
    # ============================================================
    @app.route('/api/wallet/create', methods=['POST'])
    @token_required
    def create_wallet(current_user):
        if current_user.dia_chi_vi:
            return jsonify({'success': False, 'message': 'Đã có ví'}), 400
        
        address = hashlib.sha256(f"{current_user.ten_nguoi_dung}{datetime.datetime.now()}".encode()).hexdigest()[:40]
        
        wallet = Wallet(
            dia_chi=address,
            ten_nguoi_dung=current_user.ten_nguoi_dung,
            so_du=0,
            private_key='',
            public_key=''
        )
        wallet.save()
        
        from database.connection import nguoidung_collection
        nguoidung_collection.update_one(
            {'ma_nguoi_dung': current_user.ma_nguoi_dung},
            {'$set': {'dia_chi_vi': address}}
        )
        
        return jsonify({'success': True, 'wallet': wallet.to_dict()}), 201
    
    # ============================================================
    # LẤY THÔNG TIN VÍ THEO TÊN NGƯỜI DÙNG
    # ============================================================
    @app.route('/api/wallet/<ten_nguoi_dung>', methods=['GET'])
    def get_wallet(ten_nguoi_dung):
        wallet = Wallet.find_by_username(ten_nguoi_dung)
        if not wallet:
            return jsonify({'success': False, 'message': 'Ví không tồn tại'}), 404
        return jsonify({'success': True, 'wallet': wallet}), 200

    # ============================================================
    # LẤY THÔNG TIN VÍ THEO MÃ NGƯỜI DÙNG (USER ID) / TỰ ĐỘNG KHỞI TẠO NẾU THIẾU
    # ============================================================
    @app.route('/api/wallet/user/<ma_nguoi_dung>', methods=['GET'])
    def get_wallet_by_user_id(ma_nguoi_dung):
        from database.connection import nguoidung_collection
        
        user = nguoidung_collection.find_one({'ma_nguoi_dung': ma_nguoi_dung})
        if not user:
            return jsonify({'success': False, 'message': 'Người dùng không tồn tại'}), 404

        ten_nguoi_dung = user.get('ten_nguoi_dung')
        wallet = Wallet.find_by_username(ten_nguoi_dung)

        # Nếu người dùng chưa có ví, tự động tạo mới
        if not wallet:
            address = hashlib.sha256(f"{ten_nguoi_dung}{datetime.datetime.now()}".encode()).hexdigest()[:40]
            new_wallet = Wallet(
                dia_chi=address,
                ten_nguoi_dung=ten_nguoi_dung,
                so_du=0,
                private_key='',
                public_key=''
            )
            new_wallet.save()
            
            nguoidung_collection.update_one(
                {'ma_nguoi_dung': ma_nguoi_dung},
                {'$set': {'dia_chi_vi': address}}
            )
            wallet = new_wallet.to_dict()

        return jsonify({'success': True, 'wallet': wallet}), 200

    # ============================================================
    # NẠP TIỀN VÀO VÍ
    # ============================================================
    @app.route('/api/wallet/deposit', methods=['POST'])
    @token_required
    def deposit(current_user):
        """Nạp tiền vào ví"""
        data = request.get_json() or {}
        amount = data.get('so_tien', 0)
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Số tiền không hợp lệ'}), 400
        
        # Lấy ví của người dùng hiện tại
        wallet = Wallet.find_by_username(current_user.ten_nguoi_dung)
        if not wallet:
            return jsonify({'success': False, 'message': 'Ví không tồn tại'}), 404
        
        # Cập nhật số dư
        new_balance = wallet['so_du'] + amount
        Wallet.update_balance(wallet['dia_chi'], new_balance)
        
        # Tạo giao dịch với ma_nguoi_dung
        from database.connection import giaodich_collection
        
        giao_dich = {
            'ma_giao_dich': str(uuid.uuid4()),
            'ma_hop_dong': None,
            'loai_giao_dich': 'nap_tien',
            'so_tien_giao_dich': amount,
            'hinh_thuc_thanh_toan': 'ví',
            'ma_nguoi_dung': current_user.ma_nguoi_dung,
            'ten_nguoi_dung': current_user.ten_nguoi_dung,
            'thoi_gian_thanh_toan': datetime.datetime.now(datetime.timezone.utc),
            'created_at': datetime.datetime.now(datetime.timezone.utc),
            'ghi_chu': f'Nạp {amount} COINS vào ví'
        }
        giaodich_collection.insert_one(giao_dich)
        
        return jsonify({
            'success': True,
            'message': f'Nạp thành công {amount} COINS',
            'new_balance': new_balance
        }), 200
    
    # ============================================================
    # LỊCH SỬ GIAO DỊCH
    # ============================================================
    @app.route('/api/wallet/<ten_nguoi_dung>/transactions', methods=['GET'])
    def get_wallet_transactions(ten_nguoi_dung):
        """Lấy lịch sử giao dịch của người dùng (bao gồm nạp tiền)"""
        user = NguoiDung.find_by_ten_nguoi_dung(ten_nguoi_dung)
        if not user:
            return jsonify({'success': False, 'message': 'Người dùng không tồn tại'}), 404
        
        # 1. Lấy giao dịch từ hợp đồng thuê
        rentals = HopDong.find_by_nguoi_thue(user.ma_nguoi_dung)
        
        transactions = []
        for rental in rentals:
            gds = GiaoDich.find_by_hop_dong(rental['ma_hop_dong'])
            item = VatPham.find_by_ma(rental['ma_bai_dang'])
            for g in gds:
                g['ten_vat_pham'] = item['ten_vat_pham'] if item else 'Không rõ'
                g['trang_thai_hop_dong'] = rental['trang_thai_thue']
                g['loai_hien_thi'] = g['loai_giao_dich']
                transactions.append(g)
        
        # 2. Lấy giao dịch NẠP TIỀN
        from database.connection import giaodich_collection
        deposit_transactions = list(giaodich_collection.find({
            'ten_nguoi_dung': ten_nguoi_dung,
            'loai_giao_dich': 'nap_tien'
        }, {'_id': 0}))
        
        for dt in deposit_transactions:
            dt['ten_vat_pham'] = 'Nạp tiền'
            dt['trang_thai_hop_dong'] = 'hoan_thanh'
            dt['loai_hien_thi'] = 'nap_tien'
            transactions.append(dt)
        
        # Sắp xếp theo thời gian giảm dần
        transactions.sort(key=lambda x: x.get('thoi_gian_thanh_toan', datetime.datetime.min), reverse=True)
        
        return jsonify({'success': True, 'transactions': transactions}), 200