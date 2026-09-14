import socket
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import json
import os
import customtkinter as ctk
import re
import random

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

client_socket = None
username = ""
user_mnemonic = ""
msg_mapping = {}
loading_old_messages = False
oldest_msg_id = float('inf')

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

def generate_random_words(count):
    """Генерирует случайные слова для mnemonic"""
    words = [
        "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "abuse", "access",
        "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act", "action",
        "actor", "acts", "actual", "acute", "adapt", "add", "added", "addict", "adding", "addition",
        "additional", "address", "adjust", "admit", "admixture", "admit", "adobe", "adopt", "adore", "adorn",
        "adult", "advance", "advances", "advantage", "advent", "adverb", "adverse", "advertise", "advice", "advise",
        "adobe", "advocate", "afar", "afraid", "after", "again", "against", "agency", "agenda", "agent",
        "ages", "agile", "aging", "agitate", "agony", "agree", "agreed", "agreement", "agrees", "ahead",
        "ahold", "aid", "aide", "aider", "aiding", "aids", "aim", "aimed", "aiming", "aims",
        "air", "aired", "airer", "airing", "airs", "airy", "aisle", "ajar", "ajax", "akin",
        "akin", "alarm", "alarmed", "alarms", "alas", "alaska", "albatross", "albeit", "albert", "album"
    ]
    
    selected = []
    for _ in range(count):
        selected.append(random.choice(words))
    
    return " ".join(selected)

def on_chat_scroll(event=None):
    """Проверяет, прокручивает ли пользователь вверх в конец истории"""
    global loading_old_messages, oldest_msg_id
    
    if loading_old_messages:
        return
    
    # Получаем позицию скролла
    try:
        # Если пользователь прокрутил вверх близко к началу
        first_line = chat_box.index("@0,0")
        if first_line and first_line.startswith("1."):
            # Близко к началу - загружаем старые сообщения
            if oldest_msg_id != float('inf'):
                load_old_messages()
    except:
        pass

def load_old_messages():
    """Запрашивает старые сообщения с сервера"""
    global loading_old_messages, oldest_msg_id, client_socket
    
    if loading_old_messages or oldest_msg_id == float('inf'):
        return
    
    loading_old_messages = True
    
    try:
        # Показываем спиннер
        chat_box.config(state=tk.NORMAL)
        chat_box.insert("1.0", "⏳ Загрузка старых сообщений...\n", "loading")
        chat_box.tag_config("loading", foreground="gray", font=("Arial", 10, "italic"))
        chat_box.config(state=tk.DISABLED)
        
        # Запрашиваем старые сообщения
        packet = {
            "type": "load_old_messages",
            "before_id": oldest_msg_id,
            "limit": 50
        }
        
        client_socket.sendall((json.dumps(packet) + "|||").encode('utf-8'))
    except Exception as e:
        print(f"[ERROR] Load old messages failed: {str(e)}")
        loading_old_messages = False

def receive_messages():
    global client_socket, loading_old_messages, oldest_msg_id
    buffer = ""
    while True:
        try:
            raw_recv = client_socket.recv(4096).decode('utf-8')
            if not raw_recv: 
                break
            buffer += raw_recv
            while "|||" in buffer:
                packet_str, buffer = buffer.split("|||", 1)
                packet_str = packet_str.strip()
                if packet_str:
                    try:
                        data = json.loads(packet_str)
                        window.after(0, process_packet, data)
                    except:
                        pass
        except:
            break

