import os,json,logging,asyncio,requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime

BOT_TOKEN="8787485914:AAGBTT31iLZg62oycB-L426uw4sWyP_3prg"
CHANNEL_ID="@electromobiluzb"
CHECK_INTERVAL=600
SEEN_FILE="seen_ads.json"

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s",handlers=[logging.FileHandler("bot.log",encoding="utf-8"),logging.StreamHandler()])
log=logging.getLogger(__name__)

OLX_API="https://www.olx.uz/api/v1/offers/?offset=0&limit=40&filter_enum_fuel_type%5B0%5D=electric&category_id=108&sort_by=created_at%3Adesc"
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0","Accept":"application/json","Referer":"https://www.olx.uz/"}

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
        r=requests.get(OLX_API,headers=HEADERS,timeout=20)
        r.raise_for_status()
        for o in r.json().get("data",[]):
            try:
                ad_id=str(o.get("id",""))
                title=o.get("title","Noma'lum")
                price=(o.get("price",{})or{}).get("display_value","Narx yo'q")
                link=o.get("url","")
                if link and not link.startswith("http"):link="https://www.olx.uz"+link
                photos=o.get("photos",[])or[]
                image=photos[0].get("link","").replace("{width}","600") if photos else ""
                loc=o.get("location",{})or{}
                location=(loc.get("city",{})or{}).get("name","")\
                    or(loc.get("region",{})or{}).get("name","")
                created=o.get("created_time","")
                try:
                    date_str=datetime.fromisoformat(created.replace("Z","+00:00")).strftime("%d.%m.%Y %H:%M")
                except:
                    date_str=created[:10]
                params={}
                for p in o.get("params",[])or[]:
                    k=p.get("key","");v=(p.get("value",{})or{})
                    lbl=v.get("label")or v.get("key","")
                    if k and lbl:params[k]=lbl
                if ad_id:
                    ads.append({"id":ad_id,"title":title,"price":price,"link":link,"image":image,"location":location,"date":date_str,"params":params})
            except Exception as e:
                log.warning(f"E'lon xato: {e}")
    except Exception as e:
        log.error(f"API xato: {e}")
    return ads

def caption(ad):
    p=ad.get("params",{})or{}
    lines=["⚡️ *ELEKTROMOBIL E'LONI*","",f"🚗 *{ad['title']}*",f"💰 *Narx:* {ad['price']}"]
    if p.get("year"):lines.append(f"📆 *Yil:* {p['year']}")
    if p.get("mileage"):lines.append(f"🛣 *Yurish:* {p['mileage']}")
    if p.get("color"):lines.append(f"🎨 *Rang:* {p['color']}")
    if ad.get("location"):lines.append(f"📍 *Joylashuv:* {ad['location']}")
    if ad.get("date"):lines.append(f"📅 *Sana:* {ad['date']}")
    lines+=["",f"🔗 [E'lonni ko'rish]({ad['link']})"]
    return "\n".join(lines)

async def send_ad(bot,ad):
    txt=caption(ad)
    try:
        if ad.get("image"):
            try:await bot.send_photo(chat_id=CHANNEL_ID,photo=ad["image"],caption=txt,parse_mode="Markdown")
            except:await bot.send_message(chat_id=CHANNEL_ID,text=txt,parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=CHANNEL_ID,text=txt,parse_mode="Markdown")
        log.info(f"✅ {ad['title']}")
        await asyncio.sleep(4)
    except TelegramError as e:
        log.error(f"❌ {e}")

async def main():
    bot=Bot(token=BOT_TOKEN)
    me=await bot.get_me()
    log.info(f"🤖 Bot: @{me.username}")
    seen=load_seen()
    while True:
        log.info("🔍 OLX tekshirilmoqda...")
        ads=fetch_ads()
        new=[a for a in ads if a["id"] not in seen]
        log.info(f"🆕 Yangi: {len(new)} ta")
        for ad in new:
            await send_ad(bot,ad)
            seen.add(ad["id"])
            save_seen(seen)
        log.info("⏰ 10 daqiqadan keyin...")
        await asyncio.sleep(CHECK_INTERVAL)

if __name__=="__main__":
    asyncio.run(main())