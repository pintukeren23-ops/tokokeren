import sqlite3
import asyncio
import requests as req_sync
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

import os
TOKEN = os.environ.get("TOKEN", "ISI_TOKEN_DISINI")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CUTIEZY_API_KEY = os.environ.get("CUTIEZY_API_KEY", "")
CUTIEZY_BASE_URL = "https://cutiezy.id/zy-pay/api/v1"
CHANNEL_TESTIMONI = "RanggaShoping"
ADMIN_USERNAME = "Galtzyyo"
QRIS_FILE = "qris.png"

PAKET = {
    "1": {"nama": "WA Badak Garansi 7 Hari", "deskripsi": "Max Spam 500 Nomor/Hari", "harga": 150000, "garansi": "7 Hari"},
    "2": {"nama": "WA Badak Verif Garansi 3 Bulan", "deskripsi": "Max Spam 1000 Nomor/Hari", "harga": 300000, "garansi": "3 Bulan"},
    "3": {"nama": "WA Badak Api Verif FBM Garansi 5 Bulan", "deskripsi": "Max Spam 1500 Nomor/Hari", "harga": 500000, "garansi": "5 Bulan"},
    "4": {"nama": "Paket Siaran Bisnis", "deskripsi": "WhatsApp Siaran Bisnis Tidak Berbayar", "harga": 180000, "garansi": "Seumur Hidup"},
}

