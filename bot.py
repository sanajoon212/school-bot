
# ===============================
#   BALE SCHOOL BOT PRO FIXED
# ===============================

import telebot
from telebot import types, apihelper
import sqlite3
import csv
import os
import time
import requests

TOKEN = "1365696521:AeHybgB9Rl1meM4boe-PthzTiuIeCPk_gpM"

apihelper.API_URL = "https://tapi.bale.ai/bot{0}/{1}"
bot = telebot.TeleBot(TOKEN)

print("BOT RUNNING...")

# ================= DATABASE =================

conn = sqlite3.connect("school.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    name TEXT,
    classes TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    name TEXT,
    class_name TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS grades(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code TEXT,
    lesson TEXT,
    month TEXT,
    grade TEXT,
    description TEXT
)
""")

conn.commit()

# ================= SETTINGS =================

ADMIN_ID = 1511136692

user_state = {}
teacher_sessions = {}

# ================= KEYBOARDS =================

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("ورود ادمین")
    kb.add("ورود معلم")
    kb.add("ورود دانش آموز")
    return kb


def admin_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("آپلود معلمان", "مشاهده معلمان")
    kb.add("خانه")
    return kb


def teacher_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("آپلود دانش آموزان", "آپلود نمرات")
    kb.add("دانش آموزان کلاس")
    kb.add("خانه")
    return kb


def back_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("برگشت", "خانه")
    return kb

# ================= START =================

@bot.message_handler(commands=['start'])
def start(message):
    user_state.pop(message.from_user.id, None)

    bot.send_message(
        message.chat.id,
        "به سامانه مدرسه خوش آمدید",
        reply_markup=main_keyboard()
    )

# ================= TEXT =================

@bot.message_handler(content_types=['text'])
def handle(message):

    user_id = message.from_user.id
    txt = message.text.strip()

    # ============ HOME ============
    if txt == "خانه":
        user_state.pop(user_id, None)
        bot.send_message(message.chat.id, "منوی اصلی", reply_markup=main_keyboard())
        return

    # ============ BACK ============
    if txt == "برگشت":
        user_state.pop(user_id, None)

        if user_id in teacher_sessions:
            bot.send_message(message.chat.id, "پنل معلم", reply_markup=teacher_keyboard())
        else:
            bot.send_message(message.chat.id, "منوی اصلی", reply_markup=main_keyboard())
        return

    # ============ ADMIN LOGIN ============
    if txt == "ورود ادمین":

        # ❌ FIX: اینجا قبلاً اشتباه داشتی
        if user_id != ADMIN_ID:
            bot.send_message(message.chat.id, "شما ادمین نیستید")
            return

        bot.send_message(message.chat.id, "پنل ادمین", reply_markup=admin_keyboard())
        return

    # ============ ADMIN ACTIONS ============
    if txt == "آپلود معلمان":

        if user_id != ADMIN_ID:
            return

        user_state[user_id] = "teachers"
        bot.send_message(message.chat.id, "فایل teachers.csv را ارسال کنید", reply_markup=back_keyboard())
        return

    if txt == "مشاهده معلمان":

        if user_id != ADMIN_ID:
            return

        cur.execute("SELECT name, classes FROM teachers")
        rows = cur.fetchall()

        if not rows:
            bot.send_message(message.chat.id, "معلمی ثبت نشده")
            return

        msg = "لیست معلمان:\n\n"
        for r in rows:
            msg += f"👨‍🏫 {r[0]} | {r[1]}\n\n"

        bot.send_message(message.chat.id, msg)
        return

    # ============ TEACHER LOGIN ============
    if txt == "ورود معلم":

        user_state[user_id] = "teacher_login"
        bot.send_message(message.chat.id, "کد معلم را وارد کنید", reply_markup=back_keyboard())
        return

    if user_state.get(user_id) == "teacher_login":

        cur.execute("SELECT * FROM teachers WHERE code=?", (txt,))
        teacher = cur.fetchone()

        if not teacher:
            bot.send_message(message.chat.id, "معلم پیدا نشد")
            user_state.pop(user_id, None)
            return

        teacher_sessions[user_id] = {
            "name": teacher[2],
            "classes": teacher[3]
        }

        user_state.pop(user_id, None)

        bot.send_message(
            message.chat.id,
            f"خوش آمدید {teacher[2]}",
            reply_markup=teacher_keyboard()
        )
        return

    # ============ STUDENT LOGIN ============
    if txt == "ورود دانش آموز":

        user_state[user_id] = "student_login"
        bot.send_message(message.chat.id, "کد دانش آموز را وارد کنید", reply_markup=back_keyboard())
        return

    if user_state.get(user_id) == "student_login":

        cur.execute("SELECT * FROM students WHERE code=?", (txt,))
        student = cur.fetchone()

        if not student:
            bot.send_message(message.chat.id, "دانش آموز پیدا نشد")
            return

        cur.execute("""
            SELECT lesson, month, grade, description
            FROM grades
            WHERE student_code=?
        """, (txt,))

        rows = cur.fetchall()

        msg = f"👨‍🎓 {student[2]}\n🏫 {student[3]}\n\n"

        for r in rows:
            msg += f"📘 {r[0]} | {r[1]} | {r[2]} | {r[3]}\n"

        bot.send_message(message.chat.id, msg, reply_markup=main_keyboard())
        user_state.pop(user_id, None)
        return

# ================= FILE UPLOAD =================

@bot.message_handler(content_types=['document'])
def doc(message):

    user_id = message.from_user.id

    if user_id not in user_state:
        bot.send_message(message.chat.id, "ابتدا گزینه را انتخاب کنید")
        return

    state = user_state[user_id]

    file_info = bot.get_file(message.document.file_id)
    file_url = f"https://tapi.bale.ai/file/bot{TOKEN}/{file_info.file_path}"

    data = requests.get(file_url).content

    filename = f"{state}_{user_id}.csv"

    with open(filename, "wb") as f:
        f.write(data)

    with open(filename, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if state == "teachers":
            cur.execute("DELETE FROM teachers")
            for r in reader:
                cur.execute("INSERT INTO teachers(code,name,classes) VALUES(?,?,?)",
                            (r["code"], r["name"], r["classes"]))
            conn.commit()

        elif state == "students":
            cur.execute("DELETE FROM students")
            for r in reader:
                cur.execute("INSERT INTO students(code,name,class_name) VALUES(?,?,?)",
                            (r["code"], r["name"], r["class_name"]))
            conn.commit()

        elif state == "grades":
            cur.execute("DELETE FROM grades")
            for r in reader:
                cur.execute("""
                    INSERT INTO grades(student_code,lesson,month,grade,description)
                    VALUES(?,?,?,?,?)
                """, (r["student_code"], r["lesson"], r["month"], r["grade"], r["description"]))
            conn.commit()

    os.remove(filename)
    user_state.pop(user_id, None)

    bot.send_message(message.chat.id, "انجام شد", reply_markup=main_keyboard())

# ================= RUN =================

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("ERROR:", e)
        time.sleep(5)
