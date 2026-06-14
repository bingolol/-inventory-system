import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import workspace
from database import get_db, init_db
import models, schemas, crud
from image_utils import UPLOAD_DIR, BUSINESS_TYPES, ALLOWED_TYPES, MAX_SIZE, generate_filename, save_image_file, delete_old_image
from enums import ALL_ENUMS, ENUM_LABELS
from routers import products, suppliers, customers, purchases, sales, inventory, reports, export, logs, personal, invoices, tax, income_tax, expenses, opening_balances, financial_reports, cash_flows, backup, reconciliations, confirm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(workspace.get_log_path(), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("inventory")

app = FastAPI(title="进销存管理系统", version="1.0.0")

# CORS：开发环境允许 localhost，生产环境限制来源
ALLOWED_ORIGINS = [
    "http://localhost:5173",      # Vite dev server
    "http://localhost:4173",      # Vite preview
    "http://localhost:8000",      # Same-origin fallback
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]
# 如果环境变量指定了额外来源，追加进去
_extra = os.environ.get("CORS_ORIGINS", "")
if _extra:
    ALLOWED_ORIGINS.extend(_extra.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── AI危险操作确认中间件 ──
# 拦截 AI 发出的 DELETE 和特定 PUT，返回 202 等待用户确认
from confirm_middleware import ConfirmMiddleware
app.add_middleware(ConfirmMiddleware)

# ── 422 校验错误处理器：枚举值写错时返回字段名+非法值+合法值列表 ──
# 字段名 → ALL_ENUMS key 的映射，ENUM_MAP 从 ALL_ENUMS 动态生成，避免重复定义
FIELD_ENUM_MAP = {
    "direction": "invoice_direction",
    "invoice_type": "invoice_type",
    "certification_status": "certification_status",
    "type": "personal_transaction_type",
    "payment_method": "payment_method",
    "payment_status": "payment_status",
    "flow_category": "flow_category",
    "category": "expense_categories",
    "cost_type": "cost_types",
}
ENUM_MAP = {field: ALL_ENUMS[key] for field, key in FIELD_ENUM_MAP.items()}

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    details = []
    for err in errors:
        field = err["loc"][-1] if err["loc"] else "?"
        value = err.get("input", "?")
        msg = err.get("msg", "")
        if "pattern" in msg or "match" in msg.lower():
            allowed = ENUM_MAP.get(field, [])
            if allowed:
                details.append(f"字段 '{field}' 的值 '{value}' 不合法，合法值: {allowed}")
                continue
        details.append(f"字段 '{field}': {msg} (当前值: {value})")
    return JSONResponse(status_code=422, content={"detail": "; ".join(details)})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    logger.warning(f"数据完整性冲突: {msg}")
    if "sku" in msg.lower() or "unique" in msg.lower():
        return JSONResponse(status_code=409, content={"detail": "商品编码已存在"})
    return JSONResponse(status_code=409, content={"detail": "数据冲突，请检查输入"})


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"数据库错误: {exc}")
    return JSONResponse(status_code=500, content={"detail": "数据库操作失败"})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


app.include_router(invoices.router, prefix="/api/invoices", tags=["发票管理"])
app.include_router(tax.router, prefix="/api/tax-report", tags=["增值税报表"])
app.include_router(income_tax.router, prefix="/api/income-tax-report", tags=["企业所得税报表"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["费用管理"])
app.include_router(products.router, prefix="/api/products", tags=["商品管理"])
app.include_router(suppliers.router, prefix="/api/suppliers", tags=["供应商管理"])
app.include_router(customers.router, prefix="/api/customers", tags=["客户管理"])
app.include_router(purchases.router, prefix="/api/purchases", tags=["采购管理"])
app.include_router(sales.router, prefix="/api/sales", tags=["销售管理"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["库存管理"])
app.include_router(reports.router, prefix="/api/reports", tags=["报表统计"])
app.include_router(export.router, prefix="/api/export", tags=["数据导出"])
app.include_router(logs.router, prefix="/api/logs", tags=["操作日志"])
app.include_router(personal.router, prefix="/api/personal", tags=["个人流水账"])
app.include_router(opening_balances.router, prefix="/api/opening-balances", tags=["期初余额"])
app.include_router(financial_reports.router, prefix="/api/financial-reports", tags=["财务报表"])
app.include_router(cash_flows.router, prefix="/api/cash-flows", tags=["现金流量"])
app.include_router(backup.router, prefix="/api/backup", tags=["热备份"])
app.include_router(reconciliations.router, prefix="/api/reconciliations", tags=["对账管理"])
app.include_router(confirm.router, prefix="/api/confirm", tags=["操作确认"])


@app.on_event("startup")
def startup():
    workspace.ensure_workspace()
    init_db()
    # ── EventBus 初始化 ──
    from middleware import register_middleware
    import handlers  # 触发 handler 注册
    import commands  # 确保 Command 全部注册（虽然 Router 导入已触发，但显式导入更安全）
    register_middleware()
    logger.info("进销存管理系统启动完成")


# ── 图片上传API ──

from fastapi import UploadFile, File, HTTPException

@app.post("/api/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    business_type: str = "expense",
    record_id: int = 0
):
    """上传图片，文件名: {business_type}_{record_id}_{6位随机码}.{ext}"""
    if business_type not in BUSINESS_TYPES:
        raise HTTPException(status_code=400, detail=f"业务类型只能是: {', '.join(BUSINESS_TYPES)}")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="只支持 JPG/PNG/GIF/WEBP 格式图片")
    
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过5MB")
    
    ext = ALLOWED_TYPES[file.content_type]
    filename = generate_filename(business_type, record_id, ext)
    image_url = save_image_file(content, filename)
    
    return {"image_url": image_url, "filename": filename}


@app.put("/api/upload/image")
async def replace_image(
    file: UploadFile = File(...),
    business_type: str = "expense",
    record_id: int = 0,
    old_image_url: str = ""
):
    """换图：上传新图 → 删旧图 → 返回新URL"""
    result = await upload_image(file, business_type, record_id)
    delete_old_image(old_image_url)
    return result


@app.delete("/api/upload/image")
async def delete_image(image_url: str = ""):
    """删图：只删文件，不碰订单记录"""
    if not image_url:
        raise HTTPException(status_code=400, detail="缺少 image_url 参数")
    delete_old_image(image_url)
    return {"message": "图片已删除"}


@app.get("/api/accounts", response_model=list[schemas.AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return crud.list_accounts(db)


@app.post("/api/accounts", response_model=schemas.AccountOut)
def create_account(body: schemas.AccountCreate, db: Session = Depends(get_db)):
    try:
        account = crud.create_account(db, name=body.name, type=body.type, code=body.code, taxpayer_type=body.taxpayer_type)
        db.commit()
        db.refresh(account)
        return account
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="账本代码已存在，请使用不同的代码")


@app.put("/api/accounts/{account_id}", response_model=schemas.AccountOut)
def update_account(account_id: int, body: schemas.AccountUpdate, db: Session = Depends(get_db)):
    account = crud.update_account(db, account_id, body.name)
    if not account:
        raise HTTPException(status_code=404, detail="账本不存在")
    db.commit()
    db.refresh(account)
    return account


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    try:
        if not crud.delete_account(db, account_id):
            raise HTTPException(status_code=404, detail="账本不存在")
        db.commit()
        return {"message": "账本已删除"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/enums")
def get_enums():
    """返回所有枚举值和中文标签，前端缓存使用"""
    return {"values": ALL_ENUMS, "labels": ENUM_LABELS}

# 图片静态文件（必须在前端dist之前挂载）
uploads_dir = workspace.get_uploads_root()
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# 前端静态文件（生产环境）
frontend_dist = workspace.get_frontend_dist_dir()
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)