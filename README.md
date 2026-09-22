# KakaoTranslate

Watches a KakaoTalk group chat, translates every new Korean message into English, and sends the translation to your **나와의 채팅** (Note to Self). Because KakaoTalk syncs across devices, the translations appear on your iPhone in real time.

---

## How it works

```
KakaoTalk (Windows, group chat visible)
        ↓  Windows UI Automation reads text
    monitor.py  ──→  translator.py  ──→  messenger.py
                     (Google Translate,     (types into 나와의 채팅
                      free, no API key)      → syncs to iPhone)
```

The script polls the KakaoTalk window every 5 seconds using the Windows Accessibility API — no screen recording, no OCR, no paid APIs.

---

## Requirements

- Windows 10 / 11 (the computer must stay signed in — not locked)
- Python 3.9 or later → [python.org](https://www.python.org/downloads/)
- KakaoTalk for Windows → [kakaocorp.com](https://www.kakaocorp.com/page/service/service/KakaoTalk)

---

## Setup

### 1. Clone / download the project

```
git clone https://github.com/jackxgoodman/kakaotranslate.git
cd kakaotranslate
```

### 2. Install Python dependencies

Open **Command Prompt** or **PowerShell** in the project folder and run:

```
pip install -r requirements.txt
```

### 3. Configure

Open `config.py` in any text editor and set `CHAT_NAME` to the **exact** name of the group chat you want to monitor (copy-paste it from KakaoTalk):

```python
CHAT_NAME = "스터디 그룹"   # ← your group chat name here
```

### 4. Prepare KakaoTalk

Before starting the script, arrange KakaoTalk on your Windows PC like this:

1. Open KakaoTalk and log in.
2. Open the group chat (leave it visible on screen — don't minimize it).
3. Find **나와의 채팅** in the chat list → **double-click** it to open it as a **separate pop-out window**.
4. Both windows must remain visible on screen (not minimized) while the script runs.

> **Tip:** Disable your screen saver and set Windows power settings to *Never* sleep, so the script keeps working overnight.

### 5. Run

```
python main.py
```

You'll see output like:

```
10:32:05  INFO      Initialized. Skipped 47 existing messages. Watching for new ones…
10:35:12  INFO      KO  오늘 모임 몇 시예요?
10:35:12  INFO      EN  What time is today's meeting?
10:35:12  INFO      DM sent: [번역] What time is today's meeting?
```

Stop it at any time with **Ctrl+C**.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `CHAT_NAME is not set` | Set `CHAT_NAME` in `config.py` |
| `KakaoTalk window not found` | Make sure KakaoTalk is open and not minimized |
| `나와의 채팅 window not found` | Double-click '나와의 채팅' in KakaoTalk to open it as a pop-out window |
| Messages detected but not translated | Check internet connection; Google Translate is used |
| Click lands outside the input box | Increase `INPUT_BOX_Y_OFFSET` in `config.py` (try 60, 70, …) |
| No messages detected at all | KakaoTalk may not expose its chat text via accessibility. See *Alternative (OCR)* below |

---

## Alternative: OCR-based monitoring

If the UI Automation approach picks up no messages (some KakaoTalk versions use custom rendering that bypasses accessibility), you can fall back to screenshot + OCR:

1. Install [Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki) — during installation, check **Additional script data → Korean**.
2. `pip install pytesseract Pillow`
3. Replace the body of `ChatMonitor._get_visible_korean()` in `monitor.py` with a screenshot + `pytesseract.image_to_string(img, lang='kor')` call.

The OCR path is not included by default to keep setup lightweight.
