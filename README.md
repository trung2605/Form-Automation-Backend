# 🚀 Nền Tảng ToolManager - Backend (Auto Form Website)

Đây là mã nguồn Backend chính thức cho nền tảng **ToolManager** (tiền thân là Auto Form Website). Hệ thống đã được nâng cấp toàn diện thành mô hình **SaaS (Software as a Service)** chuyên nghiệp với kiến trúc **MVC**, tích hợp bảo mật **JWT**, cơ sở dữ liệu **MongoDB** và hệ thống thanh toán tín dụng (Credits/Wallet).

---

## 🌟 Các Tính Năng Cốt Lõi

1. **Hệ Thống Xác Thực (Authentication)**: 
   - Đăng ký và Đăng nhập bảo mật sử dụng JWT (JSON Web Tokens).
   - Mật khẩu được băm một chiều an toàn bằng Bcrypt.
2. **Quản Lý Ví Điện Tử (Wallet System)**:
   - Tự động cấp ví và tặng 10 Credits khi người dùng tạo tài khoản mới.
   - Cơ chế nạp tiền mô phỏng (Fake Deposit) và ghi nhận lịch sử giao dịch rõ ràng.
3. **Form Automation Engine (Cốt Lõi)**:
   - Phân tích thông minh: Trích xuất cấu hình từ mã nguồn HTML của Google Form bằng Trí tuệ nhân tạo (hỗ trợ Gemini, OpenAI, HuggingFace).
   - Điền Form Tự Động: Tính năng giả lập trình duyệt gửi hàng loạt dữ liệu biểu mẫu.
   - **Tích hợp thanh toán**: Mỗi lần Submit thành công sẽ tự động trừ Credits trong ví của người dùng.

---

## 🏗️ Cấu Trúc Thư Mục (Kiến Trúc MVC)

Dự án được phân chia rõ ràng theo mô hình **Model-View-Controller**:

```text
Auto_Form_Backend/
├── app/
│   ├── __init__.py         # Khởi tạo App, cấu hình MongoDB & Blueprint
│   ├── config.py           # File thiết lập môi trường (Secret Key, Mongo URI)
│   ├── models/             # Định nghĩa Database Schema (MongoDB Document)
│   │   ├── user.py         # Tài khoản người dùng
│   │   ├── wallet.py       # Ví điện tử
│   │   └── transaction.py  # Lịch sử nạp/trừ tiền
│   ├── controllers/        # Nơi tiếp nhận và xử lý HTTP Request
│   │   ├── auth.py         # Nhóm API Đăng nhập / Đăng ký
│   │   ├── payment.py      # Nhóm API Nạp tiền / Lịch sử
│   │   └── forms.py        # Nhóm API Phân tích & Gửi form
│   └── services/           # Chứa Business Logic (không phụ thuộc HTTP)
│       ├── ai_parser.py    # Logic AI phân tích HTML
│       └── form_filler.py  # Logic giả lập submit HTTP form
├── run.py                  # File khởi động Server
├── requirements.txt        # Danh sách thư viện Python
└── .env                    # File biến môi trường (Tạo thủ công theo mẫu)
```

---

## ⚙️ Hướng Dẫn Cài Đặt (Local Development)

### 1. Yêu cầu hệ thống
- Python 3.10 trở lên.
- MongoDB Server đang chạy cục bộ (hoặc sử dụng MongoDB Atlas Cluster).

### 2. Cài đặt thư viện
Mở Terminal tại thư mục `Auto_Form_Backend` và chạy lệnh:
```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường (`.env`)
Tạo một file `.env` tại thư mục gốc của Backend (`Auto_Form_Backend/.env`) với nội dung sau:
```env
# Chuỗi kết nối MongoDB (Thay bằng URI của bạn, ví dụ MongoDB Atlas)
MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority&appName=ToolManager

# Khóa API để phân tích Form (Cần ít nhất 1 loại)
GOOGLE_API_KEY=AIzaSy...
# OPENAI_API_KEY=sk-...
# HF_API_KEY=hf_...

# Secret Keys cho bảo mật (Có thể giữ nguyên khi dev)
SECRET_KEY=super-secret-key
JWT_SECRET_KEY=jwt-super-secret-key
```

### 4. Khởi chạy Server
Chạy lệnh sau để khởi động Backend:
```bash
python run.py
```
*Server sẽ mặc định chạy tại `http://127.0.0.1:5000`*

---

## 📖 Tài Liệu API (Endpoints)

Toàn bộ các Endpoint yêu cầu đăng nhập cần truyền thêm Header: 
`Authorization: Bearer <Access_Token>`

### 🛡️ Nhóm API Auth (`/api/auth`)
- `POST /register`: Đăng ký tài khoản. Yêu cầu JSON body: `{"email": "...", "password": "..."}`.
- `POST /login`: Đăng nhập. Trả về `access_token` và thông tin User.
- `GET /me`: *(Cần JWT)* Lấy thông tin tài khoản hiện tại kèm số dư ví.

### 💰 Nhóm API Thanh Toán (`/api/payment`)
- `POST /deposit`: *(Cần JWT)* Nạp tiền mô phỏng. Yêu cầu JSON body: `{"amount": 100}`.
- `GET /transactions`: *(Cần JWT)* Xem lịch sử biến động số dư.

### 🤖 Nhóm API Form (`/api/forms`)
- `POST /analyze-form`: Phân tích HTML lấy cấu trúc câu hỏi. Yêu cầu JSON body: `{"htmlSource": "..."}` hoặc `{"formUrl": "..."}`.
- `POST /fill-form`: *(Cần JWT)* Bắt đầu luồng submit tự động. Tự động kiểm tra số dư và trừ 1 Credit cho mỗi lượt gửi thành công.

---

## 🛠️ Công Nghệ Sử Dụng
- **Framework**: Flask (Python)
- **Database**: MongoDB (via MongoEngine)
- **Security**: Flask-JWT-Extended, Flask-Bcrypt, Flask-CORS
- **Tích hợp AI**: Google Generative AI (Gemini), OpenAI, HuggingFace.

*Phát triển bởi Lê Trí Trung.*
