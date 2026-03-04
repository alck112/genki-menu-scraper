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
        
        categories = [
            '/tc/sushi.html',
            '/tc/sashimi.html',
            '/tc/gunkan.html',
            '/tc/drinks.html',
            '/tc/seasonal.html',
            '/tc/seared-sushi.html',
            '/tc/hot-picks.html',
            '/tc/roll-sushi.html',
            '/tc/hand-rolls.html',
            '/tc/appetizers.html',
            '/tc/hot-food.html',
            '/tc/udon.html',
            '/tc/kids-choice.html',
            '/tc/green-choice.html',
            '/tc/desserts.html'
        ]
        
        print(f"將處理 {len(categories)} 個分類")
        
        for cat in categories:
            print(f"\n{'='*50}")
            print(f"📂 {cat}")
            
            p_num = 1
            
            while p_num <= 15:
                if p_num == 1:
                    url = f"{base}{cat}"
                else:
                    url = f"{base}{cat}?p={p_num}"
                
                print(f"  第 {p_num} 頁")
                
                try:
                    response = await page.goto(url, wait_until="networkidle", timeout=20000)
                    
                    if response.status != 200:
                        print(f"    ❌ HTTP {response.status}")
                        break
                    
                    if p_num == 1:
                        try:
                            await page.click('button:has-text("確定")', timeout=5000)
                            await asyncio.sleep(2)
                        except:
                            pass
                    
                    await asyncio.sleep(3)
                    
                    # 簡化 JavaScript
                    items = await page.evaluate('''() => {
                        var results = [];
                        var elements = document.querySelectorAll('.product-item, .item');
                        
                        for (var i = 0; i < elements.length; i++) {
                            var el = elements[i];
                            var name = '';
                            var nameEl = el.querySelector('h3, h4, .product-name, strong');
                            if (nameEl) name = nameEl.innerText.trim();
                            
                            var img = el.querySelector('img');
                            var imgUrl = '';
                            if (img) {
                                imgUrl = img.getAttribute('data-src') || img.getAttribute('src');
                            }
                            
                            if (name && imgUrl && name.length > 1 && imgUrl.indexOf('media') > -1) {
                                if (imgUrl.charAt(0) === '/') {
                                    imgUrl = 'https://order.genkisushi.com.hk' + imgUrl;
                                }
                                results.push({name: name, imgUrl: imgUrl});
                            }
                        }
                        
                        return results;
                    }''')
                    
                    # Python 用 len() 檢查 list 長度
                    if not items or len(items) == 0:
                        print(f"    ⚠️ 無產品")
                        break
                    
                    new_count = 0
                    for it in items:
                        if it['name'] not in seen:
                            seen.add(it['name'])
                            all_items.append(it)
                            new_count += 1
                    
                    print(f"    ✓ +{new_count} 項 (總計: {len(all_items)})")
                    
                    if new_count == 0:
                        break
                    
                    p_num += 1
                    
                except Exception as e:
                    print(f"    ❌ 錯誤: {str(e)[:80]}")
                    break
            
            print(f"  分類完成: {len(all_items)} 項")
        
        await browser.close()
        
        with open('menu.json', 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        print(f"\n🎉 完成！{len(all_items)} 項")

if __name__ == "__main__":
    asyncio.run(scrape())