def init_db():
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, full_name TEXT, paket TEXT, harga INTEGER, status TEXT DEFAULT "pending", waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, full_name TEXT, nomor_wa TEXT, status TEXT DEFAULT "pending", waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS waiting_state (user_id INTEGER PRIMARY KEY, order_id INTEGER, nomor_paket TEXT)''')
    conn.commit()
    conn.close()

def set_waiting_bukti(user_id, order_id, nomor_paket):
    conn = sqlite3.connect("toko.db")
    conn.execute("INSERT OR REPLACE INTO waiting_state (user_id, order_id, nomor_paket) VALUES (?,?,?)", (user_id, order_id, nomor_paket))
    conn.commit()
    conn.close()

def get_waiting_bukti(user_id):
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute("SELECT order_id, nomor_paket FROM waiting_state WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row  # (order_id, nomor_paket) atau None

def clear_waiting_bukti(user_id):
    conn = sqlite3.connect("toko.db")
    conn.execute("DELETE FROM waiting_state WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

async def create_qris_payment(amount, description, order_id):
    """Buat transaksi QRIS baru via Cutiezy API."""
    def _call():
        try:
            payload = {"amount": amount, "description": description}
            headers = {"X-API-Key": CUTIEZY_API_KEY, "Content-Type": "application/json"}
            resp = req_sync.post(CUTIEZY_BASE_URL + "/create-payment", json=payload, headers=headers, timeout=10)
            data = resp.json()
            if data.get("success"):
                return data["data"]
            print("Cutiezy error:", data)
            return None
        except Exception as e:
            print("Cutiezy create payment error:", e)
            return None
    return await asyncio.get_event_loop().run_in_executor(None, _call)

async def cek_status_payment(transaction_id):
    """Cek status pembayaran dari Cutiezy API."""
    def _call():
        try:
            headers = {"X-API-Key": CUTIEZY_API_KEY}
            resp = req_sync.get(CUTIEZY_BASE_URL + "/check-payment/" + transaction_id, headers=headers, timeout=10)
            data = resp.json()
            if data.get("success"):
                return data["data"]["status"]
            return None
        except Exception as e:
            print("Cutiezy check payment error:", e)
            return None
    return await asyncio.get_event_loop().run_in_executor(None, _call)

def simpan_transaksi_qris(user_id, order_id, transaction_id):
    """Simpan mapping order_id ke transaction_id Cutiezy untuk pengecekan status."""
    conn = sqlite3.connect("toko.db")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS qris_transactions (order_id INTEGER PRIMARY KEY, user_id INTEGER, transaction_id TEXT, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.execute(
        "INSERT OR REPLACE INTO qris_transactions (order_id, user_id, transaction_id) VALUES (?,?,?)",
        (order_id, user_id, transaction_id)
    )
    conn.commit()
    conn.close()

def get_transaksi_qris(order_id):
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    try:
        c.execute("SELECT transaction_id, user_id, status FROM qris_transactions WHERE order_id=?", (order_id,))
        return c.fetchone()
    except Exception:
        return None
    finally:
        conn.close()

def register_user(user_id, username, full_name):
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?,?,?)", (user_id, username, full_name))
    conn.commit()
    conn.close()

def simpan_order(user_id, username, full_name, paket, harga):
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute("INSERT INTO orders (user_id, username, full_name, paket, harga) VALUES (?,?,?,?,?)", (user_id, username, full_name, paket, harga))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def selesaikan_order(order_id):
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status='selesai' WHERE id=?", (order_id,))
    conn.commit()
    conn.close()

def cek_punya_order_selesai(user_id):
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='selesai'", (user_id,))
    result = c.fetchone()[0]
    conn.close()
    return result > 0

def simpan_otp(user_id, username, full_name, nomor_wa):
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute("INSERT INTO otp_requests (user_id, username, full_name, nomor_wa) VALUES (?,?,?,?)", (user_id, username, full_name, nomor_wa))
    otp_id = c.lastrowid
    conn.commit()
    conn.close()
    return otp_id

def selesaikan_otp(otp_id):
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute("UPDATE otp_requests SET status='selesai' WHERE id=?", (otp_id,))
    conn.commit()
    conn.close()

def get_statistik():
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_user = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders")
    total_order = c.fetchone()[0]
    c.execute("SELECT COUNT(*), COALESCE(SUM(harga),0) FROM orders WHERE status='selesai'")
    r = c.fetchone()
    order_selesai, pemasukan = r[0], r[1]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    order_pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM otp_requests")
    total_otp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM otp_requests WHERE status='pending'")
    otp_pending = c.fetchone()[0]
    conn.close()
    return total_user, total_order, order_selesai, order_pending, pemasukan, total_otp, otp_pending

def get_semua_order():
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute("SELECT id, full_name, username, paket, harga, status, waktu FROM orders ORDER BY waktu DESC LIMIT 20")
    result = c.fetchall()
    conn.close()
    return result

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username or "", user.first_name)
    teks = (
        "Selamat Datang di WA Badak Store!\n\n"
        "Halo " + user.first_name + "!\n"
        "Kami menyediakan Nomor WA Badak berkualitas tinggi.\n\n"
        "DAFTAR PRODUK:\n\n"
        "Paket 1 - WA Badak Garansi 7 Hari\n"
        "Max Spam 500 Nomor/Hari\n"
        "Rp 150.000\n\n"
        "Paket 2 - WA Badak Verif Garansi 3 Bulan\n"
        "Max Spam 1000 Nomor/Hari\n"
        "Rp 300.000\n\n"
        "Paket 3 - WA Badak Api Verif FBM Garansi 5 Bulan\n"
        "Max Spam 1500 Nomor/Hari\n"
        "Rp 500.000\n\n"
        "Paket 4 - Paket Siaran Bisnis\n"
        "WhatsApp Siaran Bisnis Tidak Berbayar\n"
        "Rp 180.000\n\n"
        "Cara Order:\n"
        "/beli1 - Beli Paket 1\n"
        "/beli2 - Beli Paket 2\n"
        "/beli3 - Beli Paket 3\n"
        "/beli4 - Beli Paket Siaran Bisnis\n"
        "/minta_otp - Request kode OTP (khusus pembeli)\n\n"
        "Testimoni: t.me/" + CHANNEL_TESTIMONI + "\n"
        "Admin: t.me/" + ADMIN_USERNAME
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Beli Paket 1 - Rp 150.000", callback_data="beli|1")],
        [InlineKeyboardButton("Beli Paket 2 - Rp 300.000", callback_data="beli|2")],
        [InlineKeyboardButton("Beli Paket 3 - Rp 500.000", callback_data="beli|3")],
        [InlineKeyboardButton("Siaran Bisnis - Rp 180.000", callback_data="beli|4")],
        [InlineKeyboardButton("Testimoni", url="https://t.me/" + CHANNEL_TESTIMONI),
         InlineKeyboardButton("Admin", url="https://t.me/" + ADMIN_USERNAME)],
    ])
    try:
        with open("poster.png", "rb") as foto:
            await update.message.reply_photo(
                photo=foto,
                caption=teks,
                reply_markup=keyboard
            )
    except Exception:
        await update.message.reply_text(teks, reply_markup=keyboard)

async def beli1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = PAKET["1"]
    teks = "Kamu memilih:\n" + p["nama"] + "\n" + p["deskripsi"] + "\nGaransi: " + p["garansi"] + "\nHarga: Rp " + str(p["harga"]) + "\n\nApakah kamu setuju membeli paket ini?"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ya, Saya Setuju", callback_data="setuju|1")], [InlineKeyboardButton("Batal", callback_data="batal")]])
    await update.message.reply_text(teks, reply_markup=keyboard)

async def beli2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = PAKET["2"]
    teks = "Kamu memilih:\n" + p["nama"] + "\n" + p["deskripsi"] + "\nGaransi: " + p["garansi"] + "\nHarga: Rp " + str(p["harga"]) + "\n\nApakah kamu setuju membeli paket ini?"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ya, Saya Setuju", callback_data="setuju|2")], [InlineKeyboardButton("Batal", callback_data="batal")]])
    await update.message.reply_text(teks, reply_markup=keyboard)

async def beli3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = PAKET["3"]
    teks = "Kamu memilih:\n" + p["nama"] + "\n" + p["deskripsi"] + "\nGaransi: " + p["garansi"] + "\nHarga: Rp " + str(p["harga"]) + "\n\nApakah kamu setuju membeli paket ini?"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ya, Saya Setuju", callback_data="setuju|3")], [InlineKeyboardButton("Batal", callback_data="batal")]])
    await update.message.reply_text(teks, reply_markup=keyboard)

async def beli4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = PAKET["4"]
    teks = "Kamu memilih:\n" + p["nama"] + "\n" + p["deskripsi"] + "\nGaransi: " + p["garansi"] + "\nHarga: Rp " + str(p["harga"]) + "\n\nApakah kamu setuju membeli paket ini?"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ya, Saya Setuju", callback_data="setuju|4")], [InlineKeyboardButton("Batal", callback_data="batal")]])
    await update.message.reply_text(teks, reply_markup=keyboard)

async def minta_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not cek_punya_order_selesai(user.id):
        await update.message.reply_text(
            "Maaf, fitur Request OTP hanya tersedia untuk pembeli yang sudah memiliki order yang dikonfirmasi.\n\n"
            "Silakan beli paket terlebih dahulu!\n"
            "Hubungi admin jika ada pertanyaan: t.me/" + ADMIN_USERNAME
        )
        return
    context.user_data["waiting_otp_nomor"] = True
    await update.message.reply_text("Request Kode OTP\n\nKirim nomor WhatsApp kamu yang ingin diambil OTP-nya.\nFormat: 628xxxxxxxxxx")

async def statistik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Fitur ini hanya untuk admin.")
        return
    total_user, total_order, order_selesai, order_pending, pemasukan, total_otp, otp_pending = get_statistik()
    teks = "STATISTIK BOT\n\nTotal User: " + str(total_user) + "\n\nORDER:\nTotal: " + str(total_order) + "\nSelesai: " + str(order_selesai) + "\nPending: " + str(order_pending) + "\n\nPemasukan: Rp " + str(pemasukan) + "\n\nOTP REQUEST:\nTotal: " + str(total_otp) + "\nPending: " + str(otp_pending)
    await update.message.reply_text(teks)

async def riwayat_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Fitur ini hanya untuk admin.")
        return
    orders = get_semua_order()
    if not orders:
        await update.message.reply_text("Belum ada order.")
        return
    teks = "RIWAYAT ORDER (20 Terakhir)\n\n"
    for o in orders:
        emoji = "✅" if o[5] == "selesai" else "⏳"
        teks += emoji + " #" + str(o[0]) + " - " + o[3] + "\nNama: " + o[1] + " (@" + str(o[2]) + ")\nHarga: Rp " + str(o[4]) + " | " + o[5] + "\n" + str(o[6]) + "\n\n"
    await update.message.reply_text(teks)

async def kirim_ke_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Fitur ini hanya untuk admin.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Format: /kirim <user_id> <pesan>\n\nContoh:\n/kirim 123456789 Ini nomor WA kamu: 628xxx")
        return
    try:
        uid = int(context.args[0])
        pesan = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=uid, text="Pesan dari Admin:\n\n" + pesan)
        await update.message.reply_text("Pesan berhasil dikirim ke user ID: " + str(uid))
    except Exception as e:
        await update.message.reply_text("Gagal kirim pesan: " + str(e))

async def foto_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    row = get_waiting_bukti(user.id)
    if row:
        order_id, nomor = row[0], row[1]
        clear_waiting_bukti(user.id)
        p = PAKET.get(nomor)
        if not p:
            await update.message.reply_text("Terjadi error, paket tidak ditemukan. Hubungi admin.")
            return
        caption = (
            "BUKTI TRANSFER MASUK!\n\n"
            "Order ID: #" + str(order_id) + "\n"
            "Nama: " + user.first_name + "\n"
            "Username: @" + str(user.username) + "\n"
            "User ID: " + str(user.id) + "\n\n"
            "Paket: " + p["nama"] + "\n"
            "Harga: Rp " + f"{p['harga']:,}".replace(",", ".") + "\n\n"
            "Kirim nomor ke buyer:\n"
            "/kirim " + str(user.id) + " [nomor WA disini]"
        )
        photo = update.message.photo[-1].file_id
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Konfirmasi Order #" + str(order_id), callback_data="selesai|" + str(order_id) + "|" + str(user.id))
            ]])
        )
        await update.message.reply_text(
            "Bukti pembayaran diterima!\n"
            "Order ID: #" + str(order_id) + "\n\n"
            "Admin akan segera memproses pesanan kamu."
        )

async def pesan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if context.user_data.get("waiting_otp_nomor"):
        nomor_wa = update.message.text.strip()
        context.user_data["waiting_otp_nomor"] = False
        otp_id = simpan_otp(user.id, user.username or "", user.first_name, nomor_wa)
        await context.bot.send_message(chat_id=ADMIN_ID, text="REQUEST OTP BARU!\n\nNama: " + user.first_name + "\nUsername: @" + str(user.username) + "\nUser ID: " + str(user.id) + "\nNomor WA: " + nomor_wa + "\nOTP ID: #" + str(otp_id) + "\n\nKirim OTP ke user:\n/kirim " + str(user.id) + " [kode OTP disini]", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OTP Sudah Dikirim #" + str(otp_id), callback_data="otp_selesai|" + str(otp_id) + "|" + str(user.id))]]))
        await update.message.reply_text("Request OTP Terkirim!\nNomor: " + nomor_wa + "\nOTP ID: #" + str(otp_id) + "\n\nAdmin akan mengirimkan kode OTP segera. Harap tunggu!")
    elif get_waiting_bukti(user.id):
        await update.message.reply_text("Kirim FOTO bukti pembayaran kamu, bukan teks.")

async def safe_edit(query, teks, keyboard=None):
    """Edit pesan teks. Kalau pesan sebelumnya foto, hapus dulu lalu kirim baru."""
    try:
        if keyboard:
            await query.edit_message_text(teks, reply_markup=keyboard)
        else:
            await query.edit_message_text(teks)
    except Exception:
        try:
            await query.delete_message()
        except Exception:
            pass
        if keyboard:
            await query.message.chat.send_message(teks, reply_markup=keyboard)
        else:
            await query.message.chat.send_message(teks)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data == "batal":
        context.user_data["waiting_bukti"] = False
        clear_waiting_bukti(user.id)
        await safe_edit(query, "Pembelian dibatalkan. Ketik /start untuk kembali.")

    elif data == "menu":
        teks = "WA Badak Store\n\nPilih paket:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Beli Paket 1 - Rp 150.000", callback_data="beli|1")],
            [InlineKeyboardButton("Beli Paket 2 - Rp 300.000", callback_data="beli|2")],
            [InlineKeyboardButton("Beli Paket 3 - Rp 500.000", callback_data="beli|3")],
            [InlineKeyboardButton("Siaran Bisnis - Rp 180.000", callback_data="beli|4")],
            [InlineKeyboardButton("Testimoni", url="https://t.me/" + CHANNEL_TESTIMONI),
             InlineKeyboardButton("Admin", url="https://t.me/" + ADMIN_USERNAME)],
        ])
        await safe_edit(query, teks, keyboard)

    elif data.startswith("beli|"):
        nomor = data.split("|")[1]
        p = PAKET[nomor]
        teks = "Kamu memilih:\n" + p["nama"] + "\n" + p["deskripsi"] + "\nGaransi: " + p["garansi"] + "\nHarga: Rp " + f"{p['harga']:,}".replace(",", ".") + "\n\nApakah kamu setuju membeli paket ini?"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ya, Saya Setuju", callback_data="setuju|" + nomor)], [InlineKeyboardButton("Batal", callback_data="batal")]])
        await safe_edit(query, teks, keyboard)

    elif data.startswith("setuju|"):
        nomor = data.split("|")[1]
        p = PAKET[nomor]
        order_id = simpan_order(user.id, user.username or "", user.first_name, p["nama"], p["harga"])
        teks = (
            "Pilih Metode Pembayaran\n\n"
            "Paket: " + p["nama"] + "\n"
            "Nominal: Rp " + f"{p['harga']:,}".replace(",", ".") + "\n"
            "Order ID: #" + str(order_id) + "\n\n"
            "Pilih metode pembayaran yang kamu inginkan:"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("QRIS", callback_data="bayar_qris|" + str(order_id) + "|" + nomor)],
            [InlineKeyboardButton("Transfer SeaBank", callback_data="bayar_seabank|" + str(order_id) + "|" + nomor)],
            [InlineKeyboardButton("Batal", callback_data="batal")]
        ])
        await safe_edit(query, teks, keyboard)

    elif data.startswith("bayar_qris|"):
        parts = data.split("|")
        order_id, nomor = int(parts[1]), parts[2]
        p = PAKET[nomor]

        await safe_edit(query, "Membuat QRIS pembayaran... mohon tunggu sebentar.")

        trx_data = await create_qris_payment(
            amount=p["harga"],
            description="Order #" + str(order_id) + " - " + p["nama"],
            order_id=order_id
        )

        if not trx_data:
            await context.bot.send_message(
                chat_id=user.id,
                text="Gagal membuat QRIS. Silakan coba lagi atau hubungi admin @" + ADMIN_USERNAME
            )
            return

        transaction_id = trx_data["transaction_id"]
        qris_image_url = trx_data["qris_image_url"]
        total_bayar = trx_data.get("total_amount", p["harga"])
        simpan_transaksi_qris(user.id, order_id, transaction_id)

        caption = (
            "PEMBAYARAN QRIS\n\n"
            "Paket: " + p["nama"] + "\n"
            "Nominal: Rp " + f"{total_bayar:,}".replace(",", ".") + "\n"
            "Order ID: #" + str(order_id) + "\n"
            "Transaction ID: " + transaction_id + "\n\n"
            "Cara bayar:\n"
            "1. Scan QR di atas\n"
            "2. Nominal sudah otomatis terisi\n"
            "3. Selesaikan pembayaran\n"
            "4. Klik tombol Cek Status di bawah\n\n"
            "QR ini berlaku selama 30 menit."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cek Status Pembayaran", callback_data="cek_qris|" + str(order_id) + "|" + str(transaction_id) + "|" + nomor)],
            [InlineKeyboardButton("Batal", callback_data="batal")]
        ])
        try:
            await query.delete_message()
        except Exception:
            pass
        img_bytes = await asyncio.get_event_loop().run_in_executor(
            None, lambda: req_sync.get(qris_image_url, timeout=10).content
        )
        await context.bot.send_photo(
            chat_id=user.id,
            photo=img_bytes,
            caption=caption,
            reply_markup=keyboard
        )

    elif data.startswith("cek_qris|"):
        parts = data.split("|")
        order_id, transaction_id, nomor = int(parts[1]), parts[2], parts[3]
        p = PAKET[nomor]
        status = await cek_status_payment(transaction_id)

        if status == "paid":
            caption = (
                "PEMBAYARAN QRIS BERHASIL!\n\n"
                "Order ID: #" + str(order_id) + "\n"
                "Transaction ID: " + transaction_id + "\n"
                "Nama: " + user.first_name + "\n"
                "Username: @" + str(user.username) + "\n"
                "User ID: " + str(user.id) + "\n\n"
                "Paket: " + p["nama"] + "\n"
                "Harga: Rp " + f"{p['harga']:,}".replace(",", ".") + "\n\n"
                "Kirim nomor ke buyer:\n"
                "/kirim " + str(user.id) + " [nomor WA disini]"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=caption,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Konfirmasi Order #" + str(order_id), callback_data="selesai|" + str(order_id) + "|" + str(user.id))
                ]])
            )
            try:
                await query.delete_message()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=user.id,
                text="Pembayaran berhasil dikonfirmasi!\nOrder ID: #" + str(order_id) + "\n\nAdmin akan segera memproses pesanan kamu."
            )
            selesaikan_order(order_id)
        elif status == "pending":
            await query.answer("Pembayaran belum diterima. Pastikan sudah scan & bayar, lalu cek lagi.", show_alert=True)
        elif status in ("expired", "cancel"):
            try:
                await query.delete_message()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=user.id,
                text="QRIS sudah expired/dibatalkan. Silakan order ulang dengan /start"
            )
        else:
            await query.answer("Gagal cek status. Coba lagi atau hubungi admin @" + ADMIN_USERNAME, show_alert=True)

    elif data.startswith("bayar_seabank|"):
        parts = data.split("|")
        order_id, nomor = int(parts[1]), parts[2]
        p = PAKET[nomor]
        teks = (
            "PEMBAYARAN TRANSFER SEABANK\n\n"
            "Paket: " + p["nama"] + "\n"
            "Nominal: Rp " + f"{p['harga']:,}".replace(",", ".") + "\n"
            "Order ID: #" + str(order_id) + "\n\n"
            "Transfer ke:\n"
            "Bank: SeaBank\n"
            "No Rekening: 901727395930\n"
            "Atas Nama: CIT***\n"
            "Nominal: Rp " + f"{p['harga']:,}".replace(",", ".") + "\n\n"
            "Cara bayar:\n"
            "1. Transfer sesuai nominal di atas\n"
            "2. Screenshot bukti transfer\n"
            "3. Klik tombol di bawah & kirim foto bukti"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Saya Sudah Transfer - Kirim Bukti", callback_data="minta_bukti|" + str(order_id) + "|" + nomor)],
            [InlineKeyboardButton("Batal", callback_data="batal")]
        ])
        await safe_edit(query, teks, keyboard)

    elif data.startswith("minta_bukti|"):
        parts = data.split("|")
        order_id = int(parts[1])
        nomor = parts[2]
        set_waiting_bukti(user.id, order_id, nomor)
        try:
            await query.delete_message()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=user.id,
            text="Silakan kirim FOTO bukti pembayaran kamu sekarang.\nOrder ID: #" + str(order_id)
        )

    elif data.startswith("selesai|"):
        if user.id != ADMIN_ID:
            await query.answer("Kamu bukan admin!", show_alert=True)
            return
        parts = data.split("|")
        order_id, uid = int(parts[1]), int(parts[2])
        selesaikan_order(order_id)
        await context.bot.send_message(chat_id=uid, text="Pembayaran Dikonfirmasi!\nOrder #" + str(order_id) + " selesai.\nNomor WA Badak akan segera dikirim admin.\nTerima kasih!")
        await safe_edit(query, "Order #" + str(order_id) + " selesai! Notifikasi terkirim ke user.")

    elif data.startswith("otp_selesai|"):
        if user.id != ADMIN_ID:
            await query.answer("Kamu bukan admin!", show_alert=True)
            return
        parts = data.split("|")
        otp_id, uid = int(parts[1]), int(parts[2])
        selesaikan_otp(otp_id)
        await context.bot.send_message(chat_id=uid, text="Kode OTP sudah dikirim!\nSilakan cek WhatsApp kamu.")
        await safe_edit(query, "OTP #" + str(otp_id) + " selesai! Notifikasi terkirim ke user.")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("beli1", beli1))
    app.add_handler(CommandHandler("beli2", beli2))
    app.add_handler(CommandHandler("beli3", beli3))
    app.add_handler(CommandHandler("beli4", beli4))
    app.add_handler(CommandHandler("minta_otp", minta_otp))
    app.add_handler(CommandHandler("statistik", statistik))
    app.add_handler(CommandHandler("riwayat", riwayat_admin))
    app.add_handler(CommandHandler("kirim", kirim_ke_user))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, foto_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pesan_handler))
    print("Bot berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    
