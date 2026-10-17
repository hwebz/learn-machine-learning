import json
from bs4 import BeautifulSoup

d = json.load(open('scratch/minimax_thinking_probe.json', encoding='utf-8'))
html = d['full_html']

soup = BeautifulSoup(html, 'html.parser')

detail = soup.find(attrs={'data-testid': 'turn-process-detail'})
print("Detail found:", detail is not None)

if detail:
    # Let's inspect children of detail or archived/trailing blocks
    steps = []
    # Find all direct or nested activity groups and markdown blocks inside turn-process-detail
    # Notice: activity-group might be siblings with text blocks
    # Or activity-group is followed by matrix-markdown
    children = list(detail.children)
    print("Direct children count:", len(children))
    
    # Let's find all activity-group elements inside detail
    groups = detail.find_all(attrs={'data-testid': 'activity-group'})
    print("Activity groups in detail:", len(groups))
    for i, g in enumerate(groups):
        # Title
        summary = g.find(attrs={'data-testid': 'activity-group-header-summary'})
        title = summary.get('title') if summary else None
        if not title:
            header = g.find(attrs={'data-testid': 'activity-group-header'})
            title = header.get('aria-label') if header else None
        if not title:
            shimmer = g.find(class_='shimmer-text__label-text')
            title = shimmer.get_text(strip=True) if shimmer else None
            
        # Description: check inside g or following sibling
        desc = ""
        # 1. inside g
        inner_md = g.find(class_=lambda c: c and ('matrix-markdown' in c or 'mavis-markdown-blocks' in c))
        if inner_md:
            desc = inner_md.get_text(separator='\n', strip=True)
        else:
            # Check following siblings until next activity-group
            sib = g.next_sibling
            while sib:
                if getattr(sib, 'attrs', {}).get('data-testid') == 'activity-group':
                    break
                if hasattr(sib, 'find'):
                    md = sib.find(class_=lambda c: c and ('matrix-markdown' in c or 'mavis-markdown-blocks' in c))
                    if md:
                        desc = (desc + '\n\n' + md.get_text(separator='\n', strip=True)).strip()
                    elif sib.name == 'p':
                        desc = (desc + '\n\n' + sib.get_text(separator='\n', strip=True)).strip()
                sib = sib.next_sibling
        
        steps.append({'index': i, 'title': title, 'description': desc})
        
    print("Parsed steps:")
    for s in steps:
        print(f"[{s['index']}] Title: {s['title']}")
        print(f"    Description: {s['description']}\n")
