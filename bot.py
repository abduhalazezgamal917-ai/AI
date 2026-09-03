import os
import telebot
import requests
from keep_alive import keep_alive

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

bot = telebot.TeleBot(TOKEN)

def get_chat_model():
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            models = response.json().get("data", [])
            # البحث عن أول نموذج مخصص للدردشة وتخطي الصوت والحماية
            for model in models:
                m_id = model["id"].lower()
                if any(name in m_id for name in ["llama", "mixtral", "gemma", "qwen", "deepseek"]) and not any(bad in m_id for bad in ["whisper", "guard", "embed", "tts"]):
                    print(f"✅ تم اختيار نموذج دردشة صالح: {model['id']}")
                    return model["id"]
            
            # إذا لم يجد اسمًا معروفاً، يأخذ أول نموذج ليس له علاقة بالصوت أو الحماية
            for model in models:
                m_id = model["id"].lower()
                if not any(bad in m_id for bad in ["whisper", "guard", "embed", "tts"]):
                    return model["id"]
    except Exception as e:
        print(f"خطأ في جلب النماذج: {e}")
    return "llama-3.1-8b-instant"

ACTIVE_MODEL = get_chat_model()

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
    bot.reply_to(message, f"أهلاً بك! النموذج النشط للدردشة الآن هو:\n{ACTIVE_MODEL}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    ai_reply = ask_ai(message.text)
    bot.reply_to(message, ai_reply)

if __name__ == "__main__":
    print("جاري تشغيل سيرفر Keep-Alive...")
    keep_alive()
    print(f"البوت يعمل ويستخدم نموذج الدردشة: {ACTIVE_MODEL}")
    bot.infinity_polling()






