const copy = {
  kn: {
    title: "ಅಪ್ಲಿಕೇಶನ್ ಸಹಾಯ",
    welcomeTitle: "GreenPlot ಅನ್ನು ಹೇಗೆ ಬಳಸುವುದು?",
    welcome: "ಖಾತೆ, ಜಮೀನು, ಗುತ್ತಿಗೆ, ಬೆಳೆ ಮತ್ತು ಸೆಟ್ಟಿಂಗ್‌ಗಳ ಬಗ್ಗೆ ಕೇಳಿ. ಉತ್ತರಗಳು ಅಪ್ಲಿಕೇಶನ್ ಮಾರ್ಗದರ್ಶಿಯಿಂದ ಬರುತ್ತವೆ.",
    placeholder: "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಬರೆಯಿರಿ",
    send: "ಕಳುಹಿಸಿ",
    thinking: "ನೋಡುತ್ತಿದ್ದೇನೆ…",
    translating: "ಭಾಷೆ ಬದಲಾಯಿಸುತ್ತಿದ್ದೇನೆ…",
    sources: "ಮೂಲ",
    quick: [
      "ಖಾತೆ ಹೇಗೆ ತೆರೆಯುವುದು?",
      "ಜಮೀನನ್ನು ಹೇಗೆ ಸೇರಿಸುವುದು?",
      "ಗುತ್ತಿಗೆಗೆ ಹೇಗೆ ಅರ್ಜಿ ಹಾಕುವುದು?",
      "ಭಾಷೆಯನ್ನು ಹೇಗೆ ಬದಲಾಯಿಸುವುದು?",
    ],
  },
  en: {
    title: "App guide",
    welcomeTitle: "How do I use GreenPlot?",
    welcome: "Ask about your account, land, a lease, crops, or settings. Answers come from the app guide.",
    placeholder: "Type your question",
    send: "Send",
    thinking: "Looking that up…",
    translating: "Translating the conversation…",
    sources: "Source",
    quick: [
      "How do I create an account?",
      "How do I add my land?",
      "How do I apply for a lease?",
      "How do I change the language?",
    ],
  },
};

const state = { language: "kn", messages: [], busy: false, pending: "" };

const log = document.getElementById("log");
const welcome = document.getElementById("welcome");
const form = document.getElementById("form");
const input = document.getElementById("input");
const send = document.getElementById("send");
const banner = document.getElementById("banner");

document.getElementById("lang-kn").onclick = () => setLanguage("kn");
document.getElementById("lang-en").onclick = () => setLanguage("en");
form.onsubmit = (event) => {
  event.preventDefault();
  ask(input.value);
};

function sessionId() {
  let id = localStorage.getItem("guideSessionId");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("guideSessionId", id);
  }
  return id;
}

function applyChrome() {
  const language = state.language;
  document.documentElement.lang = language === "kn" ? "kn" : "en";
  document.getElementById("lang-kn").classList.toggle("active", language === "kn");
  document.getElementById("lang-en").classList.toggle("active", language === "en");
  const text = copy[language];
  document.getElementById("title").textContent = text.title;
  document.getElementById("welcome-title").textContent = text.welcomeTitle;
  document.getElementById("welcome-copy").textContent = text.welcome;
  input.placeholder = text.placeholder;
  send.textContent = text.send;
  renderQuick();
}

function renderQuick() {
  const box = document.getElementById("quick");
  box.replaceChildren();
  copy[state.language].quick.forEach((question) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chip";
    button.textContent = question;
    button.onclick = () => ask(question);
    box.appendChild(button);
  });
}

function shownText(message) {
  if (state.language === "kn") return message.textKn || message.textEn || "";
  return message.textEn || message.textKn || "";
}

function shownSuggestions(message) {
  if (state.language === "kn") return message.suggestionsKn?.length ? message.suggestionsKn : message.suggestionsEn;
  return message.suggestionsEn?.length ? message.suggestionsEn : message.suggestionsKn;
}

function renderThread() {
  log.querySelectorAll(".row").forEach((row) => row.remove());
  welcome.hidden = state.messages.length > 0 || Boolean(state.pending);
  state.messages.forEach(renderMessage);
  if (state.pending) addBubble(state.pending, "bot pending");
  log.scrollTop = log.scrollHeight;
}

function renderMessage(message) {
  if (message.role === "user") {
    addBubble(shownText(message), "user");
    return;
  }
  const row = document.createElement("div");
  row.className = "row bot";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  const body = document.createElement("div");
  body.textContent = shownText(message);
  bubble.appendChild(body);

  const tools = document.createElement("div");
  tools.className = "tools";
  if (message.sources?.length) {
    const source = document.createElement("span");
    source.className = "sources";
    const names = [...new Set(message.sources.map((item) => item.title))];
    source.textContent = `${copy[state.language].sources}: ${names.join(", ")}`;
    tools.appendChild(source);
  }
  if (tools.childNodes.length) bubble.appendChild(tools);

  const suggestions = shownSuggestions(message) || [];
  if (suggestions.length) {
    const chips = document.createElement("div");
    chips.className = "tools";
    suggestions.slice(0, 3).forEach((suggestion) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "suggest";
      button.textContent = suggestion;
      button.onclick = () => ask(suggestion);
      chips.appendChild(button);
    });
    bubble.appendChild(chips);
  }

  row.appendChild(bubble);
  log.appendChild(row);
}

