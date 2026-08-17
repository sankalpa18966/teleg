# Telegram Channel Media Transfer Tool

Telegram channel එකකින් තවත් channel එකකට media files transfer කරන්න Python tool එකක්.

## 🚀 Features

- පැරණි channel එකෙන් photos, videos, documents download කරයි
- නව channel එකට upload කරයි
- Original captions preserve කරයි
- Progress tracking
- Automatic rate limiting
- පසුව download කළ files delete කරන්න option එක

## 📋 Prerequisites

1. **Python 3.7+** installed
2. **Telegram API Credentials** - මෙන්න විදියට ගන්න:
   - https://my.telegram.org/apps වෙත යන්න
   - Login වෙන්න
   - Create new application එක click කරන්න
   - `API ID` සහ `API Hash` copy කරන්න

## 🔧 Installation

1. Dependencies install කරන්න:
```bash
py -m pip install -r requirements.txt
```

**Note:** Windows වල `python` වෙනුවට `py` command එක use කරන්න.

## ⚙️ Configuration

`telegram_media_transfer.py` file එක open කරලා මේ values edit කරන්න:

```python
# Your Telegram API credentials
API_ID = 'YOUR_API_ID'          # https://my.telegram.org/apps එකෙන් ගත්ත ID එක
API_HASH = 'YOUR_API_HASH'      # https://my.telegram.org/apps එකෙන් ගත්ත Hash එක
PHONE = 'YOUR_PHONE_NUMBER'     # ඔබේ phone number (e.g., '+94771234567')

# Channel details - find_channel_id.py run කරලා හොයා ගන්න
SOURCE_CHANNEL = 'Old Channel Name'  # Channel name, @username, හෝ ID
TARGET_CHANNEL = 'New Channel Name'  # Channel name, @username, හෝ ID
```

**Examples:**
```python
# Using channel name (username නැතිනම් මේක use කරන්න)
SOURCE_CHANNEL = "Tech Updates"
TARGET_CHANNEL = "My New Tech Channel"

# Using username (username තියෙනවනම්)
SOURCE_CHANNEL = "@oldchannel"
TARGET_CHANNEL = "@newchannel"

# Using numeric ID (find_channel_id.py එකෙන් ගත්තනම්)
SOURCE_CHANNEL = -1001234567890
TARGET_CHANNEL = -1009876543210
```

### Channel Username/ID හොයන විදිය:

#### Method 1: Automatic (ලේසිම විදිය) ✅

`find_channel_id.py` script එක run කරන්න:

```bash
python find_channel_id.py
```

මේක ඔබේ **සියලුම channels list කරයි** names, IDs, සහ usernames සමඟ. ඔබේ channels වල **Name** හෝ **ID** copy කරන්න.

#### Method 2: Manual

- Channel එකේ **username** තියෙනවනම්: `@username` විදියට දාන්න
- Channel එකේ **link** එක: `https://t.me/channelname` නම් `@channelname` දාන්න
- **Username නැති channel** (ඔබ join වෙලා ඉන්නවනම්):
  - Channel එකේ **exact name** එක use කරන්න (e.g., `"My Channel Name"`)
  - හෝ `find_channel_id.py` run කරලා ID එක ගන්න

## 🎯 Usage

### පළමුව: Channel IDs හොයා ගන්න

Username නැති channels නම්, මුලින්ම මේක run කරන්න:

```bash
py find_channel_id.py
```

මේක ඔබේ සියලුම channels **list කරයි names සහ IDs සමඟ**. ඔබට ඕනි channels වල name හෝ ID copy කරන්න.

### දෙවනුව: Media Transfer කරන්න

Script එක run කරන්න:

```bash
py telegram_media_transfer.py
```

### පළමු වතාවට run කරනකොට:

1. Script එක phone number එක verify කරන්න code එකක් එවයි
2. Code එක enter කරන්න
3. 2FA enabled නම් password එක enter කරන්න
4. Script එක automatically media transfer කරන්න පටන් ගනී

