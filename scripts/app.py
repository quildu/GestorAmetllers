from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import login_user, logout_user, current_user
import os
import sys
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
from scripts.auth import login_manager, verify_credentials, User

app = Flask(__name__,
            template_folder=resource_path('templates'),
            static_folder=resource_path('static'))
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-canvia-en-produccio')
login_manager.init_app(app)


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
        if verify_credentials(username, password):
            login_user(User(username))
            return redirect(request.args.get('next') or url_for('index'))
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
def index():
    conn = get_connection()
    # Simple summary metrics logic (filter by is_deleted=0)
    labors_total = conn.execute("SELECT SUM(total_price) FROM labors WHERE is_deleted = 0").fetchone()[0] or 0
    expenses_total = conn.execute("SELECT SUM(amount) FROM expenses WHERE is_deleted = 0").fetchone()[0] or 0
    income_total = conn.execute("SELECT SUM(total_income) FROM production WHERE is_deleted = 0").fetchone()[0] or 0
    
    total_expenses = labors_total + expenses_total
    net_profit = income_total - total_expenses

    return render_template('index.html', 
                           income_total=income_total, 
                           total_expenses=total_expenses, 
                           net_profit=net_profit)

@app.route('/labor/add', methods=['GET', 'POST'])
def add_labor():
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
        
        conn.execute("INSERT INTO labors (date, worker_id, labor_type_id, hours, price_per_hour, total_price, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description))
        conn.commit()
        return redirect(url_for('index'))
    
    workers = conn.execute("SELECT * FROM workers WHERE is_deleted = 0 ORDER BY name").fetchall()
    labor_types = conn.execute("SELECT * FROM labor_types WHERE is_deleted = 0 ORDER BY name").fetchall()
    return render_template('labor_form.html', workers=workers, labor_types=labor_types)

@app.route('/production/add', methods=['GET', 'POST'])
def add_production():
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        kilos = float(request.form['kilos'])
        price_per_kilo = float(request.form['price_per_kilo'])
        total_income = kilos * price_per_kilo
        
        conn = get_connection()
        conn.execute("INSERT INTO production (date, kilos, price_per_kilo, total_income) VALUES (?, ?, ?, ?)",
                     (date_str, kilos, price_per_kilo, total_income))
        conn.commit()
        return redirect(url_for('index'))
    return render_template('production_form.html')

@app.route('/expense/add', methods=['GET', 'POST'])
def add_expense():
    conn = get_connection()
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        expense_type_id = request.form['expense_type_id']
        description = request.form['description']
        amount = float(request.form['amount'])
        
        conn.execute("INSERT INTO expenses (date, expense_type_id, description, amount) VALUES (?, ?, ?, ?)",
                     (date_str, expense_type_id, description, amount))
        conn.commit()
        return redirect(url_for('index'))
    
    expense_types = conn.execute("SELECT * FROM expense_types WHERE is_deleted = 0 ORDER BY name").fetchall()
    return render_template('expense_form.html', expense_types=expense_types)

@app.route('/history')
def history():
    conn = get_connection()
    labors = conn.execute("""
        SELECT l.*, w.name as worker_name, lt.name as labor_type_name 
        FROM labors l
        JOIN workers w ON l.worker_id = w.id
        JOIN labor_types lt ON l.labor_type_id = lt.id
        WHERE l.is_deleted = 0
        ORDER BY l.date DESC
    """).fetchall()
    production = conn.execute("SELECT * FROM production WHERE is_deleted = 0 ORDER BY date DESC").fetchall()
    expenses = conn.execute("""
        SELECT e.*, et.name as expense_type_name
        FROM expenses e
        JOIN expense_types et ON e.expense_type_id = et.id
        WHERE e.is_deleted = 0
        ORDER BY e.date DESC
    """).fetchall()
    return render_template('history.html', labors=labors, production=production, expenses=expenses)

# Quick Add Master Data
@app.route('/master/worker/add', methods=['POST'])
def quick_add_worker():
    name = request.form.get('name')
    if name:
        conn = get_connection()
        try:
            cur = conn.execute("INSERT INTO workers (name) VALUES (?)", (name,))
            new_id = cur.lastrowid
            conn.commit()
            return jsonify({'success': True, 'id': new_id, 'name': name})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'Nom buit'}), 400

@app.route('/master/labor_type/add', methods=['POST'])
def quick_add_labor_type():
    name = request.form.get('name')
    if name:
        conn = get_connection()
        try:
            cur = conn.execute("INSERT INTO labor_types (name) VALUES (?)", (name,))
            new_id = cur.lastrowid
            conn.commit()
            return jsonify({'success': True, 'id': new_id, 'name': name})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'Nom buit'}), 400

@app.route('/master/expense_type/add', methods=['POST'])
def quick_add_expense_type():
    name = request.form.get('name')
    if name:
        conn = get_connection()
        try:
            cur = conn.execute("INSERT INTO expense_types (name) VALUES (?)", (name,))
            new_id = cur.lastrowid
            conn.commit()
            return jsonify({'success': True, 'id': new_id, 'name': name})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'Nom buit'}), 400