def process_packet(packet):
    global msg_mapping, oldest_msg_id, loading_old_messages
    
    chat_box.config(state=tk.NORMAL)
    
    if packet["type"] == "msg":
        display_text = f"{packet['sender']}: {packet['text']}\n"
        if packet["msg_type"] == "file":
            display_text = f"{packet['sender']} 📁 [FILE]: {packet['text']}\n"
        
        chat_box.insert(tk.END, display_text)
        line_num = int(float(chat_box.index(tk.END))) - 2
        msg_mapping[line_num] = packet["id"]
        
        # Обновляем oldest_msg_id
        if packet["id"] < oldest_msg_id:
            oldest_msg_id = packet["id"]
    
    elif packet["type"] == "old_messages":
        # Удаляем спиннер загрузки
        try:
            chat_box.delete("1.0", "2.0")
        except:
            pass
        
        messages = packet.get("messages", [])
        
        if messages:
            # Вставляем старые сообщения в начало чата
            insert_text = ""
            insert_mapping = {}
            
            for msg in messages:
                display_text = f"{msg['sender']}: {msg['text']}\n"
                if msg["msg_type"] == "file":
                    display_text = f"{msg['sender']} 📁 [FILE]: {msg['text']}\n"
                
                insert_text += display_text
                # Рассчитываем номер строки
                line_num = len(insert_text.split('\n')) - 2
                insert_mapping[line_num] = msg["id"]
                
                # Обновляем oldest_msg_id
                if msg["id"] < oldest_msg_id:
                    oldest_msg_id = msg["id"]
            
            # Вставляем все сразу в начало
            if insert_text:
                chat_box.insert("1.0", insert_text)
                msg_mapping.update(insert_mapping)
        
        loading_old_messages = False
    
    elif packet["type"] == "system":
        chat_box.insert(tk.END, f"{packet['text']}\n", "system")
        chat_box.tag_config("system", foreground="gray", font=("Arial", 10, "italic"))
    
    elif packet["type"] == "delete":
        for line, m_id in list(msg_mapping.items()):
            if m_id == packet["id"]:
                chat_box.delete(f"{line}.0", f"{line+1}.0")
                chat_box.insert(f"{line}.0", "🚫 This message was deleted\n", "deleted")
                chat_box.tag_config("deleted", foreground="red", font=("Arial", 11, "italic"))
    
    elif packet["type"] == "status":
        if packet["action"] == "online":
            status_label.configure(text="● ONLINE", text_color="#27AE60")
        else:
            status_label.configure(text="● OFFLINE", text_color="gray")
    
    chat_box.config(state=tk.DISABLED)
    chat_box.yview(tk.END)

def send_message():
    message = message_entry.get().strip()
    if not message: return
    packet = {"type": "new_msg", "msg_type": "text", "text": message}
    try:
        client_socket.sendall((json.dumps(packet) + "|||").encode('utf-8'))
        message_entry.delete(0, tk.END)
    except:
        messagebox.showerror("Error", "Lost connection!")

def attach_file():
    file_path = filedialog.askopenfilename()
    if not file_path: return
    file_name = os.path.basename(file_path)
    packet = {"type": "new_msg", "msg_type": "file", "text": file_name}
    try:
        client_socket.sendall((json.dumps(packet) + "|||").encode('utf-8'))
    except:
        messagebox.showerror("Error", "File transfer failed!")

def delete_message_event(event):
    click_pos = chat_box.index(f"@{event.x},{event.y}")
    line_num = int(float(click_pos))
    if line_num in msg_mapping:
        msg_id = msg_mapping[line_num]
        if messagebox.askyesno("Delete Message", "Do you want to delete this message for everyone?"):
            packet = {"type": "delete_msg", "id": msg_id}
            client_socket.sendall((json.dumps(packet) + "|||").encode('utf-8'))

def connect_and_auth():
    global client_socket, username, user_mnemonic
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('127.0.0.1', 5555))
        auth_packet = {
            "username": username,
            "mnemonic": user_mnemonic,
            "email": getattr(window, 'user_email', ''),
            "phone": getattr(window, 'user_phone', '')
        }
        client_socket.sendall((json.dumps(auth_packet) + "|||").encode('utf-8'))
        res_raw = client_socket.recv(1024).decode('utf-8')
        res = json.loads(res_raw)
        
        if res["type"] == "auth" and res["status"] == "success":
            return True
        else:
            messagebox.showerror("Auth Failed", res.get("reason", "Unknown error"))
            return False
    except Exception as e:
        messagebox.showerror("Error", f"Connection failed: {str(e)}")
        return False

def show_about():
    messagebox.showinfo("About Kareika", "Kareika Messenger v2.1\nCreated by Maxim Revin and his team.\n\nSecure Crypto Messenger with BIP39\nFull History + Pagination (Like Telegram)")

