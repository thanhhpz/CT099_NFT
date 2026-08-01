from flask import request, jsonify

from database.connection import nguoidung_collection
from models.wallet_model import Wallet
from services.auth_service import AuthService

print(">>> AUTH ROUTES ĐANG ĐƯỢC LOAD TỪ:", __file__)


def auth_routes(app):

    @app.route('/api/auth/register', methods=['POST'])
    def register():
        print(">>> ĐÃ VÀO HÀM REGISTER", flush=True)
        data = request.get_json() or {}

        required_fields = [
            'ten_nguoi_dung',
            'mat_khau',
            'ho_ten',
            'email'
        ]

        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Thiếu {field}'
                }), 400

        ten_nguoi_dung = data['ten_nguoi_dung'].strip()

        result = AuthService.register(
            ten_nguoi_dung=ten_nguoi_dung,
            mat_khau=data['mat_khau'],
            ho_ten=data['ho_ten'].strip(),
            email=data['email'].strip(),
            so_dien_thoai=data.get('so_dien_thoai', '').strip()
        )

        if not result.get('success'):
            return jsonify(result), 400

        # Tìm lại người dùng vừa được lưu trong MongoDB.
        # Không phụ thuộc vào cấu trúc trả về của AuthService.register().
        created_user = nguoidung_collection.find_one({
            'ten_nguoi_dung': ten_nguoi_dung
        })

        if not created_user:
            return jsonify({
                'success': False,
                'message': (
                    'Tài khoản đã được tạo nhưng không tìm thấy '
                    'dữ liệu người dùng trong MongoDB'
                )
            }), 500

        ma_nguoi_dung = created_user.get('ma_nguoi_dung')

        try:
            print(
                f">>> ĐANG TẠO VÍ: "
                f"ten_nguoi_dung={ten_nguoi_dung}, "
                f"ma_nguoi_dung={ma_nguoi_dung}",
                flush=True
            )

            wallet = Wallet.find_by_username(ten_nguoi_dung)

            if not wallet:
                wallet = Wallet.create_wallet(
                    ten_nguoi_dung=ten_nguoi_dung,
                    ma_nguoi_dung=ma_nguoi_dung,
                    initial_balance=0
                )

            print(
                f"[DEBUG REGISTER] wallet_address="
                f"{wallet.get('dia_chi')}"
            )

            # Chỉ trả thông tin an toàn về frontend.
            # Tuyệt đối không trả private_key.
            result['wallet'] = {
                'dia_chi': wallet.get('dia_chi'),
                'public_key': wallet.get('public_key'),
                'so_du': wallet.get('so_du', 0)
            }

            result['dia_chi_vi'] = wallet.get('dia_chi')

            # Nếu AuthService có trả user thì cập nhật thêm địa chỉ ví.
            if isinstance(result.get('user'), dict):
                result['user']['dia_chi_vi'] = wallet.get('dia_chi')

        except Exception as error:
            print(
                f"[Warning] Không thể tạo ví tự động "
                f"cho user {ma_nguoi_dung}: {str(error)}"
            )

            # Tài khoản đã được tạo nên vẫn trả 201,
            # nhưng báo rõ ví chưa tạo được.
            result['wallet_created'] = False
            result['wallet_error'] = str(error)

        return jsonify(result), 201

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.get_json() or {}

        if not data.get('ten_nguoi_dung') or not data.get('mat_khau'):
            return jsonify({
                'success': False,
                'message': 'Thiếu tên đăng nhập hoặc mật khẩu'
            }), 400

        ten_nguoi_dung = data['ten_nguoi_dung'].strip()

        result = AuthService.login(
            ten_nguoi_dung,
            data['mat_khau']
        )

        if not result.get('success'):
            return jsonify(result), 401

        current_user = nguoidung_collection.find_one({
            'ten_nguoi_dung': ten_nguoi_dung
        })

        if not current_user:
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy dữ liệu người dùng'
            }), 404

        ma_nguoi_dung = current_user.get('ma_nguoi_dung')

        try:
            wallet = Wallet.find_by_username(ten_nguoi_dung)

            if not wallet:
                print(
                    f"[DEBUG LOGIN] "
                    f"ten_nguoi_dung={ten_nguoi_dung}, "
                    f"ma_nguoi_dung={ma_nguoi_dung}"
                )

                wallet = Wallet.create_wallet(
                    ten_nguoi_dung=ten_nguoi_dung,
                    ma_nguoi_dung=ma_nguoi_dung,
                    initial_balance=0
                )

                print(
                    f"[DEBUG LOGIN] wallet_address="
                    f"{wallet.get('dia_chi')}"
                )

            if isinstance(result.get('user'), dict):
                result['user']['dia_chi_vi'] = wallet.get('dia_chi')
            else:
                result['dia_chi_vi'] = wallet.get('dia_chi')

            result['wallet'] = {
                'dia_chi': wallet.get('dia_chi'),
                'public_key': wallet.get('public_key'),
                'so_du': wallet.get('so_du', 0)
            }

        except Exception as error:
            print(
                f"[Warning] Lỗi kiểm tra ví khi đăng nhập: "
                f"{str(error)}"
            )

            result['wallet_created'] = False
            result['wallet_error'] = str(error)

        return jsonify(result), 200
    