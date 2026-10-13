import re

def format_inline_code(code_text: str) -> str:
    if not code_text:
        return '``'
    runs = re.findall(r'`+', code_text)
    max_run = max((len(r) for r in runs), default=0)
    fence_len = max_run + 1 if max_run > 0 else 1
    fence = '`' * fence_len
    if code_text.startswith('`') or code_text.endswith('`'):
        return f'{fence} {code_text} {fence}'
    return f'{fence}{code_text}{fence}'

cases = [
    'hello',
    'Test with nested `code` block',
    '`npm install`',
    '`',
    'foo `` bar'
]

for c in cases:
    print(repr(c), '->', repr(format_inline_code(c)))
