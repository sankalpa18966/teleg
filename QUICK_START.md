# ⚡ Quick Start Guide - සිංහලෙන්

## Step 1: Install කරන්න

```bash
py -m pip install -r requirements.txt
```

**Note:** Windows වල `py` command එක use කරන්න (`python` නෙමෙයි).

## Step 2: API Credentials ගන්න

1. 🌐 https://my.telegram.org/apps වෙත යන්න
2. 📱 ඔබේ phone number එකෙන් login වෙන්න
3. ➕ "Create new application" click කරන්න
4. 📋 `API ID` සහ `API Hash` copy කරන්න

## Step 3: Channel IDs හොයන්න

### Option A: Automatic (Recommended) ✅

1. **find_channel_id.py** open කරන්න
2. API credentials fill කරන්න:
   ```python
   API_ID = '12345678'              # ඔබේ API ID
   API_HASH = 'abcdef1234567890'    # ඔබේ API Hash
   PHONE = '+94771234567'           # ඔබේ phone number
   ```

3. Run කරන්න:
   ```bash
   py find_channel_id.py
   ```

4. Output එකේ ඔබේ channels list වෙයි. Example:
   ```
   📢 CHANNELS:
   --------------------------------------------------------------------------------
   1. Name: Tech News LK
      ID: -1001234567890
      🔒 Private Channel (no username)

   2. Name: My Personal Channel
      ID: -1009876543210
      Username: @mypersonalchannel
      Link: https://t.me/mypersonalchannel
   ```

5. ඔබට transfer කරන්න ඕනි channels වල **Name** හෝ **ID** copy කරන්න

### Option B: Manual (Username තියෙනවනම්)

Channel link එකෙන් username එක extract කරන්න:
- Link: `https://t.me/techchannel` → Username: `@techchannel`

## Step 4: Main Script Configure කරන්න

**telegram_media_transfer.py** open කරන්න සහ edit කරන්න:

```python
# API Credentials
API_ID = '12345678'
API_HASH = 'abcdef1234567890'
PHONE = '+94771234567'

# Channels - find_channel_id.py එකෙන් copy කරපු values
SOURCE_CHANNEL = 'Tech News LK'           # පැරණි channel name
TARGET_CHANNEL = 'My Personal Channel'    # නව channel name

# හෝ ID use කරන්න (number විදියට, quotes නැතිව):
# SOURCE_CHANNEL = -1001234567890
# TARGET_CHANNEL = -1009876543210

# හෝ username use කරන්න (තියෙනවනම්):
# SOURCE_CHANNEL = '@oldchannel'
# TARGET_CHANNEL = '@newchannel'
```

## Step 5: Run කරන්න!

```bash
py telegram_media_transfer.py
```

### පළමු වතාවට:

1. 📱 Phone number verify කරන්න code එකක් එවයි
2. 💬 Code එක enter කරන්න terminal එකේ
3. 🔐 2FA enabled නම් password එක enter කරන්න
4. ✅ Login වුණාම automatically media transfer කරන්න පටන් ගනී

## 🎛️ Advanced Settings (Optional)

`telegram_media_transfer.py` file එකේ `main()` function එකේ:

```python
await transfer.transfer_media(
    source=SOURCE_CHANNEL,
    target=TARGET_CHANNEL,
    limit=None,                    # Options:
                                   # None = all messages
                                   # 50 = පළමු messages 50 විතරක්
                                   # 100 = පළමු messages 100 විතරක්
    
    keep_caption=True,             # True = captions keep කරන්න
                                   # False = captions delete කරන්න
    
    delete_after_upload=True,      # True = upload කළ පසු local files delete
                                   # False = files keep කරන්න
    
    delay=3                        # Seconds between uploads
                                   # 3 = default (recommended)
                                   # 5-10 = FloodWait errors වැඩි නම්
)
```

## ⚠️ Important

### Target Channel Permissions:

නව channel එකට upload කරන්න ඔබට එක්කෝ:
- **Admin** විය යුතුයි, හෝ
- **Post Messages** permission එක තිබිය යුතුයි

