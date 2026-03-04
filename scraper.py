import asyncio
import json
import re
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
        
        # Step 1: 自動發現所有分類連結
        print("🔍 正在發現分類...")
        await page.goto(f"{base}/tc/", wait_until="networkidle")
        
        # 處理 cookie
        try:
            await page.click('button:has-text("確定")', timeout=5000)
            await asyncio.sleep(2)
        except:
            pass
        
        # 搵所有 .html 結尾嘅連結（排除重複、非產品頁）
        categories = await page.evaluate('''() => {
            const links = new Set();
            document.querySelectorAll('a[href*=".html"]').forEach(a => {
                const href = a.getAttribute('href');
                // 只取 /tc/xxx.html 格式，排除特殊頁面
                if (href && href.match(/^\\/tc\\/[a-z-]+\\.html$/)) {
                    links.add(href);
                }
            });
            return Array.from(links);
        }''')
        
        print(f"發現 {len(categories)} 個分類: {categories}")
        
        # Step 2: 遍歷每個分類
        for cat in categories:
            print(f"\n📂 處理分類: {cat}")
            
            p_num = 1
            prev_count = 0  # 用嚟檢查有冇新嘢
            
            while p_num <= 20:  # 安全上限
                # 第1頁唔加 ?p=，第2頁開始加
                if p_num == 1:
                    url = f"{base}{cat}"
                else:
                    url = f"{base}{cat}?p={p_num}"
                
                print(f"  第 {p_num} 頁...")
                
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(2.5)
                    
                    # 提取產品
                    items = await page.evaluate('''() => {
                        const res = [];
                        // 多個 selector 後備
                        const elements = document.querySelectorAll(
                            '.product-item, .item.product, .category-products > div, ' +
                            '[class*="product-item"], .grid-item'
                        );
                        
                        elements.forEach(el => {
                            const name = el.querySelector('h3, h4, .product-name, strong')?.innerText?.trim();
                            const img = el.querySelector('img');
                            let src = img?.dataset?.src || img?.src;
                            
                            if (name && src && name.length > 1 && name.length < 50) {
                                // 清理同驗證 URL
                                if (src.startsWith('/')) src = 'https://order.genkisushi.com.hk' + src;
                                else if (!src.startsWith('http')) src = 'https://order.genkisushi.com.hk/' + src;
                                
                                // 過濾非食物項目
                                if (!name.includes('$') && !name.includes('返回')) {
                                    res.push({name, imgUrl: src});
                                }
                            }
                        });
                        return res;
                    }''')
                    
                    if not items or len(items) == 0:
                        print(f"    無數據，分類完成")
                        break
                    
                    # 檢查係咪同上一頁完全一樣（代表分頁無效/循環）
                    current_names = set([i['name'] for i in items])
                    if p_num > 1 and len(current_names - set([i['name'] for i in all_items[-20:]])) == 0:
                        print(f"    同上一頁重複，分類完成")
                        break
                    
                    # 加入新項目
                    new_count = 0
                    for it in items:
                        if it['name'] not in seen:
                            seen.add(it['name'])
                            all_items.append(it)
                            new_count += 1
                    
                    print(f"    +{new_count} 項 (總共 {len(all_items)})")
                    
                    # 如果呢頁冇新嘢，可能已完
                    if new_count == 0 and p_num > 1:
                        break
                    
                    p_num += 1
                    
                except Exception as e:
                    print(f"    錯誤: {e}")
                    break
        
        await browser.close()
        
        # 儲存
        with open('menu.json', 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        print(f"\n🎉 完成！總共 {len(all_items)} 個品項")
        print(f"分類數量: {len(categories)}")

if __name__ == "__main__":
    asyncio.run(scrape())
