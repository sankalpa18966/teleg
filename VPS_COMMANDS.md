# 🎯 VPS Quick Commands Reference

## 🚀 Deploy කරන්න

### Option 1: Auto Deploy (Recommended)
```bash
cd /root/telegram-app
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Quick Deploy Menu
```bash
cd /root/telegram-app
chmod +x quick-deploy.sh
./quick-deploy.sh
```
Interactive menu එකක් එනවා - choose කරන්න:
1. Start/Deploy App
2. View Logs
3. Restart App
4. Stop App
5. Clean & Fresh Start
6. Check Disk Space

### Option 3: Manual Deploy

Docker Compose V2 (Modern):
```bash
docker compose up -d --build
```

Docker Compose V1 (Old):
```bash
docker-compose up -d --build
```

---

## 📋 Logs බලන්න

```bash
# Auto-detect version
docker compose logs -f       # V2
# හෝ
docker-compose logs -f       # V1

# Last 50 lines only
docker compose logs --tail=50 -f
```

---

## 🔄 Restart කරන්න

```bash
docker compose restart
# හෝ
docker-compose restart
```

---

## 🛑 Stop කරන්න

```bash
docker compose down
# හෝ
docker-compose down
```

---

## 🧹 Clean Everything (Fresh Start)

```bash
cd /root/telegram-app

# Stop app
docker compose down

# Clean data
rm -rf session_data/* telegram_downloads/*

# Rebuild & start
docker compose up -d --build
```

---

## 💾 Disk Space Management

### Check Disk Space:
```bash
df -h
```

### Check Specific Folders:
```bash
# Download folder size
du -sh /root/telegram-app/telegram_downloads/

# Session folder size
du -sh /root/telegram-app/session_data/
```

### Clean Download Folder:
```bash
cd /root/telegram-app
rm -rf telegram_downloads/*
echo "✅ Downloads cleaned!"
```

### Clean Docker Cache (Extreme):
```bash
# Warning: This removes unused Docker data
docker system prune -a
```

---

## 🔍 Container Status බලන්න

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Check container resource usage
docker stats
```

---

## 🌐 Access Info

### Find VPS IP:
```bash
hostname -I
```

### Web UI Access:
```
http://YOUR_VPS_IP:3000
```

### Check if Port 3000 is Open:
```bash
netstat -tuln | grep 3000
```

---

## 🔧 Troubleshooting

### Port 3000 Access නැත්නම්:
```bash
# Allow port in firewall
ufw allow 3000/tcp

# Check firewall status
ufw status
```

### Docker Errors:
```bash
# Restart Docker service
systemctl restart docker

# Check Docker status
systemctl status docker

# Rebuild everything
docker compose down
docker compose up -d --build --force-recreate
```

### Permission Errors:
```bash
cd /root/telegram-app
chmod -R 755 session_data telegram_downloads
chown -R root:root session_data telegram_downloads
```

### Out of Disk Space:
```bash
# 1. Check space
df -h

# 2. Clean downloads
rm -rf /root/telegram-app/telegram_downloads/*

# 3. Clean Docker
docker system prune -a

# 4. Clean system packages (careful!)
apt-get autoremove
apt-get clean
```

### App Not Starting:
```bash
# Check logs for errors
docker compose logs

# Try rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## 📱 VPS Management

### Update App Code (Git Pull):
```bash
cd /root/telegram-app
docker compose down
git pull origin main
docker compose up -d --build
```

### Backup Session Data:
```bash
cd /root/telegram-app
tar -czf session-backup-$(date +%Y%m%d).tar.gz session_data/
# Download this file via SCP/WinSCP
```

### Restore Session Data:
```bash
cd /root/telegram-app
docker compose down
tar -xzf session-backup-YYYYMMDD.tar.gz
docker compose up -d
```

---

## 🎯 Quick Reference Card

```bash
# Start
docker compose up -d --build

# Logs
docker compose logs -f

# Restart
docker compose restart

# Stop
docker compose down

# Disk
df -h

# Clean
rm -rf telegram_downloads/*

# Fresh Start
docker compose down && rm -rf session_data/* telegram_downloads/* && docker compose up -d --build
```

---

## 💡 Tips

1. **Use quick-deploy.sh** - Interactive menu with all commands
2. **Monitor disk space** regularly with `df -h`
3. **Batch Downloader** auto-manages disk (max ~6GB)
4. **Clean downloads folder** periodically
5. **Check logs** if something goes wrong

---

## 🆘 Need Help?

1. Check logs: `docker compose logs -f`
2. Check disk: `df -h`
3. Restart app: `docker compose restart`
4. Fresh start: Clean everything and rebuild

Most issues තීරෙනවා restart කරලා හෝ fresh start එකක් කරලා!
