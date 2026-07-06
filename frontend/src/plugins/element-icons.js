import {
  ArrowDown, Box, Calendar, Connection, DataAnalysis, DataBoard, DataLine,
  Delete, Document, DocumentChecked, Download, Edit, Files, FolderChecked,
  Goods, Money, OfficeBuilding, PieChart, Plus, Search, Sell, ShoppingCart,
  Ticket, TrendCharts, User, Wallet, Warning
} from '@element-plus/icons-vue'

const icons = {
  ArrowDown, Box, Calendar, Connection, DataAnalysis, DataBoard, DataLine,
  Delete, Document, DocumentChecked, Download, Edit, Files, FolderChecked,
  Goods, Money, OfficeBuilding, PieChart, Plus, Search, Sell, ShoppingCart,
  Ticket, TrendCharts, User, Wallet, Warning
}

export function registerIcons(app) {
  for (const [name, component] of Object.entries(icons)) {
    app.component(name, component)
  }
}
