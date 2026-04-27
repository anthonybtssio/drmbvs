from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, flash, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
import os
import json
import random
import secrets
import hashlib
import base64
import requests as req_lib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'drumtech-bts-sio-slam-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drums.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'pdf'}
STYLES   = ['Rock', 'Metal', 'Pop', 'Jazz', 'Funk', 'Autre']
STATUSES = [('learning', 'En apprentissage'), ('mastered', 'Maîtrisé'), ('on_hold', 'En pause')]

db = SQLAlchemy(app)

# ─── Modèles ──────────────────────────────────────────────────────────────────

class Song(db.Model):
    __tablename__ = 'songs'

    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    artist        = db.Column(db.String(200), nullable=False)
    bpm           = db.Column(db.Integer)
    style         = db.Column(db.String(50), nullable=False, default='Rock')
    difficulty    = db.Column(db.Integer, nullable=False, default=3)
    tiktok_url    = db.Column(db.String(500))
    tiktok_id     = db.Column(db.String(200))
    tablature_pdf = db.Column(db.String(200))
    notes         = db.Column(db.Text)
    status        = db.Column(db.String(20), default='learning')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship('PracticeSession', backref='song', lazy=True,
                                cascade='all, delete-orphan')

    def last_practiced(self):
        if not self.sessions: return None
        return max(self.sessions, key=lambda s: s.practiced_at).practiced_at

    def days_since_practice(self):
        lp = self.last_practiced()
        if lp is None: return 9999
        return (datetime.utcnow() - lp).days

    def to_dict(self):
        lp = self.last_practiced()
        return {
            'id':            self.id,
            'title':         self.title,
            'artist':        self.artist,
            'bpm':           self.bpm,
            'style':         self.style,
            'difficulty':    self.difficulty,
            'tiktok_url':    self.tiktok_url,
            'tiktok_id':     self.tiktok_id,
            'tablature_pdf': self.tablature_pdf,
            'notes':         self.notes,
            'status':        self.status,
            'created_at':    self.created_at.isoformat(),
            'last_practiced': lp.isoformat() if lp else None,
            'session_count': len(self.sessions),
        }


class PracticeSession(db.Model):
    __tablename__ = 'practice_sessions'

    id               = db.Column(db.Integer, primary_key=True)
    song_id          = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    practiced_at     = db.Column(db.DateTime, default=datetime.utcnow)
    duration_minutes = db.Column(db.Integer)
    rating           = db.Column(db.Integer)
    notes            = db.Column(db.Text)

    def to_dict(self):
        return {
            'id':               self.id,
            'song_id':          self.song_id,
            'song_title':       self.song.title if self.song else None,
            'song_artist':      self.song.artist if self.song else None,
            'practiced_at':     self.practiced_at.isoformat(),
            'duration_minutes': self.duration_minutes,
            'rating':           self.rating,
            'notes':            self.notes,
        }


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class SongSuggestion(db.Model):
    __tablename__ = 'song_suggestions'

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    artist       = db.Column(db.String(200), nullable=False)
    suggested_by = db.Column(db.String(100))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class TikTokConfig(db.Model):
    __tablename__ = 'tiktok_config'
    id            = db.Column(db.Integer, primary_key=True)
    client_key    = db.Column(db.String(200))
    client_secret = db.Column(db.String(200))


class TikTokToken(db.Model):
    __tablename__ = 'tiktok_tokens'
    id           = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(500))
    open_id      = db.Column(db.String(200))
    expires_at   = db.Column(db.DateTime)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow)


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_tiktok_id(url):
    if not url: return None
    parts = url.rstrip('/').split('/')
    if 'video' in parts:
        idx = parts.index('video')
        if idx + 1 < len(parts):
            return parts[idx + 1].split('?')[0]
    return None


# ─── Routes publiques ─────────────────────────────────────────────────────────

@app.route('/')
def index():
    songs          = Song.query.order_by(Song.created_at.desc()).all()
    styles         = sorted({s.style for s in songs})
    total_sessions = PracticeSession.query.count()
    return render_template('index.html', songs=songs, styles=styles,
                           statuses=STATUSES, total_sessions=total_sessions)


