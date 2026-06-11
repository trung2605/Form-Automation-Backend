import json
import re
import os
from dotenv import load_dotenv

load_dotenv(override=True)

PROMPT_TEMPLATE = """
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
            "options": ["tùy chọn 1", "tùy chọn 2"],
            "weights": [0.5, 0.5]
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
- Trả về JSON hợp lệ, không có text nào khác ngoài JSON.

Mã nguồn HTML:
{html_source}
"""

def _clip_html(html):
    if len(html) < 150000:
        return html
    return html[:100000] + ' ... (clipped) ... ' + html[-50000:]

def _clean_json(raw):
    text = raw.replace('```json', '').replace('```', '').strip()
    brace_idx = text.find('{')
    if brace_idx > 0:
        text = text[brace_idx:]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text

def _extract_hidden_fields_regex(html):
    fields = {}
    patterns = {
        'fbzx': r'name="fbzx"\s+value="([^"]+)"',
        'fvv': r'name="fvv"\s+value="([^"]+)"',
        'pageHistory': r'name="pageHistory"\s+value="([^"]+)"',
        'draftResponse': r'name="draftResponse"\s+value="([^"]*)"',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, html)
        if match:
            fields[key] = match.group(1)
    hidden_inputs = re.findall(r'<input\s+type="hidden"\s+name="([^"]+)"\s+value="([^"]*)"', html)
    for name, value in hidden_inputs:
        if name in ('fbzx', 'fvv', 'pageHistory', 'draftResponse') or name.startswith('entry.'):
            fields[name] = value
    return fields

def _merge_hidden(data, html):
    regex_hidden = _extract_hidden_fields_regex(html)
    if 'hiddenFields' not in data:
        data['hiddenFields'] = {}
    data['hiddenFields'].update(regex_hidden)
    return data

# ── Providers ──────────────────────────────────────────────────────────────────

def _parse_with_gemini(html, api_key):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = PROMPT_TEMPLATE.format(html_source=_clip_html(html))
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    raw = response.text if response.text else ""
    print(f"[Gemini] finish_reason={response.candidates[0].finish_reason if response.candidates else 'N/A'}")
    print(f"[Gemini] raw (first 300): {raw[:300]}")
    return json.loads(_clean_json(raw))

def _parse_with_openai(html, api_key):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(html_source=_clip_html(html))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or ""
    print(f"[OpenAI] raw (first 300): {raw[:300]}")
    return json.loads(_clean_json(raw))

def _parse_with_huggingface(html, api_key):
    from huggingface_hub import InferenceClient
    client = InferenceClient(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(html_source=_clip_html(html))
    # Qwen2.5-72B supports JSON mode via grammar/response_format on some endpoints,
    # but basic chat completion is the safest cross-endpoint approach.
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-72B-Instruct",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        stream=False,
    )
    raw = response.choices[0].message.content or ""
    print(f"[HuggingFace] finish_reason={response.choices[0].finish_reason}")
    print(f"[HuggingFace] raw (first 500): {raw[:500]}")
    return json.loads(_clean_json(raw))

# ── Main entry ──────────────────────────────────────────────────────────────────

def parse_form_config(html_source, gemini_key=None, openai_key=None, hf_key=None):
    # Fall back to env vars if UI didn't provide keys
    gemini_key = gemini_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    openai_key = openai_key or os.environ.get("OPENAI_API_KEY")
    hf_key     = hf_key     or os.environ.get("HF_API_KEY") or os.environ.get("HUGGINGFACE_API_KEY")

    providers = []
    if gemini_key:
        providers.append(("Gemini", lambda: _parse_with_gemini(html_source, gemini_key)))
    if openai_key:
        providers.append(("OpenAI", lambda: _parse_with_openai(html_source, openai_key)))
    if hf_key:
        providers.append(("HuggingFace", lambda: _parse_with_huggingface(html_source, hf_key)))

    if not providers:
        raise ValueError("No API key provided. Supply at least one of: Gemini, OpenAI, or HuggingFace API key.")

    last_error = None
    for name, fn in providers:
        try:
            print(f"[AI Parser] Trying {name}...")
            data = fn()
            data = _merge_hidden(data, html_source)
            print(f"[AI Parser] Success with {name}")
            data["_provider"] = name
            return data
        except Exception as e:
            import traceback
            print(f"[AI Parser] {name} failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            last_error = e

    raise RuntimeError(f"All providers failed. Last error: {last_error}")
