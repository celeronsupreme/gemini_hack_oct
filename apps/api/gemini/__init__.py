"""Everything that talks to Gemini lives here, behind mock-capable functions.

- live.py      ephemeral tokens, the voice agent's system prompt and tool declarations
- tools.py     handlers for the four tools the Live session can call (they write to the store)
- extract.py   transcript -> DiaryEntryBatch with a JSON schema (gemini-3.8-flash)
- analysis.py  questions over the diary with code execution (gemini-4-argon, fallback gemini-3.8-flash)
- wording.py   plain-language rewrites of engine output (optional; engine text is the fallback)

With no GEMINI_API_KEY every function returns a labelled mock so the whole app runs offline.
"""
