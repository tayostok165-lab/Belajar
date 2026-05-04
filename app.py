from flask import Flask, render_template_string, request, redirect, session, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# ➕ TAMBAHAN QR CODE
import qrcode
import io
import base64
import uuid

app = Flask(__name__)
app.secret_key = "ABSENSI_FINAL_CLEAN"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///absensi.db"
db = SQLAlchemy(app)

# ➕ TOKEN QR
qr_token = {}

# ================= DATABASE =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    nama = db.Column(db.String(100))
    kelas = db.Column(db.String(50))
    role = db.Column(db.String(20), default="siswa")

class Absensi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    kelas = db.Column(db.String(50))
    waktu = db.Column(db.String(50))

with app.app_context():
    db.create_all()

# ================= AUTH =================
@app.route("/", methods=["GET"])
def auth():
    return render_template_string("""
    <body style="margin:0;font-family:Arial;background:linear-gradient(120deg,#1d2b64,#f8cdda);display:flex;justify-content:center;align-items:center;height:100vh;">

    <div style="background:white;width:750px;display:flex;border-radius:15px;overflow:hidden;">

        <!-- LOGIN -->
        <div style="flex:1;padding:20px;">
            <h2>Login</h2>
            <form method="post" action="/login">
                <input name="username" placeholder="Username" required style="width:100%;padding:10px;margin:5px 0;"><br>
                <input name="password" type="password" placeholder="Password" required style="width:100%;padding:10px;margin:5px 0;"><br>
                <button style="width:100%;padding:10px;background:#1d2b64;color:white;">Login</button>
            </form>
        </div>

        <!-- REGISTER -->
        <div style="flex:1;padding:20px;background:#f2f2f2;">
            <h2>Register</h2>

            <form method="post" action="/register">

                <input name="username" placeholder="Username" required style="width:100%;padding:10px;margin:5px 0;"><br>
                <input name="password" placeholder="Password" required style="width:100%;padding:10px;margin:5px 0;"><br>
                <input name="nama" placeholder="Nama" required style="width:100%;padding:10px;margin:5px 0;"><br>
                <input name="kelas" placeholder="Kelas" required style="width:100%;padding:10px;margin:5px 0;"><br>

                <select name="role" id="role" onchange="cekRole()" style="width:100%;padding:10px;">
                    <option value="siswa">Siswa</option>
                    <option value="guru">Guru</option>
                </select><br><br>

                <input name="kode" id="kode" placeholder="Kode Guru (0909)"
                style="width:100%;padding:10px;display:none;"><br>

                <button style="width:100%;padding:10px;background:green;color:white;">Register</button>

            </form>
        </div>

    </div>

    <script>
    function cekRole(){
        var role = document.getElementById("role").value;
        document.getElementById("kode").style.display = (role=="guru") ? "block" : "none";
    }
    </script>

    </body>
    """)

# ================= REGISTER =================
@app.route("/register", methods=["POST"])
def register():
    if User.query.filter_by(username=request.form["username"]).first():
        return "Username sudah dipakai"

    if request.form["role"] == "guru":
        if request.form.get("kode") != "0909":
            return "Kode guru salah!"

    db.session.add(User(
        username=request.form["username"],
        password=generate_password_hash(request.form["password"]),
        nama=request.form["nama"],
        kelas=request.form["kelas"],
        role=request.form["role"]
    ))
    db.session.commit()

    return redirect("/")

# ================= LOGIN =================
@app.route("/login", methods=["POST"])
def login():
    user = User.query.filter_by(username=request.form["username"]).first()

    if user and check_password_hash(user.password, request.form["password"]):
        session["user"] = user.username
        return redirect("/dashboard")

    return "Login gagal"

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    user = User.query.filter_by(username=session["user"]).first()

    total_user = User.query.count()
    total_absen = Absensi.query.count()

    return f"""
    <body style="font-family:Arial;background:#f4f6f9;margin:0;">

    <div style="background:#111827;color:white;padding:15px;">
        <b>🏫 ABSENSI PERPUSTAKAAN SMKN 7 JAKARTA</b>
        <a href="/logout" style="float:right;color:white;">Logout</a>
    </div>

    <div style="padding:20px;">

        <div style="background:white;padding:20px;width:300px;border-radius:10px;">
            <h3>👤 Profil</h3>
            <p>Nama: {user.nama}</p>
            <p>Kelas: {user.kelas}</p>
            <p>Role: {user.role}</p>
        </div>

        <br>

        <div style="display:flex;gap:10px;">
            <div style="background:white;padding:15px;border-radius:10px;">👥 {total_user} User</div>
            <div style="background:white;padding:15px;border-radius:10px;">📌 {total_absen} Absen</div>
        </div>

        <br>

        <a href="/absen">📌 Absen</a> |
        <a href="/preview">📊 Preview</a> |
        <a href="/data">👥 Data</a> |
        <a href="/export">📥 Export</a>
        {" | <a href='/admin'>🔧 Admin</a>" if user.role=="guru" else ""}
        {" | <a href='/qr'>📷 QR Absen</a>" if user.role=="guru" else ""}

    </div>

    </body>
    """

