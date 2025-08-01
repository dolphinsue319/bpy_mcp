# Blender Python SDK Documentation MCP Server

一個用於搜尋 Blender Python SDK 文件的 MCP (Model Context Protocol) 伺服器，支援語意搜尋和快速查找 API 資訊。

## 功能特點

- 🔍 **語意搜尋**：使用自然語言查詢 Blender Python API
- 📚 **完整覆蓋**：索引 2,050+ 個 Blender Python 文件
- ⚡ **快速查找**：直接根據函式路徑獲取詳細資訊
- 💾 **本地快取**：SQLite 快取減少 API 呼叫，提升響應速度
- 🤖 **MCP 整合**：支援 Claude Code 和 Raycast

## 安裝步驟

### 1. 複製專案

```bash
git clone <your-repo-url>
cd bpy_mcp
```

### 2. 準備 Blender 文件

下載 Blender Python API 文件並解壓到專案目錄：

```bash
# 建立文件目錄
mkdir blender_python_reference_4_5

# 將您的 Blender Python API HTML 文件複製到此目錄
# 文件應該包含如 bpy.ops.*.html, bpy.types.*.html 等
```

**注意**：`blender_python_reference_4_5/` 資料夾已加入 `.gitignore`，不會被提交到版本控制。

### 3. 設定環境

使用提供的設定腳本（推薦）：

```bash
./scripts/setup.sh
```

這個腳本會：
- 檢查並安裝 Poetry（如果還沒安裝）
- 使用 Poetry 安裝所有依賴
- 設定環境變數

或手動設定：

```bash
# 安裝 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安裝依賴
poetry install
```

### 4. 設定環境變數

複製 `.env.example` 並建立 `.env` 檔案：

```bash
cp .env.example .env
```

編輯 `.env` 並填入您的 API keys：

```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=blender-docs
```

### 5. 建立索引

使用索引更新腳本：

```bash
./scripts/update-index.sh
```

或手動執行：

```bash
poetry run python src/indexer.py
```

這會解析 `blender_python_reference_4_5/` 目錄中的所有 HTML 文件並建立 Pinecone 向量索引。預計需要 5-10 分鐘。

## 使用方式

### 啟動 MCP Server

使用啟動腳本（推薦）：

```bash
./scripts/start-server.sh
```

或手動啟動：

```bash
poetry run python src/server.py
```

### 在 Claude Code 中設定

在 macOS 上，編輯 Claude Desktop 的設定檔：

**設定檔位置**：`~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "blender-docs": {
      "command": "/Users/your-username/Documents/bpy_mcp/scripts/start-server.sh",
      "args": [],
      "env": {}
    }
  }
}
```

**重要提醒**：
- 必須使用**絕對路徑**，不能使用相對路徑或 `~`
- 將 `/Users/your-username/Documents/bpy_mcp` 替換為您的實際專案路徑
- 使用 `start-server.sh` 會自動處理虛擬環境和環境變數載入
- 環境變數會從專案的 `.env` 檔案自動讀取

**設定步驟**：
1. 開啟 Finder，按 `Cmd+Shift+G`，輸入 `~/Library/Application Support/Claude/`
2. 編輯或建立 `claude_desktop_config.json` 檔案
3. 加入上述配置，記得替換成您的實際路徑
4. 儲存檔案後重啟 Claude Desktop

### 在 Raycast 中設定

1. 安裝 Raycast MCP 擴展
2. 添加新的 MCP server
3. 設定命令為：`python /path/to/bpy_mcp/src/server.py`

## MCP 工具使用

### 1. search_docs - 搜尋文件

搜尋 Blender Python API 文件：

```
search_docs("create mesh modifier")
search_docs("animation keyframes", limit=10)
```

**參數**：
- `query` (str): 搜尋關鍵字
- `limit` (int, optional): 返回結果數量，預設 5，最多 20

### 2. get_function - 獲取函式詳情

獲取特定函式或類別的詳細資訊：

```
get_function("bpy.ops.mesh.subdivide")
get_function("bpy.types.Mesh")
```

**參數**：
- `function_path` (str): 完整的函式路徑

### 3. list_modules - 列出模組

列出可用的 Blender Python 模組：

```
list_modules()  # 列出頂層模組
list_modules("bpy.ops")  # 列出 bpy.ops 的子模組
```

**參數**：
- `parent_module` (str, optional): 父模組路徑

### 4. cache_stats - 快取統計

查看快取使用情況：

```
cache_stats()
```

返回快取命中率、儲存大小等統計資訊。

## 使用範例

在 Claude Code 中使用：

```
> 我想了解如何在 Blender 中創建 mesh
```

MCP 會自動搜尋相關文件並返回結果。

```
> 告訴我 bpy.ops.mesh.primitive_cube_add 的詳細資訊
```

MCP 會返回該函式的完整簽名、參數說明等。

## 專案結構

```
bpy_mcp/
├── src/
│   ├── __init__.py
│   ├── server.py      # MCP server 主程式
│   ├── indexer.py     # 建立索引腳本
│   ├── parser.py      # HTML 解析工具
│   ├── cache.py       # SQLite 快取管理
│   └── utils.py       # 共用工具函式
├── scripts/
│   ├── start-server.sh   # 啟動腳本
│   ├── setup.sh         # 設定腳本
│   └── update-index.sh  # 索引更新腳本
├── blender_python_reference_4_5/  # Blender 文件目錄 (需自行準備，不在版本控制中)
├── .env.example       # 環境變數範例
├── .gitignore
├── pyproject.toml
└── README.md
```

## 需求

- Python 3.8+
- Poetry（套件管理）
- OpenAI API key
- Pinecone API key

## 成本估算

- **初始索引建立**：約 $0.10 USD（一次性）
- **每月使用**：個人使用量預估 < $1 USD
- **Pinecone**：免費層級（100K vectors）

## 技術細節

- **Embedding Model**: OpenAI text-embedding-3-small (1536 維)
- **Vector Database**: Pinecone (Serverless)
- **MCP Framework**: FastMCP
- **文件解析**: BeautifulSoup4
- **本地快取**: SQLite (24 小時 TTL)

### 快取機制

- 搜尋結果和函式詳情會自動快取 24 小時
- 減少重複的 API 呼叫，提升響應速度
- 快取資料儲存在 `.cache/` 目錄
- 啟動時自動清理過期快取

## 故障排除

### Poetry 安裝問題

如果遇到 Poetry 安裝問題：
```bash
# 手動安裝
curl -sSL https://install.python-poetry.org | python3 -

# 添加到 PATH
export PATH="$HOME/.local/bin:$PATH"
```

### 索引建立失敗

檢查：
1. API keys 是否正確設定
2. 網路連線是否正常
3. Pinecone 免費額度是否用完

### MCP 連線失敗

檢查：
1. Server 是否正在運行
2. 路徑設定是否正確
3. Poetry 是否正確安裝
4. 使用 `start-server.sh` 腳本啟動

### 搜尋結果不準確

可能原因：
1. 查詢太過簡短或模糊
2. 使用更具體的函式名稱
3. 嘗試不同的關鍵字組合

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 授權

MIT License