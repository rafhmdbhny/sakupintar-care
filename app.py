
from Services.Crypto_System import Ambil_dan_simpan_harga, Analisa_kripto
from Services.Health_System import Analisa_kesehatan
from Services.Ai_Service import generate_response
from flask import Flask, request, jsonify, render_template
import datetime as dt
import os
from Services.Main_system import (
    Main_system_keuangan_,
    Analisa_menyeluruh,
    Read_riwayat_transaksi,
    save_riwayat_transaksi,
    Analisis_riwayat_transaksi,
    Read_pengaturan,
    Save_pengaturan
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-this-key")

@app.route('/pengaturan', methods=['GET'])
def get_pengaturan():
    return jsonify(Read_pengaturan())

@app.route('/kripto')
def halaman_kripto():
    return render_template("index_crypto.html")

@app.route('/kesehatan')
def halaman_kesehatan():
    return render_template("kesehatan.html")

@app.route('/api/kesehatan', methods=['POST'])
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

@app.route('/update-harga-kripto', methods=['POST'])
def update_harga_kripto():
    koin = request.form.get('koin', 'bitcoin')
    try:
        data = Ambil_dan_simpan_harga(koin)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok", "data": data})

@app.route('/analisa-kripto', methods=['POST'])
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
def set_pengaturan():
    try:
        budget = int(request.form.get('budget_bulanan', 0))
        umur = int(request.form.get('umur')) if request.form.get('umur') else None
        berat = float(request.form.get('berat_badan')) if request.form.get('berat_badan') else None
        tinggi = float(request.form.get('tinggi_badan')) if request.form.get('tinggi_badan') else None
    except ValueError:
        return jsonify({"error": "Data harus berupa angka."}), 400

    Save_pengaturan(budget, umur, berat, tinggi)
    return jsonify({"status": "ok"})

@app.route('/')
def index():
    return render_template("index_main.html")


@app.route('/tanya', methods=['POST'])
def tanya():
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    pertanyaan = request.form.get('pertanyaan', '')
    img = request.files.get('foto')

    if not pertanyaan.strip() and not (img and img.filename):
        return jsonify({"error": "Isi pertanyaan atau upload foto struk dulu."}), 400

    try:
        if pertanyaan.strip():
            hasil = Main_system_keuangan_(pertanyaan, None)
        else:
            hasil = Main_system_keuangan_('', img)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Kalau AI berhasil nangkep nama transaksi DAN harga, otomatis dicatat ke CSV.
    # Kalau harga gak ketahuan (None), gak disimpen dulu — biar insight/rekomendasi
    # AI yang minta user kasih tau harganya susulan.
    if hasil.nama_transaksi and hasil.harga is not None:
        kartegori = hasil.kategori[0] if hasil.kategori else "Lainnya"
        save_riwayat_transaksi(
            now=now,
            nama=hasil.nama_transaksi,
            jumlah=1,
            harga=hasil.harga,
            kartegori=kartegori,
        )

    return jsonify(hasil.model_dump())


@app.route('/transaksi', methods=['POST'])
def transaksi():
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    nama = request.form.get('nama', '').strip()
    kartegori = request.form.get('kartegori', 'Lainnya')

    try:
        jumlah = int(request.form.get('jumlah', 1))
        harga = int(request.form.get('harga', 0))
    except ValueError:
        return jsonify({"error": "Jumlah dan harga harus berupa angka."}), 400

    if not nama:
        return jsonify({"error": "Nama transaksi wajib diisi."}), 400

    save_riwayat_transaksi(now=now, nama=nama, jumlah=jumlah, harga=harga, kartegori=kartegori)
    return jsonify({"status": "ok"})

@app.route('/analisa-menyeluruh')
def analisa_menyeluruh():
    try:
        hasil = Analisa_menyeluruh()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if hasil is None:
        return jsonify({"error": "Belum ada data pengeluaran maupun kripto tersimpan."}), 400

    return jsonify(hasil.model_dump())

@app.route('/statistik')
def statistik():
    pengaturan = Read_pengaturan()
    budget = pengaturan.get("budget_bulanan", 0)
    total, rata_rata, persen = Analisis_riwayat_transaksi(budget)
    return jsonify({"total": total, "rata_rata": rata_rata, "persen": persen, "budget": budget})

@app.route('/riwayat')
def riwayat():
    df = Read_riwayat_transaksi()
    return jsonify(df.to_dict(orient="records"))

@app.route('/api/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'Pesan tidak boleh kosong'}), 400

    try:
        hasil = generate_response(user_message)
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