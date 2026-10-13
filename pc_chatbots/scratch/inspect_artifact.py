import io
import sys
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('data/artifacts/ui-chatgpt-1791888941/chatgpt/page-1791889002.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

print('Title:', soup.title.string if soup.title else None)

# Check assistant message
assistant_msgs = soup.select('div[data-message-author-role="assistant"]')
print('Assistant msgs count:', len(assistant_msgs))
if assistant_msgs:
    print('Assistant text length:', len(assistant_msgs[-1].get_text()))
    print('Assistant snippet:', repr(assistant_msgs[-1].get_text()[:200]))

# Check done indicator buttons
copy_btns = soup.select('button[aria-label*="Copy"], button[data-testid="copy-turn-action-button"]')
print('Copy buttons count:', len(copy_btns))

# Check stop button
stop_btns = soup.select('button[data-testid="stop-button"], button[aria-label*="Stop"]')
print('Stop buttons count:', len(stop_btns))
