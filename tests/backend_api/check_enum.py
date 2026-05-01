import sys
sys.path.insert(0, r'C:\Users\Administrator\Desktop\inventory-system\backend')
from enums import PERSONAL_EXPENSE_CATEGORIES, PERSONAL_INCOME_CATEGORIES
print('EXPENSE:', PERSONAL_EXPENSE_CATEGORIES)
print('INCOME:', PERSONAL_INCOME_CATEGORIES)
print('工资 in EXPENSE:', '工资' in PERSONAL_EXPENSE_CATEGORIES)
print('餐饮 in INCOME:', '餐饮' in PERSONAL_INCOME_CATEGORIES)