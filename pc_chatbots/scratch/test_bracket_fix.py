import re

text = "using the `\\[` and `\\]` display-math delimiters.\n\n`\\[\nE = mc^2\n\\]`"

# Pattern: Must start with `\[, not contain backtick, contain at least one newline, end with \]`
pattern = re.compile(r'`\\\[([^`\r\n]*[\r\n][^`]*?)\\\]`')

res = pattern.sub(lambda m: f"\n\n```latex\n\\[\n{m.group(1).strip()}\n\\]\n```\n\n", text)
print("Result:")
print(res)
