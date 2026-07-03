import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-2.0-flash",
    system_instruction=(
        "Ты — TOMA, дружелюбный Telegram-помощник. "
        "Ты помогаешь с задачами, временем намазов, учёбой и повседневными делами. "
        "Отвечай кратко и по-русски. Используй эмодзи где уместно. "
        "Если просят создать задачу или напоминание — "
        "скажи что нужно написать это в формате: 'завтра в 15:00 позвонить маме'."
    ),
)

chat_sessions: dict[int, genai.ChatSession] = {}


def get_chat(user_id: int) -> genai.ChatSession:
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])
    return chat_sessions[user_id]


async def ask_ai(user_id: int, text: str) -> str:
    try:
        chat = get_chat(user_id)
        response = chat.send_message(text)
        return response.text
    except Exception as e:
        return f"⚠️ Не удалось получить ответ. Попробуй позже."


def clear_history(user_id: int):
    chat_sessions.pop(user_id, None)
