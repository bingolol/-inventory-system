import {
  ArrowDown, Box, DataAnalysis, DataBoard, DataLine, Delete, Document,
  DocumentChecked, Download, Edit, Files, FolderChecked, Goods,
  OfficeBuilding, PieChart, Plus, Search, Sell, ShoppingCart, Ticket,
  TrendCharts, User, Wallet, Warning
} from '@element-plus/icons-vue'

const icons = {
  ArrowDown: ArrowDown, Box: Box, DataAnalysis: DataAnalysis, DataBoard: DataBoard, DataLine: DataLine,
  Delete: Delete, Document: Document, DocumentChecked: DocumentChecked, Download: Download, Edit: Edit,
  Files: Files, FolderChecked: FolderChecked, Goods: Goods, OfficeBuilding: OfficeBuilding, PieChart: PieChart,
  Plus: Plus, Search: Search, Sell: Sell, ShoppingCart: ShoppingCart, Ticket: Ticket,
  TrendCharts: TrendCharts, User: User, Wallet: Wallet, Warning: Warning
}

export function registerIcons(app) {
  for (const [name, component] of Object.entries(icons)) {
    app.component(name, component)
  }
}
