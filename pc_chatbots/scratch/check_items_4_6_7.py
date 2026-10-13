with open('scratch/test_conversion_output.md', encoding='utf-8') as f:
    md = f.read()

import re

# Check item 4: Column alignment table
idx4 = md.find('Column alignment')
print("--- Column alignment table ---")
print(md[idx4:idx4+400])

# Check item 6: Horizontal rules
idx6 = md.find('Horizontal Rules')
print("\n--- Horizontal Rules ---")
print(md[idx6:idx6+400])

# Check item 7: Footnote
idx7 = md.find('Footnote')
print("\n--- Footnotes ---")
print(md[idx7:idx7+400])
