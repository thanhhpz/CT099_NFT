from flask import request, jsonify
from models.nft_model import NFT
from models.vatpham_model import VatPham
from models.nguoidung_model import NguoiDung
from models.wallet_model import Wallet
from models.hopdong_model import HopDong
from models.giaodich_model import GiaoDich
from models.game_model import Game
import datetime
import jwt
from config import Config
from functools import wraps
from database.connection import hopdong_collection, nft_collection, vatpham_collection

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

def nft_routes(app):
    
    @app.route('/api/nfts/mint', methods=['POST'])
    @token_required
    def mint_nft(current_user):
        data = request.get_json()
        required = ['ten', 'gia_thue', 'ma_vat_pham']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'message': f'Thiếu {field}'}), 400
        
        item = VatPham.find_by_ma(data['ma_vat_pham'])
        if not item:
            return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
        
        existing = NFT.find_by_vat_pham(data['ma_vat_pham'])
        if existing:
            return jsonify({'success': False, 'message': 'Vật phẩm này đã có NFT'}), 400
        
        dia_chi_chu_so_huu = data.get('dia_chi_chu_so_huu')
        if not dia_chi_chu_so_huu:
            return jsonify({'success': False, 'message': 'Thiếu địa chỉ ví chủ sở hữu'}), 400
        
        nft = NFT(
            ten=data['ten'],
            mo_ta=data.get('mo_ta', item['mo_ta']),
            dia_chi_chu_so_huu=dia_chi_chu_so_huu,
            gia_thue=data['gia_thue'],
            ma_vat_pham=data['ma_vat_pham'],
            url_hinh_anh=data.get('url_hinh_anh')
        )
        nft.save()
        
        return jsonify({'success': True, 'nft': nft.to_dict()}), 201
    
    @app.route('/api/nfts', methods=['GET'])
    def get_nfts():
        """Lấy danh sách tất cả NFT kèm thông tin người thuê"""
        try:
            nfts = NFT.find_all()
            
            for nft in nfts:
                # Lấy tên chủ sở hữu từ ví
                wallet = Wallet.find_by_address(nft['dia_chi_chu_so_huu'])
                if wallet:
                    nft['ten_chu_so_huu'] = wallet.get('ten_nguoi_dung', 'Không rõ')
                else:
                    nft['ten_chu_so_huu'] = 'Không rõ'
                
                # Lấy tên vật phẩm gốc
                item = VatPham.find_by_ma(nft.get('ma_vat_pham'))
                if item:
                    nft['ten_vat_pham'] = item.get('ten_vat_pham', 'Không rõ')
                    nft['ma_bai_dang'] = item.get('ma_bai_dang')
                else:
                    nft['ten_vat_pham'] = 'Không rõ'
                    nft['ma_bai_dang'] = None
                
                # Lấy thông tin người thuê nếu đang thuê
                nft['nguoi_thue'] = None
                if nft.get('trang_thai') == 'dang_thue':
                    hopdong = None
                    
                    # Cách 1: Tìm qua ma_bai_dang
                    if item and item.get('ma_bai_dang'):
                        hopdong = hopdong_collection.find_one({
                            'ma_bai_dang': item.get('ma_bai_dang'),
                            'trang_thai_thue': 'dang_thue'
                        })
                    
                    # Cách 2: Nếu không tìm thấy, tìm qua ma_vat_pham
                    if not hopdong and nft.get('ma_vat_pham'):
                        hopdong = hopdong_collection.find_one({
                            'ma_bai_dang': nft.get('ma_vat_pham'),
                            'trang_thai_thue': 'dang_thue'
                        })
                    
                    if hopdong:
                        nguoi_thue = NguoiDung.find_by_ma(hopdong.get('ma_nguoi_thue'))
                        if nguoi_thue:
                            nft['nguoi_thue'] = nguoi_thue.ten_nguoi_dung
                        else:
                            nft['nguoi_thue'] = 'Không rõ'
                    else:
                        nft['nguoi_thue'] = 'Không rõ'
            
            return jsonify({'success': True, 'nfts': nfts}), 200
            
        except Exception as e:
            print(f"❌ Lỗi get_nfts: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # ============================================================
    # THU HỒI NFT (ADMIN + CHỦ SỞ HỮU)
    # ============================================================
    @app.route('/api/nfts/<ma_nft>/revoke', methods=['POST'])
    @token_required
    def revoke_nft(current_user, ma_nft):
        """
        Thu hồi NFT đang được thuê (Admin hoặc chủ sở hữu)
        """
        try:
            # 1. Kiểm tra NFT tồn tại
            nft = NFT.find_by_ma(ma_nft)
            if not nft:
                return jsonify({'success': False, 'message': 'NFT không tồn tại'}), 404
            
            # 2. Kiểm tra NFT có đang được thuê không
            if nft.get('trang_thai') != 'dang_thue':
                return jsonify({'success': False, 'message': 'NFT không ở trạng thái đang thuê'}), 400
            
            # 3. Kiểm tra quyền: Admin hoặc chủ sở hữu
            is_admin = current_user.vai_tro == 'quan_tri'
            is_owner = nft['dia_chi_chu_so_huu'] == current_user.dia_chi_vi
            
            if not is_admin and not is_owner:
                return jsonify({'success': False, 'message': 'Bạn không có quyền thu hồi NFT này'}), 403
            
            # 4. Lấy vật phẩm từ NFT
            item = VatPham.find_by_ma(nft.get('ma_vat_pham'))
            if not item:
                return jsonify({'success': False, 'message': 'Không tìm thấy vật phẩm'}), 404
            
            # 5. Tìm hợp đồng đang thuê
            hopdong = hopdong_collection.find_one({
                'ma_bai_dang': item.get('ma_bai_dang'),
                'trang_thai_thue': 'dang_thue'
            })
            
            if not hopdong:
                hopdong = hopdong_collection.find_one({
                    'ma_bai_dang': nft.get('ma_vat_pham'),
                    'trang_thai_thue': 'dang_thue'
                })
            
            if not hopdong:
                all_rentals = list(hopdong_collection.find({'trang_thai_thue': 'dang_thue'}))
                for rental in all_rentals:
                    if rental.get('ma_bai_dang') == nft.get('ma_vat_pham'):
                        hopdong = rental
                        break
                    if item and rental.get('ma_bai_dang') == item.get('ma_bai_dang'):
                        hopdong = rental
                        break
            
            if not hopdong:
                return jsonify({'success': False, 'message': 'Không tìm thấy hợp đồng đang thuê'}), 404
            
            # 6. Tính tiền hoàn lại
            now = datetime.datetime.utcnow()
            start = hopdong.get('thoi_gian_bat_dau')
            
            so_ngay_da_thue = (now - start).days + 1
            if so_ngay_da_thue < 1:
                so_ngay_da_thue = 1
            
            tong_tien = hopdong.get('tong_tien', 0)
            tien_coc = hopdong.get('tien_coc', 0)
            gia_thue_ngay = nft.get('gia_thue', 0)
            
            tien_da_dung = gia_thue_ngay * so_ngay_da_thue
            if tien_da_dung > tong_tien:
                tien_da_dung = tong_tien
            
            tien_thua = tong_tien - tien_da_dung
            if tien_thua < 0:
                tien_thua = 0
            
            tien_hoan = tien_thua + tien_coc
            
            # 7. Hoàn tiền cho người thuê
            nguoi_thue = NguoiDung.find_by_ma(hopdong.get('ma_nguoi_thue'))
            ten_nguoi_thue = nguoi_thue.ten_nguoi_dung if nguoi_thue else 'Không rõ'
            
            if nguoi_thue and nguoi_thue.dia_chi_vi:
                wallet = Wallet.find_by_address(nguoi_thue.dia_chi_vi)
                if wallet:
                    Wallet.update_balance(wallet['dia_chi'], wallet['so_du'] + tien_hoan)
            
            # 8. Cập nhật trạng thái
            HopDong.update_status(hopdong.get('ma_hop_dong'), 'da_huy')
            NFT.update_status(ma_nft, 'co_san')
            VatPham.update_status(item['ma_vat_pham'], 'còn trống')
            
            # 9. Tạo giao dịch hoàn tiền
            giao_dich = GiaoDich(
                ma_hop_dong=hopdong.get('ma_hop_dong'),
                loai_giao_dich='hoan_tien_coc',
                so_tien_giao_dich=tien_hoan,
                hinh_thuc_thanh_toan='vi',
                ma_nguoi_dung=nguoi_thue.ma_nguoi_dung if nguoi_thue else None
            )
            giao_dich.save()
            
            return jsonify({
                'success': True,
                'message': f'Đã thu hồi NFT thành công! Hoàn lại {tien_hoan} COINS cho {ten_nguoi_thue}',
                'tien_hoan': tien_hoan,
                'so_ngay_da_thue': so_ngay_da_thue,
                'nguoi_thue': ten_nguoi_thue
            }), 200
            
        except Exception as e:
            print(f"❌ Lỗi revoke_nft: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/nfts/available', methods=['GET'])
    def get_available_nfts():
        nfts = NFT.find_available()

        for nft in nfts:
            # Lấy tên chủ sở hữu
            wallet = Wallet.find_by_address(
                nft['dia_chi_chu_so_huu']
            )

            nft['ten_chu_so_huu'] = (
                wallet.get('ten_nguoi_dung', 'Không rõ')
                if wallet
                else 'Không rõ'
            )

            # Lấy vật phẩm gốc của NFT
            item = VatPham.find_by_ma(
                nft.get('ma_vat_pham')
            )

            if item:
                nft['ten_vat_pham'] = item.get(
                    'ten_vat_pham',
                    'Không rõ'
                )

                nft['ma_game'] = item.get('ma_game')

                # Lấy tên game từ database
                game = Game.find_by_ma(
                    item.get('ma_game')
                )

                nft['ten_game'] = (
                    game.get('ten_game', 'Không rõ trò chơi')
                    if game
                    else 'Không rõ trò chơi'
                )
            else:
                nft['ten_vat_pham'] = 'Không rõ'
                nft['ma_game'] = None
                nft['ten_game'] = 'Không rõ trò chơi'

            nft['nguoi_thue'] = None

        return jsonify({
            'success': True,
            'nfts': nfts
        }), 200
    
    @app.route('/api/nfts/owner/<dia_chi_vi>', methods=['GET'])
    def get_nfts_by_owner(dia_chi_vi):
        nfts = NFT.find_by_owner(dia_chi_vi)
        for nft in nfts:
            wallet = Wallet.find_by_address(nft['dia_chi_chu_so_huu'])
            nft['ten_chu_so_huu'] = wallet.get('ten_nguoi_dung', 'Không rõ') if wallet else 'Không rõ'
            item = VatPham.find_by_ma(nft.get('ma_vat_pham'))
            nft['ten_vat_pham'] = item.get('ten_vat_pham', 'Không rõ') if item else 'Không rõ'
            nft['nguoi_thue'] = None
        return jsonify({'success': True, 'nfts': nfts}), 200
    
    @app.route('/api/nfts/<ma_nft>', methods=['GET'])
    def get_nft(ma_nft):
        nft = NFT.find_by_ma(ma_nft)
        if not nft:
            return jsonify({'success': False, 'message': 'NFT không tồn tại'}), 404
        wallet = Wallet.find_by_address(nft['dia_chi_chu_so_huu'])
        nft['ten_chu_so_huu'] = wallet.get('ten_nguoi_dung', 'Không rõ') if wallet else 'Không rõ'
        item = VatPham.find_by_ma(nft.get('ma_vat_pham'))
        nft['ten_vat_pham'] = item.get('ten_vat_pham', 'Không rõ') if item else 'Không rõ'
        nft['nguoi_thue'] = None
        if nft.get('trang_thai') == 'dang_thue' and item:
            hopdong = hopdong_collection.find_one({
                'ma_bai_dang': item.get('ma_bai_dang'),
                'trang_thai_thue': 'dang_thue'
            })
            if hopdong:
                nguoi_thue = NguoiDung.find_by_ma(hopdong.get('ma_nguoi_thue'))
                if nguoi_thue:
                    nft['nguoi_thue'] = nguoi_thue.ten_nguoi_dung
                else:
                    nft['nguoi_thue'] = 'Không rõ'
        return jsonify({'success': True, 'nft': nft}), 200
    
    @app.route('/api/nfts/<ma_nft>/history', methods=['GET'])
    def get_nft_history(ma_nft):
        nft = NFT.find_by_ma(ma_nft)
        if not nft:
            return jsonify({'success': False, 'message': 'NFT không tồn tại'}), 404
        
        item = VatPham.find_by_ma(nft['ma_vat_pham'])
        if not item:
            return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
        
        rentals = HopDong.find_all()
        history = []
        
        for rental in rentals:
            if rental['ma_bai_dang'] == item['ma_bai_dang']:
                nguoi_thue = NguoiDung.find_by_ma(rental['ma_nguoi_thue'])
                history.append({
                    'ma_hop_dong': rental['ma_hop_dong'],
                    'nguoi_thue': nguoi_thue.ten_nguoi_dung if nguoi_thue else 'Không rõ',
                    'thoi_gian_bat_dau': rental['thoi_gian_bat_dau'],
                    'thoi_gian_ket_thuc': rental['thoi_gian_ket_thuc'],
                    'tong_tien': rental.get('tong_tien', 0),
                    'trang_thai': rental['trang_thai_thue']
                })
        
        history.sort(key=lambda x: x['thoi_gian_bat_dau'], reverse=True)
        
        return jsonify({
            'success': True,
            'nft': {
                'ma_nft': nft['ma_nft'],
                'ten': nft['ten']
            },
            'history': history
        }), 200
    
    @app.route('/api/nfts/<ma_nft>/status', methods=['PUT'])
    @token_required
    def update_nft_status(current_user, ma_nft):
        data = request.get_json()
        status = data.get('trang_thai')
        
        if status not in ['co_san', 'dang_thue', 'tam_ngung']:
            return jsonify({'success': False, 'message': 'Trạng thái không hợp lệ'}), 400
        
        nft = NFT.find_by_ma(ma_nft)
        if not nft:
            return jsonify({'success': False, 'message': 'NFT không tồn tại'}), 404
        
        if nft['dia_chi_chu_so_huu'] != current_user.dia_chi_vi:
            return jsonify({'success': False, 'message': 'Bạn không phải chủ sở hữu'}), 403
        
        if nft['trang_thai'] == 'dang_thue':
            return jsonify({'success': False, 'message': 'NFT đang được thuê, không thể thay đổi trạng thái'}), 400
        
        NFT.update_status(ma_nft, status)
        return jsonify({'success': True, 'message': f'Đã cập nhật trạng thái thành {status}'}), 200
    
    @app.route('/api/nfts/purchase', methods=['POST'])
    @token_required
    def purchase_nft(current_user):
        data = request.get_json()
        ma_vat_pham = data.get('ma_vat_pham')
        
        if not ma_vat_pham:
            return jsonify({'success': False, 'message': 'Thiếu mã vật phẩm'}), 400
        
        item = VatPham.find_by_ma(ma_vat_pham)
        if not item:
            return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
        
        if item['trang_thai_thue'] != 'còn trống':
            return jsonify({'success': False, 'message': 'Vật phẩm đang được thuê, không thể mua NFT'}), 400
        
        existing_nft = NFT.find_by_vat_pham(ma_vat_pham)
        if existing_nft:
            return jsonify({'success': False, 'message': 'Vật phẩm này đã có NFT'}), 400
        
        gia_mua = item['gia_thue'] * 10
        
        wallet = Wallet.find_by_address(current_user.dia_chi_vi)
        if not wallet:
            return jsonify({'success': False, 'message': 'Không tìm thấy ví'}), 404
        
        if wallet['so_du'] < gia_mua:
            return jsonify({'success': False, 'message': f'Số dư không đủ. Cần {gia_mua} COINS'}), 400
        
        Wallet.update_balance(wallet['dia_chi'], wallet['so_du'] - gia_mua)
        
        nft = NFT(
            ten=item['ten_vat_pham'],
            mo_ta=item['mo_ta'],
            dia_chi_chu_so_huu=wallet['dia_chi'],
            gia_thue=item['gia_thue'],
            ma_vat_pham=ma_vat_pham
        )
        nft.save()
        
        return jsonify({
            'success': True,
            'message': f'Mua NFT thành công! Đã trừ {gia_mua} COINS.',
            'nft': nft.to_dict()
        }), 201
    
    @app.route('/api/nfts/<ma_nft>/list-for-rent', methods=['POST'])
    @token_required
    def list_nft_for_rent(current_user, ma_nft):
        data = request.get_json()
        gia_thue = data.get('gia_thue')
        
        if not gia_thue or gia_thue <= 0:
            return jsonify({'success': False, 'message': 'Giá thuê không hợp lệ'}), 400
        
        nft = NFT.find_by_ma(ma_nft)
        if not nft:
            return jsonify({'success': False, 'message': 'NFT không tồn tại'}), 404
        
        if nft['dia_chi_chu_so_huu'] != current_user.dia_chi_vi:
            return jsonify({'success': False, 'message': 'Bạn không phải chủ sở hữu'}), 403
        
        if nft['trang_thai'] == 'dang_thue':
            return jsonify({'success': False, 'message': 'NFT đang được thuê, không thể cho thuê lại'}), 400
        
        nft_collection.update_one(
            {'ma_nft': ma_nft},
            {'$set': {
                'gia_thue': gia_thue,
                'trang_thai': 'co_san'
            }}
        )
        
        return jsonify({
            'success': True,
            'message': f'Đã đăng NFT lên chợ với giá {gia_thue} COINS/ngày'
        }), 200