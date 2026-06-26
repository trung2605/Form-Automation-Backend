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

session = requests.Session()
html_resp = session.get(url).text

for step in range(10):
    fbzx = re.search(r'name="fbzx"\s+value="([^"]+)"', html_resp).group(1)
    partial = re.search(r'name="partialResponse"\s+value="([^"]*)"', html_resp)
    draft = re.search(r'name="draftResponse"\s+value="([^"]*)"', html_resp)
    pageHist = re.search(r'name="pageHistory"\s+value="([^"]*)"', html_resp)
    
    post_data = []
    post_data.append(('fbzx', fbzx))
    if partial: post_data.append(('partialResponse', partial.group(1).replace('&quot;', '"')))
    if draft: post_data.append(('draftResponse', draft.group(1).replace('&quot;', '"')))
    if pageHist: post_data.append(('pageHistory', pageHist.group(1)))
    post_data.append(('fvv', '1'))
    
    # Extract entries present on the current page
    # Look for name="entry.12345"
    current_page_entries = set(re.findall(r'name="(entry\.\d+)"', html_resp))
    
    for k, v in response_data.items():
        if k in current_page_entries:
            post_data.append((k, v))
            
    print(f"Step {step} submitting with pageHistory={pageHist.group(1) if pageHist else None}, {len(current_page_entries)} entries")
    r = session.post(res['submitUrl'], data=post_data, headers={'Content-Type': 'application/x-www-form-urlencoded', 'Referer': url})
    
    print("Status:", r.status_code)
    html_resp = r.text
    if "Your response has been recorded" in html_resp or "Câu trả lời của bạn đã được ghi lại" in html_resp:
        print("Success!")
        break
    if r.status_code != 200:
        print("Failed!")
        break
