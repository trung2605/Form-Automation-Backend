from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User

def admin_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.objects(id=user_id).first()
            
            if not user or user.role != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def check_banned():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                user = User.objects(id=user_id).first()
                if user and user.is_banned:
                    return jsonify({"error": "Tài khoản của bạn đã bị khóa."}), 403
            
            return fn(*args, **kwargs)
        return decorator
    return wrapper
