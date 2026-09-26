# 🚀 VPS එකට Deploy කරන්න - ලේසිම විදිය

## Step 1: VPS එකට Login වෙන්න

```bash
ssh root@YOUR_VPS_IP
```

උදාහරණ: `ssh root@45.77.171.72`

## Step 2: Project Download කරන්න

### Option A: Git Clone (Recommended)

```bash
cd /root
git clone YOUR_REPO_URL telegram-app
cd telegram-app
```

### Option B: Manual Upload

**WinSCP** හෝ **FileZilla** use කරලා project folder එක `/root/telegram-app` වෙත upload කරන්න.

## Step 3: Deploy කරන්න

```bash
cd /root/telegram-app
chmod +x deploy.sh
./deploy.sh
```

Script එක automatically:
- ✅ Docker install කරයි
- ✅ Container build කරයි
- ✅ Web app start කරයි

## Step 4: Access කරන්න

Browser එකෙන් යන්න:
```
http://YOUR_VPS_IP:3000
```

උදාහරණ: `http://45.77.171.72:3000`

---

## 🎯 Web Interface භාවිතය

### 1️⃣ Login කරන්න (Tab 1)
- API ID, API Hash, Phone enter කරන්න
- Code එක verify කරන්න

### 2️⃣ Channels හොයන්න (Tab 2)
- "Fetch My Channels" click කරන්න
- Channel IDs copy කරන්න

### 3️⃣ Transfer කරන්න (Tab 3)
- Source Channel ID enter කරන්න
- Target Channel ID enter කරන්න
- "Start Transfer" click කරන්න

### 4️⃣ Single Download (Tab 4)
- Message link paste කරන්න
- Download හෝ Forward option select කරන්න

### 5️⃣ Batch Download (Tab 5) 📦
**VPS Disk Safe** - Progressive processing!

#### Input කරන්න:
```
Base Link: https://t.me/c/3916408757/
Start ID:  1
End ID:    50
Target:    -1004460843642
Max Size:  6 GB (recommended)
Delete:    ✅ Check කරන්න
```

#### Start කරන්න!

මෙහෙම වෙනවා:
```
📥 Download 6GB worth of files
📤 Upload as Batch 1
🗑️ Delete files (free 6GB)
📥 Download next 6GB
📤 Upload as Batch 2
🗑️ Delete files
... repeat
```

**Result:** VPS disk එකේ maximum ~6GB විතරයි use වෙන්නේ!

---

## 🛠️ Useful Commands

### Logs බලන්න:
```bash
docker-compose logs -f
```

### Restart කරන්න:
```bash
cd /root/telegram-app
docker-compose restart
```

### Stop කරන්න:
```bash
docker-compose down
```

### Fresh Start:
```bash
cd /root/telegram-app
docker-compose down
rm -rf session_data/* telegram_downloads/*
docker-compose up -d --build
```

### Disk Space Check:
```bash
df -h
```

### Clean Downloads Folder:
```bash
cd /root/telegram-app
rm -rf telegram_downloads/*
```

---

## 💾 VPS Requirements

### Minimum (Batch Downloader සමඟ):
- **CPU:** 1 vCPU
- **RAM:** 1 GB
- **Disk:** 7-10 GB (6GB for downloads + 1-4GB for system)

### Recommended:
- **CPU:** 2 vCPU
- **RAM:** 2 GB
- **Disk:** 20 GB

---

## 🔧 Troubleshooting

### Port 3000 access නැත්නම්:
```bash
ufw allow 3000/tcp
```

### Docker errors:
```bash
systemctl restart docker
docker-compose down
docker-compose up -d --build
```

### Out of disk space:
```bash
# Check space
df -h

# Clean downloads
rm -rf /root/telegram-app/telegram_downloads/*

# Clean Docker
docker system prune -a
```

### App නැවත start කරන්න:
```bash
cd /root/telegram-app
docker-compose restart
```

---

## 🎉 Done!

ඔබේ Telegram Media Hub දැන් VPS එකේ run වෙනවා!

- 🌐 Web UI: `http://YOUR_VPS_IP:3000`
- 📦 Batch Downloader: Tab 5 (VPS disk safe!)
- 🔄 Progressive Processing: Auto cleanup
- 💾 Max Disk Usage: ~6GB

විස්තර සඳහා: **VPS_SETUP.md** බලන්න
