# 🎵 Telegram Music Bot

Продвинутый музыкальный бот для Telegram с поддержкой множества платформ и автоматическим распознаванием треков через Shazam.

## ✨ Возможности

- 🔗 **Скачивание по ссылке** — YouTube, TikTok, Instagram, VK, SoundCloud, Spotify и другие
- 🔍 **Поиск по названию** — на любом языке через YouTube Music
- 🎧 **Shazam интеграция** — автоматическое распознавание треков из TikTok/Instagram и поиск полной версии
- ⚡ **Стабильная работа** — rate limiting, таймауты, автоочистка памяти

## 📋 Поддерживаемые платформы

| Платформа | Ссылка | Поиск | Shazam |
|-----------|--------|-------|--------|
| YouTube   | ✅     | ✅    | —      |
| TikTok    | ✅     | —     | ✅     |
| Instagram | ✅     | —     | ✅     |
| VK        | ✅     | —     | —      |
| SoundCloud| ✅     | —     | —      |
| Twitter/X | ✅     | —     | ✅     |
| Facebook  | ✅     | —     | ✅     |
| Spotify   | ✅     | —     | —      |
| Bandcamp  | ✅     | —     | —      |
| OK.ru     | ✅     | —     | —      |
| Dailymotion | ✅   | —     | —      |

## 🛡️ Защита и стабильность

- **Rate limiting** — 5 запросов в минуту на пользователя
- **Таймауты** — 120 секунд на операцию (защита от зависаний)
- **Проверка размера** — отклонение файлов >50 МБ (лимит Telegram)
- **Автоочистка памяти** — результаты поиска удаляются через 10 минут
- **Graceful error handling** — понятные сообщения об ошибках

## 📁 Структура проекта

```
AAAmusicbot/
├── bot.py              # Основной файл бота
├── downloader.py       # Логика скачивания (yt-dlp + ytmusicapi)
├── shazam_client.py    # Распознавание треков через Shazam
├── requirements.txt    # Python зависимости
├── Dockerfile          # Docker конфигурация
├── railway.toml        # Railway конфигурация
├── .gitignore
└── README.md
```

## 🔧 Технологии

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — Telegram Bot API
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — Скачивание медиа
- [ytmusicapi](https://github.com/sigma67/ytmusicapi) — Поиск музыки
- [shazamio](https://github.com/dotX12/ShazamIO) — Распознавание треков
- [ffmpeg](https://ffmpeg.org/) — Конвертация аудио
