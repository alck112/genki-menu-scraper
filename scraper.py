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
        
        # 所有有效分類（15個）
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
            print(f"{'='*50}")
            
            p_num = 1
            
            while p_num <= 15:  # 每個分類最多15頁
                # 正確構造 URL：第1頁冇 ?p=，第2頁開始加 ?p=2
                if p_num == 1:
                    url = f"{base}{cat}"
                else:
                    url = f"{base}{cat}?p={p_num}"
                
                print(f"  第 {p_num} 頁: {url}")
                
                try:
                    response = await page.goto(url, wait_until="networkidle", timeout=20000)
                    
                    if response.status != 200:
                        print(f"    ❌ HTTP {response.status}，跳過")
                        break
                    
                    # 第1頁處理 cookie banner
                    if p_num == 1:
                        try:
                            await page.click('button:has-text("確定")', timeout=5000)
                            await asyncio.sleep(2)
                            print("    ✓ 已處理 cookie")
                        except:
                            pass
                    
                    # 等產品加載（重要！）
                    await asyncio.sleep(3)
                    
                    # 提取產品數據
                    items = await page.evaluate('''() => {
                        const results = [];
                        
                        // 搵產品元素（多個後備 selector）
                        const elements = document.querySelectorAll('.product-item, .item.product, .category-products > div, [class*="product-item"]');
                        
                        elements.forEach(el => {
                            // 搵名稱
                            let name = '';
                            const nameSelectors = ['h3', 'h4', '.product-name', 'strong'];
                            for (let sel of nameSelectors) {
                                const found = el.querySelector(sel);
                                if (found && found.innerText) {
                                    name = found.innerText.trim();
                                    if (name && name.length > 0) break;
                                }
                            }
                            
                            // 搵圖片（優先 data-src，因為係 lazy load）
                            const img = el.querySelector('img');
                            let imgUrl = '';
                            if (img) {
                                imgUrl = img.getAttribute('data-src') || 
                                        img.getAttribute('src') ||
                                        img.getAttribute('data-original');
                            }
                            
                            // 驗證：要有名、有圖、名要合理
                            if (name && imgUrl && 
                                name.length > 1 && 
                                name.length < 50 &&
                                !name.includes('期間限定') &&  # 過濾標題
                                !name.includes('查看更多') &&
                                imgUrl.includes('media')) {     # 確保係產品圖
                                
                                // 確保係絕對 URL
                                if (imgUrl.startsWith('/')) {
                                    imgUrl = 'https://order.genkisushi.com.hk' + imgUrl;
                                }
                                
                                results.push({name, imgUrl});
                            }
                        });
                        
                        return results;
                    }''')
                    
                    if not items or len(items) == 0:
                        print(f"    ⚠️ 無產品，分類完成")
                        break
                    
                    # 去重並加入
                    new_count = 0
                    for it in items:
                        if it['name'] not in seen:
                            seen.add(it['name'])
                            all_items.append(it)
                            new_count += 1
                    
                    print(f"    ✓ 找到 {len(items)} 個，新增 {new_count} 項 (總計: {len(all_items)})")
                    
                    # 如果無新項目（即係同上一頁重複），就停
                    if new_count == 0:
                        print(f"    🔄 無新項目，可能分頁重複")
                        break
                    
                    p_num += 1
                    
                except Exception as e:
                    print(f"    ❌ 錯誤: {str(e)[:100]}")
                    break
            
            print(f"  分類完成，暫時總數: {len(all_items)}")
        
        await browser.close()
        
        # 儲存結果
        with open('menu.json', 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*50}")
        print(f"🎉 全部完成！")
        print(f"總共 {len(all_items)} 個唯一品項")
        print(f"處理咗 {len(categories)} 個分類")
        print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(scrape())
