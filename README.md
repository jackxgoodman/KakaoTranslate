# KakaoTranslate

Watches a KakaoTalk group chat on a Windows PC, translates new Korean messages into English (offline, free), and sends them to your **My Chatroom** (나와의 채팅), which syncs to your phone.

```
[김민준] 언제가면되려나?
→ When should I go?

[Alex] Every day is national galbi day for me
```

## Three versions

| | How it reads the chat | Pros | Cons |
|---|---|---|---|
| **v3** `main_v3.py` (recommended) | Selects all + copies the chat's message list via Win32 messages, reads the clipboard | Exact text and names, no OCR model, near-zero CPU, windows can be covered, works at any text size | Depends on KakaoTalk's window internals — run `test_v3.py` to confirm your version works |
| **v2** `main_v2.py` | Captures the window, OCRs it, and reads the visual layout (bubbles, names, profile pictures, grey reply quotes) | Works with any app version that looks like KakaoTalk | OCR misreads some Korean; needs a model or the Windows Korean OCR pack |
| **v1** `main.py` | Screenshot + OCR, Korean text only, no sender names | Simplest | Least accurate |

All versions translate with **NLLB-200** (better on casual Korean) or **Argos Translate** (lighter) — see `TRANSLATOR` in `config.py`.

## Setup

1. **Install Python 3.9+** and **KakaoTalk for Windows**, then in the project folder:
   ```
   pip install -r requirements.txt
   ```
2. **Configure.** Create `config_local.py` next to `config.py` (git ignores it, so `git pull` never conflicts):
   ```python
   CHAT_NAME = "스터디 그룹"        # exact title of the group chat window
   SELF_CHAT_TITLE = "Your Name"   # exact title of your My Chatroom window
   ```
   Any other setting from `config.py` can be overridden here too.
3. **Prepare KakaoTalk.** Double-click the group chat and My Chatroom in KakaoTalk so each opens as its **own window**. For v2/v3 they can sit behind other windows; don't minimise the group chat for v2. Keep the group chat scrolled to the bottom.
4. **v2 only — optional but recommended:** install Windows' Korean OCR, which is faster and more accurate than easyocr. In an **admin PowerShell**:
   ```
   Add-WindowsCapability -Online -Name "Language.OCR~~~ko-KR~0.0.1.0"
   ```
5. **Test, then run.**
   ```
   python test_v3.py        (or test_v2.py / test.py)
   python main_v3.py        (or main_v2.py / main.py)
   ```
   `test_v3.py` writes `v3_clipboard_dump.txt`; `test_v2.py` writes `debug_v2.png` showing how each piece of text was classified. Add `--no-send` to skip the test DM.

The first run downloads the translation model (~2.5 GB for NLLB, ~150 MB for Argos).

## Sending translations to other people too

1. In KakaoTalk, double-click your 1:1 chat with that person so it opens as its **own window**, and leave it open.
2. Add the exact text from that window's title bar to `config_local.py`:
   ```python
   EXTRA_RECIPIENTS = ["홍길동"]            # several people: ["홍길동", "Alex"]
   ```
3. Check it with `python test_v3.py` (section 1 should say the window is found). `python test_v3.py --send-all` also sends them a test DM.

Every translation then goes to your My Chatroom and to each listed chat, sent from your account. The group chat being translated is never used as a recipient.

## Auto-start after reboot

1. Set `AUTOSTART_VERSION = 3` (or 1 / 2) in `config_local.py`.
2. Right-click `install_task.bat` → **Run as administrator**. It starts the chosen version 60 s after login.
3. Turn on **KakaoTalk → Settings → General → Run KakaoTalk when Windows starts**, and set Windows to never sleep.

Logs: `kakaotranslate.log`, `kakaotranslate_v2.log`, `kakaotranslate_v3.log`. Remove auto-start with `uninstall_task.bat`.

## Settings worth knowing (`config.py`)

| Setting | Default | Meaning |
|---|---|---|
| `TRANSLATOR` | `"nllb"` | `"nllb"` (better, ~2.5 GB RAM) or `"argos"` (light) |
| `EXTRA_RECIPIENTS` | `[]` | Chat window titles of other people who also get the DMs |
| `BATCH_DMS` | `True` | One DM per check with all new messages |
| `INCLUDE_OWN_MESSAGES` | `False` | Also translate your own messages |
| `OCR_ENGINE` | `"auto"` | v2: `"windows"`, `"easyocr"` or `"auto"` |
| `HEADER_HEIGHT` | `None` | v2: set only if the chat header isn't detected |
| `SEND_METHOD_V3` | `"auto"` | v3: `"message"` (no focus change) or `"keyboard"` |

## Troubleshooting

| Symptom | Fix |
|---|---|
| v3: "Couldn't copy the chat's messages" | Run `test_v3.py` and check section 1 lists a message list and input box for the chat |
| v3: messages parsed wrongly | Send a few lines of `v3_clipboard_dump.txt` so the parser can be adjusted |
| v2: wrong or missing senders | Open `debug_v2.png` after `test_v2.py` to see what was detected |
| v2: "Windows OCR unavailable" | Install the Korean OCR pack (setup step 4) or set `OCR_ENGINE = "easyocr"` |
| Window not found | Titles must match exactly; open the chat as its own window |
| v1/v2: click misses the input box | Increase `INPUT_BOX_Y_OFFSET` |
| NLLB fails to load | It falls back to Argos automatically; check the log for the reason |

## Development

`chat_parser.py`, `message_diff.py` and `chat_layout.py` are pure Python and tested on any OS:
```
python -m unittest discover -s tests -t .
```
