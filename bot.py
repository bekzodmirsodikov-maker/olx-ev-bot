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

PAGES=[
    "https://www.olx.uz/transport/legkovye-avtomobili/q-tesla/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-byd/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-zeekr/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-xpeng/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-nio/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-leapmotor/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-lixiang/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-voyah/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-avatr/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-aito/",
    "https://www.olx.uz/transport/legkovye-avtomobili/q-denza/",
]

HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":"ru-RU,ru;q=0.9,uz;q=0.8",
}

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE,"r",encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE,"w",encoding="utf-8") as f:
        json.dump(list(seen),f,ensure_ascii=False)

def get_price(o):
    p=o.get("price",None)
    if p is None:
        return "Narx ko'rsatilmagan"
    if isinstance(p,str):
        return p if p else "Narx ko'rsatilmagan"
    if isinstance(p,dict):
        val=p.get("displayValue") or p.get("regularPrice",{}).get("value","") or p.get("value","")
        cur=p.get("currency","")
        if val:
            return f"{val} {cur}".strip()
    return "Narx ko'rsatilmagan"

def fetch_page(url):
    ads=[]
    try:
        r=requests.get(url,headers=HEADERS,timeout=30)
        if r.status_code!=200:
            return ads
        soup=BeautifulSoup(r.text,"html.parser")
        script=soup.find("script",{"id":"__NEXT_DATA__"})
        if not script:
            return ads
        data=json.loads(script.string)
        offers=(data.get("props",{}).get("pageProps",{})
                .get("ads",{}).get("ads",[]))
        for o in offers:
            try:
                title=o.get("title","")
                ad_id=str(o.get("id",""))
                price=get_price(o)
                link=o.get("url","")
                if link and not link.startswith("http"):
                    link="https://www.olx.uz"+link
                photos=o.get("photos",[])or[]
                image=""
                if photos:
                    if isinstance(photos[0],str):
                        image=photos[0]
                    elif isinstance(photos[0],dict):
                        image=photos[0].get("link","")or photos[0].get("url","")
                loc=o.get("location","")
                if isinstance(loc,dict):
                    location=loc.get("cityName","")or loc.get("regionName","")
                else:
                    location=str(loc)
                created=o.get("createdTime","")or o.get("created_time","")
                try:
                    dt=datetime.fromisoformat(str(created).replace("Z","+00:00"))
                    date_str=dt.strftime("%d.%m.%Y %H:%M")
                except:
                    date_str=str(created)[:10] if created else ""
                if ad_id:
                    ads.append({"id":ad_id,"title":title,"price":price,"link":link,
                                "image":image,"location":location,"date":date_str})
            except Exception as e:
                log.warning(f"Parse xato: {e}")
    except Exception as e:
        log.error(f"Sahifa xato {url}: {e}")
    return ads

def fetch_ads():
    all_ads=[]
    seen_ids=set()
    for url in PAGES:
        ads=fetch_page(url)
        for ad in ads:
            if ad["id"] not in seen_ids:
                seen_ids.add(ad["id"])
                all_ads.append(ad)
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0))
    log.info(f"Jami elektromobillar: {len(all_ads)} ta")
    return all_ads

def caption(ad):
    lines=["⚡️ *ELEKTROMOBIL E'LONI*","",f"🚗 *{ad['title']}*",f"💰 *Narx:* {ad['price']}"]
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
        log.info(f"✅ Yuborildi: {ad['title']}")
        await asyncio.sleep(4)
    except TelegramError as e:
        log.error(f"❌ {e}")

async def main():
    bot=Bot(token=BOT_TOKEN)
    me=await bot.get_me()
    log.info(f"🤖 Bot: @{me.username}")
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
