from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'secet_key_oee_factory'

def get_db_connection():
    conn = sqlite3.connect('factory_oee.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        return "Sai tài khoản hoặc mật khẩu!"
    return '''
        <form method="post" style="max-width:300px;margin:50px auto;padding:20px;border:1px solid #ccc">
            <h2>Đăng nhập Hệ Thống OEE</h2>
            Mã/Tên nhân viên: <br><input type="text" name="username" required><br><br>
            Mật khẩu: <br><input type="password" name="password" required><br><br>
            <input type="submit" value="Đăng nhập">
        </form>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# API cho nhân viên cập nhật sản lượng thực tế
@app.route('/api/update-production', methods=['POST'])
def update_production():
    if session.get('role') not in ['ADMIN', 'OPERATOR']:
        return jsonify({'status': 'error', 'message': 'Không có quyền'}), 403
        
    data = request.json
    machine_id = data.get('machine_id')
    total_count = data.get('total_count')
    good_count = data.get('good_count')
    defect_count = total_count - good_count
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO ProductionLogs (machine_id, total_count, good_count, defect_count)
        VALUES (?, ?, ?, ?)
    ''', (machine_id, total_count, good_count, defect_count))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/dashboard')
def get_dashboard_data():
    conn = get_db_connection()
    query = '''
        SELECT m.machine_id, m.machine_name, m.status,
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
        status = row['status']
        
        availability = round((run_time / planned_time) * 100, 1) if status == 'RUNNING' else 0.0
        expected_max = ideal_rate * run_time
        performance = min(round((total / expected_max) * 100, 1), 100.0) if total > 0 else 0.0
        quality = round((good / total * 100), 1) if total > 0 else 0.0
        oee = round((availability * performance * quality) / 10000, 1)
        
        machines_data.append({
            'machine_id': row['machine_id'],
            'machine_name': row['machine_name'],
            'status': status,
            'total_produced': total,
            'total_good': good,
            'total_defect': row['defect_count'],
            'Availability': availability,
            'Performance': performance,
            'Quality': quality,
            'OEE': oee
        })
        
    return jsonify(machines_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)