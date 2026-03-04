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
        
        # 方法1：自動發現（試下先）
        print("🔍 嘗試自動發現分類...")
        try:
            await page.goto(f"{base}/tc/", wait_until="networkidle", timeout=15000)
            
            # 處理 cookie
            try:
                await page.click('button:has-text("確定")', timeout=3000)
                await asyncio.sleep(2)
            except:
                pass
            
            # 等多陣等 JavaScript 加載選單
            await asyncio.sleep(3)
            
            # 搵所有可能嘅分類連結（寬鬆版）
            categories = await page.evaluate('''() => {
                const found = new Set();
                
                // 方法A：搵所有包含分類關鍵字嘅連結
                document.querySelectorAll('a').forEach(a => {
                    const href = a.getAttribute('href') || '';
                    if (href.includes('sushi') || href.includes('sashimi') || 
                        href.includes('roll') || href.includes('rice') ||
                        href.includes('set') || href.includes('side') ||
                        href.includes('drink') || href.includes('dessert')) {
                        if (href.includes('.html')) found.add(href);
                    }
                });
                
                return Array.from(found);
            }''')
            
            # 如果搵到，清理成標準格式
            if categories and len(categories) > 0:
                # 確保係絕對路徑 /tc/xxx.html
                categories = list(set([
                    c if c.startswith('/tc/') else f'/tc/{c}'
                    for c in categories
                ]))
                print(f"✅ 自動發現: {categories}")
            else:
                categories = []
                
        except Exception as e:
            print(f"❌ 自動發現失敗: {e}")
            categories = []
        
        # 方法2：如果自動搵唔到，用手動列表（fallback）
        if not categories:
            print("⚠️ 改用預設分類列表")
            categories = [
                '/tc/sushi.html',
                '/tc/sashimi.html',
                '/tc/roll.html',
                '/tc/rice.html',
                '/tc/set.html',
                '/tc/side.html',
                '/tc/dessert.html',
                '/tc/drink.html'
            ]
        
        print(f"\n總共處理 {len(categories)} 個分類")
        
        # Step 2: 爬每個分類
        for cat in categories:
            print(f"\n📂 {cat}")
            
            for p_num in range(1, 15):
                # 第1頁冇 ?p=，之後有
                url = f"{base}{cat}" if p_num == 1 else f"{base}{cat}?p={p_num}"
                
                try:
                    await page.goto(url, wait_until="networkidle", timeout=20000)
                    await asyncio.sleep(2)
                    
                    items = await page.evaluate('''() => {
                        const res = [];
                        document.querySelectorAll('.product-item, .item, [class*="product"]').forEach(el => {
                            const name = el.querySelector('h3, h4, strong')?.innerText?.trim();
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
                        print(f"  第{p_num}頁完")
                        break
                    
                    new = sum(1 for it in items if it['name'] not in seen)
                    for it in items:
                        if it['name'] not in seen:
                            seen.add(it['name'])
                            all_items.append(it)
                    
                    print(f"  第{p_num}頁: +{new}項 (共{len(all_items)})")
                    
                    if new == 0 and p_num > 1:
                        break
                        
                except Exception as e:
                    print(f"  錯誤: {e}")
                    break
        
        await browser.close()
        
        with open('menu.json', 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        print(f"\n🎉 完成！{len(all_items)} 項")

if __name__ == "__main__":
    asyncio.run(scrape())
