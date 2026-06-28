import sys
import os

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import mongoengine
from app.config import Config
from app.models.user import User

def make_admin(email):
    # Connect to DB
    mongoengine.connect(host=Config.MONGODB_SETTINGS['host'])
    
    user = User.objects(email=email).first()
    if not user:
        print(f"[-] Lỗi: Không tìm thấy tài khoản với email '{email}'")
        return
    
    if user.role == 'admin':
        print(f"[!] Tài khoản '{email}' đã là admin từ trước.")
        return

    user.role = 'admin'
    user.save()
    print(f"[+] Thành công! Tài khoản '{email}' đã được cấp quyền Admin tối cao.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách dùng: python make_admin.py <email_cua_ban>")
    else:
        make_admin(sys.argv[1])
