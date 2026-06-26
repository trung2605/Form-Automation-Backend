import urllib.request, json, re
url='https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'
html=urllib.request.urlopen(url).read().decode('utf-8')
raw=re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[[\s\S]*?\]);\s*</script>', html).group(1)
items=json.loads(raw)[1][1]
with open('pages.txt', 'w', encoding='utf-8') as f:
    for i in items:
        if i[3] == 8:
            f.write(f"PageBreak ID: {i[0]} Title: {i[1]}\n")
