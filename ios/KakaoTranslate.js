// KakaoTranslate for iPhone — runs in the Scriptable app, called twice by a
// Shortcut (see ios/README.md).
//
// Step 1: the Shortcut passes either the text read from a screenshot of the
//         chat ("Extract Text from Image"), or an exported chat. This script
//         works out who said what and returns the Korean messages, which the
//         Shortcut translates with Apple's Translate.
// Step 2: the Shortcut passes back the translations. This script returns the
//         finished, easy-to-read list.
//
// Run it directly in Scriptable to reset saved positions (exports only).

// ── Settings ──────────────────────────────────────────────────────────────
// Names of chat members exactly as KakaoTalk shows them. Optional, but makes
// sender detection reliable, e.g. ["양영환", "박성준", "Erik", "Y"].
const MEMBERS = [];
// Show the raw text read from the screen under the results (for fixing problems).
const SHOW_SCREEN_TEXT = false;
const FIRST_RUN_COUNT = 30;  // exports: messages shown the first time you use a chat
// ──────────────────────────────────────────────────────────────────────────

const VERSION = "2026-10-27b";  // shown when you open the script in Scriptable
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
  ")[\\s\\-=>›〉)]*$"  // KakaoTalk shows "Friday, October 16, 2026 >"
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

// ── Screenshot text ───────────────────────────────────────────────────────
// "Extract Text from Image" gives plain lines in reading order: status bar,
// chat title, then names, message lines, unread counts and times mixed
// together. Names are recognised by their shape and by always being followed
// by a message line.

const SCREEN_TIME = /^((오전|오후|AM|PM)\s*)?\d{1,2}\s*[:.]\s*\d{2}(\s*(AM|PM|오전|오후))?$/i;
const SCREEN_COUNT = /^\d{1,4}$/;
const SCREEN_UI = /^(enter a message|메시지 입력|send|전송|search|검색|#|[345]G|LTE|Wi-?Fi|SKT|KT|LG U\+|SOS)$/i;
const REPLY_EN = /^Reply to\s+(.+)$/i;
const REPLY_KO = /^(.+?)(에게|님에게) 답장$/;
const SURNAMES = "김이박최정강조윤장임한오서신권황안송류유전홍고문양손배백허남심노하곽성차주우구민나진지엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥육인맹제모탁국어은편용예봉경사부";
const KO_NOT_NAMES = new Set([
  "이거", "이건", "이게", "이제", "이번", "이미", "이따", "오늘", "오케이", "정말", "진짜", "조금", "최고",
  "강추", "안녕", "신기", "장난", "우와", "고마워", "고맙습니다", "감사", "감사해요", "축하", "축하해",
  "하하", "허허", "호호", "전부", "전혀", "모두", "모레", "내일", "어제", "지금", "나중", "방금", "정답",
  "인정", "동의", "찬성", "반대", "참석", "불참", "확인", "완료", "대박", "미친", "최악", "조심",
]);
const EN_NOT_NAMES = new Set([
  "yes", "no", "ok", "okay", "thanks", "thank you", "lol", "same", "nice", "sure", "wow", "haha", "good",
  "great", "cool", "agreed", "done", "me", "hi", "hello", "hey", "bye", "sorry", "congrats", "true",
  "valid", "what", "why", "when", "where", "who", "how", "oh", "omg", "yeah", "yep", "nope", "noted",
  "perfect", "awesome", "photo", "video", "emoticon", "file", "deleted message",
]);

function screenKind(t) {
  if (SCREEN_COUNT.test(t)) return "count";
  if (!/[가-힣ㄱ-ㅎㅏ-ㅣA-Za-z]/.test(t)) return "noise";  // reactions, symbols, battery %
  if (SCREEN_TIME.test(t)) return "time";
  if (DATE_LINE.test(t)) return "date";
  if (SCREEN_UI.test(t) || SYSTEM.test(t)) return "noise";
  if (REPLY_EN.test(t) || REPLY_KO.test(t)) return "reply";
  return "text";
}

// Given names used on their own ("재영"): only trusted where a name always
// sits — at the top, or right after a timestamp or date line.
const GIVEN_NAME_END = /[다요죠네까지야어아워해래데니자게군도고서면는은를을에로와과랑만뿐함음임듯요]$/;
function looksLikeGivenName(t) {
  return /^[가-힣]{2,3}$/.test(t) && !KO_NOT_NAMES.has(t) && !GIVEN_NAME_END.test(t);
}

function looksLikeName(t) {
  if (MEMBERS.includes(t)) return true;
  if (t.length > 24 || /[.!?~,…]$/.test(t)) return false;
  if (/[가-힣]/.test(t)) {
    // Korean name, optionally with a (nickname) or an English name after it
    const m = t.match(/^([가-힣]{2,5})(\s*\([^()]{1,20}\))?((\s+[A-Za-z][A-Za-z.]*){0,3})$/);
    if (!m || KO_NOT_NAMES.has(m[1])) return false;
    return SURNAMES.includes(m[1][0]) || m[1].startsWith("남궁") || m[1].startsWith("선우") || m[1].startsWith("제갈");
  }
  if (EN_NOT_NAMES.has(t.toLowerCase())) return false;
  return /^[A-Z][A-Za-z.'-]{0,11}( [A-Z][A-Za-z.'-]{0,11})?$/.test(t);
}

