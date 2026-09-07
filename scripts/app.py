from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, abort, g
from flask_login import login_user, logout_user, current_user
from werkzeug.utils import secure_filename
import os
import sys
import uuid
from datetime import date

# Funcio per trobar recursos (templates/static) quan estem empaquetats
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        # PyInstaller guarda els recursos en una carpeta temporal _MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), relative_path)

# Asegurar que el modulo principal se encuentra en PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import get_connection, init_db
from scripts.auth import login_manager, verify_credentials, admin_required
from scripts.config import get_documents_path

app = Flask(__name__,
            template_folder=resource_path('templates'),
            static_folder=resource_path('static'))
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-canvia-en-produccio')
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB per petició (varis fitxers)
login_manager.init_app(app)

DOCUMENTS_DIR = get_documents_path()
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'heic', 'webp'}
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10MB per fitxer

DEFAULT_LABOR_TYPES = ['Poda', 'Sulfatar', 'Recol·lecció', 'Reg', 'Altres']
DEFAULT_EXPENSE_TYPES = ['Productes', 'Aigua', 'Averies', 'Gasoil', 'Altres']


# --- Suport multi-parcel·la: totes les rutes de dades porten <parcel_id> a la URL.
# Aquests dos ganxos permeten que les plantilles facin url_for('index') sense haver
# de passar parcel_id explicitament: Flask l'injecta automaticament a partir de la
# parcel·la de la petició actual (g.parcel_id).

@app.before_request
def load_current_parcel():
    parcel_id = (request.view_args or {}).get('parcel_id')
    if parcel_id is None:
        return
    conn = get_connection()
    parcel = conn.execute("SELECT * FROM parcels WHERE id = ? AND is_deleted = 0", (parcel_id,)).fetchone()
    if not parcel:
        abort(404)
    g.parcel_id = parcel_id
    g.current_parcel = parcel


@app.url_defaults
def inject_parcel_id(endpoint, values):
    if 'parcel_id' in values:
        return
    parcel_id = g.get('parcel_id')
    if not parcel_id:
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'parcel_id'):
        values['parcel_id'] = parcel_id


