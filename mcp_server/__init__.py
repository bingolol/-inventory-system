"""MCP Server — 端侧 Agent 接入进销存系统的协议适配层

设计原则:
- 单一真相源: 写操作只走 commands 层, 不直接 UPDATE 真相源表
- 政策不硬编码: server 自身不含任何税率字面量, 全部从 policy/ 取
- 不编造数据: 查询不到时返回 not_found, 禁止 agent 凑数
- 审计可追溯: 每次写操作记录 operator='ai', 写入 OperationLog
"""

__version__ = "0.1.0"
