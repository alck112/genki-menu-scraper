import asyncio
import json
from playwright.async_api import async_playwright
from urllib.parse import urljoin

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        base = "https://order.genkisushi.com.hk"
        
        all_items = []
        seen = set()
        
        # 1. 自動發現所有分類
        print("搵緊分類...")
        await page.goto(f"{base}/tc/", wait_until="networkidle")
        await page.click('button:has-text("確定")').catch(lambda _: None)
        
        cats = await page.evaluate('''() => 
            [...document.querySelectorAll('a[href*=".html"]')]
                .map(a => a.getAttribute('href'))
                .filter(h => /(sushi|sashimi|roll|rice|set|side|drink|dessert|gunkan)/.test(h))
                .filter((v,i,a) => a.indexOf(v)===i)
        ''')
        
        print(f"發現 {len(cats)} 個分類: {cats}")
        
        # 2. 爬每個分類
        for cat in cats:
            url = urljoin(base, cat)
            for p_num in range(1, 10):
                try:
                    await page.goto(f"{url}?p={p_num}", wait_until="networkidle")
                    await asyncio.sleep(1.5)  # 等圖片load
                    
                    items = await page.evaluate('''() => {
                        const res = [];
                        document.querySelectorAll('.product-item, .item').forEach(el => {
                            const name = el.querySelector('h3, h4, strong')?.innerText?.trim();
                            const img = el.querySelector('img');
                            const src = img?.dataset?.src || img?.src;
                            if (name && src) res.push({name, src});
                        });
                        return res;
                    }''')
                    
                    if not items: break
                    
                    for it in items:
                        if it['name'] not in seen:
                            seen.add(it['name'])
                            # 確保係絕對URL
                            img = it['src']
                            if img.startswith('/'): img = base + img
                            all_items.append({"name": it['name'], "imgUrl": img})
                            
                except Exception as e:
                    break
        
        await browser.close()
        
        with open('menu.json', 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        print(f"完成！{len(all_items)} 個品項")

if __name__ == "__main__":
    asyncio.run(scrape())
