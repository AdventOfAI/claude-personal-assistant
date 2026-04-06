import { marked } from "https://esm.sh/marked@12.0.2";
import DOMPurify from "https://esm.sh/dompurify@3.2.2";

marked.setOptions({
  breaks: true,
  gfm: true,
});

/**
 * Turn assistant Markdown into safe HTML for innerHTML.
 * @param {string} text
 */
export function renderAssistantMarkdown(text) {
  if (!text) return "";
  try {
    const raw = marked.parse(text);
    return DOMPurify.sanitize(raw);
  } catch {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}