@app.route('/suggestion', methods=['GET', 'POST'])
def suggestion():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        artist = request.form.get('artist', '').strip()
        name = request.form.get('name', '').strip()
        if title and artist:
            sugg = SongSuggestion(title=title, artist=artist, suggested_by=name)
            db.session.add(sugg)
            db.session.commit()
            flash('Merci ! Ta suggestion a bien été envoyée.', 'success')
            return redirect(url_for('suggestion'))
        flash('Le titre et l\'artiste sont obligatoires !', 'error')
    return render_template('suggestion.html')


@app.route('/practice')
def practice():
    learning  = Song.query.filter_by(status='learning').all()
    suggested = None
    if learning:
        suggested = max(learning, key=lambda s: s.days_since_practice())
    recent    = (PracticeSession.query
                 .order_by(PracticeSession.practiced_at.desc())
                 .limit(15).all())
    all_songs = Song.query.order_by(Song.artist).all()
    return render_template('practice.html',
                           suggested=suggested,
                           sessions=recent,
                           songs=all_songs)


@app.route('/stats')
def stats():
    total      = Song.query.count()
    mastered   = Song.query.filter_by(status='mastered').count()
    learning   = Song.query.filter_by(status='learning').count()
    on_hold    = Song.query.filter_by(status='on_hold').count()
    n_sessions = PracticeSession.query.count()

    style_data = (db.session.query(Song.style, db.func.count(Song.id))
                  .group_by(Song.style).all())
    diff_data  = (db.session.query(Song.difficulty, db.func.count(Song.id))
                  .group_by(Song.difficulty).order_by(Song.difficulty).all())

    since           = datetime.utcnow() - timedelta(days=30)
    recent_sessions = (PracticeSession.query
                       .filter(PracticeSession.practiced_at >= since)
                       .order_by(PracticeSession.practiced_at).all())
    daily = {}
    for s in recent_sessions:
        day = s.practiced_at.strftime('%Y-%m-%d')
        daily[day] = daily.get(day, 0) + 1

    top_songs = (db.session.query(
                    Song.title, Song.artist, db.func.count(PracticeSession.id).label('cnt'))
                 .join(PracticeSession, Song.id == PracticeSession.song_id)
                 .group_by(Song.id)
                 .order_by(db.desc('cnt'))
                 .limit(5).all())

    return render_template('stats.html',
        total=total, mastered=mastered, learning=learning, on_hold=on_hold,
        n_sessions=n_sessions,
        style_data=json.dumps([{'label': r[0], 'value': r[1]} for r in style_data]),
        diff_data =json.dumps([{'label': str(r[0]), 'value': r[1]} for r in diff_data]),
        daily_data=json.dumps(daily),
        top_songs=top_songs,
    )


# ─── API JSON ─────────────────────────────────────────────────────────────────

@app.route('/api/songs')
def api_songs():
    style   = request.args.get('style')
    diff    = request.args.get('difficulty', type=int)
    q       = request.args.get('q', '').strip()
    bpm_min = request.args.get('bpm_min', type=int)
    bpm_max = request.args.get('bpm_max', type=int)
    status  = request.args.get('status')

    query = Song.query
    if style:   query = query.filter_by(style=style)
    if diff:    query = query.filter_by(difficulty=diff)
    if q:       query = query.filter(Song.title.ilike(f'%{q}%') | Song.artist.ilike(f'%{q}%'))
    if bpm_min: query = query.filter(Song.bpm >= bpm_min)
    if bpm_max: query = query.filter(Song.bpm <= bpm_max)
    if status:  query = query.filter_by(status=status)

    return jsonify([s.to_dict() for s in query.all()])


@app.route('/api/practice/log', methods=['POST'])
def api_log_practice():
    data = request.get_json(force=True)
    ps   = PracticeSession(
        song_id          = data['song_id'],
        duration_minutes = data.get('duration_minutes'),
        rating           = data.get('rating'),
        notes            = data.get('notes', ''),
    )
    db.session.add(ps)
    db.session.commit()
    return jsonify({'ok': True, 'session': ps.to_dict()})


