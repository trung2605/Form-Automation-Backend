import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# Check key presence
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("❌ ERROR: GOOGLE_API_KEY not found in environment!")
else:
    print(f"✅ Gemini Parser loaded. Key found: {api_key[:8]}...")

def parse_form_config(html_source):
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""
    Bạn là một chuyên gia về cấu trúc dữ liệu Google Forms và Reverse Engineering.
    Nhiệm vụ: Trích xuất cấu hình điền form từ mã nguồn HTML được cung cấp để tạo payload gửi POST request.

    QUAN TRỌNG:
    1. Google Forms lưu dữ liệu câu hỏi trong biến `FB_PUBLIC_LOAD_DATA_`. Hãy ưu tiên phân tích mảng này.
    2. Cần phân biệt chính xác ID của các trường.
       - Hầu hết các câu hỏi (Input, Textarea, Radio, Checkbox) đều có name là "entry.ID" (ID là số).
       - TRƯỜNG HỢP ĐẶC BIỆT: Nếu form có bật chế độ "Thu thập địa chỉ email" (Collect email addresses), input đó sẽ có name là "emailAddress" (không phải entry.ID). Hãy tìm kỹ input có `name="emailAddress"` hoặc `type="email"`.

    Yêu cầu đầu ra (JSON Object duy nhất):
    {{
        "submitUrl": "Link action TUYỆT ĐỐI...",
        "hiddenFields": {{
            "key": "value"
        }},
        "formConfig": {{
            "KEY_CỦA_TRƯỜNG": {{
                "label": "Nội dung câu hỏi đầy đủ",
                "type": "loại câu hỏi",
                "options": ["tùy chọn 1", "tùy chọn 2", ...],
                "weights": [0.x, 0.y, ...]
            }}
        }}
    }}

    Quy tắc cho "hiddenFields":
    - Tìm toàn bộ thẻ <input type="hidden"> trong form.
    - Lấy name và value của chúng.
    - ĐẶC BIỆT QUAN TRỌNG: "fbzx" (thường id="uuid_..."), "fvv", "draftResponse", "pageHistory".
    - Nếu không tìm thấy value, để trống.

    Quy tắc cho "KEY_CỦA_TRƯỜNG":
    - Nếu là câu hỏi thường: Dùng "entry.ID" (Ví dụ: "entry.123456").
    - Nếu là trường thu thập email tự động của Google: Dùng "emailAddress".
    - Hãy chắc chắn ID là chính xác.

    Quy tắc cho "label":
    - Lấy nội dung câu hỏi đầy đủ từ `FB_PUBLIC_LOAD_DATA_` tương ứng với ID đó.
    - Nếu không tìm thấy, để chuỗi rỗng "".

    Quy tắc cho "type":
    - "email": Trường nhập email.
    - "choice": Trắc nghiệm (Radio), Dropdown.
    - "checkbox": Hộp kiểm (Checkbox).
    - "text": Trả lời ngắn, Đoạn văn.
    - "date": Ngày.
    - "time": Giờ.

    Quy tắc cho "options" và "weights":
    - "choice", "checkbox": Mảng "options" chứa danh sách các lựa chọn text (BẮT BUỘC). Mảng "weights" chia đều tương ứng.
    - Các loại khác: "options" là [].

    Lưu ý:
    - Bỏ qua các phần tiêu đề, hình ảnh trang trí.
    - Dữ liệu `FB_PUBLIC_LOAD_DATA_` chứa cấu trúc lồng nhau, hãy phân tích kỹ để map đúng ID với câu hỏi.
    - Trả về JSON hợp lệ.

    Mã nguồn HTML (trích đoạn):
    {html_source if len(html_source) < 150000 else html_source[:100000] + ' ... (clipped) ... ' + html_source[-50000:]}
    """

    import re

    def extract_hidden_fields_regex(html):
        fields = {}
        patterns = {
            'fbzx': r'name="fbzx"\s+value="([^"]+)"',
            'fvv': r'name="fvv"\s+value="([^"]+)"',
            'pageHistory': r'name="pageHistory"\s+value="([^"]+)"',
            'draftResponse': r'name="draftResponse"\s+value="([^"]+)"'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                fields[key] = match.group(1)

        hidden_inputs = re.findall(r'<input\s+type="hidden"\s+name="([^"]+)"\s+value="([^"]*)"', html)
        for name, value in hidden_inputs:
            if name in ['fbzx', 'fvv', 'pageHistory', 'draftResponse'] or name.startswith('entry.'):
                 fields[name] = value

        return fields

    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        raw = response.text if response.text else ""
        print(f"[Gemini] finish_reason={response.candidates[0].finish_reason if response.candidates else 'N/A'}")
        print(f"[Gemini] raw response (first 300 chars): {raw[:300]}")
        json_text = raw.replace('```json', '').replace('```', '').strip()
        # Strip any leading text before the JSON object
        brace_idx = json_text.find('{')
        if brace_idx > 0:
            json_text = json_text[brace_idx:]
        # Fix trailing commas
        import re as _re
        json_text = _re.sub(r',\s*([}\]])', r'\1', json_text)
        data = json.loads(json_text)

        regex_hidden = extract_hidden_fields_regex(html_source)
        if 'hiddenFields' not in data:
            data['hiddenFields'] = {}

        data['hiddenFields'].update(regex_hidden)

        return data
    except Exception as e:
        print(f"Lỗi khi gọi API Gemini: {e}")
        return None
