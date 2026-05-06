    #  ИИ-Ассистент с распознаванием речи

Проект представляет собой интеллектуального ассистента с возможностью голосового управления. Разработан в рамках изучения технологий искусственного интеллекта.

## Функциональность

-  Распознавание речи - преобразование голоса в текст через микрофон
-  Общение с ИИ - локальная нейросеть через LM Studio
-  Менеджер обзоров игр - добавление, просмотр и анализ отзывов на игры
- Безопасный чат - защита от вредоносных запросов и цензура
- Кеширование ответов - быстрый доступ к повторяющимся вопросам

## Технологии

- **Python 3.13.4** - основной язык программирования
- **LM Studio** - локальный сервер для запуска LLM
- **LangChain** - фреймворк для работы с LLM
- **SpeechRecognition + sounddevice** - распознавание речи
- **SQLite** - кеширование ответов

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-username/speech-ai-assistant.git
cd BOT_SPEECH


# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate


pip install -r requirements.txt



4. Установка LM Studio

    Скачайте LM Studio с официального сайта

    Установите и запустите программу

    Скачайте любую модель (рекомендуется: qwen2.5-coder-3b-instruct или llama-3.2-3b)

    Запустите локальный сервер на порту 1234:

        Нажмите "Start Server" в LM Studio

        Убедитесь, что в настройках указан порт 1234

        Адрес сервера: http://localhost:1234

5. Настройка микрофона
bash

# Windows: проверьте доступность микрофона в системе
# Linux: 
sudo apt-get install portaudio19-dev

# Mac:
brew install portaudio

# Использование
Запуск программы
bash

python main.py

Главное меню


1. 🎮 Менеджер обзоров игр
2. 🤖 Безопасный текстовый чат
3. 🎤 Голосовой чат (распознавание речи)
0. ❌ Выход


#Установка одной командой windows:
pip install langchain-core langchain-openai speechrecognition sounddevice numpy



#Linux/Mac
pip3 install langchain-core langchain-openai speechrecognition sounddevice numpy


Если возникают ошибки прописать пошагово каждую команду:

pip install --upgrade pip

# Шаг 2: Установка LangChain
pip install langchain-core
pip install langchain-openai

# Шаг 3: Установка для распознавания речи
pip install speechrecognition
pip install sounddevice
pip install numpy

# Шаг 4: Проверка установки
python -c "import langchain_core; import langchain_openai; import speech_recognition; import sounddevice; import numpy; print('✅ Все библиотеки установлены успешно!')"