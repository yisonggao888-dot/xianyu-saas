"""
选品API路由
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.services.product_service import ProductService
from app.models.models import ProductStatus

router = APIRouter()


# ========== 请求/响应模型 ==========

class ProductSearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    sources: List[str] = Field(default=["pdd", "1688"])
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_sales: Optional[int] = None
    sort: str = Field(default="default", pattern="^(default|price_asc|price_desc|sales)$")


class AddToListRequest(BaseModel):
    source: str = Field(..., pattern="^(pdd|1688)$")
    source_id: str
    title: str
    cost_price: float = Field(..., gt=0)
    sale_price: float = Field(..., gt=0)
    main_image: str
    detail_url: str
    description: Optional[str] = None


class UpdateProductRequest(BaseModel):
    title: Optional[str] = None
    sale_price: Optional[float] = None
    main_image: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    source: str
    source_id: str
    title: str
    cost_price: float
    sale_price: float
    profit: float
    profit_margin: float
    main_image: str
    detail_url: str
    description: Optional[str]
    status: str
    created_at: str


class SearchResultItem(BaseModel):
    source: str
    source_id: str
    title: str
    price: float
    original_price: Optional[float]
    main_image: str
    sales_count: int
    shop_name: str
    shop_rating: float
    detail_url: str
    category: Optional[str]
    profit_margin: dict


class SearchResponse(BaseModel):
    pdd: List[SearchResultItem]
    ali1688: List[SearchResultItem]


class StatsResponse(BaseModel):
    total_products: int
    active_products: int
    total_orders: int
    total_sales: float
    total_profit: float


# ========== API端点 ==========

@router.post("/search", response_model=SearchResponse)
async def search_products(
    data: ProductSearchRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """搜索商品（拼多多/1688）"""
    service = ProductService(db)
    
    results = await service.search_products(
        tenant_id=current_user_id,  # TODO: 从user获取tenant_id
        keyword=data.keyword,
        sources=data.sources,
        min_price=data.min_price,
        max_price=data.max_price,
        min_sales=data.min_sales,
        sort=data.sort,
    )
    
    # 格式化响应
    def format_item(item: dict) -> SearchResultItem:
        return SearchResultItem(
            source=item['source'],
            source_id=item['source_id'],
            title=item['title'],
            price=item['price'],
            original_price=item.get('original_price'),
            main_image=item['main_image'],
            sales_count=item['sales_count'],
            shop_name=item['shop_name'],
            shop_rating=item['shop_rating'],
            detail_url=item['detail_url'],
            category=item.get('category'),
            profit_margin=item.get('profit_margin', {}),
        )
    
    return {
        'pdd': [format_item(p) for p in results.get('pdd', [])],
        'ali1688': [format_item(p) for p in results.get('1688', [])],
    }


@router.post("/add-to-list", response_model=ProductResponse)
async def add_to_list(
    data: AddToListRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """添加商品到选品列表"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = ProductService(db)
    
    product = await service.add_to_list(
        tenant_id=tenant_id,
        source=data.source,
        source_id=data.source_id,
        title=data.title,
        cost_price=data.cost_price,
        sale_price=data.sale_price,
        main_image=data.main_image,
        detail_url=data.detail_url,
        description=data.description,
    )
    
    return {
        "id": product.id,
        "source": product.source,
        "source_id": product.source_id,
        "title": product.title,
        "cost_price": product.cost_price,
        "sale_price": product.sale_price,
        "profit": round(product.sale_price - product.cost_price, 2),
        "profit_margin": round((product.sale_price - product.cost_price) / product.cost_price * 100, 1),
        "main_image": product.main_image,
        "detail_url": product.detail_url,
        "description": product.description,
        "status": product.status.value,
        "created_at": product.created_at.isoformat(),
    }


@router.get("/list", response_model=List[ProductResponse])
async def get_product_list(
    status: Optional[str] = Query(None, regex="^(active|inactive|deleted)$"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取选品列表"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = ProductService(db)
    products = await service.get_product_list(tenant_id, status)
    
    return [
        {
            "id": p.id,
            "source": p.source,
            "source_id": p.source_id,
            "title": p.title,
            "cost_price": p.cost_price,
            "sale_price": p.sale_price,
            "profit": round(p.sale_price - p.cost_price, 2),
            "profit_margin": round((p.sale_price - p.cost_price) / p.cost_price * 100, 1),
            "main_image": p.main_image,
            "detail_url": p.detail_url,
            "description": p.description,
            "status": p.status.value,
            "created_at": p.created_at.isoformat(),
        }
        for p in products
    ]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取商品详情"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = ProductService(db)
    product = await service.get_product(tenant_id, product_id)
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
    
    return {
        "id": product.id,
        "source": product.source,
        "source_id": product.source_id,
        "title": product.title,
        "cost_price": product.cost_price,
        "sale_price": product.sale_price,
        "profit": round(product.sale_price - product.cost_price, 2),
        "profit_margin": round((product.sale_price - product.cost_price) / product.cost_price * 100, 1),
        "main_image": product.main_image,
        "detail_url": product.detail_url,
        "description": product.description,
        "status": product.status.value,
        "created_at": product.created_at.isoformat(),
    }


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    data: UpdateProductRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """更新商品"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = ProductService(db)
    
    update_data = data.model_dump(exclude_unset=True)
    success = await service.update_product(tenant_id, product_id, **update_data)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
    
    # 返回更新后的商品
    product = await service.get_product(tenant_id, product_id)
    
    return {
        "id": product.id,
        "source": product.source,
        "source_id": product.source_id,
        "title": product.title,
        "cost_price": product.cost_price,
        "sale_price": product.sale_price,
        "profit": round(product.sale_price - product.cost_price, 2),
        "profit_margin": round((product.sale_price - product.cost_price) / product.cost_price * 100, 1),
        "main_image": product.main_image,
        "detail_url": product.detail_url,
        "description": product.description,
        "status": product.status.value,
        "created_at": product.created_at.isoformat(),
    }


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """删除商品"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = ProductService(db)
    success = await service.delete_product(tenant_id, product_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
    
    return {"message": "商品已删除"}


@router.get("/stats/summary", response_model=StatsResponse)
async def get_stats(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取选品统计"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = ProductService(db)
    stats = await service.get_stats(tenant_id)
    
    return StatsResponse(**stats)
