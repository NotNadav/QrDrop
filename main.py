import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import socket
import os
import qrcode
import secrets
from PIL import Image, ImageTk
from flask import Flask, send_from_directory, request, abort, render_template_string
from datetime import datetime
import json

# Initialize Flask app and file paths
flask_app = Flask(__name__)
file_dir = ""
file_name = ""
access_token = ""
UPLOAD_DIR = r"C:\Users\nadav\OneDrive\Documents\Coding\Personal\qrdrop\received"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Path for logging
logs_file = "logs.json"

# Function to get device name from IP address
def get_device_name(ip):
    try:
        device_name = socket.gethostbyaddr(ip)[0]
    except socket.herror:
        device_name = ip
    return device_name

# Log the action (upload or download)
def log_action(action, filename, ip):
    device_name = get_device_name(ip)
    log_entry = {
        "action": action,
        "filename": filename,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device_name": device_name,
        "ip": ip
    }

    # Load existing logs
    if os.path.exists(logs_file):
        with open(logs_file, 'r') as f:
            logs = json.load(f)
    else:
        logs = []

    # Add new log entry
    logs.append(log_entry)

    # Save updated logs
    with open(logs_file, 'w') as f:
        json.dump(logs, f, indent=4)

# Example of logging upload and download actions
def log_upload(ip, filename):
    log_action("File Uploaded", filename, ip)

def log_download(ip, filename):
    log_action("File Downloaded", filename, ip)

# Flask routes
@flask_app.route("/upload", methods=["GET", "POST"])
def upload_from_phone():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        ip = request.remote_addr  # Get the client's IP address
        if uploaded_file:
            save_path = os.path.join(UPLOAD_DIR, uploaded_file.filename)
            uploaded_file.save(save_path)

            # Log the file upload action
            log_upload(ip, uploaded_file.filename)
            
            return "<h2>✅ File uploaded successfully!</h2><a href='/upload'>Upload another</a>"
        return "<h2>⚠️ No file selected.</h2><a href='/upload'>Try again</a>"

    return render_template_string(""" 
    <!doctype html>
    <html>
    <head><title>Upload to PC</title></head>
    <body style="font-family:sans-serif;text-align:center;padding-top:50px">
        <h2>📤 Upload a File to Your PC</h2>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" required><br><br>
            <button type="submit" style="padding:10px 20px;font-size:16px">Upload</button>
        </form>
    </body>
    </html>
    """)

@flask_app.route("/<token>")
def download_file(token):
    if token == access_token:
        ip = request.remote_addr  # Get the client's IP address
        log_download(ip, file_name)  # Log download action
        return send_from_directory(file_dir, file_name, as_attachment=True)
    return abort(403)

# Function to run the Flask server
def run_server():
    flask_app.run(host="0.0.0.0", port=5000)

# Function to get the local IP address of the machine
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# QRDropApp Class (Tkinter UI)
class QRDropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QRDrop 2-Way")
        self.root.geometry("450x680")
        self.root.configure(bg="#f9f9f9")

        self.title_label = tk.Label(root, text="🔁 QRDrop", font=("Segoe UI", 24, "bold"), bg="#f9f9f9", fg="#333")
        self.title_label.pack(pady=(30, 10))

        self.subtitle_label = tk.Label(root, text="Send & Receive Files Over LAN", font=("Segoe UI", 12), bg="#f9f9f9", fg="#666")
        self.subtitle_label.pack(pady=(0, 30))

        self.upload_btn = tk.Button(root, text="📁 Upload PC → Phone", command=self.share_file,
                                    font=("Segoe UI", 12, "bold"), bg="#4CAF50", fg="white", padx=20, pady=10)
        self.upload_btn.pack(pady=10)

        self.send_btn = tk.Button(root, text="📤 Phone → PC", command=self.show_upload_qr,
                                  font=("Segoe UI", 12, "bold"), bg="#2196F3", fg="white", padx=20, pady=10)
        self.send_btn.pack(pady=10)

        self.qr_canvas = tk.Label(root, bg="#f9f9f9")
        self.qr_canvas.pack(pady=30)

        self.url_label = tk.Label(root, text="", font=("Segoe UI", 10), wraplength=400, justify="center", bg="#f9f9f9", fg="#444")
        self.url_label.pack(pady=10)

    def share_file(self):
        global file_dir, file_name, access_token
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        file_dir = os.path.dirname(filepath)
        file_name = os.path.basename(filepath)
        access_token = secrets.token_urlsafe(8)

        threading.Thread(target=run_server, daemon=True).start()
        ip = get_local_ip()
        url = f"http://{ip}:5000/{access_token}"
        self.show_qr(url, "Scan to download on your phone:")

    def show_upload_qr(self):
        threading.Thread(target=run_server, daemon=True).start()
        ip = get_local_ip()
        url = f"http://{ip}:5000/upload"
        self.show_qr(url, "Scan to upload a file from your phone:")

    def show_qr(self, url, text):
        qr = qrcode.make(url).resize((260, 260))  # Generate QR code and resize it
        qr_img = ImageTk.PhotoImage(qr)  # Convert to Tkinter-friendly format

        # Update the canvas with the new QR code
        self.qr_canvas.config(image=qr_img)
        self.qr_canvas.image = qr_img  # Hold a reference to the image
        self.url_label.config(text=f"{text}\n{url}")  # Update the URL label
        messagebox.showinfo("QR Generated", "Scan the QR code with your phone.")

if __name__ == "__main__":
    root = tk.Tk()
    app = QRDropApp(root)
    root.mainloop()
