from __future__ import annotations

# Only the newly submitted Copilot assistant message is eligible. Copilot's
# Designer card is separate from markdown-reply and may still be loading after
# its surrounding message has rendered.
COPILOT_RESPONSE_ROOT = r"""
const visible = el => !!el.getClientRects().length &&
    !el.closest('[hidden], [aria-hidden="true"], aside, nav');
const candidates = () => {
    for (const selector of [
        '[data-testid="copilot-message-div"]',
        '[data-testid="copilot-message-reply-div"]',
        '[data-testid="chat-response-message"]',
        '[data-testid="lastChatMessage"]',
        '[role="article"][aria-labelledby^="copilot-message-"]'
    ]) {
        const nodes = [...document.querySelectorAll(selector)].filter(visible);
        if (nodes.length) return nodes;
    }
    return [];
};
const previous = window.__pcCopilotPreviousResponses;
let roots = candidates().filter(el => !previous || !previous.has(el));
if (!roots.length && !previous) roots = candidates();
const root = roots.at(-1);
const designer = root ? root.querySelector('[id^="designer-host-"], [class*="designer" i], [data-testid*="designer" i]') : null;
const mediaRoot = designer || root;
const imageElements = mediaRoot ? [...mediaRoot.querySelectorAll('img, canvas')].filter(el => {
    const rect = el.getBoundingClientRect();
    return rect.width >= 80 && rect.height >= 80 && visible(el);
}) : [];
"""

CAPTURE_COPILOT_RESPONSES = "() => {" + COPILOT_RESPONSE_ROOT + r"""
window.__pcCopilotPreviousResponses = new WeakSet(candidates());
}"""

COPILOT_RESPONSE_READY = "() => {" + COPILOT_RESPONSE_ROOT + r"""
if (!root) return null;
const hasDesigner = !!designer || !!root.querySelector('[id^="designer-host-"]');
if (!hasDesigner) return null;
if (!imageElements.length) return false;
return imageElements.every(el => {
    if (el.tagName === 'CANVAS') return el.width > 0 && el.height > 0;
    return el.complete && el.naturalWidth >= 80 && el.naturalHeight >= 80;
});
}"""

EXTRACT_COPILOT_RESPONSE = "async ({maxBytes, maxImages}) => {" + COPILOT_RESPONSE_ROOT + r"""
if (!root) return null;
const hasDesigner = !!designer || !!root.querySelector('[id^="designer-host-"]');
if (!hasDesigner) return null;
if (imageElements.length > maxImages) throw new Error('Too many Copilot generated images');
const clone = root.cloneNode(true);
const cloneDesigner = clone.querySelector('[id^="designer-host-"], [class*="designer" i], [data-testid*="designer" i]');
if (cloneDesigner) cloneDesigner.remove();
const results = [];
for (const el of imageElements) {
    const alt = el.getAttribute('alt') || el.getAttribute('aria-label') || 'Generated image';
    try {
        let bytes, type;
        if (el.tagName === 'CANVAS') {
            const dataUrl = el.toDataURL('image/png');
            if (!dataUrl.startsWith('data:image/png;base64,')) throw new Error('Canvas did not return PNG data');
            const binary = atob(dataUrl.slice(dataUrl.indexOf(',') + 1));
            bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
            type = 'image/png';
        } else {
            const src = el.currentSrc || el.src;
            if (!el.complete || el.naturalWidth < 80 || el.naturalHeight < 80)
                throw new Error('Generated image is not loaded');
            if (!/^(blob:|https:\/\/|data:image\/(png|jpeg|webp|gif);base64,)/i.test(src))
                throw new Error('Unsupported generated image source');
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), 15000);
            try {
                const response = await fetch(src, {signal: controller.signal, credentials: 'same-origin', redirect: 'error'});
                if (!response.ok) throw new Error('Image fetch failed: ' + response.status);
                type = (response.headers.get('Content-Type') || '').split(';')[0].toLowerCase();
                if (!['image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(type))
                    throw new Error('Unsupported image content type');
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
        }
        if (!bytes.length || bytes.length > maxBytes) throw new Error('Image is empty or exceeds size limit');
        let binary = '';
        for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
        results.push({alt, type, data: btoa(binary)});
    } catch (error) { results.push({alt, error: String(error)}); }
}
return {html: clone.innerHTML, images: results};
}"""
