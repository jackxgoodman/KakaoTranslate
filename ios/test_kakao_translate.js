// Tests for KakaoTranslate.js. Run with: node --test ios/
const test = require("node:test");
const assert = require("node:assert");
const kt = require("./KakaoTranslate.js");

const KOREAN_EXPORT = `스터디 그룹 님과 카카오톡 대화
저장한 날짜 : 2026. 10. 14. 오후 3:12

2026년 10월 14일 화요일
2026. 10. 14. 오후 3:10, 김민준 : 언제가면되려나?
2026. 10. 14. 오후 3:10, 이서연 : LA를 안가봐서 못해주겠습니다
두 번째 줄입니다
홍길동님이 들어왔습니다.
2026. 10. 14. 오후 3:11, Alex : Every day is national galbi day for me
2026. 10. 14. 오후 3:11, Y : ㅋㅋㅋ
`;

const ENGLISH_EXPORT = `Talk with 스터디 그룹
Date Saved : Oct 14, 2026 at 3:12 PM

Tuesday, October 14, 2026
Oct 14, 2026 at 3:10 PM, 김민준 : 언제가면되려나?
Oct 14, 2026 at 3:11 PM, Alex : see you at 3 : 30
`;

const PC_EXPORT = `[김민준] [오후 3:10] 언제가면되려나?
[Alex] [3:11 PM] ok`;

function memoryStore() {
  let state = {};
  return { load: () => JSON.parse(JSON.stringify(state)), save: s => { state = JSON.parse(JSON.stringify(s)); } };
}

// Simulates the Shortcut: step 1, "translate" each item, step 2 with the list of
// translations (Shortcuts passes nothing when the list is empty and a plain
// string when it has one item).
function runShortcut(store, exportText) {
  const toTranslate = kt.handle(exportText, store).output;
  const translations = toTranslate.map(t => `EN(${t})`);
  const step2 = translations.length === 0 ? null : translations.length === 1 ? translations[0] : translations;
  return { toTranslate, digest: kt.handle(step2, store).output };
}

test("parses Korean phone exports, continuations, dates and system lines", () => {
  const { title, messages } = kt.parseExport(KOREAN_EXPORT);
  assert.strictEqual(title, "스터디 그룹");
  assert.deepStrictEqual(messages.map(m => m.sender), ["김민준", "이서연", "Alex", "Y"]);
  assert.strictEqual(messages[0].time, "2026. 10. 14. 오후 3:10");
  assert.strictEqual(messages[1].text, "LA를 안가봐서 못해주겠습니다\n두 번째 줄입니다");
});

test("parses English phone exports and keeps ' : ' inside messages", () => {
  const { title, messages } = kt.parseExport(ENGLISH_EXPORT);
  assert.strictEqual(title, "스터디 그룹");
  assert.deepStrictEqual(messages.map(m => [m.sender, m.text]), [
    ["김민준", "언제가면되려나?"],
    ["Alex", "see you at 3 : 30"],
  ]);
  assert.strictEqual(messages[0].time, "Oct 14, 2026 at 3:10 PM");
});

test("parses PC exports", () => {
  const { messages } = kt.parseExport(PC_EXPORT);
  assert.deepStrictEqual(messages.map(m => [m.sender, m.text]), [["김민준", "언제가면되려나?"], ["Alex", "ok"]]);
});

test("first run, then only new messages, then nothing new", () => {
  const store = memoryStore();

  const first = runShortcut(store, KOREAN_EXPORT);
  assert.deepStrictEqual(first.toTranslate, ["언제가면되려나?", "LA를 안가봐서 못해주겠습니다\n두 번째 줄입니다"]);
  assert.match(first.digest, /^스터디 그룹 — 4 new messages/);
  assert.match(first.digest, /First time for this chat/);
  assert.match(first.digest, /\[김민준\] 2026\. 10\. 14\. 오후 3:10\n언제가면되려나\?\n→ EN\(언제가면되려나\?\)/);
  assert.match(first.digest, /Every day is national galbi day for me\n\n/);  // English: no translation line
  assert.match(first.digest, /ㅋㅋㅋ\n→ \(laughing\)/);

  const later = KOREAN_EXPORT + "2026. 10. 14. 오후 4:00, 김민준 : 내일 봐요\n";
  const second = runShortcut(store, later);
  assert.deepStrictEqual(second.toTranslate, ["내일 봐요"]);
  assert.match(second.digest, /— 1 new message\n/);
  assert.doesNotMatch(second.digest, /First time/);

  const third = runShortcut(store, later);
  assert.deepStrictEqual(third.toTranslate, []);
  assert.match(third.digest, /no new messages since last time/);
});

