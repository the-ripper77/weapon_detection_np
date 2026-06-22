import os
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alerts.db")

class DbService:
    def __init__(self):
        self.init_db()

    def init_db(self):
        """Initializes SQLite database and tables."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash_id TEXT UNIQUE,
                camera_source TEXT,
                location TEXT,
                object_detected TEXT DEFAULT 'unknown',
                alert_sent_to TEXT,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Add object_detected column if missing (migration for existing DBs)
        try:
            cursor.execute("ALTER TABLE alerts ADD COLUMN object_detected TEXT DEFAULT 'unknown'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Set default storage mode to 'cloud' if not already present
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('storage_mode', 'cloud')")
        conn.commit()
        conn.close()

    def get_storage_mode(self) -> str:
        """Retrieves the current storage mode ('cloud' or 'local')."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'storage_mode'")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "cloud"

    def set_storage_mode(self, mode: str):
        """Sets the storage mode ('cloud' or 'local')."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('storage_mode', ?)", (mode,))
        conn.commit()
        conn.close()

    def upload_to_cloudinary(self, file_path: str) -> str:
        """Uploads an image to Cloudinary using the unsigned upload preset."""
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "dpleaslyx")
        upload_preset = os.getenv("CLOUDINARY_UPLOAD_PRESET", "UnsignedUpload")
        
        url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {"upload_preset": upload_preset}
                response = requests.post(url, files=files, data=data, timeout=10)
                
            if response.status_code == 200:
                res_json = response.json()
                return res_json.get("secure_url")
            else:
                print(f"Cloudinary upload failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error uploading to Cloudinary: {e}")
            return None

    def create_alert_record(self, hash_id: str, camera_source: str, location: str, object_detected: str, alert_sent_to: str, image_url: str):
        """Creates an alert record in SQLite database and returns the record dict."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            created_at_str = datetime.utcnow().isoformat() + "Z"
            cursor.execute("""
                INSERT INTO alerts (hash_id, camera_source, location, object_detected, alert_sent_to, image_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (hash_id, camera_source, location, object_detected, alert_sent_to, image_url, created_at_str))
            db_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "$id": str(db_id),
                "hash_id": hash_id,
                "camera_source": camera_source,
                "location": location,
                "object_detected": object_detected,
                "alert_sent_to": alert_sent_to,
                "image_url": image_url,
                "$createdAt": created_at_str
            }
        except Exception as e:
            print(f"Failed to create alert record: {e}")
            return None

    def get_alerts(self):
        """Fetches all alert records sorted by created_at DESC."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, hash_id, camera_source, location, object_detected, alert_sent_to, image_url, created_at FROM alerts ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            
            alerts = []
            for row in rows:
                alerts.append({
                    "$id": str(row[0]),
                    "hash_id": row[1],
                    "camera_source": row[2],
                    "location": row[3],
                    "object_detected": row[4] or "unknown",
                    "alert_sent_to": row[5],
                    "image_url": row[6],
                    "$createdAt": row[7]
                })
            return alerts
        except Exception as e:
            print(f"Failed to fetch alerts: {e}")
            return []

    def send_email_alert(self, email: str, subject: str, content: str, local_image_path: str = None):
        """Sends an email alert using the configured SMTP settings, optionally attaching a local image inline (CID)."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.image import MIMEImage

            host = os.getenv('EMAIL_HOST')
            port = int(os.getenv('EMAIL_PORT', 587))
            user = os.getenv('EMAIL_HOST_USER')
            password = os.getenv('EMAIL_HOST_PASSWORD')
            use_tls = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')

            if not all([host, port, user, password]):
                print("Email credentials missing in .env")
                return

            # Use 'related' to allow inline images via cid
            msg = MIMEMultipart('related')
            msg['From'] = user
            msg['To'] = email
            msg['Subject'] = subject

            # Create alternative body part for HTML text
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            msg_alternative.attach(MIMEText(content, 'html'))

            # If there's a local image path provided, attach it as inline with Content-ID <threat_image>
            if local_image_path and os.path.exists(local_image_path):
                with open(local_image_path, 'rb') as f:
                    img_data = f.read()
                msg_image = MIMEImage(img_data)
                msg_image.add_header('Content-ID', '<threat_image>')
                msg_image.add_header('Content-Disposition', 'inline', filename=os.path.basename(local_image_path))
                msg.attach(msg_image)

            server = smtplib.SMTP(host, port)
            if use_tls:
                server.starttls()
            server.login(user, password)
            server.send_message(msg)
            server.quit()
            print(f"Email sent successfully to {email}")

        except Exception as e:
            print(f"Failed to send email: {e}")

db_service = DbService()
