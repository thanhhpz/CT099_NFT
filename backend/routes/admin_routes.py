from flask import request, jsonify
from models.nguoidung_model import NguoiDung
from models.game_model import Game
from models.nhanvat_model import NhanVat
from models.vatpham_model import VatPham
from models.nft_model import NFT
from models.hopdong_model import HopDong
from models.giaodich_model import GiaoDich
from models.danhgia_model import DanhGia
from models.wallet_model import Wallet
import jwt
from config import Config
from functools import wraps
from database.connection import nguoidung_collection, game_collection, nhanvat_collection, vatpham_collection, hopdong_collection, giaodich_collection

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

def admin_routes(app):
    
    # ============================================================
    # QUẢN LÝ NGƯỜI DÙNG
    # ============================================================
    @app.route('/api/admin/users', methods=['GET'])
    @token_required
    def admin_get_users(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            users = NguoiDung.find_all()
            return jsonify({'success': True, 'users': users}), 200
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/admin/users/<ma_nguoi_dung>/toggle-role', methods=['PUT'])
    @token_required
    def admin_toggle_role(current_user, ma_nguoi_dung):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            # Không cho tự đổi vai trò của chính mình
            if ma_nguoi_dung == current_user.ma_nguoi_dung:
                return jsonify({'success': False, 'message': 'Không thể thay đổi vai trò của chính bạn'}), 400
            
            user = NguoiDung.find_by_ma(ma_nguoi_dung)
            if not user:
                return jsonify({'success': False, 'message': 'Người dùng không tồn tại'}), 404
            
            new_role = 'quan_tri' if user.vai_tro == 'nguoi_dung' else 'nguoi_dung'
            nguoidung_collection.update_one(
                {'ma_nguoi_dung': ma_nguoi_dung},
                {'$set': {'vai_tro': new_role}}
            )
            return jsonify({'success': True, 'message': f'Đã đổi vai trò thành {new_role}'}), 200
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # ============================================================
    # QUẢN LÝ TRÒ CHƠI
    # ============================================================
    @app.route('/api/admin/games', methods=['GET'])
    @token_required
    def admin_get_games(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            games = Game.find_all()
            for game in games:
                characters = NhanVat.find_by_game(game['ma_game'])
                game['so_nhan_vat'] = len(characters)
            return jsonify({'success': True, 'games': games}), 200
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/admin/games', methods=['POST'])
    @token_required
    def admin_create_game(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ'}), 400
            
            ten_game = data.get('ten_game', '').strip()
            if not ten_game:
                return jsonify({'success': False, 'message': 'Thiếu tên game'}), 400
            
            # Kiểm tra trùng tên
            existing = game_collection.find_one({'ten_game': ten_game})
            if existing:
                return jsonify({'success': False, 'message': 'Tên game đã tồn tại'}), 400
            
            game = Game(
                ten_game=ten_game,
                mo_ta_game=data.get('mo_ta_game', ''),
                nha_phat_hanh=data.get('nha_phat_hanh', '')
            )
            game.save()
            return jsonify({'success': True, 'game': game.to_dict()}), 201
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/admin/games/<ma_game>', methods=['DELETE'])
    @token_required
    def admin_delete_game(current_user, ma_game):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            # Kiểm tra game tồn tại
            game = Game.find_by_ma(ma_game)
            if not game:
                return jsonify({'success': False, 'message': 'Game không tồn tại'}), 404
            
            # Kiểm tra có nhân vật không
            characters = NhanVat.find_by_game(ma_game)
            if characters:
                return jsonify({
                    'success': False, 
                    'message': f'Không thể xóa game vì còn {len(characters)} nhân vật liên quan. Vui lòng xóa nhân vật trước.'
                }), 400
            
            # Kiểm tra có vật phẩm không
            items = VatPham.find_by_game(ma_game)
            if items:
                return jsonify({
                    'success': False,
                    'message': f'Không thể xóa game vì còn {len(items)} vật phẩm liên quan. Vui lòng xóa vật phẩm trước.'
                }), 400
            
            result = game_collection.delete_one({'ma_game': ma_game})
            if result.deleted_count == 0:
                return jsonify({'success': False, 'message': 'Game không tồn tại'}), 404
            
            return jsonify({'success': True, 'message': f'Đã xóa game "{game["ten_game"]}" thành công'}), 200
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # ============================================================
    # QUẢN LÝ NHÂN VẬT
    # ============================================================
    @app.route('/api/admin/characters', methods=['GET'])
    @token_required
    def admin_get_characters(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            characters = NhanVat.find_all()
            
            for char in characters:
                game = Game.find_by_ma(char['ma_game'])
                char['ten_game'] = game['ten_game'] if game else 'Không rõ'
            
            return jsonify({'success': True, 'characters': characters}), 200
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/admin/characters', methods=['POST'])
    @token_required
    def admin_create_character(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ'}), 400
            
            ten_nhan_vat = data.get('ten_nhan_vat', '').strip()
            ma_game = data.get('ma_game')
            
            if not ten_nhan_vat:
                return jsonify({'success': False, 'message': 'Thiếu tên nhân vật'}), 400
            if not ma_game:
                return jsonify({'success': False, 'message': 'Thiếu mã game'}), 400
            
            # Kiểm tra game tồn tại
            game = Game.find_by_ma(ma_game)
            if not game:
                return jsonify({'success': False, 'message': 'Game không tồn tại'}), 404
            
            # Kiểm tra trùng tên trong cùng game
            existing = nhanvat_collection.find_one({
                'ten_nhan_vat': ten_nhan_vat,
                'ma_game': ma_game
            })
            if existing:
                return jsonify({'success': False, 'message': 'Nhân vật đã tồn tại trong game này'}), 400
            
            character = NhanVat(
                ten_nhan_vat=ten_nhan_vat,
                ma_game=ma_game
            )
            character.save()
            return jsonify({'success': True, 'character': character.to_dict()}), 201
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/admin/characters/<ma_nhan_vat>', methods=['DELETE'])
    @token_required
    def admin_delete_character(current_user, ma_nhan_vat):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            # Kiểm tra nhân vật tồn tại
            character = NhanVat.find_by_ma(ma_nhan_vat)
            if not character:
                return jsonify({'success': False, 'message': 'Nhân vật không tồn tại'}), 404
            
            # Kiểm tra có vật phẩm nào dùng nhân vật này không
            items = VatPham.find_by_character(ma_nhan_vat)
            if items:
                return jsonify({
                    'success': False,
                    'message': f'Không thể xóa nhân vật vì còn {len(items)} vật phẩm liên quan. Vui lòng xóa vật phẩm trước.'
                }), 400
            
            result = nhanvat_collection.delete_one({'ma_nhan_vat': ma_nhan_vat})
            if result.deleted_count == 0:
                return jsonify({'success': False, 'message': 'Nhân vật không tồn tại'}), 404
            
            return jsonify({'success': True, 'message': f'Đã xóa nhân vật "{character["ten_nhan_vat"]}" thành công'}), 200
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # ============================================================
    # QUẢN LÝ VẬT PHẨM - CÓ KIỂM TRA THUÊ
    # ============================================================
    # admin_routes.py - Cập nhật admin_get_items
    @app.route('/api/admin/items', methods=['GET'])
    @token_required
    def admin_get_items(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            items = VatPham.find_all()
            
            for item in items:
                # Thêm thông tin game
                game = Game.find_by_ma(item['ma_game'])
                item['ten_game'] = game['ten_game'] if game else 'Không rõ'
                
                # 🔥 LẤY DANH SÁCH NFT CỦA VẬT PHẨM
                from models.nft_model import NFT
                nfts = NFT.find_by_vat_pham(item['ma_vat_pham'])
                
                # Thêm danh sách NFT vào item
                item['nfts'] = nfts
                item['so_luong_nft'] = len(nfts)
                
                # Thống kê trạng thái
                item['so_luong_dang_thue'] = len([n for n in nfts if n.get('trang_thai') == 'dang_thue'])
                item['so_luong_co_san'] = len([n for n in nfts if n.get('trang_thai') == 'co_san'])
                item['so_luong_tam_ngung'] = len([n for n in nfts if n.get('trang_thai') == 'tam_ngung'])
                
                # Thêm thông tin NFT
                item['has_nft'] = len(nfts) > 0
            
            return jsonify({'success': True, 'items': items}), 200
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    @app.route('/api/admin/items', methods=['POST'])
    @token_required
    def admin_create_item(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ'}), 400
            
            ten_vat_pham = data.get('ten_vat_pham', '').strip()
            ma_game = data.get('ma_game')
            
            if not ten_vat_pham:
                return jsonify({'success': False, 'message': 'Thiếu tên vật phẩm'}), 400
            if not ma_game:
                return jsonify({'success': False, 'message': 'Thiếu mã game'}), 400
            
            # Kiểm tra game tồn tại
            game = Game.find_by_ma(ma_game)
            if not game:
                return jsonify({'success': False, 'message': 'Game không tồn tại'}), 404
            
            # Kiểm tra nhân vật nếu có
            ma_nhan_vat = data.get('duoc_dung_cho')
            if ma_nhan_vat:
                character = NhanVat.find_by_ma(ma_nhan_vat)
                if not character:
                    return jsonify({'success': False, 'message': 'Nhân vật không tồn tại'}), 404
                if character['ma_game'] != ma_game:
                    return jsonify({'success': False, 'message': 'Nhân vật không thuộc game này'}), 400
            
            item = VatPham(
                ten_vat_pham=ten_vat_pham,
                ma_game=ma_game,
                mo_ta=data.get('mo_ta', ''),
                loai=data.get('loai', ''),
                gia_thue=data.get('gia_thue', 10),
                don_vi_thue=data.get('don_vi_thue', 'ngày'),
                tien_dat_coc=data.get('tien_dat_coc', 50),
                thoi_gian_thue_toi_da=data.get('thoi_gian_thue_toi_da', 30),
                do_hiem=data.get('do_hiem', 'thường'),
                duoc_dung_cho=data.get('duoc_dung_cho')
            )
            item.save()
            return jsonify({'success': True, 'item': item.to_dict()}), 201
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/admin/items/<ma_vat_pham>', methods=['DELETE'])
    @token_required
    def admin_delete_item(current_user, ma_vat_pham):
        """
        Xóa vật phẩm - CÓ KIỂM TRA VẬT PHẨM ĐANG ĐƯỢC THUÊ
        """
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            # Kiểm tra vật phẩm tồn tại
            item = VatPham.find_by_ma(ma_vat_pham)
            if not item:
                return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
            
            # 🔥 QUAN TRỌNG: Kiểm tra có hợp đồng đang thuê không
            active_rental = hopdong_collection.find_one({
                'ma_bai_dang': ma_vat_pham,
                'trang_thai_thue': 'dang_thue'
            })
            
            if active_rental:
                # Lấy thông tin người thuê
                nguoi_thue = NguoiDung.find_by_ma(active_rental.get('ma_nguoi_thue'))
                ten_nguoi_thue = nguoi_thue.ten_nguoi_dung if nguoi_thue else 'Không rõ'
                
                return jsonify({
                    'success': False,
                    'message': f'Không thể xóa vật phẩm "{item["ten_vat_pham"]}" vì đang có người thuê!',
                    'details': {
                        'nguoi_thue': ten_nguoi_thue,
                        'ma_hop_dong': active_rental.get('ma_hop_dong'),
                        'thoi_gian_bat_dau': active_rental.get('thoi_gian_bat_dau'),
                        'thoi_gian_ket_thuc': active_rental.get('thoi_gian_ket_thuc')
                    }
                }), 400
            
            # Kiểm tra có hợp đồng đã hủy nhưng chưa trả tiền cọc
            pending_rental = hopdong_collection.find_one({
                'ma_bai_dang': ma_vat_pham,
                'trang_thai_thue': 'da_huy',
                'da_tra_tien_coc': {'$ne': True}
            })
            
            if pending_rental:
                return jsonify({
                    'success': False,
                    'message': f'Không thể xóa vật phẩm "{item["ten_vat_pham"]}" vì đã có hợp đồng hủy nhưng chưa hoàn trả tiền cọc.'
                }), 400
            
            # Xóa vật phẩm
            result = vatpham_collection.delete_one({'ma_vat_pham': ma_vat_pham})
            
            if result.deleted_count == 0:
                return jsonify({'success': False, 'message': 'Không tìm thấy vật phẩm để xóa'}), 404
            
            return jsonify({'success': True, 'message': f'Đã xóa vật phẩm "{item["ten_vat_pham"]}" thành công'}), 200
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Lỗi server: {str(e)}'}), 500
    
    # ============================================================
    # QUẢN LÝ HỢP ĐỒNG
    # ============================================================
    @app.route('/api/admin/rentals', methods=['GET'])
    @token_required
    def admin_get_rentals(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            rentals = HopDong.find_all()
            
            for rental in rentals:
                # Lấy tên người thuê
                nguoi_thue = NguoiDung.find_by_ma(rental['ma_nguoi_thue'])
                rental['ten_nguoi_thue'] = nguoi_thue.ten_nguoi_dung if nguoi_thue else 'Không rõ'
                
                # Lấy thông tin vật phẩm
                item = VatPham.find_by_ma(rental['ma_bai_dang'])
                if item:
                    rental['ten_vat_pham'] = item['ten_vat_pham']
                    
                    # Lấy chủ sở hữu từ NFT
                    nfts = NFT.find_by_vat_pham(item['ma_vat_pham'])
                    if nfts:
                        owner_wallet = Wallet.find_by_address(nfts[0]['dia_chi_chu_so_huu'])
                        if owner_wallet:
                            rental['ten_chu_so_huu'] = owner_wallet.get('ten_nguoi_dung', 'Không rõ')
                        else:
                            rental['ten_chu_so_huu'] = 'Không rõ'
                    else:
                        rental['ten_chu_so_huu'] = 'Không rõ'
                else:
                    rental['ten_vat_pham'] = '⚠️ Đã bị xóa'
                    rental['ten_chu_so_huu'] = 'Không rõ'
            
            return jsonify({'success': True, 'rentals': rentals}), 200
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # ============================================================
    # QUẢN LÝ GIAO DỊCH - ĐÃ SỬA (THÊM NGƯỜI THỰC HIỆN)
    # ============================================================
    @app.route('/api/admin/transactions', methods=['GET'])
    @token_required
    def admin_get_transactions(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            transactions = GiaoDich.find_all()
            
            # Thêm thông tin người thực hiện cho mỗi giao dịch
            for tx in transactions:
                ma_nguoi_dung = tx.get('ma_nguoi_dung')
                
                # Nếu có mã người dùng
                if ma_nguoi_dung:
                    nguoi_dung = NguoiDung.find_by_ma(ma_nguoi_dung)
                    if nguoi_dung:
                        tx['ten_nguoi_thuc_hien'] = nguoi_dung.ten_nguoi_dung
                        tx['ho_ten_nguoi_thuc_hien'] = nguoi_dung.ho_ten
                    else:
                        tx['ten_nguoi_thuc_hien'] = 'Người dùng đã bị xóa'
                        tx['ho_ten_nguoi_thuc_hien'] = 'Không rõ'
                else:
                    # Nếu là nạp tiền và không có người thực hiện -> Hệ thống
                    if tx.get('loai_giao_dich') == 'nap_tien':
                        tx['ten_nguoi_thuc_hien'] = 'Hệ thống'
                        tx['ho_ten_nguoi_thuc_hien'] = 'Hệ thống'
                    else:
                        tx['ten_nguoi_thuc_hien'] = 'Không rõ'
                        tx['ho_ten_nguoi_thuc_hien'] = 'Không rõ'
            
            return jsonify({'success': True, 'transactions': transactions}), 200
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # ============================================================
    # THỐNG KÊ
    # ============================================================
    @app.route('/api/admin/stats', methods=['GET'])
    @token_required
    def admin_get_stats(current_user):
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            stats = {
                'total_users': len(NguoiDung.find_all()),
                'total_games': len(Game.find_all()),
                'total_characters': len(NhanVat.find_all()),
                'total_items': len(VatPham.find_all()),
                'total_nfts': len(NFT.find_all()),
                'total_rentals': len(HopDong.find_all()),
                'total_transactions': len(GiaoDich.find_all()),
                'total_reviews': len(DanhGia.find_all())
            }
            return jsonify({'success': True, 'stats': stats}), 200
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500


    # admin_routes.py - Thêm API này để hỗ trợ items.html

    @app.route('/api/admin/items/<ma_vat_pham>/nfts', methods=['GET'])
    @token_required
    def admin_get_item_nfts(current_user, ma_vat_pham):
        """Lấy danh sách NFT của một vật phẩm"""
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            item = VatPham.find_by_ma(ma_vat_pham)
            if not item:
                return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
            
            nfts = NFT.find_by_vat_pham(ma_vat_pham)
            
            # Thêm thông tin chủ sở hữu và người thuê
            for nft in nfts:
                # Chủ sở hữu
                wallet = Wallet.find_by_address(nft['dia_chi_chu_so_huu'])
                nft['ten_chu_so_huu'] = wallet.get('ten_nguoi_dung', 'Không rõ') if wallet else 'Không rõ'
                
                # Người thuê nếu đang thuê
                nft['nguoi_thue'] = None
                if nft.get('trang_thai') == 'dang_thue':
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
                    else:
                        nft['nguoi_thue'] = 'Không rõ'
            
            # Thêm thông tin vật phẩm
            item_info = {
                'ma_vat_pham': item['ma_vat_pham'],
                'ten_vat_pham': item['ten_vat_pham'],
                'mo_ta': item.get('mo_ta', ''),
                'gia_thue': item.get('gia_thue', 0),
                'tien_coc': item.get('tien_dat_coc', 0)
            }
            
            return jsonify({
                'success': True,
                'item': item_info,
                'nfts': nfts,
                'total': len(nfts),
                'rented': len([n for n in nfts if n.get('trang_thai') == 'dang_thue']),
                'available': len([n for n in nfts if n.get('trang_thai') == 'co_san'])
            }), 200
            
        except Exception as e:
            print(f"❌ Lỗi admin_get_item_nfts: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500
    # ============================================================
    # API HỖ TRỢ: KIỂM TRA TRẠNG THÁI VẬT PHẨM
    # ============================================================
    @app.route('/api/admin/items/<ma_vat_pham>/status', methods=['GET'])
    @token_required
    def admin_get_item_status(current_user, ma_vat_pham):
        """
        Kiểm tra trạng thái của vật phẩm (có đang thuê không)
        """
        if current_user.vai_tro != 'quan_tri':
            return jsonify({'success': False, 'message': 'Không có quyền'}), 403
        
        try:
            item = VatPham.find_by_ma(ma_vat_pham)
            if not item:
                return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
            
            active_rental = hopdong_collection.find_one({
                'ma_bai_dang': ma_vat_pham,
                'trang_thai_thue': 'dang_thue'
            })
            
            return jsonify({
                'success': True,
                'item': {
                    'ma_vat_pham': ma_vat_pham,
                    'ten_vat_pham': item['ten_vat_pham'],
                    'is_rented': bool(active_rental)
                },
                'rental_info': {
                    'is_active': bool(active_rental),
                    'ma_hop_dong': active_rental.get('ma_hop_dong') if active_rental else None,
                    'nguoi_thue': active_rental.get('ma_nguoi_thue') if active_rental else None
                }
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500