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
- git clone https://github.com/bingolol/-inventory-system.git
- cd -inventory-system

2) 后端（Python）
- 创建并激活虚拟环境：
  - Linux/macOS: python3 -m venv venv && source venv/bin/activate
  - Windows (PowerShell): python -m venv venv; .\venv\Scripts\Activate.ps1
- 安装依赖：
  - pip install -r backend/requirements.txt

3) 前端
- cd frontend
- npm install
  - 或使用：npm ci（当你依赖 package-lock.json 并希望精确重现依赖时）
- 构建前端产物： npm run build
- 构建输出位置： frontend/dist（build.py 会将该目录嵌入到打包的 exe）

4) 本地运行（推荐）
- 推荐使用仓库提供的启动器（与打包后行为一致）：
  - 在仓库根目录运行： python launcher.py
  - launcher.py 会：选择 8000~8099 的可用端口（可用环境变量 INVENTORY_PORT 指定端口），初始化工作区（%APPDATA%/...）并自动在浏览器打开应用。

- 直接使用 uvicorn（便于调试）:
  - cd backend
  - uvicorn main:app --reload --host 127.0.0.1 --port 8000


一键构建 / 打包（生成可分发安装器）

仓库包含 build.py，自动串联前端构建、数据库模板创建、PyInstaller 打包及安装器生成。

1) 确保前端构建：
- cd frontend && npm install && npm run build

2) 在项目根目录执行：
- python build.py

build.py 做了：
- 检查并构建前端（如 frontend/dist 不存在则自动运行 npm install + npm run build）
- 运行数据库初始化以创建 inventory.db.template（如果 backend/inventory.db 存在则会复制）
- 运行 pyinstaller inventory.spec → 输出 dist/进销存管理系统/（包含 exe 与资源）
- 生成安装脚本（批处理、PowerShell 快捷方式脚本、卸载脚本）并复制图标
- 将应用目录准备到 dist2 并运行 pyinstaller --noconfirm installer.spec 生成 dist/进销存管理系统安装包.exe

手动打包参考：
- pyinstaller inventory.spec
- pyinstaller --noconfirm installer.spec

注意：
- build.py 会在找不到 PyInstaller 时尝试 pip install pyinstaller
- 若遇到 PyInstaller 报 missing module，请在虚拟环境中安装缺失模块或将其添加到 inventory.spec 的 hiddenimports


工作区、日志与数据位置
- 默认工作区（打包模式）: %APPDATA%\进销存管理系统（由 backend/workspace.py 的 get_workspace_root() 决定）
- 数据库路径: 工作区/inventory.db
- 上传文件: 工作区/uploads/images
- 日志: 工作区/app.log
- 端口信息: 工作区/port.txt（launcher.py 会写入实际使用的端口）

注：可通过环境变量 INVENTORY_WORKSPACE 覆盖工作区位置（优先级最高）。


环境变量与运行时配置
- INVENTORY_PORT：若设置则 launcher.py 使用该端口并跳过自动端口检测
  - Windows (cmd): set INVENTORY_PORT=8080
  - Windows (PowerShell): $env:INVENTORY_PORT = '8080'
  - Linux/macOS: export INVENTORY_PORT=8080
- CORS_ORIGINS：向 backend/main.py 追加��许的前端源（逗号分隔）
- INVENTORY_WORKSPACE：自定义工作区根目录


测试
- 项目包含 tests/ 与 pytest.ini，运行： pytest


常见问题与排障
- 浏览器未自动打开：launcher.py 在后台线程延迟 3 秒打开浏览器；若未打开，请手动访问 http://localhost:<port>，端口写在工作区的 port.txt
- 前端静态文件未被嵌入：确保 frontend/dist 存在（npm run build）并重新运行 build.py
- 安装器无法创建快捷方式：安装器使用 PowerShell 创建 .lnk（可能因权限或公司策略失败），以管理员运行或手动创建快捷方式
- 打包时报错 missing module：在虚拟环境安装缺失包，或将包名添加到 inventory.spec 的 hiddenimports


贡献与许可
- 欢迎提交 Issue 与 PR。建议：Fork → 新分支 → 添加/更新测试 → PR。
- 仓库当前未包含 LICENSE 文件。建议在发布前补充合适的许可证（例如 MIT）。


我已将 README.md 草稿补充了详细依赖与精确命令，现在准备将其提交到仓库。