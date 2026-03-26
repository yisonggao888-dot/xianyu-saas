# 星昌云·闲鱼无货源SaaS平台

基于 FastAPI + Vue3 的多租户闲鱼自动化运营系统。

## 项目结构

```
xianyu-saas/
├── backend/                 # FastAPI后端
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置、安全工具
│   │   ├── db/             # 数据库连接
│   │   ├── models/         # SQLAlchemy模型
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   ├── main.py             # 应用入口
│   └── requirements.txt    # Python依赖
├── frontend/               # Vue3前端
│   ├── src/
│   │   ├── views/          # 页面视图
│   │   ├── components/     # 组件
│   │   ├── api/            # API封装
│   │   ├── stores/         # Pinia状态管理
│   │   └── router/         # 路由配置
│   └── package.json
├── docker/                 # Docker配置
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
└── README.md
```

## 快速开始

### 1. 启动数据库

```bash
cd docker
docker-compose up -d db redis
```

### 2. 启动后端

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python main.py
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 技术栈

- **后端**: Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL + Redis
- **前端**: Vue 3 + TypeScript + Element Plus + Pinia
- **部署**: Docker + Docker Compose

## 开发计划

- [x] Week 1: 基础架构搭建
- [ ] Week 2: Web管理后台
- [ ] Week 3-4: AI客服改造
- [ ] Week 5-6: 选品中心
- [ ] Week 7-8: 支付与部署

## 团队

- 后端/前端开发: Kimi Claw
- 产品/测试: 飞马

## License

MIT
