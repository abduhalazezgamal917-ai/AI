import os
import re
import telebot
import requests
from keep_alive import keep_alive

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

bot = telebot.TeleBot(TOKEN)

# ترتيب أولوية النماذج - Groq أوقف نماذج Llama نهائياً (16 أغسطس 2026)
# البدائل الرسمية المقترحة من Groq نفسه:
PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
]

def test_model(model_id):
    """يرسل طلب تجريبي صغير جداً للتأكد إن النموذج فعلاً يقدر يرد على شات"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def get_chat_model():
    for model_id in PREFERRED_MODELS:
        print(f"🔍 تجربة النموذج: {model_id}")
        if test_model(model_id):
            print(f"✅ تم اختيار النموذج: {model_id}")
            return model_id
    print("⚠️ ما اشتغل أي نموذج من القائمة، رجعنا للاحتياطي")
    return "openai/gpt-oss-20b"

ACTIVE_MODEL = get_chat_model()

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are a witty, sharp, and clever AI assistant with a light sarcastic sense of humor, "
        "but your answers are always well-organized, professional, and easy to scan — like a "
        "top-tier AI assistant. Reply in the same language the user writes in (Arabic or English), "
        "automatically.\n\n"
        "FORMATTING RULES (Telegram, not standard Markdown):\n"
        "1. Telegram does NOT support #, ##, ### headers. Instead, use a short bolded line as a "
        "section title, e.g. *الخطوة الأولى* on its own line, followed by its content.\n"
        "2. Use single-asterisk *bold* for emphasis and section titles — never double asterisks.\n"
        "3. Use bullet points with '•' for lists, or numbered lists (1. 2. 3.) for sequential steps.\n"
        "4. Wrap code or commands in triple backticks ``` so they render as code blocks.\n"
        "5. Keep paragraphs short (2-3 lines max). Add a blank line between sections for readability.\n"
        "6. For longer answers, structure the response as: a one-line direct answer first, then "
        "supporting details broken into clearly bolded sections or bullets.\n"
        "7. Never use raw #, ##, ### symbols anywhere in the output.\n"
        "Be direct and substantive — skip unnecessary disclaimers or moralizing — while staying "
        "clean, structured, and professional in presentation."
    )
}

def sanitize_for_telegram(text):
    """يحول أي ماركداون قياسي لصيغة يفهمها تيليجرام مع الحفاظ على الهيكلة"""
    # حول العناوين (# ## ###) إلى سطر بولد بدل ما نشيلها بالكامل
    text = re.sub(r'^#{1,6}\s*(.+)$', r'*\1*', text, flags=re.MULTILINE)
    # حول **bold** إلى *bold* (تيليجرام يفهم نجمة وحدة بس)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # وحّد رموز القوائم (- أو *) إلى نقطة موحدة •
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
    # شيل أي أسطر فاضية زايدة عن سطرين متتاليين
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def ask_ai(text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": ACTIVE_MODEL,
        "messages": [
            SYSTEM_PROMPT,
            {"role": "user", "content": text}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            raw = response.json()["choices"][0]["message"]["content"]
            return sanitize_for_telegram(raw)
        else:
            return f"❌ خطأ API ({response.status_code}):\n{response.text}"
    except Exception as e:
        return f"❌ خطأ في السيرفر: {str(e)}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📢 قناة الأدوات", url="https://t.me/ZenoX_Tools"),
        telebot.types.InlineKeyboardButton("⚙️ حالة البوت", callback_data="status")
    )
    welcome_text = f"أهلاً بك 🚀\nالنموذج النشط: `{ACTIVE_MODEL}`\nتفضل بسؤالك:"
    bot.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "status":
        bot.answer_callback_query(call.id, f"البوت يعمل بنجاح باستخدام النموذج: {ACTIVE_MODEL}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    ai_reply = ask_ai(message.text)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📌 حفظ في المفضلة", callback_data="save_msg"))

    try:
        bot.reply_to(message, ai_reply, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        bot.reply_to(message, ai_reply, reply_markup=markup)

if __name__ == "__main__":
    print("جاري تشغيل سيرفر Keep-Alive...")
    keep_alive()
    print(f"البوت يعمل ويستخدم نموذج الدردشة: {ACTIVE_MODEL}")
    bot.infinity_polling()









