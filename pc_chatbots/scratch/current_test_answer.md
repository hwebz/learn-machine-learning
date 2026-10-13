# Complete Markdown Rendering Test Suite for ChatGPT


This document covers the major Markdown features supported by common Markdown renderers, including GitHub Flavored Markdown (GFM), code syntax highlighting, LaTeX, tables, and extended features.


Use it as a visual regression test to check formatting, layout, syntax highlighting, mathematical notation, and nested components in ChatGPT.


# 1. Headings


# Heading Level 1


## Heading Level 2


### Heading Level 3


#### Heading Level 4


#### Heading Level 5


#### Heading Level 6


# 2. Text Formatting


## Basic formatting

- Regular text


- Bold text


- Italic text


- Bold and italic text


- Strikethrough text


- `Inline code`


## Combined formatting


This sentence contains bold text with nested italic text inside it.


This sentence contains `inline_code()` and important information.


This sentence contains outdated information and its replacement.


A technical identifier: `user.get_profile(user_id=123)`.


## Special characters


Symbols: © ® ™ € £ ¥ § ¶ † ‡ • … — – ± × ÷ ≠ ≤ ≥ ∞ √ ∑ ∏ ∂ ∇


Escaped Markdown characters: *not italic*, *not bold*, `not code`, # not a heading.


# 3. Paragraphs and Line Breaks


This is the first paragraph. It contains ordinary text to test line wrapping across the available content width. The goal is to check readability on both wide and narrow screens.


This is the second paragraph, separated by a blank line.


This is the first line.
This is the second line, separated by a hard line break.


This is the third line, separated by another hard line break.


# 4. Lists


## Unordered list

- First-level item A


- First-level item B


- First-level item C


## Ordered list

1. First step


2. Second step


3. Third step


4. Fourth step


## Nested unordered list

- Frontend

  - React

    - Components


    - Hooks


    - Context


  - Vue


  - Angular


- Backend

  - REST API


  - GraphQL


  - gRPC


- Infrastructure

  - Docker


  - Kubernetes


## Nested ordered list

1. Design the system

  1. Identify requirements


  2. Define interfaces


  3. Review constraints


2. Implement the system

  1. Write code


  2. Write tests


3. Deploy the system


## Mixed list

1. Application

  - Frontend


  - Backend

    - API Gateway


    - Business Services


2. Database

  - PostgreSQL


  - Redis


3. Infrastructure

  - Docker


  - Kubernetes


## Task list / checkboxes

- Initialize the repository


- Configure the development environment


- Implement authentication


- Add unit tests


- Deploy to production


## Task list with nested items

- Backend

  - Create API


  - Configure database


  - Add monitoring


- Frontend

  - Create components


  - Integrate API


# 5. Blockquotes

> High reliability is essential.

> This is a multi-line quotation.
>
> The second paragraph belongs to the same blockquote.


## Nested blockquotes

> Level 1 quotation
>
> > Level 2 quotation
> >
> > > Level 3 quotation


## Blockquote with formatting

