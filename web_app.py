"""
Telegram Media Transfer - Web UI
Flask web application with real-time progress tracking
Supports: Login via web, Find Channel IDs, Media Transfer, Content Download
"""

from flask import Flask, render_template, request, jsonify, send_file, session
from flask_socketio import SocketIO, emit
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, Channel, Chat
import asyncio
import os
import json
import re
import io
import mimetypes
from datetime import datetime
import threading

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
DOWNLOAD_DIR = 'telegram_downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ── Migrate legacy session file ────────────────────────────────────────────────
if os.path.exists('session.session') and not os.path.exists(SESSION_PATH + '.session'):
    import shutil
    try:
        shutil.copy('session.session', SESSION_PATH + '.session')
    except Exception:
        pass
if os.path.exists('transferred_messages.json') and not os.path.exists(TRANSFERRED_DB):
    import shutil
    try:
        shutil.copy('transferred_messages.json', TRANSFERRED_DB)
    except Exception:
        pass

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

        emit_status('📥 Fetching messages...')
        messages = []
        async for message in client.iter_messages(src, limit=None):
            if message.media:
                messages.append(message)

        total = len(messages)
        transfer_status['total'] = total
        emit_status(f'📊 Found {total} media messages', 0, total)

        db = load_transferred_db()
        already = sum(1 for m in messages if is_already_transferred(db, src, m.id))
        if already:
            emit_status(f'⏭️ {already} already transferred — will skip')

        success = failed = skipped = 0

        for idx, message in enumerate(messages, 1):
            if not transfer_status['is_running']:
                emit_status('⏸️ Transfer stopped by user')
                break

            if is_already_transferred(db, src, message.id):
                skipped += 1
                transfer_status['skipped'] = skipped
                transfer_status['current'] = idx
                emit_status(f'⏭️ Skipping #{message.id}', idx, total)
                continue

            emit_status(f'📥 Downloading #{message.id}...', idx, total)
            try:
                file_path = await client.download_media(message, DOWNLOAD_DIR)
                if file_path:
                    emit_status(f'⬆️ Uploading {os.path.basename(file_path)}...', idx, total)
                    caption = message.message if message.message else None
                    is_video = file_path.lower().endswith(
                        ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'))
                    await client.send_file(
                        tgt, file_path,
                        caption=caption,
                        supports_streaming=is_video,
                        force_document=False
                    )
                    emit_status(f'✅ Done #{message.id}', idx, total)
                    success += 1
                    transfer_status['success'] = success
                    mark_as_transferred(db, src, message.id)
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                    await asyncio.sleep(3)
                else:
                    failed += 1
                    transfer_status['failed'] = failed
            except FloodWaitError as e:
                emit_status(f'⚠️ FloodWait {e.seconds}s...', idx, total)
                await asyncio.sleep(e.seconds)
            except Exception as e:
                emit_status(f'❌ Error: {e}', idx, total)
                failed += 1
                transfer_status['failed'] = failed

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

                    try:
                        caption = message.message if message.message else None
                        is_video = file_path.lower().endswith(
                            ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v')
                        )
                        def upload_progress(c, t):
                            emit_link_progress('Uploading', c, t)

                        await client.send_file(
                            tgt, file_path,
                            caption=caption,
                            supports_streaming=is_video,
                            force_document=False,
                            progress_callback=upload_progress
                        )
                    finally:
                        try:
                            os.remove(file_path)
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

    mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    # Auto-delete temp file from VPS 60 seconds after streaming to user's PC starts
    def _delayed_cleanup():
        import time; time.sleep(60)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

    threading.Thread(target=_delayed_cleanup, daemon=True).start()
    return send_file(file_path, mimetype=mime, as_attachment=True, download_name=safe_filename)


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("🚀 Starting Telegram Media Transfer Web UI on http://0.0.0.0:3000")
    socketio.run(app, host='0.0.0.0', port=3000, debug=False, allow_unsafe_werkzeug=True)