def allowed_document(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS


def save_documents(conn, parcel_id, entity_type, entity_id, files):
    """Desa al disc i registra a la taula 'documents' els fitxers rebuts per a una entitat concreta."""
    for f in files:
        if not f or not f.filename:
            continue
        if not allowed_document(f.filename):
            continue

        original_filename = secure_filename(f.filename)
        ext = original_filename.rsplit('.', 1)[1].lower()
        stored_filename = f"{uuid.uuid4().hex}.{ext}"

        entity_dir = os.path.join(DOCUMENTS_DIR, str(parcel_id), entity_type, str(entity_id))
        os.makedirs(entity_dir, exist_ok=True)
        dest_path = os.path.join(entity_dir, stored_filename)
        f.save(dest_path)

        size_bytes = os.path.getsize(dest_path)
        if size_bytes > MAX_DOCUMENT_SIZE_BYTES:
            os.remove(dest_path)
            continue

        relative_path = f"{parcel_id}/{entity_type}/{entity_id}/{stored_filename}"
        conn.execute(
            "INSERT INTO documents (parcel_id, entity_type, entity_id, original_filename, stored_filename, relative_path, mime_type, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (parcel_id, entity_type, entity_id, original_filename, stored_filename, relative_path, f.mimetype, size_bytes)
        )
    conn.commit()


def get_documents(conn, entity_type, entity_id):
    return conn.execute(
        "SELECT * FROM documents WHERE entity_type = ? AND entity_id = ? AND is_deleted = 0 ORDER BY uploaded_at DESC",
        (entity_type, entity_id)
    ).fetchall()


def seed_defaults_for_parcel(conn, parcel_id):
    conn.executemany("INSERT INTO labor_types (name, parcel_id) VALUES (?, ?)",
                     [(name, parcel_id) for name in DEFAULT_LABOR_TYPES])
    conn.executemany("INSERT INTO expense_types (name, parcel_id) VALUES (?, ?)",
                     [(name, parcel_id) for name in DEFAULT_EXPENSE_TYPES])
    conn.commit()


@app.before_request
def require_login():
    if request.endpoint in ('login', 'static') or request.endpoint is None:
        return
    if not current_user.is_authenticated:
        return redirect(url_for('login', next=request.path))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = verify_credentials(username, password)
        if user:
            login_user(user)
            return redirect(request.args.get('next') or url_for('list_parcels'))
        return render_template('login.html', error='Usuari o contrasenya incorrectes')
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.context_processor
def inject_today():
    today = date.today()
    return {
        'current_date': today.isoformat(),
        'current_year': today.year,
        'current_month': today.month,
        'current_day': today.day,
        'days': range(1, 32),
        'months': [
            (1, 'Gener'), (2, 'Febrer'), (3, 'Març'), (4, 'Abril'),
            (5, 'Maig'), (6, 'Juny'), (7, 'Juliol'), (8, 'Agost'),
            (9, 'Setembre'), (10, 'Octubre'), (11, 'Novembre'), (12, 'Desembre')
        ],
        'years': range(2024, 2031)
    }

@app.template_filter('format_date')
def format_date_filter(s):
    if not s: return ""
    # Try to parse ISO date (YYYY-MM-DD)
    try:
        if ' ' in s: # Timestamp format: 2026-04-08 12:30:00
            date_part = s.split(' ')[0]
            y, m, d = date_part.split('-')
            time_part = s.split(' ')[1][:5] # HH:MM
            return f"{d}/{m}/{y} {time_part}"
        else: # Date format: 2026-04-08
            y, m, d = s.split('-')
            return f"{d}/{m}/{y}"
    except:
        return s

@app.template_filter('minutes_to_time')
def minutes_to_time_filter(minutes):
    if minutes is None: return ""
    try:
        minutes = int(minutes)
        return f"{minutes // 60:02d}:{minutes % 60:02d}"
    except (ValueError, TypeError):
        return ""

@app.template_filter('seconds_to_duration')
def seconds_to_duration_filter(seconds):
    if seconds is None: return ""
    try:
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m = rem // 60
        return f"{h}h {m:02d}m" if h else f"{m}m"
    except (ValueError, TypeError):
        return ""


@app.route('/')
def list_parcels():
    conn = get_connection()
    parcels = conn.execute("""
        SELECT p.*,
            (SELECT COALESCE(SUM(total_income), 0) FROM production WHERE parcel_id = p.id AND is_deleted = 0) as income_total,
            (SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE parcel_id = p.id AND is_deleted = 0)
                + (SELECT COALESCE(SUM(total_price), 0) FROM labors WHERE parcel_id = p.id AND is_deleted = 0) as expenses_total
        FROM parcels p
        WHERE p.is_deleted = 0
        ORDER BY p.name
    """).fetchall()
    return render_template('parcels.html', parcels=parcels)


@app.route('/parcels/add', methods=['POST'])
@admin_required
def add_parcel():
    name = request.form.get('name', '').strip()
    if name:
        conn = get_connection()
        cur = conn.execute("INSERT INTO parcels (name) VALUES (?)", (name,))
        conn.commit()
        seed_defaults_for_parcel(conn, cur.lastrowid)
    return redirect(url_for('list_parcels'))


@app.route('/parcela/<int:parcel_id>/')
def index(parcel_id):
    conn = get_connection()
    labors_total = conn.execute("SELECT SUM(total_price) FROM labors WHERE is_deleted = 0 AND parcel_id = ?", (parcel_id,)).fetchone()[0] or 0
    expenses_total = conn.execute("SELECT SUM(amount) FROM expenses WHERE is_deleted = 0 AND parcel_id = ?", (parcel_id,)).fetchone()[0] or 0
    income_total = conn.execute("SELECT SUM(total_income) FROM production WHERE is_deleted = 0 AND parcel_id = ?", (parcel_id,)).fetchone()[0] or 0

    total_expenses = labors_total + expenses_total
    net_profit = income_total - total_expenses

    return render_template('index.html',
                           income_total=income_total,
                           total_expenses=total_expenses,
                           net_profit=net_profit)

@app.route('/parcela/<int:parcel_id>/labor/add', methods=['GET', 'POST'])
def add_labor(parcel_id):
    conn = get_connection()
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        worker_id = request.form['worker_id']
        labor_type_id = request.form['labor_type_id']
        hours = float(request.form['hours'])
        price_per_hour = float(request.form['price_per_hour'])
        description = request.form.get('description', '')
        total_price = hours * price_per_hour

        cur = conn.execute("INSERT INTO labors (parcel_id, date, worker_id, labor_type_id, hours, price_per_hour, total_price, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (parcel_id, date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description))
        conn.commit()
        save_documents(conn, parcel_id, 'labor', cur.lastrowid, request.files.getlist('documents'))
        return redirect(url_for('index'))

    workers = conn.execute("SELECT * FROM workers WHERE is_deleted = 0 AND parcel_id = ? ORDER BY name", (parcel_id,)).fetchall()
    labor_types = conn.execute("SELECT * FROM labor_types WHERE is_deleted = 0 AND parcel_id = ? ORDER BY name", (parcel_id,)).fetchall()
    return render_template('labor_form.html', workers=workers, labor_types=labor_types)

@app.route('/parcela/<int:parcel_id>/production/add', methods=['GET', 'POST'])
def add_production(parcel_id):
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        kilos = float(request.form['kilos'])
        price_per_kilo = float(request.form['price_per_kilo'])
        total_income = kilos * price_per_kilo

        conn = get_connection()
        cur = conn.execute("INSERT INTO production (parcel_id, date, kilos, price_per_kilo, total_income) VALUES (?, ?, ?, ?, ?)",
                     (parcel_id, date_str, kilos, price_per_kilo, total_income))
        conn.commit()
        save_documents(conn, parcel_id, 'production', cur.lastrowid, request.files.getlist('documents'))
        return redirect(url_for('index'))
    return render_template('production_form.html')

@app.route('/parcela/<int:parcel_id>/expense/add', methods=['GET', 'POST'])
def add_expense(parcel_id):
    conn = get_connection()
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        expense_type_id = request.form['expense_type_id']
        description = request.form['description']
        amount = float(request.form['amount'])

        cur = conn.execute("INSERT INTO expenses (parcel_id, date, expense_type_id, description, amount) VALUES (?, ?, ?, ?, ?)",
                     (parcel_id, date_str, expense_type_id, description, amount))
        conn.commit()
        save_documents(conn, parcel_id, 'expense', cur.lastrowid, request.files.getlist('documents'))
        return redirect(url_for('index'))

    expense_types = conn.execute("SELECT * FROM expense_types WHERE is_deleted = 0 AND parcel_id = ? ORDER BY name", (parcel_id,)).fetchall()
    return render_template('expense_form.html', expense_types=expense_types)

@app.route('/parcela/<int:parcel_id>/history')
def history(parcel_id):
    conn = get_connection()
    labors = conn.execute("""
        SELECT l.*, w.name as worker_name, lt.name as labor_type_name
        FROM labors l
        JOIN workers w ON l.worker_id = w.id
        JOIN labor_types lt ON l.labor_type_id = lt.id
        WHERE l.is_deleted = 0 AND l.parcel_id = ?
        ORDER BY l.date DESC
    """, (parcel_id,)).fetchall()
    production = conn.execute("SELECT * FROM production WHERE is_deleted = 0 AND parcel_id = ? ORDER BY date DESC", (parcel_id,)).fetchall()
    expenses = conn.execute("""
        SELECT e.*, et.name as expense_type_name
        FROM expenses e
        JOIN expense_types et ON e.expense_type_id = et.id
        WHERE e.is_deleted = 0 AND e.parcel_id = ?
        ORDER BY e.date DESC
    """, (parcel_id,)).fetchall()

    def docs_by_entity(entity_type):
        rows = conn.execute(
            "SELECT * FROM documents WHERE entity_type = ? AND parcel_id = ? AND is_deleted = 0 ORDER BY uploaded_at",
            (entity_type, parcel_id)
        ).fetchall()
        grouped = {}
        for row in rows:
            grouped.setdefault(row['entity_id'], []).append(row)
        return grouped

    return render_template('history.html', labors=labors, production=production, expenses=expenses,
                           labor_docs=docs_by_entity('labor'), production_docs=docs_by_entity('production'),
                           expense_docs=docs_by_entity('expense'))

# Quick Add Master Data
@app.route('/parcela/<int:parcel_id>/master/worker/add', methods=['POST'])
def quick_add_worker(parcel_id):
    name = request.form.get('name')
    if name:
        conn = get_connection()
        try:
            cur = conn.execute("INSERT INTO workers (name, parcel_id) VALUES (?, ?)", (name, parcel_id))
            new_id = cur.lastrowid
            conn.commit()
            return jsonify({'success': True, 'id': new_id, 'name': name})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'Nom buit'}), 400

