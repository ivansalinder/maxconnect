from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
import sqlite3
from typing import List
import httpx
import os

app = FastAPI(title="MAX TeamPlay API", description="Бэкенд для радара досуга (Уфа)")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Токен берем из переменных окружения (безопасность по ТЗ)
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN", "test_token")
MAX_API_URL = "https://api.max.ru/v1" # Замени на актуальный URL API MAX из их доки

def init_db():
    conn = sqlite3.connect('teamplay.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS lobbies
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, 
                  category TEXT, 
                  location TEXT, 
                  participants INTEGER, 
                  max_participants INTEGER, 
                  time TEXT)''')
    
    # Синтетический мок-слой для Уфы
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

async def send_max_message(chat_id: str, text: str):
    """Асинхронная отправка сообщения через API МАХ"""
    async with httpx.AsyncClient(verify=False) as client: # verify=False обходит ошибку SEC_E_UNTRUSTED_ROOT
        try:
            payload = {"chat_id": chat_id, "text": text}
            headers = {"Authorization": f"Bearer {MAX_BOT_TOKEN}"}
            # Убедись, что эндпоинт отправки сообщения совпадает с докой МАХ
            await client.post(f"{MAX_API_URL}/messages/send", json=payload, headers=headers)
        except Exception as e:
            print(f"Ошибка интеграции с МАХ: {e}")

class Lobby(BaseModel):
    title: str
    category: str
    location: str
    max_participants: int
    time: str

@app.get("/api/lobbies", response_model=List[dict])
def get_lobbies():
    conn = sqlite3.connect('teamplay.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM lobbies")
    lobbies = [dict(row) for row in c.fetchall()]
    conn.close()
    return lobbies

@app.post("/api/lobbies")
def create_lobby(lobby: Lobby):
    conn = sqlite3.connect('teamplay.db')
    c = conn.cursor()
    c.execute("INSERT INTO lobbies (title, category, location, participants, max_participants, time) VALUES (?, ?, ?, ?, ?, ?)",
              (lobby.title, lobby.category, lobby.location, 1, lobby.max_participants, lobby.time))
    conn.commit()
    conn.close()
    return {"status": "success"}

class JoinRequest(BaseModel):
    lobby_id: int
    user_id: str # ID участника в МАХ
    organizer_chat_id: str # Куда отправлять пуш

@app.post("/api/join")
async def join_lobby(req: JoinRequest, background_tasks: BackgroundTasks):
    # Уведомляем организатора в фоне, чтобы не задерживать ответ фронтенду
    text_for_organizer = f"К вашему сбору #{req.lobby_id} присоединился новый участник!"
    background_tasks.add_task(send_max_message, req.organizer_chat_id, text_for_organizer)
    
    # Отбивка самому участнику
    text_for_user = "Вы успешно присоединились к мероприятию! Контакты организатора: @org_name"
    background_tasks.add_task(send_max_message, req.user_id, text_for_user)
    
    return {"status": "success", "message": "Notifications sent"}

@app.post("/api/webhook")
async def max_webhook(request: Request, background_tasks: BackgroundTasks):
    """Обработка входящих вебхуков от платформы МАХ"""
    data = await request.json()
    
    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")
    
    if text == "/start" and chat_id:
        welcome_text = "Привет! Я «Радар досуга». Нажми кнопку ниже, чтобы открыть приложение и найти компанию в Уфе."
        # В рабочей версии сюда нужно добавить структуру inline-кнопки для открытия Web App (по документации МАХ)
        background_tasks.add_task(send_max_message, str(chat_id), welcome_text)
        
    return {"status": "ok"}