function addBubble(text, kind) {
  const row = document.createElement("div");
  row.className = `row ${kind.includes("user") ? "user" : "bot"}`;
  const bubble = document.createElement("div");
  bubble.className = `bubble ${kind}`;
  bubble.textContent = text;
  row.appendChild(bubble);
  log.appendChild(row);
  return bubble;
}

async function ask(raw) {
  const message = raw.trim();
  if (!message || state.busy) return;
  state.busy = true;
  input.value = "";
  send.disabled = true;
  state.pending = copy[state.language].thinking;
  state.messages.push({
    id: crypto.randomUUID(),
    role: "user",
    textKn: state.language === "kn" ? message : "",
    textEn: state.language === "en" ? message : "",
    sources: [],
    suggestionsKn: [],
    suggestionsEn: [],
  });
  renderThread();
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        language: state.language,
        sessionId: sessionId(),
        history: state.messages.slice(0, -1).slice(-6).map((turn) => ({
          role: turn.role,
          content: turn.textEn || turn.textKn,
        })),
      }),
    });
    const data = await response.json();
    state.messages.pop();
    if (data.userMessage && data.assistantMessage) {
      state.messages.push(data.userMessage, data.assistantMessage);
    } else {
      state.messages.push(
        {
          id: crypto.randomUUID(),
          role: "user",
          textKn: state.language === "kn" ? message : "",
          textEn: state.language === "en" ? message : "",
          sources: [],
          suggestionsKn: [],
          suggestionsEn: [],
        },
        {
          id: crypto.randomUUID(),
          role: "assistant",
          textKn: data.answerLanguage === "kn" ? data.reply || "" : "",
          textEn: data.replyEnglish || data.reply || "",
          sources: data.sources || [],
          suggestionsKn: data.answerLanguage === "kn" ? data.suggestions || [] : [],
          suggestionsEn: data.answerLanguage === "kn" ? [] : data.suggestions || [],
        },
      );
    }
    if (data.historyError) showBanner(data.historyError);
  } catch {
    state.messages.pop();
    showBanner(state.language === "kn"
      ? "ಸಂಪರ್ಕ ಸಿಗಲಿಲ್ಲ. ಸರ್ವರ್ ಚಾಲನೆಯಲ್ಲಿದೆಯೇ ಎಂದು ನೋಡಿ."
      : "Could not reach the server.");
  } finally {
    state.pending = "";
    state.busy = false;
    send.disabled = false;
    renderThread();
    input.focus();
  }
}

async function setLanguage(language) {
  if (state.busy || state.language === language) return;
  state.language = language;
  localStorage.setItem("guideLanguage", language);
  applyChrome();
  renderThread();
  await translateMissing();
}

async function translateMissing() {
  const target = state.language;
  const items = state.messages.flatMap((message) => {
    const text = target === "kn" ? message.textKn : message.textEn;
    if (text) return [];
    const source = target === "kn" ? message.textEn : message.textKn;
    if (!source) return [];
    const suggestions = target === "kn" ? message.suggestionsEn : message.suggestionsKn;
    return [{ id: message.id, text: source, suggestions: suggestions || [] }];
  });
  if (!items.length) return;
  state.busy = true;
  send.disabled = true;
  showBanner(copy[target].translating);
  try {
    const response = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target, sessionId: sessionId(), items }),
    });
    const data = await response.json();
    if (data.error) {
      showBanner(data.error);
      return;
    }
    let failed = 0;
    for (const item of data.items || []) {
      const message = state.messages.find((entry) => entry.id === item.id);
      if (!message || !item.text) {
        failed += 1;
        continue;
      }
      if (target === "kn") {
        message.textKn = item.text;
        if (item.suggestions?.length) message.suggestionsKn = item.suggestions;
      } else {
        message.textEn = item.text;
        if (item.suggestions?.length) message.suggestionsEn = item.suggestions;
      }
    }
    banner.hidden = failed === 0;
    if (failed) {
      showBanner(target === "kn"
        ? "ಕೆಲವು ಸಂದೇಶಗಳನ್ನು ಕನ್ನಡಕ್ಕೆ ಬದಲಾಯಿಸಲು ಆಗಲಿಲ್ಲ."
        : "Some messages could not be translated to English.");
    }
  } catch {
    showBanner(target === "kn"
      ? "ಭಾಷೆ ಬದಲಾವಣೆ ವಿಫಲವಾಗಿದೆ."
      : "Could not translate the conversation.");
  } finally {
    state.busy = false;
    send.disabled = false;
    renderThread();
  }
}

async function loadHistory() {
  try {
    const response = await fetch(`/api/history?sessionId=${sessionId()}`);
    const data = await response.json();
    if (data.error) showBanner(data.error);
    state.messages = data.messages || [];
    state.language = data.language === "en" ? "en" : "kn";
    applyChrome();
    renderThread();
    await translateMissing();
  } catch {
    applyChrome();
  }
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    if (!data.ollama) {
      showBanner("Ollama is not running. Start it, then pull qwen2.5:3b and nomic-embed-text.");
      return;
    }
    if (!data.chatReady || !data.embedReady) {
      const missing = [];
      if (!data.chatReady) missing.push(data.chatModel);
      if (!data.embedReady) missing.push(data.embedModel);
      showBanner(`Pull the missing model: ollama pull ${missing.join(" && ollama pull ")}`);
      return;
    }
    if (!data.history) showBanner(data.historyDetail || "Chat history is not connected to Supabase yet.");
    else banner.hidden = true;
  } catch {
    showBanner("The guide server is not responding.");
  }
}

function showBanner(text) {
  banner.hidden = false;
  banner.textContent = text;
}

applyChrome();
checkHealth().then(loadHistory);
