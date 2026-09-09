import asyncio
import sqlite3
import os
from datetime import date
import threading

from flask import Flask, request

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# =========================
# BOT TOKEN
# =========================

TOKEN = os.getenv("BOT_TOKEN")


# =========================
# SETTINGS
# =========================

REWARD_PER_AD = 0.05
DAILY_AD_LIMIT = 100
MIN_WITHDRAW = 10.00


# =========================
# BOT
# =========================

bot = Bot(token=TOKEN)
dp = Dispatcher()


# =========================
# DATABASE
# =========================

db = sqlite3.connect("bot.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    ads_today INTEGER DEFAULT 0,
    last_date TEXT
)
""")

db.commit()

# =========================
# FLASK SERVER
# =========================

app = Flask(__name__)
@app.get("/adsgram/reward")
def adsgram_reward():
    user_id = request.args.get("userid", type=int)

    if not user_id:
        return "Missing userid", 400

    balance, ads_today = get_user(user_id)

    if ads_today >= DAILY_AD_LIMIT:
        return "Daily limit reached", 200

    new_balance = balance + REWARD_PER_AD
    new_ads_today = ads_today + 1
    today = str(date.today())

    cursor.execute("""
        UPDATE users
        SET balance = ?, ads_today = ?, last_date = ?
        WHERE user_id = ?
    """, (new_balance, new_ads_today, today, user_id))

    db.commit()

    return "OK", 200

# =========================
# USER DATA
# =========================

def get_user(user_id):

    today = str(date.today())

    cursor.execute(
        """
        SELECT balance, ads_today, last_date
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    if user is None:

        cursor.execute(
            """
            INSERT INTO users
            (user_id, balance, ads_today, last_date)
            VALUES (?, 0, 0, ?)
            """,
            (user_id, today)
        )

        db.commit()

        return 0.00, 0

    balance, ads_today, last_date = user

    # Yeni gün
    if last_date != today:

        cursor.execute(
            """
            UPDATE users
            SET ads_today = 0,
                last_date = ?
            WHERE user_id = ?
            """,
            (today, user_id)
        )

        db.commit()

        ads_today = 0

    return balance, ads_today


# =========================
# MAIN MENU
# =========================

def main_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📺 Reklama bax +0.05 AZN",
                    callback_data="watch_ad"
                )
            ],

            [
                InlineKeyboardButton(
                    text="💰 Balansım",
                    callback_data="balance"
                )
            ],

            [
                InlineKeyboardButton(
                    text="💳 Pul çıxar",
                    callback_data="withdraw"
                )
            ],

            [
                InlineKeyboardButton(
                    text="👥 Referal",
                    callback_data="referral"
                )
            ]

        ]
    )


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    balance, ads_today = get_user(message.from_user.id)

    await message.answer(

        "🎉 Xoş gəlmisən!\n\n"
        "📺 Reklamlara baxaraq bonus qazana bilərsən.\n\n"
        "💰 1 reklam = 0.05 AZN\n"
        "📺 Gündə maksimum = 100 reklam\n"
        "💵 Gündə maksimum = 5.00 AZN\n"
        "💳 Minimum çıxarış = 10.00 AZN\n\n"

        f"💰 Balansın: {balance:.2f} AZN\n"
        f"📊 Bu gün: {ads_today}/100 reklam",

        reply_markup=main_menu()
    )


# =========================
# WATCH AD
# =========================

@dp.callback_query(F.data == "watch_ad")
async def watch_ad(callback: CallbackQuery):

    balance, ads_today = get_user(callback.from_user.id)

    if ads_today >= DAILY_AD_LIMIT:

        await callback.answer(
            "🚫 Bu gün üçün 100 reklam limitinə çatmısan.",
            show_alert=True
        )

        return

    await callback.answer(
        "📺 Real reklam hələ qoşulmayıb.",
        show_alert=True
    )


# =========================
# BALANCE
# =========================

@dp.callback_query(F.data == "balance")
async def balance_button(callback: CallbackQuery):

    balance, ads_today = get_user(callback.from_user.id)

    await callback.answer(

        f"💰 Balans: {balance:.2f} AZN\n\n"
        f"📺 Bu gün: {ads_today}/100 reklam\n"
        f"💵 Reklam başına: 0.05 AZN\n"
        f"💳 Minimum çıxarış: 10.00 AZN",

        show_alert=True
    )


# =========================
# WITHDRAW
# =========================

@dp.callback_query(F.data == "withdraw")
async def withdraw(callback: CallbackQuery):

    balance, ads_today = get_user(callback.from_user.id)

    if balance < MIN_WITHDRAW:

        remaining = MIN_WITHDRAW - balance

        await callback.answer(

            f"❌ Minimum çıxarış: {MIN_WITHDRAW:.2f} AZN\n\n"
            f"💰 Balansın: {balance:.2f} AZN\n"
            f"📌 Daha {remaining:.2f} AZN toplamalısan.",

            show_alert=True
        )

        return

    await callback.answer(
        "💳 Çıxarış sistemi növbəti mərhələdə qoşulacaq.",
        show_alert=True
    )


# =========================
# REFERRAL
# =========================

@dp.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):

    await callback.answer(
        "👥 Referal sistemi hazırlanır.",
        show_alert=True
    )


# =========================
# START BOT
# =========================

def run_flask():
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
        use_reloader=False
    )


async def main():
    print("🤖 Reklam botu başladı!")
    print("💰 Reklam reward: 0.05 AZN")
    print("📺 Gündəlik limit: 100")
    print("💳 Minimum çıxarış: 10 AZN")

    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
