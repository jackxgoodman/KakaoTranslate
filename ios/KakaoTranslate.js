// KakaoTranslate for iPhone — runs in the Scriptable app, called by the
// "Kakao Translate" Shortcut (see ios/README.md).
//
// Step 1: the Shortcut passes the exported chat text. This script finds the
//         messages since your last run and returns the Korean ones, which the
//         Shortcut translates with Apple's Translate.
// Step 2: the Shortcut passes back the translations. This script returns the
//         finished list and remembers where you left off.
//
// Run it directly in Scriptable to reset the saved position.

// ── Settings ──────────────────────────────────────────────────────────────
const FIRST_RUN_COUNT = 30;  // messages shown the first time you use a chat
// ──────────────────────────────────────────────────────────────────────────

const MARK = "KT-TRANSLATIONS";
const SEP = "@@@";
const ANCHOR_LEN = 5;

const SYLLABLE = /[가-힣]/;  // only text with real Korean syllables goes to Translate
const JAMO_MEANINGS = [[/ㅋ|ㅎ/, "(laughing)"], [/ㅠ|ㅜ/, "(crying)"], [/ㅇㅇ/, "(yeah)"], [/ㄱㄱ/, "(let's go)"]];
const TIME = /\d{1,2}:\d{2}/;
const PC_LINE = /^\[([^\[\]]+)\]\s*\[([^\]]*\d{1,2}:\d{2}[^\]]*)\]\s?(.*)$/;
const DATE_LINE = new RegExp(
  "^[\\s\\-=]*(" +
    "\\d{4}\\s*년\\s*\\d{1,2}\\s*월\\s*\\d{1,2}\\s*일.*" +
    "|(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\\s.*\\d{4}" +
    "|[A-Z][a-z]+\\.? \\d{1,2}, \\d{4}" +
    "|\\d{4}\\.\\s?\\d{1,2}\\.\\s?\\d{1,2}\\.?(\\s[가-힣]+요일)?" +
  ")[\\s\\-=]*$"
);
const SYSTEM = /(님이 들어왔습니다|님이 나갔습니다|님을 초대했습니다|님을 내보냈습니다|joined this chatroom|left this chatroom|invited .+ to)/i;

// ── Parsing ───────────────────────────────────────────────────────────────

function parseLine(line) {
  const pc = line.match(PC_LINE);
  if (pc) return { sender: pc[1].trim(), time: pc[2].trim(), text: pc[3] };

  // Phone exports: "<date and time>, <name> : <message>"
  const split = line.indexOf(" : ");
  if (split < 0) return null;
  const head = line.slice(0, split);
  if (!TIME.test(head)) return null;  // e.g. "Date Saved : …"
  const comma = head.lastIndexOf(", ");
  const sender = comma >= 0 ? head.slice(comma + 2).trim() : "";
  const time = comma >= 0 ? head.slice(0, comma).trim() : head.trim();
  return { sender, time, text: line.slice(split + 3) };
}

function parseExport(raw) {
  const lines = String(raw).replace(/\r\n?/g, "\n").split("\n");
  const title = cleanTitle(lines.find(l => l.trim()) || "KakaoTalk chat");
  const messages = [];
  let current = null;
  for (const line of lines) {
    const msg = parseLine(line);
    if (msg) {
      current = msg;
      messages.push(current);
      continue;
    }
    const t = line.trim();
    if (DATE_LINE.test(t) || SYSTEM.test(t)) {
      current = null;
    } else if (current) {
      current.text += "\n" + line;
    }
  }
  for (const m of messages) m.text = m.text.trim();
  return { title, messages: messages.filter(m => m.text) };
}

function cleanTitle(line) {
  return line.trim()
    .replace(/\s*님과 카카오톡 대화\s*$/, "")
    .replace(/^Talk(s)? with\s+/i, "")
    .replace(/^KakaoTalk Chats with\s+/i, "");
}

const keyOf = m => `${m.sender}\u0001${m.time}\u0001${m.text}`;

// Index just after the saved anchor (the last few messages seen), or -1.
function findAfterAnchor(anchor, messages) {
  if (!anchor || !anchor.length) return -1;
  const keys = messages.map(keyOf);
  for (let len = Math.min(ANCHOR_LEN, anchor.length); len >= 1; len--) {
    const tail = anchor.slice(anchor.length - len);
    for (let start = keys.length - len; start >= 0; start--) {
      let ok = true;
      for (let i = 0; i < len; i++) if (keys[start + i] !== tail[i]) { ok = false; break; }
      if (ok) return start + len;
    }
    if (len <= 2 && anchor.length > len) break;  // too short to trust
  }
  return -1;
}

// ── Output ────────────────────────────────────────────────────────────────

function buildDigest(pending, translations) {
  const { title, messages, note } = pending;
  if (pending.error) return pending.error;
  const lines = [];
  lines.push(messages.length
    ? `${title} — ${messages.length} new message${messages.length === 1 ? "" : "s"}`
    : `${title} — no new messages since last time.`);
  if (note) lines.push(note);
  let t = 0;
  for (const m of messages) {
    lines.push("");
    lines.push(`[${m.sender || "?"}] ${m.time}`);
    lines.push(m.text);
    if (SYLLABLE.test(m.text)) {
      const tr = translations[t++];
      lines.push(`→ ${tr === undefined ? "(not translated)" : tr.trim()}`);
    } else {
      const meaning = JAMO_MEANINGS.find(([re]) => re.test(m.text));
      if (meaning) lines.push(`→ ${meaning[1]}`);
    }
  }
  return lines.join("\n");
}

