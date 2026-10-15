import asyncio
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "changeme"


def send_request(path, data=None, method="GET"):
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def main():
    model_id = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.1-pro"
    thinking_level = sys.argv[2] if len(sys.argv) > 2 else "high"

    prompt = (
        "Generate a comprehensive showcase of all kinds of markdown components supported by Gemini. "
        "Include:\n"
        "1. Headings (H1, H2, H3, H4)\n"
        "2. Formatted text: Bold, Italic, Strikethrough, Inline code\n"
        "3. Blockquotes and nested quotes\n"
        "4. Ordered lists, Unordered lists, and Nested bullet points\n"
        "5. Task checklists with completed and pending items\n"
        "6. Rich Data Table with headers, alignment, and multiple rows\n"
        "7. Code blocks with syntax highlighting for Python, TypeScript, and SQL\n"
        "8. LaTeX Math equations (both inline like $E = mc^2$ and block display equations like $\\int_{0}^{\\infty} x^2 e^{-x} dx$)\n"
        "9. Alert/Callout blocks (Note, Tip, Important, Warning)\n"
        "Make it rich, well-formatted, and educational."
    )

    payload = {
        "query": prompt,
        "providers": ["gemini"],
        "provider_options": {
            "gemini": {
                "model_id": model_id,
                "thinking_level_id": thinking_level,
            }
        },
    }

    print(f"Submitting research job with Gemini (Model: {model_id}, Thinking: {thinking_level})...")
    res = send_request("/research", payload, method="POST")
    job_id = res["job_id"]
    print(f"Job created: {job_id}")

    # Poll job status
    seen_steps = 0
    while True:
        await asyncio.sleep(3.0)
        job_info = send_request(f"/research/{job_id}")
        status = job_info.get("status")
        steps = job_info.get("steps", [])

        while seen_steps < len(steps):
            st = steps[seen_steps]
            step_name = st.get("step")
            msg = st.get("message")
            print(f"[{st.get('timestamp')}] [{st.get('provider')}] {step_name}: {msg}")
            seen_steps += 1

        if status in {"completed", "failed", "cancelled"}:
            print(f"\nJob ended with status: {status}")
            report = job_info.get("report_markdown", "")
            print(f"Report length: {len(report)} characters")
            if report:
                print("--- Report Preview (first 1000 chars) ---")
                print(report[:1000])
                print("...\n--- End Preview ---")
            break


if __name__ == "__main__":
    asyncio.run(main())
