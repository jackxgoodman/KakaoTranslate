# KakaoTranslate for iPhone (no computer needed)

Open a KakaoTalk chat and **double-tap the back of your iPhone**. The Shortcut reads the messages on screen, works out who said what, translates the Korean with Apple's built-in Translate (free, works offline once Korean is downloaded), and shows an easy-to-read list:

```
[김민준]
언제가면되려나?
→ When should I go?

[이서연]
LA를 안가봐서 못해주겠습니다
→ I can't do it because I haven't been to LA

[박도윤] ↩ replying to 이서연
valid
```

- Timestamps, unread counts, the status bar, the chat title, the message box and quoted reply text are left out.
- A sender's wrapped lines and back-to-back bubbles are joined into one message.
- `[… earlier]` means the sender's name is above the top of the screen. `[?]` means the message came after a timestamp with no name above it — either your own message or the same person a minute later; the screen alone can't tell.
- It translates what's on screen. To catch up on more, scroll up and double-tap again.

You need: **Scriptable** (free, App Store) and the built-in **Shortcuts** app.

---

## 1. Install the script (about 2 minutes)

1. Install **Scriptable** from the App Store and open it once.
2. On your iPhone, open `ios/KakaoTranslate.js` from this repository on GitHub (signed in to GitHub in Safari or the GitHub app), tap **Raw**, then select all the text and **Copy**.
3. In Scriptable, tap **+** (top right), paste the code, and tap the title at the top to rename the script to exactly **Kakao Translate**. Tap **Done**. If you already have a **Kakao Translate** script, open it, select all, and paste over it.
4. **Optional but recommended:** near the top of the script, put your chat members' names, exactly as KakaoTalk shows them, between the brackets of `MEMBERS`, e.g. `const MEMBERS = ["양영환", "박성준", "Erik", "Y"];`. Without it the script recognises most names by their shape; with it, every listed name is recognised.

## 2. Make the Shortcut (about 5 minutes)

If you already made the Back Tap shortcut (*Take Screenshot → Extract Text from Image → Translate → Quick Look*), edit that one. The finished shortcut must contain these steps, in this order:

| # | Action | Settings |
|---|---|---|
| 1 | **Take Screenshot** | — |
| 2 | **Extract Text from Image** | Input: **Screenshot** |
| 3 | **Run Script** (Scriptable) | Script: **Kakao Translate** · Parameter: the text from step 2 (shown as **Text from Image** or **Extracted Text**, with the same icon as step 2) — **not** *Repeat Item* · *Run In App* off |
| 4 | **Repeat with Each** | Repeat with each item in **Script Output** |
| 4a | ↳ **Translate Text** (inside the repeat) | Translate **Repeat Item** (not *Text from Image*) from **Korean** to **English** |
| 5 | **Run Script** (Scriptable), after *End Repeat* | Script: **Kakao Translate** · Parameter: **Repeat Results** · *Run In App* off |
| 6 | **Quick Look** | Input: **Script Output** from step 5 (the `{ }` Scriptable icon — not the Translate icon) |

How to do the basic moves in the editor:
- **Add an action:** use the action search field and type the action's name; tap the result to add it to the end. Scriptable's action is **Run Script**.
- **Change a value:** tap the blue word in the action (e.g. *Script*, *Parameter*, a language) and pick from the list. Earlier results — **Text from Image**, **Script Output**, **Repeat Results** — appear in that list.
- **Move an action:** touch and hold it, then drag. *Translate Text* must sit **between** *Repeat with Each* and *End Repeat*.
- **Run In App:** on Scriptable's Run Script action this option may be behind a **>** or *Show More*; keep it **off**.
- If you're editing the old shortcut, delete its old *Translate Text* (the one outside the repeat), and make sure the last action shows **Script Output**, not *Translated Text*.

Then:
1. **Run it once from the Shortcuts app** (tap the shortcut). It will translate the Shortcuts screen itself — that's fine. Answer **Always Allow** to the questions about taking screenshots, running the script and using Translate. Back Tap can't show these questions, so until they're answered the shortcut silently stops.
2. **Set up Back Tap:** Settings → Accessibility → Touch → **Back Tap** → **Double Tap** → choose the shortcut (listed under *Shortcuts*).
3. **Optional — offline translation:** Settings → Apps → Translate → Downloaded Languages → **Korean**.

## 3. Use it

Open the group chat in KakaoTalk and double-tap the back of the phone. Read the list, then swipe it away. Scroll up and repeat for older messages.

## Troubleshooting

| What you see | Fix |
|---|---|
| Nothing appears after double-tapping | Run the shortcut once from the Shortcuts app and allow everything (section 2, "Then", step 1). Turn on Settings → Notifications → **Shortcuts** so errors show. If still nothing, replace **Quick Look** with **Show Result** (input **Script Output**). |
| "Script completed without presenting UI…" in red above the first Run Script, or "The script received no text" | The first Run Script's input is wrong (often *Repeat Item*, which is empty outside the repeat). Tap it and choose the text from **Extract Text**. Also re-copy the latest script. |
| "No chat messages found on the screen" | The screenshot had no chat text. Open the chat first. |
| A name is shown as a message, or a message as a name | Add the member names to `MEMBERS` in the script (section 1, step 4). |
| Translations missing ("(not translated)") | Check *Translate Text* is inside the repeat and step 5's parameter is **Repeat Results**. |
| Something else looks wrong | In the script set `SHOW_SCREEN_TEXT = true`, run it again, and send the "Text read from the screen" part (replace the names) so the script can be adjusted. |
| Want to reset | Open Scriptable, tap **Kakao Translate**, choose **Reset** (only affects exported chats). |

The same Shortcut also accepts a KakaoTalk chat **export** (for example one saved to the Files app from a computer) and then shows only the messages since the last export. On iPhone, KakaoTalk only exports to an email draft, so the screen method is the practical one.
