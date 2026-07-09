"""固定资产 Command + Handler

原 routers/fixed_assets.py 中直接调用 FixedAssetEngine 的折旧/处置端点下沉到本模块，
router 只负责 HTTP 解析 + dispatch。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import models
from commands.base import Command, CommandHandler, register
from crud.base import log_op
from engine_fixed_asset import FixedAssetEngine
from errors import BusinessError, ErrorCode
from finance_integration import reverse_journal
from operation_result import OperationType, EntityType, OperationResult


# ═══════════════════════════════════════════════════════════
# 1. DepreciateFixedAsset — 计提单个固定资产折旧
# ═══════════════════════════════════════════════════════════

@dataclass
class DepreciateFixedAsset(Command):
    asset_id: int = 0
    period: str = ""           # YYYY-MM


@register(DepreciateFixedAsset)
class DepreciateFixedAssetHandler(CommandHandler):
    # FixedAssetDepreciation / FixedAsset 字段由 FixedAssetEngine 写入，
    # 已在 engine_fixed_asset.py 声明；Handler 仅做编排，不再重复声明。
    def handle(self, cmd: DepreciateFixedAsset, db: Any) -> Any:
        eng = FixedAssetEngine(db, cmd.account_id)
        dep = eng.record_depreciation(cmd.asset_id, cmd.period)
        if dep is None:
            return {"message": "无需计提（已提足或不在计提期）", "depreciation_id": None}
        return {
            "message": f"折旧计提成功: {dep.amount_l2}",
            "depreciation_id": dep.id,
            "amount": str(dep.amount_l2),
        }


# ═══════════════════════════════════════════════════════════
# 2. BatchDepreciateFixedAssets — 批量计提折旧
# ═══════════════════════════════════════════════════════════

@dataclass
class BatchDepreciateFixedAssets(Command):
    period: str = ""           # YYYY-MM


@register(BatchDepreciateFixedAssets)
class BatchDepreciateFixedAssetsHandler(CommandHandler):
    # 批量折旧统一走 FinanceOrchestrator，由 orchestrator 分发到 FixedAssetEngine。
    def handle(self, cmd: BatchDepreciateFixedAssets, db: Any) -> Any:
        from finance_orchestrator import FinanceOrchestrator
        results = FinanceOrchestrator(db, cmd.account_id).batch_depreciate(cmd.period)
        return {
            "message": f"批量折旧完成: {len(results)}项资产已计提",
            "count": len(results),
            "details": [
                {"asset_id": d.asset_id, "period": d.period, "amount": str(d.amount_l2)}
                for d in results
            ],
        }


# ═══════════════════════════════════════════════════════════
# 3. DisposeFixedAsset — 处置固定资产
# ═══════════════════════════════════════════════════════════

@dataclass
class DisposeFixedAsset(Command):
    asset_id: int = 0
    disposal_price: Decimal = Decimal("0")
    disposal_date: str = ""            # YYYY-MM-DD
    bank_account_id: Optional[int] = None


@register(DisposeFixedAsset)
class DisposeFixedAssetHandler(CommandHandler):
    # 处置字段由 FixedAssetEngine.record_disposal 写入，引擎已声明 @writes。
    def handle(self, cmd: DisposeFixedAsset, db: Any) -> Any:
        parsed_date = None
        if cmd.disposal_date:
            try:
                parsed_date = datetime.strptime(cmd.disposal_date, "%Y-%m-%d").date()
            except ValueError:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"disposal_date 格式错误: {cmd.disposal_date}，应为 YYYY-MM-DD"
                )

        eng = FixedAssetEngine(db, cmd.account_id)
        eng.record_disposal(
            cmd.asset_id,
            cmd.disposal_price,
            disposal_date=parsed_date,
            bank_account_id=cmd.bank_account_id,
        )
        return {"message": "固定资产已处置"}


# ═══════════════════════════════════════════════════════════
# 4. ReverseDepreciation — 冲红单次折旧计提
# ═══════════════════════════════════════════════════════════

@dataclass
class ReverseDepreciation(Command):
    """冲红指定资产指定期间的折旧计提

    安全约束：
    - 资产状态为"已报废"或"已冲红"时拒绝冲红
    - 已处置的资产折旧不可冲回
    - 凭证冲红后，FixedAssetDepreciation 记录保留（审计追溯），标记 is_reversed=True
    """
    asset_id: int = 0
    period: str = ""               # YYYY-MM
    depreciation_id: Optional[int] = None   # 指定具体折旧记录 id（多笔时使用）


@register(ReverseDepreciation)
class ReverseDepreciationHandler(CommandHandler):
    def handle(self, cmd: ReverseDepreciation, db: Any) -> Any:
        account_id = cmd.account_id

        # 1. 校验资产状态
        asset = db.query(models.FixedAsset).filter(
            models.FixedAsset.id == cmd.asset_id,
            models.FixedAsset.account_id == account_id,
        ).first()
        if not asset:
            raise BusinessError(code=ErrorCode.FIXED_ASSET_NOT_FOUND, data={"asset_id": cmd.asset_id})
        if asset.status in ("已报废", "已冲红"):
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"资产 #{cmd.asset_id} 状态为 {asset.status}，禁止冲红折旧",
                ai_instruction="STOP_RETRYING. 已处置/已冲红资产的折旧不可冲回。",
            )

        # 2. 定位折旧记录
        from models_finance import FixedAssetDepreciation
        dep_q = db.query(FixedAssetDepreciation).filter(
            FixedAssetDepreciation.asset_id == cmd.asset_id,
        )
        if cmd.depreciation_id:
            dep_q = dep_q.filter(FixedAssetDepreciation.id == cmd.depreciation_id)
        else:
            dep_q = dep_q.filter(FixedAssetDepreciation.period == cmd.period)
        dep = dep_q.order_by(FixedAssetDepreciation.id.desc()).first()
        if not dep:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"未找到资产 #{cmd.asset_id} 期间 {cmd.period} 的折旧记录",
                data={"asset_id": cmd.asset_id, "period": cmd.period},
            )

        # 3. 冲红凭证（source_model="fixed_asset_depreciation", source_id=dep.id）
        move = reverse_journal(db, account_id, "fixed_asset_depreciation", dep.id, force=True)
        if not move:
            return {"message": "无原折旧凭证可冲红（可能已冲红）", "depreciation_id": dep.id}

        # 4. 回退累计折旧余额（FixedAsset.accumulated_depreciation_l4 是 L4 派生字段）
        asset.accumulated_depreciation_l4 = (asset.accumulated_depreciation_l4 or 0) - dep.amount_l2

        log_op(db, account_id, "reverse", "depreciation", dep.id,
               f"冲红折旧: 资产#{cmd.asset_id} 期间{cmd.period} 金额{dep.amount_l2}",
               operator=cmd.operator)

        return OperationResult(
            operation=OperationType.DELETE,
            entity_type=EntityType.DEPRECIATION,
            entity_id=dep.id,
            summary=f"折旧冲红成功，资产 #{cmd.asset_id} 期间 {cmd.period} 金额 {dep.amount_l2}",
            ai_hint="折旧已冲红，累计折旧已回退。",
            data={"asset_id": cmd.asset_id, "period": cmd.period, "amount": str(dep.amount_l2)},
        ).to_dict()


# ═══════════════════════════════════════════════════════════
# 5. ReverseAssetDisposal — 冲红资产处置
# ═══════════════════════════════════════════════════════════

@dataclass
class ReverseAssetDisposal(Command):
    """冲红固定资产处置（恢复资产卡片为在用状态）

    安全约束：
    - 资产必须处于"已报废"状态（处置后才能冲回）
    - "已冲红"状态拒绝重复冲回
    - 凭证冲红后，资产卡片恢复为"在用"
    - 处置冲红不回滚处置期间的折旧（如需调整折旧请用 ReverseDepreciation）
    """
    asset_id: int = 0


@register(ReverseAssetDisposal)
class ReverseAssetDisposalHandler(CommandHandler):
    def handle(self, cmd: ReverseAssetDisposal, db: Any) -> Any:
        account_id = cmd.account_id

        asset = db.query(models.FixedAsset).filter(
            models.FixedAsset.id == cmd.asset_id,
            models.FixedAsset.account_id == account_id,
        ).first()
        if not asset:
            raise BusinessError(code=ErrorCode.FIXED_ASSET_NOT_FOUND, data={"asset_id": cmd.asset_id})

        if asset.status == "已冲红":
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"资产 #{cmd.asset_id} 已被冲红（发票级冲红），不可重复操作",
                ai_instruction="STOP_RETRYING. 已冲红资产不可重复冲回。",
            )
        if asset.status != "已报废":
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"资产 #{cmd.asset_id} 状态为 {asset.status}，仅'已报废'状态可冲红处置",
                ai_instruction="STOP_RETRYING. 仅已报废资产的处置可冲回。",
            )

        # 冲红处置凭证（source_model="fixed_asset_disposal", source_id=asset_id）
        move = reverse_journal(db, account_id, "fixed_asset_disposal", cmd.asset_id, force=True)
        if not move:
            return {"message": "无原处置凭证可冲红（可能已冲红）", "asset_id": cmd.asset_id}

        # 恢复资产状态（FixedAsset 模型无处置日期/价格字段，仅状态标记）
        asset.status = "在用"

        log_op(db, account_id, "reverse", "asset_disposal", cmd.asset_id,
               f"冲红资产处置: 资产#{cmd.asset_id} 恢复在用",
               operator=cmd.operator)

        return OperationResult(
            operation=OperationType.DELETE,
            entity_type=EntityType.ASSET_DISPOSAL,
            entity_id=cmd.asset_id,
            summary=f"资产处置冲红成功，资产 #{cmd.asset_id} 恢复为在用",
            ai_hint="处置已冲红，资产恢复在用状态。如需调整折旧请单独调用 ReverseDepreciation。",
            data={"asset_id": cmd.asset_id, "status": "在用"},
        ).to_dict()
