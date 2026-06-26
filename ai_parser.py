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

# ── Native Python Parser for FB_PUBLIC_LOAD_DATA_ ─────────────────────────────

def _extract_fb_raw(html):
    """Extract the raw FB_PUBLIC_LOAD_DATA_ JSON string from HTML."""
    # Try to find the variable assignment ending at </script>
    m = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[[\s\S]*?\]);\s*</script>', html)
    if m:
        return m.group(1)
    # Fallback: grab the content between = and next semicolon (can be large)
    m2 = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[[\s\S]{100,2000000}?);', html)
    if m2:
        return m2.group(1)
    return None


def _parse_native(html):
    """
    Parse FB_PUBLIC_LOAD_DATA_ directly in Python without sending to AI.
    Returns a dict with submitUrl, hiddenFields, formConfig or None on failure.
    """
    raw = _extract_fb_raw(html)
    if not raw:
        print("[NativeParser] Could not find FB_PUBLIC_LOAD_DATA_ in HTML")
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[NativeParser] JSON parse failed: {e}")
        return None

    # ── Extract submit URL ──────────────────────────────────────────────────
    action = re.search(r'action="([^"]*formResponse[^"]*)"', html)
    submit_url = action.group(1) if action else ""

    # ── Extract hidden fields ───────────────────────────────────────────────
    hidden_fields = _extract_hidden_fields_regex(html)

    # ── Parse questions from FB_PUBLIC_LOAD_DATA_ ───────────────────────────
    # Structure: data[1] is a list of items
    # Each item: [item_id, title, description, type_int, sub_items?, ...]
    # type_int: 0=short text, 1=paragraph, 2=choice/radio, 3=dropdown, 4=checkbox,
    #           5=linear scale, 6=?, 7=grid/matrix, 8=section header,
    #           9=date, 10=time, 11=image, 12=video
    # For type=2 (radio/dropdown): item[4][0] is the question group
    #   group[0] = entry_id, group[1] = list of [option_text, ...]
    # For type=7 (grid/matrix): item[4] is list of row groups
    #   each group[0] = entry_id, group[1] = list of row labels
    #   Columns are shared across rows via item[4][0][1]

    form_config = {}
    question_order = []  # track original question sequence

    # Check if email collection is enabled
    email_input = re.search(r'name=["\']emailAddress["\']', html, re.IGNORECASE)
    if email_input:
        form_config["emailAddress"] = {
            "label": "Email",
            "type": "email",
            "options": [],
            "weights": []
        }
        question_order.append("emailAddress")

    # data[1] has structure: [description_str, [[item1], [item2], ...], ...]
    # data[1][1] is the flat list of all form items across all pages
    items = None
    try:
        if isinstance(data, list) and len(data) > 1:
            d1 = data[1]
            if isinstance(d1, list) and len(d1) > 1 and isinstance(d1[1], list):
                # data[1][1] is the items list
                items = d1[1]
            elif isinstance(d1, list):
                # fallback: data[1] itself might be items
                items = d1
    except Exception:
        pass

    if items is None:
        print("[NativeParser] Could not find items list in FB_PUBLIC_LOAD_DATA_")
        return None

    # Calculate pageHistory dynamically to support multi-page forms
    page_count = 1
    for item in items:
        if isinstance(item, list) and len(item) >= 4 and item[3] == 8:
            page_count += 1
    calculated_page_history = ",".join(str(i) for i in range(page_count))
    hidden_fields["pageHistory"] = calculated_page_history
    print(f"[NativeParser] Calculated pageHistory: {calculated_page_history} ({page_count} pages)")

    QUESTION_TYPES = {0, 1, 2, 3, 4, 5, 7, 9, 10}

    form_routing = []
    current_page_idx = 0
    current_page_id = None
    current_page_entries = []

    for item in items:
        if not isinstance(item, list) or len(item) < 4:
            continue
            
        item_type = item[3]
        if item_type == 8:
            form_routing.append({
                "page_index": current_page_idx,
                "page_id": current_page_id,
                "entries": current_page_entries
            })
            current_page_idx += 1
            current_page_id = str(item[0]) if item[0] else None
            current_page_entries = []
            continue

        item_type = item[3]

        # Skip non-integer types (section headers, images, videos, etc.)
        if not isinstance(item_type, int) or item_type not in QUESTION_TYPES:
            continue

        label = item[1] if isinstance(item[1], str) else ""
        # Strip HTML tags from label
        label = re.sub(r'<[^>]+>', '', label).strip()

        sub_items = item[4] if len(item) > 4 and isinstance(item[4], list) else []

        if item_type == 7:
            # Grid / Matrix: multiple entry IDs, one per row
            # Columns (scale options) are the same for all rows
            # sub_items is a list of groups: each group[0]=entry_id, group[1]=row_labels (list)
            # The column options are stored differently depending on the form
            # Typically: sub_items[i] = [entry_id, [[col_text,...]], ...]
            # Rows are the sub-questions, columns are the rating options

            # Find column options from the first sub-item
            col_options = []
            if sub_items and len(sub_items[0]) > 1 and isinstance(sub_items[0][1], list):
                for opt in sub_items[0][1]:
                    if isinstance(opt, list) and opt:
                        opt_text = opt[0]
                        if isinstance(opt_text, str) and opt_text:
                            col_options.append(opt_text)

            for group in sub_items:
                if not isinstance(group, list) or len(group) < 2:
                    continue
                entry_id = group[0]
                if not entry_id:
                    continue

                # Row label is in group[3] or similar
                row_label = ""
                if len(group) > 3 and isinstance(group[3], list):
                    row_label_raw = group[3][0] if group[3] else ""
                    row_label = re.sub(r'<[^>]+>', '', str(row_label_raw)).strip()

                row_label_clean = row_label if row_label else ""
                field_label = f"{label} — {row_label_clean}" if row_label_clean else label
                weights = [1 / len(col_options)] * len(col_options) if col_options else []

                key = f"entry.{entry_id}"
                form_config[key] = {
                    "label": field_label,
                    "type": "choice",
                    "options": col_options,
                    "weights": weights,
                    "group": label  # parent grid question title
                }
                question_order.append(key)
                current_page_entries.append(key)

        elif item_type in (2, 3):
            # Radio / Dropdown
            if not sub_items or not isinstance(sub_items[0], list):
                continue
            group = sub_items[0]
            entry_id = group[0]
            if not entry_id:
                continue

            options_raw = group[1] if len(group) > 1 and isinstance(group[1], list) else []
            options = []
            option_targets = {}
            for opt in options_raw:
                if isinstance(opt, list) and opt:
                    opt_text = opt[0]
                    if isinstance(opt_text, str) and opt_text:
                        options.append(opt_text)
                        if len(opt) > 2:
                            target = opt[2]
                            if target == -2 or target == -1 or (isinstance(target, int) and target > 0) or (isinstance(target, str) and target.isdigit()):
                                option_targets[opt_text] = str(target)

            weights = [1 / len(options)] * len(options) if options else []
            key = f"entry.{entry_id}"
            form_config[key] = {
                "label": label,
                "type": "choice",
                "options": options,
                "weights": weights,
                "group": None,
                "optionTargets": option_targets
            }
            question_order.append(key)
            current_page_entries.append(key)

        elif item_type == 4:
            # Checkbox
            if not sub_items or not isinstance(sub_items[0], list):
                continue
            group = sub_items[0]
            entry_id = group[0]
            if not entry_id:
                continue

            options_raw = group[1] if len(group) > 1 and isinstance(group[1], list) else []
            options = []
            for opt in options_raw:
                if isinstance(opt, list) and opt:
                    opt_text = opt[0]
                    if isinstance(opt_text, str) and opt_text:
                        options.append(opt_text)

            weights = [1 / len(options)] * len(options) if options else []
            key = f"entry.{entry_id}"
            form_config[key] = {
                "label": label,
                "type": "checkbox",
                "options": options,
                "weights": weights,
                "group": None
            }
            question_order.append(key)
            current_page_entries.append(key)

        elif item_type in (0, 1):
            # Short text / Paragraph
            if not sub_items or not isinstance(sub_items[0], list):
                continue
            entry_id = sub_items[0][0]
            if not entry_id:
                continue
            key = f"entry.{entry_id}"
            form_config[key] = {
                "label": label,
                "type": "text",
                "options": [],
                "weights": [],
                "group": None
            }
            question_order.append(key)
            current_page_entries.append(key)

        elif item_type == 9:
            # Date
            if not sub_items or not isinstance(sub_items[0], list):
                continue
            entry_id = sub_items[0][0]
            if not entry_id:
                continue
            key = f"entry.{entry_id}"
            form_config[key] = {
                "label": label,
                "type": "date",
                "options": [],
                "weights": [],
                "group": None
            }
            question_order.append(key)
            current_page_entries.append(key)

        elif item_type == 10:
            # Time
            if not sub_items or not isinstance(sub_items[0], list):
                continue
            entry_id = sub_items[0][0]
            if not entry_id:
                continue
            key = f"entry.{entry_id}"
            form_config[key] = {
                "label": label,
                "type": "time",
                "options": [],
                "weights": [],
                "group": None
            }
            question_order.append(key)
            current_page_entries.append(key)

        elif item_type == 5:
            # Linear scale — treat as choice
            if not sub_items or not isinstance(sub_items[0], list):
                continue
            group = sub_items[0]
            entry_id = group[0]
            if not entry_id:
                continue
            options_raw = group[1] if len(group) > 1 and isinstance(group[1], list) else []
            options = []
            for opt in options_raw:
                if isinstance(opt, list) and opt:
                    opt_text = opt[0]
                    if isinstance(opt_text, str) and opt_text:
                        options.append(opt_text)

            weights = [1 / len(options)] * len(options) if options else []
            key = f"entry.{entry_id}"
            form_config[key] = {
                "label": label,
                "type": "choice",
                "options": options,
                "weights": weights,
                "group": None
            }
            question_order.append(key)
            current_page_entries.append(key)

    question_count = len(form_config)
    print(f"[NativeParser] Parsed {question_count} questions successfully")

    if question_count == 0:
        print("[NativeParser] No questions found, will fall back to AI")
        return None

    # Append final page
    form_routing.append({
        "page_index": current_page_idx,
        "page_id": current_page_id,
        "entries": current_page_entries
    })

    return {
        "submitUrl": submit_url,
        "formConfig": form_config,
        "questionOrder": question_order,
        "hiddenFields": hidden_fields,
        "formRouting": form_routing
    }


