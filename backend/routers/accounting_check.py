"""会计准则约束检查接口 - 让端侧Agent在操作前验证是否符合会计准则"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from typing import Optional

from database import get_db
from account_dep import get_account_id
import models
from accounting_engine import AccountingEngine, AccountingError, AccountingErrorCode
from utils import _d
from policy.entity_profile import EntityProfile
from policy.policy_engine import calculate_vat as policy_vat, calculate_income_tax as policy_income_tax

router = APIRouter()
_engine = AccountingEngine()


@router.get("/invoice-amounts")
def check_invoice_amounts(
    amount_with_tax: Decimal = Query(..., description="含税金额"),
    tax_amount: Decimal = Query(..., description="税额（发票上的实际值）"),
    account_id: int = Depends(get_account_id),
):
    """检查发票金额等式：不含税金额 + 税额 == 含税金额（BR-27: 税额手动输入，不推导）"""
    amount_without_tax = amount_with_tax - tax_amount
    diff = amount_without_tax + tax_amount - amount_with_tax

    if diff != Decimal("0"):
        return {
            "valid": False,
            "violations": [
                f"金额不平衡：不含税 {amount_without_tax} + 税额 {tax_amount} = {amount_without_tax + tax_amount} ≠ 含税 {amount_with_tax}（差额 {diff}）"
            ],
            "ai_instruction": "STOP_RETRYING. 发票金额计算错误。含税金额务必等于 不含税金额 + 税额。",
            "accounting_rule": "《小企业会计准则》第十五条：收入按从购买方已收或应收的合同价款确定"
        }

    return {
        "valid": True,
        "result": {
            "amount_without_tax": float(amount_without_tax),
            "tax_amount": float(tax_amount),
            "amount_with_tax": float(amount_with_tax),
        },
        "rules": [
            "发票金额三件套：不含税金额 + 税额 = 含税金额",
            f"计算：{float(amount_without_tax)} + {float(tax_amount)} = {float(amount_with_tax)}"
        ],
        "ai_instruction": "发票金额计算正确，可以继续。"
    }


@router.get("/depreciation")
def check_depreciation(
    method: str = Query(..., description="折旧方法: 直线法/双倍余额递减法/年数总和法"),
    original_value: Decimal = Query(..., description="原值"),
    salvage_rate: Optional[Decimal] = Query(default=None, description="残值率（不传则从账本固定资产配置读取）"),
    useful_life: int = Query(..., gt=0, description="使用寿命(月)"),
    months_used: int = Query(..., gt=0, description="已使用月数"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """检查固定资产折旧计算是否正确"""
    # 残值率默认从 L3 政策配置读取（取该账本第一个固定资产的配置）
    if salvage_rate is None:
        fa = db.query(models.FixedAsset).filter(
            models.FixedAsset.account_id == account_id,
        ).first()
        salvage_rate = fa.salvage_rate_l3 if fa and fa.salvage_rate_l3 is not None else Decimal("0.05")
    else:
        salvage_rate = Decimal(str(salvage_rate))
    violations = []

    if useful_life <= 0:
        violations.append("使用寿命必须大于0")

    if salvage_rate < 0 or salvage_rate > 1:
        violations.append("残值率必须在0-1之间")

    if original_value <= 0:
        violations.append("原值必须大于0")

    if violations:
        return {
            "valid": False,
            "violations": violations,
            "ai_instruction": "STOP_RETRYING. 参数校验失败，请检查原值、残值率、使用寿命是否正确。",
            "accounting_rule": "《小企业会计准则》第三十条：固定资产折旧采用年限平均法"
        }

    if method == "直线法":
        result = _engine.calculate_depreciation_straight_line(original_value, salvage_rate, useful_life, months_used)
    elif method == "双倍余额递减法":
        result = _engine.calculate_depreciation_double_declining(original_value, useful_life, months_used)
    elif method == "年数总和法":
        result = _engine.calculate_depreciation_sum_of_years(original_value, salvage_rate, useful_life, months_used)
    else:
        return {
            "valid": False,
            "violations": [f"不支持的折旧方法: {method}，合法值：直线法、双倍余额递减法、年数总和法"],
            "ai_instruction": f"STOP_RETRYING. 折旧方法不合法，请使用：直线法、双倍余额递减法、年数总和法。",
            "accounting_rule": "《小企业会计准则》第三十条"
        }

    return {
        "valid": True,
        "result": {
            "monthly_depreciation": float(result.monthly_depreciation),
            "accumulated_depreciation": float(result.accumulated_depreciation),
            "net_value": float(result.net_value),
        },
        "rules": [
            f"折旧方法：{method}",
            f"原值：{original_value}，残值率：{salvage_rate}，使用寿命：{useful_life}个月",
            f"已使用：{months_used}个月",
            f"月折旧：{result.monthly_depreciation}",
            f"累计折旧：{result.accumulated_depreciation}",
            f"净值：{result.net_value}"
        ],
        "ai_instruction": "折旧计算正确，可以继续。"
    }


@router.get("/amortization")
def check_amortization(
    original_value: Decimal = Query(..., description="无形资产原值"),
    useful_life: int = Query(..., gt=0, description="使用寿命(月)"),
    months_used: int = Query(..., ge=0, description="已使用月数"),
    account_id: int = Depends(get_account_id),
):
    """检查无形资产摊销计算是否正确

    依据：《小企业会计准则》§二/2.3 无形资产摊销 + 第四十一条
    公式：月摊销额 = 原值 ÷ 使用寿命(月)；累计摊销 = 月摊销额 × min(已用月数, 使用寿命)
    """
    violations = []

    if useful_life <= 0:
        violations.append("使用寿命必须大于0")

    if original_value <= 0:
        violations.append("原值必须大于0")

    if violations:
        return {
            "valid": False,
            "violations": violations,
            "ai_instruction": "STOP_RETRYING. 参数校验失败，请检查原值、使用寿命是否正确。",
            "accounting_rule": "《小企业会计准则》第四十一条：无形资产应当在其使用寿命内采用年限平均法进行摊销"
        }

    result = _engine.calculate_intangible_amortization(original_value, useful_life, months_used)

    return {
        "valid": True,
        "result": {
            "monthly_amortization": float(result.monthly_amortization),
            "accumulated_amortization": float(result.accumulated_amortization),
            "net_value": float(result.net_value),
        },
        "rules": [
            f"原值：{original_value}，使用寿命：{useful_life}个月",
            f"已使用：{months_used}个月",
            f"月摊销：{result.monthly_amortization}",
            f"累计摊销：{result.accumulated_amortization}",
            f"净值：{result.net_value}"
        ],
        "ai_instruction": "摊销计算正确，可以继续。"
    }


@router.get("/balance-sheet")
def check_balance_sheet(
    date: str = Query(..., description="报表日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """检查资产负债表是否平衡"""
    import crud

    try:
        balance_sheet = crud.generate_balance_sheet(db, account_id, date)
        total_assets = balance_sheet.get("total_assets", 0)
        total_liabilities = balance_sheet.get("total_liabilities", 0)
        total_equity = balance_sheet.get("total_equity", 0)

        diff = abs(Decimal(str(total_assets)) - Decimal(str(total_liabilities)) - Decimal(str(total_equity)))

        if diff > Decimal("0.01"):
            return {
                "valid": False,
                "violations": [
                    f"资产负债表不平衡：资产={total_assets}，负债={total_liabilities}，权益={total_equity}"
                ],
                "ai_instruction": "STOP_RETRYING. 资产负债表不平衡，请检查：1) 期初余额是否正确；2) 收支记录是否完整；3) 金额计算是否正确。",
                "accounting_rule": "《小企业会计准则》第二十一条：资产 = 负债 + 所有者权益"
            }

        return {
            "valid": True,
            "result": {
                "total_assets": float(total_assets),
                "total_liabilities": float(total_liabilities),
                "total_equity": float(total_equity),
            },
            "rules": [
                f"资产 = 负债 + 权益",
                f"{total_assets} = {total_liabilities} + {total_equity}",
                "资产负债表平衡"
            ],
            "ai_instruction": "资产负债表平衡，可以继续。"
        }
    except AccountingError:
        raise  # 会计错误冒泡到全局 handler
    except Exception as e:
        return {
            "valid": False,
            "violations": [f"生成资产负债表失败: {str(e)}"],
            "ai_instruction": f"STOP_RETRYING. 生成资产负债表失败，请检查期初余额是否已设置。"
        }


@router.get("/vat")
def check_vat(
    total_revenue: Decimal = Query(..., description="不含税销售额"),
    taxpayer_type: Optional[str] = Query(default=None, description="纳税人类型: small_scale/general（不传则从账本配置读取）"),
    input_tax: Decimal = Query(default=Decimal("0"), description="进项税额（一般纳税人）"),
    output_tax: Optional[Decimal] = Query(default=None, description="销项税额（一般纳税人必填，取自发票明细汇总）"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """检查增值税计算是否正确"""
    try:
        # 纳税人类型默认从 L3 政策配置读取
        if taxpayer_type is None:
            account = db.query(models.Account).filter(models.Account.id == account_id).first()
            taxpayer_type = account.taxpayer_type_l3 if account and account.taxpayer_type_l3 else "small_scale"
        if taxpayer_type not in ("small_scale", "general"):
            raise AccountingError(
                code=AccountingErrorCode.VAT_TAXPAYER_TYPE_INVALID,
                message=f"无效的纳税人类型：{taxpayer_type}",
                ai_instruction="STOP_RETRYING. 纳税人类型只能是 small_scale（小规模）或 general（一般）"
            )
        profile = EntityProfile(
            vat_type=taxpayer_type,
            income_type="small_micro" if taxpayer_type == "small_scale" else "general",
            surcharge_halved=taxpayer_type == "small_scale",
            effective_date=date.today(),
        )
        result = policy_vat(profile, total_revenue, input_tax, output_tax)

        return {
            "valid": True,
            "result": {
                "total_revenue": float(result.total_revenue),
                "tax_rate": float(result.tax_rate),
                "tax_payable_gross": float(result.tax_payable_gross),
                "tax_payable": float(result.tax_payable),
            },
            "rules": [
                f"纳税人类型：{taxpayer_type}",
                f"税率：{result.tax_rate}",
                f"销项税额：{result.tax_payable_gross}",
                f"进项税额：{input_tax}",
                f"应纳税额：{result.tax_payable}",
            ],
            "ai_instruction": "增值税计算正确，可以继续。"
        }
    except AccountingError:
        raise  # 会计错误冒泡到全局 handler,保留 code/accounting_rule/calculation_detail
    except Exception as e:
        return {
            "valid": False,
            "violations": [str(e)],
            "ai_instruction": f"STOP_RETRYING. 增值税计算失败：{str(e)}"
        }


@router.get("/income-tax")
def check_income_tax(
    profit: Decimal = Query(..., description="利润总额"),
    taxpayer_type: Optional[str] = Query(default=None, description="纳税人类型: small_micro/general（不传则从账本配置读取）"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """检查所得税计算是否正确"""
    try:
        # 纳税人类型默认从 L3 政策配置读取
        if taxpayer_type is None:
            account = db.query(models.Account).filter(models.Account.id == account_id).first()
            if account:
                taxpayer_type = "small_micro" if account.taxpayer_type_l3 == "small_scale" else "general"
                if account.type == "personal":
                    taxpayer_type = "personal"
            else:
                taxpayer_type = "small_micro"
        profile = EntityProfile(
            vat_type="" if taxpayer_type == "personal" else "general",
            income_type="personal" if taxpayer_type == "personal"
                else ("small_micro" if taxpayer_type in ("small_scale", "small_micro") else "general"),
            surcharge_halved=taxpayer_type in ("small_scale", "small_micro", "personal"),
            effective_date=date.today(),
        )
        result = policy_income_tax(profile, profit)

        return {
            "valid": True,
            "result": {
                "profit": float(result.profit),
                "tax_rate": float(result.tax_rate),
                "tax_payable": float(result.tax_payable),
                "reduction_item": result.reduction_item,
            },
            "rules": [
                f"纳税人类型：{taxpayer_type}",
                f"法定税率：{result.tax_rate}",
                f"应纳税所得额：{result.profit}",
                f"应纳税额：{result.tax_payable}",
                f"优惠说明：{result.reduction_item}",
            ],
            "ai_instruction": "所得税计算正确，可以继续。"
        }
    except AccountingError:
        raise  # 会计错误冒泡到全局 handler,保留 code/accounting_rule/calculation_detail
    except Exception as e:
        return {
            "valid": False,
            "violations": [str(e)],
            "ai_instruction": f"STOP_RETRYING. 所得税计算失败：{str(e)}"
        }


@router.get("/income-statement")
def check_income_statement(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """检查利润表等式是否正确"""
    import crud

    try:
        income_statement = crud.generate_income_statement(db, account_id, start_date, end_date)

        revenue = income_statement.get("revenue", 0)
        cost_of_goods_sold = income_statement.get("cost_of_goods_sold", 0)
        gross_profit = income_statement.get("gross_profit", 0)
        total_operating_expenses = income_statement.get("total_operating_expenses", 0)
        operating_profit = income_statement.get("operating_profit", 0)
        net_profit = income_statement.get("net_profit", 0)

        # 校验：毛利 = 收入 - 成本
        expected_gross_profit = revenue - cost_of_goods_sold
        gross_diff = abs(Decimal(str(gross_profit)) - Decimal(str(expected_gross_profit)))

        # 校验：营业利润 = 毛利 - 费用
        expected_operating_profit = Decimal(str(gross_profit)) - Decimal(str(total_operating_expenses))
        operating_diff = abs(Decimal(str(operating_profit)) - expected_operating_profit)

        violations = []
        if gross_diff > Decimal("0.01"):
            violations.append(f"毛利计算错误：收入{revenue} - 成本{cost_of_goods_sold} = {expected_gross_profit}，但报表显示{gross_profit}")
        if operating_diff > Decimal("0.01"):
            violations.append(f"营业利润计算错误：毛利{gross_profit} - 费用{total_operating_expenses} = {expected_operating_profit}，但报表显示{operating_profit}")

        if violations:
            return {
                "valid": False,
                "violations": violations,
                "ai_instruction": "STOP_RETRYING. 利润表等式校验失败，请检查收入、成本、费用计算。"
            }

        return {
            "valid": True,
            "result": income_statement,
            "rules": [
                f"毛利 = 收入 - 成本 = {revenue} - {cost_of_goods_sold} = {gross_profit}",
                f"营业利润 = 毛利 - 费用 = {gross_profit} - {total_operating_expenses} = {operating_profit}",
                f"净利润 = {net_profit}",
            ],
            "ai_instruction": "利润表等式正确，可以继续。"
        }
    except AccountingError:
        raise  # 会计错误冒泡到全局 handler
    except Exception as e:
        return {
            "valid": False,
            "violations": [f"生成利润表失败: {str(e)}"],
            "ai_instruction": f"STOP_RETRYING. 生成利润表失败，请检查业务数据是否完整。"
        }


@router.get("/cash-flow")
def check_cash_flow_statement(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """检查现金流量表等式是否正确"""
    import crud

    try:
        cash_flow = crud.generate_cash_flow_statement(db, account_id, start_date, end_date)

        operating = cash_flow.get("operating_activities", {})
        investing = cash_flow.get("investing_activities", {})
        financing = cash_flow.get("financing_activities", {})

        net_operating = operating.get("net", 0)
        net_investing = investing.get("net", 0)
        net_financing = financing.get("net", 0)
        net_cash_flow = cash_flow.get("net_cash_flow", 0)

        # 校验：净现金流 = 经营净额 + 投资净额 + 筹资净额
        expected_net = Decimal(str(net_operating)) + Decimal(str(net_investing)) + Decimal(str(net_financing))
        diff = abs(Decimal(str(net_cash_flow)) - expected_net)

        if diff > Decimal("0.01"):
            return {
                "valid": False,
                "violations": [f"净现金流计算错误：经营{net_operating} + 投资{net_investing} + 筹资{net_financing} = {expected_net}，但报表显示{net_cash_flow}"],
                "ai_instruction": "STOP_RETRYING. 现金流量表等式校验失败，请检查经营、投资、筹资活动计算。"
            }

        return {
            "valid": True,
            "result": cash_flow,
            "rules": [
                f"经营活动净额：{net_operating}",
                f"投资活动净额：{net_investing}",
                f"筹资活动净额：{net_financing}",
                f"净现金流 = {net_operating} + {net_investing} + {net_financing} = {net_cash_flow}",
            ],
            "ai_instruction": "现金流量表等式正确，可以继续。"
        }
    except AccountingError:
        raise  # 会计错误冒泡到全局 handler
    except Exception as e:
        return {
            "valid": False,
            "violations": [f"生成现金流量表失败: {str(e)}"],
            "ai_instruction": f"STOP_RETRYING. 生成现金流量表失败，请检查业务数据是否完整。"
        }
