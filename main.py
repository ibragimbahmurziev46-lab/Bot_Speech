# ============================================================
# ОБЩИЕ ИМПОРТЫ
# ============================================================
import json
import os
import re
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
import tempfile
import wave
import numpy as np
import sounddevice as sd
import speech_recognition as sr

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# ============================================================
# НАСТРОЙКИ
# ============================================================
MODEL_NAME = "qwen2.5-coder-3b-instruct"
BASE_URL = "http://localhost:1234/v1"

FILE_NAME = "game_reviews.json"
BANNED_WORDS_FILE = "banned_words.txt"

# ============================================================
# КЕШ НА SQLITE
# ============================================================
class SimpleCache:
    def __init__(self, db_path="simple_cache.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    prompt_hash TEXT PRIMARY KEY,
                    prompt TEXT,
                    response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
    
    def get(self, prompt: str):
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT response FROM cache WHERE prompt_hash = ?",
                (self._hash(prompt),)
            ).fetchone()
            return result[0] if result else None
    
    def set(self, prompt: str, response: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (prompt_hash, prompt, response) VALUES (?, ?, ?)",
                (self._hash(prompt), prompt, response)
            )

cache = SimpleCache()

# ============================================================
# ИНИЦИАЛИЗАЦИЯ МОДЕЛИ
# ============================================================
chat_model = ChatOpenAI(
    base_url=BASE_URL,
    api_key="lm-studio",
    model=MODEL_NAME,
    temperature=0.1,
    max_tokens=4000,
    timeout=120,
    max_retries=3
)

# ============================================================
# ЦЕНЗУРА / SQLi / JAILBREAK
# ============================================================
def load_banned_words():
    if not os.path.exists(BANNED_WORDS_FILE):
        open(BANNED_WORDS_FILE, "w", encoding="utf-8").close()
        return []
    return [w.strip().lower() for w in open(BANNED_WORDS_FILE, encoding="utf-8") if w.strip()]

BANNED_WORDS = load_banned_words()

def censored(text):
    return any(w in text.lower() for w in BANNED_WORDS)

def check_sql(text):
    return bool(re.search(r"\b(select|union|drop|insert|delete)\b", text, re.I))

def check_jailbreak(text):
    return bool(re.search(r"\b(ignore|bypass|dan|developer mode)\b", text, re.I))

# ============================================================
# 🎤 РАСПОЗНАВАНИЕ РЕЧИ (ДЛЯ PYTHON 3.13)
# ============================================================
def list_microphones():
    """Показывает список доступных микрофонов"""
    print("\n📋 Доступные микрофоны:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  {i}: {device['name']}")

def recognize_speech(duration=5):
    """Распознаёт речь через микрофон с помощью sounddevice"""
    
    input("\n🎤 Нажми Enter, чтобы начать говорить...")
    print(f"🎙️ Слушаю... (запись {duration} секунд)")
    
    # Параметры записи
    sample_rate = 16000
    
    # Запись звука
    print("🔴 Запись...")
    recording = sd.rec(int(duration * sample_rate), 
                       samplerate=sample_rate, 
                       channels=1, 
                       dtype='int16')
    sd.wait()  # Ждём завершения
    print("✅ Запись завершена")
    
    # Сохраняем во временный WAV файл
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmpfile:
        with wave.open(tmpfile.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(recording.tobytes())
        tmp_path = tmpfile.name
    
    # Распознаём через Google Speech Recognition
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)
        
        print("🔄 Распознаю...")
        text = recognizer.recognize_google(audio, language="ru-RU")
        print(f"✅ Распознано: {text}")
        return text
    except sr.UnknownValueError:
        print("❌ Не удалось распознать речь")
        return None
    except sr.RequestError as e:
        print(f"❌ Ошибка сервиса распознавания: {e}")
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None
    finally:
        # Удаляем временный файл
        try:
            os.unlink(tmp_path)
        except:
            pass

def voice_chat():
    """Голосовой чат с ИИ"""
    print("\n" + "="*50)
    print("🎙️ ГОЛОСОВОЙ ЧАТ С ИИ")
    print("="*50)
    
    # Показываем микрофоны (опционально)
    list_microphones()
    
    spoken_text = recognize_speech(duration=5)  # 5 секунд на фразу
    
    if not spoken_text:
        print("\n⚠️ Не удалось распознать речь, возврат в меню")
        return
    
    # Проверка безопасности
    if censored(spoken_text) or check_sql(spoken_text) or check_jailbreak(spoken_text):
        print("❌ Вопрос заблокирован системой безопасности")
        return
    
    print(f"\n📝 Ваш вопрос: {spoken_text}")
    
    # Проверяем кеш
    cached = cache.get(spoken_text)
    if cached:
        print("💾 (из кеша)")
        print("\n🤖 ОТВЕТ ИИ:\n", cached)
        return
    
    # Отправляем в LM Studio
    print("🧠 Отправляю запрос в LM Studio...")
    try:
        response = chat_model.invoke([
            SystemMessage(content="Ты полезный ИИ-ассистент. Отвечай на вопросы дружелюбно и информативно."),
            HumanMessage(content=spoken_text)
        ])
        
        answer = response.content
        cache.set(spoken_text, answer)
        
        print("\n🤖 ОТВЕТ ИИ:\n", answer)
        
    except Exception as e:
        print(f"❌ Ошибка при обращении к LM Studio: {e}")
        print("Проверьте, запущен ли сервер LM Studio (http://localhost:1234)")