def _extract_fb_data(html):
    """Extract FB_PUBLIC_LOAD_DATA_ + form action + hidden inputs — much smaller than full HTML."""
    parts = []

    # 1. FB_PUBLIC_LOAD_DATA_ — contains all questions, IDs, options
    raw = _extract_fb_raw(html)
    if raw:
        parts.append('FB_PUBLIC_LOAD_DATA_ = ' + raw)
    else:
        parts.append(_clip_html(html))

    # 2. Form action URL
    action = re.search(r'action="([^"]*formResponse[^"]*)"', html)
    if action:
        parts.append(f'<form action="{action.group(1)}">')

    # 3. Hidden inputs
    hidden = re.findall(r'<input[^>]+type=["\']hidden["\'][^>]*>', html, re.IGNORECASE)
    parts.extend(hidden[:30])

    # 4. Email input
    email_input = re.search(r'<input[^>]+name=["\']emailAddress["\'][^>]*>', html, re.IGNORECASE)
    if email_input:
        parts.append(email_input.group(0))

    result = '\n'.join(parts)
    print(f"[AI Parser] Extracted payload: {len(result)} chars (original: {len(html)} chars)")
    return result if result.strip() else _clip_html(html)


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
        'pageHistory': r'name="pageHistory"\s+value="([^"]*)"',
        'draftResponse': r'name="draftResponse"\s+value="([^"]*)"',
        'submissionTimestamp': r'name="submissionTimestamp"\s+value="([^"]*)"',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, html)
        if match:
            fields[key] = match.group(1)
    hidden_inputs = re.findall(r'<input\s+type="hidden"\s+name="([^"]+)"\s+value="([^"]*)"', html)
    for name, value in hidden_inputs:
        if name in ('fbzx', 'fvv', 'pageHistory', 'draftResponse', 'submissionTimestamp') or name.startswith('entry.'):
            fields[name] = value
    return fields


