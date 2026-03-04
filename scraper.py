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
        
        # 直接用手動 list（避免自動發現失敗）
        categories = [
            '/tc/sushi.html',
            '/tc/sashimi.html', 
            '/tc/roll.html',
            '/tc/rice.html',
            '/tc/set.html',
            '/tc/side.html',
            '/tc/dessert.html',
            '/tc/drink.html',
            '/tc/nigiri.html',
            '/tc/gunkan.html'
        ]
        
        print(f"將會處理 {len(categories)} 個分類")
        
        for cat in categories:
            print(f"\n{'='*50}")
            print(f"📂 開始處理: {cat}")
            print(f"{'='*50}")
            
            p_num = 1
            
            while p_num <= 15:
                # 關鍵：第1頁唔加 ?p=
                if p_num == 1:
                    url = f"{base}{cat}"
                else:
                    url = f"{base}{cat}?p={p_num}"
                
                print(f"\n  🌐 第 {p_num} 頁: {url}")
                
                try:
                    # 去頁面
                    response = await page.goto(url, wait_until="networkidle", timeout=20000)
                    print(f"     狀態碼: {response.status if response else 'N/A'}")
                    
                    # 第1頁處理 cookie
                    if p_num == 1:
                        try:
                            await page.click('button:has-text("確定")', timeout=5000)
                            await asyncio.sleep(2)
                            print("     ✓ 已點擊確定")
                        except:
                            print("     冇 cookie banner 或已處理")
                    
                    # 等產品加載
                    await asyncio.sleep(3)
                    
                    # 檢查頁面標題（確認入到正確頁面）
                    title = await page.title()
                    print(f"     頁面標題: {title[:30]}...")
                    
                    # 提取產品（多個後備 selector）
                    items = await page.evaluate('''() => {
                        const results = [];
                        
                        // 後備 selector 列表
                        const selectors = [
                            '.product-item',
                            '.item.product',
                            '.category-products .item',
                            '.products-grid > div',
                            '[data-product-id]',
                            '.product-list .item'
                        ];
                        
                        let elements = [];
                        for (let sel of selectors) {
                            elements = document.querySelectorAll(sel);
                            if (elements.length > 0) {
                                console.log('Selector matched:', sel, elements.length);
                                break;
                            }
                        }
                        
                        // 如果都搵唔到，試下搵有圖片嘅 div
                        if (elements.length === 0) {
                            document.querySelectorAll('div').forEach(div => {
                                if (div.querySelector('img') && div.innerText.includes('$')) {
                                    elements.push(div);
                                }
                            });
                        }
                        
                        console.log('Total elements found:', elements.length);
                        
                        elements.forEach((el, idx) => {
                            // 搵名
                            let name = '';
                            const nameSelectors = ['h3', 'h4', '.product-name', 'strong', 'b'];
                            for (let sel of nameSelectors) {
                                const found = el.querySelector(sel);
                                if (found) {
                                    name = found.innerText.trim();
                                    if (name && name.length > 1) break;
                                }
                            }
                            
                            // 搵圖
                            const img = el.querySelector('img');
                            let imgUrl = '';
                            if (img) {
                                imgUrl = img.getAttribute('data-src') || 
                                        img.getAttribute('src') ||
                                        img.getAttribute('data-original');
                            }
                            
                            // 驗證
                            if (name && imgUrl && 
                                name.length > 1 && 
                                name.length < 100 &&
                                !name.includes('期間限定') &&  // 過濾標題
                                !name.includes('查看更多') &&
                                imgUrl.includes('media')) {     // 確保係產品圖
                                
                                if (imgUrl.startsWith('/')) {
                                    imgUrl = 'https://order.genkisushi.com.hk' + imgUrl;
                                }
                                
                                results.push({name, imgUrl});
                            }
                        });
                        
                        return results;
                    }''')
                    
                    if not items or len(items) == 0:
                        print(f"     ⚠️ 無產品數據")
                        # 如果第1頁就無，可能頁面結構唔同，試下截圖或攝 HTML
                        if p_num == 1:
                            html_preview = await page.content()
                            print(f"     HTML 長度: {len(html_preview)}")
                            # 檢查有冇「即將推出」或「暫無產品」
                            if "即將推出" in html_preview or "暫無" in html_preview:
                                print("     頁面顯示暫無產品")
                        break
                    
                    # 加入新項目
                    new_count = 0
                    for it in items:
                        if it['name'] not in seen:
                            seen.add(it['name'])
                            all_items.append(it)
                            new_count += 1
                    
                    print(f"     ✓ 找到 {len(items)} 個元素，新增 {new_count} 項")
                    print(f"     例子: {items[0]['name'][:20]}... ({items[0]['imgUrl'][:50]}...)")
                    
                    # 如果冇新項目，可能分頁已完
                    if new_count == 0 and p_num > 1:
                        print(f"     無新項目，分類完成")
                        break
                    
                    p_num += 1
                    
                except Exception as e:
                    print(f"     ❌ 錯誤: {str(e)[:100]}")
                    break
            
            print(f"  分類完成，暫時總數: {len(all_items)}")
        
        await browser.close()
        
        # 儲存
        with open('menu.json', 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*50}")
        print(f"🎉 完成！總共 {len(all_items)} 個品項")
        print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(scrape())
