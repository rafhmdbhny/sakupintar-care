from flask import session, redirect, url_for
from Services.Main_system import Daftar_user, Cek_login
from Services.Crypto_System import Ambil_dan_simpan_harga, Analisa_kripto
from Services.Ai_Service import generate_response
from flask import Flask, request, jsonify, render_template
from functools import wraps
import datetime as dt
import os
from Services.Main_system import (
    Main_system_keuangan_,
    Analisa_menyeluruh,
    Read_riwayat_transaksi,
    save_riwayat_transaksi,
    Analisis_riwayat_transaksi,
    Read_pengaturan,
    Save_pengaturan,
    Analisa_kesehatan,
    Ambil_saldo_dana_darurat,
    Alokasikan_dana_darurat,
    Setor_manual_dana_darurat,
)
from Services.Health_System import (
    Catat_konsumsi,
    Baca_riwayat_konsumsi,
    Analisa_kesehatan_menyeluruh,
)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or "saku-pintar-care-dev-secret-change-me",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(os.environ.get("FLASK_ENV", "").lower() == "production"),
)
app.secret_key = app.config["SECRET_KEY"]


def normalize_username(value):
    return (value or "").strip()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            if request.path.startswith("/api/") or request.is_json or request.method == "POST":
                return jsonify({"error": "Login diperlukan."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route('/pengaturan', methods=['GET'])
@login_required
def get_pengaturan():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    return jsonify(Read_pengaturan(username))

@app.route('/kripto')
@login_required
def halaman_kripto():
    return render_template("index_crypto.html")

@app.route('/kesehatan')
@login_required
def halaman_kesehatan():
    return render_template("kesehatan.html")

@app.route('/laporan')
@login_required
def halaman_laporan():
    return render_template("laporan.html")

@app.route('/api/kesehatan', methods=['POST'])
@login_required
def api_kesehatan():
    data = request.get_json(silent=True) or {}
    try:
        hasil = Analisa_kesehatan(
            umur=data.get('umur'),
            berat=data.get('berat'),
            tinggi=data.get('tinggi'),
            bmi=data.get('bmi'),
            kategori_bmi=data.get('kategori'),
            keluhan=data.get('keluhan'),
        )
        return jsonify(hasil.model_dump())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/catat-kesehatan', methods=['POST'])
@login_required
def catat_kesehatan():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Login diperlukan.'}), 401

    deskripsi = request.form.get('deskripsi', '').strip()
    if not deskripsi:
        return jsonify({'error': 'Deskripsi konsumsi/aktivitas wajib diisi.'}), 400

    try:
        hasil = Catat_konsumsi(username, deskripsi)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify(hasil.model_dump())

@app.route('/riwayat-kesehatan')
@login_required
def riwayat_kesehatan():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Login diperlukan.'}), 401

    df = Baca_riwayat_konsumsi(username)
    return jsonify(df.to_dict(orient='records'))

@app.route('/analisa-kesehatan-menyeluruh')
@login_required
def analisa_kesehatan_menyeluruh_route():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Login diperlukan.'}), 401

    try:
        hasil = Analisa_kesehatan_menyeluruh(username)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    if hasil is None:
        return jsonify({'error': 'Belum ada data konsumsi/aktivitas tersimpan.'}), 400

    return jsonify(hasil.model_dump())

@app.route('/api/dana-darurat')
@login_required
def api_dana_darurat():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    try:
        return jsonify(Ambil_saldo_dana_darurat(username))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dana-darurat/alokasikan', methods=['POST'])
@login_required
def api_alokasikan_dana():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    try:
        return jsonify(Alokasikan_dana_darurat(username))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dana-darurat/setor', methods=['POST'])
@login_required
def api_setor_dana():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    try:
        try:
            jumlah = float(request.form.get("jumlah", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Jumlah setor harus berupa angka."}), 400
        if not (jumlah > 0 and (jumlah == jumlah)):
            return jsonify({"error": "Jumlah setor harus lebih besar dari 0."}), 400
        hasil = Setor_manual_dana_darurat(username, jumlah)
        return jsonify(hasil)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update-harga-kripto', methods=['POST'])
@login_required
def update_harga_kripto():
    koin = request.form.get('koin', 'bitcoin')
    try:
        data = Ambil_dan_simpan_harga(koin)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok", "data": data})

@app.route('/analisa-kripto', methods=['POST'])
@login_required
def analisa_kripto():
    koin = request.form.get('koin', '').strip()

    if not koin:
        return jsonify({"error": "Parameter 'koin' wajib diisi."}), 400

    try:
        Ambil_dan_simpan_harga(koin)  
        hasil = Analisa_kripto(koin) 
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if hasil is None:
        return jsonify({"error": "Belum ada data harga tersimpan."}), 400

    return jsonify(hasil.model_dump())

@app.route('/pengaturan', methods=['POST'])
@login_required
def set_pengaturan():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    try:
        budget = int(request.form.get('budget_bulanan', 0))
        umur = int(request.form.get('umur')) if request.form.get('umur') else None
        berat = float(request.form.get('berat_badan')) if request.form.get('berat_badan') else None
        tinggi = float(request.form.get('tinggi_badan')) if request.form.get('tinggi_badan') else None
    except ValueError:
        return jsonify({"error": "Data harus berupa angka."}), 400

    Save_pengaturan(username, budget, umur, berat, tinggi)
    return jsonify({"status": "ok"})

@app.route('/')
@login_required
def index():
    return render_template("index_main.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = normalize_username(request.form.get("username"))
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template("login.html", error="Username dan password wajib diisi.")

        if Cek_login(username, password):
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Username atau password salah.")

    return render_template("login.html")

@app.route("/daftar", methods=["GET", "POST"])
def daftar():
    if request.method == "POST":
        username = normalize_username(request.form.get("username"))
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template("daftar.html", error="Username dan password wajib diisi.")

        berhasil, pesan = Daftar_user(username, password)
        if berhasil:
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return render_template("daftar.html", error=pesan)

    return render_template("daftar.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route('/tanya', methods=['POST'])
@login_required
def tanya():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    pertanyaan = request.form.get('pertanyaan', '')
    img = request.files.get('foto')

    if not pertanyaan.strip() and not (img and img.filename):
        return jsonify({"error": "Isi pertanyaan atau upload foto struk dulu."}), 400

    try:
        if pertanyaan.strip():
            hasil = Main_system_keuangan_(pertanyaan, None, username)
        else:
            hasil = Main_system_keuangan_('', img, username)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Kalau AI berhasil nangkep nama transaksi DAN harga, otomatis dicatat ke CSV.
    # Kalau harga gak ketahuan (None), gak disimpen dulu — biar insight/rekomendasi
    # AI yang minta user kasih tau harganya susulan.
    catatan_kesehatan = None

    if hasil.nama_transaksi and hasil.harga is not None:
        kartegori = hasil.kategori[0] if hasil.kategori else "Lainnya"
        save_riwayat_transaksi(
            username=username,
            now=now,
            nama=hasil.nama_transaksi,
            jumlah=hasil.jumlah,
            harga=hasil.harga,
            kartegori=kartegori,
        )

        # BARU: kalau transaksi ini makanan/minuman, catat juga ke riwayat
        # kesehatan (kalori & kategori sehat/kurang sehat/tidak sehat).
        # Jumlah/porsi ikut dikirim biar Gemini hitung total kalori sesuai
        # porsi yang beneran dikonsumsi, bukan cuma per 1 porsi.
        if hasil.kategori and "Makanan & Minuman" in hasil.kategori:
            try:
                deskripsi_konsumsi = f"{hasil.jumlah}x {hasil.nama_transaksi}"
                catatan_kesehatan = Catat_konsumsi(username, deskripsi_konsumsi)
            except Exception as e:
                catatan_kesehatan = None

    response_data = hasil.model_dump()
    if catatan_kesehatan:
        response_data["catatan_kesehatan"] = catatan_kesehatan.model_dump()

    return jsonify(response_data)


@app.route('/transaksi', methods=['POST'])
@login_required
def transaksi():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    nama = request.form.get('nama', '').strip()
    kartegori = request.form.get('kartegori', 'Lainnya')

    try:
        jumlah = int(request.form.get('jumlah', 1))
        harga = int(request.form.get('harga', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Jumlah dan harga harus berupa angka."}), 400

    if not nama:
        return jsonify({"error": "Nama transaksi wajib diisi."}), 400
    if jumlah <= 0:
        return jsonify({"error": "Jumlah transaksi harus lebih dari 0."}), 400
    if harga < 0:
        return jsonify({"error": "Harga transaksi tidak boleh negatif."}), 400

    save_riwayat_transaksi(username=username, now=now, nama=nama, jumlah=jumlah, harga=harga, kartegori=kartegori)
    return jsonify({"status": "ok"})

@app.route('/analisa-menyeluruh')
@login_required
def analisa_menyeluruh():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    try:
        hasil = Analisa_menyeluruh(username)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if hasil is None:
        return jsonify({"error": "Belum ada data pengeluaran maupun kripto tersimpan."}), 400

    return jsonify(hasil.model_dump())

@app.route('/statistik')
@login_required
def statistik():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    pengaturan = Read_pengaturan(username)
    budget = pengaturan.get("budget_bulanan", 0)
    total, rata_rata, persen = Analisis_riwayat_transaksi(username, budget)
    return jsonify({"total": total, "rata_rata": rata_rata, "persen": persen, "budget": budget})

@app.route('/riwayat')
@login_required
def riwayat():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login diperlukan."}), 401
    df = Read_riwayat_transaksi(username)
    return jsonify(df.to_dict(orient="records"))

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    payload = request.get_json(silent=True) or {}
    user_message = payload.get('message')
    if not isinstance(user_message, str) or not user_message.strip():
        return jsonify({'error': 'Pesan tidak boleh kosong'}), 400

    try:
        hasil = generate_response(user_message.strip())
        return jsonify({'reply': hasil})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        use_reloader=False,
    )