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
        
        await asyncio.sleep(5)
        
        # 搵所有連結（處理絕對同相對 URL）
        raw_links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a'))
                .map(a => a.getAttribute('href'))
                .filter(h => h && (
                    h.includes('/tc/') || 
                    h.includes('order.genkisushi.com.hk/tc/')
                ));
        }''')
        
        print(f"  搵到 {len(raw_links)} 個連結")
        print(f"  例子: {raw_links[:10]}")
        
        # 清理：統一變成 /tc/xxx.html 格式
        categories = set()
        for link in raw_links:
            # 如果係完整 URL，提取 path 部分
            if link.startswith('http'):
                # 提取 https://.../tc/xxx.html → /tc/xxx.html
                if '/tc/' in link:
                    path = link.split('/tc/')[1]
                    if path and path.endswith('.html'):
                        categories.add(f'/tc/{path}')
            # 如果已經係相對路徑
            elif link.startswith('/tc/') and link.endswith('.html'):
                categories.add(link)
        
        categories = list(categories)
        print(f"\n✅ 清理後: {categories}")
        
        # Fallback 如果搵唔到
        if not categories:
            print("⚠️ 用後備列表")
            categories = ['/tc/sushi.html', '/tc/sashimi.html', '/tc/gunkan.html']
        
        # Step 2: 爬每個分類
        for cat in categories:
            print(f"\n📂 {cat}")
            p_num = 1
            
            while p_num <= 10:
                # 正確構造 URL
                if p_num == 1:
                    url = f"{base}{cat}"
                else:
                    url = f"{base}{cat}?p={p_num}"
                
                try:
                    response = await page.goto(url, wait_until="networkidle", timeout=15000)
                    
                    if response.status != 200:
                        print(f"  ❌ {response.status}")
                        break
                    
                    if p_num == 1:
                        try:
                            await page.click('button:has-text("確定")', timeout=3000)
                            await asyncio.sleep(1)
                        except:
                            pass
                    
                    await asyncio.sleep(2)
                    
                    # 提取產品
                    items = await page.evaluate('''() => {
                        const res = [];
                        document.querySelectorAll('.product-item, .item').forEach(el => {
                            const name = el.querySelector('h3, h4, .product-name')?.innerText?.trim();
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
