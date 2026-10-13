Here’s a comprehensive Markdown rendering test suite you can copy into ChatGPT to test headings, formatting, lists, tables, code blocks, mathematics, links, images, HTML, and other Markdown features.


Writing


# ChatGPT Markdown Rendering Test Suite

> **Purpose:** Test Markdown syntax, rendering behavior, nested structures, and edge cases in ChatGPT.
>
> **Test coverage:** CommonMark, GitHub Flavored Markdown (GFM), extended Markdown, LaTeX, and selected HTML elements.


---


## 1. Headings


# Heading Level 1


## Heading Level 2


### Heading Level 3


#### Heading Level 4


##### Heading Level 5


###### Heading Level 6


# Heading using Setext syntax


## Another Setext heading


This is a normal paragraph following the headings.


---


## 2. Text Formatting


### Basic Inline Formatting
- Regular text
- **Bold text**
- *Italic text*
- ***Bold and italic text***
- Strikethrough text
- `Inline code`
- Underlined text using HTML
- <mark>Highlighted text using HTML</mark>
- <sub>Subscript text</sub>
- <sup>Superscript text</sup>


### Combined Formatting


This sentence contains **bold text with *****nested italic text*** inside it.


This is *italic text containing *`*inline code*`.


This is **bold text containing **`**code**`** and ****strikethrough**** formatting**.


