import io
import sys
from playwright.sync_api import sync_playwright
import os

from app.browser.extraction import clean_markdown_text, html_to_markdown

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

html_path = os.path.abspath('data/artifacts/ui-chatgpt-1791888941/chatgpt/page-1791889002.html')

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page()
    page.goto(f"file:///{html_path.replace(os.sep, '/')}")
    
    loc = page.locator("[data-markdown-text-style]")
    print("Count:", loc.count())
    if loc.count() > 0:
        val = loc.first.get_attribute("data-markdown-text-style")
        print("Attribute value:", val)
        html = loc.first.inner_html()
        print("HTML length:", len(html))
        md = html_to_markdown(html, provider="chatgpt")
        cleaned_md = clean_markdown_text(md)
        print("Markdown length:", len(cleaned_md))
        print("Markdown snippet:\n", cleaned_md[:300])
        with open("scratch/extracted_answer.md", "w", encoding="utf-8") as f:
            f.write(cleaned_md)
        print("Wrote scratch/extracted_answer.md successfully.")
    browser.close()
