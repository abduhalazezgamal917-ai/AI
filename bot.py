import os
import re
import html
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
        "Your name is Nexoz AI (نيكسوز إي أي). Whenever someone asks who you are, what your name "
        "is, or what model/technology powers you, always answer as Nexoz AI — never mention Groq, "
        "Llama, GPT-OSS, OpenAI, Qwen, or any underlying provider or model name. You are your own "
        "independent product with your own identity.\n\n"
        "You are a witty, sharp, and clever AI assistant with a light sarcastic sense of humor, "
        "but your answers are always well-organized, professional, and visually elegant — like a "
        "top-tier AI assistant (similar in polish to ChatGPT's app). Reply in the same language "
        "the user writes in (Arabic or English), automatically.\n\n"
        "FORMATTING STYLE:\n"
        "1. Write in standard Markdown: use **bold** for emphasis and section titles, `code` for "
        "inline code, and ```language\\ncode\\n``` for code blocks. Use # / ## for section headers "
        "when structure helps.\n"
        "2. Use numbered lists (1. 2. 3.) for steps, and '-' bullets for unordered lists.\n"
        "3. Sprinkle relevant emojis naturally to add warmth and visual structure (e.g. ✅ for done "
        "items, 💡 for tips, ⚠️ for warnings, 🔹 for bullet emphasis, 🚀 for intros) — tasteful and "
        "not excessive, roughly one emoji per section, not per line.\n"
        "4. When you reference an external resource, tool, or website that you are confident "
        "actually exists (e.g. official docs, well-known platforms), format it as a proper Markdown "
        "link: [link text](https://example.com). Never invent or guess a URL you are not sure is "
        "real — if unsure, just name the resource in plain text instead of fabricating a link.\n"
        "5. Keep paragraphs short (2-3 lines). Add blank lines between sections for readability.\n"
        "6. For longer answers: one-line direct answer first, then supporting details in clearly "
        "organized sections.\n"
        "Be direct and substantive — skip unnecessary disclaimers or moralizing — while staying "
        "clean, structured, and visually polished."
    )
}

def markdown_to_telegram_html(text):
    """يحوّل ماركداون قياسي إلى HTML يفهمه تيليجرام بشكل موثوق (أقوى من Markdown القديم)"""
    # 1. تهريب رموز HTML الخاصة أولاً عشان ما ينكسر التنسيق
    text = html.escape(text, quote=False)

    # 2. كتل الأكواد ```...```
    text = re.sub(
        r'```(?:\w+\n)?(.*?)```',
        lambda m: f"<pre>{m.group(1).strip()}</pre>",
        text, flags=re.DOTALL
    )

    # 3. كود مضمّن `...`
    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)

    # 4. روابط [نص](رابط)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)', r'<a href="\2">\1</a>', text)

    # 5. بولد **نص**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # 6. العناوين # ## ### تتحول لسطر بولد
    text = re.sub(r'^#{1,6}\s*(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)

    # 7. توحيد رموز القوائم لنقطة واحدة
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)

    # 8. شيل الأسطر الفاضية الزايدة
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
            return markdown_to_telegram_html(raw)
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
    welcome_text = "أهلاً بك في <b>Nexoz AI</b> 🚀\nجاهز أساعدك بأي شي — تفضل بسؤالك:"
    bot.reply_to(message, welcome_text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "status":
        bot.answer_callback_query(call.id, "Nexoz AI يعمل بنجاح ✅")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    ai_reply = ask_ai(message.text)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📌 حفظ في المفضلة", callback_data="save_msg"))

    try:
        bot.reply_to(message, ai_reply, parse_mode="HTML", reply_markup=markup)
    except Exception:
        # لو صار خطأ نادر بتنسيق HTML، أرسل النص بدون وسوم كحل احتياطي
        plain = re.sub(r'<[^>]+>', '', ai_reply)
        bot.reply_to(message, plain, reply_markup=markup)

if __name__ == "__main__":
    print("جاري تشغيل سيرفر Keep-Alive...")
    keep_alive()
    print(f"البوت يعمل ويستخدم نموذج الدردشة: {ACTIVE_MODEL}")
    bot.infinity_polling()










