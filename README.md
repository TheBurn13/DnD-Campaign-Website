# 🐉 The Compendium — D&D Campaign Manager

A self-hosted D&D 5e campaign management website for your Raspberry Pi 5.  
Players can register, log in, and create/edit their full character sheets.

---

## ⚙️ Quick Setup on Raspberry Pi 5 (Ubuntu Server)

### 1. Transfer the Project

Copy the `dnd_campaign/` folder to your Pi. From your local machine:

```bash
scp -r dnd_campaign/ ubuntu@<PI_IP>:/home/ubuntu/
```

Or clone/copy however you prefer.

---

### 2. Install Python & Create Virtual Environment

```bash
cd /home/ubuntu/dnd_campaign

# Make sure Python 3.11+ is installed
sudo apt update && sudo apt install python3 python3-venv python3-pip -y

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 3. Set a Secret Key

Edit the `.env` or set it directly. Open `compendium.service` and replace:

```
Environment=SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_STRING
```

Generate a strong key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

### 4. Test Run

```bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8080
```

Open your browser at `http://<PI_IP>:8080` — you should see the landing page!

Press `Ctrl+C` to stop.

---

### 5. Run as a System Service (Auto-start on boot)

```bash
# Copy the service file
sudo cp compendium.service /etc/systemd/system/

# Edit it to set your SECRET_KEY (important!)
sudo nano /etc/systemd/system/compendium.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable compendium
sudo systemctl start compendium

# Check status
sudo systemctl status compendium

# View logs
sudo journalctl -u compendium -f
```

---

### 6. (Optional) Use Port 80 with nginx

If you want to serve on the standard port 80 instead of 8080:

```bash
sudo apt install nginx -y
```

Create `/etc/nginx/sites-available/compendium`:

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/compendium /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

### 7. Find Your Pi's IP Address

```bash
hostname -I
```

Share this IP with your players — they connect to `http://<IP>` or `http://<IP>:8080`.

---

## 📁 Project Structure

```
dnd_campaign/
├── main.py              # FastAPI app — routes, auth, API
├── requirements.txt     # Python dependencies
├── compendium.service   # systemd service file
├── data/
│   └── campaign.db      # SQLite database (auto-created)
├── static/
│   ├── css/
│   │   └── main.css     # Fantasy design system
│   └── js/
│       └── main.js      # Core JS helpers
└── templates/
    ├── base.html         # Shared layout & nav
    ├── index.html        # Landing page
    ├── login.html        # Login
    ├── register.html     # Registration
    ├── dashboard.html    # Character roster
    └── character_sheet.html  # Full D&D 5e sheet
```

---

## 🎲 Features

- **Player accounts** — register, login, secure JWT sessions
- **Full D&D 5e character sheets** with:
  - Ability scores with auto-calculated modifiers
  - Skills & saving throws with proficiency toggles
  - HP tracking with visual bar, AC, initiative, speed
  - Spell slots (per level, used/total)
  - Equipment inventory
  - Features & traits
  - Personality, ideals, bonds, flaws, backstory, notes
- **Auto-save** with Ctrl+S shortcut
- **Dark fantasy aesthetic** — parchment & stone design

---

## 🔮 Planned Features (Easy to Add Later)

- Campaign notes / DM dashboard
- Shared party view
- Dice roller
- Combat tracker
- NPC/monster bestiary
- Session log
- Image uploads for character portraits

---

## 🔐 Security Notes

- Always change `SECRET_KEY` to a long random string in production
- The app uses HTTP-only cookies for auth tokens
- Passwords are hashed with bcrypt
- Each player can only see/edit their own characters

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Make sure venv is activated: `source venv/bin/activate` |
| Can't connect from another device | Check Pi firewall: `sudo ufw allow 8080` |
| Database errors | Delete `data/campaign.db` to reset (loses all data) |
| Port 8080 already in use | Change `--port 8080` to another port |
