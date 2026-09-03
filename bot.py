import os
import telebot
import requests
from keep_alive import keep_alive

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

bot = telebot.TeleBot(TOKEN)

def get_valid_model():
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            models = response.json().get("data", [])
            for model in models:
                model_id = model["id"]
                # نتجنب نماذج الحماية، الصوت، أو النماذج غير المخصصة للدردشة
                if "llama" in model_id and "guard" not in model_id and "whisper" not in model_id:
                    print(f"✅ تم اختيار نموذج دردشة صالح: {model_id}")
                    return model_id
    except Exception as e:
        print(f"خطأ في جلب النماذج: {e}")
    return "llama-3.3-70b-versatile"

ACTIVE_MODEL = get_valid_model()

def ask_ai(text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": ACTIVE_MODEL,
        "messages": [{"role": "user", "content": text}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ خطأ API ({response.status_code}):\n{response.text}"
    except Exception as e:
        return f"❌ خطأ في السيرفر: {str(e)}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"أهلاً بك! أنا أعمل الآن بنموذج الدردشة: {ACTIVE_MODEL}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    ai_reply = ask_ai(message.text)
    bot.reply_to(message, ai_reply)

if __name__ == "__main__":
    print("جاري تشغيل سيرفر Keep-Alive...")
    keep_alive()
    print(f"البوت يعمل ويستخدم النموذج: {ACTIVE_MODEL}")
    bot.infinity_polling()




