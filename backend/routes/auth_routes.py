from flask import Blueprint, request, jsonify
from models.nguoidung_model import NguoiDung
from services.auth_service import AuthService
from models.wallet_model import Wallet

def auth_routes(app):
    
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        data = request.get_json() or {}
        required = ['ten_nguoi_dung', 'mat_khau', 'ho_ten', 'email']
        for field in required:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'message': f'Thiếu {field}'}), 400
        
        # 1. Tiến hành đăng ký tài khoản
        result = AuthService.register(
            ten_nguoi_dung=data['ten_nguoi_dung'].strip(),
            mat_khau=data['mat_khau'],
            ho_ten=data['ho_ten'].strip(),
            email=data['email'].strip(),
            so_dien_thoai=data.get('so_dien_thoai', '')
        )
        
        if result.get('success'):
            user_id = result.get('user_id') or (result.get('user', {}).get('id_nguoi_dung'))
            
            # 2. Tự động khởi tạo ví cho người dùng mới
            try:
                if user_id and hasattr(Wallet, 'create_wallet'):
                    wallet_address = Wallet.create_wallet(user_id)
                    result['wallet_address'] = wallet_address
            except Exception as e:
                print(f"[Warning] Không thể tạo ví tự động cho user {user_id}: {str(e)}")

            return jsonify(result), 201
            
        return jsonify(result), 400
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.get_json() or {}
        if 'ten_nguoi_dung' not in data or 'mat_khau' not in data:
            return jsonify({'success': False, 'message': 'Thiếu tên đăng nhập hoặc mật khẩu'}), 400
        
        result = AuthService.login(data['ten_nguoi_dung'], data['mat_khau'])
        
        if result.get('success'):
            user = result.get('user', {})
            user_id = user.get('id_nguoi_dung') or user.get('id') or user.get('ma_nguoi_dung')
            
            # 3. Đảm bảo người dùng cũ chưa có ví sẽ được tự động tạo ví khi đăng nhập
            if user_id:
                try:
                    user_wallet = Wallet.find_by_username(data['ten_nguoi_dung'])
                    if not user_wallet and hasattr(Wallet, 'create_wallet'):
                        Wallet.create_wallet(user_id)
                except Exception as e:
                    print(f"[Warning] Lỗi kiểm tra ví khi đăng nhập: {str(e)}")

            return jsonify(result), 200
            
        return jsonify(result), 401