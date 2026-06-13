import os,json,logging,asyncio,requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime

BOT_TOKEN="8787485914:AAGBTT31iLZg62oycB-L426uw4sWyP_3prg"
CHANNEL_ID="@electromobiluzb"
CHECK_INTERVAL=600
SEEN_FILE="seen_ads.json"

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s",handlers=[logging.StreamHandler()])
log=logging.getLogger(__name__)

EV_BRANDS=["tesla","byd","nio","zeekr","xpeng","avatr","enovate","voyah","leapmotor","aito","denza","deepal","lynk","ora","hongqi","lixiang","wuling","jaecoo","omoda"]

HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":"ru-RU,ru;q=0.9",
    "Connection":"keep-alive",
}

SEARCH_URLS=[
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=tesla",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=byd",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=zeekr",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=xpeng",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=nio",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=leapmotor",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=lixiang",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=voyah",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=avatr",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=aito",
    "https://www.olx.uz/transport/legkovye-avtomobili/?search[filter_enum_make][0]=denza",
]

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE,"r",encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE,"w",encoding="utf-8") as f:
        json.dump(list(seen),f,ensure_ascii=False)

def is_ev(title):
    return any(b in title.lower() for b in EV_BRANDS)

def parse_card(card):
    try:
        title_t=card.select_one("h4,h3,[data-cy='ad-title']")
        title=title_t.get_text(strip=True) if title_t else ""
        if not title or not is_ev(title):
            return None
        link_t=card.select_one("a[href]")
        href=link_t["href"] if link_t else ""
        link=href if href.startswith("http") else "https://www.olx.uz"+href
        ad_id=link.rstrip("/").split("-")[-1]
        price_t=card.select_one("[data-testid='ad-price'],[class*='price']")
        price=price_t.get_text(strip=True) if price_t else "Narx ko'rsatilmagan"
        img_t=card.select_one("img[src]")
        image=img_t["src"] if img_t else ""
        if image.startswith("//"):
            image="https:"+image
        loc_t=card.select_one("[class*='location'],[data-testid='location-date']")
        location=loc_t.get_text(strip=True) if loc_t else ""
        return {"id":ad_id,"title":title,"price":price,"link":link,"image":image,"location":location,"date":""}
    except:
        return None

def fetch_page(url):
    ads=[]
    try:
        r=requests.get(url,headers=HEADERS,timeout=30)
        log.info(f"Status {r.status_code}: {url[-40:]}")
        if r.status_code!=200:
            return ads
        soup=BeautifulSoup(r.text,"html.parser")
        cards=soup.select("div[data-cy='l-card'],div[class*='listing-grid-item']")
        log.info(f"Kartochkalar: {len(cards)}")
        for card in cards:
            ad=parse_card(card)
            if ad:
                ads.append(ad)
    except Exception as e:
        log.error(f"Fetch xato: {e}")
    return ads

def fetch_ads():
    all_ads=[]
    seen_ids=set()
    for url in SEARCH_URLS:
        for ad in fetch_page(url):
            if ad["id"] not in seen_ids:
                seen_ids.add(ad["id"])
                all_ads.append(ad)
    log.info(f"Jami: {len(all_ads)} ta elektromobil")
    return all_ads

def caption(ad):
    lines=["⚡️ *ELEKTROMOBIL E'LONI*","",f"🚗 *{ad['title']}*",f"💰 *Narx:* {ad['price']}"]
    if ad.get("location"):lines.append(f"📍 *{ad['location']}*")
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
        log.info("🔍 OLX tekshirilmoqda...")
        ads=fetch_ads()
        new=[a for a in ads if a["id"] not in seen]
        log.info(f"🆕 Yangi: {len(new)} ta")
        for ad in new:
            await send_ad(bot,ad)
            seen.add(ad["id"])
            save_seen(seen)
        log.info(f"⏰ {CHECK_INTERVAL//60} daqiqadan keyin...")
        await asyncio.sleep(CHECK_INTERVAL)

if __name__=="__main__":
    asyncio.run(main())
