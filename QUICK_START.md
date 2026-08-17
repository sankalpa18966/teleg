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