@app.route('/parcela/<int:parcel_id>/master/labor_type/add', methods=['POST'])
def quick_add_labor_type(parcel_id):
    name = request.form.get('name')
    if name:
        conn = get_connection()
        try:
            cur = conn.execute("INSERT INTO labor_types (name, parcel_id) VALUES (?, ?)", (name, parcel_id))
            new_id = cur.lastrowid
            conn.commit()
            return jsonify({'success': True, 'id': new_id, 'name': name})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'Nom buit'}), 400

@app.route('/parcela/<int:parcel_id>/master/expense_type/add', methods=['POST'])
def quick_add_expense_type(parcel_id):
    name = request.form.get('name')
    if name:
        conn = get_connection()
        try:
            cur = conn.execute("INSERT INTO expense_types (name, parcel_id) VALUES (?, ?)", (name, parcel_id))
            new_id = cur.lastrowid
            conn.commit()
            return jsonify({'success': True, 'id': new_id, 'name': name})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'Nom buit'}), 400

@app.route('/parcela/<int:parcel_id>/delete/<string:category>/<int:item_id>', methods=['POST'])
def delete_item(parcel_id, category, item_id):
    conn = get_connection()
    if category == 'labor':
        conn.execute("UPDATE labors SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND parcel_id = ?", (item_id, parcel_id))
    elif category == 'production':
        conn.execute("UPDATE production SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND parcel_id = ?", (item_id, parcel_id))
    elif category == 'expense':
        conn.execute("UPDATE expenses SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND parcel_id = ?", (item_id, parcel_id))
    conn.commit()
    return redirect(url_for('history'))

