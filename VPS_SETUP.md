# 🚀 VPS Setup Guide - Docker සමඟ

VPS IP: **45.77.171.72**

## 📋 Prerequisites

VPS එකේ:
- Ubuntu/Debian Linux
- Docker සහ Docker Compose installed
- SSH access

---

## Step 1: VPS එකට Connect වෙන්න

```bash
ssh root@45.77.171.72
```

Password එක enter කරන්න.

---

## Step 2: Docker Install කරන්න (Install කරලා නැත්නම්)

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Verify installation
docker --version
docker-compose --version
```

---

## Step 3: Project Files Upload කරන්න

### Option A: SCP/SFTP Use කරන්න (Windows වලින්)

**WinSCP** හෝ **FileZilla** use කරලා files upload කරන්න:
- Host: `45.77.171.72`
- Protocol: SFTP
- Port: 22

Upload කරන්න ඕනි files:
- `telegram_media_transfer.py`
- `find_channel_id.py`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

Upload location: `/root/telegram-transfer/`

### Option B: Git Use කරන්න (Recommended)

VPS එකේ:

```bash
# Install git (නැත්නම්)
apt install git -y

# Create directory
mkdir -p /root/telegram-transfer
cd /root/telegram-transfer

# Upload files using git (if you have a repo)
# git clone YOUR_REPO_URL .

# Or create files manually and paste content
# nano telegram_media_transfer.py
# (paste content and save with Ctrl+O, Ctrl+X)
```

---

## Step 4: Configure කරන්න

VPS එකේ `docker-compose.yml` file එක edit කරන්න:

```bash
cd /root/telegram-transfer
nano docker-compose.yml
```

Edit කරන්න ඕනි values:
```yaml
environment:
  - API_ID=33864150                    # ඔබේ API ID
  - API_HASH=0938f04741c164281a160dd7099e4025  # ඔබේ API Hash
  - PHONE=+94714527083                 # ඔබේ phone number
  - SOURCE_CHANNEL=-1003916408757      # Source channel ID
  - TARGET_CHANNEL=-1004460843642      # Target channel ID
  - TRANSFER_LIMIT=                    # Empty for all, or set number
  - DELAY=3                            # Delay between uploads
  - DELETE_AFTER_UPLOAD=True           # Delete local files after upload
```

Save කරන්න: `Ctrl+O` then `Enter`, Exit: `Ctrl+X`

---

## Step 5: Docker Image Build කරන්න

```bash
cd /root/telegram-transfer
docker-compose build
```

මේක කිපයක් minutes ගතවෙයි.

---

## Step 6: පළමු වතාවට Run කරන්න (Login කරන්න)

```bash
docker-compose run --rm telegram-transfer python find_channel_id.py
```

මේක:
1. Phone verification code එකක් ඉල්ලයි - ඔබේ Telegram app එකෙන් code එක type කරන්න
2. 2FA password ඉල්ලයි (තියෙනවනම්)
3. Login වුණාම channels list කරයි
4. Verify කරන්න SOURCE_CHANNEL සහ TARGET_CHANNEL IDs හරිද කියලා

---

## Step 7: Transfer Service Run කරන්න

### Interactive Mode (Test කරන්න):

```bash
docker-compose up
```

මේක foreground එකේ run වෙයි, output එක real-time එකේ පෙන්වයි.
Stop කරන්න: `Ctrl+C`

### Background Mode (Production):

```bash
docker-compose up -d
```

මේක background එකේ run වෙයි.

---

## 🎛️ Docker Commands

### Logs බලන්න:
```bash
docker-compose logs -f
```

### Status check කරන්න:
```bash
docker-compose ps
```

### Service නවත්තන්න:
```bash
docker-compose down
```

### Service restart කරන්න:
```bash
docker-compose restart
```

### Session files clear කරන්න (re-login):
```bash
rm -rf session_data/*.session
docker-compose restart
```

### Container එකට shell access:
```bash
docker-compose exec telegram-transfer bash
```

---

## 🔄 Auto-Restart Configuration

Service එක automatically restart වෙන්න config කරලා තියෙනවා (`restart: unless-stopped`):
- Server reboot වුණාම auto-start
- Crash වුණාම auto-restart
- Manual stop කරනකන් run වෙනවා

---

## 📊 Monitoring

### Real-time logs:
```bash
docker-compose logs -f telegram-transfer
```

### Last 100 lines:
```bash
docker-compose logs --tail=100 telegram-transfer
```

### Resource usage:
```bash
docker stats telegram_media_transfer
```

---

## 🛠️ Troubleshooting

### Container restart වෙනවා නම්:
```bash
docker-compose logs telegram-transfer
```

### Session expired නම්:
```bash
docker-compose down
rm -rf session_data/*.session
docker-compose up
# Enter verification code again
```

### Permission errors:
```bash
chmod -R 777 session_data/
chmod -R 777 telegram_downloads/
```

### Disk space full:
```bash
# Check disk usage
df -h

# Clear downloaded files
rm -rf telegram_downloads/*

# Enable DELETE_AFTER_UPLOAD in docker-compose.yml
```

---

## 🔐 Security Notes

1. **Firewall:** Ports 80, 443, 2005 use කරන්නේ නැහැ, ඒ නිසා firewall rules අවශ්‍ය නැහැ
2. **Session files:** `session_data/` folder එක secure කරන්න - මේකේ login details තියෙනවා
3. **Credentials:** `docker-compose.yml` එකේ credentials secure කරන්න
4. **Backups:** `session_data/` folder එක backup කරන්න re-login වෙන්න වෙන්නේ නැහැ වගේ

---

## 📁 File Structure (VPS එකේ)

```
/root/telegram-transfer/
├── telegram_media_transfer.py
├── find_channel_id.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── session_data/              # Auto-created (session files)
│   └── session.session
└── telegram_downloads/        # Auto-created (temp downloads)
    └── (media files)
```

---

## ✅ Quick Start Summary

```bash
# 1. Connect to VPS
ssh root@45.77.171.72

# 2. Go to project directory
cd /root/telegram-transfer

# 3. Build
docker-compose build

# 4. First run (login)
docker-compose run --rm telegram-transfer python find_channel_id.py

# 5. Start service
docker-compose up -d

# 6. Check logs
docker-compose logs -f
```

---

## 🎉 Done!

Service එක දැන් VPS එකේ background එකේ run වෙනවා!

- Auto-restart enabled
- Session files persisted
- Logs viewable anytime
- No ports exposed (secure)
