from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3

app = Flask(__name__, template_folder='.')
app.secret_key = 'secret_key_oee_factory_2026'

def get_db_connection():
    conn = sqlite3.connect('factory_oee.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect('factory_oee.db')
    cursor = conn.cursor()
    
    # 1. Tạo bảng Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # 2. Tạo bảng Machines (lưu trạng thái & lý do dừng máy)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Machines (
            machine_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'RUNNING',
            stop_reason TEXT DEFAULT ''
        )
    ''')
    
    # Tự động nâng cấp bảng Machines nếu dùng file DB cũ chưa có cột stop_reason
    cursor.execute("PRAGMA table_info(Machines)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'stop_reason' not in columns:
        cursor.execute("ALTER TABLE Machines ADD COLUMN stop_reason TEXT DEFAULT ''")
    
    # 3. Tạo bảng ProductionLogs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ProductionLogs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER,
            total_count INTEGER DEFAULT 0,
            good_count INTEGER DEFAULT 0,
            defect_count INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Thêm tài khoản mặc định
    cursor.execute("INSERT OR IGNORE INTO Users (username, password, role) VALUES ('quanly', '123456', 'ADMIN')")
    cursor.execute("INSERT OR IGNORE INTO Users (username, password, role) VALUES ('nhanvien1', '123456', 'OPERATOR')")
    
    # Khởi tạo 3 máy mặc định đều ở trạng thái RUNNING (sẵn sàng làm việc)
    cursor.execute("SELECT COUNT(*) FROM Machines")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO Machines (machine_name, status, stop_reason) VALUES ('Máy Đóng Gói 01', 'RUNNING', '')")
        cursor.execute("INSERT INTO Machines (machine_name, status, stop_reason) VALUES ('Máy Cắt CNC 02', 'RUNNING', '')")
        cursor.execute("INSERT INTO Machines (machine_name, status, stop_reason) VALUES ('Máy Dập 03', 'RUNNING', '')")
    else:
        cursor.execute("UPDATE Machines SET status = 'RUNNING', stop_reason = '' WHERE stop_reason IS NULL OR stop_reason = ''")
        
    conn.commit()
    conn.close()

# Khởi tạo và đồng bộ database ngay khi chạy
init_db()

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        error = "Sai tên đăng nhập hoặc mật khẩu!"
        
    return f'''
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Đăng nhập Hệ thống OEE</title>
        <style>
            body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f1f5f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .login-box {{ background: white; padding: 32px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 100%; max-width: 360px; }}
            h2 {{ margin-top: 0; color: #1e293b; text-align: center; margin-bottom: 24px; }}
            label {{ display: block; font-size: 0.9rem; font-weight: 600; color: #334155; margin-bottom: 6px; }}
            input[type="text"], input[type="password"] {{ width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 16px; box-sizing: border-box; font-size: 1rem; }}
            button {{ width: 100%; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; }}
            button:hover {{ background: #1d4ed8; }}
            .error {{ color: #ef4444; font-size: 0.85rem; text-align: center; margin-bottom: 12px; }}
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>🏭 ĐĂNG NHẬP OEE</h2>
            {f'<div class="error">{error}</div>' if error else ''}
            <form method="post">
                <label>Tài khoản nhân viên:</label>
                <input type="text" name="username" placeholder="Nhập quanly hoặc nhanvien1" required>
                <label>Mật khẩu:</label>
                <input type="password" name="password" placeholder="Nhập mật khẩu" required>
                <button type="submit">Đăng nhập hệ thống</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/machine-status', methods=['POST'])
def update_machine_status():
    role = session.get('role')
    if role not in ['ADMIN', 'OPERATOR']:
        return jsonify({'status': 'error', 'message': 'Không có quyền truy cập'}), 403
        
    data = request.json
    machine_id = data.get('machine_id')
    new_status = data.get('status') # 'RUNNING' hoặc 'STOPPED'
    stop_reason = data.get('reason', '').strip()
    
    # Chỉ Quản lý (ADMIN) mới được phép xác nhận khởi động lại máy
    if new_status == 'RUNNING' and role != 'ADMIN':
        return jsonify({'status': 'error', 'message': 'Chỉ Quản lý (ADMIN) mới có quyền xác nhận chạy lại máy sau khi kiểm tra!'}), 403
        
    if new_status == 'STOPPED' and not stop_reason:
        return jsonify({'status': 'error', 'message': 'Vui lòng nhập lý do dừng máy!'}), 400
        
    if new_status == 'RUNNING':
        stop_reason = ''
    else:
        # Ghi nhận người báo dừng để Quản lý nắm rõ
        reporter = session.get('username', 'Nhân viên')
        stop_reason = f"{stop_reason} (Báo bởi: {reporter})"
        
    conn = get_db_connection()
    conn.execute('UPDATE Machines SET status = ?, stop_reason = ? WHERE machine_id = ?', (new_status, stop_reason, machine_id))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/update-production', methods=['POST'])
def update_production():
    if session.get('role') not in ['ADMIN', 'OPERATOR']:
        return jsonify({'status': 'error', 'message': 'Không có quyền truy cập'}), 403
        
    data = request.json
    try:
        machine_id = int(data.get('machine_id'))
        total_count = int(data.get('total_count'))
        good_count = int(data.get('good_count'))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Dữ liệu phải là số nguyên'}), 400

    if total_count <= 0 or good_count < 0 or good_count > total_count:
        return jsonify({'status': 'error', 'message': 'Số lượng không hợp lệ (Sản phẩm đạt phải nhỏ hơn hoặc bằng tổng sản lượng)'}), 400
        
    defect_count = total_count - good_count
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO ProductionLogs (machine_id, total_count, good_count, defect_count)
        VALUES (?, ?, ?, ?)
    ''', (machine_id, total_count, good_count, defect_count))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/reset-shift', methods=['POST'])
def reset_shift():
    if session.get('role') != 'ADMIN':
        return jsonify({'status': 'error', 'message': 'Chỉ Quản lý (ADMIN) mới có quyền làm mới ca!'}), 403
        
    conn = get_db_connection()
    conn.execute('DELETE FROM ProductionLogs')
    conn.execute("UPDATE Machines SET status = 'RUNNING', stop_reason = ''")
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/dashboard')
def get_dashboard_data():
    conn = get_db_connection()
    query = '''
        SELECT m.machine_id, m.machine_name, m.status, m.stop_reason,
               IFNULL(SUM(p.total_count), 0) as total_count,
               IFNULL(SUM(p.good_count), 0) as good_count,
               IFNULL(SUM(p.defect_count), 0) as defect_count
        FROM Machines m
        LEFT JOIN ProductionLogs p ON m.machine_id = p.machine_id
        GROUP BY m.machine_id
    '''
    rows = conn.execute(query).fetchall()
    conn.close()
    
    machines_data = []
    planned_time, run_time, ideal_rate = 480, 420, 2.0
    
    for row in rows:
        total = row['total_count']
        good = row['good_count']
        defect = max(0, row['defect_count'])
        status = row['status']
        stop_reason = row['stop_reason'] or ''
        
        availability = round((run_time / planned_time) * 100, 1) if status == 'RUNNING' else 0.0
        expected_max = ideal_rate * run_time
        performance = min(round((total / expected_max) * 100, 1), 100.0) if total > 0 else 0.0
        quality = min(round((good / total * 100), 1), 100.0) if total > 0 else 0.0
        oee = round((availability * performance * quality) / 10000, 1)
        
        machines_data.append({
            'machine_id': row['machine_id'],
            'machine_name': row['machine_name'],
            'status': status,
            'stop_reason': stop_reason,
            'total_produced': total,
            'total_good': good,
            'total_defect': defect,
            'Availability': availability,
            'Performance': performance,
            'Quality': quality,
            'OEE': oee
        })
        
    return jsonify(machines_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)