def update_logo_color(theme_mode):
    color = "#FFFFFF" if theme_mode == "Dark" else "#000000"
    try:
        if 'login_logo_label' in globals() and login_logo_label.winfo_exists(): 
            login_logo_label.configure(text_color=color)
        if 'logo_label' in globals() and logo_label.winfo_exists(): 
            logo_label.configure(text_color=color)
    except:
        pass

def set_dark_theme():
    ctk.set_appearance_mode("Dark")
    try:
        chat_box.config(bg="#242424", fg="#FFFFFF", insertbackground="white")
    except:
        pass
    update_logo_color("Dark")

def set_light_theme():
    ctk.set_appearance_mode("Light")
    try:
        chat_box.config(bg="#F3F3F3", fg="#000000", insertbackground="black")
    except:
        pass
    update_logo_color("Light")

def show_register_screen():
    login_frame.pack_forget()
    register_frame.pack(fill=tk.BOTH, expand=True)

def show_login_screen():
    register_frame.pack_forget()
    login_frame.pack(fill=tk.BOTH, expand=True)

def generate_mnemonic_12():
    words = generate_random_words(12)
    mnemonic_text.configure(state=tk.NORMAL)
    mnemonic_text.delete(0, tk.END)
    mnemonic_text.insert(0, words)
    mnemonic_text.configure(state=tk.DISABLED)

def generate_mnemonic_24():
    words = generate_random_words(24)
    mnemonic_text.configure(state=tk.NORMAL)
    mnemonic_text.delete(0, tk.END)
    mnemonic_text.insert(0, words)
    mnemonic_text.configure(state=tk.DISABLED)

def register_action():
    global username, user_mnemonic
    
    username = reg_user_entry.get().strip()
    user_mnemonic = mnemonic_text.get().strip()
    email = reg_email_entry.get().strip()
    phone = reg_phone_entry.get().strip()
    
    if not username:
        messagebox.showerror("Error", "Username required!")
        return
    
    if not user_mnemonic:
        messagebox.showerror("Error", "Generate mnemonic first!")
        return
    
    if len(user_mnemonic.split()) not in [12, 24]:
        messagebox.showerror("Error", "Mnemonic must be 12 or 24 words!")
        return
    
    if email and not validate_email(email):
        messagebox.showerror("Error", "Invalid email format!")
        return
    
    if phone and not validate_phone(phone):
        messagebox.showerror("Error", "Invalid phone format!")
        return
    
    if not username.startswith('@'): 
        username = '@' + username
    
    window.user_email = email
    window.user_phone = phone
    
    if not connect_and_auth():
        return
    
    open_chat_window()

def login_action():
    global username, user_mnemonic
    
    username = user_entry.get().strip()
    user_mnemonic = key_entry.get().strip()
    
    if not username or not user_mnemonic:
        messagebox.showerror("Error", "Username and mnemonic required!")
        return
    
    if not username.startswith('@'): 
        username = '@' + username
    
    window.user_email = ''
    window.user_phone = ''
    
    if not connect_and_auth():
        return
    
    open_chat_window()

