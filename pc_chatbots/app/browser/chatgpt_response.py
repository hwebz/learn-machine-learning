from __future__ import annotations

# Shared by readiness and extraction: only the new, visible response is eligible.
# _prepare_response marks existing responses before submitting; when extraction
# runs without that snapshot (e.g. provider retry), only image-bearing responses
# are treated as new so prior text turns are never re-captured.
RESPONSE_ROOT = r"""
const visible = el => !!el.getClientRects().length &&
    !el.closest('[hidden], [aria-hidden="true"], aside, nav');
const candidates = () => {
    for (const selector of [
        '[data-talvt-turn-state]', '[data-message-author-role="assistant"]',
        '[data-markdown-text-style="assistant-message"], [class*="MarkdownRoot"], [data-chatgpt-selection-message-id]',
        '[data-markdown-copy="contents"], div.markdown'
    ]) {
        const nodes = [...document.querySelectorAll(selector)].filter(visible);
        if (nodes.length) return nodes;
    }
    return [];
};
const previous = window.__pcChatGPTPreviousResponses;
let roots = candidates().filter(el => !previous || !previous.has(el));
if (!roots.length && !previous) {
    roots = candidates().filter(el =>
        el.querySelector('[data-testid="generated-image-gallery"], [data-testid="generated-image-preview"]'));
}
const root = roots.at(-1);
const images = root ? [...root.querySelectorAll(
    '[data-testid="generated-image-preview"] img, [data-testid="generated-image-gallery"] img'
)] : [];
"""

CAPTURE_RESPONSES = "() => {" + RESPONSE_ROOT + """
window.__pcChatGPTPreviousResponses = new WeakSet(candidates());
}"""

RESPONSE_READY = "() => {" + RESPONSE_ROOT + r"""
if (!root) return false;
const galleries = root.querySelectorAll('[data-testid="generated-image-gallery"], [data-testid="generated-image-preview"]');
if (!galleries.length) return null;
return images.length > 0 && images.every(img => img.complete && img.naturalWidth > 0 &&
    img.naturalHeight > 0 && /^(blob:https:\/\/chatgpt\.com\/|https:\/\/|data:image\/(png|jpeg|webp|gif);base64,)/i.test(img.currentSrc || img.src));
}"""

EXTRACT_RESPONSE = "async ({maxBytes, maxImages}) => {" + RESPONSE_ROOT + r"""
if (!root || !images.length) return null;
if (images.length > maxImages) throw new Error('Too many generated images');
const clone = root.cloneNode(true);
clone.querySelectorAll('[data-testid="generated-image-gallery"], [data-testid="generated-image-preview"]').forEach(el => el.remove());
const results = [];
for (const img of images) {
    const alt = img.alt || 'Generated image';
    try {
        const src = img.currentSrc || img.src;
        if (!img.complete || !img.naturalWidth || !img.naturalHeight) throw new Error('Generated image is not loaded');
        if (!/^(blob:https:\/\/chatgpt\.com\/|https:\/\/|data:image\/(png|jpeg|webp|gif);base64,)/i.test(src))
            throw new Error('Unsupported generated image source');
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 15000);
        let bytes, type;
        try {
            const response = await fetch(src, {signal: controller.signal, credentials: 'same-origin', redirect: 'error'});
            if (!response.ok) throw new Error('Image fetch failed: ' + response.status);
            type = (response.headers.get('Content-Type') || '').split(';')[0].toLowerCase();
            if (!['image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(type)) throw new Error('Unsupported image content type');
            if (Number(response.headers.get('Content-Length')) > maxBytes) throw new Error('Image exceeds size limit');
            const reader = response.body.getReader();
            const chunks = [];
            let size = 0;
            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                size += value.length;
                if (size > maxBytes) { await reader.cancel(); throw new Error('Image exceeds size limit'); }
                chunks.push(value);
            }
            bytes = new Uint8Array(size);
            let offset = 0;
            for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
        } finally { clearTimeout(timer); }
        let binary = '';
        for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
        results.push({alt, type, data: btoa(binary)});
    } catch (error) { results.push({alt, error: String(error)}); }
}
return {html: clone.innerHTML, images: results};
}"""