test("finds your place even if the export's title line changes", () => {
  const store = memoryStore();
  runShortcut(store, KOREAN_EXPORT);
  const renamed = KOREAN_EXPORT.replace("스터디 그룹 님과", "새 이름 님과") + "2026. 10. 14. 오후 4:00, Y : 좋아\n";
  const run = runShortcut(store, renamed);
  assert.deepStrictEqual(run.toTranslate, ["좋아"]);
});

test("first run is limited to the most recent messages", () => {
  const store = memoryStore();
  let big = "스터디 그룹 님과 카카오톡 대화\n";
  for (let i = 0; i < 100; i++) big += `2026. 10. 14. 오후 3:${String(i % 60).padStart(2, "0")}, A : 메시지 ${i}\n`;
  const run = runShortcut(store, big);
  assert.strictEqual(run.toTranslate.length, 30);
  assert.strictEqual(run.toTranslate[29], "메시지 99");
});

test("a screen with no chat messages says so", () => {
  const store = memoryStore();
  assert.deepStrictEqual(kt.handle("3:47\n85\n5G", store).output, []);
  assert.match(kt.handle(null, store).output, /No chat messages found/);
  assert.match(kt.handle(kt.MARK + kt.SEP, memoryStore()).output, /Export Chats/);
});

test("still accepts the older marked-text layout", () => {
  const store = memoryStore();
  kt.handle(KOREAN_EXPORT, store);
  const out = kt.handle(`${kt.MARK}\n@@@A@@@B`, store).output;
  assert.match(out, /→ A\n/);
  assert.match(out, /→ B\n/);
});

test("explains when the Shortcut passed a file name instead of the file", () => {
  const store = memoryStore();
  kt.handle("Talk_2026.10.14 15:12-1.txt", store);
  assert.match(kt.handle(null, store).output, /file name/);
});

test("a fresh export is never mistaken for translations", () => {
  const store = memoryStore();
  kt.handle(KOREAN_EXPORT, store);  // step 1, then the run is abandoned
  const out = kt.handle(KOREAN_EXPORT + "2026. 10. 14. 오후 4:00, Y : 좋아\n", store).output;
  assert.ok(Array.isArray(out));
});

test("an abandoned run older than 10 minutes is ignored", () => {
  const store = memoryStore();
  kt.handle(KOREAN_EXPORT, store, 0);
  const out = kt.handle("Some translation", store, 11 * 60 * 1000).output;
  assert.ok(Array.isArray(out));  // treated as a (bad) export, not as step 2
});

test("one translation passed as plain text lines up correctly", () => {
  const store = memoryStore();
  const later = KOREAN_EXPORT + "2026. 10. 14. 오후 4:00, 김민준 : 내일 봐요\n";
  runShortcut(store, KOREAN_EXPORT);
  assert.deepStrictEqual(kt.handle(later, store).output, ["내일 봐요"]);
  assert.match(kt.handle("See you tomorrow", store).output, /내일 봐요\n→ See you tomorrow/);
});

// ── Screenshot text (what "Extract Text from Image" returns) ──────────────

// Modelled on a real KakaoTalk group chat screen; names replaced.
const SCREEN_1 = `3:47
5G
85
스터디 그룹
38
찬성
17
10:47 AM
김민준
언제가면되려나?
17
10:47 AM
이서연
LA를 안가봐서 못해주겠습니다
17
10:47 AM
Y
고마워 미리
17
10:47 AM
박도윤
Reply to 이서연
LA를 안가봐서 못해주겠습니다
valid
18
10:47 AM
Alex
Reply to 이서연
National Galbi Day
Every day is national galbi day for me
18
10:49 AM
♥ 2 3 1
Enter a message
Send`;

const SCREEN_2 = `스터디 그룹
38
최유나(Yuna)
9/24-9/25 치폴레 이벤트 있는 것 같아서 공
유 드려요 ㅎㅎ
23
10:23 AM
MK
쿼사디아 매우 좋아하긴 하는데...
26
내셔널 쿼사디아 데이가 있는줄은 꿈에
도 몰랐네
27
10:24 AM
Y
허얼 조져야지
27
10:25 AM
1
10:26 AM
나도 갈게`;

function runScreen(text) {
  const store = memoryStore();
  const toTranslate = kt.handle(text, store).output;
  const translations = toTranslate.map(t => `EN(${t})`);
  const step2 = translations.length === 0 ? null : translations.length === 1 ? translations[0] : translations;
  return { toTranslate, digest: kt.handle(step2, store).output };
}

