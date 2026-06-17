# 进销存管理系统（Inventory System）

本仓库为面向 Windows 的进销存（库存/采购/销售）管理系统源码与打包脚本。仓库包含后端（FastAPI）、前端（Vite + Vue3）、打包与安装器脚本，支持将前端构建产物嵌入后端并使用 PyInstaller 生成可分发的 exe 与安装器。

此 README 基于仓库内脚本（例如 build.py、launcher.py、installer.py、inventory.spec、installer.spec）与依赖文件（backend/requirements.txt、frontend/package.json）自动生成并补充了可直接执行的命令与注意事项。


主要亮点
- 后端：Python + FastAPI（入口：backend/main.py，启动器：launcher.py）
- 前端：Vue 3 + Vite（位于 frontend/，构建命令：npm run build）
- 打包：PyInstaller（inventory.spec、installer.spec），一键构建脚本：build.py
- 安装器：installer.py（tkinter GUI），会被打包为单文件安装器
- 工作区与数据：默认存放于 Windows 的 %APPDATA%/进销存管理系统（通过 backend/workspace.py 管理）


技术栈与关键依赖（从仓库文件提取）

后端（backend/requirements.txt）:
- fastapi>=0.110
- uvicorn[standard]>=0.29
- sqlalchemy>=2.0
- pydantic>=2.0
- python-multipart
- httpx
- openpyxl

前端（frontend/package.json）:
- 运行/构建脚本：
  - dev: vite
  - build: vite build
  - preview: vite preview
- 依赖（主要）：vue, element-plus, pinia, vue-router, axios, dayjs, echarts, vue-echarts, @element-plus/icons-vue
- devDependencies：vite, @vitejs/plugin-vue

其他工具：PyInstaller（用于打包），UPX（可选，.spec 文件启用了 upx），Node.js & npm（用于前端构建），tkinter（用于 installer.py 的 GUI，在大多数 Windows Python 发行版中可用）。


快速开始（开发）

环境建议
- Python 3.10+（建议 3.10/3.11）
- Node.js 18+（与 npm）

1) 克隆仓库

```bash
git clone https://github.com/bingolol/-inventory-system.git
cd -inventory-system
```

2) 后端（Python）

在项目根目录：

Windows (PowerShell)：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Linux / macOS：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

3) 前端（开发或构建）

开发（热重载）：

```bash
cd frontend
npm install
npm run dev
# 默认 Vite dev server 在 http://localhost:5173
```

构建（用于打包）：

```bash
cd frontend
npm install
npm run build
# 构建输出位于 frontend/dist，build.py 会将其嵌入到打包 exe
```

4) 本地运行（示例步骤）

A. 使用启动器（推荐 — 等同于打包后行为）

在项目根目录（确保已安装 backend 依赖并构建前端）：

```bash
python launcher.py
```

行为说明：
- launcher.py 会尝试在 8000~8099 范围内选择可用端口（可通过环境变量 INVENTORY_PORT 指定端口）。
- 启动后会自动打开默认浏览器访问 http://localhost:<port>。
- 运行时工作区、日志与数据库默认在 %APPDATA%/进销存管理系统（可通过 INVENTORY_WORKSPACE 覆盖）。

B. 调试模式（按模块启动）

```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

5) 验证服务（快速 API 示例）

服务启动后（假设端口 8000），可执行下列命令验证：

- 健康检查：

```bash
curl http://localhost:8000/api/health
# 返回 {"status":"ok"}
```

- 获取枚举：

```bash
curl http://localhost:8000/api/enums | jq '.'
```

- 示例：创建账本（Accounts API）

```bash
curl -X POST http://localhost:8000/api/accounts \
  -H "Content-Type: application/json" \
  -d '{"name":"默认账本","type":1,"code":"A001","taxpayer_type":0}'
```

（请根据后端 schemas/ 和 API 文档调整字段）

6) 如何查看实际端口（打包/启动器场景）

launcher.py 会在工作区创建 `port.txt`，包含实际监听端口：

- Windows 示例路径： `%APPDATA%/进销存管理系统/port.txt`
- 读取端口：

```powershell
Get-Content $env:APPDATA\"进销存管理系统\port.txt"
```


详细一键构建 / 打包示例

在已准备好 frontend/dist 的情况下（或让 build.py 自动完成构建），在项目根目录执行：

```bash
python build.py
```

build.py 将做：
- 构建 frontend（如需要）-> 生成 frontend/dist
- 运行 DB 初始化以创建 inventory.db.template（或复制现有 inventory.db）
- pyinstaller inventory.spec -> 生成 dist/进销存管理系统/
- 生成安装脚本并复制资源到发布目录
- 准备 dist2 并运行 pyinstaller --noconfirm installer.spec -> 生成 dist/进销存管理系统安装包.exe

构建完成后示例操作（Windows）：

```powershell
# 打开发布目录
explorer .\dist\"进销存管理系统"
# 或运行安装器
.\dist\"进销存管理系统安装包.exe"
```


工作区、日志与数据位置
- 默认工作区（打包模式）: %APPDATA%\进销存管理系统（由 backend/workspace.py 的 get_workspace_root() 决定）
- 数据库路径: 工作区/inventory.db
- 上传文件: 工作区/uploads/images
- 日志: 工作区/app.log
- 端口信息: 工作区/port.txt（launcher.py 会写入实际使用的端口）

注：可通过环境变量 INVENTORY_WORKSPACE 覆盖工作区位置（优先级最高）。


环境变量与运行时配置
- INVENTORY_PORT：强制指定端口（例如 Windows PowerShell: $env:INVENTORY_PORT='8080'）
- CORS_ORIGINS：向 backend/main.py 追加允许的前端源（逗号分隔）
- INVENTORY_WORKSPACE：自定义工作区根目录


测试
- 项目包含 tests/ 与 pytest.ini，运行：

```bash
pytest
```


常见问题与排障
- 浏览器未自动打开：launcher.py 会在后台线程延迟 3 秒打开浏览器；若未打开，请手动访问 http://localhost:<port>，端口写在工作区的 port.txt
- 前端静态文件未被嵌入：确保 frontend/dist 存在（npm run build）并重新运行 build.py
- 安装器无法创建快捷方式：安装器使用 PowerShell 创建 .lnk（可能因权限或公司策略失败），以管理员运行或手动创建快捷方式
- 打包时报错 missing module：在虚拟环境安装缺失包，或将包名添加到 inventory.spec 的 hiddenimports


贡献与许可
- 欢迎提交 Issue 与 PR。建议：Fork → 新分支 → 添加/更新测试 → PR。
- 仓库当前未包含 LICENSE 文件。建议在发布前补充合适的许可证（例如 MIT）。
