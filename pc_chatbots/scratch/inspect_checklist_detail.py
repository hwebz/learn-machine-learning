with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    h = f.read()

import re

idx = h.find('Compatibility Checklist')
print("Found Compatibility Checklist at:", idx)
sub = h[idx - 100:idx + 5000]
print("Section 18 start:")
print(sub[:2000])

# Check how buttons or checkboxes are defined in this section
buttons = re.findall(r'<button[^>]*role="checkbox"[^>]*>', h)
print("Role checkbox buttons count in entire html:", len(buttons))
if buttons:
    print("Sample checkbox button:", buttons[0])
