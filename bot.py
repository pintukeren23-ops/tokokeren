import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = "8956798122:AAFJBRkQS0Rl4mWk8pQzgszhau4VlpxzPIU"
ADMIN_ID = 8123373116
NOMOR_REKENING = "901727395930"
NAMA_REKENING = "CIT***"
BANK = "SeaBank"
CHANNEL_TESTIMONI = "RanggaShoping"
ADMIN_USERNAME = "Galtzyyo"

PAKET = {
    "1": {"nama": "WA Badak Garansi 7 Hari", "deskripsi": "Max Spam 500 Nomor/Hari", "harga": 150000, "garansi": "7 Hari"},
    "2": {"nama": "WA Badak Verif Garansi 3 Bulan", "deskripsi": "Max Spam 1000 Nomor/Hari", "harga": 300000, "garansi": "3 Bulan"},
    "3": {"nama": "WA Badak Api Verif FBM Garansi 5 Bulan", "deskripsi": "Max Spam 1500 Nomor/Hari", "harga": 500000, "garansi": "5 Bulan"},
    "4": {"nama": "Paket Siaran Bisnis", "deskripsi": "WhatsApp Siaran Bisnis Tidak Berbayar", "harga": 250000, "garansi": "Seumur Hidup"},
}

def init_db():
    conn = sqlite3.connect("toko.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, full_name TEXT, paket TEXT, harga INTEGER, status TEXT DEFAULT "pending", waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, full_name TEXT, nomor_wa TEXT, status TEXT DEFAULT "pending", waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
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
        "Rp 250.000\n\n"
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
        [InlineKeyboardButton("Siaran Bisnis - Rp 250.000", callback_data="beli|4")],
        [InlineKeyboardButton("Testimoni", url="https://t.me/" + CHANNEL_TESTIMONI),
         InlineKeyboardButton("Admin", url="https://t.me/" + ADMIN_USERNAME)],
    ])
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
    if context.user_data.get("waiting_bukti"):
        order_id = context.user_data.get("order_id_bukti")
        nomor = context.user_data.get("nomor_paket_bukti")
        context.user_data["waiting_bukti"] = False
        p = PAKET[nomor]
        caption = "BUKTI TRANSFER MASUK!\n\nOrder ID: #" + str(order_id) + "\nNama: " + user.first_name + "\nUsername: @" + str(user.username) + "\nUser ID: " + str(user.id) + "\n\nPaket: " + p["nama"] + "\nHarga: Rp " + str(p["harga"]) + "\n\nKirim nomor ke buyer:\n/kirim " + str(user.id) + " [nomor WA disini]"
        photo = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=caption, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Konfirmasi Order #" + str(order_id), callback_data="selesai|" + str(order_id) + "|" + str(user.id))]]))
        await update.message.reply_text("Bukti transfer diterima!\nOrder ID: #" + str(order_id) + "\n\nAdmin akan segera memproses pesanan kamu.")

