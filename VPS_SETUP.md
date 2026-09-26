# 🚀 VPS Deployment Guide — Telegram Hub Web App

මෙම මාර්ගෝපදේශය මගින් ඔබේ Telegram Web Application එක VPS (Virtual Private Server) එකක පහසුවෙන්ම Setup කරගන්නා ආකාරය පියවරෙන් පියවර විස්තර කෙරේ.

---

## 📋 Prerequisites (අවශ්‍ය දෑ)

- **Ubuntu / Debian** සහිත ඕනෑම VPS එකක් (e.g. Vultr, DigitalOcean, Hetzner, AWS)
- VPS එකෙහි **IP Address** සහ **Root Password** (හෝ SSH Key)

---

## 🛠️ Step 1: VPS එකට Connect වෙන්න

ඔබගේ கணිනියේ Terminal (Command Prompt / PowerShell) එකෙන්:

```bash
ssh root@YOUR_VPS_IP
```
*(උදා: `ssh root@45.77.171.72`)*

---

## 📁 Step 2: Files Upload කරන්න

### 💡 Option A: Git ක්ලෝන් කිරීම (Recommended)
VPS එක තුළදී:
```bash
mkdir -p /root/telegram-app
cd /root/telegram-app
# git clone <YOUR_REPO_URL> .
```

### 💡 Option B: WinSCP / FileZilla භාවිතයෙන්
**WinSCP** හෝ **FileZilla** හරහා VPS එකට Connect වී `/root/telegram-app` folder එකට project හි සියලුම files upload කරන්න.

---

## 🚀 Step 3: Script එක Run කර Deploy කරන්න

VPS එකේ project folder එකට ගොස් මෙම Command එක ලබාදෙන්න:

```bash
cd /root/telegram-app
chmod +x deploy.sh
./deploy.sh
```

මෙම script එක මගින්:
1. **Docker & Docker Compose** නොමැති නම් automatically install කරයි.
2. Web app එක Docker container එකක් ලෙස background එකෙහි start කරයි.

---

## 🌐 Step 4: Web UI එකට පිවිසෙන්න

Deployment එක සාර්ථක වූ පසු ඔබේ Browser එකෙන්:

```
http://YOUR_VPS_IP:3000
```
*(උදා: `http://45.77.171.72:3000`)*

### Web UI එක හරහා:
1. **Tab 1 (Credentials & Login)** එකෙන් ඔබේ **API ID**, **API Hash**, සහ **Phone Number** ඇතුළත් කර Telegram එකට Log වන්න.
2. **Tab 2 (Find Channel IDs)** එකෙන් ඔබේ සියලුම Channels වල IDs ලබා ගන්න.
3. **Tab 3 (Media Transfer)** එකෙන් Source & Target Channel IDs දී Transfer එක ආරම්භ කරන්න.
4. **Tab 4 (Content Downloader)** එකෙන් Telegram Post Link එකක් දී Media Download හෝ Transfer කරගන්න.
5. **Tab 5 (Batch Downloader) 📦 NEW!** එකෙන් Message range එකක් දී bulk download & batch upload කරගන්න.

---

## 📦 Batch Downloader භාවිතය (Tab 5)

### VPS Disk Space Management ✨

Batch Downloader එක **VPS disk space safe** කරන්න special design කරලා තියෙනවා:

#### 💾 Progressive Processing:
```
Download 6GB → Upload Batch 1 → Delete Files → Download Next 6GB
```

මේ හින්දා:
- **Maximum disk usage:** ~6GB පමණයි
- 7GB VPS එකකට perfect
- Space pressure නැහැ

### භාවිත කරන හැටි:

1. **Base Link:** Channel URL එක message ID නැතිව
   ```
   Private: https://t.me/c/3916408757/
   Public:  https://t.me/channelname/
   ```

2. **Message Range:**
   - Start ID: `1` (පළමු message)
   - End ID: `50` (අවසාන message)

3. **Target Channel:** Upload කරන channel ID/username
   ```
   -1004460843642  හෝ  @targetchannel
   ```

4. **Max Batch Size:** Default `6 GB` (7GB VPS එකට recommended)
   - මේක VPS disk space protect කරන්න
   - 6GB වැඩි උනාම auto upload & cleanup

5. **Delete After Upload:** ✅ (recommended)
   - Upload කරපු පසු files delete කරයි
   - Disk space free කරයි

6. **Start Process** button එක click කරන්න!

### මෙහෙම වැඩ කරයි:

```
Phase 1: 📥 Progressive Download
├─ Download messages 1-5 (4.2 GB total)
├─ Monitor: 4.2 GB / 6 GB ✅ Continue...
│
├─ Download message 6 (2.1 GB)
├─ Monitor: 6.3 GB / 6 GB ⚠️ Limit reached!
│
Phase 2: 📤 Auto Upload & Cleanup
├─ Upload Batch 1 (6 files, 6.3 GB) ✅
├─ Delete all batch 1 files (freed 6.3 GB) ✅
│
Phase 3: 🔄 Continue Next Batch
├─ Download messages 7-12 (5.8 GB)
├─ Monitor: 5.8 GB / 6 GB ✅
│
└─ Repeat until all messages done...
```

### Real-time Progress Display:

```
📥 Downloading message 25... (Batch size: 4532 MB / 6144 MB)
💾 Batch 2 full (5879 MB) - uploading now...
✅ Batch 2 uploaded!
🗑️ Cleaned batch 2 files to free disk space
📥 Downloading message 26... (Batch size: 234 MB / 6144 MB)
```

---

## 💡 VPS Disk Space Tips

### Check Available Space:
```bash
df -h
```

### Clean Telegram Downloads Manually:
```bash
cd /root/telegram-app
rm -rf telegram_downloads/*
```

### Monitor Disk Usage Real-time:
```bash
watch -n 2 df -h
```

### Recommended VPS Specs:
- **Minimum:** 1 vCPU, 1GB RAM, 10GB Disk
- **Recommended:** 2 vCPU, 2GB RAM, 20GB Disk
- **With Batch Downloader:** 1GB RAM ප්‍රමාණවත්, Disk ~7-10GB

---

## 🎛️ ප්‍රයෝජනවත් Commands (Useful Commands)

### 📊 Logs පරීක්ෂා කිරීමට:
```bash
docker-compose logs -f
```

### 🔄 App එක Restart කිරීමට:
```bash
docker-compose restart
```

### 🛑 App එක නවත්වන්න:
```bash
docker-compose down
```

### 🔒 Firewall Access (Port 3000 Open කිරීමට අවශ්‍ය නම්):
VPS එකේ ufw තිබේ නම්:
```bash
ufw allow 3000/tcp
```

### 🧹 Clean Everything (Fresh Start):
```bash
docker-compose down
rm -rf session_data/* telegram_downloads/*
docker-compose up -d --build
```