function parseScreen(raw) {
  const lines = String(raw).replace(/\r\n?/g, "\n").split("\n").map(s => s.trim()).filter(Boolean);
  let items = lines.map(text => ({ text, kind: screenKind(text) }));

  // Chat title at the top: the first text line, followed by the member count
  // either on the next line or on the same line ("스터디 그룹 42").
  const first = items.findIndex(i => i.kind === "text");
  if (first >= 0 && first <= 3 &&
      ((items[first + 1] && items[first + 1].kind === "count") || /\s\d{1,4}$/.test(items[first].text))) {
    items[first].kind = "noise";
  }
  items = items.filter(i => i.kind !== "noise" && i.kind !== "count");

  // The line after "Reply to X" is the quoted message, not new text.
  for (let i = 0; i < items.length - 1; i++) {
    if (items[i].kind === "reply" && items[i + 1].kind === "text") items[i + 1].kind = "quote";
  }

  // A name is a name-shaped line followed by a message (or a reply), unless
  // that next line is itself the name (e.g. a short message, then a name).
  const isName = new Array(items.length).fill(false);
  for (let i = items.length - 1; i >= 0; i--) {
    const it = items[i];
    const next = items[i + 1];
    const prev = items[i - 1];
    const atNameSpot = !prev || prev.kind === "time" || prev.kind === "date";
    isName[i] = it.kind === "text" && (looksLikeName(it.text) || (atNameSpot && looksLikeGivenName(it.text))) && !!next &&
      (next.kind === "reply" || (next.kind === "text" && !isName[i + 1]));
  }

  const groups = [];
  let cur = null;
  let afterTime = false;
  const start = sender => { cur = { sender, replyTo: "", lines: [] }; groups.push(cur); };
  items.forEach((it, i) => {
    if (it.kind === "time") { afterTime = true; return; }
    if (it.kind === "date") {
      // A new day: shown as a divider; messages after it start fresh.
      groups.push({ divider: it.text.replace(/[\s\-=>›〉)]+$/, "").replace(/^[\s\-=]+/, "") });
      cur = null;
      afterTime = true;
      return;
    }
    if (it.kind === "quote") return;
    if (isName[i]) { start(it.text); afterTime = false; return; }
    if (it.kind === "reply") {
      if (!cur || afterTime) start(cur ? "?" : "");
      const m = it.text.match(REPLY_EN) || it.text.match(REPLY_KO);
      cur.replyTo = m[1].trim();
      afterTime = false;
      return;
    }
    // Message text with no name above it after a timestamp: it's yours, or the
    // same person a minute later — the screen alone can't tell, so mark it "?".
    if (!cur || afterTime) start(cur || groups.length ? "?" : "");
    cur.lines.push(it.text);
    afterTime = false;
  });
  return groups
    .filter(g => g.divider || g.lines.length)
    .map(g => (g.divider ? g : { sender: g.sender, replyTo: g.replyTo, text: g.lines.join(" ") }));
}

