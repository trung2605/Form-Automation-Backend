import urllib.request, json, re

url = 'https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'
html = urllib.request.urlopen(url).read().decode('utf-8')

raw = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[[\s\S]*?\]);\s*</script>', html).group(1)
data = json.loads(raw)
items = data[1][1]

pages = []
current_page_idx = 0
current_page_entries = []

for idx, item in enumerate(items):
    if item[3] == 8:
        pages.append(current_page_entries)
        current_page_idx += 1
        current_page_entries = []
    elif item[3] in (0, 1, 2, 3, 4, 5, 9, 10):
        entry_id = item[4][0][0]
        # Check for branch options
        options = []
        if len(item[4][0]) > 1:
            opts = item[4][0][1]
            if opts:
                for opt in opts:
                    # opt is usually [value, unknown, unknown, [target_page, ...]]
                    # or [value, unknown, unknown, unknown, target_page]
                    target = None
                    if len(opt) > 4:
                        target = opt[4]
                    options.append({"value": opt[0], "target": target})
                    
        current_page_entries.append({
            "id": entry_id,
            "title": item[1],
            "options": options
        })

pages.append(current_page_entries)

with open('branching.json', 'w', encoding='utf-8') as f:
    json.dump(pages, f, ensure_ascii=False, indent=2)