# ============================================================
# МЕНЕДЖЕР ОБЗОРОВ ИГР
# ============================================================
def load_reviews():
    if not Path(FILE_NAME).exists():
        return []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return json.load(f)

def save_reviews(reviews):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=4)

def add_review(reviews):
    print("\n➕ ДОБАВЛЕНИЕ ОБЗОРА")
    title = input("Название игры: ").strip()
    if not title:
        print("❌ Название не может быть пустым")
        return
    
    genre = input("Жанр: ").strip()
    
    try:
        rating = int(input("Оценка (1-10): ").strip())
        if rating < 1 or rating > 10:
            print("❌ Оценка должна быть от 1 до 10")
            return
    except ValueError:
        print("❌ Оценка должна быть числом")
        return
    
    text = input("Текст обзора: ").strip()
    if not text:
        print("❌ Текст обзора не может быть пустым")
        return

    reviews.append({
        "title": title,
        "genre": genre,
        "rating": rating,
        "review": text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_reviews(reviews)
    print(f"✅ Обзор '{title}' добавлен!")

def show_reviews(reviews):
    if not reviews:
        print("\n📭 Обзоров пока нет")
        return
    
    print("\n📚 СПИСОК ОБЗОРОВ:")
    print("-" * 50)
    for i, r in enumerate(reviews, 1):
        print(f"{i}. {r['title']} ({r['genre']}) — {r['rating']}/10")
        print(f"   📅 {r['date']}")
        print(f"   💬 {r['review'][:100]}...")
        print()

def ask_ai_about_reviews(reviews):
    if not reviews:
        print("\n⚠️ Сначала добавьте хотя бы один обзор")
        return
    
    print("\n❓ ВОПРОС К ИИ ОБ ОБЗОРАХ")
    q = input("Ваш вопрос: ").strip()
    if not q:
        return

    if censored(q) or check_sql(q) or check_jailbreak(q):
        print("❌ Вопрос заблокирован системой безопасности")
        return

    cached = cache.get(q)
    if cached:
        print("\n💾 ИЗ КЕША:")
        print(cached)
        return

    # Формируем краткую сводку обзоров
    summary = "\n".join(
        f"- {r['title']} ({r['genre']}): {r['rating']}/10. {r['review'][:200]}"
        for r in reviews[:10]
    )
    
    system = f"""Ты ИИ-помощник менеджера обзоров видеоигр.
Отвечай ТОЛЬКО про видеоигры, жанры, оценки и рекомендации.

Вот обзоры пользователей:
{summary}

Отвечай полезно и по делу."""

    print("🧠 Думаю...")
    resp = chat_model.invoke([
        SystemMessage(content=system),
        HumanMessage(content=q)
    ])

    cache.set(q, resp.content)
    print("\n🤖 ОТВЕТ ИИ:\n", resp.content)

def game_manager():
    reviews = load_reviews()
    while True:
        print("\n" + "="*40)
        print("🎮 МЕНЕДЖЕР ОБЗОРОВ ИГР")
        print("="*40)
        print("1. 📝 Добавить обзор")
        print("2. 📖 Показать все обзоры")
        print("3. 🤖 Спросить ИИ об обзорах")
        print("0. 🔙 Назад")
        print("-"*40)
        
        choice = input("> ").strip()
        
        if choice == "1":
            add_review(reviews)
        elif choice == "2":
            show_reviews(reviews)
        elif choice == "3":
            ask_ai_about_reviews(reviews)
        elif choice == "0":
            break
        else:
            print("❌ Неверный ввод")

def secure_chat():
    print("\n" + "="*50)
    print("🤖 БЕЗОПАСНЫЙ ТЕКСТОВЫЙ ЧАТ")
    print("="*50)
    print("Введите 'exit' или 'выход' для выхода")
    print("-"*50)
    
    while True:
        q = input("\n👤 Вы: ").strip()
        if q.lower() in ("exit", "выход"):
            print("👋 До свидания!")
            break

        if censored(q) or check_sql(q) or check_jailbreak(q):
            print("❌ Сообщение заблокировано системой безопасности")
            continue

        cached = cache.get(q)
        if cached:
            print("🤖 ИИ (кеш):", cached)
            continue

        try:
            response = chat_model.invoke([
                SystemMessage(content="Ты безопасный и дружелюбный ИИ-ассистент. Отвечай полезно и безвредно."),
                HumanMessage(content=q)
            ])
            
            answer = response.content
            cache.set(q, answer)
            print("🤖 ИИ:", answer)
        except Exception as e:
            print(f"❌ Ошибка: {e}")

# ============================================================
# ТОЧКА ВХОДА
# ============================================================
if __name__ == "__main__":
    print("\n" + "🔷"*30)
    print("   🤖 ИИ-АССИСТЕНТ С РАСПОЗНАВАНИЕМ РЕЧИ")
    print("🔷"*30)
    
    while True:
        print("\n" + "="*50)
        print("🔥 ГЛАВНОЕ МЕНЮ")
        print("="*50)
        print("1. 🎮 Менеджер обзоров игр")
        print("2. 🤖 Безопасный текстовый чат")
        print("3. 🎤 Голосовой чат (распознавание речи)")
        print("0. ❌ Выход")
        print("-"*50)

        choice = input("> ").strip()
        
        if choice == "1":
            game_manager()
        elif choice == "2":
            secure_chat()
        elif choice == "3":
            voice_chat()
        elif choice == "0":
            print("\n👋 До свидания! Спасибо за использование!")
            break
        else:
            print("❌ Неверный выбор! Введите 0, 1, 2 или 3")