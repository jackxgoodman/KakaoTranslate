# KakaoTranslate for iPhone (no computer needed)

Whenever you want to catch up, export the chat from KakaoTalk (it arrives as an email attachment) and share that file to the **Kakao Translate** Shortcut. It shows only the messages since your last run, each with an English translation:

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

## 2. Make the Shortcut (about 5 minutes)

The shortcut has only five steps. Here is what the finished shortcut must contain — whichever way you build it, check it against this list:

| # | Action | Settings |
|---|---|---|
| 1 | **Receive** input from **Share Sheet** | Accepts **Files** and **Text** (appears when *Show in Share Sheet* is on) |
| 2 | **Run Script** (Scriptable) | Script: **Kakao Translate** · Parameter: **Shortcut Input** · *Run In App* off |
| 3 | **Repeat with Each** | Repeat with each item in **Script Output** |
| 3a | ↳ **Translate** (inside the repeat) | Translate **Repeat Item** from **Korean** to **English** |
| 4 | **Run Script** (Scriptable), after *End Repeat* | Script: **Kakao Translate** · Parameter: **Repeat Results** · *Run In App* off |
| 5 | **Quick Look** | Shows **Script Output** (from step 4) |

### Option A — let iOS build it (iOS 27 with Apple Intelligence)

1. Open **Shortcuts** and tap **+**. On the **Describe a Shortcut** screen, paste this:

   > Show this shortcut in the share sheet and accept files and text. Run the Scriptable script "Kakao Translate" with the shortcut input as its parameter. Then repeat with each item in that script's output: translate the item from Korean to English. After the repeat, run the Scriptable script "Kakao Translate" again with the repeat results as its parameter. Finally, show the output of that second script with Quick Look.

2. Review the steps it creates against the table above and fix anything that differs (tap a blue value to change it). The most common things to check: both scripts are **Kakao Translate**, the second one's parameter is **Repeat Results**, and Translate is set to **Korean → English** rather than *Detect Language*.
3. Name the shortcut **Kakao Translate** and save it.

### Option B — build it yourself in the editor

If tapping **+** opens *Describe a Shortcut* and you'd rather build it by hand, switch to the editor from that screen, or make the editor the default: **Settings → Apps → Shortcuts → Open shortcuts to → Editor**.

How to do the basic moves in the editor:
- **Add an action:** use the action search field in the editor and type the action's name; tap the result to add it to the end.
- **Change a value:** tap the blue word in the action (for example *Script*, *Parameter*, or a language) and pick from the list. To use a result from an earlier step, choose it from the variable list that appears (e.g. **Shortcut Input**, **Script Output**, **Repeat Results**).
- **Move an action:** touch and hold it, then drag.

Steps:
1. Name the shortcut **Kakao Translate**. Open its settings (**Details**, or the **ⓘ** / settings button, or the menu under the shortcut's name) and turn on **Show in Share Sheet**. A *Receive … from Share Sheet* block appears at the top — tap its input types and leave only **Files** and **Text** selected.
2. Add Scriptable's **Run Script**. Set *Script* to **Kakao Translate** and *Parameter* to **Shortcut Input**. If the action has a *Run In App* option (sometimes behind a **>** or *Show More*), make sure it's **off**.
3. Add **Repeat with Each** and set it to **Script Output** (it usually picks this automatically).
4. Add **Translate** (Apple's *Translate Text* action) and drag it **inside** the repeat, between *Repeat with Each* and *End Repeat*. Set it to translate **Repeat Item** from **Korean** to **English**.
5. Add another Scriptable **Run Script** below *End Repeat*. *Script*: **Kakao Translate**, *Parameter*: **Repeat Results**, *Run In App* off.
6. Add **Quick Look**; it should show **Script Output**.

## 3. Use it

KakaoTalk on iPhone exports a chat as an email attachment (a `.txt` file), so the file goes through Mail on its way to the Shortcut.

1. In KakaoTalk, open the group chat → **☰** (top right) → **⚙** (bottom right) → **Export Chats** → **Send text only** (Korean: 대화 내용 내보내기 → 텍스트만 보내기). A Mail draft opens with the chat attached.
2. **Try the quick way first:** touch and hold the attachment in the draft. If a menu with **Share** appears, tap it, choose **Kakao Translate**, and when you're done, cancel the draft (**Cancel → Delete Draft**).
3. **If there's no Share option in the draft:** enter your own email address in **To** and tap **Send**. Open that email in Mail, touch and hold the attachment (or tap it, then tap the **Share** button), and choose **Kakao Translate**.
4. The first time, allow the Shortcut to run the script and to use Translate. Read the translations, then swipe the preview away.

Tip: if you save the attachment with **Save to Files** instead, you can share it to Kakao Translate later from the **Files** app (touch and hold the file → **Share**).

Next time you do the same thing, you'll only see what's new since then. It works for several chats; each remembers its own place.

**Optional — faster offline translation:** Settings → Apps → Translate → Downloaded Languages → download **Korean**.

## Troubleshooting

| What you see | Fix |
|---|---|
| "Couldn't find any messages in that export" | The export format is different from what the script expects. Send a few lines of the exported file (replace the names) so it can be adjusted. |
| "Export the chat in KakaoTalk … and share the .txt attachment" | The script ran without a chat. Share the exported `.txt` attachment to the Shortcut as in section 3. |
| Nothing translated / "(not translated)" | Check the table above: Translate must be *inside* the repeat, and the second Run Script's parameter must be **Repeat Results**. |
| "The Shortcut passed the file name … instead of its contents" | Add a **Text** action containing **Shortcut Input** right after the Receive block, and set the first Run Script's parameter to that **Text**. |
| Kakao Translate isn't in the share menu | Show in Share Sheet must be on, and **Files** must be one of the accepted input types. In the share menu, scroll to the bottom and tap **Edit Actions** to add it if it's still hidden. |
| A step here doesn't match your screen | Send a screenshot of the Shortcuts editor (and your iOS version, from Settings → General → About) so these instructions can be corrected. |
| Want to start over | Open Scriptable, tap **Kakao Translate**, choose **Reset**. |
