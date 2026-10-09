"""
Telegram Media Transfer - Web UI
Flask web application with real-time progress tracking
Supports: Login via web, Find Channel IDs, Media Transfer, Content Download
"""

from flask import Flask, render_template, request, jsonify, send_file, session
from flask_socketio import SocketIO, emit
from telethon import TelegramClient, utils
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, Channel, Chat, InputMediaUploadedDocument, InputMediaUploadedPhoto, DocumentAttributeVideo, DocumentAttributeFilename, InputSingleMedia
from telethon.tl.functions.messages import SendMultiMediaRequest
import asyncio
import os
import random
import json
import re
import io
import mimetypes
from datetime import datetime
import threading
import subprocess
import shutil

app = Flask(__name__)
app.config['SECRET_KEY'] = 'telegram-transfer-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ── Directories ────────────────────────────────────────────────────────────────
SESSION_DIR = 'session_data'
os.makedirs(SESSION_DIR, exist_ok=True)
SESSION_PATH = os.path.join(SESSION_DIR, 'session')
TRANSFERRED_DB = os.path.join(SESSION_DIR, 'transferred_messages.json')
CONFIG_FILE = os.path.join(SESSION_DIR, 'config.json')
LOGIN_LOG = os.path.join(SESSION_DIR, 'login_log.json')
DOWNLOAD_DIR = os.path.abspath('telegram_downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ── Auto-cleaner for temporary downloads ───────────────────────────────────────
import time

# Active PC batch download synchronization
active_pc_events = {}          # filename -> threading.Event()
active_pc_skip_delay = threading.Event()

def start_auto_cleaner():
    """Background thread that automatically purges orphaned temp files in telegram_downloads older than 30 minutes."""
    def _cleaner_loop():
        while True:
            try:
                time.sleep(60)
                if os.path.exists(DOWNLOAD_DIR):
                    now = time.time()
                    for f in os.listdir(DOWNLOAD_DIR):
                        fp = os.path.join(DOWNLOAD_DIR, f)
                        if os.path.isfile(fp):
                            # Never clean files currently waiting or streaming to user's PC
                            if f in active_pc_events:
                                continue
                            if now - os.path.getmtime(fp) > 1800:
                                try:
                                    os.remove(fp)
                                    print(f"🧹 Auto-cleaned orphaned temp file from VPS: {f}")
                                except Exception:
                                    pass
            except Exception:
                pass

    threading.Thread(target=_cleaner_loop, daemon=True).start()

start_auto_cleaner()

# ── Global state ───────────────────────────────────────────────────────────────
transfer_status = {
    'is_running': False,
    'current': 0,
    'total': 0,
    'success': 0,
    'failed': 0,
    'skipped': 0,
    'message': 'Ready',
    'logged_in': False
}

client = None
client_loop = None
# Runtime credentials (populated from config or web form)
_api_id = None
_api_hash = None
_phone = None


# ══════════════════════════════════════════════════════════════════════════════
#  Config / Log helpers
# ══════════════════════════════════════════════════════════════════════════════

def load_config():
    """Load saved API credentials from disk."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(api_id, api_hash, phone):
    """Persist API credentials to disk."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'api_id': api_id, 'api_hash': api_hash, 'phone': phone}, f, indent=2)


def load_login_log():
    """Return list of login log entries."""
    if os.path.exists(LOGIN_LOG):
        try:
            with open(LOGIN_LOG, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def append_login_log(phone, status, note=''):
    """Append a login event to the log file."""
    entries = load_login_log()
    entries.append({
        'timestamp': datetime.now().isoformat(),
        'phone': phone,
        'status': status,
        'note': note
    })
    with open(LOGIN_LOG, 'w') as f:
        json.dump(entries, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
#  Transfer DB helpers
# ══════════════════════════════════════════════════════════════════════════════

def load_transferred_db():
    if os.path.exists(TRANSFERRED_DB):
        try:
            with open(TRANSFERRED_DB, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_transferred_db(db):
    with open(TRANSFERRED_DB, 'w') as f:
        json.dump(db, f, indent=2)


def is_already_transferred(db, source_channel, message_id):
    return f"{source_channel}_{message_id}" in db


def mark_as_transferred(db, source_channel, message_id):
    db[f"{source_channel}_{message_id}"] = {
        'transferred_at': datetime.now().isoformat(),
        'message_id': message_id
    }
    save_transferred_db(db)


# ══════════════════════════════════════════════════════════════════════════════
#  Async / client helpers
# ══════════════════════════════════════════════════════════════════════════════

def run_async(coro):
    """Run an async coroutine from a sync context on the shared event loop."""
    global client_loop
    if client_loop is None:
        client_loop = asyncio.new_event_loop()
        threading.Thread(target=client_loop.run_forever, daemon=True).start()
    return asyncio.run_coroutine_threadsafe(coro, client_loop).result()


def ensure_client():
    """Instantiate and connect TelegramClient using current credentials."""
    global client, _api_id, _api_hash
    if client is None:
        if not _api_id or not _api_hash:
            raise RuntimeError("API credentials not configured")
        client = TelegramClient(SESSION_PATH, int(_api_id), _api_hash)
        run_async(client.connect())
    return client


def reset_client():
    """Disconnect and clear the global client (used when credentials change)."""
    global client
    if client is not None:
        try:
            run_async(client.disconnect())
        except Exception:
            pass
        client = None


def check_login_status():
    global transfer_status, _api_id, _api_hash, _phone
    # Load credentials from config if not in memory
    if not _api_id:
        cfg = load_config()
        _api_id = cfg.get('api_id')
        _api_hash = cfg.get('api_hash')
        _phone = cfg.get('phone')

    if not transfer_status['logged_in'] and os.path.exists(SESSION_PATH + '.session') and _api_id:
        try:
            ensure_client()
            if run_async(client.is_user_authorized()):
                transfer_status['logged_in'] = True
        except Exception:
            pass


def emit_status(message, current=None, total=None):
    global transfer_status
    transfer_status['message'] = message
    if current is not None:
        transfer_status['current'] = current
    if total is not None:
        transfer_status['total'] = total
    socketio.emit('status_update', transfer_status)


# ══════════════════════════════════════════════════════════════════════════════
#  Thumbnail Extraction & Generation Helper
# ══════════════════════════════════════════════════════════════════════════════

async def get_or_generate_thumbnail(client, message, file_path, output_dir):
    """
    1. Download highest-quality original thumbnail from Telegram message if available.
    2. Fallback: For video files, use ffmpeg to capture a crisp frame at 1s (avoids black screen).
    Returns absolute path to the thumbnail JPG file or None.
    """
    thumb_path = None
    try:
        if message:
            has_thumb = False
            if hasattr(message, 'document') and message.document and hasattr(message.document, 'thumbs') and message.document.thumbs:
                has_thumb = True
            elif hasattr(message, 'video') and message.video and hasattr(message.video, 'thumbs') and message.video.thumbs:
                has_thumb = True

            if has_thumb:
                rnd_id = random.randint(1000, 9999)
                target_thumb = os.path.join(output_dir, f'thumb_{message.id}_{rnd_id}.jpg')
                downloaded = await client.download_media(message, file=target_thumb, thumb=-1)
                if downloaded and os.path.exists(downloaded) and os.path.getsize(downloaded) > 100:
                    thumb_path = os.path.abspath(downloaded)
    except Exception as e:
        print(f"Original thumbnail download note: {e}")

    # Fallback to ffmpeg for videos if no thumbnail was retrieved
    if (not thumb_path or not os.path.exists(thumb_path) or os.path.getsize(thumb_path) < 100) and file_path:
        is_video = file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
        if is_video and shutil.which('ffmpeg'):
            rnd_id = random.randint(10000, 99999)
            target_thumb = os.path.join(output_dir, f'ffmpeg_thumb_{rnd_id}.jpg')
            try:
                # Seek 1s to capture a non-black frame
                cmd = [
                    'ffmpeg', '-y', '-ss', '00:00:01', '-i', file_path,
                    '-vframes', '1', '-vf', 'scale=320:-1', target_thumb
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                if not os.path.exists(target_thumb) or os.path.getsize(target_thumb) < 100:
                    # If 1s failed, try 0s
                    cmd[2] = '00:00:00'
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)

                if os.path.exists(target_thumb) and os.path.getsize(target_thumb) > 100:
                    thumb_path = os.path.abspath(target_thumb)
            except Exception as fe:
                print(f"FFmpeg thumbnail extraction note: {fe}")

    return thumb_path


# ══════════════════════════════════════════════════════════════════════════════
#  Transfer async core
# ══════════════════════════════════════════════════════════════════════════════

async def transfer_media_async(source_channel, target_channel):
    global client, transfer_status
    try:
        # Resolve channel identifiers (int IDs or strings)
        def _resolve(ch):
            if isinstance(ch, str) and ch.lstrip('-').isdigit():
                return int(ch)
            return ch

        src = _resolve(source_channel)
        tgt = _resolve(target_channel)

        emit_status('📥 Fetching messages from channel...')
        messages = []
        async for message in client.iter_messages(src, limit=None):
            if message.media:
                messages.append(message)

        # Reverse so messages are processed chronologically (oldest to newest)
        messages.reverse()

        total = len(messages)
        transfer_status['total'] = total
        transfer_status['current'] = 0
        transfer_status['success'] = 0
        transfer_status['skipped'] = 0
        transfer_status['failed'] = 0
        emit_status(f'📊 Found {total} media messages', 0, total)

        db = load_transferred_db()

        # Group consecutive messages sharing the same grouped_id into collections/albums (max 10 items)
        grouped_items = []
        current_album = []
        current_gid = None

        for msg in messages:
            gid = msg.grouped_id
            if gid:
                if current_gid == gid and len(current_album) < 10:
                    current_album.append(msg)
                else:
                    if current_album:
                        grouped_items.append(current_album)
                    current_album = [msg]
                    current_gid = gid
            else:
                if current_album:
                    grouped_items.append(current_album)
                    current_album = []
                    current_gid = None
                grouped_items.append([msg])

        if current_album:
            grouped_items.append(current_album)

        success = failed = skipped = 0
        processed = 0

        for group in grouped_items:
            if not transfer_status['is_running']:
                emit_status('⏸️ Transfer stopped by user')
                break

            # Check if all messages in this group are already transferred
            untransferred = [m for m in group if not is_already_transferred(db, src, m.id)]
            if not untransferred:
                skipped += len(group)
                processed += len(group)
                transfer_status['skipped'] = skipped
                transfer_status['current'] = processed
                emit_status(f'⏭️ Skipping already transferred (#{group[0].id}..)', processed, total)
                continue

            msgs_to_process = untransferred
            is_album = len(msgs_to_process) > 1

            if is_album:
                emit_status(f'📥 Downloading Collection ({len(msgs_to_process)} files: #{msgs_to_process[0].id}..#{msgs_to_process[-1].id})...', processed, total)
                downloaded_group = []
                for m in msgs_to_process:
                    try:
                        f_path = await client.download_media(m, DOWNLOAD_DIR)
                        if f_path and os.path.exists(f_path):
                            abs_p = os.path.abspath(f_path)
                            thumb_p = await get_or_generate_thumbnail(client, m, abs_p, DOWNLOAD_DIR)
                            downloaded_group.append({
                                'path': abs_p,
                                'thumb': thumb_p,
                                'caption': m.message if m.message else None,
                                'msg_id': m.id
                            })
                    except Exception as de:
                        print(f"Download item error: {de}")

                if downloaded_group:
                    emit_status(f'⬆️ Uploading Collection ({len(downloaded_group)} files together as album)...', processed, total)
                    paths = [item['path'] for item in downloaded_group]
                    captions = [item['caption'] or '' for item in downloaded_group]
                    
                    sent = False
                    retries = 0
                    while not sent and retries < 3 and transfer_status['is_running']:
                        try:
                            if any(captions):
                                try:
                                    await client.send_file(tgt, paths, caption=captions, supports_streaming=True)
                                except Exception:
                                    await client.send_file(tgt, paths, supports_streaming=True)
                            else:
                                await client.send_file(tgt, paths, supports_streaming=True)

                            for item in downloaded_group:
                                mark_as_transferred(db, src, item['msg_id'])

                            success += len(downloaded_group)
                            processed += len(group)
                            transfer_status['success'] = success
                            transfer_status['current'] = processed
                            emit_status(f'✅ Done Collection ({len(downloaded_group)} files)', processed, total)
                            sent = True
                            await asyncio.sleep(2)
                        except FloodWaitError as e:
                            emit_status(f'⚠️ FloodWait {e.seconds}s...', processed, total)
                            await asyncio.sleep(e.seconds + 1)
                            retries += 1
                        except Exception as e:
                            emit_status(f'❌ Error uploading album: {e}', processed, total)
                            failed += len(downloaded_group)
                            processed += len(group)
                            transfer_status['failed'] = failed
                            transfer_status['current'] = processed
                            sent = True

                    # Cleanup files and thumbs
                    for item in downloaded_group:
                        if os.path.exists(item['path']):
                            try:
                                os.remove(item['path'])
                            except Exception:
                                pass
                        if item.get('thumb') and os.path.exists(item['thumb']):
                            try:
                                os.remove(item['thumb'])
                            except Exception:
                                pass
                else:
                    failed += len(group)
                    processed += len(group)
                    transfer_status['failed'] = failed
                    transfer_status['current'] = processed

            else:
                # Single message
                msg = msgs_to_process[0]
                emit_status(f'📥 Downloading #{msg.id}...', processed, total)
                try:
                    file_path = await client.download_media(msg, DOWNLOAD_DIR)
                    if file_path and os.path.exists(file_path):
                        abs_p = os.path.abspath(file_path)
                        emit_status(f'⬆️ Uploading {os.path.basename(abs_p)}...', processed, total)
                        caption = msg.message if msg.message else None
                        is_video = abs_p.lower().endswith(
                            ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
                        thumb_path = await get_or_generate_thumbnail(client, msg, abs_p, DOWNLOAD_DIR)
                        valid_thumb = thumb_path if (thumb_path and os.path.exists(thumb_path)) else None

                        sent = False
                        retries = 0
                        while not sent and retries < 3 and transfer_status['is_running']:
                            try:
                                await client.send_file(
                                    tgt, abs_p,
                                    caption=caption,
                                    thumb=valid_thumb,
                                    supports_streaming=is_video,
                                    force_document=False
                                )
                                mark_as_transferred(db, src, msg.id)
                                success += 1
                                processed += 1
                                transfer_status['success'] = success
                                transfer_status['current'] = processed
                                emit_status(f'✅ Done #{msg.id}', processed, total)
                                sent = True
                                await asyncio.sleep(2)
                            except FloodWaitError as e:
                                emit_status(f'⚠️ FloodWait {e.seconds}s...', processed, total)
                                await asyncio.sleep(e.seconds + 1)
                                retries += 1
                            except Exception as e:
                                emit_status(f'❌ Error: {e}', processed, total)
                                failed += 1
                                processed += 1
                                transfer_status['failed'] = failed
                                transfer_status['current'] = processed
                                sent = True

                        if os.path.exists(abs_p):
                            try:
                                os.remove(abs_p)
                            except Exception:
                                pass
                        if thumb_path and os.path.exists(thumb_path):
                            try:
                                os.remove(thumb_path)
                            except Exception:
                                pass
                    else:
                        failed += 1
                        processed += 1
                        transfer_status['failed'] = failed
                        transfer_status['current'] = processed
                except Exception as e:
                    emit_status(f'❌ Error downloading #{msg.id}: {e}', processed, total)
                    failed += 1
                    processed += 1
                    transfer_status['failed'] = failed
                    transfer_status['current'] = processed

        transfer_status['is_running'] = False
        emit_status(
            f'✅ Done! Success:{success} Failed:{failed} Skipped:{skipped}',
            total, total
        )
    except Exception as e:
        transfer_status['is_running'] = False
        emit_status(f'❌ Error: {e}')


def run_transfer(source_channel, target_channel):
    try:
        ensure_client()
        run_async(transfer_media_async(source_channel, target_channel))
    except Exception as e:
        transfer_status['is_running'] = False
        emit_status(f'❌ Error: {e}')


# ══════════════════════════════════════════════════════════════════════════════
#  Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    check_login_status()
    cfg = load_config()
    return render_template('index.html',
                           logged_in=transfer_status['logged_in'],
                           saved_phone=cfg.get('phone', ''),
                           saved_api_id=cfg.get('api_id', ''))


@app.route('/api/status')
def get_status():
    check_login_status()
    return jsonify(transfer_status)


# ── Login ──────────────────────────────────────────────────────────────────────

@app.route('/api/login', methods=['POST'])
def login():
    global client, _api_id, _api_hash, _phone, transfer_status
    data = request.get_json() or {}

    api_id = data.get('api_id', '').strip()
    api_hash = data.get('api_hash', '').strip()
    phone = data.get('phone', '').strip()

    if not api_id or not api_hash or not phone:
        return jsonify({'status': 'error', 'message': 'API ID, API Hash and Phone are required'}), 400

    try:
        # Reset client if credentials changed
        if _api_id != api_id or _api_hash != api_hash:
            reset_client()

        _api_id = api_id
        _api_hash = api_hash
        _phone = phone

        save_config(api_id, api_hash, phone)

        ensure_client()
        is_authorized = run_async(client.is_user_authorized())

        if is_authorized:
            transfer_status['logged_in'] = True
            append_login_log(phone, 'already_authorized')
            return jsonify({'status': 'logged_in', 'message': 'Already logged in!'})
        else:
            run_async(client.send_code_request(phone))
            append_login_log(phone, 'code_sent')
            return jsonify({'status': 'code_sent', 'message': 'Verification code sent to Telegram'})

    except Exception as e:
        append_login_log(phone, 'error', str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/verify', methods=['POST'])
def verify_code():
    global client, _phone, transfer_status
    data = request.get_json() or {}
    code = data.get('code', '')
    password = data.get('password', '')

    if not code:
        return jsonify({'status': 'error', 'message': 'Code is required'}), 400

    try:
        ensure_client()

        try:
            run_async(client.sign_in(_phone, code))
            transfer_status['logged_in'] = True
            append_login_log(_phone, 'login_success')
            return jsonify({'status': 'success', 'message': 'Login successful!'})
        except SessionPasswordNeededError:
            if password:
                run_async(client.sign_in(password=password))
                transfer_status['logged_in'] = True
                append_login_log(_phone, 'login_success_2fa')
                return jsonify({'status': 'success', 'message': 'Login successful (2FA)!'})
            else:
                return jsonify({'status': 'password_required', 'message': '2FA password required'})
        except PhoneCodeInvalidError:
            append_login_log(_phone, 'invalid_code')
            return jsonify({'status': 'error', 'message': 'Invalid verification code'}), 400

    except Exception as e:
        append_login_log(_phone or '', 'error', str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/logout', methods=['POST'])
def logout():
    global transfer_status, client
    try:
        if client:
            run_async(client.log_out())
        reset_client()
        transfer_status['logged_in'] = False
        append_login_log(_phone or '', 'logout')
        return jsonify({'status': 'success', 'message': 'Logged out'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


# ── Login Log ──────────────────────────────────────────────────────────────────

@app.route('/api/login_log')
def get_login_log():
    return jsonify(load_login_log())


# ── Find Channel IDs ───────────────────────────────────────────────────────────

@app.route('/api/get_channels', methods=['POST'])
def get_channels():
    if not transfer_status['logged_in']:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 400
    try:
        ensure_client()

        async def _fetch():
            results = []
            async for dialog in client.iter_dialogs():
                entity = dialog.entity
                entity_type = type(entity).__name__
                username = getattr(entity, 'username', None)
                is_channel = entity_type == 'Channel'
                is_broadcast = getattr(entity, 'broadcast', False)

                kind = 'chat'
                if is_channel and is_broadcast:
                    kind = 'channel'
                elif is_channel:
                    kind = 'group'

                results.append({
                    'name': dialog.name,
                    'id': dialog.id,
                    'type': kind,
                    'username': f'@{username}' if username else None
                })
            return results

        channels = run_async(_fetch())
        return jsonify({'status': 'success', 'channels': channels})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


# ── Media Transfer ─────────────────────────────────────────────────────────────

@app.route('/api/start', methods=['POST'])
def start_transfer():
    global transfer_status
    if not transfer_status['logged_in']:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 400
    if transfer_status['is_running']:
        return jsonify({'status': 'error', 'message': 'Transfer already running'}), 400

    data = request.get_json() or {}
    source_channel = data.get('source_channel', '').strip()
    target_channel = data.get('target_channel', '').strip()

    if not source_channel or not target_channel:
        return jsonify({'status': 'error', 'message': 'Source and Target channel IDs are required'}), 400

    transfer_status.update({
        'is_running': True, 'current': 0, 'total': 0,
        'success': 0, 'failed': 0, 'skipped': 0
    })

    t = threading.Thread(target=run_transfer, args=(source_channel, target_channel), daemon=True)
    t.start()
    return jsonify({'status': 'success', 'message': 'Transfer started'})


@app.route('/api/stop', methods=['POST'])
def stop_transfer():
    global transfer_status
    transfer_status['is_running'] = False
    return jsonify({'status': 'success', 'message': 'Transfer stopping...'})


# ── Content Download & Forward ──────────────────────────────────────────────────

def parse_telegram_url(url):
    """
    Parses Telegram message URL formats:
    1. Private channel: https://t.me/c/4458181295/198
    2. Public channel: https://t.me/channelname/198
    3. Invite link: https://t.me/+hash/198
    """
    url = url.strip().rstrip('/')
    
    # 1. Private channel format: t.me/c/123456789/198
    m_private = re.match(r'https?://t\.me/c/(?P<chan_id>\d+)/(?P<msg_id>\d+)', url)
    if m_private:
        chan_id_str = m_private.group('chan_id')
        msg_id = int(m_private.group('msg_id'))
        if chan_id_str.startswith('100'):
            peer = int(f"-{chan_id_str}")
        else:
            peer = int(f"-100{chan_id_str}")
        return {'peer': peer, 'msg_id': msg_id, 'type': 'private'}

    # 2. Invite/Join link format: t.me/+hash/198
    m_hash = re.match(r'https?://t\.me/\+(?P<hash>[^/]+)/(?P<msg_id>\d+)', url)
    if m_hash:
        return {'peer': m_hash.group('hash'), 'msg_id': int(m_hash.group('msg_id')), 'type': 'hash'}

    # 3. Public username format: t.me/username/198
    m_public = re.match(r'https?://t\.me/(?P<username>[^/]+)/(?P<msg_id>\d+)', url)
    if m_public:
        username = m_public.group('username')
        msg_id = int(m_public.group('msg_id'))
        if username == 'c':
            raise ValueError("Invalid private channel URL format. Expected: https://t.me/c/CHANNEL_ID/MSG_ID")
        return {'peer': username, 'msg_id': msg_id, 'type': 'public'}

    raise ValueError("Invalid Telegram URL. Supported formats:\n• https://t.me/c/4458181295/198 (Private)\n• https://t.me/channelname/198 (Public)\n• https://t.me/+invite_hash/198 (Invite)")


def parse_telegram_base_link(link):
    """Parse base link and extract channel info for batch operations"""
    link = link.strip().rstrip('/')
    
    # Private channel: https://t.me/c/1234567890
    m_private = re.match(r'https?://t\.me/c/(?P<chan_id>\d+)$', link)
    if m_private:
        chan_id_str = m_private.group('chan_id')
        if chan_id_str.startswith('100'):
            peer = int(f"-{chan_id_str}")
        else:
            peer = int(f"-100{chan_id_str}")
        return peer
    
    # Public channel: https://t.me/channelname
    m_public = re.match(r'https?://t\.me/(?P<username>[^/]+)$', link)
    if m_public:
        return m_public.group('username')
    
    raise ValueError("Invalid base link format. Expected: https://t.me/c/CHANNEL_ID or https://t.me/channelname")


async def fetch_message_by_url(client, parsed):
    peer = parsed['peer']
    msg_id = parsed['msg_id']
    entity = None

    try:
        entity = await client.get_entity(peer)
    except Exception:
        if isinstance(peer, int):
            async for dialog in client.iter_dialogs():
                if dialog.id == peer or dialog.entity.id == abs(peer):
                    entity = dialog.entity
                    break
        if not entity:
            raise ValueError(f"Cannot find channel corresponding to ID {peer}. Ensure you are a member of this channel.")

    message = await client.get_messages(entity, ids=msg_id)
    if not message:
        raise ValueError(f"Message #{msg_id} not found in that channel.")
    return message


def emit_link_progress(action_name, current, total):
    pct = (current / total) * 100 if total > 0 else 0
    mb_curr = round(current / (1024 * 1024), 2)
    mb_tot = round(total / (1024 * 1024), 2)
    socketio.emit('link_download_progress', {
        'action': action_name,
        'current': current,
        'total': total,
        'percent': round(pct, 1),
        'mb_current': mb_curr,
        'mb_total': mb_tot,
        'message': f"{action_name}: {mb_curr} MB / {mb_tot} MB ({round(pct, 1)}%)"
    })


@app.route('/api/download_link', methods=['POST'])
def download_link():
    """Download media from a Telegram message URL to device OR send to target channel."""
    if not transfer_status['logged_in']:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 400

    data = request.get_json() or {}
    url = data.get('url', '').strip()
    action = data.get('action', 'download')  # 'download' or 'send_channel'
    target_channel = data.get('target_channel', '').strip()
    send_mode = data.get('send_mode', 'clean')  # 'clean' or 'forward'

    if not url:
        return jsonify({'status': 'error', 'message': 'URL is required'}), 400

    if action == 'send_channel' and not target_channel:
        return jsonify({'status': 'error', 'message': 'Target Channel ID / Username is required'}), 400

    try:
        parsed = parse_telegram_url(url)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

    def _resolve(ch):
        if isinstance(ch, str) and ch.lstrip('-').isdigit():
            return int(ch)
        return ch

    try:
        ensure_client()

        if action == 'send_channel':
            tgt = _resolve(target_channel)

            async def _send_to_channel():
                message = await fetch_message_by_url(client, parsed)

                if send_mode == 'forward':
                    # Check if message is part of an album/collection
                    if message.grouped_id:
                        try:
                            min_id = max(1, message.id - 10)
                            max_id = message.id + 10
                            nearby = await client.get_messages(parsed['peer'], min_id=min_id, max_id=max_id)
                            album_msgs = [m for m in nearby if m and m.grouped_id == message.grouped_id]
                            album_msgs.sort(key=lambda m: m.id)
                            if len(album_msgs) > 1:
                                emit_link_progress('Forwarding Album', 1, 1)
                                await client.forward_messages(tgt, album_msgs)
                                return f'Collection / Album ({len(album_msgs)} items) forwarded successfully!'
                        except Exception as e:
                            print(f"Could not forward as album: {e}")

                    emit_link_progress('Forwarding', 1, 1)
                    await client.forward_messages(tgt, message)
                    return 'Message forwarded successfully!'
                else:
                    if not message.media:
                        raise ValueError('No media found in that message')
                    
                    def download_progress(c, t):
                        emit_link_progress('Downloading', c, t)

                    file_path = await client.download_media(message, DOWNLOAD_DIR, progress_callback=download_progress)
                    if not file_path:
                        raise ValueError('Failed to download media')

                    thumb_path = await get_or_generate_thumbnail(client, message, file_path, DOWNLOAD_DIR)

                    try:
                        caption = message.message if message.message else None
                        is_video = file_path.lower().endswith(
                            ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v')
                        )
                        def upload_progress(c, t):
                            emit_link_progress('Uploading', c, t)

                        valid_thumb = thumb_path if (thumb_path and os.path.exists(thumb_path)) else None
                        await client.send_file(
                            tgt, file_path,
                            caption=caption,
                            thumb=valid_thumb,
                            supports_streaming=is_video,
                            force_document=False,
                            progress_callback=upload_progress
                        )
                    finally:
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
                        if thumb_path and os.path.exists(thumb_path):
                            try:
                                os.remove(thumb_path)
                            except Exception:
                                pass
                    return 'Media uploaded to target channel successfully!'

            res_msg = run_async(_send_to_channel())
            return jsonify({'status': 'success', 'message': res_msg})

        else:
            # Action: download to device
            async def _download():
                message = await fetch_message_by_url(client, parsed)
                if not message.media:
                    raise ValueError('No media found in that message')

                def download_progress(c, t):
                    emit_link_progress('Downloading from Telegram', c, t)

                file_path = await client.download_media(message, DOWNLOAD_DIR, progress_callback=download_progress)
                return file_path

            file_path = run_async(_download())

            if not file_path or not os.path.exists(file_path):
                return jsonify({'status': 'error', 'message': 'Could not download media from Telegram'}), 400

            filename = os.path.basename(file_path)
            emit_link_progress('Ready! Transferring to PC', 100, 100)

            return jsonify({
                'status': 'success',
                'mode': 'download',
                'filename': filename,
                'download_url': f'/api/get_file/{filename}',
                'message': 'Media ready! Starting download to your PC...'
            })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/get_file/<filename>')
def get_file(filename):
    """Serve file to user's PC browser and auto-delete from VPS afterwards."""
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(DOWNLOAD_DIR, safe_filename)

    if not os.path.exists(file_path):
        return "File not found or already downloaded.", 404

    delete_after = request.args.get('delete_after', 'false').lower() == 'true'
    is_batch = request.args.get('batch', 'false').lower() == 'true'
    mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    def on_close():
        # Signal the waiting batch thread that PC has finished receiving the file
        if safe_filename in active_pc_events:
            try:
                active_pc_events[safe_filename].set()
            except Exception:
                pass

        # Immediate cleanup for batch downloads or if delete_after is true
        if delete_after or is_batch:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🧹 Cleaned from VPS storage immediately: {safe_filename}")
            except Exception as e:
                print(f"Cleanup error for {safe_filename}: {e}")
        else:
            # Auto-delete temp file from VPS 120 seconds after streaming to user's PC starts
            def _delayed_cleanup():
                time.sleep(120)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass

            threading.Thread(target=_delayed_cleanup, daemon=True).start()

    response = send_file(file_path, mimetype=mime, as_attachment=True, download_name=safe_filename)
    response.call_on_close(on_close)
    return response


@app.route('/api/batch/pc_ack', methods=['POST'])
def batch_pc_ack():
    """Acknowledge receipt of a PC download from client side."""
    data = request.get_json() or {}
    filename = data.get('filename')
    if filename and filename in active_pc_events:
        try:
            active_pc_events[filename].set()
        except Exception:
            pass
    return jsonify({'status': 'ok'})


@app.route('/api/batch/pc_skip_delay', methods=['POST'])
def batch_pc_skip_delay():
    """Skip the delay countdown and proceed to next file immediately."""
    active_pc_skip_delay.set()
    return jsonify({'status': 'ok'})


@app.route('/api/clear_temp', methods=['POST'])
def clear_temp():
    """Clear all temporary downloaded files manually."""
    count = 0
    if os.path.exists(DOWNLOAD_DIR):
        for f in os.listdir(DOWNLOAD_DIR):
            fp = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                    count += 1
                except Exception:
                    pass
    return jsonify({'status': 'success', 'message': f'Cleaned {count} temporary files from VPS'})


# ── Batch Downloader ────────────────────────────────────────────────────────────

batch_status = {
    'is_running': False,
    'phase': 'idle',  # idle, downloading, batching, uploading, complete
    'current_item': 0,
    'total_items': 0,
    'downloaded_count': 0,
    'batch_count': 0,
    'current_batch': 0,
    'message': 'Ready',
    'total_size_mb': 0
}


def emit_batch_status(message, phase=None, current=None, total=None):
    """Emit batch process status updates"""
    global batch_status
    batch_status['message'] = message
    if phase:
        batch_status['phase'] = phase
    if current is not None:
        batch_status['current_item'] = current
    if total is not None:
        batch_status['total_items'] = total
    socketio.emit('batch_status_update', batch_status)


def format_size_mb(bytes_size):
    """Convert bytes to MB"""
    return round(bytes_size / (1024 * 1024), 2)


async def batch_download_and_upload(base_link, start_id, end_id, target_channel, max_batch_gb=6, delete_after=True):
    """Download range of messages to server first, then upload as grouped media albums of up to 10 files per set"""
    global client, batch_status
    
    try:
        # Parse base link
        peer = parse_telegram_base_link(base_link)
        entity = await client.get_entity(peer)
        
        total_messages = end_id - start_id + 1
        batch_status['total_items'] = total_messages
        batch_status['downloaded_count'] = 0
        batch_status['current_batch'] = 0
        batch_status['batch_count'] = 0
        batch_status['total_size_mb'] = 0
        total_downloaded_bytes = 0
        
        # Resolve target channel
        def _resolve(ch):
            if isinstance(ch, str) and ch.lstrip('-').isdigit():
                return int(ch)
            return ch
        
        target = _resolve(target_channel)
        try:
            target_entity = await client.get_entity(target)
        except Exception:
            target_entity = target
        
        emit_batch_status(
            f'📥 Phase 1: Downloading all media in range ({start_id} to {end_id})...',
            'downloading', 0, total_messages
        )
        
        downloaded_files = []
        
        # ── PHASE 1: DOWNLOAD ALL MEDIA IN RANGE TO VPS SERVER ────────────────
        for msg_id in range(start_id, end_id + 1):
            if not batch_status['is_running']:
                emit_batch_status('⏸️ Process stopped by user', 'idle')
                return
            
            current_idx = msg_id - start_id + 1
            batch_status['current_batch'] = current_idx
            
            emit_batch_status(
                f'📥 Downloading message {msg_id}/{end_id}...',
                'downloading', current_idx, total_messages
            )
            
            try:
                message = await client.get_messages(entity, ids=msg_id)
                
                if message and message.media:
                    file_path = await client.download_media(message, DOWNLOAD_DIR)
                    
                    if file_path and os.path.exists(file_path):
                        abs_file_path = os.path.abspath(file_path)
                        file_size = os.path.getsize(abs_file_path)
                        
                        # Extract or download thumbnail for video/media
                        thumb_path = await get_or_generate_thumbnail(client, message, abs_file_path, DOWNLOAD_DIR)

                        total_downloaded_bytes += file_size
                        batch_status['downloaded_count'] += 1
                        batch_status['total_size_mb'] = format_size_mb(total_downloaded_bytes)
                        
                        downloaded_files.append({
                            'path': abs_file_path,
                            'thumb': thumb_path,
                            'size': file_size,
                            'caption': message.message if message.message else None,
                            'msg_id': msg_id,
                            'grouped_id': message.grouped_id
                        })
                        
                        emit_batch_status(
                            f'✅ Downloaded #{msg_id}: {os.path.basename(abs_file_path)} ({format_size_mb(file_size)} MB)',
                            'downloading', current_idx, total_messages
                        )
                    else:
                        emit_batch_status(f'⚠️ Failed to download media for #{msg_id}', 'downloading', current_idx, total_messages)
                else:
                    emit_batch_status(f'⏭️ Skipping #{msg_id} (no media)', 'downloading', current_idx, total_messages)
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                emit_batch_status(f'❌ Error downloading #{msg_id}: {str(e)}', 'downloading', current_idx, total_messages)
        
        if not downloaded_files:
            batch_status['is_running'] = False
            emit_batch_status('⚠️ No media files were downloaded in the specified range.', 'complete')
            return

        # ── PHASE 2: GROUP INTO ALBUMS ACCORDING TO ORIGINAL GROUPED_ID & UPLOAD ──
        chunks = []
        current_album = []
        current_gid = None

        for item in downloaded_files:
            gid = item.get('grouped_id')
            if gid:
                if current_gid == gid and len(current_album) < 10:
                    current_album.append(item)
                else:
                    if current_album:
                        chunks.append(current_album)
                    current_album = [item]
                    current_gid = gid
            else:
                if current_album:
                    chunks.append(current_album)
                    current_album = []
                    current_gid = None
                chunks.append([item])

        if current_album:
            chunks.append(current_album)

        total_chunks = len(chunks)
        batch_status['batch_count'] = total_chunks
        
        emit_batch_status(
            f'📦 Phase 2: Uploading {len(downloaded_files)} file(s) in {total_chunks} group(s) (collections preserved)...',
            'uploading', 0, total_chunks
        )
        
        uploaded_media_count = 0
        
        for chunk_idx, chunk in enumerate(chunks, 1):
            if not batch_status['is_running']:
                emit_batch_status('⏸️ Process stopped by user', 'idle')
                break
                
            chunk_paths = [f['path'] for f in chunk if os.path.exists(f['path'])]
            chunk_captions = [f['caption'] or '' for f in chunk]
            
            if not chunk_paths:
                continue
                
            group_desc = f"Collection/Album ({len(chunk_paths)} files)" if len(chunk_paths) > 1 else f"#{chunk[0]['msg_id']}"
            emit_batch_status(
                f'📤 Uploading Group {chunk_idx}/{total_chunks}: {group_desc}...',
                'uploading', chunk_idx, total_chunks
            )
            
            sent = False
            retries = 0
            while not sent and retries < 3 and batch_status['is_running']:
                try:
                    if len(chunk_paths) > 1:
                        # Upload collection as Telegram Album / Media Group (max 10)
                        if any(chunk_captions):
                            try:
                                await client.send_file(target_entity, chunk_paths, caption=chunk_captions, supports_streaming=True)
                            except Exception:
                                await client.send_file(target_entity, chunk_paths, supports_streaming=True)
                        else:
                            await client.send_file(target_entity, chunk_paths, supports_streaming=True)
                    else:
                        # Single file with custom thumbnail and streaming enabled
                        item = chunk[0]
                        f_path = item['path']
                        f_thumb = item.get('thumb')
                        is_vid = f_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
                        cap = item['caption'] if item['caption'] else None
                        valid_thumb = f_thumb if (f_thumb and os.path.exists(f_thumb)) else None

                        await client.send_file(
                            target_entity,
                            f_path,
                            caption=cap,
                            thumb=valid_thumb,
                            supports_streaming=is_vid,
                            force_document=False
                        )
                    
                    sent = True
                    uploaded_media_count += len(chunk_paths)
                    emit_batch_status(
                        f'✅ Group {chunk_idx}/{total_chunks} uploaded successfully ({len(chunk_paths)} media files)!',
                        'uploading', chunk_idx, total_chunks
                    )
                    await asyncio.sleep(2)
                    
                except FloodWaitError as e:
                    emit_batch_status(f'⚠️ FloodWait {e.seconds}s during group upload...', 'uploading', chunk_idx, total_chunks)
                    await asyncio.sleep(e.seconds + 2)
                    retries += 1
                except Exception as up_err:
                    # Fallback to uploading files individually if album creation encounters error
                    emit_batch_status(f'⚠️ Album note ({str(up_err)}), uploading files individually...', 'uploading', chunk_idx, total_chunks)
                    for item in chunk:
                        if os.path.exists(item['path']):
                            try:
                                is_vid = item['path'].lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
                                f_thumb = item.get('thumb')
                                valid_thumb = f_thumb if (f_thumb and os.path.exists(f_thumb)) else None
                                await client.send_file(
                                    target_entity,
                                    item['path'],
                                    caption=item['caption'],
                                    thumb=valid_thumb,
                                    supports_streaming=is_vid,
                                    force_document=False
                                )
                                uploaded_media_count += 1
                                await asyncio.sleep(1.5)
                            except Exception as f_err:
                                emit_batch_status(f'❌ Upload error: {str(f_err)}', 'uploading', chunk_idx, total_chunks)
                    sent = True
            
            # Clean up files for this chunk after upload if requested
            if delete_after:
                for item in chunk:
                    if os.path.exists(item['path']):
                        try:
                            os.remove(item['path'])
                        except Exception:
                            pass
                    f_thumb = item.get('thumb')
                    if f_thumb and os.path.exists(f_thumb):
                        try:
                            os.remove(f_thumb)
                        except Exception:
                            pass
        
        batch_status['is_running'] = False
        emit_batch_status(
            f'✅ Process complete! Downloaded & uploaded {uploaded_media_count} media file(s) in {total_chunks} album group(s)',
            'complete'
        )
        
    except Exception as e:
        batch_status['is_running'] = False
        emit_batch_status(f'❌ Error: {str(e)}', 'complete')


async def upload_single_batch(batch_files, target_channel, batch_number, total_batches_str):
    """Upload batch files to target channel using Telethon send_file"""
    global client
    try:
        if not batch_files:
            return True
            
        total_files = len(batch_files)
        
        # Resolve target channel entity
        def _resolve(ch):
            if isinstance(ch, str) and ch.lstrip('-').isdigit():
                return int(ch)
            return ch
            
        target_resolved = _resolve(target_channel)
        try:
            target_entity = await client.get_entity(target_resolved)
        except Exception:
            target_entity = target_resolved
        
        # Collect absolute paths for existing downloaded files
        files_to_send = []
        for file_info in batch_files:
            p = os.path.abspath(file_info['path'])
            if os.path.exists(p):
                files_to_send.append(p)
                
        if not files_to_send:
            emit_batch_status('⚠️ No downloaded files found on disk to upload', 'uploading')
            return False
            
        # Telegram albums support up to 10 files per group
        chunk_size = 10
        chunks = [files_to_send[i:i + chunk_size] for i in range(0, len(files_to_send), chunk_size)]
        total_chunks = len(chunks)
        
        uploaded_count = 0
        for chunk_idx, chunk in enumerate(chunks, 1):
            emit_batch_status(
                f'📤 Uploading group {chunk_idx}/{total_chunks} ({len(chunk)} files)...',
                'uploading'
            )
            
            uploaded_chunk = False
            retry_count = 0
            while not uploaded_chunk and retry_count < 3:
                try:
                    if len(chunk) > 1:
                        # Send as Telethon album
                        await client.send_file(
                            target_entity,
                            chunk
                        )
                    else:
                        is_vid = chunk[0].lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
                        await client.send_file(
                            target_entity,
                            chunk[0],
                            supports_streaming=is_vid
                        )
                    uploaded_chunk = True
                    uploaded_count += len(chunk)
                    emit_batch_status(
                        f'✅ Uploaded group {chunk_idx}/{total_chunks} ({len(chunk)} files)',
                        'uploading'
                    )
                    await asyncio.sleep(2)
                except FloodWaitError as e:
                    emit_batch_status(f'⚠️ FloodWait {e.seconds}s during upload...', 'uploading')
                    await asyncio.sleep(e.seconds + 2)
                    retry_count += 1
                except Exception as chunk_err:
                    # Fallback to sending files individually if group fails
                    emit_batch_status(f'⚠️ Group upload note ({str(chunk_err)}), sending files individually...', 'uploading')
                    for f_path in chunk:
                        try:
                            is_vid = f_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
                            await client.send_file(
                                target_entity,
                                f_path,
                                supports_streaming=is_vid
                            )
                            uploaded_count += 1
                            await asyncio.sleep(1.5)
                        except Exception as f_err:
                            emit_batch_status(f'❌ Error uploading {os.path.basename(f_path)}: {str(f_err)}', 'uploading')
                    uploaded_chunk = True
            
        return uploaded_count > 0
        
    except Exception as e:
        emit_batch_status(f'❌ Error uploading batch: {str(e)}', 'uploading')
        return False


def cleanup_files(file_list):
    """Delete a list of files"""
    for file_info in file_list:
        try:
            if os.path.exists(file_info['path']):
                os.remove(file_info['path'])
        except Exception:
            pass


async def batch_direct_forward(base_link, start_id, end_id, target_channel):
    """Directly forward messages in a range using Telegram relay - no download, no re-upload."""
    global client, batch_status

    try:
        peer = parse_telegram_base_link(base_link)
        entity = await client.get_entity(peer)

        def _resolve(ch):
            if isinstance(ch, str) and ch.lstrip('-').isdigit():
                return int(ch)
            return ch

        target = _resolve(target_channel)
        try:
            target_entity = await client.get_entity(target)
        except Exception:
            target_entity = target

        total_messages = end_id - start_id + 1
        batch_status['total_items'] = total_messages
        batch_status['downloaded_count'] = 0
        batch_status['current_batch'] = 0
        batch_status['batch_count'] = 0
        batch_status['total_size_mb'] = 0

        emit_batch_status(
            f'🚀 Direct Forward Mode: Forwarding messages {start_id} → {end_id}...',
            'forwarding', 0, total_messages
        )

        forwarded = 0
        failed = 0

        # We buffer consecutive messages that share the same grouped_id to forward together as an album/collection
        current_group = []
        current_grouped_id = None

        async def forward_current_group():
            nonlocal forwarded, failed, current_group, current_grouped_id
            if not current_group:
                return
            retries = 0
            success = False
            group_to_send = list(current_group)
            current_group = []
            current_grouped_id = None

            while not success and retries < 3 and batch_status['is_running']:
                try:
                    if len(group_to_send) == 1:
                        await client.forward_messages(target_entity, group_to_send[0])
                        item_label = f"#{group_to_send[0].id}"
                    else:
                        await client.forward_messages(target_entity, group_to_send)
                        item_label = f"Collection/Album ({len(group_to_send)} items: #{group_to_send[0].id}..#{group_to_send[-1].id})"

                    forwarded += len(group_to_send)
                    batch_status['downloaded_count'] = forwarded
                    emit_batch_status(
                        f'✅ Forwarded {item_label}',
                        'forwarding', current_idx, total_messages
                    )
                    success = True
                    await asyncio.sleep(0.8)
                except FloodWaitError as e:
                    emit_batch_status(f'⚠️ FloodWait {e.seconds}s...', 'forwarding', current_idx, total_messages)
                    await asyncio.sleep(e.seconds + 1)
                    retries += 1
                except Exception as e:
                    emit_batch_status(f'❌ Error forwarding group: {str(e)}', 'forwarding', current_idx, total_messages)
                    failed += len(group_to_send)
                    success = True

        for msg_id in range(start_id, end_id + 1):
            if not batch_status['is_running']:
                emit_batch_status('⏸️ Process stopped by user', 'idle')
                return

            current_idx = msg_id - start_id + 1
            batch_status['current_batch'] = current_idx

            emit_batch_status(
                f'🚀 Reading message {msg_id}/{end_id}...',
                'forwarding', current_idx, total_messages
            )

            try:
                message = await client.get_messages(entity, ids=msg_id)
                if not message:
                    emit_batch_status(f'⏭️ Skipping #{msg_id} (not found)', 'forwarding', current_idx, total_messages)
                    continue

                gid = message.grouped_id
                if gid:
                    if current_grouped_id == gid and len(current_group) < 10:
                        current_group.append(message)
                    else:
                        if current_group:
                            await forward_current_group()
                        current_group = [message]
                        current_grouped_id = gid
                else:
                    if current_group:
                        await forward_current_group()
                    current_group = [message]
                    current_grouped_id = None
                    await forward_current_group()

            except FloodWaitError as e:
                emit_batch_status(f'⚠️ FloodWait {e.seconds}s...', 'forwarding', current_idx, total_messages)
                await asyncio.sleep(e.seconds + 1)
            except Exception as e:
                emit_batch_status(f'❌ Error on #{msg_id}: {str(e)}', 'forwarding', current_idx, total_messages)
                failed += 1

        # Flush any remaining album group
        if current_group:
            await forward_current_group()

        batch_status['is_running'] = False
        emit_batch_status(
            f'✅ Direct Forward complete! Forwarded {forwarded} messages, {failed} failed.',
            'complete'
        )

    except Exception as e:
        batch_status['is_running'] = False
        emit_batch_status(f'❌ Error: {str(e)}', 'complete')


async def batch_download_to_pc(base_link, start_id, end_id, delay_seconds=5, delete_after=True):
    """
    Sequentially download messages in range from Telegram, send each to user's PC browser,
    clean storage on VPS immediately after sending, and wait configured delay before next file.
    """
    global client, batch_status, active_pc_events, active_pc_skip_delay

    try:
        peer = parse_telegram_base_link(base_link)
        entity = await client.get_entity(peer)

        total_messages = end_id - start_id + 1
        batch_status['total_items'] = total_messages
        batch_status['downloaded_count'] = 0
        batch_status['current_batch'] = 0
        batch_status['batch_count'] = total_messages
        batch_status['total_size_mb'] = 0

        emit_batch_status(
            f'💻 Starting PC Batch Download ({start_id} → {end_id}) with {delay_seconds}s delay...',
            'pc_download', 0, total_messages
        )

        downloaded_count = 0
        total_downloaded_bytes = 0

        for msg_id in range(start_id, end_id + 1):
            if not batch_status['is_running']:
                emit_batch_status('⏸️ Process stopped by user', 'idle')
                return

            current_idx = msg_id - start_id + 1
            batch_status['current_item'] = current_idx
            batch_status['current_batch'] = current_idx

            emit_batch_status(
                f'🔍 Checking message {msg_id}/{end_id} from Telegram...',
                'pc_download', current_idx, total_messages
            )

            try:
                message = await client.get_messages(entity, ids=msg_id)

                if not message or not message.media:
                    emit_batch_status(f'⏭️ Skipping #{msg_id} (no media found)', 'pc_download', current_idx, total_messages)
                    await asyncio.sleep(0.5)
                    continue

                emit_batch_status(f'📥 Downloading #{msg_id} from Telegram to VPS...', 'downloading', current_idx, total_messages)

                def _dl_progress(c, t):
                    pct = round((c / t) * 100, 1) if t > 0 else 0
                    mb_curr = format_size_mb(c)
                    mb_tot = format_size_mb(t)
                    emit_batch_status(
                        f'📥 Downloading #{msg_id} to VPS: {mb_curr}/{mb_tot} MB ({pct}%)',
                        'downloading', current_idx, total_messages
                    )

                file_path = await client.download_media(message, DOWNLOAD_DIR, progress_callback=_dl_progress)

                if not file_path or not os.path.exists(file_path):
                    emit_batch_status(f'⚠️ Failed to download media for #{msg_id}', 'pc_download', current_idx, total_messages)
                    continue

                abs_path = os.path.abspath(file_path)
                safe_filename = os.path.basename(abs_path)
                file_size = os.path.getsize(abs_path)
                total_downloaded_bytes += file_size
                downloaded_count += 1
                batch_status['downloaded_count'] = downloaded_count
                batch_status['total_size_mb'] = format_size_mb(total_downloaded_bytes)

                # Event to wait for stream to PC to complete
                event = threading.Event()
                active_pc_events[safe_filename] = event
                active_pc_skip_delay.clear()

                download_url = f'/api/get_file/{safe_filename}?batch=true&delete_after={str(delete_after).lower()}'
                socketio.emit('batch_pc_file_ready', {
                    'filename': safe_filename,
                    'download_url': download_url,
                    'msg_id': msg_id,
                    'file_size_mb': format_size_mb(file_size),
                    'current': current_idx,
                    'total': total_messages,
                    'delay': delay_seconds
                })

                emit_batch_status(
                    f'💻 #{msg_id}: Ready! Streaming {safe_filename} ({format_size_mb(file_size)} MB) to PC...',
                    'pc_download', current_idx, total_messages
                )

                # Wait for PC stream to finish (or timeout up to 300s, or user skip)
                wait_seconds = 300
                while wait_seconds > 0 and not event.is_set() and batch_status['is_running']:
                    await asyncio.sleep(1)
                    wait_seconds -= 1

                active_pc_events.pop(safe_filename, None)

                if not batch_status['is_running']:
                    if delete_after and os.path.exists(abs_path):
                        try:
                            os.remove(abs_path)
                        except Exception:
                            pass
                    emit_batch_status('⏸️ Process stopped by user', 'idle')
                    return

                # Ensure storage cleanup on VPS
                if delete_after and os.path.exists(abs_path):
                    try:
                        os.remove(abs_path)
                        print(f"🧹 VPS storage cleaned: removed {safe_filename}")
                    except Exception as e:
                        print(f"Cleanup error: {e}")

                emit_batch_status(
                    f'🧹 VPS Storage cleaned for #{msg_id} ({safe_filename})',
                    'pc_download', current_idx, total_messages
                )

                # Delay before fetching the next file
                if msg_id < end_id and batch_status['is_running'] and delay_seconds > 0:
                    for sec in range(delay_seconds, 0, -1):
                        if not batch_status['is_running'] or active_pc_skip_delay.is_set():
                            break
                        emit_batch_status(
                            f'⏳ Delay: Waiting {sec}s before next download (#{msg_id + 1}/{end_id})... [VPS Storage Cleaned 🧹]',
                            'delay', current_idx, total_messages
                        )
                        await asyncio.sleep(1)

            except FloodWaitError as e:
                emit_batch_status(f'⚠️ FloodWait: Telegram asked to wait {e.seconds}s...', 'pc_download', current_idx, total_messages)
                await asyncio.sleep(e.seconds + 1)
            except Exception as e:
                emit_batch_status(f'❌ Error on #{msg_id}: {str(e)}', 'pc_download', current_idx, total_messages)
                await asyncio.sleep(1)

        batch_status['is_running'] = False
        emit_batch_status(
            f'✅ PC Batch Download complete! {downloaded_count} file(s) saved to PC. VPS storage 100% clean.',
            'complete'
        )

    except Exception as e:
        batch_status['is_running'] = False
        emit_batch_status(f'❌ Error: {str(e)}', 'complete')


def run_batch_process(base_link, start_id, end_id, target_channel, batch_mode, max_batch_gb, delete_after, delay_seconds=5):
    """Thread wrapper for batch process - routes to forward, download+upload, or download to PC based on mode."""
    try:
        ensure_client()
        if batch_mode == 'direct_forward':
            run_async(batch_direct_forward(base_link, start_id, end_id, target_channel))
        elif batch_mode == 'pc_download':
            run_async(batch_download_to_pc(base_link, start_id, end_id, delay_seconds, delete_after))
        else:
            run_async(batch_download_and_upload(base_link, start_id, end_id, target_channel, max_batch_gb, delete_after))
    except Exception as e:
        batch_status['is_running'] = False
        emit_batch_status(f'❌ Error: {str(e)}', 'complete')


@app.route('/api/batch/start', methods=['POST'])
def start_batch_download():
    """Start batch download process"""
    global batch_status
    
    if not transfer_status['logged_in']:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 400
    
    if batch_status['is_running']:
        return jsonify({'status': 'error', 'message': 'Batch process already running'}), 400
    
    data = request.get_json() or {}
    base_link = data.get('base_link', '').strip()
    start_id = data.get('start_id')
    end_id = data.get('end_id')
    target_channel = data.get('target_channel', '').strip()
    batch_mode = data.get('batch_mode', 'download_upload')  # 'download_upload', 'direct_forward', 'pc_download'
    max_batch_gb = data.get('max_batch_gb', 6)
    delete_after = data.get('delete_after', True)
    delay_seconds = int(data.get('delay_seconds', 5))
    
    if not base_link:
        return jsonify({'status': 'error', 'message': 'Base link is required'}), 400

    if batch_mode != 'pc_download' and not target_channel:
        return jsonify({'status': 'error', 'message': 'Target channel is required for upload / forward mode'}), 400
    
    try:
        start_id = int(start_id)
        end_id = int(end_id)
        
        if start_id <= 0 or end_id <= 0 or start_id > end_id:
            return jsonify({'status': 'error', 'message': 'Invalid message ID range'}), 400
            
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Start ID and End ID must be valid numbers'}), 400
    
    # Reset batch status
    batch_status.update({
        'is_running': True,
        'phase': 'starting',
        'current_item': 0,
        'total_items': 0,
        'downloaded_count': 0,
        'batch_count': 0,
        'current_batch': 0,
        'total_size_mb': 0
    })
    
    # Start in background thread
    t = threading.Thread(
        target=run_batch_process,
        args=(base_link, start_id, end_id, target_channel, batch_mode, max_batch_gb, delete_after, delay_seconds),
        daemon=True
    )
    t.start()
    
    return jsonify({'status': 'success', 'message': 'Batch process started'})


@app.route('/api/batch/stop', methods=['POST'])
def stop_batch_download():
    """Stop batch download process"""
    global batch_status, active_pc_skip_delay
    batch_status['is_running'] = False
    active_pc_skip_delay.set()
    for ev in list(active_pc_events.values()):
        try:
            ev.set()
        except Exception:
            pass
    return jsonify({'status': 'success', 'message': 'Batch process stopping...'})


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("🚀 Starting Telegram Media Transfer Web UI on http://0.0.0.0:3000")
    socketio.run(app, host='0.0.0.0', port=3000, debug=False, allow_unsafe_werkzeug=True)
