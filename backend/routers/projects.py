from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from database import get_db
from auth import get_account_id
from account_dep import get_operator
from models import SaleOrder, PurchaseOrder, Project, Customer, ProjectCost, ProjectIncome, Product
import schemas
import crud
from crud.linkage import cost_restore_inventory
from utils import update_project_summary, verify_invariants
from uow import unit_of_work

router = APIRouter(tags=["projects"])

class ProjectCreate(BaseModel):
    name: str
    customer_id: Optional[int] = None
    status: str = "ongoing"
    start_date: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
async def get_projects(
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取项目列表（统一从 Project 表出发，通过 project_id 查询关联订单数）

    ★ 使用 GROUP BY 聚合一次查出关联订单数，避免 N+1 查询
    """
    projects = db.query(Project).filter(
        Project.account_id == account_id
    ).order_by(Project.created_at.desc()).all()

    if not projects:
        return {"items": []}

    project_ids = [p.id for p in projects]

    # ★ 批量聚合：一次查出所有项目的关联订单数
    sale_counts = dict(
        db.query(SaleOrder.project_id, sqlfunc.count(SaleOrder.id))
        .filter(SaleOrder.project_id.in_(project_ids))
        .group_by(SaleOrder.project_id).all()
    )
    purchase_counts = dict(
        db.query(PurchaseOrder.project_id, sqlfunc.count(PurchaseOrder.id))
        .filter(PurchaseOrder.project_id.in_(project_ids))
        .group_by(PurchaseOrder.project_id).all()
    )

    items = []
    for project in projects:
        items.append({
            "id": project.id,
            "name": project.name,
            "customer_name": project.customer.name if project.customer else None,
            "status": project.status,
            "total_income": project.total_income,
            "total_cost": project.total_cost,
            "profit": project.profit,
            "sale_count": sale_counts.get(project.id, 0),
            "purchase_count": purchase_counts.get(project.id, 0),
        })
    return {"items": items}


@router.get("/list")
async def get_project_list(
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取项目管理列表（机制B：基于Project表）"""
    projects = db.query(Project).filter(
        Project.account_id == account_id
    ).outerjoin(Customer).order_by(Project.created_at.desc()).all()

    items = []
    for project in projects:
        items.append({
            "id": project.id,
            "name": project.name,
            "customer_name": project.customer.name if project.customer else None,
            "status": project.status,
            "start_date": project.start_date.strftime("%Y-%m-%d") if project.start_date else None,
            "total_income": project.total_income,
            "total_cost": project.total_cost,
            "profit": project.profit,
            "notes": project.notes
        })

    return {"items": items}


@router.post("/")
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """创建项目"""
    # 验证客户是否存在且属于当前账户
    if project_data.customer_id:
        customer = db.query(Customer).filter(
            Customer.id == project_data.customer_id,
            Customer.account_id == account_id
        ).first()
        if not customer:
            raise HTTPException(status_code=404, detail="客户不存在")

    # 创建项目
    project = Project(
        name=project_data.name,
        customer_id=project_data.customer_id,
        status=project_data.status,
        start_date=datetime.strptime(project_data.start_date, "%Y-%m-%d") if project_data.start_date else None,
        notes=project_data.notes,
        account_id=account_id,
        total_income=0,
        total_cost=0,
        profit=0
    )

    with unit_of_work(db):
        db.add(project)
    db.refresh(project)

    return project


@router.get("/{project_id}/cost-income")
async def get_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取项目详情（成本+收入+采购单明细）"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.account_id == account_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    costs = db.query(ProjectCost).filter(
        ProjectCost.project_id == project_id
    ).all()

    incomes = db.query(ProjectIncome).filter(
        ProjectIncome.project_id == project_id
    ).all()

    # ★ 关联采购单
    purchases = db.query(PurchaseOrder).filter(
        PurchaseOrder.project_id == project_id,
        PurchaseOrder.account_id == account_id
    ).order_by(PurchaseOrder.purchase_date.desc()).all()

    # 批量查询商品名
    product_ids = list(set(c.product_id for c in costs if c.product_id))
    product_map = {}
    if product_ids:
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        product_map = {p.id: p.name for p in products}

    return {
        "id": project.id,
        "name": project.name,
        "customer_name": project.customer.name if project.customer else None,
        "status": project.status,
        "start_date": project.start_date.strftime("%Y-%m-%d") if project.start_date else None,
        "total_income": project.total_income,
        "total_cost": project.total_cost,
        "profit": project.profit,
        "notes": project.notes,
        "costs": [
            {
                "id": c.id,
                "cost_type": c.cost_type,
                "amount": c.amount,
                "payment_method": c.payment_method,
                "invoice_status": c.invoice_status,
                "supplier_name": c.supplier_name,
                "notes": c.notes,
                "image_url": c.image_url or "",
                "cost_date": c.cost_date.isoformat() if c.cost_date else None,
                "product_id": c.product_id,
                "quantity": c.quantity,
                "product_name": product_map.get(c.product_id) if c.product_id else None,
            } for c in costs
        ],
        "incomes": [
            {
                "id": i.id,
                "amount": i.amount,
                "payment_status": i.payment_status,
                "received_amount": i.received_amount,
                "invoice_status": i.invoice_status,
                "notes": i.notes,
                "income_date": i.income_date.isoformat() if i.income_date else None,
                "source_type": i.source_type,
                "source_id": i.source_id,
            } for i in incomes
        ],
        "purchases": [
            {
                "order_no": p.order_no,
                "supplier_name": p.supplier.name if p.supplier else None,
                "total_price": p.total_price,
                "status": p.status,
                "purchase_date": p.purchase_date.isoformat() if p.purchase_date else None
            } for p in purchases
        ]
    }


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    customer_id: Optional[int] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    notes: Optional[str] = None