# ─── Admin — Auth ─────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password', '')):
            session['user_id']  = user.id
            session['username'] = user.username
            return redirect(url_for('admin_dashboard'))
        flash('Identifiants incorrects.', 'error')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))


# ─── Admin — Dashboard & Songs ────────────────────────────────────────────────

@app.route('/admin')
@login_required
def admin_dashboard():
    songs = Song.query.order_by(Song.created_at.desc()).all()
    return render_template('admin/dashboard.html', songs=songs)


@app.route('/admin/songs/add', methods=['GET', 'POST'])
@login_required
def admin_add_song():
    if request.method == 'POST':
        tiktok_url = request.form.get('tiktok_url', '').strip()
        song = Song(
            title      = request.form.get('title', '').strip(),
            artist     = request.form.get('artist', '').strip(),
            bpm        = request.form.get('bpm', type=int),
            style      = request.form.get('style', 'Rock'),
            difficulty = request.form.get('difficulty', type=int, default=3),
            tiktok_url = tiktok_url or None,
            tiktok_id  = extract_tiktok_id(tiktok_url),
            notes      = request.form.get('notes', '').strip() or None,
            status     = request.form.get('status', 'learning'),
        )
        _handle_pdf_upload(request, song)
        db.session.add(song)
        db.session.commit()
        flash(f'« {song.title} » ajouté avec succès !', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/song_form.html', song=None, styles=STYLES, statuses=STATUSES)


@app.route('/admin/songs/<int:song_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_song(song_id):
    song = Song.query.get_or_404(song_id)
    if request.method == 'POST':
        tiktok_url      = request.form.get('tiktok_url', '').strip()
        song.title      = request.form.get('title', '').strip()
        song.artist     = request.form.get('artist', '').strip()
        song.bpm        = request.form.get('bpm', type=int)
        song.style      = request.form.get('style', 'Rock')
        song.difficulty = request.form.get('difficulty', type=int, default=3)
        song.tiktok_url = tiktok_url or None
        song.tiktok_id  = extract_tiktok_id(tiktok_url)
        song.notes      = request.form.get('notes', '').strip() or None
        song.status     = request.form.get('status', 'learning')
        _handle_pdf_upload(request, song)
        db.session.commit()
        flash(f'« {song.title} » modifié.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/song_form.html', song=song, styles=STYLES, statuses=STATUSES)


@app.route('/admin/songs/<int:song_id>/delete', methods=['POST'])
@login_required
def admin_delete_song(song_id):
    song  = Song.query.get_or_404(song_id)
    title = song.title
    db.session.delete(song)
    db.session.commit()
    flash(f'« {title} » supprimé.', 'info')
    return redirect(url_for('admin_dashboard'))


# ─── Admin — Suggestions & TikTok Sync ────────────────────────────────────────

@app.route('/admin/suggestions')
@login_required
def admin_suggestions():
    suggestions = SongSuggestion.query.order_by(SongSuggestion.created_at.desc()).all()
    return render_template('admin/suggestions.html', suggestions=suggestions)


@app.route('/admin/suggestions/<int:sugg_id>/delete', methods=['POST'])
@login_required
def admin_delete_suggestion(sugg_id):
    sugg = SongSuggestion.query.get_or_404(sugg_id)
    db.session.delete(sugg)
    db.session.commit()
    flash('Suggestion supprimée.', 'info')
    return redirect(url_for('admin_suggestions'))


@app.route('/admin/tiktok')
@login_required
def admin_tiktok():
    cfg = TikTokConfig.query.first() or TikTokConfig()
    token = TikTokToken.query.first()
    tt_songs = Song.query.filter(Song.tiktok_id.isnot(None)).all()
    return render_template('admin/tiktok.html', cfg=cfg, token=token, tt_songs=tt_songs)


@app.route('/admin/tiktok/save', methods=['POST'])
@login_required
def admin_tiktok_save():
    cfg = TikTokConfig.query.first()
    if not cfg:
        cfg = TikTokConfig()
        db.session.add(cfg)
    cfg.client_key = request.form.get('client_key', '').strip()
    cfg.client_secret = request.form.get('client_secret', '').strip()
    db.session.commit()
    flash('Identifiants TikTok sauvegardés.', 'success')
    return redirect(url_for('admin_tiktok'))


@app.route('/admin/tiktok/connect')
@login_required
def admin_tiktok_connect():
    cfg = TikTokConfig.query.first()
    if not cfg or not cfg.client_key:
        flash('Configure ton Client Key d\'abord.', 'error')
        return redirect(url_for('admin_tiktok'))
    
    # On détecte l'URL de base dynamiquement (ex: https://xxx.ngrok.app)
    # TikTok exige du HTTPS, donc on s'assure que le redirect_uri utilise le bon schéma
    base_url = request.host_url.rstrip('/')
    if '127.0.0.1' not in base_url and 'localhost' not in base_url:
        # Si on est sur un tunnel (ngrok), Flask peut voir http au lieu de https
        # On force https car TikTok l'exige
        base_url = base_url.replace('http://', 'https://')
    
    redirect_uri = f"{base_url}/admin/tiktok/callback"
    
    print(f"DEBUG: Tentative de connexion avec Client Key: {cfg.client_key}")
    print(f"DEBUG: Redirect URI généré : {redirect_uri}")
    
    # Génération du PKCE
    code_verifier = secrets.token_urlsafe(64)
    session['tiktok_code_verifier'] = code_verifier
    
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')

    csrf_state = secrets.token_hex(16)
    session['tiktok_csrf'] = csrf_state
    
    url = "https://www.tiktok.com/v2/auth/authorize/"
    scopes = "user.info.basic,video.list"
    
    params = {
        "client_key": cfg.client_key,
        "scope": scopes,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": csrf_state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    
    from urllib.parse import urlencode
    target = f"{url}?{urlencode(params)}"
    return redirect(target)


@app.route('/admin/tiktok/callback')
@login_required
def admin_tiktok_callback():
    code  = request.args.get('code')
    state = request.args.get('state')
    
    if state != session.get('tiktok_csrf'):
        flash('Erreur de sécurité (CSRF mismatch).', 'error')
        return redirect(url_for('admin_tiktok'))
    
    cfg = TikTokConfig.query.first()
    code_verifier = session.get('tiktok_code_verifier')

    # On utilise la même logique pour le callback
    base_url = request.host_url.rstrip('/')
    if '127.0.0.1' not in base_url and 'localhost' not in base_url:
        base_url = base_url.replace('http://', 'https://')
    redirect_uri = f"{base_url}/admin/tiktok/callback"

    # Échange du code contre un token
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    data = {
        "client_key": cfg.client_key,
        "client_secret": cfg.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        resp = req_lib.post(url, data=data, headers=headers)
        res = resp.json()
        if 'access_token' in res:
            tk = TikTokToken.query.first()
            if not tk:
                tk = TikTokToken()
                db.session.add(tk)
            tk.access_token = res['access_token']
            tk.open_id = res['open_id']
            tk.expires_at = datetime.utcnow() + timedelta(seconds=res['expires_in'])
            tk.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Connecté à TikTok avec succès !', 'success')
        else:
            flash(f"Erreur TikTok : {res.get('error_description', res.get('message', 'Inconnue'))}", 'error')
    except Exception as e:
        flash(f"Erreur technique : {str(e)}", 'error')
        
    return redirect(url_for('admin_tiktok'))


@app.route('/admin/tiktok/sync', methods=['POST'])
@login_required
def admin_tiktok_sync():
    tk = TikTokToken.query.first()
    if not tk or tk.expires_at < datetime.utcnow():
        flash('Session TikTok expirée ou absente. Reconnecte-toi.', 'error')
        return redirect(url_for('admin_tiktok'))
    
    url = "https://open.tiktokapis.com/v2/video/list/"
    headers = {"Authorization": f"Bearer {tk.access_token}", "Content-Type": "application/json"}
    
    # On demande explicitement les champs nécessaires (id, titre, description, lien, etc.)
    body = {
        "max_count": 20,
        "fields": "id,title,video_description,share_url,cover_image_url,create_time"
    }

    try:
        resp = req_lib.post(url, headers=headers, json=body)
        data = resp.json()
        
        # Debug pour voir la structure exacte en cas d'erreur
        if data.get('error', {}).get('code') != 'ok':
            print(f"DEBUG SYNC TIKTOK : {data}")
            msg = data.get('error', {}).get('message') or "Erreur API"
            flash(f"Erreur TikTok : {msg}", 'error')
            return redirect(url_for('admin_tiktok'))
        
        videos = data.get('data', {}).get('videos', [])
        added = 0
        for v in videos:
            vid_id = v.get('id')
            if vid_id and not Song.query.filter_by(tiktok_id=vid_id).first():
                # On utilise video_description si le titre est vide
                desc = v.get('video_description') or v.get('title') or "Sans titre"
                title, artist = _parse_video_description(desc)
                s = Song(
                    title=title,
                    artist=artist,
                    tiktok_id=vid_id,
                    tiktok_url=v.get('share_url'),
                    status='learning',
                    style='Autre'
                )
                db.session.add(s)
                added += 1
        db.session.commit()
        flash(f"{added} vidéos importées !", 'success')
    except Exception as e:
        flash(f"Erreur : {str(e)}", 'error')
        
    return redirect(url_for('admin_tiktok'))


@app.route('/admin/tiktok/disconnect', methods=['POST'])
@login_required
def admin_tiktok_disconnect():
    tk = TikTokToken.query.first()
    if tk:
        db.session.delete(tk)
        db.session.commit()
    flash('Déconnecté de TikTok.', 'info')
    return redirect(url_for('admin_tiktok'))


# Configuration TikTok par pseudo (pour affichage ou fallback)
TIKTOK_USERNAME = "drmbvs"

def _parse_video_description(desc):
    """
    Tente d'extraire le titre et l'artiste d'une description TikTok.
    Format attendu : "Titre - Artiste" ou "Artiste - Titre"
    """
    if not desc:
        return "Sans titre", "Artiste inconnu"
    
    # Nettoyage des hashtags
    clean = " ".join([w for w in desc.split() if not w.startswith('#')])
    
    if " - " in clean:
        parts = clean.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    
    return clean.strip() or "Sans titre", "Artiste inconnu"


@app.route('/admin/sync-tiktok', methods=['POST'])
@login_required
def admin_sync_tiktok():
    """Redirige vers la synchronisation officielle si le token est présent."""
    tk = TikTokToken.query.first()
    if not tk:
        flash('Tu dois d\'abord connecter ton compte TikTok officiel dans "Gérer TikTok".', 'info')
        return redirect(url_for('admin_tiktok'))
    return admin_tiktok_sync()


# ─── Fichiers & Helpers ───────────────────────────────────────────────────────

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def _handle_pdf_upload(req, song):
    if 'tablature' not in req.files: return
    f = req.files['tablature']
    if f and f.filename and allowed_file(f.filename):
        safe = secure_filename(f"{song.artist}_{song.title}.pdf".replace(' ', '_'))
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], safe))
        song.tablature_pdf = safe


TIKTOK_CLIENT_KEY = "sbawjisz6xb01ig6cv"
TIKTOK_CLIENT_SECRET = "HftANNpSxu20fNlFJb2nFYzeLQcQ4OsA"

def _seed():
    if User.query.count() == 0:
        admin = User(username='admin')
        admin.set_password('drumtech2024')
        db.session.add(admin)
    
    # Configuration TikTok par défaut avec les clés fournies
    cfg = TikTokConfig.query.first()
    if not cfg:
        cfg = TikTokConfig(client_key=TIKTOK_CLIENT_KEY, client_secret=TIKTOK_CLIENT_SECRET)
        db.session.add(cfg)
        print(f"DEBUG: Création config TikTok avec {TIKTOK_CLIENT_KEY}")
    else:
        # On force la mise à jour avec les clés du script
        cfg.client_key = TIKTOK_CLIENT_KEY
        cfg.client_secret = TIKTOK_CLIENT_SECRET
        print(f"DEBUG: Mise à jour config TikTok avec {TIKTOK_CLIENT_KEY}")

    if Song.query.count() == 0:
        # Quelques données par défaut...
        pass
    db.session.commit()


with app.app_context():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.create_all()
    _seed()


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)