def _merge_hidden(data, html):
    regex_hidden = _extract_hidden_fields_regex(html)
    if 'hiddenFields' not in data:
        data['hiddenFields'] = {}
    for k, v in regex_hidden.items():
        if k not in data['hiddenFields']:
            data['hiddenFields'][k] = v
    return data

# ── AI Providers ──────────────────────────────────────────────────────────────

def _parse_with_gemini(html, api_key):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = PROMPT_TEMPLATE.format(html_source=_extract_fb_data(html))
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
    prompt = PROMPT_TEMPLATE.format(html_source=_extract_fb_data(html))
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
    prompt = PROMPT_TEMPLATE.format(html_source=_extract_fb_data(html))
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

    # ── Step 1: Try native Python parser first (fast, no AI cost, handles ALL pages) ──
    print("[AI Parser] Attempting native Python parse of FB_PUBLIC_LOAD_DATA_...")
    native_result = _parse_native(html_source)
    if native_result and native_result.get("formConfig"):
        native_result = _merge_hidden(native_result, html_source)
        native_result["_provider"] = "NativeParser"
        print(f"[AI Parser] Native parse succeeded with {len(native_result['formConfig'])} questions.")
        return native_result

    # ── Step 2: Fall back to AI providers ──────────────────────────────────
    print("[AI Parser] Native parse insufficient, falling back to AI...")

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
