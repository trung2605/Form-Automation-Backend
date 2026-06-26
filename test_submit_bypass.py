import requests, urllib.request, json, re
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'
html = urllib.request.urlopen(url).read().decode('utf-8')

res = requests.post('http://127.0.0.1:5000/api/analyze-form', json={'htmlSource': html}).json()

fbzx = re.search(r'name="fbzx"\s+value="([^"]+)"', html).group(1)

post_data = []
post_data.append(('fbzx', fbzx))
post_data.append(('draftResponse', f'[null,null,"{fbzx}"]'))
post_data.append(('pageHistory', '0'))
post_data.append(('fvv', '1'))
post_data.append(('submissionTimestamp', '-1'))

# Add only the fields from page 1
# From earlier, page 1 has 5 entries (actually page 2, since page 0 has 0 entries)
# Wait, page 0 has 0 entries. Page 1 has 5 entries.
# Let's just submit the first section's questions!
# Actually, the user's form:
# 1002380681, 1308751871, 1973638413, 482028411, 95443666
post_data.append(('entry.1973638413', 'Nam'))
post_data.append(('entry.1308751871', 'Nhân viên văn phòng'))
post_data.append(('entry.482028411', '> 10 triệu VNĐ'))
post_data.append(('entry.1002380681', 'Dưới 18 tuổi'))
post_data.append(('entry.618847587', 'Võ Trần Nhật Diệu'))
post_data.append(('entry.95443666', 'Không')) # Choose Không!

r = requests.post(res['submitUrl'], data=post_data, headers={'Content-Type': 'application/x-www-form-urlencoded', 'Referer': url})
print("Status:", r.status_code)
if r.status_code != 200:
    print(r.text[:500])
else:
    print("SUCCESS!")