### Options Customize කරන්න:

`main()` function එකේ parameters edit කරන්න:

```python
await transfer.transfer_media(
    source=SOURCE_CHANNEL,
    target=TARGET_CHANNEL,
    limit=100,                    # 100 messages විතරක් transfer කරන්න (None = all)
    keep_caption=True,            # Original captions keep කරන්නද?
    delete_after_upload=True,     # Upload කළ පසු local files delete කරන්නද?
    delay=3                       # Messages අතර delay (seconds) - වැඩි කරන්න FloodWait errors නම්
)
```

## 📊 Example Output

```
✅ Successfully logged in!
📥 Fetching messages from @old_channel...
📊 Found 50 media messages to transfer

[1/50] Processing message...
✅ Downloaded: photo_2024_01_15.jpg
✅ Uploaded to @new_channel
🗑️ Deleted local file

[2/50] Processing message...
✅ Downloaded: video_2024_01_16.mp4
✅ Uploaded to @new_channel
🗑️ Deleted local file

...

==================================================
✅ Transfer completed!
📊 Success: 48/50
❌ Failed: 2/50
==================================================
```

## ⚠️ Important Notes

### Admin Access Requirements:

- **Source Channel (පැරණි)**: Admin access අවශ්‍ය නැහැ, channel එකේ messages බලන්න පුළුවන් නම් ඇති
- **Target Channel (නව)**: ඔබට එම channel එකට **messages post කරන්න permission** තියෙන්න ඕනි (admin හෝ posting rights)

### Private Channels:

- Private channels වලින් download කරන්න ඔබ member කෙනෙක් විය යුතුයි
- Target channel එකට upload කරන්න admin access හෝ posting rights ඕනි

### Rate Limits:

- Telegram rate limits තියෙනවා spam වලක්වන්න
- Script එක messages අතර **3 second delay** එකක් දාලා තියෙනවා
- FloodWait errors ආවොත් **automatically retry** කරයි
- ගොඩක් messages තියෙනවනම් time ගතවෙයි (100 messages = ~5-10 minutes)
- Delay එක වැඩි කරන්න පුළුවන් (5-10 seconds) errors වැඩි නම්

## 🛠️ Advanced Usage

### Specific message range එකක් transfer කරන්න:

Script එක modify කරන්න:

```python
# Get messages between specific IDs
messages = await self.client.get_messages(
    source,
    min_id=100,
    max_id=200
)
```

### Specific media types විතරක් (photos only):

```python
async for message in self.client.iter_messages(channel, limit=limit):
    if message.photo:  # Photos only
        messages.append(message)
```

## 🐛 Troubleshooting

### "FloodWaitError":
Telegram rate limits hit වුණා. Script එක **automatically wait කරයි** සහ retry කරයි. ඔබට කිසිම දෙයක් කරන්න වෙන්නේ නැහැ - wait කරන්න.

ගොඩක් FloodWait errors නම්:
- `delay` parameter එක වැඩි කරන්න (e.g., `delay=5` or `delay=10`)
- Messages ටිකක් ටිකක් transfer කරන්න (`limit=50` විදියට)

### "ChatWriteForbiddenError":
Target channel එකට messages post කරන්න permission නැහැ. Admin කෙනෙක්ට කියන්න permission දෙන්න.

### "ChannelPrivateError":
Channel එක private හෝ ඔබ member කෙනෙක් නෙමෙයි.

## 📝 Notes

- පළමු වතාවට run කරනකොට `session.session` file එකක් create වෙයි - මේක login details save කරයි
- Media files default වශයෙන් `telegram_downloads` folder එකට download වෙයි
- `delete_after_upload=True` set කරොත් disk space save වෙයි

## 🔐 Security

- API credentials secure කරන්න
- `session.session` file එක share නොකරන්න
- Public repositories වලට credentials commit නොකරන්න

## 📄 License

Free to use and modify!
