# GreenPlot guide

A local how-to chatbot for farmers and land owners. It answers from the module docs in `greenplot_docs/` and runs fully on [Ollama](https://ollama.com). There is no login.

Kannada is the default. English is available from the language switch, and Kannada answers include an English translation.

Architecture, database, and roadmap notes are not indexed. Password and key details are stripped before search.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

brew install ollama
ollama serve
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

python -m app.ingest
uvicorn app.main:app --port 8000
```

Open http://127.0.0.1:8000

## Chat history

Each browser keeps its own chat. Refreshing the page loads that chat from Supabase. Switching Kannada or English translates the messages already on screen and saves both languages.

1. In Supabase, open the SQL editor and run `supabase/guide_chat.sql`.
2. Copy `.env.example` to `.env`.
3. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. Keep the service role key on this machine. The page never sees it.

Restart the Python server after changing `.env`.

The chat model and embed model can be changed with `OLLAMA_CHAT_MODEL` and `OLLAMA_EMBED_MODEL`. See `.env.example`.

`qwen2.5:3b` answers in English and does not translate the conversation. The page itself is in Kannada by default. For Kannada answers and for translating the chat when the language changes, pull a larger model and point the app at it:

```bash
ollama pull qwen2.5:7b
OLLAMA_CHAT_MODEL=qwen2.5:7b uvicorn app.main:app --port 8000
```
