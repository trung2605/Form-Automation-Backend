import requests, urllib.request, json, re
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'

session = requests.Session()
r = session.get(url)
html = r.text

fbzx = re.search(r'name="fbzx"\s+value="([^"]+)"', html).group(1)
partial = re.search(r'name="partialResponse"\s+value="([^"]*)"', html)
draft = re.search(r'name="draftResponse"\s+value="([^"]*)"', html)
pageHist = re.search(r'name="pageHistory"\s+value="([^"]*)"', html)
fvv = re.search(r'name="fvv"\s+value="([^"]*)"', html)

post_data = []
post_data.append(('fbzx', fbzx))
if partial: post_data.append(('partialResponse', partial.group(1).replace('&quot;', '"')))
if draft: post_data.append(('draftResponse', draft.group(1).replace('&quot;', '"')))
if pageHist: post_data.append(('pageHistory', pageHist.group(1)))
if fvv: post_data.append(('fvv', fvv.group(1)))
post_data.append(('continue', '1'))
post_data.append(('submissionTimestamp', '-1'))

submit_url = url.replace('viewform', 'formResponse')
print("Submitting Step 0...")
r2 = session.post(submit_url, data=post_data, headers={'Content-Type': 'application/x-www-form-urlencoded', 'Referer': url})

print("Status:", r2.status_code)
if r2.status_code == 200:
    print("Success! Got next page.")
else:
    print("Failed!")
    print(r2.text[:500])
