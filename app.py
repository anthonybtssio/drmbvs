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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'drumtech-bts-sio-slam-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drums.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'pdf'}
STYLES = ['Rock', 'Metal', 'Pop', 'Jazz', 'Funk', 'Autre']
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
    difficulty    = db.Column(db.Integer, nullable=False, default=3)   # 1-5
    tiktok_url    = db.Column(db.String(500))
    tiktok_id     = db.Column(db.String(200))
    tablature_pdf = db.Column(db.String(200))
    notes         = db.Column(db.Text)
    status        = db.Column(db.String(20), default='learning')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship('PracticeSession', backref='song', lazy=True,
                                cascade='all, delete-orphan')

    def last_practiced(self):
        if not self.sessions:
            return None
        return max(self.sessions, key=lambda s: s.practiced_at).practiced_at

    def days_since_practice(self):
        lp = self.last_practiced()
        if lp is None:
            return 9999
        return (datetime.utcnow() - lp).days

    def to_dict(self):
        lp = self.last_practiced()
        return {
            'id':           self.id,
            'title':        self.title,
            'artist':       self.artist,
            'bpm':          self.bpm,
            'style':        self.style,
            'difficulty':   self.difficulty,
            'tiktok_url':   self.tiktok_url,
            'tiktok_id':    self.tiktok_id,
            'tablature_pdf':self.tablature_pdf,
            'notes':        self.notes,
            'status':       self.status,
            'created_at':   self.created_at.isoformat(),
            'last_practiced': lp.isoformat() if lp else None,
            'session_count': len(self.sessions),
        }


class PracticeSession(db.Model):
    __tablename__ = 'practice_sessions'

    id               = db.Column(db.Integer, primary_key=True)
    song_id          = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    practiced_at     = db.Column(db.DateTime, default=datetime.utcnow)
    duration_minutes = db.Column(db.Integer)
    rating           = db.Column(db.Integer)   # 1-5
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


# ─── Auth ─────────────────────────────────────────────────────────────────────

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
    if not url:
        return None
    parts = url.rstrip('/').split('/')
    if 'video' in parts:
        idx = parts.index('video')
        if idx + 1 < len(parts):
            return parts[idx + 1].split('?')[0]
    return None


# ─── Routes publiques ─────────────────────────────────────────────────────────

@app.route('/')
def index():
    songs  = Song.query.order_by(Song.created_at.desc()).all()
    styles = sorted({s.style for s in songs})
    return render_template('index.html', songs=songs, styles=styles, statuses=STATUSES)


@app.route('/practice')
def practice():
    learning = Song.query.filter_by(status='learning').all()
    suggested = None
    if learning:
        suggested = max(learning, key=lambda s: s.days_since_practice())

    recent = (PracticeSession.query
              .order_by(PracticeSession.practiced_at.desc())
              .limit(15).all())
    all_songs = Song.query.order_by(Song.artist).all()
    return render_template('practice.html',
                           suggested=suggested,
                           sessions=recent,
                           songs=all_songs)


@app.route('/stats')
def stats():
    total    = Song.query.count()
    mastered = Song.query.filter_by(status='mastered').count()
    learning = Song.query.filter_by(status='learning').count()
    on_hold  = Song.query.filter_by(status='on_hold').count()
    n_sessions = PracticeSession.query.count()

    style_data = (db.session.query(Song.style, db.func.count(Song.id))
                  .group_by(Song.style).all())

    diff_data = (db.session.query(Song.difficulty, db.func.count(Song.id))
                 .group_by(Song.difficulty).order_by(Song.difficulty).all())

    # Sessions des 30 derniers jours par jour
    since = datetime.utcnow() - timedelta(days=30)
    recent_sessions = (PracticeSession.query
                       .filter(PracticeSession.practiced_at >= since)
                       .order_by(PracticeSession.practiced_at).all())

    daily = {}
    for s in recent_sessions:
        day = s.practiced_at.strftime('%Y-%m-%d')
        daily[day] = daily.get(day, 0) + 1

    # Top 5 morceaux pratiqués
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
        diff_data=json.dumps([{'label': str(r[0]), 'value': r[1]} for r in diff_data]),
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
    if style:
        query = query.filter_by(style=style)
    if diff:
        query = query.filter_by(difficulty=diff)
    if q:
        query = query.filter(
            Song.title.ilike(f'%{q}%') | Song.artist.ilike(f'%{q}%')
        )
    if bpm_min:
        query = query.filter(Song.bpm >= bpm_min)
    if bpm_max:
        query = query.filter(Song.bpm <= bpm_max)
    if status:
        query = query.filter_by(status=status)

    return jsonify([s.to_dict() for s in query.all()])


