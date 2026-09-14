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