def open_chat_window():
    global chat_box, message_entry, send_button, logo_label, status_label
    
    login_frame.pack_forget()
    register_frame.pack_forget()
    window.geometry("750x650")
    window.title(f"Kareika - {username}")

    menu_frame = ctk.CTkFrame(window, height=40, corner_radius=0)
    menu_frame.pack(fill=tk.X, side=tk.TOP)
    ctk.CTkButton(menu_frame, text="🌙 Dark", width=60, height=25, command=set_dark_theme).pack(side=tk.LEFT, padx=5, pady=5)
    ctk.CTkButton(menu_frame, text="☀️ Light", width=60, height=25, command=set_light_theme).pack(side=tk.LEFT, padx=5, pady=5)
    ctk.CTkButton(menu_frame, text="ℹ️ About", width=80, height=25, command=show_about).pack(side=tk.RIGHT, padx=5, pady=5)

    profile_frame = ctk.CTkFrame(window, width=220, corner_radius=10, fg_color=("#EAEAEA", "#1E1E1E"))
    profile_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
    profile_frame.pack_propagate(False)

    ctk.CTkLabel(profile_frame, text="🕊️", font=("Arial", 64)).pack(pady=20)
    ctk.CTkLabel(profile_frame, text="MY PROFILE", font=("Arial", 14, "bold"), text_color="#0088cc").pack()
    ctk.CTkLabel(profile_frame, text=username, font=("Arial", 16, "bold")).pack(pady=5)
    
    if getattr(window, 'user_email', ''):
        ctk.CTkLabel(profile_frame, text=f"📧 {window.user_email}", font=("Arial", 10)).pack()
    if getattr(window, 'user_phone', ''):
        ctk.CTkLabel(profile_frame, text=f"📱 {window.user_phone}", font=("Arial", 10)).pack()
    
    status_card = ctk.CTkFrame(profile_frame, height=40, corner_radius=20, fg_color=("#DFDFDF", "#2D2D2D"))
    status_card.pack(fill=tk.X, padx=25, pady=10)
    status_label = ctk.CTkLabel(status_card, text="● ONLINE", font=("Arial", 12, "bold"), text_color="#27AE60")
    status_label.pack(pady=8)

    beta_card = ctk.CTkFrame(profile_frame, height=35, corner_radius=5, fg_color=("#DFDFDF", "#2D2D2D"))
    beta_card.pack(fill=tk.X, padx=10, pady=5)
    ctk.CTkLabel(beta_card, text="Status: Beta Tester 🛠️", font=("Arial", 11)).pack(pady=5)

    ctk.CTkButton(profile_frame, text="Log Out", width=180, fg_color="#C0392B", command=window.destroy).pack(pady=15, side=tk.BOTTOM)

    chat_main_frame = ctk.CTkFrame(window, fg_color="transparent")
    chat_main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)

    start_logo_color = "#FFFFFF" if ctk.get_appearance_mode() == "Dark" else "#000000"
    logo_label = ctk.CTkLabel(chat_main_frame, text="Kareika", font=("Arial", 28, "bold"), text_color=start_logo_color)
    logo_label.pack(pady=10)

    current_bg = "#242424" if ctk.get_appearance_mode() == "Dark" else "#F3F3F3"
    current_fg = "#FFFFFF" if ctk.get_appearance_mode() == "Dark" else "#000000"
    
    chat_box = tk.Text(chat_main_frame, bd=0, bg=current_bg, fg=current_fg, insertbackground="white", font=("Arial", 12), state=tk.DISABLED)
    chat_box.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
    chat_box.bind("<Double-Button-1>", delete_message_event)
    chat_box.bind("<MouseWheel>", on_chat_scroll)
    chat_box.bind("<Button-4>", on_chat_scroll)
    chat_box.bind("<Button-5>", on_chat_scroll)

    input_frame = ctk.CTkFrame(chat_main_frame, fg_color="transparent")
    input_frame.pack(fill=tk.X, pady=5)

    attach_button = ctk.CTkButton(input_frame, text="📎", width=40, height=40, corner_radius=10, fg_color="#2C3E50", hover_color="#34495E", command=attach_file)
    attach_button.pack(side=tk.LEFT, padx=(0, 5))

    message_entry = ctk.CTkEntry(input_frame, placeholder_text="Write a message...", height=40, corner_radius=10)
    message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    message_entry.bind("<Return>", lambda event: send_message())

    send_button = ctk.CTkButton(chat_main_frame, text="Send Message", height=40, corner_radius=10, fg_color="#0088cc", hover_color="#006699", font=("Arial", 12, "bold"), command=send_message)
    send_button.pack(padx=5, pady=5, fill=tk.X)

    threading.Thread(target=receive_messages, daemon=True).start()

window = ctk.CTk()
window.title("Kareika - Secure Messenger")
window.geometry("500x700")
window.resizable(False, False)

# LOGIN FRAME
login_frame = ctk.CTkFrame(window, fg_color="transparent")
login_frame.pack(fill=tk.BOTH, expand=True)

