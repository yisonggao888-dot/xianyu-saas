# 1688 RPA 爬虫配置说明

## 快速开始

### 1. 安装 Playwright 浏览器

```bash
cd backend
pip install -r requirements.txt

# 安装 Playwright 浏览器（只需执行一次）
playwright install chromium
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件，或修改 `backend/.env`：

```bash
# 启用 1688 RPA 真实抓取（默认 false，使用演示数据）
USE_1688_RPA=true

# 可选：设置 Playwright 无头模式（生产环境建议 true）
PLAYWRIGHT_HEADLESS=true
```

### 3. 测试爬虫

```bash
# 测试演示数据模式
python test_1688_rpa.py --mode mock

# 测试 RPA 真实抓取（会打开浏览器窗口）
python test_1688_rpa.py --mode rpa
```

## 使用方式

### 方式1：环境变量控制（推荐）

```python
from app.services.scraper import ProductScraper

# 自动读取 USE_1688_RPA 环境变量
scraper = ProductScraper()
results = await scraper.search_all(keyword="手机壳", sources=['1688'])
```

### 方式2：代码中显式控制

```python
from app.services.scraper import ProductScraper

# 强制启用 RPA
scraper = ProductScraper(use_1688_rpa=True)

# 强制使用演示数据
scraper = ProductScraper(use_1688_rpa=False)
```

### 方式3：直接使用 RPA 类

```python
from app.services.ali1688_rpa import Ali1688RpaScraper

scraper = Ali1688RpaScraper()
await scraper.init_browser(headless=True)
products = await scraper.search(keyword="手机壳", page_num=1)
await scraper.close()
```

## 技术说明

### RPA 技术栈

- **Playwright**: 微软开源的浏览器自动化库
- **Stealth 脚本**: 注入 JavaScript 绕过反检测
- **BeautifulSoup**: 解析 HTML 提取数据

### 反爬策略

| 检测点 | 应对措施 |
|--------|----------|
| webdriver 检测 | 覆盖 navigator.webdriver |
| 插件检测 | 模拟真实插件列表 |
| Canvas 指纹 | 暂未处理（如有需要可添加） |
| 行为分析 | 模拟随机滚动、停顿 |

### 已知限制

1. **页面结构变化**: 1688 页面结构更新可能导致解析失败（需维护选择器）
2. **登录态**: 大量抓取可能需要登录（当前使用游客模式）
3. **频率限制**: 单IP频繁请求会触发验证码

## 生产环境部署建议

### 方案A：服务器部署（有图形界面）

```bash
# Ubuntu 安装桌面环境
sudo apt-get install -y xvfb

# 使用 xvfb-run 运行（无头但有图形支持）
xvfb-run python main.py
```

### 方案B：Docker 部署

```dockerfile
# 使用包含 Playwright 的镜像
FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

# 安装浏览器依赖
RUN playwright install chromium
RUN playwright install-deps chromium

# 复制代码
COPY . /app
WORKDIR /app

# 安装 Python 依赖
RUN pip install -r requirements.txt

CMD ["python", "main.py"]
```

### 方案C：代理池 + 低频率

```python
# 配置代理（可选）
proxy = {
    'server': 'http://your-proxy:port',
    'username': 'user',
    'password': 'pass'
}

context = await browser.new_context(proxy=proxy)
```

## 故障排查

### 问题1：浏览器启动失败

```bash
# 重新安装浏览器
playwright install chromium
playwright install-deps chromium
```

### 问题2：抓取结果为空

可能原因：
- 1688 页面结构更新
- 触发反爬被拦截
- 网络连接问题

排查方法：
```bash
# 启用调试日志查看页面内容
export LOGURU_LEVEL=DEBUG
python test_1688_rpa.py --mode rpa
```

### 问题3：内存占用过高

每个浏览器实例占用约 200MB 内存，建议：
- 复用浏览器实例
- 限制并发数
- 使用连接池模式

## 后续优化方向

1. [ ] 支持登录态保持（Cookie 持久化）
2. [ ] 接入打码平台处理验证码
3. [ ] 代理 IP 池集成
4. [ ] 商品详情页抓取
5. [ ] 图片下载功能

## 参考

- [Playwright 文档](https://playwright.dev/python/)
- [1688 反爬研究](https://www.cnblogs.com/one-jason/p/18647982)
