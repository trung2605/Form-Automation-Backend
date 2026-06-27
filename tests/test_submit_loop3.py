import requests, urllib.request, json, re
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'
html = urllib.request.urlopen(url).read().decode('utf-8')

res = requests.post('http://127.0.0.1:5000/api/analyze-form', json={'htmlSource': html}).json()
from app import GoogleFormFiller
formConfig = res['formConfig']
formConfig['entry.95443666']['weights'] = [1.0, 0.0]

submitter = GoogleFormFiller(url, res['submitUrl'], emails=[], hidden_fields=res['hiddenFields'])
response_data = submitter.generate_response_data(formConfig)

# Parse pages from FB_PUBLIC_LOAD_DATA_
raw = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[[\s\S]*?\]);\s*</script>', html).group(1)
data = json.loads(raw)
items = data[1][1]

pages = []
current_page_entries = []
for item in items:
    if isinstance(item, list) and len(item) >= 4:
        if item[3] == 8: # Page break
            pages.append(current_page_entries)
            current_page_entries = []
        else:
            # Check if it has an entry ID
            if item[3] in (0, 1, 2, 3, 4, 5, 9, 10):
                if len(item) > 4 and isinstance(item[4], list) and len(item[4]) > 0:
                    entry_id = item[4][0][0]
                    if entry_id:
                        current_page_entries.append(f"entry.{entry_id}")
            elif item[3] == 7: # Grid
                if len(item) > 4 and isinstance(item[4], list):
                    for group in item[4]:
                        if isinstance(group, list) and len(group) > 0 and group[0]:
                            current_page_entries.append(f"entry.{group[0]}")
pages.append(current_page_entries)

print(f"Parsed {len(pages)} pages: {[len(p) for p in pages]}")

session = requests.Session()
html_resp = session.get(url).text

for step, page_entries in enumerate(pages):
    fbzx = re.search(r'name="fbzx"\s+value="([^"]+)"', html_resp)
    partial = re.search(r'name="partialResponse"\s+value="([^"]*)"', html_resp)
    draft = re.search(r'name="draftResponse"\s+value="([^"]*)"', html_resp)
    pageHist = re.search(r'name="pageHistory"\s+value="([^"]*)"', html_resp)
    
    if not pageHist:
        print("Done early?")
        break

    post_data = []
    if fbzx: post_data.append(('fbzx', fbzx.group(1)))
    if partial: post_data.append(('partialResponse', partial.group(1).replace('&quot;', '"')))
    if draft: post_data.append(('draftResponse', draft.group(1).replace('&quot;', '"')))
    post_data.append(('pageHistory', pageHist.group(1)))
    post_data.append(('fvv', '1'))
    post_data.append(('continue', '1'))
    
    timestamp = re.search(r'name="submissionTimestamp"\s+value="([^"]*)"', html_resp)
    if timestamp: post_data.append(('submissionTimestamp', timestamp.group(1)))
    
    for k, v in response_data.items():
        if k in page_entries:
            # Handle multiple selections for checkboxes
            if isinstance(v, list):
                for item_val in v:
                    post_data.append((k, item_val))
            else:
                post_data.append((k, v))
            
    print(f"Step {step} submitting {len(page_entries)} entries")
    r = session.post(res['submitUrl'], data=post_data, headers={'Content-Type': 'application/x-www-form-urlencoded', 'Referer': url})
    
    html_resp = r.text
    if "Your response has been recorded" in html_resp or "Câu trả lời của bạn đã được ghi lại" in html_resp or r.status_code != 200:
        print("Final Status:", r.status_code)
        break

print("All done!")