@app.route('/api/practice/log', methods=['POST'])
def api_log_practice():
    data = request.get_json(force=True)
    ps = PracticeSession(
        song_id          = data['song_id'],
        duration_minutes = data.get('duration_minutes'),
        rating           = data.get('rating'),
        notes            = data.get('notes', ''),
    )
    db.session.add(ps)
    db.session.commit()
    return jsonify({'ok': True, 'session': ps.to_dict()})


@app.route('/api/stats/summary')
def api_stats_summary():
    return jsonify({
        'total':    Song.query.count(),
        'mastered': Song.query.filter_by(status='mastered').count(),
        'learning': Song.query.filter_by(status='learning').count(),
        'sessions': PracticeSession.query.count(),
    })


# ─── Admin ────────────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password', '')):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('admin_dashboard'))
        flash('Identifiants incorrects.', 'error')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))


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
        tiktok_url = request.form.get('tiktok_url', '').strip()
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
    song = Song.query.get_or_404(song_id)
    title = song.title
    db.session.delete(song)
    db.session.commit()
    flash(f'« {title} » supprimé.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ─── Helpers internes ─────────────────────────────────────────────────────────

def _handle_pdf_upload(req, song):
    if 'tablature' not in req.files:
        return
    f = req.files['tablature']
    if f and f.filename and allowed_file(f.filename):
        safe = secure_filename(f"{song.artist}_{song.title}.pdf".replace(' ', '_'))
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], safe))
        song.tablature_pdf = safe


def _seed():
    if User.query.count() == 0:
        admin = User(username='admin')
        admin.set_password('drumtech2024')
        db.session.add(admin)

    if Song.query.count() == 0:
        songs_data = [
            ('In the Air Tonight',   'Phil Collins',        99,  'Rock',  2, 'mastered'),
            ('Tom Sawyer',           'Rush',               184,  'Rock',  5, 'learning'),
            ('Hysteria',             'Muse',               106,  'Rock',  4, 'learning'),
            ('Enter Sandman',        'Metallica',          123,  'Metal', 3, 'mastered'),
            ('One',                  'Metallica',          212,  'Metal', 5, 'learning'),
            ('Painkiller',           'Judas Priest',       240,  'Metal', 5, 'learning'),
            ('Uptown Funk',          'Mark Ronson',        115,  'Pop',   2, 'mastered'),
            ("Can't Stop",           'Red Hot Chili Peppers', 92,'Rock',  3, 'learning'),
            ('Hot for Teacher',      'Van Halen',          180,  'Rock',  5, 'on_hold'),
            ('Superstition',         'Stevie Wonder',       98,  'Funk',  3, 'mastered'),
            ('Soul to Squeeze',      'RHCP',                80,  'Rock',  2, 'mastered'),
            ('Toxicity',             'System of a Down',   110,  'Metal', 4, 'learning'),
            ('YYZ',                  'Rush',               176,  'Rock',  5, 'on_hold'),
            ('Billie Jean',          'Michael Jackson',    117,  'Pop',   2, 'mastered'),
            ('Take Five',            'Dave Brubeck',        84,  'Jazz',  4, 'learning'),
        ]
        notes_map = {
            'Tom Sawyer':      'Section Neil Peart très technique, fills complexes',
            'Hysteria':        'Groove disco-rock, hi-hat pattern tricky',
            'One':             'Section double pédale ultra-rapide en fin de morceau',
            'Painkiller':      'Scott Travis — vitesse maximale, extrêmement difficile',
            'Hot for Teacher': 'Intro légendaire Alex Van Halen',
            'Take Five':       'Morceau en 5/4, pattern inhabituel',
            'YYZ':             'Intro en 10/8, très complexe',
        }
        all_songs = []
        for title, artist, bpm, style, diff, status in songs_data:
            s = Song(title=title, artist=artist, bpm=bpm, style=style,
                     difficulty=diff, status=status,
                     notes=notes_map.get(title))
            all_songs.append(s)
            db.session.add(s)

        db.session.flush()

        # Sessions de pratique pour les 45 derniers jours
        mastered_songs = [s for s in all_songs if s.status == 'mastered']
        learning_songs = [s for s in all_songs if s.status == 'learning']

        for i in range(45, 0, -1):
            day = datetime.utcnow() - timedelta(days=i)
            if random.random() < 0.6:  # ~60% de jours de pratique
                pool = mastered_songs + random.sample(
                    learning_songs, min(2, len(learning_songs))
                )
                for song in random.sample(pool, min(3, len(pool))):
                    ps = PracticeSession(
                        song_id          = song.id,
                        practiced_at     = day + timedelta(hours=random.randint(14, 22)),
                        duration_minutes = random.choice([10, 15, 20, 30]),
                        rating           = random.randint(3, 5),
                    )
                    db.session.add(ps)

    db.session.commit()


# ─── Init ─────────────────────────────────────────────────────────────────────

with app.app_context():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.create_all()
    _seed()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
