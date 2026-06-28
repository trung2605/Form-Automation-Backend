from app import bcrypt
from app.models.user import User
from app.models.wallet import Wallet
from flask_jwt_extended import create_access_token

class AuthService:
    @staticmethod
    def register_user(email, password):
        if not email or not password:
            return {"error": "Vui lòng nhập đầy đủ email và password"}, 400

        if User.objects(email=email).first():
            return {"error": "Email này đã được đăng ký"}, 409

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password_hash=hashed_pw)
        new_user.save()

        # Create a wallet for the new user, give them 10 free credits
        new_wallet = Wallet(user_id=str(new_user.id), balance=10)
        new_wallet.save()

        return {"message": "Đăng ký thành công! Bạn được tặng 10 credits dùng thử."}, 201

    @staticmethod
    def authenticate_user(email, password):
        user = User.objects(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            access_token = create_access_token(identity=str(user.id))
            return {
                "message": "Đăng nhập thành công",
                "access_token": access_token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role
                }
            }, 200

        return {"error": "Email hoặc mật khẩu không chính xác"}, 401

    @staticmethod
    def get_user_profile(user_id):
        user = User.objects(id=user_id).first()
        if not user:
            return {"error": "Không tìm thấy User"}, 404
            
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "wallet_balance": user.wallet.balance if user.wallet else 0
        }, 200