@app.route('/delete/<string:category>/<int:item_id>', methods=['POST'])
def delete_item(category, item_id):
    conn = get_connection()
    if category == 'labor':
        conn.execute("UPDATE labors SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))
    elif category == 'production':
        conn.execute("UPDATE production SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))
    elif category == 'expense':
        conn.execute("UPDATE expenses SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))
    conn.commit()
    return redirect(url_for('history'))

@app.route('/labor/edit/<int:id>', methods=['GET', 'POST'])
def edit_labor(id):
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
        
        conn.execute("UPDATE labors SET date=?, worker_id=?, labor_type_id=?, hours=?, price_per_hour=?, total_price=?, description=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description, id))
        conn.commit()
        return redirect(url_for('history'))
    
    item = conn.execute("SELECT * FROM labors WHERE id=? AND is_deleted = 0", (id,)).fetchone()
    # Parse date
    y, m, d = item['date'].split('-')
    item_date = {'year': int(y), 'month': int(m), 'day': int(d)}
    
    workers = conn.execute("SELECT * FROM workers WHERE is_deleted = 0 ORDER BY name").fetchall()
    labor_types = conn.execute("SELECT * FROM labor_types WHERE is_deleted = 0 ORDER BY name").fetchall()
    return render_template('labor_form.html', item=item, item_date=item_date, workers=workers, labor_types=labor_types)

@app.route('/production/edit/<int:id>', methods=['GET', 'POST'])
def edit_production(id):
    conn = get_connection()
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        kilos = float(request.form['kilos'])
        price_per_kilo = float(request.form['price_per_kilo'])
        total_income = kilos * price_per_kilo
        
        conn.execute("UPDATE production SET date=?, kilos=?, price_per_kilo=?, total_income=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (date_str, kilos, price_per_kilo, total_income, id))
        conn.commit()
        return redirect(url_for('history'))
    
    item = conn.execute("SELECT * FROM production WHERE id=? AND is_deleted = 0", (id,)).fetchone()
    y, m, d = item['date'].split('-')
    item_date = {'year': int(y), 'month': int(m), 'day': int(d)}
    return render_template('production_form.html', item=item, item_date=item_date)

@app.route('/expense/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    conn = get_connection()
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        expense_type_id = request.form['expense_type_id']
        description = request.form['description']
        amount = float(request.form['amount'])
        
        conn.execute("UPDATE expenses SET date=?, expense_type_id=?, description=?, amount=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (date_str, expense_type_id, description, amount, id))
        conn.commit()
        return redirect(url_for('history'))
    
    item = conn.execute("SELECT * FROM expenses WHERE id=? AND is_deleted = 0", (id,)).fetchone()
    y, m, d = item['date'].split('-')
    item_date = {'year': int(y), 'month': int(m), 'day': int(d)}
    expense_types = conn.execute("SELECT * FROM expense_types WHERE is_deleted = 0 ORDER BY name").fetchall()
    return render_template('expense_form.html', item=item, item_date=item_date, expense_types=expense_types)


VEGGA_UNIT_DEFAULT = 9982
VEGGA_PAGES = ["a25/programs", "sectors", "fertilizers", "filters", "sensors"]
VEGGA_SYNC_INTERVAL_HOURS = 4


def vegga_hours_since_sync(conn, unit_id):
    row = conn.execute("""
        SELECT (julianday('now') - julianday(MAX(snapshot_at))) * 24 AS hours_since
        FROM vegga_status WHERE unit_id = ?
    """, (unit_id,)).fetchone()
    return row['hours_since'] if row and row['hours_since'] is not None else None


@app.route('/vegga')
def vegga():
    from scripts.vegga_scraper import scrape as vegga_scrape

    conn = get_connection()
    unit_id = request.args.get('unit', VEGGA_UNIT_DEFAULT, type=int)
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


@app.route('/reports')
def reports():
    conn = get_connection()
    
    # Expenses by type
    expenses_by_type = conn.execute("""
        SELECT et.name, SUM(e.amount) as total 
        FROM expenses e 
        JOIN expense_types et ON e.expense_type_id = et.id 
        WHERE e.is_deleted = 0
        GROUP BY et.name
    """).fetchall()

    # Monthly Summary (Income and Expenses)
    monthly_data = conn.execute("""
        SELECT strftime('%Y-%m', date) as month, SUM(amount) as exp 
        FROM expenses 
        WHERE is_deleted = 0
        GROUP BY month
    """).fetchall()
    
    # We need to merge this with production and labor costs for a true monthly view
    # For now, let's keep it simple as requested
    
    return render_template('reports.html', expenses_by_type=expenses_by_type)

import csv
import io
from flask import make_response

@app.route('/export/csv/<string:category>')
def export_csv(category):
    conn = get_connection()
    si = io.StringIO()
    cw = csv.writer(si)
    
    if category == 'labors':
        data = conn.execute("SELECT * FROM labors").fetchall()
        cw.writerow(['ID', 'Data', 'WorkerID', 'TypeID', 'Hours', 'Price/H', 'Total', 'Notes'])
    elif category == 'production':
        data = conn.execute("SELECT * FROM production").fetchall()
        cw.writerow(['ID', 'Data', 'Kilos', 'Price/Kg', 'Total'])
    elif category == 'expenses':
        data = conn.execute("SELECT * FROM expenses").fetchall()
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
    # Seed Labor Types if empty
    if not conn.execute("SELECT 1 FROM labor_types LIMIT 1").fetchone():
        conn.executemany("INSERT INTO labor_types (name) VALUES (?)", 
                         [('Poda',), ('Sulfatar',), ('Recol·lecció',), ('Reg',), ('Altres',)])
    # Seed Expense Types if empty
    if not conn.execute("SELECT 1 FROM expense_types LIMIT 1").fetchone():
        conn.executemany("INSERT INTO expense_types (name) VALUES (?)", 
                         [('Productes',), ('Aigua',), ('Averies',), ('Gasoil',), ('Altres',)])
    conn.commit()

if __name__ == '__main__':
    init_db()
    seed_data()
    app.run(debug=os.getenv('FLASK_DEBUG', '0') == '1', host='0.0.0.0', port=5000)
