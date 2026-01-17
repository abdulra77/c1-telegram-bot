import os
import datetime as dt
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from supabase import create_client
from openai import OpenAI

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
OPENAI_KEY = os.environ["OPENAI_API_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
ai = OpenAI(api_key=OPENAI_KEY)

TABLE = "progress"

def get_next_session_no(user_id: int) -> int:
    res = (
        sb.table(TABLE)
        .select("session_no")
        .eq("telegram_user_id", user_id)
        .order("session_no", desc=True)
        .limit(1)
        .execute()
    )
    if res.data:
        return int(res.data[0]["session_no"]) + 1
    return 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ C1 Coach Bot läuft!\n\n"
        "Befehle:\n"
        "/pingdb – Test: schreibt in Supabase\n"
        "/session – heutige Session\n"
        "/stats – letzter Stand"
    )

async def pingdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = str(dt.date.today())

    payload = {
        "telegram_user_id": user_id,
        "date": today,
        "session_no": 0,
        "reading_score": 0,
        "vocab_score": 0,
        "writing_score": 0,
    }

    sb.table(TABLE).insert(payload).execute()
    await update.message.reply_text("✅ DB OK – Testzeile gespeichert.")

async def session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session_no = get_next_session_no(user_id)

    prompt = f"""
Du bist ein Deutsch-C1 Tutor.
Erstelle Session Nr. {session_no} (allgemeines C1).

FORMAT:
TEXT:
(200-260 Wörter, sachlich, modernes Thema)

FRAGEN:
1) ...
2) ...
3) ...
4) ...
5) ...

AUFGABE:
(90-120 Wörter Schreibauftrag)

Alles auf Deutsch.
"""
    r = ai.responses.create(model="gpt-5.2-instant", input=prompt)
    content = r.output_text.strip()

    await update.message.reply_text(content)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    res = (
        sb.table(TABLE)
        .select("*")
        .eq("telegram_user_id", user_id)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        await update.message.reply_text("Noch keine Daten. Nutze /pingdb oder /session.")
        return
    last = res.data[0]
    await update.message.reply_text(
        f"📊 Letzter Eintrag:\n"
        f"Datum: {last.get('date')}\n"
        f"Session: {last.get('session_no')}\n"
        f"Scores (R/V/W): {last.get('reading_score')}/{last.get('vocab_score')}/{last.get('writing_score')}"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pingdb", pingdb))
    app.add_handler(CommandHandler("session", session))
    app.add_handler(CommandHandler("stats", stats))
    app.run_polling()

if __name__ == "__main__":
    main()
