"""
1688 RPA 爬虫测试脚本
测试 Playwright 真实抓取功能
"""
import asyncio
import sys
import os

# 添加后端目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.ali1688_rpa import Ali1688RpaScraper


async def test_1688_rpa():
    """测试 1688 RPA 爬虫"""
    print("=" * 60)
    print("1688 RPA 爬虫测试")
    print("=" * 60)
    
    scraper = Ali1688RpaScraper()
    
    try:
        # 初始化浏览器（非无头模式，方便观察）
        print("\n[1/3] 启动浏览器...")
        await scraper.init_browser(headless=False)
        
        # 测试搜索
        keyword = "手机壳"
        print(f"\n[2/3] 搜索关键词: {keyword}")
        products = await scraper.search(keyword=keyword, page_num=1)
        
        print(f"\n[3/3] 抓取结果: 找到 {len(products)} 个商品")
        print("-" * 60)
        
        # 展示前3个商品
        for i, product in enumerate(products[:3]):
            print(f"\n商品 {i+1}:")
            print(f"  标题: {product.title}")
            print(f"  价格: ¥{product.price}")
            print(f"  销量: {product.sales_count}")
            print(f"  店铺: {product.shop_name}")
            print(f"  链接: {product.detail_url}")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n关闭浏览器...")
        await scraper.close()


async def test_with_mock():
    """测试演示数据模式"""
    print("=" * 60)
    print("演示数据模式测试")
    print("=" * 60)
    
    from app.services.scraper import ProductScraper
    
    # 使用演示数据模式
    scraper = ProductScraper(use_1688_rpa=False)
    
    results = await scraper.search_all(
        keyword="手机壳",
        sources=['1688'],
        min_price=10,
        max_price=100
    )
    
    print(f"\n找到 {len(results.get('1688', []))} 个1688商品（演示数据）")
    
    await scraper.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='1688 RPA 爬虫测试')
    parser.add_argument('--mode', choices=['rpa', 'mock'], default='mock',
                        help='测试模式: rpa=真实抓取, mock=演示数据')
    
    args = parser.parse_args()
    
    if args.mode == 'rpa':
        print("注意：RPA模式会启动真实浏览器窗口，请观察浏览器行为")
        print("测试完成后浏览器会自动关闭\n")
        asyncio.run(test_1688_rpa())
    else:
        asyncio.run(test_with_mock())
