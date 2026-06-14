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

EV_BRANDS=["tesla","byd","nio","zeekr","xpeng","avatr","enovate","voyah","leapmotor","aito","denza","deepal","lynk","ora","li auto","lixiang"]

BASE_URL="https://www.olx.uz/api/v1/offers/?offset=0&limit=50&category_id=108&sort_by=created_at%3Adesc"
HEADERS={
    "User-Agent":"Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept":"application/json",
    "Accept-Language":"ru-RU,ru;q=0.9",
    "Origin":"https://www.olx.uz",
    "Referer":"https://www.olx.uz/transport/legkovye-avtomobili/",
}
HTML_HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":"ru-RU,ru;q=0.9",
}

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE,"r",encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE,"w",encoding="utf-8") as f:
        json.dump(list(seen),f,ensure_ascii=False)

def is_ev(title):
    return any(brand in title.lower() for brand in EV_BRANDS)

def get_price_from_page(link):
    try:
        r=requests.get(link,headers=HTML_HEADERS,timeout=15)
        if r.status_code!=200:
            return "Narx ko'rsatilmagan"
        soup=BeautifulSoup(r.text,"html.parser")
        price_tag=soup.select_one("[data-testid='ad-price-container'], [class*='price'], strong[class*='price']")
        if price_tag:
            return price_tag.get_text(strip=True)
        return "Narx ko'rsatilmagan"
    except:
        return "Narx ko'rsatilmagan"

def fetch_ads():
    ads=[]
    try:
        r=requests.get(BASE_URL,headers=HEADERS,timeout=30)
        log.info(f"OLX status: {r.status_code}")
        if r.status_code!=200:
            log.error(f"OLX xato: {r.status_code}")
            return ads
        data=r.json().get("data",[])
        log.info(f"Jami e'lonlar: {len(data)}")
        for o in data:
            try:
                title=o.get("title","")
                if not is_ev(title):
                    continue
                ad_id=str(o.get("id",""))
                link=o.get("url","")
                if link and not link.startswith("http"):
                    link="https://www.olx.uz"+link
                photos=o.get("photos",[])or[]
                image=""
                if photos:
                    img=photos[0]
                    image=img.get("link","")or img.get("url","")
                    image=image.replace("{width}","600")
                loc=o.get("location",{})or{}
                city=(loc.get("city",{})or{}).get("name","")
                region=(loc.get("region",{})or{}).get("name","")
                location=city or region
                created=o.get("created_time","")
                try:
                    dt=datetime.fromisoformat(created.replace("Z","+00:00"))
                    date_str=dt.strftime("%d.%m.%Y %H:%M")
                except:
                    date_str=created[:10] if created else ""
                params={}
                for p in o.get("params",[])or[]:
                    k=p.get("key","")
                    v=(p.get("value",{})or{})
                    lbl=v.get("label")or v.get("key","")
                    if k and lbl:params[k]=lbl
                if ad_id:
                    ads.append({"id":ad_id,"title":title,"link":link,
                                "image":image,"location":location,"date":date_str,"params":params})
            except Exception as e:
                log.warning(f"Parse xato: {e}")
        log.info(f"Elektromobillar: {len(ads)} ta")
    except Exception as e:
        log.error(f"Fetch xato: {e}")
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
            try:
                await bot.send_photo(chat_id=CHANNEL_ID,photo=ad["image"],caption=txt,parse_mode="Markdown")
            except:
                await bot.send_message(chat_id=CHANNEL_ID,text=txt,parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=CHANNEL_ID,text=txt,parse_mode="Markdown")
        log.info(f"✅ {ad['title']} | {ad['price']}")
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
            log.info(f"Narx o'qilmoqda: {ad['link']}")
            price=get_price_from_page(ad["link"])
            ad["price"]=price
            await send_ad(bot,ad)
            seen.add(ad["id"])
            save_seen(seen)
        log.info(f"⏰ 1 daqiqadan keyin...")
        await asyncio.sleep(CHECK_INTERVAL)

if __name__=="__main__":
    asyncio.run(main())
