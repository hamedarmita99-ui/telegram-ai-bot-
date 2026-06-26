import os
import asyncio
import logging
from datetime import datetime
import anthropic
import httpx
from telegram import Bot
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Config ────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID       = os.environ["TELEGRAM_CHANNEL_ID"]   # e.g. @YourChannel or -100xxxxxxxxx
ANTHROPIC_KEY    = os.environ["ANTHROPIC_API_KEY"]

bot    = Bot(token=TELEGRAM_TOKEN)
client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ─── AI News Fetcher ────────────────────────────────────────
async def fetch_ai_news() -> list[dict]:
    """Fetch latest AI news headlines via web search through Claude."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": (
                "Search for the 3 most important AI news stories from the last 24 hours. "
                "Return ONLY a JSON array with this exact format, no extra text:\n"
                '[{"title":"...","summary":"...","source":"..."}]'
            )
        }]
    )

    # Extract text from response blocks
    full_text = ""
    for block in message.content:
        if hasattr(block, "text"):
            full_text += block.text

    import json, re
    match = re.search(r'\[.*\]', full_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return []


# ─── Prompt Generator ───────────────────────────────────────
def generate_prompt_pack() -> list[dict]:
    """Generate 3 premium AI prompts in Persian using Claude."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": (
                "Generate 3 unique, high-quality AI prompts in Persian (Farsi) for a Telegram channel. "
                "Topics: marketing copy, productivity, or creative writing. "
                "Return ONLY a JSON array, no extra text:\n"
                '[{"category":"دسته‌بندی","title":"عنوان","prompt":"متن پرامپت کامل به فارسی"}]'
            )
        }]
    )

    import json, re
    text = message.content[0].text
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return []


# ─── Message Formatters ─────────────────────────────────────
def format_news_post(news_items: list[dict]) -> str:
    today = datetime.now().strftime("%d %B %Y")
    lines = [f"🤖 *اخبار هوش مصنوعی امروز*\n📅 {today}\n"]
    for i, item in enumerate(news_items, 1):
        lines.append(
            f"*{i}\\. {escape(item.get('title',''))}*\n"
            f"{escape(item.get('summary',''))}\n"
            f"📌 منبع: {escape(item.get('source',''))}\n"
        )
    lines.append("━━━━━━━━━━━━━━━━━━\n🔔 کانال ما رو به دوستات معرفی کن\\!")
    return "\n".join(lines)


def format_prompt_post(prompts: list[dict]) -> str:
    today = datetime.now().strftime("%d %B %Y")
    lines = [f"✨ *پرامپت‌های ویژه امروز*\n📅 {today}\n"]
    for i, p in enumerate(prompts, 1):
        lines.append(
            f"*{i}\\. {escape(p.get('title',''))}*\n"
            f"🏷 دسته: {escape(p.get('category',''))}\n\n"
            f"```\n{p.get('prompt','')}\n```\n"
        )
    lines.append("━━━━━━━━━━━━━━━━━━\n💡 برای پرامپت‌های بیشتر @PromptTradePro رو دنبال کن\\!")
    return "\n".join(lines)


def escape(text: str) -> str:
    """Escape MarkdownV2 special chars."""
    for ch in r'\_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text


# ─── Post Functions ─────────────────────────────────────────
async def post_ai_news():
    logger.info("Fetching AI news...")
    news = await fetch_ai_news()
    if not news:
        logger.warning("No news fetched.")
        return
    text = format_news_post(news)
    await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.MARKDOWN_V2)
    logger.info("✅ News posted.")


async def post_prompts():
    logger.info("Generating prompts...")
    prompts = generate_prompt_pack()
    if not prompts:
        logger.warning("No prompts generated.")
        return
    text = format_prompt_post(prompts)
    await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.MARKDOWN_V2)
    logger.info("✅ Prompts posted.")


# ─── Scheduler ──────────────────────────────────────────────
async def scheduler():
    """
    Schedule:
      08:00 → AI News
      14:00 → Prompts
      20:00 → AI News (evening)
    """
    logger.info("Scheduler started...")
    while True:
        now = datetime.now()
        hour = now.hour
        minute = now.minute

        if minute == 0:
            if hour == 8:
                await post_ai_news()
            elif hour == 14:
                await post_prompts()
            elif hour == 20:
                await post_ai_news()

        await asyncio.sleep(60)  # check every minute


# ─── Entry Point ────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "news":
            asyncio.run(post_ai_news())
        elif cmd == "prompts":
            asyncio.run(post_prompts())
        else:
            print("Usage: python bot.py [news|prompts]")
    else:
        # Run scheduler
        asyncio.run(scheduler())
