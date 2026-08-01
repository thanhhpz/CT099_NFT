from flask import request, jsonify
from models.hopdong_model import HopDong
from models.vatpham_model import VatPham
from models.nft_model import NFT
from models.nguoidung_model import NguoiDung
from models.giaodich_model import GiaoDich
from models.wallet_model import Wallet
from models.nhanvat_model import NhanVat
from config import Config
from models.nhanvat_vatpham_model import NhanVatVatPham
import datetime
import jwt
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
        except:
            return jsonify({'success': False, 'message': 'Token không hợp lệ'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def rental_routes(app):
    
    # ============================================================
    # CHUẨN BỊ THANH TOÁN THUÊ NFT
    # Chỉ kiểm tra và tính tiền, chưa trừ tiền, chưa tạo hợp đồng
    # ============================================================
    @app.route('/api/rentals/prepare', methods=['POST'])
    @token_required
    def prepare_rental(current_user):
        data = request.get_json(silent=True) or {}

        # Hiện frontend đang gửi mã vật phẩm trong trường ma_bai_dang.
        # Tạm giữ cách này để không phá luồng cũ.
        ma_vat_pham = data.get('ma_bai_dang')

        if not ma_vat_pham:
            return jsonify({
                'success': False,
                'message': 'Thiếu ma_bai_dang'
            }), 400

        # --------------------------------------------------------
        # 1. Kiểm tra vật phẩm
        # --------------------------------------------------------
        item = VatPham.find_by_ma(ma_vat_pham)

        if not item:
            return jsonify({
                'success': False,
                'message': 'Vật phẩm không tồn tại'
            }), 404

        if item.get('trang_thai_thue') != 'còn trống':
            return jsonify({
                'success': False,
                'message': 'Vật phẩm đang được thuê'
            }), 400

        # --------------------------------------------------------
        # 2. Kiểm tra NFT gắn với vật phẩm
        # --------------------------------------------------------
        nfts = NFT.find_by_vat_pham(item['ma_vat_pham'])

        if not nfts:
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy NFT của vật phẩm'
            }), 404

        nft = nfts[0]

        if nft.get('trang_thai') != 'co_san':
            return jsonify({
                'success': False,
                'message': 'NFT hiện không sẵn sàng để thuê'
            }), 400

        # Không cho chủ sở hữu thuê chính NFT của mình.
        if nft.get('dia_chi_chu_so_huu') == current_user.dia_chi_vi:
            return jsonify({
                'success': False,
                'message': 'Bạn không thể thuê NFT của chính mình'
            }), 400

        # --------------------------------------------------------
        # 4. Tính thời gian thuê
        # --------------------------------------------------------
        don_vi = item.get('don_vi_thue', 'ngay')

        now = datetime.datetime.utcnow()

        if don_vi == 'gio':
            try:
                so_gio = int(data.get('so_gio', 0))
            except (TypeError, ValueError):
                so_gio = 0

            if so_gio <= 0:
                return jsonify({
                    'success': False,
                    'message': 'Số giờ thuê không hợp lệ'
                }), 400

            max_gio = item.get('thoi_gian_thue_toi_da', 1) * 24

            if so_gio > max_gio:
                return jsonify({
                    'success': False,
                    'message': (
                        f'Vượt quá thời gian thuê tối đa '
                        f'({max_gio} giờ)'
                    )
                }), 400

            so_ngay_thue = so_gio / 24
            tong_tien = item['gia_thue'] * so_ngay_thue
            thoi_gian_ket_thuc = now + datetime.timedelta(hours=so_gio)

            thoi_luong_hien_thi = f'{so_gio} giờ'

        else:
            try:
                so_ngay_thue = float(data.get('so_ngay_thue', 0))
            except (TypeError, ValueError):
                so_ngay_thue = 0

            if so_ngay_thue <= 0:
                return jsonify({
                    'success': False,
                    'message': 'Số ngày thuê không hợp lệ'
                }), 400

            if so_ngay_thue > item.get('thoi_gian_thue_toi_da', 1):
                return jsonify({
                    'success': False,
                    'message': (
                        'Vượt quá thời gian thuê tối đa '
                        f'({item["thoi_gian_thue_toi_da"]} ngày)'
                    )
                }), 400

            tong_tien = item['gia_thue'] * so_ngay_thue
            thoi_gian_ket_thuc = now + datetime.timedelta(
                days=so_ngay_thue
            )

            if don_vi == 'tuan':
                so_tuan = so_ngay_thue / 7
                thoi_luong_hien_thi = f'{so_tuan:g} tuần'
            else:
                thoi_luong_hien_thi = f'{so_ngay_thue:g} ngày'

        # --------------------------------------------------------
        # 5. Tính phí dịch vụ và tổng thanh toán
        # --------------------------------------------------------
        phi_dich_vu = (
            tong_tien
            * Config.PLATFORM_FEE_PERCENT
            / 100
        )

        tong_thanh_toan = tong_tien + phi_dich_vu

        # Làm tròn để tránh số thực kiểu 10.5000000001.
        tong_tien = round(tong_tien, 2)
        phi_dich_vu = round(phi_dich_vu, 2)
        tong_thanh_toan = round(tong_thanh_toan, 2)

        # --------------------------------------------------------
        # 6. Kiểm tra ví người thuê
        # --------------------------------------------------------
        wallet = Wallet.find_by_address(current_user.dia_chi_vi)

        if not wallet:
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy ví người thuê'
            }), 404

        so_du_hien_tai = round(float(wallet.get('so_du', 0)), 2)
        so_du_sau_thanh_toan = round(
            so_du_hien_tai - tong_thanh_toan,
            2
        )

        if so_du_hien_tai < tong_thanh_toan:
            return jsonify({
                'success': False,
                'message': (
                    f'Số dư không đủ. '
                    f'Cần {tong_thanh_toan} COINS'
                ),
                'pdúngchưaayment': {
                    'so_du_hien_tai': so_du_hien_tai,
                    'tong_thanh_toan': tong_thanh_toan,
                    'so_tien_con_thieu': round(
                        tong_thanh_toan - so_du_hien_tai,
                        2
                    )
                }
            }), 400

        # --------------------------------------------------------
        # 7. Trả thông tin cho giao diện thanh toán
        # --------------------------------------------------------
        return jsonify({
            'success': True,
            'message': 'Chuẩn bị thanh toán thành công',
            'payment': {
                'ma_vat_pham': item['ma_vat_pham'],
                'ma_nft': nft.get('ma_nft'),
                'ten_nft': nft.get(
                    'ten',
                    item.get('ten_vat_pham', 'NFT')
                ),
                'url_hinh_anh': nft.get('url_hinh_anh'),

                'don_vi': don_vi,
                'so_ngay_thue': so_ngay_thue,
                'so_gio': (
                    int(data.get('so_gio', 0))
                    if don_vi == 'gio'
                    else None
                ),
                'thoi_luong_hien_thi': thoi_luong_hien_thi,

                'thoi_gian_bat_dau': now.isoformat(),
                'thoi_gian_ket_thuc': (
                    thoi_gian_ket_thuc.isoformat()
                ),

                'gia_thue': round(
                    float(item.get('gia_thue', 0)),
                    2
                ),
                'tien_thue': tong_tien,
                'ty_le_phi_dich_vu': (
                    Config.PLATFORM_FEE_PERCENT
                ),
                'phi_dich_vu': phi_dich_vu,
                'tong_thanh_toan': tong_thanh_toan,

                'so_du_hien_tai': so_du_hien_tai,
                'so_du_sau_thanh_toan': (
                    so_du_sau_thanh_toan
                ),

                'dia_chi_nguoi_thue': wallet.get('dia_chi'),
                'dia_chi_chu_so_huu': nft.get(
                    'dia_chi_chu_so_huu'
                )
            }
        }), 200
    
    # ============================================================
    # TẠO HỢP ĐỒNG THUÊ (HỖ TRỢ THUÊ THEO GIỜ)
    # ============================================================
    @app.route('/api/rentals/create', methods=['POST'])
    # rental_routes.py - Phần create_rental đã sửa

    @token_required
    def create_rental(current_user):
        print(">>>>>>>>>>> CREATE RENTAL CALLED <<<<<<<<<<<", flush=True)
        data = request.get_json()
        required = ['ma_bai_dang']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'message': f'Thiếu {field}'}), 400
        
        item = VatPham.find_by_ma(data['ma_bai_dang'])
        if not item:
            return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
        
        if item['trang_thai_thue'] != 'còn trống':
            return jsonify({'success': False, 'message': 'Vật phẩm đang được thuê'}), 400
        
        don_vi = item.get('don_vi_thue', 'ngay')
        
        # Xác định thời gian thuê
        if don_vi == 'gio':
            so_gio = data.get('so_gio', 1)
            if so_gio <= 0:
                return jsonify({'success': False, 'message': 'Số giờ không hợp lệ'}), 400
            max_gio = item['thoi_gian_thue_toi_da'] * 24
            if so_gio > max_gio:
                return jsonify({'success': False, 'message': f'Vượt quá thời gian thuê tối đa ({max_gio} giờ)'}), 400
            
            tong_tien = item['gia_thue'] * (so_gio / 24)
            end_date = datetime.datetime.utcnow() + datetime.timedelta(hours=so_gio)
            so_ngay_thue = so_gio / 24
            
        else:  # 'ngay' hoặc 'tuan'
            so_ngay = data.get('so_ngay_thue', 1)
            if so_ngay <= 0:
                return jsonify({'success': False, 'message': 'Số ngày không hợp lệ'}), 400
            if so_ngay > item['thoi_gian_thue_toi_da']:
                return jsonify({'success': False, 'message': f'Vượt quá thời gian thuê tối đa ({item["thoi_gian_thue_toi_da"]} ngày)'}), 400
            
            tong_tien = item['gia_thue'] * so_ngay
            end_date = datetime.datetime.utcnow() + datetime.timedelta(days=so_ngay)
            so_ngay_thue = so_ngay
        
        # Tính phí dịch vụ
        phi_dich_vu = tong_tien * Config.PLATFORM_FEE_PERCENT / 100

        # Không còn tiền đặt cọc.
        tong_thanh_toan = tong_tien + phi_dich_vu
        
        wallet = Wallet.find_by_address(current_user.dia_chi_vi)
        if not wallet:
            return jsonify({'success': False, 'message': 'Không tìm thấy ví'}), 404
        
        print(
            "[DEBUG RENT]",
            {
                "file": __file__,
                "gia_thue": item.get("gia_thue"),
                "so_ngay_thue": so_ngay_thue,
                "tong_tien": tong_tien,
                "phi_dich_vu": phi_dich_vu,
                "tong_thanh_toan": tong_thanh_toan
            },
            flush=True
        )
        if wallet['so_du'] < tong_thanh_toan:
            return jsonify({'success': False, 'message': f'Số dư không đủ. Cần {tong_thanh_toan} COINS'}), 400
        
        start_date = datetime.datetime.utcnow()
        
        hopdong = HopDong(
            ma_bai_dang=data['ma_bai_dang'],
            ma_nguoi_thue=current_user.ma_nguoi_dung,
            thoi_gian_bat_dau=start_date,
            thoi_gian_ket_thuc=end_date,
            ma_nhan_vat=data.get('ma_nhan_vat')
        )
        hopdong.tong_tien = tong_tien
        hopdong.so_ngay_thue = so_ngay_thue
        hopdong.don_vi_thue = don_vi
        hopdong.phi_dich_vu = phi_dich_vu
        hopdong.save()
        
        # Trừ tiền từ ví người thuê
        Wallet.update_balance(wallet['dia_chi'], wallet['so_du'] - tong_thanh_toan)
        
        # Cộng tiền cho chủ sở hữu (nếu có NFT)
        nfts = NFT.find_by_vat_pham(item['ma_vat_pham'])
        if nfts:
            owner_wallet = Wallet.find_by_address(nfts[0]['dia_chi_chu_so_huu'])
            if owner_wallet:
                Wallet.update_balance(owner_wallet['dia_chi'], owner_wallet['so_du'] + tong_tien)
        
        # Cập nhật trạng thái vật phẩm
        VatPham.update_status(item['ma_vat_pham'], 'đang thuê')
        
        # Cập nhật trạng thái NFT
        if nfts:
            NFT.update_status(nfts[0]['ma_nft'], 'dang_thue')
        
        # Tạo giao dịch thanh toán
        giao_dich = GiaoDich(
            ma_hop_dong=hopdong.ma_hop_dong,
            loai_giao_dich='thanh_toan_thue',
            so_tien_giao_dich=tong_thanh_toan,
            hinh_thuc_thanh_toan='ví',
            ma_nguoi_dung=current_user.ma_nguoi_dung
        )
        giao_dich.save()
        
        # ✅ THÊM RETURN Ở ĐÂY
        return jsonify({
            'success': True,
            'message': f'Tạo hợp đồng thuê thành công!',
            'hop_dong': hopdong.to_dict(),
            'tong_thanh_toan': tong_thanh_toan
        }), 201
        

    
    # ============================================================
    # TRẢ NFT
    # ============================================================
    @app.route('/api/rentals/return/<ma_hop_dong>', methods=['POST'])
    @token_required
    def return_rental(current_user, ma_hop_dong):
        hopdong = HopDong.find_by_ma(ma_hop_dong)
        if not hopdong:
            return jsonify({'success': False, 'message': 'Hợp đồng không tồn tại'}), 404
        
        if hopdong['trang_thai_thue'] != 'dang_thue':
            return jsonify({'success': False, 'message': 'Hợp đồng không ở trạng thái đang thuê'}), 400
        
        if hopdong['ma_nguoi_thue'] != current_user.ma_nguoi_dung:
            return jsonify({'success': False, 'message': 'Bạn không phải người thuê'}), 403
        
        HopDong.update_status(ma_hop_dong, 'da_tra')
        
        item = VatPham.find_by_ma(hopdong['ma_bai_dang'])
        if item:
            VatPham.update_status(item['ma_vat_pham'], 'còn trống')
        
        nfts = NFT.find_by_vat_pham(item['ma_vat_pham']) if item else []
        if nfts:
            NFT.update_status(nfts[0]['ma_nft'], 'co_san') 
        
        return jsonify({'success': True, 'message': 'Đã trả vật phẩm thành công'}), 200
    
    # ============================================================
    # HỦY HỢP ĐỒNG TRƯỚC HẠN
    # ============================================================
    @app.route('/api/rentals/cancel/<ma_hop_dong>', methods=['POST'])
    @token_required
    def cancel_rental(current_user, ma_hop_dong):
        hopdong = HopDong.find_by_ma(ma_hop_dong)
        if not hopdong:
            return jsonify({'success': False, 'message': 'Hợp đồng không tồn tại'}), 404
        
        if hopdong['ma_nguoi_thue'] != current_user.ma_nguoi_dung:
            return jsonify({'success': False, 'message': 'Bạn không phải người thuê'}), 403
        
        if hopdong['trang_thai_thue'] != 'dang_thue':
            return jsonify({'success': False, 'message': 'Hợp đồng không ở trạng thái đang thuê'}), 400
        
        now = datetime.datetime.utcnow()  # SỬA: dùng utcnow() không timezone
        start = hopdong['thoi_gian_bat_dau']
        
        # Tính số ngày/giờ đã thuê
        don_vi = hopdong.get('don_vi_thue', 'ngay')
        if don_vi == 'gio':
            so_don_vi_da_thue = (now - start).total_seconds() / 3600
            if so_don_vi_da_thue < 1:
                so_don_vi_da_thue = 1
            so_don_vi_da_thue = int(so_don_vi_da_thue)
        else:
            so_don_vi_da_thue = (now - start).days + 1  # SỬA: now - start đã hoạt động
            if so_don_vi_da_thue < 1:
                so_don_vi_da_thue = 1
        
        item = VatPham.find_by_ma(hopdong['ma_bai_dang'])
        if not item:
            return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
        
        # Tính tiền hoàn lại
        tong_tien = hopdong['tong_tien']
        if don_vi == 'gio':
            gia_moi_don_vi = item['gia_thue'] / 24
            tong_tien_da_dung = gia_moi_don_vi * so_don_vi_da_thue
        else:
            tong_tien_da_dung = item['gia_thue'] * so_don_vi_da_thue
        
        if tong_tien_da_dung > tong_tien:
            tong_tien_da_dung = tong_tien
        
        tien_thua = tong_tien - tong_tien_da_dung
        if tien_thua < 0:
            tien_thua = 0
        
        # Chỉ hoàn phần tiền thuê chưa sử dụng.
        # Không còn hoàn tiền cọc.
        tien_hoan = tien_thua
        
        wallet = Wallet.find_by_address(current_user.dia_chi_vi)
        if wallet:
            Wallet.update_balance(wallet['dia_chi'], wallet['so_du'] + tien_hoan)
            
            nfts = NFT.find_by_vat_pham(item['ma_vat_pham'])
            if nfts:
                owner_wallet = Wallet.find_by_address(nfts[0]['dia_chi_chu_so_huu'])
                if owner_wallet:
                    Wallet.update_balance(
                        owner_wallet['dia_chi'],
                        owner_wallet['so_du'] - tien_hoan
                    )
        
        HopDong.update_status(ma_hop_dong, 'da_huy')
        VatPham.update_status(item['ma_vat_pham'], 'còn trống')
        
        nfts = NFT.find_by_vat_pham(item['ma_vat_pham'])
        if nfts:
            NFT.update_status(nfts[0]['ma_nft'], 'co_san')
        
        giao_dich = GiaoDich(
            ma_hop_dong=ma_hop_dong,
            loai_giao_dich='hoan_tien_thue',
            so_tien_giao_dich=tien_hoan,
            hinh_thuc_thanh_toan='ví',
            ma_nguoi_dung=current_user.ma_nguoi_dung
        )
        giao_dich.save()
        
        return jsonify({
            'success': True,
            'message': f'Đã hủy hợp đồng. Hoàn lại {tien_hoan} COINS',
            'tien_hoan': tien_hoan,
            'so_don_vi_da_dung': so_don_vi_da_thue
        }), 200
    
    # ============================================================
    # GIA HẠN HỢP ĐỒNG
    # ============================================================
    @app.route('/api/rentals/extend/<ma_hop_dong>', methods=['POST'])
    @token_required
    def extend_rental(current_user, ma_hop_dong):
        data = request.get_json()
        them_ngay = data.get('them_ngay', 0)
        
        if them_ngay <= 0:
            return jsonify({'success': False, 'message': 'Số ngày gia hạn không hợp lệ'}), 400
        
        hopdong = HopDong.find_by_ma(ma_hop_dong)
        if not hopdong:
            return jsonify({'success': False, 'message': 'Hợp đồng không tồn tại'}), 404
        
        if hopdong['ma_nguoi_thue'] != current_user.ma_nguoi_dung:
            return jsonify({'success': False, 'message': 'Bạn không phải người thuê'}), 403
        
        if hopdong['trang_thai_thue'] != 'dang_thue':
            return jsonify({'success': False, 'message': 'Hợp đồng không ở trạng thái đang thuê'}), 400
        
        item = VatPham.find_by_ma(hopdong['ma_bai_dang'])
        if not item:
            return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
        
        tong_ngay = (hopdong['thoi_gian_ket_thuc'] - hopdong['thoi_gian_bat_dau']).days + them_ngay
        if tong_ngay > item['thoi_gian_thue_toi_da']:
            return jsonify({'success': False, 'message': f'Vượt quá số ngày thuê tối đa ({item["thoi_gian_thue_toi_da"]} ngày)'}), 400
        
        tien_gia_han = round(
            item['gia_thue'] * them_ngay,
            2
        )

        phi_dich_vu = round(
            tien_gia_han
            * Config.PLATFORM_FEE_PERCENT
            / 100,
            2
        )

        tong_thanh_toan = round(
            tien_gia_han + phi_dich_vu,
            2
        )
        
        wallet = Wallet.find_by_address(current_user.dia_chi_vi)
        if not wallet:
            return jsonify({'success': False, 'message': 'Không tìm thấy ví'}), 404
        
        if wallet['so_du'] < tong_thanh_toan:
            return jsonify({
                'success': False,
                'message': (
                    f'Số dư không đủ. '
                    f'Cần {tong_thanh_toan} COINS'
                )
            }), 400
        
        Wallet.update_balance(
            wallet['dia_chi'],
            wallet['so_du'] - tong_thanh_toan
        )
        
        nfts = NFT.find_by_vat_pham(item['ma_vat_pham'])
        if nfts:
            owner_wallet = Wallet.find_by_address(nfts[0]['dia_chi_chu_so_huu'])
            if owner_wallet:
                Wallet.update_balance(owner_wallet['dia_chi'], owner_wallet['so_du'] + tien_gia_han)
        
        new_end = hopdong['thoi_gian_ket_thuc'] + datetime.timedelta(days=them_ngay)
        from database.connection import hopdong_collection
        hopdong_collection.update_one(
            {'ma_hop_dong': ma_hop_dong},
            {
                '$set': {
                    'thoi_gian_ket_thuc': new_end
                },
                '$inc': {
                    'tong_tien': tien_gia_han,
                    'phi_dich_vu': phi_dich_vu
                }
            }
        )
        
        giao_dich = GiaoDich(
            ma_hop_dong=ma_hop_dong,
            loai_giao_dich='gia_han',
            so_tien_giao_dich=tong_thanh_toan,
            hinh_thuc_thanh_toan='ví',
            ma_nguoi_dung=current_user.ma_nguoi_dung
        )
        giao_dich.save()
        
        return jsonify({
            'success': True,
            'message': f'Gia hạn thành công {them_ngay} ngày',
            'thoi_gian_ket_thuc_moi': new_end.isoformat(),
            'tien_gia_han': tien_gia_han,
            'phi_dich_vu': phi_dich_vu,
            'tong_thanh_toan': tong_thanh_toan
        }), 200
    
    # ============================================================
    # LẤY DANH SÁCH HỢP ĐỒNG CỦA USER
    # ============================================================
    @app.route('/api/rentals/user/<ma_nguoi_thue>', methods=['GET'])
    def get_user_rentals(ma_nguoi_thue):
        rentals = HopDong.find_by_nguoi_thue(ma_nguoi_thue)
        
        for rental in rentals:
            nguoi_thue = NguoiDung.find_by_ma(rental['ma_nguoi_thue'])
            if nguoi_thue:
                rental['ten_nguoi_thue'] = nguoi_thue.ten_nguoi_dung
            
            item = VatPham.find_by_ma(rental['ma_bai_dang'])
            if item:
                rental['ten_vat_pham'] = item['ten_vat_pham']
                rental['mo_ta_vat_pham'] = item['mo_ta']
                rental['gia_thue_vat_pham'] = item['gia_thue']
                
                nfts = NFT.find_by_vat_pham(item['ma_vat_pham'])
                if nfts:
                    nft = nfts[0]
                    rental['ma_nft'] = nft['ma_nft']
                    rental['ten_nft'] = nft['ten']
                    rental['gia_thue_nft'] = nft['gia_thue']
                    rental['trang_thai_nft'] = nft['trang_thai']
                    
                    owner_wallet = Wallet.find_by_address(nft['dia_chi_chu_so_huu'])
                    if owner_wallet:
                        rental['ten_chu_so_huu_nft'] = owner_wallet.get('ten_nguoi_dung', 'Không rõ')
                    else:
                        rental['ten_chu_so_huu_nft'] = 'Không rõ'
        
        return jsonify({'success': True, 'rentals': rentals}), 200
    
    # ============================================================
    # CHI TIẾT HỢP ĐỒNG
    # ============================================================
    @app.route('/api/rentals/<ma_hop_dong>/detail', methods=['GET'])
    @token_required
    def get_rental_detail(current_user, ma_hop_dong):
        hopdong = HopDong.find_by_ma(ma_hop_dong)
        if not hopdong:
            return jsonify({'success': False, 'message': 'Hợp đồng không tồn tại'}), 404
        
        item = VatPham.find_by_ma(hopdong['ma_bai_dang'])
        
        nfts = []
        ten_chu_so_huu = None
        if item:
            nfts = NFT.find_by_vat_pham(item['ma_vat_pham'])
            if nfts:
                owner_wallet = Wallet.find_by_address(nfts[0]['dia_chi_chu_so_huu'])
                if owner_wallet:
                    ten_chu_so_huu = owner_wallet.get('ten_nguoi_dung', 'Không rõ')
        
        nguoi_thue = NguoiDung.find_by_ma(hopdong['ma_nguoi_thue'])
        
        nhan_vat = None
        if hopdong.get('ma_nhan_vat'):
            nhan_vat = NhanVat.find_by_ma(hopdong['ma_nhan_vat'])
        
        giao_dichs = GiaoDich.find_by_hop_dong(ma_hop_dong)
        
        vat_pham_data = None
        if item:
            vat_pham_data = {
                'ten': item.get('ten_vat_pham', 'Không rõ'),
                'mo_ta': item.get('mo_ta', 'Không có mô tả'),
                'gia_thue': item.get('gia_thue', 0),
                'loai': item.get('loai', 'Không rõ'),
                'trang_thai': item.get(
                    'trang_thai_thue',
                    'Không rõ'
                )
            }
        
        return jsonify({
            'success': True,
            'hop_dong': hopdong,
            'vat_pham': vat_pham_data,
            'nft': nfts[0] if nfts else None,
            'ten_chu_so_huu': ten_chu_so_huu,
            'nguoi_thue': nguoi_thue.to_dict() if nguoi_thue else None,
            'nhan_vat': nhan_vat if nhan_vat else None,
            'giao_dich': giao_dichs
        }), 200
    
    # ============================================================
    # ĐỀ XUẤT NHÂN VẬT PHÙ HỢP
    # ============================================================
    @app.route(
        '/api/rentals/suggest-characters/<ma_vat_pham>',
        methods=['GET']
    )
    def suggest_characters(ma_vat_pham):
        item = VatPham.find_by_ma(ma_vat_pham)

        if not item:
            return jsonify({
                'success': False,
                'message': 'Vật phẩm không tồn tại'
            }), 404

        relations = NhanVatVatPham.find_by_vat_pham(
            ma_vat_pham
        )

        characters = []

        for relation in relations:
            character = NhanVat.find_by_ma(
                relation['ma_nhan_vat']
            )

            if character:
                characters.append(character)

        return jsonify({
            'success': True,
            'suggested': characters,
            'message': (
                f'Có {len(characters)} nhân vật phù hợp'
            )
        }), 200
    