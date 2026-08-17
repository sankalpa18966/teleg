# 🐳 Docker Quick Start - සිංහලෙන්

VPS එකේ (`45.77.171.72`) Telegram media transfer service එක run කරන්න.

## 🎯 මොනවද හදලා තියෙන්නේ?

✅ **Dockerfile** - Python app එක containerize කරන්න
✅ **docker-compose.yml** - Service configuration
✅ **VPS_SETUP.md** - සම්පූර්ණ setup guide
✅ **deploy.sh** - Automated deployment script

## ⚡ Quick Deploy (3 Steps)

### 1️⃣ Files Upload කරන්න VPS එකට

**Option A: WinSCP/FileZilla Use කරන්න**
- Connect to: `45.77.171.72`
- Upload මේ files:
  - `telegram_media_transfer.py`
  - `find_channel_id.py`
  - `requirements.txt`
  - `Dockerfile`
  - `docker-compose.yml`
  - `.dockerignore`
  - `deploy.sh`
- Location: `/root/telegram-transfer/`

**Option B: Manual Copy-Paste (SSH එකෙන්)**
```bash
ssh root@45.77.171.72
mkdir -p /root/telegram-transfer
cd /root/telegram-transfer
nano telegram_media_transfer.py  # Paste content, Ctrl+O, Ctrl+X
nano docker-compose.yml          # Paste content, Ctrl+O, Ctrl+X
# ... repeat for other files
```

### 2️⃣ VPS එකේ Setup කරන්න

SSH එකෙන්:
```bash
ssh root@45.77.171.72

cd /root/telegram-transfer

# Install Docker (නැත්නම්)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install docker-compose -y

# Edit credentials
nano docker-compose.yml
# Change: API_ID, API_HASH, PHONE, SOURCE_CHANNEL, TARGET_CHANNEL
# Save: Ctrl+O, Enter, Ctrl+X

# Build
docker-compose build
```

### 3️⃣ Run කරන්න

```bash
# First time - Login
docker-compose run --rm telegram-transfer python find_channel_id.py
# Enter verification code from Telegram

# Start service
docker-compose up -d

# View logs
docker-compose logs -f
```

## 🎛️ Common Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# Logs
docker-compose logs -f

# Status
docker-compose ps

# Resource usage
docker stats telegram_media_transfer
```

## 📊 What Happens?

1. **Container run වෙයි** background එකේ
2. **Auto-restart** enabled (crash/reboot වුණාම)
3. **Session persistent** - login once, works forever
4. **No ports exposed** - secure
5. **Logs available** anytime

## 🔥 Production Ready Features

✅ Auto-restart on crash/reboot
✅ Session persistence (no re-login needed)
✅ FloodWait auto-handling
✅ Resource limits (1GB RAM, 1 CPU)
✅ Volume mounts for data persistence
✅ Proper error handling

## 📝 Important Notes

### Ports:
- මේ service එකට ports 80, 443, 2005 අවශ්‍ය **නැහැ**
- මේක background task එකක්, web service එකක් නෙමෙයි
- Firewall rules අවශ්‍ය නැහැ

### Security:
- Session files `/root/telegram-transfer/session_data/` එකේ save වෙනවා
- මේ folder එක **secure** කරන්න - login details තියෙනවා
- `docker-compose.yml` එකේ credentials **private** කරන්න

### Continuous Operation:
- Service එක **24/7** run වෙනවා
- Media transfer complete වුණාම automatically stop වෙයි
- Restart කරනවනම් ආයෙත් run වෙයි

## 🐛 Troubleshooting

### Container නැවතුනොත්:
```bash
docker-compose logs telegram-transfer
```

### Re-login කරන්න:
```bash
docker-compose down
rm -rf session_data/*.session
docker-compose run --rm telegram-transfer python find_channel_id.py
docker-compose up -d
```

### Disk full:
```bash
rm -rf telegram_downloads/*
# හෝ docker-compose.yml එකේ DELETE_AFTER_UPLOAD=True set කරන්න
```

## 📚 More Info

සම්පූර්ණ guide: **VPS_SETUP.md** බලන්න

---

## ✅ Checklist

- [ ] VPS එකට SSH access තියෙනවා
- [ ] Docker installed
- [ ] Files uploaded to `/root/telegram-transfer/`
- [ ] `docker-compose.yml` edited with credentials
- [ ] `docker-compose build` run කරලා
- [ ] First time login completed
- [ ] Service started with `docker-compose up -d`
- [ ] Logs check කරලා everything working

🎉 All done? Service එක දැන් VPS එකේ run වෙනවා!
