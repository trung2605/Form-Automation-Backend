from flask import Blueprint, request, jsonify
from app import bcrypt
from app.models.user import User
from app.models.wallet import Wallet
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Vui lòng nhập đầy đủ email và password"}), 400

    if User.objects(email=email).first():
        return jsonify({"error": "Email này đã được đăng ký"}), 409

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(email=email, password_hash=hashed_pw)
    new_user.save()

    # Create a wallet for the new user, give them 10 free credits
    new_wallet = Wallet(user_id=str(new_user.id), balance=10)
    new_wallet.save()

    return jsonify({"message": "Đăng ký thành công! Bạn được tặng 10 credits dùng thử."}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.objects(email=email).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "message": "Đăng nhập thành công",
            "access_token": access_token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role
            }
        }), 200

    return jsonify({"error": "Email hoặc mật khẩu không chính xác"}), 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()
    if not user:
        return jsonify({"error": "Không tìm thấy User"}), 404
        
    return jsonify({
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "wallet_balance": user.wallet.balance if user.wallet else 0
    }), 200
