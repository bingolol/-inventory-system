"""一键重置 + 重跑 + 月结

用法: python -m scripts.qiaoyou_sim.reset_and_run_all
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import shutil
from datetime import datetime, date
from decimal import Decimal

from database import SessionLocal, set_maintenance_mode, init_db, DB_PATH
import models
from uow import unit_of_work


ACCOUNT_ID = 1
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "test123456"


def reset_database():
    """[1] 删除数据库 → [2] 初始化"""
    print("[1/6] 删除数据库:", DB_PATH)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("  已删除")
    else:
        print("  不存在，跳过")

    print("[2/6] 初始化数据库（建表 + 触发器 + 自动迁移）")
    init_db()
    print("  init_db 完成")


def create_account_and_admin():
    """[3] 创建账本 + admin 用户 + 初始 TaxpayerTypeHistory"""
    print("[3/6] 创建账本 + admin 用户")
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        # 创建账本（巧游电子科技，小规模纳税人）
        acc = models.Account(
            name="巧游电子科技",
            type="company",
            code="qiaoyou",
            taxpayer_type_l3="small_scale",
            surcharge_halved=True,  # 小型微利企业，附加税减半
        )
        db.add(acc)
        db.flush()
        print(f"  账本创建: id={acc.id}, code=qiaoyou, taxpayer=small_scale")

        # 写初始纳税人类型历史记录（早于业务起始月，确保回溯查询能命中 small_scale）
        try:
            db.add(models.TaxpayerTypeHistory(
                account_id=acc.id,
                taxpayer_type_l3="small_scale",
                effective_period="2025-01",
            ))
            db.flush()
            print(f"  初始 TaxpayerTypeHistory: small_scale (effective_period=2025-01)")
        except AttributeError:
            print("  [警告] TaxpayerTypeHistory 模型不存在，跳过初始历史记录")

        # admin 用户（使用 pbkdf2 哈希，与 auth 模块一致）
        import hashlib, secrets
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', ADMIN_PASSWORD.encode(), salt.encode(), 100000).hex()
        admin = models.User(
            username=ADMIN_USERNAME,
            password_hash=pwd_hash,
            password_salt=salt,
            account_id=acc.id,
        )
        db.add(admin)
        db.flush()
        print(f"  {ADMIN_USERNAME} 用户已创建（密码 {ADMIN_PASSWORD}）")

        db.commit()
    finally:
        db.close()
        set_maintenance_mode(False)


def run_simulation():
    """[4] 跑业务模拟（7阶段）"""
    print("\n[4/6] 跑业务模拟（7阶段）")
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        from .helpers import setup_basic_data, PRODUCTS, CUSTOMERS, SUPPLIERS, BANK_ACCOUNT_ID
        from .period_dec_2025 import step2_dec_2025
        from .period_jan_feb_2026 import step3_jan_feb_2026
        from .period_mar_2026 import step4_mar_2026
        from .period_apr_2026 import step5_apr_2026
        from .period_may_2026 import step6_may_2026
        from .period_jun_2026 import step7_jun_2026

        # 阶段1：基础数据
        print("\n=== 阶段 1：建基础数据 ===")
        setup_basic_data(db, ACCOUNT_ID)
        print(f"[阶段1] 商品: {len(PRODUCTS)}")
        print(f"[阶段1] 客户: {len(CUSTOMERS)}")
        print(f"[阶段1] 供应商: {len(SUPPLIERS)}")
        print(f"[阶段1] 银行账户: id={BANK_ACCOUNT_ID}")

        # 阶段2-7
        step2_dec_2025(db, ACCOUNT_ID)

        # 2025-12 业务完成后，创建 OpeningBalance 作为 2026 年期初
        # 2025-12 银行业务：收款2000 + 利息0.01 - 手续费72.80 = 净1927.21
        # 月结（附加税/所得税/损益结转）不涉及 1002，所以现在读 = 2025-12-31 期末余额
        from models_finance import Ledger
        from crud.finance._ledger_helpers import _bal
        acc = db.query(models.Account).filter(models.Account.id == ACCOUNT_ID).first()
        ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
        bank_bal = _bal(db, ledger, "1002", datetime(2025, 12, 31, 23, 59, 59))
        ob = models.OpeningBalance(
            account_id=ACCOUNT_ID,
            date_l1=date(2025, 12, 31),
            bank_balance_l1=bank_bal,
        )
        db.add(ob)
        db.flush()
        print(f"[阶段2后] 创建 OpeningBalance: date=2025-12-31, bank_balance={bank_bal}")

        step3_jan_feb_2026(db, ACCOUNT_ID)
        step4_mar_2026(db, ACCOUNT_ID)
        step5_apr_2026(db, ACCOUNT_ID)
        step6_may_2026(db, ACCOUNT_ID)
        step7_jun_2026(db, ACCOUNT_ID)

        print("\n[完成] 全部阶段 1-7 执行完毕")
        db.commit()
    finally:
        db.close()
        set_maintenance_mode(False)


def run_month_close():
    """[5] 月结 2025-12 ~ 2026-06"""
    print("\n[5/6] 月结 2025-12 ~ 2026-06")
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        from engine_tax import TaxAccrualEngine
        from engine_period_close import PeriodCloseEngine
        from commands.fixed_asset_commands import BatchDepreciateFixedAssets
        from commands.base import dispatch

        periods = ["2025-12", "2026-01", "2026-02", "2026-03",
                   "2026-04", "2026-05", "2026-06"]

        for period in periods:
            print(f"\n=== 月结 {period} ===")

            # 1. 批量折旧
            with unit_of_work(db):
                dispatch(BatchDepreciateFixedAssets(
                    account_id=ACCOUNT_ID,
                    operator="sim",
                    period=period,
                ), db)
            db.flush()

            # 2. 税务计提
            with unit_of_work(db):
                engine = TaxAccrualEngine(db)
                result = engine.execute(ACCOUNT_ID, period)
                print(f"  状态: {result.get('status')}")
                if result.get("lines"):
                    print(f"  明细: {'; '.join(result['lines'])}")
                print(f"  累计利润: {result.get('cumulative_profit', 0):.2f}")

            # 3. 期间损益结转
            with unit_of_work(db):
                close_engine = PeriodCloseEngine(db)
                close_result = close_engine.execute(ACCOUNT_ID, period, force=False)
                if close_result.get("status") == "ok":
                    print(f"  损益结转: 收入={close_result['total_revenue']:.2f} "
                          f"费用={close_result['total_expense']:.2f} "
                          f"净利润={close_result['net_profit']:.2f}")
                else:
                    print(f"  损益结转: {close_result.get('msg', 'skipped')}")

            db.commit()
            print(f"[{period}] 月结成功")

    finally:
        db.close()
        set_maintenance_mode(False)


def run_compare_report():
    """[6] 对照分析报告"""
    print("\n[6/6] 对照分析报告")
    from .compare_report import main as compare_main
    compare_main()


def main():
    print("=" * 80)
    print("  巧游电子科技 — 一键重置 + 重跑 + 月结 + 对照分析")
    print("=" * 80)

    reset_database()
    create_account_and_admin()
    run_simulation()
    run_month_close()
    run_compare_report()

    print("\n" + "=" * 80)
    print("  全流程完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
