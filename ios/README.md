# KakaoTranslate for iPhone (no computer needed)

Whenever you want to catch up, export the chat from KakaoTalk and send it to the **Kakao Translate** Shortcut. It shows only the messages since your last run, each with an English translation:

```
스터디 그룹 — 3 new messages

[김민준] 2026. 10. 14. 오후 3:10
언제가면되려나?
→ When should I go?

[Alex] 2026. 10. 14. 오후 3:11
Every day is national galbi day for me

[Y] 2026. 10. 14. 오후 3:11
ㅋㅋㅋ
→ (laughing)
```

Nothing runs in the background. Translation uses Apple's built-in Translate (free, works offline once Korean is downloaded). The first time you use a chat it shows the last 30 messages.

You need: **Scriptable** (free, App Store) and the built-in **Shortcuts** app.

---

## 1. Install the script (about 2 minutes)

1. Install **Scriptable** from the App Store and open it once.
2. On your iPhone, open `ios/KakaoTranslate.js` from this repository on GitHub (signed in to GitHub in Safari or the GitHub app), tap **Raw**, then select all the text and **Copy**.
3. In Scriptable, tap **+** (top right), paste the code, and tap the title at the top to rename the script to exactly **Kakao Translate**. Tap **Done**.

## 2. Build the Shortcut (about 5 minutes)

Open **Shortcuts**, tap **+** to make a new shortcut, and name it **Kakao Translate**. Add these actions in order: tap **Search Actions** (bottom) and type the action's name.

1. **Turn on the share menu.** Tap the **ⓘ** (or the name at the top → **Details**) and turn on **Show in Share Sheet**. A block "Receive … from Share Sheet" appears at the top: tap the blue input types, tap **Clear**, then select only **Files** and **Text**.
2. **Text** — tap inside its box, then in the bar above the keyboard choose **Shortcut Input**.
3. **Run Script** (Scriptable) — tap *Script* → **Kakao Translate**. Tap *Parameter* → choose **Text** (from step 2). Tap the arrow **>** on the action and make sure **Run In App** is **off**.
4. **Repeat with Each** — it should read "Repeat with each item in **Script Output**". If not, tap the blue item and pick **Script Output**.
5. **Translate Text** — drag it *inside* the repeat (between "Repeat with Each" and "End Repeat"). Make it read "Translate **Repeat Item** from **Korean** to **English**" (tap each blue word to set it; choose Korean, not *Detect Language*).
6. **Combine Text** — below "End Repeat". Make it read "Combine **Repeat Results** with **Custom**", and type `@@@` in the custom box.
7. **Text** — type `KT-TRANSLATIONS@@@` and then, right after it (no space), insert **Combined Text** from the bar above the keyboard.
8. **Run Script** (Scriptable) — *Script* → **Kakao Translate**. *Parameter* → tap and choose **Select Variable**, then tap the **Text** action from step 7. **Run In App** off.
9. **Quick Look** — it should show **Script Output**.

Tap **Done**.

## 3. Use it

1. In KakaoTalk, open the group chat → **☰** (top right) → **⚙** (bottom right) → **Export Chats** → **Send text only** (Korean: 대화 내용 내보내기 → 텍스트만 보내기).
2. In the share menu, tap **Kakao Translate** (scroll the app row or tap **More** if you don't see it).
3. The first time, allow the Shortcut to run the script and to use Translate. Read the translations, then swipe the preview away.

Next time you do the same thing, you'll only see what's new since then. It works for several chats; each remembers its own place.

**Optional — faster offline translation:** Settings → Apps → Translate → Downloaded Languages → download **Korean**.

## Troubleshooting

| What you see | Fix |
|---|---|
| "Couldn't find any messages in that export" | The export format is different from what the script expects. Send a few lines of the exported file (replace the names) so it can be adjusted. |
| "Start the Shortcut from KakaoTalk's Export Chats share menu" | The script ran without a chat. Start from KakaoTalk as in step 3. |
| Nothing translated / "(not translated)" | Check step 5 is *inside* the repeat and step 6 uses **Repeat Results**. |
| Kakao Translate isn't in the share menu | Step 2.1: Show in Share Sheet must be on and **Files** must be selected. |
| Want to start over | Open Scriptable, tap **Kakao Translate**, choose **Reset**. |
