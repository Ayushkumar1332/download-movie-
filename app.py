import os, json, uuid, shutil
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, abort
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
MOVIES = BASE / 'uploads' / 'movies'
POSTERS = BASE / 'uploads' / 'posters'
CHUNKS = BASE / 'tmp_chunks'
DATA_FILE = BASE / 'movies.json'
for p in (MOVIES, POSTERS, CHUNKS): p.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'replace-this-secret-key-before-hosting')
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # Each chunk is limited to 25MB
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB per video
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'Ayush')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Ayush@12345')
ALLOWED_VIDEO_EXT = {'.mp4', '.mkv', '.webm', '.mov', '.avi'}
ALLOWED_POSTER_EXT = {'.jpg', '.jpeg', '.png', '.webp'}

def load_movies():
    if not DATA_FILE.exists(): return []
    try: return json.loads(DATA_FILE.read_text(encoding='utf-8'))
    except Exception: return []

def save_movies(items):
    DATA_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin'): return redirect(url_for('admin_login'))
        return fn(*args, **kwargs)
    return wrapper

@app.get('/')
def home():
    return render_template('index.html', movies=load_movies())

@app.get('/movie/<movie_id>')
def movie_detail(movie_id):
    movie = next((m for m in load_movies() if m['id'] == movie_id), None)
    if not movie: abort(404)
    return render_template('movie.html', movie=movie)

@app.get('/download/<movie_id>')
def download(movie_id):
    movie = next((m for m in load_movies() if m['id'] == movie_id), None)
    if not movie: abort(404)
    path = MOVIES / movie['stored_name']
    if not path.exists(): abort(404, 'Video file is missing from server storage.')
    movies = load_movies()
    movie = next((m for m in movies if m['id'] == movie_id), None)
    movie['downloads'] = int(movie.get('downloads', 0)) + 1
    save_movies(movies)
    return send_file(path, as_attachment=True, download_name=movie['original_name'], conditional=True)

@app.get('/admin/login')
def admin_login():
    return render_template('login.html')

@app.post('/admin/login')
def admin_login_post():
    if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return redirect(url_for('admin_dashboard'))
    return render_template('login.html', error='Incorrect username or password.'), 401

@app.get('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('home'))

@app.get('/admin')
@admin_required
def admin_dashboard():
    movies = load_movies()
    return render_template('admin.html', movies=movies, total=len(movies), downloads=sum(m.get('downloads', 0) for m in movies))

@app.post('/api/upload/start')
@admin_required
def upload_start():
    payload = request.get_json(force=True)
    name = secure_filename(payload.get('filename', ''))
    ext = Path(name).suffix.lower()
    size = int(payload.get('size', 0))
    if not name or ext not in ALLOWED_VIDEO_EXT: return jsonify(error='Unsupported video format.'), 400
    if size <= 0 or size > MAX_FILE_SIZE: return jsonify(error='File must be between 1 byte and 5GB.'), 400
    upload_id = uuid.uuid4().hex
    folder = CHUNKS / upload_id
    folder.mkdir()
    meta = {'filename': name, 'size': size, 'title': payload.get('title', Path(name).stem)[:150], 'description': payload.get('description', '')[:2000], 'category': payload.get('category', 'Other')[:80], 'year': payload.get('year', '')[:4], 'language': payload.get('language', 'Unknown')[:80], 'chunk_count': int(payload.get('chunk_count', 0))}
    (folder / 'meta.json').write_text(json.dumps(meta), encoding='utf-8')
    return jsonify(upload_id=upload_id)

@app.post('/api/upload/chunk/<upload_id>/<int:chunk_index>')
@admin_required
def upload_chunk(upload_id, chunk_index):
    folder = CHUNKS / upload_id
    if not folder.exists(): return jsonify(error='Upload session not found.'), 404
    if chunk_index < 0: return jsonify(error='Invalid chunk index.'), 400
    chunk = request.files.get('chunk')
    if not chunk: return jsonify(error='Chunk is missing.'), 400
    chunk.save(folder / f'{chunk_index:06d}.part')
    return jsonify(ok=True)


@app.post('/api/upload/finish/<upload_id>')
@admin_required
def upload_finish(upload_id):
    folder = CHUNKS / upload_id
    if not folder.exists(): return jsonify(error='Upload session not found.'), 404
    meta = json.loads((folder / 'meta.json').read_text(encoding='utf-8'))
    target_name = f'{uuid.uuid4().hex}{Path(meta["filename"]).suffix.lower()}'
    target = MOVIES / target_name
    received = sorted(folder.glob('*.part'))
    if len(received) != meta['chunk_count']:
        return jsonify(error=f'Expected {meta["chunk_count"]} chunks but received {len(received)}.'), 400
    total = 0
    with target.open('wb') as output:
        for part in received:
            with part.open('rb') as stream:
                shutil.copyfileobj(stream, output, 1024 * 1024)
            total += part.stat().st_size
    if total != meta['size']:
        target.unlink(missing_ok=True)
        return jsonify(error='Uploaded file size does not match the original.'), 400
    poster_name = ''
    poster = request.files.get('poster')
    if poster and poster.filename:
        ext = Path(poster.filename).suffix.lower()
        if ext in ALLOWED_POSTER_EXT:
            poster_name = f'{uuid.uuid4().hex}{ext}'
            poster.save(POSTERS / poster_name)
    movies = load_movies()
    movies.insert(0, {'id': uuid.uuid4().hex, 'title': meta['title'] or Path(meta['filename']).stem, 'description': meta['description'], 'category': meta['category'], 'year': meta['year'], 'language': meta['language'], 'original_name': meta['filename'], 'stored_name': target_name, 'size': total, 'poster': poster_name, 'downloads': 0})
    save_movies(movies)
    shutil.rmtree(folder, ignore_errors=True)
    return jsonify(ok=True)

@app.post('/admin/delete/<movie_id>')
@admin_required
def delete_movie(movie_id):
    movies = load_movies()
    movie = next((m for m in movies if m['id'] == movie_id), None)
    if movie:
        (MOVIES / movie['stored_name']).unlink(missing_ok=True)
        if movie.get('poster'): (POSTERS / movie['poster']).unlink(missing_ok=True)
        save_movies([m for m in movies if m['id'] != movie_id])
    return redirect(url_for('admin_dashboard'))

@app.get('/posters/<filename>')
def poster(filename):
    return send_file(POSTERS / secure_filename(filename))

@app.errorhandler(413)
def too_large(_):
    return jsonify(error='Chunk too large. Upload chunks are capped at 25MB.'), 413


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
