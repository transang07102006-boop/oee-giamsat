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
    
    # Tạo bảng Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Tạo bảng Machines
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Machines (
            machine_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_name TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    
   
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
    

    cursor.execute("INSERT OR IGNORE INTO Users (username, password, role) VALUES ('quanly', '123456', 'ADMIN')")
    cursor.execute("INSERT OR IGNORE INTO Users (username, password, role)
        
   
