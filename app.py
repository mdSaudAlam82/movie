"""
HubLoader Flask App
Run locally : python app.py
Deploy      : gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 2
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import threading
import core

app = Flask(__name__)
CORS(app)

# ── Per-thread session (one per gunicorn thread, cookies never mix) ───────────
_local = threading.local()

def sess():
    if not hasattr(_local, 's'):
        _local.s = core.make_session()
    return _local.s


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/trending')
def trending():
    page = max(1, int(request.args.get('page', 1)))
    return jsonify(core.get_homepage_movies(sess(), page))


@app.route('/api/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    return jsonify(core.search_movies(q, sess()))


@app.route('/api/info')
def info():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    return jsonify(core.get_content_info(url, sess()))


@app.route('/api/extract', methods=['POST'])
def extract():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400
    return jsonify(core.extract_link(url, sess()))


# ── Dev server ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