// ── Main logic (independent of Scriptable, so it can be tested) ───────────

const PENDING_MAX_AGE_MS = 10 * 60 * 1000;

const asText = param => (Array.isArray(param) ? param.join("\n") : String(param == null ? "" : param));

function asList(param) {
  if (param == null) return [];
  if (Array.isArray(param)) return param.map(t => String(t).trim());
  const s = String(param).trim();
  return s ? [s] : [];
}

// Older Shortcut layout: "KT-TRANSLATIONS@@@one@@@two"
function markedTranslations(param) {
  if (typeof param !== "string" || !param.trimStart().startsWith(MARK)) return null;
  const rest = param.trimStart().slice(MARK.length).replace(/^\s*@@@/, "");
  return rest.trim() ? rest.split(SEP).map(t => t.trim()) : [];
}

function handle(param, store, now = Date.now()) {
  const state = store.load();
  state.chats = state.chats || {};
  const pending = state.pending;
  const awaiting = !!(pending && pending.awaiting && now - (pending.createdAt || 0) < PENDING_MAX_AGE_MS);

  // Step 2: the Shortcut passes back the translations (anything that isn't a chat export).
  let translations = markedTranslations(param);
  if (translations === null && awaiting && !parseExport(asText(param)).messages.length) {
    translations = asList(param);
  }
  if (translations !== null) {
    if (!pending) return { output: "Start the Shortcut from KakaoTalk's Export Chats share menu." };
    const output = buildDigest(pending, translations);
    if (!pending.error) state.chats[pending.title] = { anchor: pending.anchor };
    delete state.pending;
    store.save(state);
    return { output };
  }

  // Step 1: the Shortcut passes the exported chat.
  const raw = asText(param);
  const { title, messages } = parseExport(raw);
  if (!messages.length) {
    const gotFileName = /^[^\n]*\.(txt|zip)\s*$/i.test(raw.trim());
    state.pending = {
      awaiting: true,
      createdAt: now,
      error: gotFileName
        ? `The Shortcut passed the file name ("${raw.trim()}") instead of its contents. ` +
          "Add a Text action containing Shortcut Input before the first Run Script, and pass that Text instead."
        : "Couldn't find any messages in that export. Use Export Chats → Send text only.",
    };
    store.save(state);
    return { output: [] };
  }

  // Find where you left off: this chat's saved position, or any saved position
  // that matches (in case the export's first line changed).
  let chatKey = title;
  let start = findAfterAnchor(state.chats[title] && state.chats[title].anchor, messages);
  if (start < 0) {
    for (const [key, saved] of Object.entries(state.chats)) {
      const found = findAfterAnchor(saved.anchor, messages);
      if (found >= 0) { chatKey = key; start = found; break; }
    }
  }
  const saved = state.chats[chatKey];
  let note = "";
  if (start < 0) {
    start = Math.max(0, messages.length - FIRST_RUN_COUNT);
    note = saved
      ? `(Couldn't find where you left off — showing the last ${messages.length - start}.)`
      : `(First time for this chat — showing the last ${messages.length - start}.)`;
  }
  const fresh = messages.slice(start);
  state.pending = {
    awaiting: true,
    createdAt: now,
    title: chatKey,
    note,
    messages: fresh,
    anchor: messages.slice(-ANCHOR_LEN).map(keyOf),
  };
  store.save(state);
  return { output: fresh.filter(m => SYLLABLE.test(m.text)).map(m => m.text) };
}

// ── Scriptable glue ───────────────────────────────────────────────────────

if (typeof Script !== "undefined") (async () => {
  const fm = FileManager.local();
  const dir = fm.joinPath(fm.documentsDirectory(), "KakaoTranslate");
  const file = fm.joinPath(dir, "state.json");
  const store = {
    load: () => (fm.fileExists(file) ? JSON.parse(fm.readString(file)) : {}),
    save: s => {
      if (!fm.fileExists(dir)) fm.createDirectory(dir, true);
      fm.writeString(file, JSON.stringify(s));
    },
  };

  if (config.runsFromShortcut) {
    let param = args.shortcutParameter;
    const path = typeof param === "string" ? param.trim() : "";
    if (/^\/.*\.txt$/i.test(path) && fm.fileExists(path)) param = fm.readString(path);
    Script.setShortcutOutput(handle(param, store).output);
    Script.complete();
  } else {
    const alert = new Alert();
    alert.title = "Kakao Translate";
    alert.message = "Run the \"Kakao Translate\" Shortcut from KakaoTalk: chat → ⚙ → Export Chats → " +
      "Send text only → Kakao Translate.\n\nReset forgets where you left off in every chat.";
    alert.addDestructiveAction("Reset");
    alert.addCancelAction("Close");
    if ((await alert.present()) === 0) {
      store.save({});
    }
    Script.complete();
  }
})();

if (typeof module !== "undefined") {
  module.exports = { parseExport, parseLine, findAfterAnchor, buildDigest, handle, MARK, SEP };
}