test("screen text: senders, replies and noise", () => {
  const groups = kt.parseScreen(SCREEN_1);
  assert.deepStrictEqual(groups.map(g => [g.sender, g.text, g.replyTo]), [
    ["", "찬성", ""],
    ["김민준", "언제가면되려나?", ""],
    ["이서연", "LA를 안가봐서 못해주겠습니다", ""],
    ["Y", "고마워 미리", ""],
    ["박도윤", "valid", "이서연"],
    ["Alex", "Every day is national galbi day for me", "이서연"],
  ]);
});

test("screen text: wrapped lines and several bubbles are merged per sender", () => {
  const groups = kt.parseScreen(SCREEN_2);
  assert.deepStrictEqual(groups.map(g => [g.sender, g.text]), [
    ["최유나(Yuna)", "9/24-9/25 치폴레 이벤트 있는 것 같아서 공 유 드려요 ㅎㅎ"],
    ["MK", "쿼사디아 매우 좋아하긴 하는데... 내셔널 쿼사디아 데이가 있는줄은 꿈에 도 몰랐네"],
    ["Y", "허얼 조져야지"],
    ["?", "나도 갈게"],  // after a timestamp with no name: yours, or the same person later
  ]);
});

test("screen text: full Shortcut round trip gives an easy-to-read list", () => {
  const { toTranslate, digest } = runScreen(SCREEN_1);
  assert.deepStrictEqual(toTranslate, ["찬성", "언제가면되려나?", "LA를 안가봐서 못해주겠습니다", "고마워 미리"]);
  assert.strictEqual(digest, [
    "[… earlier]", "찬성", "→ EN(찬성)", "",
    "[김민준]", "언제가면되려나?", "→ EN(언제가면되려나?)", "",
    "[이서연]", "LA를 안가봐서 못해주겠습니다", "→ EN(LA를 안가봐서 못해주겠습니다)", "",
    "[Y]", "고마워 미리", "→ EN(고마워 미리)", "",
    "[박도윤] ↩ replying to 이서연", "valid", "",
    "[Alex] ↩ replying to 이서연", "Every day is national galbi day for me",
  ].join("\n"));
});

test("screen text: a single Korean message round trip", () => {
  const { digest } = runScreen("김민준\n언제가면되려나?\n10:47 AM");
  assert.strictEqual(digest, "[김민준]\n언제가면되려나?\n→ EN(언제가면되려나?)");
});

test("names: shapes that are and aren't names", () => {
  for (const n of ["김민준", "이서연", "최유나(Yuna)", "김지은 Jenny Kim", "Alex", "MK", "Y", "Sonny K"]) {
    assert.ok(kt.looksLikeName(n), n);
  }
  for (const n of ["찬성", "이거", "고마워", "좋아", "Yes", "Thanks", "valid", "언제가면되려나?", "ok"]) {
    assert.ok(!kt.looksLikeName(n), n);
  }
});

test("screen text is never mistaken for step 2", () => {
  const store = memoryStore();
  kt.handle("김민준\n언제가면되려나?\n10:47 AM", store);  // step 1 expecting 1 translation, then abandoned
  assert.ok(Array.isArray(kt.handle(SCREEN_1, store).output));
});

// ── Shortcut-facing wrapper (what Scriptable actually returns) ────────────

test("first Run Script given no text: explains the fix instead of failing", () => {
  const store = memoryStore();
  const step1 = kt.runStep(null, store);            // e.g. input set to Repeat Item outside the repeat
  assert.deepStrictEqual(step1, [kt.NOTHING]);      // never an empty list
  const out = kt.runStep("Confirm", store);         // Apple Translate's rendering of the placeholder
  assert.match(out, /received no text/);
  assert.match(out, /not Repeat Item/);
});

test("screen with only English: placeholder goes through Translate and is ignored", () => {
  const store = memoryStore();
  const step1 = kt.runStep("Alex\nsee you at the booth\n10:49 AM", store);
  assert.deepStrictEqual(step1, [kt.NOTHING]);
  assert.strictEqual(kt.runStep("Confirm", store), "[Alex]\nsee you at the booth");
});

test("normal screen through the wrapper", () => {
  const store = memoryStore();
  const step1 = kt.runStep("김민준\n언제가면되려나?\n10:47 AM", store);
  assert.deepStrictEqual(step1, ["언제가면되려나?"]);
  assert.strictEqual(kt.runStep("When should I go?", store), "[김민준]\n언제가면되려나?\n→ When should I go?");
});

test("an unexpected error becomes a readable message", () => {
  const broken = { load: () => { throw new Error("disk full"); }, save: () => {} };
  assert.match(kt.runStep("anything", broken), /hit a problem: disk full/);
});