@app.route('/documents/<int:doc_id>/download')
def download_document(doc_id):
    conn = get_connection()
    doc = conn.execute("SELECT * FROM documents WHERE id=? AND is_deleted = 0", (doc_id,)).fetchone()
    if not doc:
        abort(404)
    return send_from_directory(DOCUMENTS_DIR, doc['relative_path'], as_attachment=True, download_name=doc['original_filename'])

@app.route('/documents/<int:doc_id>/delete', methods=['POST'])
def delete_document(doc_id):
    conn = get_connection()
    conn.execute("UPDATE documents SET is_deleted = 1 WHERE id = ?", (doc_id,))
    conn.commit()
    redirect_to = request.form.get('redirect_to') or ''
    if not redirect_to.startswith('/') or redirect_to.startswith('//'):
        redirect_to = url_for('list_parcels')
    return redirect(redirect_to)

@app.route('/parcela/<int:parcel_id>/labor/edit/<int:id>', methods=['GET', 'POST'])
def edit_labor(parcel_id, id):
    conn = get_connection()
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        worker_id = request.form['worker_id']
        labor_type_id = request.form['labor_type_id']
        hours = float(request.form['hours'])
        price_per_hour = float(request.form['price_per_hour'])
        description = request.form.get('description', '')
        total_price = hours * price_per_hour

        conn.execute("UPDATE labors SET date=?, worker_id=?, labor_type_id=?, hours=?, price_per_hour=?, total_price=?, description=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND parcel_id=?",
                     (date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description, id, parcel_id))
        conn.commit()
        save_documents(conn, parcel_id, 'labor', id, request.files.getlist('documents'))
        return redirect(url_for('history'))

    item = conn.execute("SELECT * FROM labors WHERE id=? AND parcel_id=? AND is_deleted = 0", (id, parcel_id)).fetchone()
    if not item:
        abort(404)
    # Parse date
    y, m, d = item['date'].split('-')
    item_date = {'year': int(y), 'month': int(m), 'day': int(d)}

    workers = conn.execute("SELECT * FROM workers WHERE is_deleted = 0 AND parcel_id = ? ORDER BY name", (parcel_id,)).fetchall()
    labor_types = conn.execute("SELECT * FROM labor_types WHERE is_deleted = 0 AND parcel_id = ? ORDER BY name", (parcel_id,)).fetchall()
    documents = get_documents(conn, 'labor', id)
    return render_template('labor_form.html', item=item, item_date=item_date, workers=workers, labor_types=labor_types, documents=documents)

