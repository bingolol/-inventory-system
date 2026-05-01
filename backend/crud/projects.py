"""项目 CRUD（含事务包裹和金额精度）"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
import models, schemas
from datetime import datetime

from .base import _log

logger = logging.getLogger("inventory")


def create_project(db: Session, account_id: int, data):
    """创建项目"""
    db_project = models.Project(
        account_id=account_id,
        name=data.name,
        customer_id=data.customer_id,
        status=data.status or "ongoing",
        start_date=datetime.strptime(data.start_date, "%Y-%m-%d") if data.start_date else datetime.now(),
        end_date=datetime.strptime(data.end_date, "%Y-%m-%d") if data.end_date else None,
        notes=data.notes or ""
    )
    db.add(db_project)
    db.flush()
    _log(db, account_id, "create", "project", db_project.id, f"创建项目: {db_project.name}")
    return db_project


def update_project(db: Session, account_id: int, project_id: int, data):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.account_id == account_id
    ).first()
    if not project:
        return None
    changes = data.model_dump(exclude_unset=True)
    if 'start_date' in changes and changes['start_date']:
        changes['start_date'] = datetime.strptime(changes['start_date'], "%Y-%m-%d")
    for k, v in changes.items():
        setattr(project, k, v)
    _log(db, account_id, "update", "project", project.id, f"更新项目: {project.name}")
    db.flush()
    return project


def delete_project(db: Session, account_id: int, project_id: int):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.account_id == account_id
    ).first()
    if not project:
        return False
    _log(db, account_id, "delete", "project", project.id, f"删除项目: {project.name}")
    db.delete(project)
    db.flush()
    return True


def get_project_report(db: Session, account_id: int, project_id: int = None, start_date: str = None, end_date: str = None):
    """获取项目报表"""
    from utils import update_project_summary
    
    q = db.query(models.Project).filter(models.Project.account_id == account_id)
    if project_id:
        q = q.filter(models.Project.id == project_id)
    projects = q.all()
    
    project_data = []
    total_income = 0
    total_cost = 0
    total_profit = 0
    
    for project in projects:
        update_project_summary(db, project.id)
        db.refresh(project)
        
        costs = db.query(models.ProjectCost).filter(models.ProjectCost.project_id == project.id)
        incomes = db.query(models.ProjectIncome).filter(models.ProjectIncome.project_id == project.id)
        
        if start_date:
            costs = costs.filter(models.ProjectCost.cost_date >= start_date)
            incomes = incomes.filter(models.ProjectIncome.income_date >= start_date)
        if end_date:
            costs = costs.filter(models.ProjectCost.cost_date <= end_date + " 23:59:59")
            incomes = incomes.filter(models.ProjectIncome.income_date <= end_date + " 23:59:59")
        
        costs = costs.all()
        incomes = incomes.all()
        
        project_data.append({
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "total_income": round(project.total_income, 2),
            "total_cost": round(project.total_cost, 2),
            "profit": round(project.profit, 2),
            "costs": costs,
            "incomes": incomes
        })
        
        total_income += project.total_income
        total_cost += project.total_cost
        total_profit += project.profit
    
    return {
        "total_income": round(total_income, 2),
        "total_cost": round(total_cost, 2),
        "total_profit": round(total_profit, 2),
        "project_count": len(projects),
        "projects": project_data
    }