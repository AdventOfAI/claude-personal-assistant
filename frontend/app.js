import { renderAssistantMarkdown } from "./markdown.js";

const STORAGE_KEY = "pa_client_id";

function getClientId() {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}

const clientId = getClientId();

const api = (path, options = {}) =>
  fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

async function loadProfile() {
  const r = await api(`/api/profile?client_id=${encodeURIComponent(clientId)}`);
  if (!r.ok) throw new Error("Failed to load profile");
  return r.json();
}

async function saveProfile(profile) {
  const r = await api(`/api/profile?client_id=${encodeURIComponent(clientId)}`, {
    method: "PUT",
    body: JSON.stringify({ profile }),
  });
  if (!r.ok) throw new Error("Failed to save profile");
  return r.json();
}

async function loadConversation() {
  const r = await api(`/api/conversation?client_id=${encodeURIComponent(clientId)}`);
  if (!r.ok) throw new Error("Failed to load conversation");
  return r.json();
}

async function clearConversationServer() {
  const r = await fetch(
    `/api/conversation?client_id=${encodeURIComponent(clientId)}`,
    { method: "DELETE" },
  );
  if (!r.ok) throw new Error("Failed to clear conversation");
  return r.json();
}

/** @type {{ role: 'user' | 'assistant', content: string }[]} */
let transcript = [];

const messagesEl = document.getElementById("messages");
const composer = document.getElementById("composer");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const toggleSettings = document.getElementById("toggle-settings");
const settingsPanel = document.getElementById("settings-panel");
const displayName = document.getElementById("display-name");
const tone = document.getElementById("tone");
const aboutMe = document.getElementById("about-me");
const extraInstructions = document.getElementById("extra-instructions");
const saveProfileBtn = document.getElementById("save-profile");
const profileStatus = document.getElementById("profile-status");
const fileInput = document.getElementById("file-input");
const attachBtn = document.getElementById("attach-btn");
const fileStatus = document.getElementById("file-status");
const clearFileBtn = document.getElementById("clear-file");
const clearChatBtn = document.getElementById("clear-chat");

/** @type {File | null} */
let pendingFile = null;

function appendMessage(role, content) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const label = document.createElement("div");
  label.className = "label";
  label.textContent = role === "user" ? "You" : "Assistant";
  const body = document.createElement("div");
  body.className = role === "assistant" ? "msg-body md" : "msg-body";
  if (role === "assistant") {
    body.innerHTML = renderAssistantMarkdown(content);
  } else {
    body.textContent = content;
  }
  wrap.appendChild(label);
  wrap.appendChild(body);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

/** @returns {HTMLElement} body element for assistant reply */
function appendAssistantPlaceholder() {
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";
  const label = document.createElement("div");
  label.className = "label";
  label.textContent = "Assistant";
  const body = document.createElement("div");
  body.className = "msg-body md typing";
  body.textContent = "Thinking…";
  wrap.appendChild(label);
  wrap.appendChild(body);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return body;
}

function setFileUI() {
  if (pendingFile) {
    fileStatus.textContent = pendingFile.name;
    fileStatus.classList.add("has-file");
    clearFileBtn.hidden = false;
  } else {
    fileStatus.textContent = "";
    fileStatus.classList.remove("has-file");
    clearFileBtn.hidden = true;
    fileInput.value = "";
  }
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  userInput.value = "";
  userInput.style.height = "auto";
  appendMessage("user", text);
  transcript.push({ role: "user", content: text });

  const fileToSend = pendingFile;
  pendingFile = null;
  setFileUI();

  sendBtn.disabled = true;

  const bodyEl = appendAssistantPlaceholder();

  const fd = new FormData();
  fd.append("messages", JSON.stringify(transcript));
  fd.append("client_id", clientId);
  if (fileToSend) fd.append("file", fileToSend, fileToSend.name);

  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      body: fd,
    });

    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      const detail = err.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || d).join("; ")
            : r.statusText;
      bodyEl.classList.remove("md", "typing");
      bodyEl.textContent = `Error: ${msg}`;
      transcript.pop();
      return;
    }

    const data = await r.json();
    const full = data.message?.content ?? "";
    bodyEl.classList.remove("typing");
    if (!full) {
      bodyEl.classList.remove("md");
      bodyEl.textContent = "(empty reply)";
    } else {
      bodyEl.innerHTML = renderAssistantMarkdown(full);
    }
    transcript.push({ role: "assistant", content: full });
  } catch (e) {
    bodyEl.classList.remove("md", "typing");
    bodyEl.textContent = `Network error: ${String(e)}`;
    transcript.pop();
  } finally {
    sendBtn.disabled = false;
    userInput.focus();
  }
}

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage();
});

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

userInput.addEventListener("input", () => {
  userInput.style.height = "auto";
  userInput.style.height = `${Math.min(userInput.scrollHeight, 160)}px`;
});

attachBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  const f = fileInput.files?.[0];
  pendingFile = f || null;
  setFileUI();
});

clearFileBtn.addEventListener("click", () => {
  pendingFile = null;
  setFileUI();
});

clearChatBtn.addEventListener("click", async () => {
  if (!window.confirm("Clear saved chat history for this browser?")) return;
  try {
    await clearConversationServer();
    transcript = [];
    messagesEl.replaceChildren();
  } catch {
    window.alert("Could not clear chat on the server.");
  }
});

toggleSettings.addEventListener("click", () => {
  const open = settingsPanel.hidden;
  settingsPanel.hidden = !open;
  toggleSettings.setAttribute("aria-expanded", String(open));
});

saveProfileBtn.addEventListener("click", async () => {
  profileStatus.textContent = "";
  try {
    await saveProfile({
      display_name: displayName.value.trim(),
      tone: tone.value,
      about_me: aboutMe.value.trim(),
      extra_instructions: extraInstructions.value.trim(),
    });
    profileStatus.textContent = "Saved.";
    setTimeout(() => {
      profileStatus.textContent = "";
    }, 2500);
  } catch {
    profileStatus.textContent = "Could not save.";
  }
});

(async function init() {
  try {
    const p = await loadProfile();
    displayName.value = p.display_name || "";
    tone.value = p.tone || "balanced";
    aboutMe.value = p.about_me || "";
    extraInstructions.value = p.extra_instructions || "";
  } catch {
    profileStatus.textContent = "Could not load profile.";
  }
  try {
    const conv = await loadConversation();
    transcript = Array.isArray(conv.messages) ? conv.messages : [];
    messagesEl.replaceChildren();
    for (const m of transcript) {
      if (m.role === "user" || m.role === "assistant") {
        appendMessage(m.role, m.content ?? "");
      }
    }
  } catch {
    /* chat can load empty if API fails */
  }
})();
