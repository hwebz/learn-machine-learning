import json
import re

d = json.load(open('scratch/minimax_thinking_probe.json', 'r', encoding='utf-8'))
html = d['full_html']

print("Full HTML length:", len(html))

# 1. All data-testid attributes
testids = set(re.findall(r'data-testid=[\'"]([^\'"]+)[\'"]', html))
print("\nUnique data-testid attributes:")
for t in sorted(testids):
    print(" -", t)

# 2. Look for copy buttons
copy_matches = re.findall(r'<[^>]+(?:aria-label=[\'"][^\'"]*copy[^\'"]*[\'"]|class=[\'"][^\'"]*copy[^\'"]*[\'"])[^>]*>', html, re.I)
print("\nCopy buttons found:", len(copy_matches))
for c in copy_matches[:5]:
    print("  *", c)

# 3. Look for turn-process-disclosure or thinking elements
print("\nThinking / Disclosure matches:")
disclosure_matches = re.findall(r'<section[^>]*data-testid=[\'"]turn-process-disclosure[\'"][^>]*>.*?</section>', html, re.DOTALL)
print(f"Found {len(disclosure_matches)} turn-process-disclosure sections")
for i, dm in enumerate(disclosure_matches):
    print(f"--- Disclosure {i} (len {len(dm)}) ---")
    headers = re.findall(r'data-testid=[\'"]activity-group-header-summary[\'"][^>]*title=[\'"]([^\'"]+)[\'"]', dm)
    print("Activity summaries:", headers)
    texts = re.findall(r'<div class=[\'"][^\'"]*mavis-markdown-blocks[^\'"]*[\'"][^>]*>(.*?)</div>', dm, re.DOTALL)
    cleaned_texts = [re.sub(r'<[^>]+>', '', t).strip() for t in texts]
    print("Disclosure texts:", cleaned_texts)

# 4. Look for assistant markdown response outside turn-process-disclosure
asst_match = re.search(r'<div[^>]*data-message-role=[\'"]assistant[\'"][^>]*>(.*)', html, re.DOTALL)
if asst_match:
    asst_inner = asst_match.group(1)
    print("\nAssistant inner length:", len(asst_inner))
    # Extract action buttons inside assistant
    actions = re.findall(r'<div[^>]*data-testid=[\'"]message-actions[\'"][^>]*>.*?</div>\s*</div>\s*</div>', asst_inner, re.DOTALL)
    print("Action matches count:", len(actions))
    if actions:
        print("Message actions HTML:", actions[0][:800])
    else:
        # Check anything with aria-label Copy
        all_copies = re.findall(r'<[^>]+aria-label=[\'"]Copy[\'"][^>]*>', asst_inner)
        print("All Copy in asst_inner:", all_copies)
