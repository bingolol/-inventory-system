from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from decimal import Decimal
from models import Project, ProjectCost, ProjectIncome, PurchaseOrder

Q2 = Decimal('0.01')

def _d(val):
    """安全转换为 Decimal"""
    if val is None:
        return Decimal('0')
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def get_current_account():
    """获取当前账本ID（暂时返回默认值，实际应该从请求头获取）"""
    # 实际应该从请求头 X-Account-ID 获取
    return 1


def update_project_summary(db: Session, project_id: int):
    """更新项目汇总数据（统一利润计算：项目成本 + 采购成本）

    所有联动场景统一调用此函数，不再在各路由中手动增量累加。

    ★ 此函数只计算+赋值，不调用 db.commit()。
    由路由/服务层统一 commit，保证与联动操作在同一事务中原子生效。
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return

    # 1. 项目收入 = ProjectIncome 合计
    total_income = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(ProjectIncome.amount), 0)).filter(
        ProjectIncome.project_id == project_id
    ).scalar())

    # 2. 项目成本 = ProjectCost 合计
    project_cost = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(ProjectCost.amount), 0)).filter(
        ProjectCost.project_id == project_id
    ).scalar())

    # 3. 采购成本 = 关联该项目的已完成采购单合计
    purchase_cost = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(PurchaseOrder.total_price), 0)).filter(
        PurchaseOrder.project_id == project_id,
        PurchaseOrder.status == "completed"
    ).scalar())

    # 4. 统一利润
    total_cost = project_cost + purchase_cost
    profit = total_income - total_cost

    project.total_income = total_income.quantize(Q2)
    project.total_cost = total_cost.quantize(Q2)
    project.profit = profit.quantize(Q2)
    # ★ 不 commit，由调用方统一 commit


def verify_invariants(db: Session, account_id: int = None) -> dict:
    """验证三大不变量，返回违规项列表

    可在测试中调用，也可通过 /api/projects/verify-invariants API 触发。
    """
    violations = []

    # ── 不变量 I：库存不变量 ──
    # 硬校验：所有 inventory.quantity >= 0
    from models import Inventory
    query = db.query(Inventory)
    if account_id:
        query = query.filter(Inventory.account_id == account_id)
    negative_inv = query.filter(Inventory.quantity < 0).all()
    for inv in negative_inv:
        violations.append({
            "invariant": "I",
            "type": "negative_inventory",
            "detail": f"商品ID={inv.product_id} 库存={inv.quantity} < 0"
        })

    # ── 不变量 II：收入不变量 ──
    # 校验：同一 source_type + source_id 最多一条记录
    from models import ProjectIncome
    duplicates = db.query(
        ProjectIncome.source_type, ProjectIncome.source_id,
        sqlfunc.count(ProjectIncome.id).label("cnt")
    ).filter(
        ProjectIncome.source_type.isnot(None),
        ProjectIncome.source_id.isnot(None)
    ).group_by(
        ProjectIncome.source_type, ProjectIncome.source_id
    ).having(sqlfunc.count(ProjectIncome.id) > 1).all()
    for source_type, source_id, cnt in duplicates:
        violations.append({
            "invariant": "II",
            "type": "duplicate_income",
            "detail": f"source_type={source_type}, source_id={source_id} 存在{cnt}条记录（应最多1条）"
        })

    # ── 不变量 III：汇总不变量 ──
    # 校验：projects.total_income/total_cost/profit 与明细重算一致
    from models import Project, PurchaseOrder
    projects_query = db.query(Project)
    if account_id:
        projects_query = projects_query.filter(Project.account_id == account_id)
    for project in projects_query.all():
        calc_income = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(ProjectIncome.amount), 0)).filter(
            ProjectIncome.project_id == project.id
        ).scalar())
        calc_cost = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(ProjectCost.amount), 0)).filter(
            ProjectCost.project_id == project.id
        ).scalar())
        calc_purchase = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(PurchaseOrder.total_price), 0)).filter(
            PurchaseOrder.project_id == project.id,
            PurchaseOrder.status == "completed"
        ).scalar())
        calc_total_cost = calc_cost + calc_purchase
        calc_profit = calc_income - calc_total_cost

        if _d(project.total_income) != calc_income.quantize(Q2):
            violations.append({
                "invariant": "III",
                "type": "income_mismatch",
                "detail": f"项目ID={project.id} stored_total_income={project.total_income} != calc={calc_income.quantize(Q2)}"
            })
        if _d(project.total_cost) != calc_total_cost.quantize(Q2):
            violations.append({
                "invariant": "III",
                "type": "cost_mismatch",
                "detail": f"项目ID={project.id} stored_total_cost={project.total_cost} != calc={calc_total_cost.quantize(Q2)}"
            })
        if _d(project.profit) != calc_profit.quantize(Q2):
            violations.append({
                "invariant": "III",
                "type": "profit_mismatch",
                "detail": f"项目ID={project.id} stored_profit={project.profit} != calc={calc_profit.quantize(Q2)}"
            })

    return {
        "ok": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations
    }