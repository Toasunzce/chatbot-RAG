# Telegram-бот: ReAct-агент + RAG

Telegram-бот построенный поверх **LangGraph**. Агент самостоятельно выполняет использует необходимые инструменты, обогощает ответ знаниями из web-search. Все handles выполнены асинхронными, каждый запрос к бд и вызов агента аналогично выполнены асинхронно. Пользователям предоставлена возможность создания собственной базы документов, каждая из которых изолированна от других пользователей.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-blueviolet)
![Groq](https://img.shields.io/badge/LLM-gpt--oss--120b%20(Groq)-ff69b4)
![Qdrant](https://img.shields.io/badge/VectorDB-Qdrant-DC244C)

## Возможности

| Команда | Описание |
|---|---|
| `/start` | описание и сброс истории диалога |
| `/ask <вопрос>` | вопрос агенту (можно писать просто текстом) |
| `/parse` | включить или выключить веб-поиск |
| `/rag` | загрузить документ (.txt, .md, .pdf) в личную базу знаний |

## Структура проекта

```
app/
├── main.py                  # точка входа, сборка зависимостей
├── config.py                # настройки
├── interfaces.py            # KnowledgeBase, WebSearcher
├── logging_config.py        # логи
├── bot/handlers.py          # Telegram-хендлеры
├── agent/
│   ├── graph.py             # ReAct-граф LangGraph
│   └── tools.py             # инструменты агента
└── services/
    ├── knowledge_base.py    # RAG
    └── web.py               # веб-поиск
docs/
├── architecture.puml
└── assets/architecture.png
```

## Запуск

Предварительно необходимо получить токен бота от [@BotFather](https://t.me/BotFather), а также ключ [Groq](https://console.groq.com). Конфигурация, включая LLM [gpt-oss-120b](https://console.groq.com/docs/model/openai/gpt-oss-120b) актуальна на момент 13.11.2026.

```bash
git clone https://github.com/Toasunzce/chatbot-RAG.git
cd chatbot-RAG
pip install -r requirements.txt
python -m app.main
```

## Настройки

Основные параметры лежат в `app/config.py`:

| Параметр | По умолчанию | Описание |
|---|---|---|
| `LLM_MODEL` | `openai/gpt-oss-120b` | модель Groq с поддержкой tool calling |
| `EMBEDDING_MODEL` | `ai-forever/ru-en-RoSBERTa` | модель эмбеддингов |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 300 / 50 | нарезка документов |
| `TOP_K` | 5 | сколько фрагментов отдавать агенту |
| `MAX_HISTORY` | 20 | сколько сообщений помнит агент |
| `LOG_LEVEL` | `INFO` | `DEBUG` для подробных логов (переменная окружения) |

## Roadmap

- Reranker и фильтрация по relevance score
- Хранение истории и настроек в SQLite/Redis вместо памяти процесса
- Docker
- Mini-app