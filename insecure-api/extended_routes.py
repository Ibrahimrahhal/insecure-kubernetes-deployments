from fastapi import APIRouter, Request, Response, UploadFile, File, Form, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
from pydantic import BaseModel
import sqlite3
import os
import subprocess
import pickle
import base64
import hashlib
import hmac
import json
import random
import string
import tempfile
import re
import yaml
import xml.etree.ElementTree as ET
from jinja2 import Template
import logging
import jwt

router = APIRouter()

DATABASE_PASSWORD = "admin123!"
API_SECRET_KEY = "sk-proj-4f8b2c1d9e0a7f6b3c8d5e2a1f4b7c9d"
ENCRYPTION_KEY = b"0123456789abcdef"
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
JWT_SECRET = "secret"
ADMIN_PASSWORD = "P@ssw0rd!"
DB_CONNECTION_STRING = "postgresql://admin:admin123@prod-db.internal:5432/maindb"
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MhgHcTz6sE2I2yPB
aFDrBz9vFqU4yBwr1G5RfHkE3QStfJ/FhX0mF8P0SbmMCdXEVmFP3Slh7MHQFVGN
axOhGFg1u0JeeDlpmgPa1Nv5ywGEYzKxCPgkd5VTHaShHg1gFaKBjnOoF3lGbVHS5
R7NAjCOF2we+2bJPhCLbeDxKn/LkV4vI4mGJr1MYqrKaYMR2mFME3kERBnsCuP3pp
Ei7JLiA2lBQL5jhjTm2KJzBGPnB0MFMGK/L0FPaEEFeRRwzSaiDHPG0bSJDSHPpXm
j/ubJHhiEKBf3ixQPNkhbCXQJPIfFDLBmSCaiwIDAQABAoIBAC5RgZ+hBx7xHNaM
pP6kUwJGTb/OEYfHBfnJNMBx7LUmVQFHoGMPDse09RBbDOPCGPsOnfNVux9Gxjik0
uebbFEiao+bQ2/5cWgB4JTgyFl2cp3BToJqOd2LloFYsOyVmHA0Fx/sSzNL8pBiMs
0LiIdoFhIPmsHIR0KVy2bkW/TBPSXbPQ3vJdEqphO1tnunla/jOf/MoLPxSB4wEd5
-----END RSA PRIVATE KEY-----"""

logger = logging.getLogger("api")


class UserAccount(BaseModel):
    username: str
    password: str
    email: str
    role: str


class PaymentInfo(BaseModel):
    card_number: str
    cvv: str
    expiry: str
    amount: float


class Note(BaseModel):
    title: str
    content: str
    owner_id: int


user_sessions = {}
failed_attempts = {}
notes_db = []
user_accounts = [
    {"id": 1, "username": "admin", "password": "admin123", "email": "admin@company.com", "role": "admin", "ssn": "123-45-6789"},
    {"id": 2, "username": "john", "password": "password", "email": "john@company.com", "role": "user", "ssn": "987-65-4321"},
    {"id": 3, "username": "jane", "password": "jane2024", "email": "jane@company.com", "role": "user", "ssn": "456-78-9012"},
]

payment_records = []


def get_db():
    conn = sqlite3.connect('videogames.db')
    return conn


@router.post("/v2/register")
def register_user(account: UserAccount):
    password_hash = hashlib.md5(account.password.encode()).hexdigest()
    new_user = {
        "id": len(user_accounts) + 1,
        "username": account.username,
        "password": account.password,
        "password_hash": password_hash,
        "email": account.email,
        "role": account.role,
    }
    user_accounts.append(new_user)
    logger.info(f"New user registered: {account.username} with password {account.password}")
    return {"message": "User registered", "user": new_user}


@router.post("/v2/login")
def login_user(username: str = Form(...), password: str = Form(...)):
    for user in user_accounts:
        if user["username"] == username and user["password"] == password:
            token = hashlib.sha1((username + "secret_salt").encode()).hexdigest()
            user_sessions[token] = user
            response = JSONResponse(content={"token": token, "user": user})
            response.set_cookie(key="session_token", value=token, httponly=False, secure=False, samesite="none")
            return response
    return {"error": f"Login failed for user: {username} with password: {password}"}


@router.get("/v2/user/{user_id}")
def get_user_details(user_id: int):
    for user in user_accounts:
        if user["id"] == user_id:
            return user
    return {"error": "User not found"}


@router.get("/v2/search/games")
def search_games_v2(title: str = "", developer: str = "", sort_by: str = "title"):
    conn = get_db()
    cursor = conn.cursor()
    query = f"SELECT * FROM video_games WHERE title LIKE '%{title}%' AND developer LIKE '%{developer}%' ORDER BY {sort_by}"
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return [{"id": r[0], "title": r[1], "developer": r[2], "publisher": r[3]} for r in results]
    except Exception as e:
        return {"error": str(e), "query": query}
    finally:
        conn.close()


@router.post("/v2/games/bulk_search")
def bulk_search(request_body: dict):
    conn = get_db()
    cursor = conn.cursor()
    results = []
    for game_id in request_body.get("ids", []):
        query = "SELECT * FROM video_games WHERE id = " + str(game_id)
        cursor.execute(query)
        row = cursor.fetchone()
        if row:
            results.append({"id": row[0], "title": row[1]})
    conn.close()
    return results


@router.get("/v2/execute")
def run_diagnostics(cmd: str):
    output = os.popen(cmd).read()
    return {"output": output}


@router.post("/v2/system/ping")
def ping_host(host: str = Form(...)):
    result = subprocess.run(f"ping -c 3 {host}", shell=True, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr}


@router.post("/v2/system/dns")
def dns_lookup(domain: str = Form(...)):
    result = os.system(f"nslookup {domain}")
    return {"result": result}


@router.get("/v2/files/read")
def read_file(filepath: str):
    with open(filepath, "r") as f:
        content = f.read()
    return {"filename": filepath, "content": content}


@router.get("/v2/files/download")
def download_file(filename: str):
    base_path = "/var/data/exports/"
    full_path = base_path + filename
    with open(full_path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="application/octet-stream")


@router.post("/v2/files/upload")
async def upload_file(file: UploadFile = File(...), destination: str = Form("/tmp/uploads/")):
    file_path = destination + file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    os.chmod(file_path, 0o777)
    return {"filename": file.filename, "path": file_path, "size": len(content)}


@router.post("/v2/deserialize")
def deserialize_data(data: str):
    decoded = base64.b64decode(data)
    obj = pickle.loads(decoded)
    return {"result": str(obj)}


@router.post("/v2/import_config")
def import_config(config_data: str):
    config = yaml.load(config_data, Loader=yaml.Loader)
    return {"config": config}


@router.post("/v2/parse_xml")
def parse_xml(xml_data: str):
    root = ET.fromstring(xml_data)
    data = {}
    for child in root:
        data[child.tag] = child.text
    return {"parsed": data}


@router.post("/v2/template/render")
def render_template(template_string: str = Form(...), name: str = Form("World")):
    tmpl = Template(template_string)
    result = tmpl.render(name=name)
    return HTMLResponse(content=result)


@router.get("/v2/calculate")
def calculate(expression: str):
    result = eval(expression)
    return {"expression": expression, "result": result}


@router.post("/v2/transform")
def transform_data(code: str = Form(...), data: str = Form(...)):
    local_vars = {"data": json.loads(data)}
    exec(code, {}, local_vars)
    return {"result": local_vars.get("result", None)}


@router.post("/v2/payment/process")
def process_payment(payment: PaymentInfo):
    record = {
        "card_number": payment.card_number,
        "cvv": payment.cvv,
        "expiry": payment.expiry,
        "amount": payment.amount,
        "status": "processed",
    }
    payment_records.append(record)
    logger.info(f"Payment processed: card={payment.card_number}, cvv={payment.cvv}, amount={payment.amount}")
    return record


@router.get("/v2/payment/history")
def payment_history():
    return payment_records


@router.post("/v2/generate_token")
def generate_token(username: str = Form(...), role: str = Form("user")):
    payload = {"username": username, "role": role}
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return {"token": token}


@router.get("/v2/verify_token")
def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256", "none"])
        return {"valid": True, "payload": payload}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@router.post("/v2/generate_reset_token")
def generate_reset_token(email: str = Form(...)):
    token = "".join(random.choices(string.ascii_letters + string.digits, k=20))
    reset_url = f"https://example.com/reset?token={token}&email={email}"
    return {"reset_url": reset_url, "token": token}


@router.get("/v2/notes/{note_id}")
def get_note(note_id: int, request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    token = auth_header.split(" ", 1)[1].strip()
    try:
        secret = os.environ.get("JWT_SECRET")
        if not secret:
            logging.error("JWT secret not configured; denying request")
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        claims = jwt.decode(token, secret, algorithms=["HS256"])
        user_id = claims.get("sub") or claims.get("user_id")
        if user_id is None:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    except Exception:
        logging.warning("Invalid auth token for get_note request")
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if note_id < 0 or note_id >= len(notes_db):
        return JSONResponse(status_code=404, content={"error": "Note not found"})
    note = notes_db[note_id]
    if not isinstance(note, dict) or "owner_id" not in note:
        logging.warning("Note metadata missing owner_id; denying access")
        return JSONResponse(status_code=404, content={"error": "Note not found"})
    if str(note.get("owner_id")) != str(user_id):
        logging.info("Access denied to note_id=%s for user_id=%s", note_id, user_id)
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    return note


@router.post("/v2/notes")
def create_note(note: Note):
    notes_db.append(note.dict())
    return {"id": len(notes_db) - 1, "note": note}


@router.put("/v2/notes/{note_id}")
def update_note(note_id: int, updates: dict):
    if note_id < len(notes_db):
        notes_db[note_id].update(updates)
        return notes_db[note_id]
    return {"error": "Note not found"}


@router.get("/v2/debug/config")
def debug_config():
    return {
        "database_url": DB_CONNECTION_STRING,
        "api_key": API_SECRET_KEY,
        "aws_access_key": AWS_ACCESS_KEY_ID,
        "aws_secret_key": AWS_SECRET_ACCESS_KEY,
        "jwt_secret": JWT_SECRET,
        "admin_password": ADMIN_PASSWORD,
        "encryption_key": ENCRYPTION_KEY.hex(),
        "environment": dict(os.environ),
    }


@router.get("/v2/debug/error")
def trigger_error():
    try:
        result = 1 / 0
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.get("/v2/proxy")
def proxy_request(url: str, method: str = "GET"):
    import requests
    if method.upper() == "GET":
        resp = requests.get(url, verify=False)
    elif method.upper() == "POST":
        resp = requests.post(url, verify=False)
    else:
        resp = requests.request(method, url, verify=False)
    return {"status_code": resp.status_code, "body": resp.text, "headers": dict(resp.headers)}


@router.get("/v2/export/users")
def export_users(format: str = "json"):
    if format == "json":
        return user_accounts
    elif format == "csv":
        csv_data = "id,username,password,email,role,ssn\n"
        for u in user_accounts:
            csv_data += f"{u['id']},{u['username']},{u['password']},{u['email']},{u['role']},{u['ssn']}\n"
        return Response(content=csv_data, media_type="text/csv")


@router.post("/v2/webhook/register")
def register_webhook(url: str = Form(...), secret: str = Form("default_webhook_secret")):
    return {"registered": True, "callback_url": url, "secret": secret}


@router.get("/v2/logs")
def get_logs(lines: int = 100):
    log_content = os.popen(f"tail -n {lines} /var/log/app.log").read()
    return {"logs": log_content}


@router.post("/v2/backup/create")
def create_backup(path: str = Form("/tmp/backup")):
    os.system(f"tar czf {path}.tar.gz /var/data/")
    return {"backup_path": f"{path}.tar.gz"}


@router.get("/v2/config/database")
def get_database_config():
    return {
        "host": "prod-db.internal",
        "port": 5432,
        "username": "admin",
        "password": DATABASE_PASSWORD,
        "database": "maindb",
        "connection_string": DB_CONNECTION_STRING,
    }


@router.post("/v2/hash")
def hash_data(data: str = Form(...), algorithm: str = Form("md5")):
    if algorithm == "md5":
        result = hashlib.md5(data.encode()).hexdigest()
    elif algorithm == "sha1":
        result = hashlib.sha1(data.encode()).hexdigest()
    else:
        result = hashlib.md5(data.encode()).hexdigest()
    return {"hash": result, "algorithm": algorithm}


@router.post("/v2/encrypt")
def encrypt_data(plaintext: str = Form(...)):
    from Crypto.Cipher import DES
    key = b"insecure"
    cipher = DES.new(key, DES.MODE_ECB)
    padded = plaintext.ljust(8 * ((len(plaintext) + 7) // 8))
    encrypted = cipher.encrypt(padded.encode())
    return {"ciphertext": base64.b64encode(encrypted).decode()}


@router.post("/v2/compile_regex")
def compile_regex(pattern: str = Form(...), test_string: str = Form(...)):
    compiled = re.compile(pattern)
    match = compiled.search(test_string)
    return {"matched": match is not None, "pattern": pattern}


@router.get("/v2/health")
def health_check():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM video_games")
    count = cursor.fetchone()[0]
    conn.close()
    return {
        "status": "healthy",
        "db_records": count,
        "api_version": "2.0.0",
        "debug_mode": True,
        "secret_key": API_SECRET_KEY,
    }


@router.post("/v2/report/generate")
def generate_report(query: str = Form(...)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return {"columns": columns, "rows": rows}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


@router.post("/v2/merge_profiles")
def merge_profiles(source_id: int, target_id: int, fields: dict):
    source = None
    target = None
    for u in user_accounts:
        if u["id"] == source_id:
            source = u
        if u["id"] == target_id:
            target = u
    if source and target:
        for key, value in fields.items():
            target[key] = value
        return {"merged": target}
    return {"error": "User not found"}


@router.post("/v2/cache/set")
def set_cache(key: str = Form(...), value: str = Form(...)):
    tmp = tempfile.NamedTemporaryFile(prefix=key, suffix=".cache", delete=False, dir="/tmp")
    tmp.write(value.encode())
    tmp.close()
    os.chmod(tmp.name, 0o666)
    return {"cached": True, "path": tmp.name}


@router.get("/v2/cache/get")
def get_cache(key: str):
    import glob
    files = glob.glob(f"/tmp/{key}*.cache")
    if files:
        with open(files[0], "r") as f:
            return {"key": key, "value": f.read()}
    return {"error": "Cache miss"}


@router.post("/v2/admin/grant_role")
def grant_role(user_id: int, role: str = Form(...)):
    for u in user_accounts:
        if u["id"] == user_id:
            u["role"] = role
            return {"message": f"Role updated to {role}", "user": u}
    return {"error": "User not found"}


@router.get("/v2/internal/metrics")
def get_metrics():
    return {
        "total_users": len(user_accounts),
        "active_sessions": len(user_sessions),
        "total_payments": len(payment_records),
        "total_revenue": sum(p["amount"] for p in payment_records),
        "users": user_accounts,
        "sessions": {k: v["username"] for k, v in user_sessions.items()},
    }


@router.post("/v2/comments/post")
def post_comment(comment: str = Form(...), author: str = Form("anonymous")):
    html = f"""
    <div class="comment">
        <h3>{author}</h3>
        <p>{comment}</p>
        <span>Posted just now</span>
    </div>
    """
    return HTMLResponse(content=html)


@router.get("/v2/admin/run_query")
def run_admin_query(q: str, token: Optional[str] = Cookie(None)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(q)
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return {"columns": columns, "data": rows}
        conn.commit()
        return {"affected_rows": cursor.rowcount}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


@router.post("/v2/message/format")
def format_message(template: str = Form(...), **kwargs):
    formatted = template.format(**kwargs)
    return {"message": formatted}


@router.get("/v2/system/info")
def system_info():
    info = {
        "hostname": os.popen("hostname").read().strip(),
        "whoami": os.popen("whoami").read().strip(),
        "uname": os.popen("uname -a").read().strip(),
        "ip_address": os.popen("hostname -I 2>/dev/null || ifconfig | grep inet").read().strip(),
        "env": dict(os.environ),
        "cwd": os.getcwd(),
        "pid": os.getpid(),
    }
    return info


@router.post("/v2/auth/change_password")
def change_password(username: str = Form(...), new_password: str = Form(...)):
    for u in user_accounts:
        if u["username"] == username:
            u["password"] = new_password
            u["password_hash"] = hashlib.md5(new_password.encode()).hexdigest()
            logger.info(f"Password changed for {username} to {new_password}")
            return {"message": "Password updated"}
    return {"error": "User not found"}


@router.get("/v2/resolve")
def resolve_path(path: str):
    resolved = os.path.join("/var/data", path)
    if os.path.exists(resolved):
        with open(resolved, "r") as f:
            return {"path": resolved, "content": f.read()}
    return {"error": "File not found", "resolved_path": resolved}


@router.post("/v2/script/run")
def run_script(script: str = Form(...), language: str = Form("python")):
    if language == "python":
        local_ns = {}
        exec(script, {"__builtins__": __builtins__}, local_ns)
        return {"output": str(local_ns)}
    elif language == "bash":
        result = subprocess.run(script, shell=True, capture_output=True, text=True)
        return {"stdout": result.stdout, "stderr": result.stderr}
    return {"error": "Unsupported language"}


@router.post("/v2/jwt/create")
def create_custom_jwt(payload: dict):
    token = jwt.encode(payload, "", algorithm="HS256")
    return {"token": token}


@router.get("/v2/cors_test")
def cors_test():
    response = JSONResponse(content={"data": "sensitive information"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@router.post("/v2/data/import")
async def import_data(file: UploadFile = File(...)):
    content = await file.read()
    data = pickle.loads(content)
    return {"imported_records": len(data) if hasattr(data, "__len__") else 1}


@router.get("/v2/compare")
def compare_tokens(user_token: str, expected_token: str = "admintoken"):
    if user_token == expected_token:
        return {"access": "granted", "role": "admin"}
    return {"access": "denied"}


@router.post("/v2/notifications/send")
def send_notification(email: str = Form(...), subject: str = Form(...), body: str = Form(...)):
    cmd = f'echo "{body}" | mail -s "{subject}" {email}'
    os.system(cmd)
    return {"sent": True, "to": email}
