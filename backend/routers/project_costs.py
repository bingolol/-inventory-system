from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import Project, ProjectCost, ProjectIncome, Product
from image_utils import delete_old_image
import schemas
from account_dep import get_account_id, get_operator
from enums import COST_TYPES
import crud
from crud.linkage import cost_deduct_inventory, cost_restore_inventory, cost_update_inventory
from utils import update_project_summary
from uow import unit_of_work

router = APIRouter()


@router.post("/")
def add_project_cost(
    cost_data: schemas.ProjectCostCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """添加项目成本"""
    project_id = cost_data.project_id
    if not project_id:
        raise HTTPException(status_code=400, detail="缺少项目ID")
    
    # 验证项目存在
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.account_id == account_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 校验成本类型
    if cost_data.cost_type not in COST_TYPES:
        raise HTTPException(status_code=422, detail=f"cost_type '{cost_data.cost_type}' not in {COST_TYPES}")
    
    # 创建成本记录
    cost = ProjectCost(
        project_id=project_id,
        cost_type=cost_data.cost_type,
        amount=cost_data.amount,
        payment_method=cost_data.payment_method,
        invoice_status=cost_data.invoice_status,
        supplier_name=cost_data.supplier_name,
        notes=cost_data.notes,
        product_id=cost_data.product_id,
        quantity=cost_data.quantity,
    )
    
    if cost_data.cost_date:
        from datetime import datetime as dt
        try:
            cost.cost_date = dt.strptime(cost_data.cost_date, "%Y-%m-%d")
        except:
            pass
    
    try:
        with unit_of_work(db):
            db.add(cost)
            db.flush()

            # ★ 联动：材料类成本扣减库存（不变量 I）
            cost_deduct_inventory(db, account_id, cost, operator)

            # ★ 统一重算项目汇总（不变量 III，在 commit 之前）
            update_project_summary(db, cost.project_id)

            # 记录操作日志（与业务数据同一事务）
            crud._log(db, account_id, "create", "project_cost", cost.id,
                      f"添加成本:{cost.cost_type} {cost.amount}", operator=operator)
    except HTTPException:
        raise
    except Exception:
        raise
    db.refresh(cost)

    # 查询商品名用于展示
    product_name = None
    if cost.product_id:
        p = db.query(Product).filter(Product.id == cost.product_id).first()
        if p:
            product_name = p.name

    return schemas.ProjectCostOut(
        id=cost.id,
        project_id=cost.project_id,
        cost_type=cost.cost_type,
        amount=cost.amount,
        payment_method=cost.payment_method,
        invoice_status=cost.invoice_status,
        supplier_name=cost.supplier_name,
        notes=cost.notes,
        image_url=cost.image_url or "",
        cost_date=cost.cost_date.isoformat() if cost.cost_date else None,
        product_id=cost.product_id,
        quantity=cost.quantity,
        product_name=product_name,
        created_at=cost.created_at
    )


@router.post("/incomes/")
def add_project_income(
    income_data: schemas.ProjectIncomeCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """添加项目收入"""
    project_id = income_data.project_id
    if not project_id:
        raise HTTPException(status_code=400, detail="缺少项目ID")
    
    # 验证项目存在
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.account_id == account_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 创建收入记录
    income = ProjectIncome(
        project_id=project_id,
        amount=income_data.amount,
        payment_status=income_data.payment_status,
        received_amount=income_data.received_amount,
        invoice_status=income_data.invoice_status,
        notes=income_data.notes,
        source_type=income_data.source_type or "manual",
        source_id=income_data.source_id,
    )
    
    if income_data.income_date:
        from datetime import datetime as dt
        try:
            income.income_date = dt.strptime(income_data.income_date, "%Y-%m-%d")
        except:
            pass
    
    if income_data.received_date:
        from datetime import datetime as dt
        try:
            income.received_date = dt.strptime(income_data.received_date, "%Y-%m-%d")
        except:
            pass
    
    try:
        with unit_of_work(db):
            db.add(income)
            db.flush()

            # ★ 统一重算项目汇总（不变量 III）
            update_project_summary(db, income.project_id)

            # 记录操作日志（与业务数据同一事务）
            crud._log(db, account_id, "create", "project_income", income.id,
                      f"添加收入:{income.amount}", operator=operator)
    except HTTPException:
        raise
    except Exception:
        raise
    db.refresh(income)

    return schemas.ProjectIncomeOut(
        id=income.id,
        project_id=income.project_id,
        amount=income.amount,
        payment_status=income.payment_status,
        received_amount=income.received_amount,
        invoice_status=income.invoice_status,
        notes=income.notes,
        income_date=income.income_date.isoformat() if income.income_date else None,
        received_date=income.received_date.isoformat() if income.received_date else None,
        source_type=income.source_type,
        source_id=income.source_id,
        created_at=income.created_at
    )


@router.get("/")
def list_project_costs(
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取项目成本列表"""
    query = db.query(ProjectCost).join(Project).filter(Project.account_id == account_id)
    if project_id:
        query = query.filter(ProjectCost.project_id == project_id)
    total = query.count()
    items = query.offset(skip).limit(limit).all()

    # 批量查询商品名
    product_ids = list(set(c.product_id for c in items if c.product_id))
    product_map = {}
    if product_ids:
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        product_map = {p.id: p.name for p in products}

    return {
        "total": total,
        "items": [
            schemas.ProjectCostOut(
                id=c.id,
                project_id=c.project_id,
                cost_type=c.cost_type,
                amount=c.amount,
                payment_method=c.payment_method,
                invoice_status=c.invoice_status,
                supplier_name=c.supplier_name,
                notes=c.notes,
                image_url=c.image_url or "",
                cost_date=c.cost_date.isoformat() if c.cost_date else None,
                product_id=c.product_id,
                quantity=c.quantity,
                product_name=product_map.get(c.product_id) if c.product_id else None,
                created_at=c.created_at
            ).model_dump() for c in items
        ]
    }


@router.get("/incomes/")
def list_project_incomes(
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取项目收入列表"""
    query = db.query(ProjectIncome).join(Project).filter(Project.account_id == account_id)
    if project_id:
        query = query.filter(ProjectIncome.project_id == project_id)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            schemas.ProjectIncomeOut(
                id=i.id,
                project_id=i.project_id,
                amount=i.amount,
                payment_status=i.payment_status,
                received_amount=i.received_amount,
                invoice_status=i.invoice_status,
                notes=i.notes,
                income_date=i.income_date.isoformat() if i.income_date else None,
                received_date=i.received_date.isoformat() if i.received_date else None,
                source_type=i.source_type,
                source_id=i.source_id,
                created_at=i.created_at
            ).model_dump() for i in items
        ]
    }


@router.put("/{cost_id}")
def update_project_cost(
    cost_id: int,
    cost_update: schemas.ProjectCostUpdate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """更新项目成本"""
    cost = db.query(ProjectCost).join(Project).filter(
        ProjectCost.id == cost_id,
        Project.account_id == account_id
    ).first()

    if not cost:
        raise HTTPException(status_code=404, detail="成本记录不存在")

    # ★ 记录旧值（允许 None：旧记录可能没有 product_id/quantity）
    old_cost_type = cost.cost_type
    old_product_id = cost.product_id
    old_quantity = cost.quantity

    # 校验成本类型（仅当修改了 cost_type 时）
    if cost_update.cost_type is not None and cost_update.cost_type not in COST_TYPES:
        raise HTTPException(status_code=422, detail=f"cost_type '{cost_update.cost_type}' not in {COST_TYPES}")

    # 更新字段
    update_data = cost_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "cost_date" and value:
            try:
                setattr(cost, field, datetime.strptime(value, "%Y-%m-%d"))
            except:
                pass
        elif field not in ("unit_price",):  # unit_price 仅前端辅助用，不存储
            setattr(cost, field, value)

    try:
        with unit_of_work(db):
            # ★ 联动：先回补旧的，再扣减新的（不变量 I）
            cost_update_inventory(db, account_id, cost,
                                  old_cost_type, old_product_id, old_quantity, operator)

            # ★ 统一重算项目汇总（不变量 III）
            update_project_summary(db, cost.project_id)

            # 记录操作日志（与业务数据同一事务）
            crud._log(db, account_id, "update", "project_cost", cost.id,
                      f"更新成本:{cost.cost_type} {cost.amount}", operator=operator)
    except HTTPException:
        raise
    except Exception:
        raise
    db.refresh(cost)

    # 查询商品名
    product_name = None
    if cost.product_id:
        p = db.query(Product).filter(Product.id == cost.product_id).first()
        if p:
            product_name = p.name

    return schemas.ProjectCostOut(
        id=cost.id,
        project_id=cost.project_id,
        cost_type=cost.cost_type,
        amount=cost.amount,
        payment_method=cost.payment_method,
        invoice_status=cost.invoice_status,
        supplier_name=cost.supplier_name,
        notes=cost.notes,
        image_url=cost.image_url or "",
        cost_date=cost.cost_date.isoformat() if cost.cost_date else None,
        product_id=cost.product_id,
        quantity=cost.quantity,
        product_name=product_name,
        created_at=cost.created_at
    )


@router.delete("/{cost_id}")
def delete_project_cost(
    cost_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """删除项目成本"""
    cost = db.query(ProjectCost).join(Project).filter(
        ProjectCost.id == cost_id,
        Project.account_id == account_id
    ).first()

    if not cost:
        raise HTTPException(status_code=404, detail="成本记录不存在")

    project_id = cost.project_id  # ★ 先保存，删除后 cost 对象失效

    try:
        with unit_of_work(db):
            # ★ 联动：材料类成本回补库存（不变量 I，在 delete 之前）
            cost_restore_inventory(db, account_id, cost, operator)

            # 删除关联图片文件
            if cost.image_url:
                delete_old_image(cost.image_url)

            db.delete(cost)

            # ★ 统一重算项目汇总（不变量 III）
            update_project_summary(db, project_id)

            # 记录操作日志（与业务数据同一事务）
            crud._log(db, account_id, "delete", "project_cost", cost_id,
                      f"删除成本:{cost.cost_type} {cost.amount}", operator=operator)
    except HTTPException:
        raise
    except Exception:
        raise

    return {"message": "成本删除成功"}


@router.put("/incomes/{income_id}")
def update_project_income(
    income_id: int,
    income_update: schemas.ProjectIncomeCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """更新项目收入"""
    income = db.query(ProjectIncome).join(Project).filter(
        ProjectIncome.id == income_id,
        Project.account_id == account_id
    ).first()
    if not income:
        raise HTTPException(status_code=404, detail="收入记录不存在")

    # ★ 保护：sale_order 自动生成的收入，不允许通过此接口修改金额/项目
    if income.source_type == "sale_order":
        raise HTTPException(status_code=400, detail="销售单自动生成的收入不可手动修改，请通过销售单操作")

    try:
        with unit_of_work(db):
            income.amount = income_update.amount
            income.payment_status = income_update.payment_status
            income.received_amount = income_update.received_amount or 0
            income.invoice_status = income_update.invoice_status
            income.notes = income_update.notes

            if income_update.income_date:
                try:
                    income.income_date = datetime.strptime(income_update.income_date, "%Y-%m-%d")
                except:
                    pass
            if income_update.received_date:
                try:
                    income.received_date = datetime.strptime(income_update.received_date, "%Y-%m-%d")
                except:
                    pass

            # ★ 统一重算项目汇总（不变量 III）
            update_project_summary(db, income.project_id)

            # 记录操作日志（与业务数据同一事务）
            crud._log(db, account_id, "update", "project_income", income.id,
                      f"更新收入:{income.amount}", operator=operator)
    except HTTPException:
        raise
    except Exception:
        raise
    db.refresh(income)

    return schemas.ProjectIncomeOut(
        id=income.id, project_id=income.project_id, amount=income.amount,
        payment_status=income.payment_status, received_amount=income.received_amount,
        invoice_status=income.invoice_status, notes=income.notes,
        income_date=income.income_date.isoformat() if income.income_date else None,
        received_date=income.received_date.isoformat() if income.received_date else None,
        source_type=income.source_type,
        source_id=income.source_id,
        created_at=income.created_at
    )


@router.delete("/incomes/{income_id}")
def delete_project_income(
    income_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """删除项目收入"""
    income = db.query(ProjectIncome).join(Project).filter(
        ProjectIncome.id == income_id,
        Project.account_id == account_id
    ).first()
    if not income:
        raise HTTPException(status_code=404, detail="收入记录不存在")

    # ★ 保护：sale_order 自动生成的收入，不允许手动删除，应通过销售单联动删除
    if income.source_type == "sale_order":
        raise HTTPException(status_code=400, detail="销售单自动生成的收入不可手动删除，请通过销售单操作")

    project_id = income.project_id  # ★ 先保存

    try:
        with unit_of_work(db):
            db.delete(income)

            # ★ 统一重算项目汇总（不变量 III）
            update_project_summary(db, project_id)

            # 记录操作日志（与业务数据同一事务）
            crud._log(db, account_id, "delete", "project_income", income_id,
                      f"删除收入:{income.amount}", operator=operator)
    except HTTPException:
        raise
    except Exception:
        raise

    return {"message": "收入删除成功"}