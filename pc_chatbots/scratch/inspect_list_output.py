with open('scratch/current_test_answer.md', encoding='utf-8') as f:
    c = f.read()

import re

m = re.search(r'Design the system', c)
if m:
    print(c[m.start() - 200:m.start() + 600])
else:
    print("Not found in current_test_answer.md")