function buildScreenDigest(pending, translations) {
  const { groups } = pending;
  const out = [];
  if (!groups.some(g => !g.divider)) {
    out.push("No chat messages found on the screen. Open the KakaoTalk chat, then run the Shortcut.");
  }
  let t = 0;
  groups.forEach((g, i) => {
    if (i) out.push("");
    if (g.divider) {
      out.push(`── ${g.divider} ──`);
      return;
    }
    const who = g.sender === "" ? "[… earlier]" : `[${g.sender}]`;
    out.push(g.replyTo ? `${who} ↩ replying to ${g.replyTo}` : who);
    out.push(g.text);
    if (SYLLABLE.test(g.text)) {
      const tr = translations[t++];
      out.push(`→ ${tr === undefined ? "(not translated)" : tr.trim()}`);
    } else {
      const meaning = JAMO_MEANINGS.find(([re]) => re.test(g.text));
      if (meaning) out.push(`→ ${meaning[1]}`);
    }
  });
  if (pending.raw) out.push("", "── Text read from the screen ──", pending.raw);
  return out.join("\n");
}

// ── Output ────────────────────────────────────────────────────────────────

function buildDigest(pending, translations) {
  if (pending.mode === "screen") return buildScreenDigest(pending, translations);
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

const PENDING_MAX_AGE_MS = 2 * 60 * 1000;  // step 2 always follows step 1 within seconds
const MAX_PENDING = 5;

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

// Current Shortcut layout for step 2: one Text action containing
//     <the text from Extract Text>
//     KT-TRANSLATIONS
//     <Repeat Results>
// so step 2 can rebuild everything without relying on anything saved by step 1.
const MARK_ANYWHERE = /KT\s*[-‐‑‒–—_]?\s*TRANSLATIONS/i;

function splitCombined(param) {
  if (param == null) return null;
  const text = asText(param).replace(/\r\n?/g, "\n");
  const m = text.match(MARK_ANYWHERE);
  if (!m) return null;
  const after = text.slice(m.index + m[0].length);
  if (after.trim().startsWith(SEP)) return null;  // older "KT-TRANSLATIONS@@@…" layout
  return { source: text.slice(0, m.index), translations: parseTranslationList(after) };
}

// Repeat Results inside a Text action arrives either one per line, or (on
// recent iOS) as a bracketed list on one line: ["One","Two"].
function parseTranslationList(text) {
  const t = text.trim();
  if (t.startsWith("[") && t.endsWith("]")) {
    try {
      const list = JSON.parse(t);
      if (Array.isArray(list)) return list.map(x => String(x).trim()).filter(Boolean);
    } catch (_) { /* not strict JSON — fall through to the lenient reading */ }
    const inner = t.slice(1, -1).trim().replace(/^"/, "").replace(/"$/, "");
    return inner
      .split(/"\s*,?\s*"/)  // item boundaries: "," or "" (Shortcuts sometimes drops the comma)
      .map(x => x.replace(/\\"/g, '"').replace(/\\n/g, " ").trim())
      .filter(Boolean);
  }
  return t.split("\n").map(l => l.trim()).filter(Boolean);
}

// Small stable fingerprint of the screen text, to recognise the same screen arriving twice.
function fingerprint(text) {
  let h = 2166136261;
  for (const ch of String(text).replace(/\s+/g, " ").trim()) h = Math.imul(h ^ ch.codePointAt(0), 16777619) >>> 0;
  return h.toString(16);
}

// Older layout (step 2 gets only Repeat Results): is this step 1's input?
// Step 2 sends a list, nothing, or one or two short lines; screen text has
// bare time lines and several lines.
function isStepOneInput(param) {
  if (markedTranslations(param) !== null) return false;
  const items = Array.isArray(param) ? param.map(String) : asText(param).split("\n");
  const lines = items.map(l => l.trim()).filter(Boolean);
  if (!lines.length) return false;
  if (parseExport(items.join("\n")).messages.length) return true;
  if (lines.some(l => SCREEN_TIME.test(l))) return true;
  if (lines.length === 1 && /\.(txt|zip)$/i.test(lines[0])) return true;  // a file name instead of the file
  if (Array.isArray(param)) return false;
  return lines.length > 2;
}

function livePendings(state, now) {
  const list = state.pendings || (state.pending ? [state.pending] : []);
  delete state.pending;  // older single-run layout
  return list.filter(p => p && now - (p.createdAt || 0) < PENDING_MAX_AGE_MS);
}

function savePending(state, store, pending, now) {
  state.pendings = livePendings(state, now).concat(pending).slice(-MAX_PENDING);
  store.save(state);
}

const SAME_SCREEN_MS = 60 * 1000;
const WRONG_LAST_INPUT = "The last Run Script received the screen text instead of the translations. " +
  "Set its input to the Text action just above it (the one with Text from Image, KT-TRANSLATIONS and " +
  "Repeat Results), not to Text from Image.";
const LOST_TRACK = "Kakao Translate lost track of this run. Please run it again — and to stop this " +
  "happening, update the Shortcut so the last Run Script gets the screen text too (see the guide, step 5).";
const NO_TEXT = "The script received no text. In the Shortcut, set the first Run Script's input to the " +
  "text from Extract Text (not Repeat Item), and check it comes right after Extract Text.";

const forTranslate = text => text.replace(/\s*\n\s*/g, " ");

// Work out the messages to show and the Korean texts to translate. Pure: the
// same input always gives the same result, so step 2 can simply redo it.
function prepare(raw, state, now) {
  const { title, messages } = parseExport(raw);
  if (!messages.length) {
    if (!raw.trim()) return { pending: { awaiting: true, createdAt: now, expected: 0, error: NO_TEXT }, toTranslate: [] };
    if (/^[^\n]*\.(txt|zip)\s*$/i.test(raw.trim())) {
      return {
        pending: {
          awaiting: true, createdAt: now, expected: 0,
          error: `The Shortcut passed the file name ("${raw.trim()}") instead of its contents. ` +
            "Add a Text action containing Shortcut Input before the first Run Script, and pass that Text instead.",
        },
        toTranslate: [],
      };
    }
    const groups = parseScreen(raw);
    const toTranslate = groups.filter(g => !g.divider && SYLLABLE.test(g.text)).map(g => forTranslate(g.text));
    return {
      pending: { mode: "screen", awaiting: true, createdAt: now, expected: toTranslate.length, groups,
        raw: SHOW_SCREEN_TEXT ? raw : "" },
      toTranslate,
    };
  }

  // Exports: find where you left off — this chat's saved position, or any
  // saved position that matches (in case the export's first line changed).
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
  const toTranslate = fresh.filter(m => SYLLABLE.test(m.text)).map(m => forTranslate(m.text));
  return {
    pending: {
      awaiting: true, createdAt: now, expected: toTranslate.length, title: chatKey, note,
      messages: fresh, anchor: messages.slice(-ANCHOR_LEN).map(keyOf),
    },
    toTranslate,
  };
}

function finish(state, store, pending, translations) {
  const expected = pending.expected || 0;
  const used = expected === 0 ? [] : translations;  // with nothing to translate, the placeholder's translation is ignored
  let output = buildDigest(pending, used);
  if (expected && used.length !== expected && !pending.error) {
    output += "\n\n(Some translations may not line up with their messages — try again if they look wrong.)";
  }
  if (!pending.error && pending.mode !== "screen") state.chats[pending.title] = { anchor: pending.anchor };
  store.save(state);
  return output;
}

function handle(param, store, now = Date.now()) {
  const state = store.load();
  state.chats = state.chats || {};
  const pendings = livePendings(state, now);

  // Step 2, current layout: screen text + translations together. No saved state needed.
  const combined = splitCombined(param);
  if (combined) {
    const { pending } = prepare(combined.source, state, now);
    const fp = fingerprint(combined.source);
    state.pendings = pendings.filter(p => p.fingerprint !== fp);
    return { output: finish(state, store, pending, combined.translations) };
  }

  // Step 2, older layout: only the translations; match them to step 1's saved run.
  if (!isStepOneInput(param)) {
    const translations = markedTranslations(param) || asList(param);
    const fits = p => (p.expected || 0) === translations.length || ((p.expected || 0) === 0 && translations.length <= 1);
    const pending = pendings.slice().reverse().find(fits);
    if (!pending) {
      state.pendings = pendings;
      store.save(state);
      if (!asText(param).trim()) {
        // Nothing passed and no run in progress: most likely the first Run Script's input is wrong.
        savePending(state, store, { awaiting: true, createdAt: now, expected: 0, error: NO_TEXT }, now);
        return { output: [] };
      }
      return { output: LOST_TRACK };
    }
    state.pendings = pendings.filter(p => p !== pending);
    return { output: finish(state, store, pending, translations) };
  }

  // Step 1: the Shortcut passes screenshot text or an exported chat.
  const raw = asText(param);
  const fp = fingerprint(raw);
  if (raw.trim() && pendings.some(p => p.fingerprint === fp && now - p.createdAt < SAME_SCREEN_MS)) {
    // The same screen text again seconds later, with no translations: almost
    // certainly the last Run Script is set to the screen text instead of the Text action.
    state.pendings = pendings.filter(p => p.fingerprint !== fp);
    store.save(state);
    return { output: WRONG_LAST_INPUT };
  }
  const { pending, toTranslate } = prepare(raw, state, now);
  pending.fingerprint = fp;
  savePending(state, store, pending, now);
  return { output: toTranslate };
}

// What the Shortcut gets back. Never an empty list (Scriptable reports that
// as an error and the Shortcut stops): when there's nothing to translate, a
// placeholder word goes through Translate instead and is ignored in step 2.
// Errors become a message shown at the end instead of stopping the Shortcut.
const NOTHING = "확인";

function runStep(param, store, now = Date.now()) {
  let output;
  try {
    output = handle(param, store, now).output;
  } catch (e) {
    const message = `Kakao Translate hit a problem: ${(e && e.message) || e}`;
    try {
      savePending(store.load(), store, { awaiting: true, createdAt: now, expected: 0, error: message }, now);
    } catch (_) { /* storage itself failed; the message below still shows */ }
    return message;
  }
  if (Array.isArray(output) && output.length === 0) return [NOTHING];
  return output;
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

  // Started by Shortcuts' Run Script? Scriptable sets config.runsInApp only
  // when the script is opened in the app itself; a Shortcut may also pass a
  // parameter while running it in the app.
  const fromShortcut = !config.runsInApp || (args.shortcutParameter !== undefined && args.shortcutParameter !== null);
  if (fromShortcut) {
    let output;
    try {
      let param = args.shortcutParameter;
      const path = typeof param === "string" ? param.trim() : "";
      if (/^\/.*\.txt$/i.test(path) && fm.fileExists(path)) param = fm.readString(path);
      output = runStep(param, store);
    } catch (e) {
      output = `Kakao Translate hit a problem: ${(e && e.message) || e}`;
    }
    Script.setShortcutOutput(output);
    Script.complete();
  } else {
    const alert = new Alert();
    alert.title = `Kakao Translate (version ${VERSION})`;
    alert.message = "Open a KakaoTalk chat and double-tap the back of your iPhone (or run the " +
      "\"Kakao Translate\" Shortcut).\n\nReset forgets saved positions for exported chats.";
    alert.addDestructiveAction("Reset");
    alert.addCancelAction("Close");
    if ((await alert.present()) === 0) {
      store.save({});
    }
    Script.complete();
  }
})();

if (typeof module !== "undefined") {
  module.exports = {
    parseExport, parseLine, parseScreen, looksLikeName, findAfterAnchor, buildDigest, handle, runStep,
    MARK, SEP, NOTHING,
  };
}
