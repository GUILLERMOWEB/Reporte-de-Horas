from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
from datetime import datetime, timedelta
import hashlib
import os
from openpyxl import Workbook
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
DB_NAME = "registro_horas.db"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", (username, hash_password(password)))
            return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (username, hash_password(password)))
        return cursor.fetchone()

def add_record(user_id, tipo):
    now = datetime.now()
    fecha = now.strftime("%Y-%m-%d")
    hora = now.strftime("%H:%M:%S")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO registros (usuario_id, fecha, hora, tipo) VALUES (?, ?, ?, ?)", (user_id, fecha, hora, tipo))

def get_user_records(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registros WHERE usuario_id = ? ORDER BY fecha, hora", (user_id,))
        return cursor.fetchall()

def calculate_total_hours(registros):
    total = timedelta()
    i = 0
    while i < len(registros) - 1:
        if registros[i][4] == 'entrada' and registros[i + 1][4] == 'salida':
            entrada = datetime.strptime(registros[i][2] + ' ' + registros[i][3], "%Y-%m-%d %H:%M:%S")
            salida = datetime.strptime(registros[i + 1][2] + ' ' + registros[i + 1][3], "%Y-%m-%d %H:%M:%S")
            total += salida - entrada
            i += 2
        else:
            i += 1
    return str(total)

def export_to_excel(registros):
    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Usuario_ID", "Fecha", "Hora", "Tipo"])
    for r in registros:
        ws.append(r)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = login_user(username, password)
    if user:
        session['user_id'] = user[0]
        session['username'] = username
        return redirect(url_for('dashboard'))
    return render_template('login.html', error="Credenciales incorrectas")

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    if register_user(username, password):
        return redirect(url_for('index'))
    return render_template('login.html', error="Usuario ya existe")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    registros = get_user_records(user_id)
    total = calculate_total_hours(registros)
    return render_template('dashboard.html', registros=registros, total=total, username=session.get('username'))

@app.route('/registrar/<tipo>')
def registrar(tipo):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    add_record(user_id, tipo)
    return redirect(url_for('dashboard'))

@app.route('/exportar')
def exportar():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    registros = get_user_records(user_id)
    output = export_to_excel(registros)
    return send_file(output, as_attachment=True, download_name="registro_horas.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    app.run(debug=True)
