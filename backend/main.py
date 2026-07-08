import sys
import os
import logging
from contextlib import asynccontextmanager

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
from errors import BusinessError, ErrorCode, ERROR_STATUS_MAP
from accounting_engine import AccountingError
from routers import products, suppliers, customers, purchases, sales, inventory, reports, export, logs, personal, invoices, tax, income_tax, expenses, opening_balances, financial_reports, cash_flows, backup, reconciliations, confirm, fixed_assets, bank_accounts, bank_transactions, payments, receipts, check, accounting_check, ai_capabilities, auth, bootstrap, finance, month_end, tax_check, bank_reconcile, personal_advances, accounting_guide, tax_declaration

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(workspace.get_log_path(), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("inventory")


def _startup():
    """应用启动逻辑"""
    from database import set_maintenance_mode
    workspace.ensure_workspace()
    set_maintenance_mode(True)
    init_db()
    set_maintenance_mode(False)
    # ── 硬约束：Truth Source Bypass 静态扫描 + 不变量测试 ──
    # 启动时强制跑，ERROR/测试失败 → sys.exit(1) 拒绝启动
    _run_truth_source_hard_constraints()
    # ── 清理过期 confirm token ──
    from middleware.confirm_middleware import confirm_store
    confirm_store.cleanup_expired()
    # ── EventBus 初始化 ──
    from middleware import register_middleware
    import handlers
    import commands
    register_middleware()
    # ── 审计日志事件监听 ──
    from utils.audit import register_listeners
    register_listeners()
    logger.info("进销存管理系统启动完成")


def _shutdown():
    """应用关闭逻辑：关闭日志文件句柄，避免 ResourceWarning"""
    for handler in logging.getLogger().handlers:
        try:
            handler.close()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理（替代 deprecated @app.on_event）"""
    _startup()
    yield
    _shutdown()


app = FastAPI(title="进销存管理系统", version="1.0.0", lifespan=lifespan)

# CORS：开发环境允许 localhost，生产环境限制来源
# 用正则匹配 localhost 开发端口（5173-5179/4173/8000），避免 Vite 端口漂移后 CORS 拦截
ALLOWED_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:(517\d|4173|8000))?$"
# 环境变量可追加明确来源（生产环境部署）
_extra_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_extra_origins,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 安全中间件栈（从外到内执行）──
#   1. AIGatewayMiddleware：白名单校验入口合法性
#   2. WritePermissionMiddleware：给已放行的写请求设 SecureSession 令牌
#   3. ConfirmMiddleware：对危险写操作做二次确认
from middleware.confirm_middleware import ConfirmMiddleware
from middleware.write_permission import WritePermissionMiddleware
from middleware.readonly_middleware import ReadonlyMiddleware
from ai_gateway import AIGatewayMiddleware
app.add_middleware(ConfirmMiddleware)              # 最内层
app.add_middleware(ReadonlyMiddleware)             # 只读拦截：阻止 DELETE 历史数据
app.add_middleware(WritePermissionMiddleware)      # 中间层
app.add_middleware(AIGatewayMiddleware)            # 最外层

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
}
ENUM_MAP = {field: ALL_ENUMS[key] for field, key in FIELD_ENUM_MAP.items()}


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    """业务逻辑错误 → 4xx + 结构化响应"""
    status_code = ERROR_STATUS_MAP.get(exc.code, 422)
    return JSONResponse(status_code=status_code, content=exc.to_dict())


@app.exception_handler(AccountingError)
async def accounting_error_handler(request: Request, exc: AccountingError):
    """会计计算错误 → 422 + 结构化响应(保留法规依据 + 计算明细 + AI 引导)

    避免 AccountingError 落到 generic handler 被吞成 500 + INTERNAL_ERROR,
    让 AI Agent 能拿到 accounting_rule / calculation_detail 据此修正输入。
    """
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


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
    return JSONResponse(status_code=422, content={
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "; ".join(details),
            "action": "user_input",
            "action_data": {},
            "data": {},
            "ai_instruction": "STOP_RETRYING. 参数校验失败，请检查字段名和值是否正确。"
        }
    })


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    logger.warning(f"数据完整性冲突: {msg}")
    if "sku" in msg.lower() or "unique" in msg.lower():
        return JSONResponse(status_code=409, content={
            "error": {
                "code": "DUPLICATE_ENTRY",
                "message": "商品编码已存在",
                "action": "user_input",
                "action_data": {},
                "data": {},
                "ai_instruction": "STOP_RETRYING. 数据重复，请检查输入是否与已有数据冲突。"
            }
        })
    return JSONResponse(status_code=409, content={
        "error": {
            "code": "DUPLICATE_ENTRY",
            "message": "数据冲突，请检查输入",
            "action": "user_input",
            "action_data": {},
            "data": {},
            "ai_instruction": "STOP_RETRYING. 数据重复，请检查输入是否与已有数据冲突。"
        }
    })


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"数据库错误: {exc}")
    return JSONResponse(status_code=500, content={
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "数据库操作失败",
            "action": "contact_admin",
            "action_data": {},
            "data": {},
            "ai_instruction": "STOP_RETRYING. 数据库错误，请联系管理员。"
        }
    })


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    err_msg = str(exc) or "未知错误"
    return JSONResponse(status_code=500, content={
        "error": {
            "code": "INTERNAL_ERROR",
            "message": err_msg,
            "action": "none",
            "action_data": {},
            "data": {"exception_type": type(exc).__name__},
            "ai_instruction": f"系统异常: {err_msg}"
        }
    })


app.include_router(auth.router)
app.include_router(invoices.router, prefix="/api/invoices", tags=["发票管理"])
app.include_router(tax.router, prefix="/api/tax-report", tags=["增值税报表"])
app.include_router(income_tax.router, prefix="/api/income-tax-report", tags=["企业所得税报表"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["费用管理"])
app.include_router(fixed_assets.router, prefix="/api/fixed-assets", tags=["固定资产管理"])
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
app.include_router(personal_advances.router, prefix="/api/personal-advances", tags=["其他应付款/个人垫付"])
app.include_router(opening_balances.router, prefix="/api/opening-balances", tags=["期初余额"])
app.include_router(financial_reports.router, prefix="/api/financial-reports", tags=["财务报表"])
app.include_router(cash_flows.router, prefix="/api/cash-flows", tags=["现金流量"])
app.include_router(backup.router, prefix="/api/backup", tags=["热备份"])
app.include_router(reconciliations.router, prefix="/api/reconciliations", tags=["对账管理"])
app.include_router(confirm.router, prefix="/api/confirm", tags=["操作确认"])
app.include_router(bank_accounts.router, prefix="/api/bank-accounts", tags=["银行账户"])
app.include_router(bank_transactions.router, prefix="/api/bank-transactions", tags=["银行流水"])
app.include_router(payments.router, prefix="/api/payments", tags=["付款管理"])
app.include_router(receipts.router, prefix="/api/receipts", tags=["收款管理"])
app.include_router(check.router, prefix="/api/check", tags=["前置条件检查"])
app.include_router(accounting_check.router, prefix="/api/accounting", tags=["会计准则约束检查"])
app.include_router(finance.router, prefix="/api/finance", tags=["财务管理查询"])
app.include_router(month_end.router, prefix="/api/finance", tags=["月末结账"])
app.include_router(tax_check.router, prefix="/api/tax", tags=["税务核对"])
app.include_router(tax_declaration.router, prefix="/api/tax", tags=["税务申报"])
app.include_router(bank_reconcile.router, prefix="/api", tags=["银行对账"])
app.include_router(accounting_guide.router, prefix="/api", tags=["会计规则指引"])
# AI 能力发现接口（/api/_ai 前缀已在 AIGatewayMiddleware._SKIP_PREFIXES 放行）
app.include_router(ai_capabilities.router, prefix="/api/_ai", tags=["AI 能力发现"])
app.include_router(bootstrap.router, prefix="/api/bootstrap", tags=["初始化"])


def _load_truth_source_scanner():
    """从 tests/invariants/check_truth_source.py 加载模块（不污染 sys.path）"""
    import importlib.util
    scanner_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "tests", "invariants", "check_truth_source.py")
    )
    spec = importlib.util.spec_from_file_location("_truth_source_scanner", scanner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_truth_source_hard_constraints():
    """启动硬约束检查：
    1. 静态扫描 backend/ 源码（毫秒级）
       - ERROR 级别违规 → sys.exit(1) 拒绝启动
       - WARNING 级别违规 → 打日志警告
    2. 不变量测试 tests/invariants/test_truth_source_invariants.py（约 2-3 秒）
    - 任意测试失败 → sys.exit(1) 拒绝启动
    """
    if os.environ.get("SKIP_HARD_CONSTRAINTS") == "1":
        return
    # ── 1. 静态扫描 ──
    try:
        scanner = _load_truth_source_scanner()
        violations = scanner.scan()
    except Exception as e:
        logger.error(f"❌ Truth Source 扫描器加载失败：{e}")
        sys.exit(1)
        return

    errors = [v for v in violations if v["severity"] == "ERROR"]
    warnings = [v for v in violations if v["severity"] == "WARNING"]

    for v in warnings:
        logger.warning(
            f"[{v['rule_id']}] {v['file']}:{v['line']} - {v['message']} (修复: {v['fix_hint']})"
        )

    if errors:
        logger.error(
            f"❌ 启动检查失败：检测到 {len(errors)} 处 Truth Source Bypass ERROR 违规，拒绝启动："
        )
        for v in errors:
            logger.error(f"  [{v['rule_id']}] {v['file']}:{v['line']}")
            logger.error(f"    代码: {v['code']}")
            logger.error(f"    问题: {v['message']}")
            logger.error(f"    修复: {v['fix_hint']}")
        sys.exit(1)

    logger.info(
        f"✅ Truth Source 静态扫描通过（{len(warnings)} warning, 0 error）"
    )

    # ── 2. 不变量测试 ──
    import subprocess
    import re as _re
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    test_file = os.path.join(
        project_root, "tests", "invariants", "test_truth_source_invariants.py"
    )
    if not os.path.exists(test_file):
        logger.warning(f"不变量测试文件不存在: {test_file}，跳过")
        return

    logger.info("⏳ 跑不变量测试套件（约 2-3 秒）...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file,
             "-q", "--tb=line", "--no-header", "--color=no"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        logger.error("❌ 不变量测试超时（>60s），拒绝启动")
        sys.exit(1)
        return
    except FileNotFoundError:
        logger.error("❌ 找不到 pytest，请安装：pip install pytest")
        sys.exit(1)
        return

    if result.returncode != 0:
        logger.error("❌ 不变量测试失败，拒绝启动：")
        logger.error(result.stdout)
        if result.stderr:
            logger.error(result.stderr)
        sys.exit(1)

    m = _re.search(r"(\d+) passed", result.stdout)
    n = m.group(1) if m else "?"
    logger.info(f"✅ 不变量测试通过（{n} 个）")


# ── 图片上传API ──

from fastapi import UploadFile, File

@app.post("/api/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    business_type: str = "expense",
    record_id: int = 0
):
    """上传图片，文件名: {business_type}_{record_id}_{6位随机码}.{ext}"""
    if business_type not in BUSINESS_TYPES:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message=f"业务类型只能是: {', '.join(BUSINESS_TYPES)}")
    if file.content_type not in ALLOWED_TYPES:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="只支持 JPG/PNG/GIF/WEBP 格式图片")
    
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="图片大小不能超过5MB")
    
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
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="缺少 image_url 参数")
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
        raise BusinessError(code=ErrorCode.DUPLICATE_ENTRY, message="账本代码已存在，请使用不同的代码")


@app.put("/api/accounts/{account_id}", response_model=schemas.AccountOut)
def update_account(account_id: int, body: schemas.AccountUpdate, db: Session = Depends(get_db)):
    account = crud.update_account(db, account_id, body.name, body.taxpayer_type)
    if not account:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "账本"})
    db.commit()
    db.refresh(account)
    return account


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    try:
        if not crud.delete_account(db, account_id):
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "账本"})
        db.commit()
        return {"message": "账本已删除"}
    except ValueError:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "删除账本失败，请先清理关联数据"})


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
    class NoCacheStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):
            response = await super().get_response(path, scope)
            if path == "" or path.endswith(".html") or "text/html" in response.headers.get("content-type", ""):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            return response
    app.mount("/", NoCacheStaticFiles(directory=frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    import sys
    import uvicorn
    is_dev = (
        os.environ.get("ENV") == "development"
        or os.environ.get("DEV") == "1"
        or "--reload" in sys.argv
    )
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=is_dev,
        reload_dirs=["."] if is_dev else None
    )