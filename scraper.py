import asyncio
import json
from playwright.async_api import async_playwright

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        base = "https://order.genkisushi.com.hk"
        all_items = []
        seen = set()
        
        # Step 1: 去主頁搵分類
        print("🔍 去主頁搵分類...")
        await page.goto(f"{base}/tc/", wait_until="networkidle")
        
        try:
            await page.click('button:has-text("確定")', timeout=3000)
            await asyncio.sleep(2)
        except:
            pass
        
        # 等多陣等 menu 生成
        await asyncio.sleep(5)
        
        # 檢查有幾多個 <a> tag
        link_count = await page.evaluate('() => document.querySelectorAll("a").length')
        print(f"  頁面有 {link_count} 個連結")
        
        # 試搵所有包含 /tc/ 嘅 href
        all_links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a'))
                .map(a => a.getAttribute('href'))
                .filter(h => h && h.includes('/tc/'));
        }''')
        print(f"  其中 {len(all_links)} 個包含 /tc/")
        print(f"  例子: {all_links[:10]}")  # 顯示頭10個
        
        # 正規篩選
        categories = [h for h in all_links if h and h.endswith('.html') and 'privacy' not in h and 'terms' not in h]
        categories = list(set(categories))  # 去重
        
        print(f"\n✅ 篩選後: {categories}")
        
        # 如果都係空，fallback
        if not categories:
            print("⚠️ 自動搵唔到，用後備")
            categories = ['/tc/sushi.html', '/tc/sashimi.html', '/tc/gunkan.html']
        
        # Step 2: 爬每個分類（同之前一樣）
        for cat in categories:
            print(f"\n📂 {cat}")
            # ...（後面同之前一樣）
            p_num = 1
            while p_num <= 10:
                url = f"{base}{cat}" if p_num == 1 else f"{base}{cat}?p={p_num}"
                try:
                    await page.goto(url, wait_until="networkidle", timeout=15000)
                    await asyncio.sleep(2)
                    
                    items = await page.evaluate('''() => {
                        const res = [];
                        document.querySelectorAll('.product-item, .item').forEach(el => {
                            const name = el.querySelector('h3, h4')?.innerText?.trim();
                            const img = el.querySelector('img');
                            let src = img?.dataset?.src || img?.src;
                            if (name && src) {
                                if (src.startsWith('/')) src = 'https://order.genkisushi.com.hk' + src;
                                res.push({name, imgUrl: src});
                            }
                        });
                        return res;
                    }''')
                    
                    if not items:
                        break
                    
                    new = sum(1 for it in items if it['name'] not in seen)
                    for it in items:
                        if it['name'] not in seen:
                            seen.add(it['name'])
                            all_items.append(it)
                    
                    print(f"  第{p_num}頁: +{new}項 (共{len(all_items)})")
                    
                    if new == 0:
                        break
                    p_num += 1
                    
                except Exception as e:
                    print(f"  錯誤: {e}")
                    break
        
        await browser.close()
        
        with open('menu.json', 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        print(f"\n🎉 完成！{len(all_items)} 項")

if __name__ == "__main__":
    asyncio.run(scrape())
