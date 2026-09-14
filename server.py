import socket
import sqlite3
import threading
import json
import re
import time
from datetime import datetime

clients = {}
db_lock = threading.Lock()

def init_db():
    with db_lock:
        db_connect = sqlite3.connect('kareika.db')
        cursor = db_connect.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            mnemonic TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            msg_type TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender) REFERENCES users(username)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS deleted_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msg_id INTEGER NOT NULL,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Админ пользователь
        try:
            cursor.execute("INSERT INTO users (username, mnemonic, email, phone) VALUES (?, ?, ?, ?)", 
                         ('@maxim', 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about', 'maxim@kareika.com', '+1234567890'))
        except sqlite3.IntegrityError:
            pass
        
        db_connect.commit()
        db_connect.close()
    print("[SERVER DB] Kareika initialized successfully ✓")

def validate_username(username):
    if not username.startswith('@'):
        return False
    if len(username) < 3 or len(username) > 30:
        return False
    pattern = r'^@[a-zA-Z0-9_]+$'
    return re.match(pattern, username) is not None

def validate_mnemonic(mnemonic):
    words = mnemonic.strip().split()
    if len(words) not in [12, 24]:
        return False
    pattern = r'^[a-z]+$'
    return all(re.match(pattern, word) for word in words)

def validate_email(email):
    if not email:
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    if not phone:
        return True
    pattern = r'^\+?1?\d{9,15}$'
    return re.match(pattern, phone) is not None

def broadcast(payload_dict):
    """Отправляет пакет всем клиентам"""
    payload = json.dumps(payload_dict) + "|||"
    dead_clients = []
    
    for username, conn in list(clients.items()):
        try:
            conn.sendall(payload.encode('utf-8'))
        except Exception as e:
            print(f"[ERROR] Failed to send to {username}: {str(e)}")
            dead_clients.append(username)
    
    for username in dead_clients:
        if username in clients:
            del clients[username]

def send_last_messages(connection, count=500):
    """Отправляет последние N сообщений новому клиенту"""
    with db_lock:
        db_connect = sqlite3.connect('kareika.db')
        cursor = db_connect.cursor()
        
        cursor.execute(
            "SELECT id, sender, msg_type, text FROM messages ORDER BY id DESC LIMIT ?",
            (count,)
        )
        history = cursor.fetchall()
        db_connect.close()
    
    # Отправляем в обратном порядке (старые сначала)
    for msg in reversed(history):
        msg_id, sender, msg_type, text = msg
        payload = {
            "type": "msg",
            "id": msg_id,
            "sender": sender,
            "msg_type": msg_type,
            "text": text
        }
        try:
            connection.sendall((json.dumps(payload) + "|||").encode('utf-8'))
        except:
            break
        time.sleep(0.01)

def get_old_messages(before_id, limit=50):
    """Получает старые сообщения ДО указанного ID"""
    with db_lock:
        db_connect = sqlite3.connect('kareika.db')
        cursor = db_connect.cursor()
        
        cursor.execute(
            "SELECT id, sender, msg_type, text FROM messages WHERE id < ? ORDER BY id DESC LIMIT ?",
            (before_id, limit)
        )
        history = cursor.fetchall()
        db_connect.close()
    
    return list(reversed(history))

def handle_client(connection, address):
    current_user = None
    try:
        # Получаем данные авторизации/регистрации
        raw_auth = connection.recv(4096).decode('utf-8')
        if not raw_auth:
            connection.close()
            return
        
        if "|||" in raw_auth:
            raw_auth = raw_auth.split("|||")[0]
        
        try:
            auth_data = json.loads(raw_auth)
        except json.JSONDecodeError:
            connection.sendall(json.dumps({
                "type": "auth",
                "status": "failed",
                "reason": "Invalid JSON format"
            }).encode('utf-8'))
            connection.close()
            return
        
        username = auth_data.get("username", "").strip().lower()
        mnemonic = auth_data.get("mnemonic", "").strip()
        email = auth_data.get("email", "").strip()
        phone = auth_data.get("phone", "").strip()
        
        # Валидация
        if not username or not mnemonic:
            connection.sendall(json.dumps({
                "type": "auth",
                "status": "failed",
                "reason": "Username and mnemonic required"
            }).encode('utf-8'))
            connection.close()
            return
        
        if not validate_username(username):
            connection.sendall(json.dumps({
                "type": "auth",
                "status": "failed",
                "reason": "Invalid username format (@username, 3-30 chars)"
            }).encode('utf-8'))
            connection.close()
            return
        
        if not validate_mnemonic(mnemonic):
            connection.sendall(json.dumps({
                "type": "auth",
                "status": "failed",
                "reason": "Invalid mnemonic (12 or 24 words)"
            }).encode('utf-8'))
            connection.close()
            return
        
        if not validate_email(email):
            connection.sendall(json.dumps({
                "type": "auth",
                "status": "failed",
                "reason": "Invalid email format"
            }).encode('utf-8'))
            connection.close()
            return
        
        if not validate_phone(phone):
            connection.sendall(json.dumps({
                "type": "auth",
                "status": "failed",
                "reason": "Invalid phone format"
            }).encode('utf-8'))
            connection.close()
            return
        
        # Проверяем или создаем пользователя
        with db_lock:
            db_connect = sqlite3.connect('kareika.db')
            cursor = db_connect.cursor()
            
            cursor.execute("SELECT mnemonic FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if result:
                # Пользователь существует - проверяем mnemonic
                if result[0] != mnemonic:
                    connection.sendall(json.dumps({
                        "type": "auth",
                        "status": "failed",
                        "reason": "Wrong mnemonic phrase!"
                    }).encode('utf-8'))
                    db_connect.close()
                    connection.close()
                    return
            else:
                # Новый пользователь - регистрируем
                try:
                    cursor.execute(
                        "INSERT INTO users (username, mnemonic, email, phone) VALUES (?, ?, ?, ?)",
                        (username, mnemonic, email if email else None, phone if phone else None)
                    )
                    db_connect.commit()
                except sqlite3.IntegrityError:
                    connection.sendall(json.dumps({
                        "type": "auth",
                        "status": "failed",
                        "reason": "Username already exists"
                    }).encode('utf-8'))
                    db_connect.close()
                    connection.close()
                    return
            
            db_connect.close()
        
        # Авторизация успешна
        current_user = username
        clients[current_user] = connection
        
        connection.sendall(json.dumps({
            "type": "auth",
            "status": "success"
        }).encode('utf-8'))
        time.sleep(0.05)
        
        # Отправляем последние 500 сообщений
        send_last_messages(connection, count=500)
        
        # Broadcast статус онлайн
        broadcast({
            "type": "status",
            "user": current_user,
            "action": "online"
        })
        
        broadcast({
            "type": "system",
            "text": f"📢 {current_user} joined KAREIKA!"
        })
        
        print(f"[LOGIN] {current_user} connected from {address}")
        
        # Обработка сообщений
        buffer = ""
        while True:
            try:
                raw_data = connection.recv(1024 * 1024).decode('utf-8')
                if not raw_data:
                    break
                
                buffer += raw_data
                while "|||" in buffer:
                    packet_str, buffer = buffer.split("|||", 1)
                    packet_str = packet_str.strip()
                    if not packet_str:
                        continue
                    
                    try:
                        packet = json.loads(packet_str)
                    except json.JSONDecodeError:
                        continue
                    
                    # Обработка нового сообщения
                    if packet.get("type") == "new_msg":
                        msg_type = packet.get("msg_type", "text")
                        text = packet.get("text", "").strip()
                        
                        if not text or len(text) > 5000:
                            continue
                        
                        with db_lock:
                            db_connect = sqlite3.connect('kareika.db')
                            cursor = db_connect.cursor()
                            
                            cursor.execute(
                                "INSERT INTO messages (sender, msg_type, text) VALUES (?, ?, ?)",
                                (current_user, msg_type, text)
                            )
                            msg_id = cursor.lastrowid
                            db_connect.commit()
                            db_connect.close()
                        
                        broadcast({
                            "type": "msg",
                            "id": msg_id,
                            "sender": current_user,
                            "msg_type": msg_type,
                            "text": text
                        })
                    
                    # Обработка удаления сообщения
                    elif packet.get("type") == "delete_msg":
                        msg_id = packet.get("id")
                        
                        with db_lock:
                            db_connect = sqlite3.connect('kareika.db')
                            cursor = db_connect.cursor()
                            
                            # Проверяем владельца сообщения
                            cursor.execute(
                                "SELECT sender FROM messages WHERE id = ?",
                                (msg_id,)
                            )
                            result = cursor.fetchone()
                            
                            if result and result[0] == current_user:
                                cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
                                db_connect.commit()
                                
                                broadcast({"type": "delete", "id": msg_id})
                            
                            db_connect.close()
                    
                    # Загрузка старых сообщений (pagination)
                    elif packet.get("type") == "load_old_messages":
                        before_id = packet.get("before_id")
                        limit = packet.get("limit", 50)
                        
                        if before_id:
                            old_messages = get_old_messages(before_id, limit)
                            
                            response = {
                                "type": "old_messages",
                                "messages": [
                                    {
                                        "id": msg[0],
                                        "sender": msg[1],
                                        "msg_type": msg[2],
                                        "text": msg[3]
                                    }
                                    for msg in old_messages
                                ]
                            }
                            
                            try:
                                connection.sendall((json.dumps(response) + "|||").encode('utf-8'))
                            except:
                                break
            
            except Exception as e:
                print(f"[ERROR] Processing message from {current_user}: {str(e)}")
                break
    
    except Exception as e:
        print(f"[ERROR] Client handler exception: {str(e)}")
    
    finally:
        if current_user and current_user in clients:
            del clients[current_user]
        connection.close()
        
        if current_user:
            broadcast({
                "type": "status",
                "user": current_user,
                "action": "offline"
            })
            broadcast({
                "type": "system",
                "text": f"🚪 {current_user} left KAREIKA."
            })
            print(f"[LOGOUT] {current_user} disconnected")

# Инициализация
init_db()

# Запуск сервера
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('127.0.0.1', 5555))
server_socket.listen(100)

print("╔════════════════════════════════════════╗")
print("║   KAREIKA TG-CORE SERVER v2.1 RUNNING  ║")
print("║   Address: 127.0.0.1:5555             ║")
print("║   Full History + Pagination (Like TG)  ║")
print("╚════════════════════════════════════════╝")

try:
    while True:
        try:
            connection, address = server_socket.accept()
            print(f"[CONNECTION] New client from {address}")
            threading.Thread(target=handle_client, args=(connection, address), daemon=True).start()
        except Exception as e:
            print(f"[ERROR] Accept failed: {str(e)}")
            continue
except KeyboardInterrupt:
    print("\n[SERVER] Shutting down...")
finally:
    server_socket.close()
    print("[SERVER] Closed")