async def pesan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if context.user_data.get("waiting_otp_nomor"):
        nomor_wa = update.message.text.strip()
        context.user_data["waiting_otp_nomor"] = False
        otp_id = simpan_otp(user.id, user.username or "", user.first_name, nomor_wa)
        await context.bot.send_message(chat_id=ADMIN_ID, text="REQUEST OTP BARU!\n\nNama: " + user.first_name + "\nUsername: @" + str(user.username) + "\nUser ID: " + str(user.id) + "\nNomor WA: " + nomor_wa + "\nOTP ID: #" + str(otp_id) + "\n\nKirim OTP ke user:\n/kirim " + str(user.id) + " [kode OTP disini]", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OTP Sudah Dikirim #" + str(otp_id), callback_data="otp_selesai|" + str(otp_id) + "|" + str(user.id))]]))
        await update.message.reply_text("Request OTP Terkirim!\nNomor: " + nomor_wa + "\nOTP ID: #" + str(otp_id) + "\n\nAdmin akan mengirimkan kode OTP segera. Harap tunggu!")
    elif context.user_data.get("waiting_bukti"):
        await update.message.reply_text("Kirim FOTO bukti transfer kamu, bukan teks.")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data == "batal":
        context.user_data["waiting_bukti"] = False
        await query.edit_message_text("Pembelian dibatalkan. Ketik /start untuk kembali.")

    elif data == "menu":
        teks = "WA Badak Store\n\nPilih paket:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Beli Paket 1 - Rp 150.000", callback_data="beli|1")],
            [InlineKeyboardButton("Beli Paket 2 - Rp 300.000", callback_data="beli|2")],
            [InlineKeyboardButton("Beli Paket 3 - Rp 500.000", callback_data="beli|3")],
            [InlineKeyboardButton("Siaran Bisnis - Rp 250.000", callback_data="beli|4")],
            [InlineKeyboardButton("Testimoni", url="https://t.me/" + CHANNEL_TESTIMONI),
             InlineKeyboardButton("Admin", url="https://t.me/" + ADMIN_USERNAME)],
        ])
        await query.edit_message_text(teks, reply_markup=keyboard)

    elif data.startswith("beli|"):
        nomor = data.split("|")[1]
        p = PAKET[nomor]
        teks = "Kamu memilih:\n" + p["nama"] + "\n" + p["deskripsi"] + "\nGaransi: " + p["garansi"] + "\nHarga: Rp " + str(p["harga"]) + "\n\nApakah kamu setuju membeli paket ini?"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ya, Saya Setuju", callback_data="setuju|" + nomor)], [InlineKeyboardButton("Batal", callback_data="batal")]])
        await query.edit_message_text(teks, reply_markup=keyboard)

    elif data.startswith("setuju|"):
        nomor = data.split("|")[1]
        p = PAKET[nomor]
        order_id = simpan_order(user.id, user.username or "", user.first_name, p["nama"], p["harga"])
        teks = "Detail Pembayaran\n\n" + p["nama"] + "\nHarga: Rp " + str(p["harga"]) + "\n\nTransfer ke:\nBank: " + BANK + "\nNo Rek: " + NOMOR_REKENING + "\nAtas Nama: " + NAMA_REKENING + "\nNominal: Rp " + str(p["harga"]) + "\n\nOrder ID: #" + str(order_id) + "\n\nSetelah transfer klik tombol di bawah lalu kirim foto bukti transfer!"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Saya Sudah Transfer - Kirim Bukti", callback_data="minta_bukti|" + str(order_id) + "|" + nomor)], [InlineKeyboardButton("Batal", callback_data="batal")]])
        await query.edit_message_text(teks, reply_markup=keyboard)

    elif data.startswith("minta_bukti|"):
        parts = data.split("|")
        order_id = int(parts[1])
        nomor = parts[2]
        context.user_data["waiting_bukti"] = True
        context.user_data["order_id_bukti"] = order_id
        context.user_data["nomor_paket_bukti"] = nomor
        await query.edit_message_text("Silakan kirim FOTO bukti transfer kamu sekarang.\nOrder ID: #" + str(order_id))

    elif data.startswith("selesai|"):
        if user.id != ADMIN_ID:
            await query.answer("Kamu bukan admin!", show_alert=True)
            return
        parts = data.split("|")
        order_id, uid = int(parts[1]), int(parts[2])
        selesaikan_order(order_id)
        await context.bot.send_message(chat_id=uid, text="Pembayaran Dikonfirmasi!\nOrder #" + str(order_id) + " selesai.\nNomor WA Badak akan segera dikirim admin.\nTerima kasih!")
        await query.edit_message_text("Order #" + str(order_id) + " selesai! Notifikasi terkirim ke user.")

    elif data.startswith("otp_selesai|"):
        if user.id != ADMIN_ID:
            await query.answer("Kamu bukan admin!", show_alert=True)
            return
        parts = data.split("|")
        otp_id, uid = int(parts[1]), int(parts[2])
        selesaikan_otp(otp_id)
        await context.bot.send_message(chat_id=uid, text="Kode OTP sudah dikirim!\nSilakan cek WhatsApp kamu.")
        await query.edit_message_text("OTP #" + str(otp_id) + " selesai! Notifikasi terkirim ke user.")

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
    
