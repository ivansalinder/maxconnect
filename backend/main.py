import os
import sqlite3
import logging
import httpx
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="MAX TeamPlay API", description="Бэкенд для радара досуга (Уфа)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN", "f9LHodD0cOL5VFLxyvlUr0pgowbe9NfMW02XI41VCwmgvSv91cQz7_1bPZ34wpuRb55aaNAHptfXO_vuZt8B")
MAX_API_URL = "https://platform-api2.max.ru"
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://saturate-undecided-perfected.ngrok-free.dev")

def init_db():
    conn = sqlite3.connect('teamplay.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS lobbies
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, category TEXT, location TEXT, 
                  participants INTEGER, max_participants INTEGER, time TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM lobbies")
    if c.fetchone()[0] == 0:
        mock_data = [
            ('Баскетбол 3х3', 'Спорт', 'Парк Кашкадан', 2, 6, 'Сегодня 19:00'),
            ('Квиз: Эпоха 90-х', 'Настолки/Квизы', 'Арт-КВАДРАТ', 3, 5, 'Завтра 20:00'),
            ('Сбор на настолки', 'Культура', 'Мега Уфа', 1, 4, 'Суббота 15:00'),
            ('Волейбол', 'Спорт', 'Манеж УГНТУ', 8, 12, 'Сегодня 21:00')
        ]
        c.executemany("INSERT INTO lobbies (title, category, location, participants, max_participants, time) VALUES (?, ?, ?, ?, ?, ?)", mock_data)
    conn.commit()
    conn.close()

init_db()

class JoinRequest(BaseModel):
    lobby_id: int
    user_id: str 
    organizer_chat_id: str 

async def send_max_message(text: str, target_id: str, is_group: bool = False, with_webapp: bool = False):
    headers = {
        "Authorization": MAX_BOT_TOKEN,
        "Content-Type": "application/json"
    }

    params = {"chat_id": target_id} if is_group else {"user_id": target_id}
    
    payload = {
        "text": text
    }

    if with_webapp:
        # Правильный параметр для платформ семейства MyTeam / MAX API
        payload["inline_keyboard_row"] = [
            [
                {
                    "text": "Открыть радар досуга",
                    "url": WEBAPP_URL
                }
            ]
        ]

    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.post(
                f"{MAX_API_URL}/messages", 
                params=params, 
                json=payload, 
                headers=headers
            )
            logger.info(f"Статус отправки MAX: {response.status_code}")
            logger.info(f"Ответ MAX: {response.text}")
        except Exception as e:
            logger.error(f"Исключение при вызове MAX API: {e}")

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/api/lobbies", response_model=List[dict])
def get_lobbies():
    conn = sqlite3.connect('teamplay.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM lobbies")
    lobbies = [dict(row) for row in c.fetchall()]
    conn.close()
    return lobbies

@app.post("/api/join")
async def join_lobby(req: JoinRequest, background_tasks: BackgroundTasks):
    text_for_organizer = f"К вашему сбору #{req.lobby_id} присоединился новый участник!"
    background_tasks.add_task(send_max_message, text=text_for_organizer, target_id=req.organizer_chat_id)
    
    text_for_user = "Вы успешно присоединились к мероприятию! Контакты организатора: @org_name"
    background_tasks.add_task(send_max_message, text=text_for_user, target_id=req.user_id)
    return {"status": "success"}

@app.post("/api/webhook")
async def max_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    message_data = data.get("message") or data.get("payload", {})
    text = message_data.get("body", {}).get("text", "").strip()

    recipient_data = message_data.get("recipient", {})
    chat_type = recipient_data.get("chat_type", "dialog")
    chat_id = recipient_data.get("chat_id")
    
    sender = message_data.get("sender", {})
    sender_user_id = sender.get("user_id")

    is_group = chat_type != "dialog"
    target_id = str(chat_id) if is_group else str(sender_user_id)

    if text.startswith("/start"):
        welcome_text = "Привет! Я «Радар досуга». Нажми на кнопку ниже, чтобы открыть мини-приложение:"
        background_tasks.add_task(
            send_max_message,
            text=welcome_text,
            target_id=target_id,
            is_group=is_group,
            with_webapp=True
        )
        
    return {"status": "ok"}