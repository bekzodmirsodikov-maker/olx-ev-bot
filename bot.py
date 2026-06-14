import os,json,logging,asyncio,requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime

BOT_TOKEN="8787485914:AAGBTT31iLZg62oycB-L426uw4sWyP_3prg"
CHANNEL_ID="@electromobiluzb"
CHECK_INTERVAL=60
SEEN_FILE="seen_ads.json"

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s",handlers=[logging.StreamHandler()])
log=logging.getLogger(__name__)

HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":"ru-RU,ru;q=0.9,uz;q=0.8",
}

URL="https://www.avtoelon.uz/cars/?fuel=electric"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE,"r",encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE,"w",encoding="utf-8") as f:
        json.dump(list(seen),f,ensure_ascii=False)

def fetch_ads():
    ads=[]
    try:
        r=requests.get(URL,headers=HEADERS,timeout=30)
        log.info(f"Status: {r.status_code}")
        if r.status_code!=200:
            log.error(f"Xato: {r.status_code}")
            return ads
        soup=BeautifulSoup(r.text,"html.parser")
        cards=soup.select("div.item-card, div.car-item, article.listing, div[class*='card'], li[class*='item']")
        log.info(f"Kartochkalar: {len(cards)}")
        for card in cards:
            try:
                title_t=card.select_one("h2,h3,h4,a[class*='title'],[class*='name']")
                title=title_t.get_text(strip=True) if title_t else ""
                if not title:
                    continue
                link_t=card.select_one("a[href]")
                href=link_t["href"] if link_t else ""
                if not href:
                    continue
                link=href if href.startswith("http") else "https://www.avtoelon.uz"+href
                ad_id=href.rstrip("/").split("/")[-1]
                price_t=card.select_one("[class*='price'],[class*='cost']")
                price=price_t.get_text(strip=True) if price_t else "Narx ko'rsatilmagan"
                img_t=card.select_one("img[src]")
                image=img_t["src"] if img_t else ""
                if image and image.startswith("//"):
                    image="https:"+image
                loc_t=card.select_one("[class*='location'],[class*='city'],[class*='region']")
                location=loc_t.get_text(strip=True) if loc_t else ""
                if ad_id:
                    ads.append({"id":ad_id,"title":title,"price":price,
                                "link":link,"image":image,"location":location})
            except Exception as e:
                log.warning(f"Parse xato: {e}")
        log.info(f"E'lonlar: {len(ads)} ta")
    except Exception as e:
        log.error(f"Fetch xato: {e}")
    return ads

def caption(ad):
    lines=["⚡️ *ELEKTROMOBIL E'LONI*","",f"🚗 *{ad['title']}*",f"💰 *Narx:* {ad['price']}"]
    if ad.get("location"):lines.append(f"📍 *Joylashuv:* {ad['location']}")
    lines+=["",f"🔗 [E'lonni ko'rish]({ad['link']})"]
    return "\n".join(lines)

async def send_ad(bot,ad):
    txt=caption(ad)
    try:
        if ad.get("image"):
            try:
                await bot.send_photo(chat_id=CHANNEL_ID,photo=ad["image"],caption=txt,parse_mode="Markdown")
            except:
                await bot.send_message(chat_id=CHANNEL_ID,text=txt,parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=CHANNEL_ID,text=txt,parse_mode="Markdown")
        log.info(f"✅ {ad['title']}")
        await asyncio.sleep(4)
    except TelegramError as e:
        log.error(f"❌ {e}")

async def main():
    bot=Bot(token=BOT_TOKEN)
    me=await bot.get_me()
    log.info(f"🤖 @{me.username}")
    seen=load_seen()
    log.info(f"Ko'rilgan: {len(seen)} ta")
    while True:
        log.info("🔍 Avtoelon.uz tekshirilmoqda...")
        ads=fetch_ads()
        new=[a for a in ads if a["id"] not in seen]
        log.info(f"🆕 Yangi: {len(new)} ta")
        for ad in new:
            await send_ad(bot,ad)
            seen.add(ad["id"])
            save_seen(seen)
        log.info(f"⏰ 1 daqiqadan keyin...")
        await asyncio.sleep(CHECK_INTERVAL)

if __name__=="__main__":
    asyncio.run(main())