This is a paragraph with a [link](https://example.com), some **bold text**, and `code` all together.


### Special Characters
- Ampersand: `&` and `&amp;`
- Less than: `<` and `&lt;`
- Greater than: `>` and `&gt;`
- Quotes: `"double"` and `'single'`
- Backslash: `\`
- Pipe: `|`
- Asterisk: `*`
- Underscore: `_`
- Backticks: ```
- Brackets: `[text]`
- Braces: `{text}`


### Unicode and Emoji


English, Tiếng Việt, 中文, 日本語, 한국어, العربية, हिन्दी


😀 😎 🚀 🎯 ✅ ❌ ⚠️ 🔥 💡 🎉


---


## 3. Paragraphs and Line Breaks


This is the first paragraph. It contains enough text to test normal line wrapping, paragraph spacing, and rendering across multiple lines of content.


This is the second paragraph. It should be separated from the first paragraph by a visible amount of vertical spacing.


This line ends with two spaces.
This line should begin on a new line.


This line ends with a backslash.
This line should also begin on a new line.


---


## 4. Horizontal Rules


Content above the first horizontal rule.


---


Content between the first and second horizontal rules.


---


Content between the second and third horizontal rules.


---


Content below the third horizontal rule.


---


## 5. Unordered Lists


### Basic Unordered List
- First item
- Second item
- Third item


### Alternative List Markers
- First item using an asterisk
- Second item using an asterisk
- First item using a plus sign
- Second item using a plus sign


### Nested Unordered Lists
- Level 1 — Item A
    - Level 2 — Item A.1
        - Level 3 — Item A.1.a
            - Level 4 — Item A.1.a.i
    - Level 2 — Item A.2
- Level 1 — Item B
    - Level 2 — Item B.1


### Lists with Rich Content
- **Bold item:** This item includes bold text.
- *Italic item:* This item includes italic text.
- `Code item:` This item includes inline code.
- Item containing a [hyperlink](https://example.com).
- Item containing a paragraph.This is a continuation paragraph inside the same list item.


### Empty Lines Between List Items
- First item
- Second item with an empty line above
- Third item with an empty line above


---


## 6. Ordered Lists


### Basic Numbered List
1. First item
2. Second item
3. Third item
4. Fourth item


### Nested Numbered Lists
1. First main item
    1. First nested item
    2. Second nested item
        1. Third-level item
        2. Another third-level item
2. Second main item
    1. Nested item
    2. Nested item


### Alternative Numbering
1. First item
2. Second item
3. Third item


### Lists Starting from a Specific Number
1. Fifth item
2. Sixth item
3. Seventh item


### Mixed Nested Lists
1. Architecture
    - Frontend
    - Backend
        1. API Gateway
        2. Authentication Service
    - Database
2. Deployment
    - Docker
    - Kubernetes


---


## 7. Task Lists and Checkboxes


### Unchecked Tasks
- [ ] Create a project
- [ ] Configure the environment
- [ ] Write unit tests
- [ ] Deploy the application


### Checked Tasks
- [x] Initialize the repository
- [x] Install dependencies
- [ ] Run integration tests


### Nested Task Lists
- [x] Backend
    - [x] Create API endpoints
    - [x] Add authentication
    - [ ] Add rate limiting
- [ ] Frontend
    - [x] Create layout
    - [ ] Implement API integration
    - [ ] Add error handling


---


## 8. Blockquotes


### Basic Blockquote

> High reliability is essential.


### Multi-Paragraph Blockquote

> This is the first paragraph inside a blockquote.
>
> This is the second paragraph inside the same blockquote.


### Nested Blockquotes

> This is the outer quote.
>
> > This is a nested quote.
> >
> > > This is a third-level nested quote.


### Blockquote with Rich Formatting

> **Important:** Read the documentation carefully.
>
> Use `npm test` to run the tests.
>
> Visit [the official website](https://example.com) for more information.


### Blockquote Containing a List

> Recommended steps:
> 1. Read the requirements.
> 2. Implement the solution.
> 3. Validate the results.


### Blockquote Containing Code

> Example command:
>
> ```bash
> docker compose up -d
> ```


---


## 9. Links and References


### Inline Links
- [Example Website](https://example.com)
- [OpenAI](https://openai.com)
- [Link with a title](https://example.com)
- [Relative link](./README.md)
- [Email link](mailto:test@example.com)
- [Telephone link](tel:+1234567890)


### Autolinks
- Website: [https://example.com](https://example.com)
- Email: [test@example.com](mailto:test@example.com)
- URL with path: [https://example.com/docs/guide](https://example.com/docs/guide)


### Reference-Style Links


Here is a [reference-style link](https://example.com).


Here is another [reference link](https://openai.com).


You can also reuse [reference-one](https://example.com) in another sentence.


### Link Escaping


This should not become a link: `https://example.com`


This is a visible URL with punctuation: [https://example.com](https://example.com).


This is a link to a [page with query parameters](https://example.com/search?q=markdown&page=1).


---


## 10. Images


### Basic Image


### Image with Alt Text


### Image with a Title


### Image Inside a Link


### Images with Different Aspect Ratios


---


## 11. Tables


### Basic Table

| Name | Role | Department |
| --- | --- | --- |
| Alice | Engineer | Platform |
| Bob | Designer | Product |
| Charlie | Manager | Engineering |


### Column Alignment

| Left Aligned | Center Aligned | Right Aligned |
| --- | --- | --- |
| Left | Center | Right |
| Short | Medium | 123.45 |
| Longer text | Centered text | 1,234.56 |


### Table with Four Columns

| Feature | System A | System B | Complexity |
| --- | --- | --- | --- |
| Search | Linear scan | Binary search | (O(\log N)) |
| Sorting | Bubble sort | Merge sort | (O(N \log N)) |
| Storage | File system | Database | Medium |
| Scaling | Vertical | Horizontal | High |


### Table with Rich Formatting

| Component | Description | Status |
| --- | --- | --- |
| **API Gateway** | Routes incoming requests | ✅ Active |
| *Cache Layer* | Improves read performance | ✅ Active |
| `Worker Service` | Processes background jobs | 🟡 Pending |
| Legacy API | Deprecated endpoint | ❌ Removed |


### Table with Long Text

| ID | Description | Expected Result |
| --- | --- | --- |
| TC-001 | Verify that a user can successfully authenticate using valid credentials. | Return HTTP 200 and a valid session token. |
| TC-002 | Verify that an unauthenticated request cannot access protected resources. | Return HTTP 401 Unauthorized. |
| TC-003 | Verify that invalid input is rejected without crashing the server. | Return a structured validation error. |


### Table with Special Characters

| Expression | Meaning |
| --- | --- |
| `a \| b` | Literal pipe character in code |
| `x < y` | Less-than comparison |
| `x > y` | Greater-than comparison |
| `A & B` | Ampersand |
| `N \log N` | Complexity expression |


### Table with Inline Links

| Resource | Link |
| --- | --- |
| Documentation | Read docs |
| Source Code | View repository |
| Support | Contact support |


---


## 12. Inline Code and Code Blocks


### Inline Code


Use `console.log("Hello, World!");` to print a message.


Common commands: `git status`, `npm install`, `docker compose up`, and `pytest`.


Test unusual characters inside code: ``backticks``, `$HOME`, `${variable}`, and `foo_bar`.


### Plain Code Block

```
This is a plain fenced code block.
No language is specified.
Special characters: < > & " '
```


### JavaScript

```javascript
function greet(name) {
  return `Hello, ${name}!`;
}

console.log(greet("World"));
```


### TypeScript

```typescript
interface User {
  id: number;
  name: string;
}

function greet(user: User): string {
  return `Hello, ${user.name}!`;
}

console.log(greet({ id: 1, name: "Alice" }));
```


### Python

```python
from typing import Sequence

def calculate_average(numbers: Sequence[float]) -> float:
    if not numbers:
        raise ValueError("numbers must not be empty")

    return sum(numbers) / len(numbers)

print(calculate_average([10, 20, 30]))
```


### Java

```java
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```


### Kotlin

```kotlin
fun main() {
    val message = "Hello, World!"
    println(message)
}
```


### Go

```go
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
```


### Rust

```rust
fn main() {
    println!("Hello, World!");
}
```


### C

```c
#include <stdio.h>

int main(void) {
    printf("Hello, World!\n");
    return 0;
}
```


### C++

```cpp
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
```


### JavaScript Shell Commands

```bash
#!/usr/bin/env bash

set -euo pipefail

echo "Hello, World!"
node --version
npm --version
```


### SQL

```sql
SELECT
    users.id,
    users.name,
    COUNT(orders.id) AS order_count
FROM users
LEFT JOIN orders
    ON orders.user_id = users.id
GROUP BY users.id, users.name
ORDER BY order_count DESC;
```


### JSON

```json
{
  "name": "markdown-test-suite",
  "version": "1.0.0",
  "enabled": true,
  "tags": ["markdown", "rendering", "testing"],
  "metadata": {
    "author": "ChatGPT",
    "priority": null
  }
}
```


### YAML

```yaml
application:
  name: markdown-test-suite
  version: "1.0.0"

features:
  - headings
  - tables
  - code_blocks

settings:
  enabled: true
  retries: 3
```


### XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<application>
    <name>markdown-test-suite</name>
    <enabled>true</enabled>
    <version>1.0.0</version>
</application>
```


### HTML

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Markdown Test</title>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>Testing HTML code highlighting.</p>
</body>
</html>
```


### Diff

```diff
- const environment = "development";
+ const environment = "production";

  function run() {
-   console.log("Old behavior");
+   console.log("New behavior");
  }
```


### GraphQL

```graphql
query GetUser($id: ID!) {
  user(id: $id) {
    id
    name
    email
  }
}
```


### Nested Code Fences

```markdown
Here is a code fence containing another code fence:
```
console.log("Nested fence");
```
---

## 13. Mathematics and LaTeX

### Inline Mathematics
- Pythagorean theorem: (a^2 + b^2 = c^2)
- Einstein's mass-energy equivalence: (E = mc^2)
- Quadratic formula: (x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a})
- Big-O notation: (O(N \log N))
- Set notation: (x \in \mathbb{R})
- Summation: (\sum_{i=1}^{n} i = \frac{n(n+1)}{2})

### Display Mathematics

The following formula should appear on its own line:

[
E = mc^2
]

### Fractions and Radicals

[
\frac{a+b}{c+d}
]

[
\sqrt{x^2+y^2}
]

[
\sqrt[n]{x}
]

### Superscripts and Subscripts

[
x^2 + y^2 = z^2
]

[
a_n = a_0 + nd
]

[
H_2O,\quad CO_2,\quad x_i^j
]

### Matrices

[
A =
\begin{bmatrix}
1 & 2 & 3 \
4 & 5 & 6 \
7 & 8 & 9
\end{bmatrix}
]

### Piecewise Functions

[
f(x) =
\begin{cases}
x^2 & \text{if } x \geq 0 \
-x & \text{if } x < 0
\end{cases}
]

### Calculus

[
\frac{d}{dx} x^n = nx^{n-1}
]

[
\int_0^1 x^2 , dx = \frac{1}{3}
]

[
\lim_{x \to 0} \frac{\sin x}{x} = 1
]

### Multiple Equations

[
\begin{aligned}
x + y &= 10 \
2x - y &= 5
\end{aligned}
]

### Probability and Statistics

[
P(A \mid B) = \frac{P(A \cap B)}{P(B)}
]

[
\mu = \frac{1}{N}\sum_{i=1}^{N}x_i
]

[
\sigma^2 = \frac{1}{N}\sum_{i=1}^{N}(x_i-\mu)^2
]

### Algorithm Complexity

[
T(N) = 2T\left(\frac{N}{2}\right)+O(N)
]

[
T(N) = O(N\log N)
]

---

## 14. Footnotes

Markdown supports footnotes in some extended renderers.

Here is a sentence with a footnote.

Here is another sentence with a second footnote.

---

## 15. Definition Lists

Definition lists are supported by some Markdown extensions but are not part of standard CommonMark.

Markdown
: A lightweight markup language for creating formatted text.

CommonMark
: A specification that standardizes core Markdown syntax.

GFM
: GitHub Flavored Markdown, an extension of CommonMark.

---

## 16. Details and Summary (HTML)

<details>
<summary>Click to expand this section</summary>

This content is inside a collapsible HTML element.

It can contain normal paragraphs, **bold text**, lists, and code.
```
console.log("Expanded content");
```
- First hidden item
- Second hidden item

</details>

<details open>
<summary>This section is open by default</summary>

This section uses the HTML `open` attribute.

</details>

---

## 17. HTML Elements

### Basic HTML

<div>
  <strong>Strong text</strong>
  <em>Emphasized text</em>
  <code>Code text</code>
</div>

### HTML Paragraph

<p>This paragraph uses an HTML paragraph element.</p>

### HTML Line Break

First HTML line.<br>
Second HTML line.

### HTML Table

<table>
  <thead>
    <tr>
      <th>ID</th>
      <th>Feature</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1</td>
      <td>Rendering</td>
      <td>Passed</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Formatting</td>
      <td>Pending</td>
    </tr>
  </tbody>
</table>

### HTML Semantic Elements

<article>
  <header>
    <h3>Article Title</h3>
    <p>Article metadata</p>
  </header>
  <section>
    <p>This is the main content of the article.</p>
  </section>
  <footer>
    <p>Article footer</p>
  </footer>
</article>

> **Note:** HTML support varies across Markdown renderers. Some elements may be escaped, sanitized, or displayed differently.

---

## 18. Mermaid Diagrams

Mermaid is an extension commonly supported by technical documentation tools. Its rendering is separate from core Markdown.

### Flowchart
```
flowchart TD
    A[Start] --> B{Is input valid?}
    B -->|Yes| C[Process input]
    B -->|No| D[Return error]
    C --> E[Save result]
    D --> F[End]
    E --> F
```
### Sequence Diagram
```
sequenceDiagram
    participant U as User
    participant A as API
    participant D as Database

    U->>A: Send request
    A->>D: Query data
    D-->>A: Return result
    A-->>U: Send response
```
### Class Diagram
```
classDiagram
    class User {
        +String name
        +String email
        +login()
    }

    class Order {
        +String id
        +float total
        +submit()
    }

    User "1" --> "*" Order : places
```
### Entity Relationship Diagram
```
erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ ORDER_ITEM : contains
    PRODUCT ||--o{ ORDER_ITEM : appears_in

    USER {
        int id
        string name
    }

    ORDER {
        int id
        int user_id
    }
```
---
## 19. Escaping and Literal Markdown
### Escape Formatting Symbols
\*This text should not be italicized\*
\*This text should not be bolded\*
\# This should not become a heading
- This should not become a list item
\> This should not become a blockquote
### Show Markdown Source Literally
Use inline code to show the source: `**bold text**`.
Use a fenced code block to display:
```
# Heading
**Bold**
*Italic*
- List item
[Link](https://example.com)
```
### Backslash and Escaping Edge Cases
- `\*` — escaped asterisk
- `\_` — escaped underscore
- `\#` — escaped hash
- `\[` — escaped opening bracket
- `\]` — escaped closing bracket
- `\\` — escaped backslash

---

## 20. Long-Content and Wrapping Tests

### Long Unbroken String

`abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`

### Long URL

[https://example.com/a/very/long/path/used/to/test/url/wrapping/behavior/and/overflow/handling?parameter_one=first_value&parameter_two=second_value&parameter_three=third_value](https://example.com/a/very/long/path/used/to/test/url/wrapping/behavior/and/overflow/handling?parameter_one=first_value&parameter_two=second_value&parameter_three=third_value)

### Wide Table

| Column A | Column B | Column C | Column D | Column E | Column F | Column G | Column H |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | B1 | C1 | D1 | E1 | F1 | G1 | H1 |
| A2 | B2 | C2 | D2 | E2 | F2 | G2 | H2 |
| A3 | B3 | C3 | D3 | E3 | F3 | G3 | H3 |

### Long Paragraph

This paragraph is deliberately longer to test wrapping and readability. A well-behaved Markdown renderer should wrap ordinary text to fit its container while preserving spaces, punctuation, inline formatting, links, and code spans. It should also maintain appropriate spacing between paragraphs and avoid introducing unintended horizontal scrolling for ordinary prose.

---

## 21. Edge Cases and Ambiguous Syntax

### Adjacent Formatting

**Bold***Italic*`Code`Strike

### Punctuation and Emphasis

A word with *emphasis*, punctuation.

A word with **strong emphasis**, punctuation.

A word with strikethrough, punctuation.

### Nested Parentheses in Links

[Example link](https://example.com/path_(section))

### Empty Links and Images

These are intentionally malformed test cases:
- `[](https://example.com)`
- `![Alt text]()`
- `[Missing destination]()`

### Incomplete Formatting
- `**Unclosed bold`
- `*Unclosed italic`
- ``Unclosed code`
- `[Unclosed link](https://example.com`

### Mixed List and Blockquote
- First item
- Second item

> A blockquote inside a list item.It contains two paragraphs.
- Third item

### Code Block Following a List
1. First step
2. Second step
```
print("Code nested inside a list item")
```
3. Third step

---

## 22. Rendering Validation Checklist

Use this checklist when validating the Markdown renderer.

### Core Syntax
- [ ] All six heading levels render correctly.
- [ ] Bold, italic, bold italic, and strikethrough render correctly.
- [ ] Inline code uses distinct formatting.
- [ ] Paragraphs and line breaks have the expected spacing.
- [ ] Horizontal rules render as separators.
- [ ] Special characters and escaped symbols behave correctly.

### Lists and Quotes
- [ ] Unordered lists render correctly.
- [ ] Ordered lists retain the intended sequence.
- [ ] Nested lists preserve indentation.
- [ ] Task-list checkboxes render correctly where supported.
- [ ] Nested blockquotes render correctly.
- [ ] Code blocks inside lists and quotes retain their formatting.

### Links and Images
- [ ] Inline links are clickable.
- [ ] Reference-style links resolve correctly.
- [ ] Autolinks are recognized where supported.
- [ ] Images load and display their alt text when appropriate.
- [ ] Long URLs wrap or overflow gracefully.

### Tables and Code
- [ ] Tables align columns correctly.
- [ ] Left, center, and right alignment work.
- [ ] Wide tables handle overflow gracefully.
- [ ] Code blocks preserve whitespace and indentation.
- [ ] Language-specific syntax highlighting works.
- [ ] Multiline code remains intact when copied.

### Extended Features
- [ ] Inline and display LaTeX render correctly.
- [ ] Footnotes work where supported.
- [ ] Definition lists work where supported.
- [ ] HTML elements render or sanitize predictably.
- [ ] Mermaid diagrams render where supported.
- [ ] Unicode and emoji display correctly.
- [ ] Malformed Markdown does not break surrounding content.

---

## 23. Final Combined Stress Test

# Markdown Stress Test

This section combines several Markdown features into one document.

> **Objective:** Validate mixed-content rendering in a realistic technical note.

The application uses **TypeScript**, *Python*, `PostgreSQL`, and legacy infrastructure.

### Architecture
1. **Client**
    - React
    - TypeScript
2. **Backend**
    - REST API
    - Authentication
3. **Data**
    - PostgreSQL
    - Redis cache

### Complexity Comparison

| Algorithm | Time Complexity | Space Complexity | Recommended |
| --- | --- | --- | --- |
| Linear Search | (O(N)) | (O(1)) | Small datasets |
| Binary Search | (O(\log N)) | (O(1)) | Sorted arrays |
| Merge Sort | (O(N\log N)) | (O(N)) | Stable sorting |
| Quick Sort | Average (O(N\log N)) | Average (O(\log N)) | General-purpose sorting |

### Example Implementation
```
type AlgorithmResult = {
  name: string;
  complexity: string;
  passed: boolean;
};

const results: AlgorithmResult[] = [
  { name: "Linear Search", complexity: "O(N)", passed: true },
  { name: "Binary Search", complexity: "O(log N)", passed: true },
  { name: "Merge Sort", complexity: "O(N log N)", passed: true },
];

for (const result of results) {
  console.log(`${result.name}: ${result.passed ? "PASS" : "FAIL"}`);
}
```
### Mathematical Model

[
T(N) =
\begin{cases}
O(1) & \text{constant time} \
O(\log N) & \text{logarithmic time} \
O(N) & \text{linear time} \
O(N \log N) & \text{linearithmic time} \
O(N^2) & \text{quadratic time}
\end{cases}
]

### Deployment Checklist
- [x] Application implemented
- [x] Unit tests completed
- [ ] Integration tests completed
- [ ] Performance testing completed
- [ ] Production deployment completed

> **Final note:** Markdown implementations differ. CommonMark defines the core syntax, while GFM and other renderers add features such as task lists, tables, or strikethrough. LaTeX, Mermaid, HTML, and footnotes depend on additional renderer support.

**End of Markdown Rendering Test Suite.**

Testing tip: Run this document in ChatGPT and check whether every section renders as expected. Features such as LaTeX, tables, task lists, HTML, and Mermaid are especially useful for identifying differences between Markdown renderers.
```