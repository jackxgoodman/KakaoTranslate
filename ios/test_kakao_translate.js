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

// Simulates the Shortcut: step 1, "translate" each item, step 2.
function runShortcut(store, exportText) {
  const toTranslate = kt.handle(exportText, store).output;
  const translations = toTranslate.map(t => `EN(${t})`);
  const step2 = kt.MARK + kt.SEP + translations.join(kt.SEP);
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

test("non-export input explains what to do", () => {
  const store = memoryStore();
  assert.deepStrictEqual(kt.handle("hello", store).output, []);
  assert.match(kt.handle(kt.MARK + kt.SEP, store).output, /Couldn't find any messages/);
  assert.match(kt.handle(kt.MARK + kt.SEP, memoryStore()).output, /Export Chats/);
});

test("tolerates a newline or space after the marker", () => {
  const store = memoryStore();
  kt.handle(KOREAN_EXPORT, store);
  const out = kt.handle(`${kt.MARK}\n@@@A@@@B`, store).output;
  assert.match(out, /→ A\n/);
  assert.match(out, /→ B\n/);
});

test("explains when the Shortcut passed a file name instead of the file", () => {
  const store = memoryStore();
  kt.handle("Talk_2026.10.14 15:12-1.txt", store);
  assert.match(kt.handle(kt.MARK + kt.SEP, store).output, /file name/);
});