Admin නැත්නම්:
1. Channel admin කෙනෙක්ට කියන්න
2. ඔබව admin කරන්න හෝ "Post Messages" permission එක දෙන්න කියන්න

## 🎉 Done!

ඒ විතරයි! Script එක automatically:
- 📥 Media download කරයි
- ⬆️ Upload කරයි නව channel එකට
- 💬 Captions preserve කරයි
- 🗑️ Local files clean කරයි (option එක enable කරොත්)

## 📞 Need Help?

Problems තියෙනවනම් **README.md** file එකේ **Troubleshooting** section එක බලන්න!

---

# 🌐 Web Interface Guide

## Starting the Web App

```bash
py web_app.py
```

මේකෙන් web interface එක start වෙයි **http://localhost:3000** එකේ.

## Web Interface Features

### 1️⃣ **Credentials & Login Tab**
- API credentials enter කරන්න
- Telegram login කරන්න
- Login history බලන්න

### 2️⃣ **Find Channel IDs Tab**
- ඔබේ සියලු channels සහ groups list කරගන්න
- Channel IDs copy කරගන්න
- Private/Public channels identify කරන්න

### 3️⃣ **Media Transfer Tab**
- Source සහ target channels set කරන්න
- Media transfer process run කරන්න
- Real-time progress tracking
- Success/Failed/Skipped statistics

### 4️⃣ **Content Downloader Tab**
- Single message link එකක් paste කරන්න
- Media download කරගන්න ඔබේ device එකට
- හෝ වෙනත් channel එකක forward/upload කරන්න
- Real-time download progress

### 5️⃣ **Batch Downloader Tab** 📦 NEW!
- **Message range** එකක් download කරන්න (උදාහරණ: messages 1-50)
- **Automatic batching** - 6GB බැගින් groups කරයි
- **Batch upload** - Groups විදියට target channel එකට upload කරයි
- **Progress tracking** - Download, batching, upload phases
- **Smart cleanup** - Upload කරපු පසු auto delete

#### Batch Downloader භාවිතය:

1. **Base Link:** Channel URL එක message ID නැතිව
   - Private: `https://t.me/c/3916408757/`
   - Public: `https://t.me/channelname/`

2. **Message Range:**
   - Start ID: `1` (පළමු message)
   - End ID: `50` (අවසාන message)

3. **Target Channel:** Upload කරන channel එකේ ID හෝ username
   - `-1004460843642` හෝ `@targetchannel`

4. **Max Batch Size:** Batch එකක max size (default: 6GB)

5. **Delete After:** Upload කරපු පසු files delete කරන්නද? (recommended ✅)

6. **Start Process** ක්ලික් කරන්න!

#### මෙහෙම වෙනවා:

```
Phase 1: 📥 DOWNLOADING
├─ Message 1 → video1.mp4 (234 MB) ✅
├─ Message 2 → video2.mp4 (456 MB) ✅
├─ Message 3 → video3.mp4 (189 MB) ✅
└─ ... (messages 4-50)

Phase 2: 📦 BATCHING
├─ Grouping files by 6GB limit
├─ Batch 1: 15 files (5.2 GB)
└─ Batch 2: 35 files (4.8 GB)

Phase 3: 📤 UPLOADING
├─ Batch 1/2 → Upload as media group ✅
├─ Wait 5 seconds...
└─ Batch 2/2 → Upload as media group ✅

Phase 4: 🗑️ CLEANUP
└─ Delete all downloaded files ✅

✅ Complete!
```

#### Benefits:

- **කාලය save කරයි:** Bulk operations
- **Organized uploads:** Groups විදියට upload
- **Space efficient:** Auto cleanup
- **Progress visibility:** Real-time tracking
- **Resumable:** Stopped නම් ආයෙ start කරන්න පුළුවන්

## 🚀 Running on VPS

VPS එකක run කරන්න **DOCKER_QUICK_START.md** හෝ **VPS_SETUP.md** බලන්න.

