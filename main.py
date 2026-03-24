from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3, bcrypt, jwt, json, os, uuid
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
from contextlib import contextmanager

app = FastAPI(title="D&D Campaign Manager")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM  = "HS256"
DB_PATH    = "data/campaign.db"

DM_USERNAME         = "dungeonmaster"
DM_EMAIL            = "dm@compendium.local"
DM_DEFAULT_PASSWORD = "critical"

# ─── Auth Helpers (before init_db so hash_password is available at seed time) ─

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, username: str,
                 role: str = "player", must_change_password: bool = False) -> str:
    payload = {
        "sub":                  user_id,
        "username":             username,
        "role":                 role,
        "must_change_password": must_change_password,
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(request: Request) -> dict:
    token = request.cookies.get("auth_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(token)

def require_player(request: Request) -> dict:
    """Raises 403 if the caller is the DM account — DMs may not mutate characters."""
    user = get_current_user(request)
    if user.get("role") == "dm":
        raise HTTPException(status_code=403, detail="Dungeon Masters cannot edit character sheets")
    return user

# ─── Database ─────────────────────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    os.makedirs("data", exist_ok=True)
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id                   TEXT PRIMARY KEY,
                username             TEXT UNIQUE NOT NULL,
                email                TEXT UNIQUE NOT NULL,
                password_hash        TEXT NOT NULL,
                role                 TEXT NOT NULL DEFAULT 'player',
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at           TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS characters (
                id                 TEXT PRIMARY KEY,
                user_id            TEXT NOT NULL,
                name               TEXT NOT NULL,
                race               TEXT,
                class              TEXT,
                subclass           TEXT,
                background         TEXT,
                alignment          TEXT,
                level              INTEGER DEFAULT 1,
                experience         INTEGER DEFAULT 0,
                hp_max             INTEGER DEFAULT 10,
                hp_current         INTEGER DEFAULT 10,
                hp_temp            INTEGER DEFAULT 0,
                armor_class        INTEGER DEFAULT 10,
                initiative         INTEGER DEFAULT 0,
                speed              INTEGER DEFAULT 30,
                str_score          INTEGER DEFAULT 10,
                dex_score          INTEGER DEFAULT 10,
                con_score          INTEGER DEFAULT 10,
                int_score          INTEGER DEFAULT 10,
                wis_score          INTEGER DEFAULT 10,
                cha_score          INTEGER DEFAULT 10,
                saving_throws      TEXT DEFAULT '{}',
                skills             TEXT DEFAULT '{}',
                proficiencies      TEXT DEFAULT '',
                languages          TEXT DEFAULT '',
                features           TEXT DEFAULT '[]',
                equipment          TEXT DEFAULT '[]',
                spells             TEXT DEFAULT '[]',
                spell_slots        TEXT DEFAULT '{}',
                spell_save_dc      INTEGER DEFAULT 0,
                spell_attack_bonus INTEGER DEFAULT 0,
                personality        TEXT DEFAULT '',
                ideals             TEXT DEFAULT '',
                bonds              TEXT DEFAULT '',
                flaws              TEXT DEFAULT '',
                backstory          TEXT DEFAULT '',
                notes              TEXT DEFAULT '',
                portrait_url       TEXT DEFAULT '',
                created_at         TEXT NOT NULL,
                updated_at         TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        # Non-destructive migration for databases created before role columns existed
        for col, defn in [
            ("role",                 "TEXT NOT NULL DEFAULT 'player'"),
            ("must_change_password", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                db.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
            except Exception:
                pass  # Column already present

        # Seed the DM account exactly once
        if not db.execute("SELECT id FROM users WHERE username=?", (DM_USERNAME,)).fetchone():
            db.execute(
                "INSERT INTO users "
                "(id, username, email, password_hash, role, must_change_password, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), DM_USERNAME, DM_EMAIL,
                 hash_password(DM_DEFAULT_PASSWORD),
                 "dm", 1, datetime.utcnow().isoformat()),
            )

init_db()

# ─── Pydantic Models ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    new_password: str
    confirm_password: str

class CharacterCreate(BaseModel):
    name: str
    race: Optional[str] = ""
    char_class: Optional[str] = ""
    background: Optional[str] = ""
    alignment: Optional[str] = ""

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    race: Optional[str] = None
    char_class: Optional[str] = None
    subclass: Optional[str] = None
    background: Optional[str] = None
    alignment: Optional[str] = None
    level: Optional[int] = None
    experience: Optional[int] = None
    hp_max: Optional[int] = None
    hp_current: Optional[int] = None
    hp_temp: Optional[int] = None
    armor_class: Optional[int] = None
    initiative: Optional[int] = None
    speed: Optional[int] = None
    str_score: Optional[int] = None
    dex_score: Optional[int] = None
    con_score: Optional[int] = None
    int_score: Optional[int] = None
    wis_score: Optional[int] = None
    cha_score: Optional[int] = None
    saving_throws: Optional[dict] = None
    skills: Optional[dict] = None
    proficiencies: Optional[str] = None
    languages: Optional[str] = None
    features: Optional[list] = None
    equipment: Optional[list] = None
    spells: Optional[list] = None
    spell_slots: Optional[dict] = None
    spell_save_dc: Optional[int] = None
    spell_attack_bonus: Optional[int] = None
    personality: Optional[str] = None
    ideals: Optional[str] = None
    bonds: Optional[str] = None
    flaws: Optional[str] = None
    backstory: Optional[str] = None
    notes: Optional[str] = None
    portrait_url: Optional[str] = None

# ─── Page Routes ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dm", response_class=HTMLResponse)
async def dm_dashboard(request: Request):
    return templates.TemplateResponse("dm_dashboard.html", {"request": request})

@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    return templates.TemplateResponse("change_password.html", {"request": request})

@app.get("/character/new", response_class=HTMLResponse)
async def new_character_page(request: Request):
    return templates.TemplateResponse("character_sheet.html",
                                      {"request": request, "mode": "new"})

@app.get("/character/{char_id}", response_class=HTMLResponse)
async def view_character_page(request: Request, char_id: str):
    return templates.TemplateResponse("character_sheet.html",
                                      {"request": request, "mode": "view", "char_id": char_id})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("auth_token")
    return response

# ─── API: Auth ────────────────────────────────────────────────────────────────

@app.post("/api/register")
async def register(body: RegisterRequest):
    if len(body.username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if body.username.lower() == DM_USERNAME.lower():
        raise HTTPException(400, "That username is reserved")
    with get_db() as db:
        if db.execute("SELECT id FROM users WHERE username=? OR email=?",
                      (body.username, body.email)).fetchone():
            raise HTTPException(400, "Username or email already taken")
        user_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO users "
            "(id, username, email, password_hash, role, must_change_password, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (user_id, body.username, body.email,
             hash_password(body.password), "player", 0, datetime.utcnow().isoformat()),
        )
    token = create_token(user_id, body.username, "player", False)
    response = JSONResponse({"message": "Account created!", "username": body.username})
    response.set_cookie("auth_token", token, httponly=True, max_age=604800, samesite="lax")
    return response

@app.post("/api/login")
async def login(body: LoginRequest):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE username=?", (body.username,)).fetchone()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    mcp = bool(user["must_change_password"])
    token = create_token(user["id"], user["username"], user["role"], mcp)
    response = JSONResponse({
        "message":              "Welcome back!",
        "username":             user["username"],
        "role":                 user["role"],
        "must_change_password": mcp,
    })
    response.set_cookie("auth_token", token, httponly=True, max_age=604800, samesite="lax")
    return response

@app.get("/api/me")
async def me(request: Request):
    user = get_current_user(request)
    return {
        "user_id":              user["sub"],
        "username":             user["username"],
        "role":                 user.get("role", "player"),
        "must_change_password": user.get("must_change_password", False),
    }

@app.post("/api/change-password")
async def change_password(body: ChangePasswordRequest, request: Request):
    user = get_current_user(request)
    if body.new_password != body.confirm_password:
        raise HTTPException(400, "Passwords do not match")
    if len(body.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    with get_db() as db:
        db.execute(
            "UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?",
            (hash_password(body.new_password), user["sub"]),
        )
    new_token = create_token(user["sub"], user["username"], user.get("role", "player"), False)
    response = JSONResponse({"message": "Password updated successfully."})
    response.set_cookie("auth_token", new_token, httponly=True, max_age=604800, samesite="lax")
    return response

# ─── API: Characters ──────────────────────────────────────────────────────────

@app.get("/api/characters")
async def list_characters(request: Request):
    user = get_current_user(request)
    with get_db() as db:
        if user.get("role") == "dm":
            rows = db.execute(
                """SELECT c.id, c.name, c.race, c.class, c.level,
                          c.hp_current, c.hp_max, c.portrait_url, c.updated_at,
                          u.username AS player_name
                   FROM characters c
                   JOIN users u ON u.id = c.user_id
                   ORDER BY u.username, c.updated_at DESC"""
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT id, name, race, class, level,
                          hp_current, hp_max, portrait_url, updated_at
                   FROM characters WHERE user_id=? ORDER BY updated_at DESC""",
                (user["sub"],),
            ).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/characters")
async def create_character(body: CharacterCreate, request: Request):
    user = require_player(request)
    char_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_db() as db:
        db.execute(
            "INSERT INTO characters "
            "(id, user_id, name, race, class, background, alignment, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (char_id, user["sub"], body.name, body.race, body.char_class,
             body.background, body.alignment, now, now),
        )
    return {"id": char_id, "message": "Character created!"}

@app.get("/api/characters/{char_id}")
async def get_character(char_id: str, request: Request):
    user = get_current_user(request)
    with get_db() as db:
        if user.get("role") == "dm":
            char = db.execute("SELECT * FROM characters WHERE id=?", (char_id,)).fetchone()
        else:
            char = db.execute("SELECT * FROM characters WHERE id=? AND user_id=?",
                              (char_id, user["sub"])).fetchone()
    if not char:
        raise HTTPException(404, "Character not found")
    c = dict(char)
    for field in ["saving_throws", "skills", "spell_slots"]:
        c[field] = json.loads(c[field]) if c[field] else {}
    for field in ["features", "equipment", "spells"]:
        c[field] = json.loads(c[field]) if c[field] else []
    return c

@app.put("/api/characters/{char_id}")
async def update_character(char_id: str, body: CharacterUpdate, request: Request):
    user = require_player(request)
    with get_db() as db:
        if not db.execute("SELECT id FROM characters WHERE id=? AND user_id=?",
                          (char_id, user["sub"])).fetchone():
            raise HTTPException(404, "Character not found")
        updates = body.dict(exclude_none=True)
        if not updates:
            return {"message": "Nothing to update"}
        for field in ["saving_throws", "skills", "spell_slots", "features", "equipment", "spells"]:
            if field in updates:
                updates[field] = json.dumps(updates[field])
        if "char_class" in updates:
            updates["class"] = updates.pop("char_class")
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k}=?" for k in updates)
        db.execute(f"UPDATE characters SET {set_clause} WHERE id=?",
                   list(updates.values()) + [char_id])
    return {"message": "Character saved!"}

@app.delete("/api/characters/{char_id}")
async def delete_character(char_id: str, request: Request):
    user = require_player(request)
    with get_db() as db:
        if not db.execute("SELECT id FROM characters WHERE id=? AND user_id=?",
                          (char_id, user["sub"])).fetchone():
            raise HTTPException(404, "Character not found")
        db.execute("DELETE FROM characters WHERE id=?", (char_id,))
    return {"message": "Character deleted"}
