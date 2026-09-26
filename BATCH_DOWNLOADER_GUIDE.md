# 📦 Telegram Batch Downloader - භාවිත කරන හැටි

## 🎯 මේක මොකද්ද?

Private/Public Telegram channel එකක message links range එකක් දීලා:
- ඒ සියලු media download කරගන්න
- 6GB බැගින් batches හදාගන්න
- Target channel එකට upload කරන්න

## 🚀 භාවිත කරන්නෙ කොහොමද?

### 1️⃣ Message Links සොයා ගන්න

**Private Channel සඳහා:**
```
https://t.me/c/3916408757/1
https://t.me/c/3916408757/2
https://t.me/c/3916408757/3
...
https://t.me/c/3916408757/50
```

**Public Channel සඳහා:**
```
https://t.me/channelname/1
https://t.me/channelname/2
...
```

### 2️⃣ Script එක Configure කරන්න

`telegram_batch_downloader.py` file එක open කරලා `main()` function එකේ settings edit කරන්න:

```python
# Private channel example
base_link = "https://t.me/c/3916408757/"  # ඔයාගේ channel link (අන්තිමට / දාන්න)
start_id = 1        # පළමු message number
end_id = 50         # අවසාන message number

# Target channel (upload කරන තැන)
target = -1004460843642  # හෝ "@channelname"

# Download කරපු files delete කරන්නද?
delete_after = True  # True = delete, False = keep
```

### 3️⃣ Run කරන්න

```bash
python telegram_batch_downloader.py
```

## 📊 මෙහෙම වැඩ කරයි:

1. **Download Phase:**
   - Message 1 සිට 50 දක්වා එකින් එක download කරනවා
   - `telegram_downloads/` folder එකට save කරනවා
   - Progress එක display කරනවා

2. **Batch Creation:**
   - Download කරගත්ත files 6GB බැගින් groups කරනවා
   - මොනයම් file එකක් 6GB වැඩිනම් එක alone batch එකක් දානවා

3. **Upload Phase:**
   - එක batch එක media group එකක් විදියට upload කරනවා
   - Batch info caption එකේ දාලා යවනවා
   - Batches අතර 5 second delay එකක් දානවා

4. **Cleanup:**
   - `delete_after = True` නම් local files delete කරනවා

## 🎨 Output එක මෙහෙමයි:

```
📥 Starting download of 50 messages...
Range: 1 to 50
============================================================

[1/50] Processing: https://t.me/c/3916408757/1
✅ Downloaded: video1.mp4 (234.56 MB)

[2/50] Processing: https://t.me/c/3916408757/2
✅ Downloaded: video2.mp4 (456.78 MB)
...

✅ Successfully downloaded 50 files
Total size: 4.32 GB

📦 Creating batches (Max 6GB per batch)...
✅ Created 1 batch(es)
  Batch 1: 50 files, 4.32 GB

📤 Starting upload to channel -1004460843642...

📤 Uploading Batch 1/1
Files in batch: 50
Total size: 4.32 GB
============================================================
  [1/50] Adding: video1.mp4
  [2/50] Adding: video2.mp4
  ...
✅ Batch 1 uploaded successfully!

🗑️ Cleaning up downloaded files...
  Deleted: video1.mp4
  Deleted: video2.mp4
  ...

============================================================
✅ Process completed!
Downloaded: 50 files
Uploaded: 1/1 batches
============================================================
```

## ⚙️ Advanced Settings

Script එක තුළ මේවා change කරන්න පුළුවන්:

```python
# Maximum batch size (default 6GB)
MAX_BATCH_SIZE_GB = 6

# Download directory
DOWNLOAD_DIR = 'telegram_downloads'

# Delay between downloads (seconds)
await asyncio.sleep(1)  # මේක වෙනස් කරන්න පුළුවන්

# Delay between batch uploads (seconds)
await asyncio.sleep(5)  # මේකත් වෙනස් කරන්න පුළුවන්
```

## 🔍 Use Cases

### Example 1: කුඩා range එකක්
```python
base_link = "https://t.me/c/3916408757/"
start_id = 10
end_id = 20
# Messages 10-20 download කරයි (11 messages)
```

### Example 2: විශාල range එකක්
```python
base_link = "https://t.me/c/3916408757/"
start_id = 1
end_id = 500
# Messages 1-500 download කරයි, multiple batches හදයි
```

### Example 3: Public channel
```python
base_link = "https://t.me/mychannel/"
start_id = 1
end_id = 100
```

## ❗ Important Notes

1. **Private Channel Access:**
   - Private channels වලට access තියෙන්න ඕනි
   - ඔයාගේ account එක එම channel එකේ member එකක් විය යුතුයි

2. **Rate Limits:**
   - Telegram rate limits avoid කරන්න delays දාලා තියෙනවා
   - FloodWait errors ආවොත් automatic retry කරයි

3. **File Size:**
   - Telegram 2GB file limit එකක් තියෙනවා
   - 2GB වැඩි files upload වෙන්නේ නැහැ

4. **Batch Size:**
   - 6GB default limit එක ඔයා අවශ්ය විදියට වෙනස් කරන්න පුළුවන්
   - MAX_BATCH_SIZE_GB value එක change කරන්න

## 🐛 Troubleshooting

**Problem:** Invalid link format
```
✅ Fix: Link එක format එක check කරන්න
Private: https://t.me/c/CHANNEL_ID/
Public: https://t.me/channelname/
```

**Problem:** No media found
```
✅ Fix: Message එකේ media තියෙනවද check කරන්න
```

**Problem:** FloodWait errors
```
✅ Fix: Script එක automatic handle කරයි, wait වෙන්න
```

**Problem:** Permission denied
```
✅ Fix: Channel එකේ member එකක් වගේ ඉන්නවද check කරන්න
```

## 📝 Notes

- Caption එකෙත් batch info එකක් add වෙනවා: `📦 Batch 1/3 | 50 files | 4.32 GB`
- Original message captions preserve වෙනවා
- Videos වලට streaming support enable කරලා තියෙනවා
- Progress tracking හොඳින් තියෙනවා

---

**Made with ❤️ for easy Telegram media management**
