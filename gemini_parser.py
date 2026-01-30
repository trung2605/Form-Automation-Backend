# gemini_parser.py
import google.generativeai as genai
import json
import os
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def parse_form_config(html_source):
    model = genai.GenerativeModel('gemini-2.5-flash')

    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            # print(f"Tên mô hình khả dụng: {m.name}") # Comment out to reduce noise
            pass
    
    prompt = f"""
    Bạn là một chuyên gia về cấu trúc dữ liệu Google Forms và Reverse Engineering.
    Nhiệm vụ: Trích xuất cấu hình điền form từ mã nguồn HTML được cung cấp.

    QUAN TRỌNG:
    Google Forms lưu trữ toàn bộ cấu trúc câu hỏi (bao gồm cả các trang ẩn, rẽ nhánh) trong một biến JavaScript có tên là `FB_PUBLIC_LOAD_DATA_`.
    Đừng chỉ nhìn vào các thẻ HTML <input> vì chúng thường chỉ hiện thị trang đầu tiên.
    Hãy tìm và phân tích mảng dữ liệu trong `FB_PUBLIC_LOAD_DATA_` để lấy danh sách ĐẦY ĐỦ các câu hỏi.

    Yêu cầu đầu ra (JSON Object duy nhất):
    {{
        "submitUrl": "Tìm trong thẻ <form action='...'>, thường kết thúc bằng formResponse",
        "formConfig": {{
            "entry.ID_CỦA_CÂU_HỎI": {{
                "type": "loại câu hỏi",
                "options": ["tùy chọn 1", "tùy chọn 2", ...],
                "weights": [0.x, 0.y, ...] (Tổng các trọng số = 1, chia đều mặc định)
            }}
        }}
    }}

    Chi tiết về "formConfig":
    1. Key là 'entry.ID': Tìm ID này trong dữ liệu (thường là số nguyên lớn). Hãy chắc chắn thêm tiền tố "entry." vào trước ID.
    2. "type":
       - "email": Nếu câu hỏi yêu cầu địa chỉ email.
       - "choice": Trắc nghiệm (Radio), Menu thả xuống (Dropdown).
       - "checkbox": Hộp kiểm (Checkbox) - Cho phép chọn nhiều.
       - "text": Câu trả lời ngắn (Short answer), Đoạn văn (Paragraph).
       - "date": Ngày tháng.
       - "time": Giờ.
    3. "options":
       - BẮT BUỘC phải có cho "choice" và "checkbox".
       - Liệt kê toàn bộ các text hiển thị của tùy chọn.
       - Với "text", "date", "time", "email": để mảng rỗng [] hoặc null.
    4. "weights":
       - Tạo một mảng số thực có độ dài bằng mảng "options".
       - Giá trị mặc định: chia đều (ví dụ 2 options thì [0.5, 0.5]).

    Lưu ý xử lý:
    - Bỏ qua các phần tiêu đề (HeaderImage, Description).
    - Chỉ lấy các câu hỏi người dùng cần nhập.
    - Nếu không tìm thấy `FB_PUBLIC_LOAD_DATA_`, hãy cố gắng fallback sang phân tích DOM HTML thông thường nhưng ưu tiên dữ liệu gốc.
    - Đảm bảo JSON hợp lệ, không có trailing comma.

    Mã nguồn HTML:
    {html_source[:100000]} ... (đã cắt bớt nếu quá dài) ... {html_source[-50000:]}

    Chỉ trả về JSON thuần túy, không Markdown.
    """

    try:
        # Google Form HTML can be very large, Gemini Flash handles context well but let's be safe
        # We pass the full source if possible, or truncate intelligently if needed knowing Flash has ~1M context window
        # For now simply passing the source.
        response = model.generate_content(prompt)
        json_text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(json_text)
        return data
    except Exception as e:
        print(f"Lỗi khi gọi API Gemini: {e}")
        return None