// ── The Scriptable glue, run the way Shortcuts runs it ────────────────────

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const SOURCE = fs.readFileSync(path.join(__dirname, "KakaoTranslate.js"), "utf8");

// Runs the script once in a fake Scriptable environment; resolves with what it gave Shortcuts.
function runInScriptable({ param, runsInApp = false, files = {}, alertChoice = 1 }) {
  return new Promise(resolve => {
    const result = { output: undefined, completed: false, alerted: false };
    const sandbox = {
      args: { shortcutParameter: param },
      config: { runsInApp, runsWithSiri: !runsInApp },  // note: no runsFromShortcut — Scriptable has none
      Script: {
        setShortcutOutput: v => { result.output = v; },
        complete: () => { result.completed = true; setImmediate(() => resolve(result)); },
      },
      FileManager: {
        local: () => ({
          documentsDirectory: () => "/docs",
          joinPath: (a, b) => `${a}/${b}`,
          fileExists: p => p in files || p === "/docs/KakaoTranslate",
          readString: p => files[p],
          writeString: (p, s) => { files[p] = s; },
          createDirectory: () => {},
        }),
      },
      Alert: class {
        addDestructiveAction() {}
        addCancelAction() {}
        present() { result.alerted = true; return Promise.resolve(alertChoice); }
      },
      setImmediate,
    };
    vm.runInNewContext(SOURCE, sandbox);
  });
}

test("Scriptable glue: a Shortcut run returns values (no 'completed without outputting')", async () => {
  const files = {};
  const step1 = await runInScriptable({ param: "김민준\n언제가면되려나?\n10:47 AM", files });
  assert.ok(step1.completed);
  assert.deepStrictEqual(Array.from(step1.output), ["언제가면되려나?"]);
  const step2 = await runInScriptable({ param: "When should I go?", files });
  assert.strictEqual(step2.output, "[김민준]\n언제가면되려나?\n→ When should I go?");
});

test("Scriptable glue: a Shortcut run with no input still outputs something", async () => {
  const run = await runInScriptable({ param: null });
  assert.ok(run.completed);
  assert.ok(run.output && run.output.length > 0);
  assert.ok(!run.alerted);
});

test("Scriptable glue: opening the script in the app shows the menu", async () => {
  const run = await runInScriptable({ param: null, runsInApp: true });
  assert.ok(run.alerted);
  assert.ok(run.completed);
});

// Modelled on a real dark-mode screen with 24-hour times and a new day; names replaced.
const SCREEN_NEW_DAY = `01:30
스터디 그룹 42
박지훈씨 왜 c52를 점거하셨나요?
14
21:39
1
박지훈
ㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋ
14
21:40
박지훈
그게.. 보이나..?
14
차주 한국인들 휴식용 대형방임다
14
월수오후
14
21:41
Friday, October 16, 2026 >
김민준
Reply to 박지훈
지훈 유나 민준 서연 도윤...
유나 추가요 @최유나(Yuna)
24
00:14
최유나(Yuna)
감사합니다
감사합니다~
24
00:15
Enter a message`;

test("screen text: new-day date line, 24-hour times, title with member count", () => {
  const groups = kt.parseScreen(SCREEN_NEW_DAY);
  assert.deepStrictEqual(groups.map(g => (g.divider ? ["──", g.divider] : [g.sender, g.text, g.replyTo])), [
    ["", "박지훈씨 왜 c52를 점거하셨나요?", ""],
    ["박지훈", "ㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋ", ""],
    ["박지훈", "그게.. 보이나..? 차주 한국인들 휴식용 대형방임다 월수오후", ""],
    ["──", "Friday, October 16, 2026"],
    ["김민준", "유나 추가요 @최유나(Yuna)", "박지훈"],
    ["최유나(Yuna)", "감사합니다 감사합니다~", ""],
  ]);
});

test("screen text: the date shows as a divider in the results and isn't translated", () => {
  const { toTranslate, digest } = runScreen(SCREEN_NEW_DAY);
  assert.ok(!toTranslate.some(t => /October/.test(t)));
  assert.match(digest, /\n── Friday, October 16, 2026 ──\n/);
  assert.match(digest, /\[박지훈\]\nㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋ\n→ \(laughing\)/);
  assert.match(digest, /\[김민준\] ↩ replying to 박지훈\n유나 추가요 @최유나\(Yuna\)\n→ EN/);
});

test("screen text: Korean date lines too", () => {
  const groups = kt.parseScreen("김민준\n안녕\n10:00\n2026년 10월 16일 금요일 >\n김민준\n좋아요\n00:15");
  assert.deepStrictEqual(groups.filter(g => g.divider).map(g => g.divider), ["2026년 10월 16일 금요일"]);
});