start_login_color = "#FFFFFF" if ctk.get_appearance_mode() == "Dark" else "#000000"
login_logo_label = ctk.CTkLabel(login_frame, text="Kareika", font=("Arial", 36, "bold"), text_color=start_login_color)
login_logo_label.pack(pady=25)

ctk.CTkLabel(login_frame, text="Sign In", font=("Arial", 18, "bold")).pack(pady=(0, 15))

ctk.CTkLabel(login_frame, text="Username:", font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=75)
user_entry = ctk.CTkEntry(login_frame, placeholder_text="@username", width=250, height=35, corner_radius=8)
user_entry.pack(pady=5)

ctk.CTkLabel(login_frame, text="Mnemonic Phrase (12 or 24 words):", font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=75, pady=(15, 0))
key_entry = ctk.CTkEntry(login_frame, placeholder_text="Enter your mnemonic...", width=250, height=50, corner_radius=8)
key_entry.pack(pady=5)
key_entry.bind("<Return>", lambda event: login_action())

login_button = ctk.CTkButton(login_frame, text="Sign In", width=250, height=40, corner_radius=8, fg_color="#0088cc", hover_color="#006699", font=("Arial", 13, "bold"), command=login_action)
login_button.pack(pady=15)

ctk.CTkLabel(login_frame, text="Don't have an account?", font=("Arial", 10)).pack(pady=(10, 0))
register_btn = ctk.CTkButton(login_frame, text="Create Account", width=250, height=35, fg_color="#27AE60", hover_color="#229954", command=show_register_screen)
register_btn.pack(pady=5)

# REGISTER FRAME
register_frame = ctk.CTkFrame(window, fg_color="transparent")

ctk.CTkLabel(register_frame, text="Kareika", font=("Arial", 36, "bold")).pack(pady=25)
ctk.CTkLabel(register_frame, text="Create Account", font=("Arial", 18, "bold")).pack(pady=(0, 15))

ctk.CTkLabel(register_frame, text="Username:", font=("Arial", 11, "bold")).pack(anchor=tk.W, padx=50)
reg_user_entry = ctk.CTkEntry(register_frame, placeholder_text="@username", width=300, height=35, corner_radius=8)
reg_user_entry.pack(pady=5)

ctk.CTkLabel(register_frame, text="Mnemonic Phrase:", font=("Arial", 11, "bold")).pack(anchor=tk.W, padx=50, pady=(10, 0))
mnemonic_text = ctk.CTkEntry(register_frame, width=300, height=60, corner_radius=8, state=tk.DISABLED)
mnemonic_text.pack(pady=5)

gen_frame = ctk.CTkFrame(register_frame, fg_color="transparent")
gen_frame.pack(pady=5)
ctk.CTkButton(gen_frame, text="Generate 12 words", width=140, height=30, command=generate_mnemonic_12).pack(side=tk.LEFT, padx=5)
ctk.CTkButton(gen_frame, text="Generate 24 words", width=140, height=30, command=generate_mnemonic_24).pack(side=tk.LEFT, padx=5)

ctk.CTkLabel(register_frame, text="Email (optional):", font=("Arial", 11, "bold")).pack(anchor=tk.W, padx=50, pady=(10, 0))
reg_email_entry = ctk.CTkEntry(register_frame, placeholder_text="your@email.com", width=300, height=35, corner_radius=8)
reg_email_entry.pack(pady=5)

ctk.CTkLabel(register_frame, text="Phone (optional):", font=("Arial", 11, "bold")).pack(anchor=tk.W, padx=50)
reg_phone_entry = ctk.CTkEntry(register_frame, placeholder_text="+1234567890", width=300, height=35, corner_radius=8)
reg_phone_entry.pack(pady=5)

reg_btn = ctk.CTkButton(register_frame, text="Create Account", width=300, height=40, fg_color="#27AE60", hover_color="#229954", command=register_action)
reg_btn.pack(pady=15)

back_btn = ctk.CTkButton(register_frame, text="Back to Login", width=300, height=35, fg_color="#34495E", hover_color="#2C3E50", command=show_login_screen)
back_btn.pack(pady=5)

window.mainloop()
