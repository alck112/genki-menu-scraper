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
        
        # Step 1: 自動發現（從主頁 menu 搵）
        print("🔍 自動發現分類...")
        await page.goto(f"{base}/tc/", wait_until="networkidle")
        
        try:
            await page.click('button:has-text("確定")', timeout=3000)
            await asyncio.sleep(2)
        except:
            pass
        
        await asyncio.sleep(3)  # 等 JavaScript menu 生成
        
        # 搵所有 /tc/xxx.html（實際存在嘅鏈結）
        categories = await page.evaluate('''() => {
            const found = new Set();
            document.querySelectorAll('a[href^="/tc/"]').forEach(a => {
                const href = a.getAttribute('href');
                // 只取 .html 結尾，排除系統頁面
                if (href && href.match(/^\\/tc\\/[a-z0-9-]+\\.html$/) && 
                    !href.includes('privacy') && 
                    !href.includes('terms')) {
                    found.add(href);
                }
            });
            return Array.from(found);
        }''')
        
        print(f"✅ 主頁發現: {categories}")
        
        # Step 2: 驗證每個分類（有產品先保留）
        valid_categories = []
        print("\n🧪 驗證分類...")
        
        for cat in categories:
            url = f"{base}{cat}"
            try:
                response = await page.goto(url, timeout=10000)
                
                if response.status == 200:
                    # 檢查係咪真係有產品（唔係空白頁）
                    has_products = await page.evaluate('''() => {
                        return document.querySelectorAll('.product-item, .item').length > 0;
                    }''')
                    
                    if has_products:
                        valid_categories.append(cat)
                        print(f"  ✅ {cat} ({has_products} 個產品)")
                    else:
                        print(f"  ⚠️ {cat} (無產品)")
                else:
                    print(f"  ❌ {cat} ({response.status})")
                    
            except:
                print(f"  ❌ {cat} (載入失敗)")
        
        print(f"\n🎯 有效分類: {len(valid_categories)} 個")
        
        # Step 3: 爬有效分類
        for cat in valid_categories:
            print(f"\n📂 爬取: {cat}")
            p_num = 1
            
            while p_num <= 10:
                url = f"{base}{cat}" if p_num == 1 else f"{base}{cat}?p={p_num}"
                
                try:
                    await page.goto(url, wait_until="networkidle")
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
                    
                    new = 0
                    for it in items:
                        if it['name'] not in seen:
                            seen.add(it['name'])
                            all_items.append(it)
                            new += 1
                    
                    print(f"  第{p_num}頁: +{new}項")
                    
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