> Important: Always validate external input.
>
> Use `try/catch` to handle expected failures.
>
> See the [official documentation](https://www.markdownguide.org/) for more information.


# 6. Links


## Inline links


[OpenAI](https://openai.com/)


[GitHub](https://github.com/)


[Markdown Guide](https://www.markdownguide.org/)


## Automatic links


[https://www.example.com](https://www.example.com)


[https://github.com](https://github.com)


## Email links


Contact support


## Reference-style links


This paragraph references [OpenAI](https://openai.com/) and the [Markdown Guide](https://www.markdownguide.org/).


## Link with inline formatting


Read the [official API documentation](https://platform.openai.com/docs) for implementation details.


# 7. Images


## Basic image


Figure 1. An image with alternative text and a caption.


## Image syntax


```markdown
![Alternative text](https://example.com/image.png)
![Alternative text](https://example.com/image.png "Image title")
```


## Linked image


```markdown
[![Image description](https://example.com/image.png)](https://example.com)
```


Note: Remote images depend on network access and the renderer's image-loading policies.


# 8. Tables


## Basic table


| ID | Name | Role | Active |
| --- | --- | --- | --- |
| 1 | Alice | Engineer | Yes |
| 2 | Bob | Designer | No |
| 3 | Charlie | Manager | Yes |
| 4 | Diana | Analyst | Yes |


## Column alignment


| Left aligned | Center aligned | Right aligned |
| --- | --- | --- |
| Apple | Banana | 100 |
| Orange | Grape | 250 |
| Mango | Pineapple | 500 |


## Technical comparison table


| Feature | System A | System B | Complexity |
| --- | --- | --- | --- |
| Search | Linear search | Binary search | $O(N)$ vs. $O(\log N)$ |
| Sorting | Bubble sort | Merge sort | $O(N^2)$ vs. $O(N \log N)$ |
| Storage | Array | Hash table | $O(N)$ |
| Lookup | Sequential | Indexed | $O(N)$ vs. $O(1)$ average |


## Table with formatted content


| Component | Description | Status |
| --- | --- | --- |
| API Gateway | Routes incoming requests | ✅ Complete |
| Authentication | Validates user credentials | 🔄 In progress |
| `CacheService` | Stores frequently accessed data | ⏳ Pending |
| Legacy API | Replaced by v2 | ❌ Deprecated |


## Table with special characters


| Expression | Value | Notes |
| --- | --- | --- |
| $x^2$ | 25 | Mathematical notation |
| `a \\| b` | Bitwise OR | Escaped pipe character |
| A & B | Combined | Special character handling |
| $N \log N$ | Growth rate | Complexity notation |


# 9. Inline Code and Code Blocks


## Inline code


Use `console.log("Hello, World!")` to print a message.


Call `GET /api/v1/users` to retrieve users.


The configuration key is `database.connection.timeout`.


## Plain code block


```code
This is a plain code block.
No programming language is specified.
```


## JavaScript


```javascript
function greet(name) {
  return `Hello, ${name}!`;
}

console.log(greet("World"));
```


## TypeScript


```typescript
interface User {
  id: number;
  name: string;
  email?: string;
}

function greet(user: User): string {
  return `Hello, ${user.name}!`;
}

const user: User = {
  id: 1,
  name: "Alice",
};

console.log(greet(user));
```


## Python


```python
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str

def greet(user: User) -> str:
    return f"Hello, {user.name}!"

if __name__ == "__main__":
    user = User(id=1, name="Alice")
    print(greet(user))
```


## Java


```java
public class Main {
    public static void main(String[] args) {
        String message = "Hello, World!";
        System.out.println(message);
    }
}
```


## Kotlin


```kotlin
fun main() {
    val message = "Hello, World!"
    println(message)
}
```


## Go


```go
package main

import "fmt"

func main() {
    message := "Hello, World!"
    fmt.Println(message)
}
```


## Rust


```rust
fn main() {
    let message = "Hello, World!";
    println!("{}", message);
}
```


## C


```c
#include <stdio.h>

int main(void) {
    printf("Hello, World!\n");
    return 0;
}
```


## C++


```c++
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
```


## C#


```c#
using System;

class Program {
    static void Main() {
        Console.WriteLine("Hello, World!");
    }
}
```


## SQL


```sql
SELECT
    u.id,
    u.name,
    COUNT(o.id) AS order_count
FROM users AS u
LEFT JOIN orders AS o
    ON o.user_id = u.id
GROUP BY u.id, u.name
ORDER BY order_count DESC;
```


## Bash


```bash
#!/usr/bin/env bash

set -euo pipefail

APP_NAME="markdown-test"

echo "Starting ${APP_NAME}..."

if [[ -d "./src" ]]; then
    echo "Source directory exists."
else
    echo "Source directory not found."
fi
```


## JSON


```json
{
  "application": {
    "name": "markdown-test",
    "version": "1.0.0"
  },
  "features": [
    "headings",
    "tables",
    "code-blocks",
    "math"
  ],
  "enabled": true,
  "retryCount": 3
}
```


## YAML


```yaml
application:
  name: markdown-test
  version: "1.0.0"

server:
  host: localhost
  port: 8080

features:
  - markdown
  - syntax-highlighting
  - latex

enabled: true
```


## HTML


```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Markdown Test</title>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>Testing HTML syntax highlighting.</p>
</body>
</html>
```


## Diff


```diff
 function greet(name) {
-  return "Hello!";
+  return `Hello, ${name}!`;
 }
```


# 10. Mathematical Expressions — LaTeX


## Inline math


The Pythagorean theorem is $a^2 + b^2 = c^2$.


Einstein's equation is $E = mc^2$.


The time complexity is $O(N \log N)$.


A probability density function satisfies $\int_{-\infty}^{\infty} f(x)\,dx = 1$.


## Display math: Algebra


$$
(a+b)^2 = a^2 + 2ab + b^2
$$


$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$


## Calculus


$$
\frac{d}{dx}x^n = nx^{n-1}
$$


$$
\int x^n\,dx = \frac{x^{n+1}}{n+1}+C,
\qquad n \ne -1
$$


$$
\lim_{x \to 0}\frac{\sin x}{x}=1
$$


## Summation and products


$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$


$$
\prod_{i=1}^{n} i = n!
$$


## Matrices


$$
A =
\begin{bmatrix}
1 & 2 & 3 \\
4 & 5 & 6 \\
7 & 8 & 9
\end{bmatrix}
$$


## Systems of equations


$$
\begin{cases}
2x + y = 5 \\
x - y = 1
\end{cases}
$$


## Vectors


$$
\vec{a} \cdot \vec{b}
= |\vec{a}|\,|\vec{b}|\cos\theta
$$


## Aligned equations


$$
\begin{aligned}
f(x) &= (x+1)^2 \\
&= x^2 + 2x + 1
\end{aligned}
$$


## Set notation


$$
A \cup B,\qquad A \cap B,\qquad A \subseteq B
$$


$$
\mathbb{R},\quad \mathbb{Z},\quad \mathbb{N},\quad \varnothing
$$


# 11. Horizontal Rules


The paragraph above the divider.


The paragraph below the divider.


Another divider.


A third divider.


# 12. Footnotes


Here is a statement that references a footnote.[^first]


Here is another statement with its own reference.[^second]


[^first]: This is the first footnote.
[^second]: This is the second footnote, containing additional explanatory information.


Footnote rendering depends on the Markdown implementation.


# 13. HTML and Extended Formatting


Some Markdown renderers support selected HTML tags within Markdown documents.


## HTML syntax example


```html
<details>
  <summary>Click to expand</summary>

  This is the hidden content.

  - Item A
  - Item B
</details>
```


## Keyboard and superscript notation


Press


 to copy.


The mathematical expression is x


.


The chemical formula is H


O.


## Definition lists


Term 1
: Definition for term 1.


Term 2
: Definition for term 2.


Definition lists are an extension and may render as ordinary text in some environments.


# 14. GitHub-Flavored Markdown Extensions


## Strikethrough


This requirement has been removed.


## Autolinks


[https://github.com/openai](https://github.com/openai)


[https://www.markdownguide.org/](https://www.markdownguide.org/)


## Task lists

- Unit tests pass


- Integration tests pass


- Performance tests pass


## Alerts / callouts


The following syntax is supported by some GitHub-oriented Markdown renderers. ChatGPT may display the blockquotes without special alert styling.

> [!NOTE]
> This is additional information for the reader.

> [!TIP]
> Use smaller, reusable components where practical.

> [!IMPORTANT]
> Validate assumptions before deploying changes.

> [!WARNING]
> This operation may modify existing data.

> [!CAUTION]
> Back up critical information before executing destructive operations.


# 15. Mermaid Diagrams


Mermaid is a diagramming extension, not part of core Markdown. Some ChatGPT surfaces support Mermaid code-block previews.


## Flowchart


## Sequence diagram


## Class diagram


# 16. Escaping and Literal Syntax


These examples test whether Markdown syntax can be displayed literally.


## Escaped characters


*This text should not be italicized.*


*This text should not be bold.*


# This should not become a heading.


> This should not become a blockquote.


## Inline code containing Markdown


`**bold syntax displayed as code**`


`# heading syntax displayed as code`


`[link syntax](https://example.com)`


## Fenced code containing Markdown


```markdown
# This is source Markdown

**Bold text**

- First item
- Second item

| Key | Value |
|---|---|
| A | 1 |
```


# 17. Combined Real-World Technical Document


This final section combines the preceding components into a realistic example.


## System Architecture


The system processes incoming requests through an API gateway, applies business rules, and persists results in a relational database.


### Key Traits

- Scalability: Supports horizontal scaling.


- Reliability: Implements retries and fault handling.


- Observability: Uses structured logs and metrics.


- Security: Applies authentication and authorization.


### Request Lifecycle

1. Receive and validate a request.


2. Authenticate the caller.


3. Execute the business operation.


4. Persist changes and return the response.


> High reliability is essential when the service handles critical business operations.


### Performance Comparison


| Metric | Synchronous API | Asynchronous API | Notes |
| --- | --- | --- | --- |
| Latency | Potentially higher | Often lower perceived latency | Workload-dependent |
| Throughput | Resource-dependent | Can improve concurrency | Requires capacity testing |
| Complexity | Lower | Higher | Queue and retry management |
| Complexity class | $O(N)$ | $O(N \log N)$ | Illustrative only |


### Example implementation


```python
def process_request(request: dict) -> dict:
    """Validate and process an incoming request."""

    if not request.get("id"):
        raise ValueError("Missing request ID")

    return {
        "id": request["id"],
        "status": "processed",
    }

result = process_request({"id": "req-001"})
print(result)
```


### Performance model


For a workload of size $N$, a common comparison is:


$$
T(N) = O(N \log N)
$$


Given the following resource constraints:


$$
\begin{aligned}
\text{CPU} &\leq C_{\max} \\
\text{Memory} &\leq M_{\max} \\
\text{Latency} &\leq L_{\max}
\end{aligned}
$$


the system must meet its service-level objectives while maintaining correctness.


### Deployment checklist

- Code reviewed


- Unit tests passed


- Integration tests completed


- Load tests completed


- Production rollout approved


# 18. Rendering Compatibility Checklist


Use this checklist to record which components render correctly in your ChatGPT interface.


## Markdown test results


0/27 passed


Core Markdown


Heading levels 1–6


Paragraphs and line breaks


Bold, italic and strikethrough


Inline code


Horizontal rules


Lists and blocks


Ordered and unordered lists


Nested lists


Task lists / checkboxes


Blockquotes and nested blockquotes


Links and reference links


Images


Structured content


Tables and column alignment


Tables containing inline math


Fenced code blocks


Syntax highlighting


Escaped Markdown characters


Extensions


Inline LaTeX


Display equations


Footnotes


HTML formatting


GitHub-style alerts


Mermaid diagrams


Layout and combined rendering


Long code blocks


Long tables


Mixed formatting inside lists


Responsive wrapping


Combined technical document


Copy resultsReset


Compatibility note: Markdown rendering varies by ChatGPT client, platform, and renderer. Core features such as headings, lists, blockquotes, tables, and fenced code are widely supported. Footnotes, raw HTML, reference links, alert blocks, and Mermaid previews are more implementation-dependent. Some features may look different in the web interface, mobile app, or exported content.