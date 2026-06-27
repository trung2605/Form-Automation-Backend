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

fbzx = re.search(r'name="fbzx"\s+value="([^"]+)"', html).group(1)

post_data = []
post_data.append(('fbzx', fbzx))
post_data.append(('partialResponse', f'[null,null,"{fbzx}"]'))
post_data.append(('draftResponse', f'[,,,"{fbzx}"]'))
post_data.append(('pageHistory', '0,1,2,3,4'))
post_data.append(('fvv', '0'))

for k, v in response_data.items():
    post_data.append((k, v))

r = requests.post(res['submitUrl'], data=post_data, headers={'Content-Type': 'application/x-www-form-urlencoded', 'Referer': url})
print("Status:", r.status_code)
if r.status_code != 200:
    print(r.text[:500])