@router.put("/manage/{project_id}")
def update_project_route(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    project = crud.update_project(db, account_id, project_id, project_data)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.delete("/manage/{project_id}")
def delete_project_route(
    project_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """删除项目（前置校验+级联回补库存）"""
    project = db.query(Project).filter(
        Project.id == project_id, Project.account_id == account_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # ── 前置校验：存在关联的未取消销售单/采购单时禁止删除 ──
    active_sales = db.query(SaleOrder).filter(
        SaleOrder.project_id == project_id,
        SaleOrder.status != "cancelled"
    ).count()
    if active_sales > 0:
        raise HTTPException(status_code=400,
            detail=f"项目下有 {active_sales} 条未取消的销售单，请先取消或解除关联")

    active_purchases = db.query(PurchaseOrder).filter(
        PurchaseOrder.project_id == project_id,
        PurchaseOrder.status != "cancelled"
    ).count()
    if active_purchases > 0:
        raise HTTPException(status_code=400,
            detail=f"项目下有 {active_purchases} 条未取消的采购单，请先取消或解除关联")

    with unit_of_work(db):
        # ── 级联回补：材料类成本的库存必须在 cascade 删除前回补 ──
        for cost in project.costs:
            cost_restore_inventory(db, account_id, cost, operator)

        db.delete(project)  # cascade 会自动删除关联的 costs/incomes

    return {"result": "项目已删除"}


@router.post("/verify-invariants")
async def verify_invariants_endpoint(
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """验证三大不变量（库存/收入/汇总），返回违规项"""
    return verify_invariants(db, account_id)


@router.post("/reconcile")
async def reconcile_endpoint(
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """对账：重算所有项目汇总，修复汇总不变量 III 违规"""
    projects = db.query(Project).filter(Project.account_id == account_id).all()
    fixed = []
    with unit_of_work(db):
        for project in projects:
            old_income = project.total_income
            old_cost = project.total_cost
            old_profit = project.profit
            update_project_summary(db, project.id)  # 只计算+赋值，不commit
            if (abs(old_income - project.total_income) > 0.01 or
                abs(old_cost - project.total_cost) > 0.01 or
                abs(old_profit - project.profit) > 0.01):
                fixed.append({
                    "project_id": project.id,
                    "name": project.name,
                    "before": {"income": old_income, "cost": old_cost, "profit": old_profit},
                    "after": {"income": project.total_income, "cost": project.total_cost, "profit": project.profit}
                })
    return {"fixed_count": len(fixed), "fixed": fixed}