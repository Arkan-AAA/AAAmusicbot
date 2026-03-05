# 🎵 Telegram Music Bot

Скачивает музыку по ссылке или названию. Поддерживает YouTube, TikTok, Instagram,
VK, SoundCloud, Spotify и другие. Для TikTok/Instagram распознаёт трек через Shazam
и находит полную версию.

---

## Деплой на Railway

### 1. Создать бота
1. Открой [@BotFather](https://t.me/BotFather) → `/newbot`
2. Скопируй токен

### 2. Загрузить код
```bash
git init
git add .
git commit -m "init"
```

Создай репо на GitHub и запушь:
```bash
git remote add origin https://github.com/YOU/music-bot.git
git push -u origin main
```

### 3. Задеплоить на Railway
1. Зайди на [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Выбери репозиторий
3. Перейди в **Variables** и добавь:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | `123456:ABC-токен_от_BotFather` |

4. Railway автоматически соберёт Docker-образ и запустит бота.

---

## Локальный запуск

```bash
# установить зависимости
pip install -r requirements.txt

# установить ffmpeg (Ubuntu/Debian)
sudo apt install ffmpeg

# запустить
BOT_TOKEN=ВАШ_ТОКЕН python bot.py
```

---

## Поддерживаемые платформы

| Платформа | Ссылка | Поиск + Shazam |
|-----------|--------|----------------|
| YouTube   | ✅     | ✅             |
| TikTok    | ✅     | ✅ (Shazam)    |
| Instagram | ✅     | ✅ (Shazam)    |
| VK        | ✅     | —              |
| SoundCloud| ✅     | —              |
| Twitter/X | ✅     | ✅ (Shazam)    |
| Facebook  | ✅     | ✅ (Shazam)    |
| OK.ru     | ✅     | —              |
| Bandcamp  | ✅     | —              |
| Dailymotion | ✅   | —              |

Поиск по названию работает через **YouTube Music** — поддерживает русские,
казахские, английские и другие языки.

---

## Cookies (опционально)

Если yt-dlp не может скачать из-за ограничений (возраст, геоблок):

1. Установи расширение [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/)
2. Экспортируй cookies для нужного сайта
3. Положи файл рядом с ботом как `cookies.txt`

---

## Структура проекта

```
music_bot/
├── bot.py           # Telegram-бот, все хендлеры
├── downloader.py    # yt-dlp + YouTube Music поиск
├── shazam_client.py # Распознавание треков (shazamio)
├── requirements.txt
├── Dockerfile
├── railway.toml
└── .gitignore
```
