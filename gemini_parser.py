# gemini_parser.py
import google.generativeai as genai
import json
import os
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def parse_form_config(html_source):
    model = genai.GenerativeModel('gemini-2.5-flash')

    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(f"Tên mô hình khả dụng: {m.name}")
    
    prompt = f"""
    Bạn là một trợ lý phân tích HTML chuyên nghiệp.
    Mã nguồn HTML sau đây là một Google Form. Nhiệm vụ của bạn là trích xuất cấu hình biểu mẫu dưới dạng một đối tượng JSON.

    Định dạng JSON cần tuân theo mẫu sau:
    {{
        "submitUrl": "string",
        "formConfig": {{
            "entry.field_id_1": {{
                "type": "string",
                "options": "array",
                "weights": "array"
            }},
            "entry.field_id_2": {{...}}
        }}
    }}

    Hãy làm theo các quy tắc sau:
    1. Tìm 'action' của thẻ <form> để lấy 'submitUrl'.
    2. Duyệt qua các trường nhập liệu để tìm 'entry ID' (thường có dạng entry.XXXXXXXXX) và tên trường.
    3. Xác định loại trường:
       - Nếu tên trường chứa từ "email", loại là "email".
       - Nếu có các thẻ input radio hoặc label với thuộc tính data-value, loại là "choice".
       - Nếu có các thẻ input checkbox, loại là "checkbox".
       - Các trường còn lại là "text".
    4. Đối với "choice" và "checkbox", hãy liệt kê tất cả các tùy chọn trong mảng "options". Gán trọng số đều nhau cho tất cả các tùy chọn.
    5. Đối với trường "text" hoặc "email", mảng "options" có thể để trống.
    6. Đảm bảo toàn bộ đầu ra là một đối tượng JSON hợp lệ và duy nhất.

    Mã nguồn HTML:
    {html_source}

    Trả về chỉ đối tượng JSON. KHÔNG thêm bất kỳ văn bản, giải thích hoặc code block nào khác.
    """

    try:
        response = model.generate_content(prompt)
        json_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_text)
    except Exception as e:
        print(f"Lỗi khi gọi API Gemini: {e}")
        return None