# ================= ABSEN =================
@app.route("/absen", methods=["GET","POST"])
def absen():
    if "user" not in session:
        return redirect("/")

    user = User.query.filter_by(username=session["user"]).first()

    if request.method == "POST":
        db.session.add(Absensi(
            nama=user.nama,
            kelas=user.kelas,
            waktu=str(datetime.now())
        ))
        db.session.commit()
        return redirect("/preview")

    return f"""
    <body style="font-family:Arial;background:linear-gradient(120deg,#1d2b64,#f8cdda);display:flex;justify-content:center;align-items:center;height:100vh;">

    <div style="background:white;padding:30px;border-radius:15px;text-align:center;width:300px;">
        <h2>📌 ABSEN</h2>
        <p>{user.nama} - {user.kelas}</p>

        <form method="post">
            <button style="padding:10px;background:#1d2b64;color:white;border:none;border-radius:8px;">
                Absen
            </button>
        </form>
    </div>

    </body>
    """

# ================= QR ABSEN (TAMBAHAN BARU) =================
@app.route("/qr")
def qr():
    if "user" not in session:
        return redirect("/")

    user = User.query.filter_by(username=session["user"]).first()

    if user.role != "guru":
        return "❌ Hanya guru"

    token = str(uuid.uuid4())
    qr_token[token] = True

    link = f"http://127.0.0.1:5000/scan/{token}"

    img = qrcode.make(link)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_str = base64.b64encode(buf.getvalue()).decode()

    return f"""
    <body style="text-align:center;font-family:Arial;">
        <h2>📌 QR ABSENSI</h2>
        <img src="data:image/png;base64,{img_str}" width="250">
        <p>Scan untuk absen</p>
    </body>
    """

# ================= SCAN QR =================
@app.route("/scan/<token>")
def scan(token):
    if "user" not in session:
        return redirect("/")

    user = User.query.filter_by(username=session["user"]).first()

    if token not in qr_token:
        return "❌ QR tidak valid / sudah expired"

    qr_token.pop(token)

    db.session.add(Absensi(
        nama=user.nama,
        kelas=user.kelas,
        waktu=str(datetime.now())
    ))
    db.session.commit()

    return f"""
    <h2>✅ Absen Berhasil</h2>
    <p>{user.nama} sudah tercatat</p>
    <a href="/dashboard">Kembali</a>
    """

# ================= PREVIEW =================
@app.route("/preview")
def preview():
    q = request.args.get("q","")

    if q:
        data = Absensi.query.filter(
            (Absensi.nama.like(f"%{q}%")) |
            (Absensi.kelas.like(f"%{q}%")) |
            (Absensi.waktu.like(f"%{q}%"))
        ).all()
    else:
        data = Absensi.query.all()

    rows = ""
    for d in data:
        rows += f"<tr><td>{d.nama}</td><td>{d.kelas}</td><td>{d.waktu}</td></tr>"

    return f"""
    <body style="font-family:Arial;background:#f4f6f9;padding:20px;">

    <h2>📊 Preview Absensi</h2>

    <form>
        <input name="q" placeholder="Cari..." style="padding:10px;width:300px;">
        <button>Cari</button>
    </form>

    <br>

    <table style="width:100%;background:white;">
    <tr style="background:#1d2b64;color:white;">
        <th>Nama</th><th>Kelas</th><th>Waktu</th>
    </tr>
    {rows}
    </table>

    </body>
    """

# ================= DATA USER =================
@app.route("/data")
def data():
    q = request.args.get("q","")

    if q:
        users = User.query.filter(
            (User.nama.like(f"%{q}%")) |
            (User.kelas.like(f"%{q}%")) |
            (User.role.like(f"%{q}%"))
        ).all()
    else:
        users = User.query.all()

    rows = ""
    for u in users:
        rows += f"<tr><td>{u.nama}</td><td>{u.kelas}</td><td>{u.role}</td></tr>"

    return f"""
    <body style="font-family:Arial;background:#f4f6f9;padding:20px;">

    <h2>👥 Data User</h2>

    <form>
        <input name="q" placeholder="Cari user..." style="padding:10px;width:300px;">
        <button>Cari</button>
    </form>

    <br>

    <table style="width:100%;background:white;">
    <tr style="background:#111827;color:white;">
        <th>Nama</th><th>Kelas</th><th>Role</th>
    </tr>
    {rows}
    </table>

    </body>
    """

# ================= EXPORT =================
@app.route("/export")
def export():
    data = Absensi.query.all()
    csv = "Nama,Kelas,Waktu\n"
    for d in data:
        csv += f"{d.nama},{d.kelas},{d.waktu}\n"

    return Response(csv, mimetype="text/csv",
        headers={"Content-Disposition":"attachment;filename=absensi.csv"})

# ================= ADMIN =================
@app.route("/admin")
def admin():
    user = User.query.filter_by(username=session.get("user")).first()

    if not user or user.role != "guru":
        return "❌ Akses ditolak"

    return "<h2>🔧 ADMIN PANEL GURU AKTIF</h2>"

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN =================


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)