@app.route('/parcela/<int:parcel_id>/production/edit/<int:id>', methods=['GET', 'POST'])
def edit_production(parcel_id, id):
    conn = get_connection()
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        kilos = float(request.form['kilos'])
        price_per_kilo = float(request.form['price_per_kilo'])
        total_income = kilos * price_per_kilo

        conn.execute("UPDATE production SET date=?, kilos=?, price_per_kilo=?, total_income=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND parcel_id=?",
                     (date_str, kilos, price_per_kilo, total_income, id, parcel_id))
        conn.commit()
        save_documents(conn, parcel_id, 'production', id, request.files.getlist('documents'))
        return redirect(url_for('history'))

    item = conn.execute("SELECT * FROM production WHERE id=? AND parcel_id=? AND is_deleted = 0", (id, parcel_id)).fetchone()
    if not item:
        abort(404)
    y, m, d = item['date'].split('-')
    item_date = {'year': int(y), 'month': int(m), 'day': int(d)}
    documents = get_documents(conn, 'production', id)
    return render_template('production_form.html', item=item, item_date=item_date, documents=documents)

@app.route('/parcela/<int:parcel_id>/expense/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(parcel_id, id):
    conn = get_connection()
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        expense_type_id = request.form['expense_type_id']
        description = request.form['description']
        amount = float(request.form['amount'])

        conn.execute("UPDATE expenses SET date=?, expense_type_id=?, description=?, amount=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND parcel_id=?",
                     (date_str, expense_type_id, description, amount, id, parcel_id))
        conn.commit()
        save_documents(conn, parcel_id, 'expense', id, request.files.getlist('documents'))
        return redirect(url_for('history'))

    item = conn.execute("SELECT * FROM expenses WHERE id=? AND parcel_id=? AND is_deleted = 0", (id, parcel_id)).fetchone()
    if not item:
        abort(404)
    y, m, d = item['date'].split('-')
    item_date = {'year': int(y), 'month': int(m), 'day': int(d)}
    expense_types = conn.execute("SELECT * FROM expense_types WHERE is_deleted = 0 AND parcel_id = ? ORDER BY name", (parcel_id,)).fetchall()
    documents = get_documents(conn, 'expense', id)
    return render_template('expense_form.html', item=item, item_date=item_date, expense_types=expense_types, documents=documents)


VEGGA_PAGES = ["a25/programs", "sectors", "fertilizers", "filters", "sensors"]
VEGGA_SYNC_INTERVAL_HOURS = 4


def vegga_hours_since_sync(conn, unit_id):
    row = conn.execute("""
        SELECT (julianday('now') - julianday(MAX(snapshot_at))) * 24 AS hours_since
        FROM vegga_status WHERE unit_id = ?
    """, (unit_id,)).fetchone()
    return row['hours_since'] if row and row['hours_since'] is not None else None


@app.route('/parcela/<int:parcel_id>/vegga')
def vegga(parcel_id):
    from scripts.vegga_scraper import scrape as vegga_scrape

    conn = get_connection()
    unit_id = request.args.get('unit', type=int) or g.current_parcel['vegga_unit_id']

    if not unit_id:
        return render_template('vegga.html', unit_id=None, status=None, meters=[], filter_events=[],
                               sectors=[], programs=[], analog_sensors=[], digital_sensors=[],
                               sync_error=None, just_synced=False)

    force_refresh = request.args.get('refresh') == '1'

    hours_since = vegga_hours_since_sync(conn, unit_id)
    needs_sync = force_refresh or hours_since is None or hours_since > VEGGA_SYNC_INTERVAL_HOURS

    sync_error = None
    if needs_sync:
        try:
            vegga_scrape(str(unit_id), VEGGA_PAGES, show=False)
        except Exception as e:
            sync_error = str(e)

    status = conn.execute(
        "SELECT * FROM vegga_status WHERE unit_id = ? ORDER BY id DESC LIMIT 1", (unit_id,)
    ).fetchone()

    meters = conn.execute("""
        SELECT * FROM vegga_water_meters
        WHERE unit_id = ? AND id IN (
            SELECT MAX(id) FROM vegga_water_meters WHERE unit_id = ? GROUP BY meter_id
        )
        ORDER BY CAST(meter_id AS INTEGER)
    """, (unit_id, unit_id)).fetchall()

    filter_events = conn.execute("""
        SELECT * FROM vegga_filter_events
        WHERE unit_id = ?
        ORDER BY CAST(vegga_id AS INTEGER) DESC
        LIMIT 20
    """, (unit_id,)).fetchall()

    sectors = conn.execute("""
        SELECT * FROM vegga_sectors
        WHERE unit_id = ? AND sector_op = 1
        ORDER BY sector_id
    """, (unit_id,)).fetchall()

    programs = conn.execute("""
        SELECT * FROM vegga_programs
        WHERE unit_id = ? AND (duration_seconds > 0 OR sector1 > 0)
        ORDER BY program_id
    """, (unit_id,)).fetchall()

    analog_sensors = conn.execute("""
        SELECT * FROM vegga_analog_sensors
        WHERE unit_id = ? AND snapshot_at = (SELECT MAX(snapshot_at) FROM vegga_analog_sensors WHERE unit_id = ?)
    """, (unit_id, unit_id)).fetchall()

    digital_sensors = conn.execute("""
        SELECT * FROM vegga_digital_sensors
        WHERE unit_id = ? AND snapshot_at = (SELECT MAX(snapshot_at) FROM vegga_digital_sensors WHERE unit_id = ?)
    """, (unit_id, unit_id)).fetchall()

    return render_template('vegga.html', unit_id=unit_id, status=status, meters=meters,
                           filter_events=filter_events, sectors=sectors, programs=programs,
                           analog_sensors=analog_sensors, digital_sensors=digital_sensors,
                           sync_error=sync_error, just_synced=needs_sync)


@app.route('/parcela/<int:parcel_id>/reports')
def reports(parcel_id):
    conn = get_connection()

    # Expenses by type
    expenses_by_type = conn.execute("""
        SELECT et.name, SUM(e.amount) as total
        FROM expenses e
        JOIN expense_types et ON e.expense_type_id = et.id
        WHERE e.is_deleted = 0 AND e.parcel_id = ?
        GROUP BY et.name
    """, (parcel_id,)).fetchall()

    return render_template('reports.html', expenses_by_type=expenses_by_type)

import csv
import io
from flask import make_response

@app.route('/parcela/<int:parcel_id>/export/csv/<string:category>')
def export_csv(parcel_id, category):
    conn = get_connection()
    si = io.StringIO()
    cw = csv.writer(si)

    if category == 'labors':
        data = conn.execute("SELECT * FROM labors WHERE parcel_id = ?", (parcel_id,)).fetchall()
        cw.writerow(['ID', 'Data', 'WorkerID', 'TypeID', 'Hours', 'Price/H', 'Total', 'Notes'])
    elif category == 'production':
        data = conn.execute("SELECT * FROM production WHERE parcel_id = ?", (parcel_id,)).fetchall()
        cw.writerow(['ID', 'Data', 'Kilos', 'Price/Kg', 'Total'])
    elif category == 'expenses':
        data = conn.execute("SELECT * FROM expenses WHERE parcel_id = ?", (parcel_id,)).fetchall()
        cw.writerow(['ID', 'Data', 'TypeID', 'Description', 'Amount'])
    else: return "Invalid"

    for row in data:
        cw.writerow(list(row))

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={category}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

def seed_data():
    conn = get_connection()
    # Seed Labor Types if empty (parcel·la 1 = Servereta)
    if not conn.execute("SELECT 1 FROM labor_types WHERE parcel_id = 1 LIMIT 1").fetchone():
        conn.executemany("INSERT INTO labor_types (name, parcel_id) VALUES (?, 1)",
                         [(n,) for n in DEFAULT_LABOR_TYPES])
    # Seed Expense Types if empty
    if not conn.execute("SELECT 1 FROM expense_types WHERE parcel_id = 1 LIMIT 1").fetchone():
        conn.executemany("INSERT INTO expense_types (name, parcel_id) VALUES (?, 1)",
                         [(n,) for n in DEFAULT_EXPENSE_TYPES])
    conn.commit()

if __name__ == '__main__':
    init_db()
    seed_data()
    app.run(debug=os.getenv('FLASK_DEBUG', '0') == '1', host='0.0.0.0', port=5000)
