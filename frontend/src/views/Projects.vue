<template>
  <div class="projects-container">
    <h2>项目看板</h2>

    <el-tabs v-model="activeTab">
      <!-- Tab 1: 项目管理（Project表） -->
      <el-tab-pane label="项目管理" name="management">
        <div style="margin-bottom: 16px;">
          <el-button type="primary" @click="showCreateDialog">创建项目</el-button>
        </div>

        <el-table :data="managedProjects" style="width: 100%" v-loading="loadingManaged">
          <el-table-column prop="name" label="项目名称" width="180" />
          <el-table-column prop="customer_name" label="客户" width="150" />
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.status)">
                {{ statusLabel(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="start_date" label="开始日期" width="120" />
          <el-table-column prop="total_income" label="总收入" width="130" align="right">
            <template #default="scope">
              {{ scope.row.total_income != null ? scope.row.total_income.toFixed(2) : '' }}
            </template>
          </el-table-column>
          <el-table-column prop="total_cost" label="总成本" width="130" align="right">
            <template #default="scope">
              {{ scope.row.total_cost != null ? scope.row.total_cost.toFixed(2) : '' }}
            </template>
          </el-table-column>
          <el-table-column prop="profit" label="利润" width="130" align="right">
            <template #default="scope">
              <span :class="scope.row.profit != null && scope.row.profit >= 0 ? 'text-green' : 'text-red'">
                {{ scope.row.profit != null ? scope.row.profit.toFixed(2) : '' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="center">
            <template #default="scope">
              <el-button @click="viewManagedDetail(scope.row)" type="primary" size="small">详情</el-button>
              <el-button @click="showEditDialog(scope.row)" type="warning" size="small">编辑</el-button>
              <el-popconfirm title="确定删除此项目？关联的成本和收入记录将一并删除" @confirm="handleDeleteProject(scope.row.id)">
                <template #reference>
                  <el-button type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 2: 项目概览（统一从Project表） -->
      <el-tab-pane label="项目概览" name="aggregation">
        <el-table :data="projects" style="width: 100%" v-loading="loadingAgg">
          <el-table-column prop="name" label="项目名称" width="200" />
          <el-table-column prop="customer_name" label="客户" width="150" />
          <el-table-column prop="total_income" label="收入" width="130" align="right">
            <template #default="scope">
              {{ (scope.row.total_income || 0).toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="total_cost" label="成本" width="130" align="right">
            <template #default="scope">
              {{ (scope.row.total_cost || 0).toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="profit" label="利润" width="130" align="right">
            <template #default="scope">
              <span :class="scope.row.profit >= 0 ? 'text-green' : 'text-red'">
                {{ (scope.row.profit || 0).toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="sale_count" label="销售单" width="100" align="center" />
          <el-table-column prop="purchase_count" label="采购单" width="100" align="center" />
          <el-table-column label="操作" width="150" align="center">
            <template #default="scope">
              <el-button @click="viewManagedDetail(scope.row)" type="primary" size="small">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 项目详情抽屉（机制B：Project表） -->
    <el-drawer
      v-model="managedDialogVisible"
      :title="`项目详情：${managedDetail.name || ''}`"
      size="980px"
      destroy-on-close
      :with-header="true"
    >
      <div class="project-detail-sticky">
        <div class="project-detail-top">
          <div class="project-meta">
            <div class="project-name-row">
              <span class="project-name">{{ managedDetail.name || '-' }}</span>
              <el-tag :type="statusTagType(managedDetail.status)" size="small" style="margin-left:8px;">
                {{ statusLabel(managedDetail.status) }}
              </el-tag>
            </div>
            <div class="project-submeta">
              <span>客户：{{ managedDetail.customer_name || '-' }}</span>
              <span style="margin-left:12px;">开始：{{ managedDetail.start_date || '-' }}</span>
            </div>
          </div>
          <div class="project-actions">
            <el-button type="primary" size="small" @click="showCostAddDialog(managedDetail.id)">添加成本</el-button>
          </div>
        </div>

        <div class="kpi-row">
          <div class="kpi-card">
            <div class="kpi-label">总收入</div>
            <div class="kpi-value">¥{{ (managedDetail.total_income || 0).toFixed(2) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">总成本</div>
            <div class="kpi-value">¥{{ (managedDetail.total_cost || 0).toFixed(2) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">利润</div>
            <div class="kpi-value" :class="(managedDetail.profit || 0) >= 0 ? 'text-green' : 'text-red'">
              ¥{{ (managedDetail.profit || 0).toFixed(2) }}
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">待收款</div>
            <div class="kpi-value">¥{{ receivableAmount.toFixed(2) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">已收款</div>
            <div class="kpi-value">¥{{ receivedAmount.toFixed(2) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">未开票金额</div>
            <div class="kpi-value">¥{{ unInvoicedIncome.toFixed(2) }}</div>
          </div>
        </div>
      </div>

      <el-tabs v-model="detailActiveTab">
        <el-tab-pane label="成本明细" name="costs">
          <div class="filter-row">
            <el-select v-model="costFilters.cost_type" clearable placeholder="成本类型" style="width:120px" @change="noop">
              <el-option v-for="t in costTypes" :key="t" :label="t" :value="t" />
            </el-select>
            <el-select v-model="costFilters.payment_method" clearable placeholder="支付方式" style="width:120px" @change="noop">
              <el-option label="公司" value="company" />
              <el-option label="个人垫付" value="private_advance" />
            </el-select>
            <el-select v-model="costFilters.invoice_status" clearable placeholder="发票状态" style="width:120px" @change="noop">
              <el-option label="未开" value="未开" />
              <el-option label="已开" value="已开" />
              <el-option label="不需开" value="不需开" />
            </el-select>
            <el-date-picker
              v-model="costFilters.date_range"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width:260px"
              @change="noop"
            />
            <el-input v-model="costFilters.keyword" clearable placeholder="搜索 商品/供应商/备注" style="width:220px" />
            <div class="filter-summary">
              合计：<b>¥{{ filteredCostTotal.toFixed(2) }}</b>
            </div>
          </div>

          <el-table :data="filteredCosts" style="width: 100%" size="small">
            <el-table-column prop="cost_type" label="类型" width="80" />
            <el-table-column label="商品/数量" width="160">
              <template #default="scope">
                <span v-if="scope.row.product_name">
                  {{ scope.row.product_name }}
                  <span style="color:#999;margin-left:6px;">× {{ scope.row.quantity || 0 }}</span>
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="金额" width="100" align="right">
              <template #default="scope">{{ scope.row.amount.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="payment_method" label="支付方式" width="100">
              <template #default="scope">{{ scope.row.payment_method === 'company' ? '公司' : '个人垫付' }}</template>
            </el-table-column>
            <el-table-column prop="invoice_status" label="发票状态" width="80" />
            <el-table-column prop="supplier_name" label="供应商" width="120" />
            <el-table-column prop="cost_date" label="日期" width="110" />
            <el-table-column prop="notes" label="备注" />
            <el-table-column label="附件" width="70" align="center">
              <template #default="scope">
                <el-image v-if="scope.row.image_url" :src="resolveImageUrl(scope.row.image_url)" style="width:36px;height:36px;border-radius:4px;" fit="cover" :preview-src-list="[resolveImageUrl(scope.row.image_url)]" preview-teleported />
                <span v-else style="color:#999;font-size:12px;">无</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="scope">
                <el-button size="small" link type="primary" @click="editProjectCost(scope.row)">编辑</el-button>
                <el-popconfirm title="确定删除此成本记录?" @confirm="deleteProjectCost(scope.row.id)">
                  <template #reference><el-button size="small" link type="danger">删除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="收入明细" name="incomes">
          <div class="filter-row">
            <el-select v-model="incomeFilters.source_type" clearable placeholder="来源" style="width:140px" @change="noop">
              <el-option label="手动录入" value="manual" />
              <el-option label="销售单自动" value="sale_order" />
            </el-select>
            <el-select v-model="incomeFilters.payment_status" clearable placeholder="收款状态" style="width:140px" @change="noop">
              <el-option label="待收款" value="pending" />
              <el-option label="部分收取" value="partial" />
              <el-option label="已收" value="completed" />
            </el-select>
            <el-select v-model="incomeFilters.invoice_status" clearable placeholder="发票状态" style="width:120px" @change="noop">
              <el-option label="未开" value="未开" />
              <el-option label="已开" value="已开" />
              <el-option label="不需开" value="不需开" />
            </el-select>
            <el-date-picker
              v-model="incomeFilters.date_range"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width:260px"
              @change="noop"
            />
            <el-input v-model="incomeFilters.keyword" clearable placeholder="搜索备注" style="width:220px" />
            <div class="filter-summary">
              待收：<b>¥{{ filteredIncomeReceivable.toFixed(2) }}</b>
              <span style="margin:0 8px;color:#ddd;">|</span>
              已收：<b>¥{{ filteredIncomeReceived.toFixed(2) }}</b>
            </div>
          </div>

          <el-table :data="filteredIncomes" style="width: 100%" size="small">
            <el-table-column prop="amount" label="金额" width="100" align="right">
              <template #default="scope">{{ scope.row.amount.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="source_type" label="来源" width="100">
              <template #default="scope">
                <el-tag v-if="scope.row.source_type === 'sale_order'" type="success" size="small">销售单自动</el-tag>
                <el-tag v-else type="info" size="small">手动录入</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="payment_status" label="收款状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.payment_status === 'completed' ? 'success' : 'warning'" size="small">
                  {{ scope.row.payment_status === 'completed' ? '已收' : scope.row.payment_status === 'partial' ? '部分收取' : '待收款' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="received_amount" label="已收金额" width="100" align="right">
              <template #default="scope">{{ (scope.row.received_amount || 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="invoice_status" label="发票状态" width="80" />
            <el-table-column prop="income_date" label="日期" width="110" />
            <el-table-column prop="notes" label="备注" />
            <el-table-column label="附件" width="70" align="center">
              <template #default="scope">
                <el-image v-if="scope.row.image_url" :src="resolveImageUrl(scope.row.image_url)" style="width:36px;height:36px;border-radius:4px;" fit="cover" :preview-src-list="[resolveImageUrl(scope.row.image_url)]" preview-teleported />
                <span v-else style="color:#999;font-size:12px;">无</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="scope">
                <el-button
                  v-if="scope.row.source_type === 'sale_order' && scope.row.source_id"
                  size="small"
                  link
                  type="primary"
                  @click="openSaleOrder(scope.row.source_id)"
                >
                  查看销售单
                </el-button>
                <template v-else>
                  <el-button size="small" link type="primary" @click="editProjectIncome(scope.row)">编辑</el-button>
                  <el-popconfirm title="确定删除此收入记录?" @confirm="handleDeleteIncome(scope.row.id)">
                    <template #reference><el-button size="small" link type="danger">删除</el-button></template>
                  </el-popconfirm>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="关联采购单" v-if="managedDetail.purchases && managedDetail.purchases.length > 0">
          <el-table :data="managedDetail.purchases" style="width: 100%" size="small">
            <el-table-column prop="order_no" label="采购单号" width="160" />
            <el-table-column prop="supplier_name" label="供应商" width="120" />
            <el-table-column prop="total_price" label="金额" width="100" align="right">
              <template #default="scope">{{ (scope.row.total_price || 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80" />
            <el-table-column prop="purchase_date" label="日期" width="110" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <!-- 销售单详情（收入追溯） -->
    <el-dialog v-model="saleDetailVisible" :title="`销售单详情：${saleDetail?.order_no || ''}`" width="820px" destroy-on-close>
      <template v-if="saleDetail">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="客户">{{ saleDetail.customer_name || '散客' }}</el-descriptions-item>
          <el-descriptions-item label="项目">{{ saleDetail.project_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ saleDetail.sale_date?.slice(0, 10) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="总额">¥{{ (saleDetail.total_price || 0).toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ saleDetail.status }}</el-descriptions-item>
          <el-descriptions-item label="出库">{{ saleDetail.deduct_inventory ? '零售扣库存' : '不扣库存' }}</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:12px;font-weight:600;">销售明细</div>
        <el-table :data="saleDetail.items || []" size="small" :border="true" style="width:100%;margin-top:8px;">
          <el-table-column prop="product_name" label="商品" min-width="160" />
          <el-table-column prop="quantity" label="数量" width="90" align="center" />
          <el-table-column prop="unit_price" label="单价" width="110" align="right">
            <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="total_price" label="小计" width="110" align="right">
            <template #default="{ row }">¥{{ (row.total_price || 0).toFixed(2) }}</template>
          </el-table-column>
        </el-table>
      </template>
      <template v-else>
        <el-empty description="销售单不存在或加载失败" />
      </template>
      <template #footer>
        <el-button @click="saleDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 创建项目弹窗 -->
    <el-dialog v-model="createDialogVisible" :title="editingProjectId ? '编辑项目' : '创建项目'" width="500px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="createForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-select v-model="createForm.customer_id" placeholder="选择客户（可选）" clearable filterable>
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="createForm.status">
            <el-option label="进行中" value="ongoing" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="createForm.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProject" :loading="saving">{{ editingProjectId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- 编辑项目成本弹窗 -->
    <el-dialog v-model="costEditVisible" title="编辑项目成本" width="480px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="金额">
          <el-input-number v-model="costEditForm.amount" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="附件图片">
          <ImageUpload v-model="costEditForm.image_url" business-type="cost" :record-id="costEditForm.id || 0" :update-api="(data) => api.updateProjectCost(costEditForm.id, data)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="costEditVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCostEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 编辑项目收入弹窗 -->
    <el-dialog v-model="incomeEditVisible" title="编辑项目收入" width="480px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="金额">
          <el-input-number v-model="incomeEditForm.amount" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="收款状态">
          <el-select v-model="incomeEditForm.payment_status" style="width:100%">
            <el-option label="待收款" value="pending" />
            <el-option label="部分收取" value="partial" />
            <el-option label="已收" value="completed" />
          </el-select>
        </el-form-item>
        <el-form-item label="已收金额">
          <el-input-number v-model="incomeEditForm.received_amount" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="发票状态">
          <el-select v-model="incomeEditForm.invoice_status" style="width:100%">
            <el-option label="已开" value="已开" />
            <el-option label="未开" value="未开" />
            <el-option label="不需开" value="不需开" />
          </el-select>
        </el-form-item>
        <el-form-item label="收入日期">
          <el-date-picker v-model="incomeEditForm.income_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="到账日期">
          <el-date-picker v-model="incomeEditForm.received_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="incomeEditForm.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="incomeEditVisible = false">取消</el-button>
        <el-button type="primary" @click="saveIncomeEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加项目成本弹窗 -->
    <el-dialog v-model="costAddVisible" title="添加项目成本" width="500px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="成本类型" required>
          <el-select v-model="costAddForm.cost_type" @change="onCostTypeChange">
            <el-option v-for="t in costTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <template v-if="costAddForm.cost_type === '材料'">
          <el-form-item label="商品" required>
            <el-select v-model="costAddForm.product_id" filterable placeholder="选择商品" @change="onProductSelect">
              <el-option v-for="p in costAddProducts" :key="p.id"
                :label="`${p.name} (库存:${p.current_stock ?? 0})`" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="数量" required>
            <el-input-number v-model="costAddForm.quantity" :min="1" @change="calcMaterialAmount" />
          </el-form-item>
          <el-form-item label="单价">
            <el-input-number v-model="costAddForm.unit_price" :min="0" :precision="2" @change="calcMaterialAmount" />
            <span style="color:#999;font-size:12px;margin-left:8px;">自动取采购价，可修改</span>
          </el-form-item>
          <el-form-item label="金额">
            <span style="font-weight:600;">¥{{ costAddForm.amount.toFixed(2) }}</span>
            <span style="color:#999;font-size:12px;margin-left:8px;">= 数量 × 单价</span>
          </el-form-item>
        </template>
        <template v-else-if="costAddForm.cost_type">
          <el-form-item label="金额" required>
            <el-input-number v-model="costAddForm.amount" :min="0" :precision="2" style="width:100%" />
          </el-form-item>
        </template>
        <el-form-item label="支付方式">
          <el-select v-model="costAddForm.payment_method">
            <el-option label="公司" value="company" />
            <el-option label="个人垫付" value="private_advance" />
          </el-select>
        </el-form-item>
        <el-form-item label="发票状态">
          <el-select v-model="costAddForm.invoice_status">
            <el-option label="未开" value="未开" />
            <el-option label="已开" value="已开" />
            <el-option label="不需开" value="不需开" />
          </el-select>
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="costAddForm.supplier_name" placeholder="可选" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="costAddForm.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="costAddVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCostAdd">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { resolveImageUrl } from '../api'
import ImageUpload from '../components/ImageUpload.vue'

const activeTab = ref('management')

// 机制A：订单聚合
const projects = ref([])
const loadingAgg = ref(false)

// 机制B：项目管理
const managedProjects = ref([])
const managedDialogVisible = ref(false)
const managedDetail = ref({ costs: [], incomes: [], purchases: [] })
const loadingManaged = ref(false)
const detailActiveTab = ref('costs')

const noop = () => {}

// 详情 KPI（前端即时计算）
const receivableAmount = computed(() => {
  const incomes = managedDetail.value?.incomes || []
  return incomes.reduce((sum, i) => {
    const status = i.payment_status
    if (status === 'pending' || status === 'partial') {
      const amt = Number(i.amount || 0)
      const received = Number(i.received_amount || 0)
      return sum + Math.max(amt - received, 0)
    }
    return sum
  }, 0)
})
const receivedAmount = computed(() => {
  const incomes = managedDetail.value?.incomes || []
  return incomes.reduce((sum, i) => sum + Number(i.received_amount || 0), 0)
})
const unInvoicedIncome = computed(() => {
  const incomes = managedDetail.value?.incomes || []
  return incomes.reduce((sum, i) => {
    if (i.invoice_status && i.invoice_status !== '已开') return sum + Number(i.amount || 0)
    if (!i.invoice_status) return sum + Number(i.amount || 0)
    return sum
  }, 0)
})

// 成本筛选
const costFilters = ref({
  cost_type: '',
  payment_method: '',
  invoice_status: '',
  date_range: null,
  keyword: ''
})
const filteredCosts = computed(() => {
  const rows = managedDetail.value?.costs || []
  const f = costFilters.value
  const kw = (f.keyword || '').trim().toLowerCase()
  const [ds, de] = f.date_range || []
  return rows.filter(r => {
    if (f.cost_type && r.cost_type !== f.cost_type) return false
    if (f.payment_method && r.payment_method !== f.payment_method) return false
    if (f.invoice_status && r.invoice_status !== f.invoice_status) return false
    if (ds && r.cost_date && r.cost_date.slice(0, 10) < ds) return false
    if (de && r.cost_date && r.cost_date.slice(0, 10) > de) return false
    if (kw) {
      const hay = `${r.product_name || ''} ${r.supplier_name || ''} ${r.notes || ''}`.toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
})
const filteredCostTotal = computed(() => (filteredCosts.value || []).reduce((s, r) => s + Number(r.amount || 0), 0))

// 收入筛选
const incomeFilters = ref({
  source_type: '',
  payment_status: '',
  invoice_status: '',
  date_range: null,
  keyword: ''
})
const filteredIncomes = computed(() => {
  const rows = managedDetail.value?.incomes || []
  const f = incomeFilters.value
  const kw = (f.keyword || '').trim().toLowerCase()
  const [ds, de] = f.date_range || []
  return rows.filter(r => {
    if (f.source_type) {
      const normalized = (r.source_type === 'sale_order') ? 'sale_order' : 'manual'
      if (normalized !== f.source_type) return false
    }
    if (f.payment_status && r.payment_status !== f.payment_status) return false
    if (f.invoice_status && r.invoice_status !== f.invoice_status) return false
    if (ds && r.income_date && r.income_date.slice(0, 10) < ds) return false
    if (de && r.income_date && r.income_date.slice(0, 10) > de) return false
    if (kw) {
      const hay = `${r.notes || ''}`.toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
})
const filteredIncomeReceivable = computed(() => {
  const rows = filteredIncomes.value || []
  return rows.reduce((sum, i) => {
    if (i.payment_status === 'pending' || i.payment_status === 'partial') {
      const amt = Number(i.amount || 0)
      const received = Number(i.received_amount || 0)
      return sum + Math.max(amt - received, 0)
    }
    return sum
  }, 0)
})
const filteredIncomeReceived = computed(() => {
  const rows = filteredIncomes.value || []
  return rows.reduce((sum, i) => sum + Number(i.received_amount || 0), 0)
})

// 销售单追溯
const saleDetailVisible = ref(false)
const saleDetail = ref(null)
const openSaleOrder = async (saleId) => {
  if (!saleId) return
  try {
    saleDetail.value = await api.getSale(saleId)
    saleDetailVisible.value = true
  } catch (e) {
    saleDetail.value = null
    saleDetailVisible.value = true
  }
}

// 创建/编辑项目
const createDialogVisible = ref(false)
const saving = ref(false)
const editingProjectId = ref(null)
const createForm = ref({
  name: '',
  customer_id: null,
  status: 'ongoing',
  start_date: '',
  notes: ''
})
const customers = ref([])

const statusTagType = (status) => {
  const map = { ongoing: 'primary', completed: 'success', cancelled: 'info' }
  return map[status] || 'info'
}
const statusLabel = (status) => {
  const map = { ongoing: '进行中', completed: '已完成', cancelled: '已取消' }
  return map[status] || status
}

// 机制A：获取聚合项目列表（统一从Project表）
const getProjects = async () => {
  loadingAgg.value = true
  try {
    const response = await api.getProjects()
    projects.value = response?.items || []
  } catch (error) {
    console.error('获取项目列表失败:', error)
    projects.value = []
  } finally {
    loadingAgg.value = false
  }
}

// 机制B：获取项目管理列表
const getManagedProjects = async () => {
  loadingManaged.value = true
  try {
    const response = await api.getProjectList()
    managedProjects.value = response?.items || []
  } catch (error) {
    console.error('获取项目管理列表失败:', error)
    managedProjects.value = []
  } finally {
    loadingManaged.value = false
  }
}

// 机制B：查看项目详情
const viewManagedDetail = async (row) => {
  try {
    const response = await api.getProjectDetail(row.id)
    managedDetail.value = response
    managedDialogVisible.value = true
    detailActiveTab.value = 'costs'
    costFilters.value = { cost_type: '', payment_method: '', invoice_status: '', date_range: null, keyword: '' }
    incomeFilters.value = { source_type: '', payment_status: '', invoice_status: '', date_range: null, keyword: '' }
  } catch (error) {
    console.error('获取项目详情失败:', error)
  }
}

// 创建项目
const showCreateDialog = async () => {
  editingProjectId.value = null
  createForm.value = { name: '', customer_id: null, status: 'ongoing', start_date: '', notes: '' }
  try {
    const res = await api.getCustomers()
    customers.value = res?.items || res || []
  } catch (e) { customers.value = [] }
  createDialogVisible.value = true
}

const showEditDialog = async (row) => {
  editingProjectId.value = row.id
  createForm.value = {
    name: row.name,
    customer_id: row.customer_id || null,
    status: row.status,
    start_date: row.start_date || '',
    notes: row.notes || ''
  }
  try {
    const res = await api.getCustomers()
    customers.value = res?.items || res || []
  } catch (e) { customers.value = [] }
  createDialogVisible.value = true
}

const saveProject = async () => {
  if (!createForm.value.name) {
    ElMessage.warning('请输入项目名称')
    return
  }
  saving.value = true
  try {
    if (editingProjectId.value) {
      await api.updateProject(editingProjectId.value, createForm.value)
      ElMessage.success('更新成功')
    } else {
      await api.createProject(createForm.value)
      ElMessage.success('创建成功')
    }
    createDialogVisible.value = false
    getManagedProjects()
    getProjects()
  } catch (error) {
    console.error('保存项目失败:', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const handleDeleteProject = async (id) => {
  try {
    await api.deleteProject(id)
    ElMessage.success('已删除')
    getManagedProjects()
    getProjects()
  } catch (e) { ElMessage.error('删除失败') }
}

// 编辑项目成本
const costEditVisible = ref(false)
const costEditForm = ref({ id: null, amount: 0, image_url: '', project_id: null })

const editProjectCost = (row) => {
  costEditForm.value = {
    id: row.id,
    amount: row.amount,
    image_url: row.image_url || '',
    project_id: row.project_id
  }
  costEditVisible.value = true
}

const saveCostEdit = async () => {
  try {
    await api.updateProjectCost(costEditForm.value.id, { amount: costEditForm.value.amount })
    ElMessage.success('更新成功')
    costEditVisible.value = false
    viewManagedDetail({ id: costEditForm.value.project_id })
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

// 删除项目成本
const deleteProjectCost = async (costId) => {
  try {
    await api.deleteProjectCost(costId)
    ElMessage.success('已删除')
    // 刷新详情（如果有打开的对话框）
    if (managedDialogVisible.value && managedDetail.value.id) {
      viewManagedDetail({ id: managedDetail.value.id })
    }
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// 添加项目成本
const costAddVisible = ref(false)
const costAddForm = ref({
  project_id: null, cost_type: '', product_id: null, quantity: 1,
  unit_price: 0, amount: 0, payment_method: 'company',
  invoice_status: '未开', supplier_name: '', notes: ''
})
const costAddProducts = ref([])
const costTypes = ['材料', '人工', '差旅', '外包', '设备', '其他']

const onCostTypeChange = () => {
  costAddForm.value.product_id = null
  costAddForm.value.quantity = 1
  costAddForm.value.amount = 0
  costAddForm.value.unit_price = 0
}

const onProductSelect = (productId) => {
  const p = costAddProducts.value.find(x => x.id === productId)
  if (p) {
    costAddForm.value.unit_price = p.purchase_price || 0
    calcMaterialAmount()
  }
}

const calcMaterialAmount = () => {
  costAddForm.value.amount = costAddForm.value.quantity * costAddForm.value.unit_price
}

const showCostAddDialog = async (projectId) => {
  costAddForm.value = {
    project_id: projectId, cost_type: '', product_id: null, quantity: 1,
    unit_price: 0, amount: 0, payment_method: 'company',
    invoice_status: '未开', supplier_name: '', notes: ''
  }
  try {
    const res = await api.getProducts({ page: 1, page_size: 1000 })
    costAddProducts.value = res.items || res
  } catch (e) { costAddProducts.value = [] }
  costAddVisible.value = true
}

const saveCostAdd = async () => {
  const f = costAddForm.value
  if (!f.cost_type) { ElMessage.warning('请选择成本类型'); return }
  if (f.cost_type === '材料' && !f.product_id) { ElMessage.warning('请选择商品'); return }
  if (f.amount <= 0) { ElMessage.warning('金额必须大于0'); return }
  try {
    await api.createProjectCost({
      project_id: f.project_id,
      cost_type: f.cost_type,
      amount: f.amount,
      product_id: f.cost_type === '材料' ? f.product_id : null,
      quantity: f.cost_type === '材料' ? f.quantity : null,
      payment_method: f.payment_method,
      invoice_status: f.invoice_status,
      supplier_name: f.supplier_name || null,
      notes: f.notes || null
    })
    ElMessage.success('成本添加成功')
    costAddVisible.value = false
    viewManagedDetail({ id: f.project_id })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  }
}

// 编辑项目收入
const incomeEditVisible = ref(false)
const incomeEditForm = ref({ id: null, amount: 0, payment_status: 'pending', received_amount: 0, invoice_status: '未开', income_date: '', received_date: '', notes: '', project_id: null })

const editProjectIncome = (row) => {
  incomeEditForm.value = {
    id: row.id, amount: row.amount, payment_status: row.payment_status,
    received_amount: row.received_amount || 0, invoice_status: row.invoice_status,
    income_date: row.income_date?.slice(0, 10) || '', received_date: row.received_date?.slice(0, 10) || '',
    notes: row.notes || '', project_id: row.project_id
  }
  incomeEditVisible.value = true
}

const saveIncomeEdit = async () => {
  try {
    await api.updateProjectIncome(incomeEditForm.value.id, incomeEditForm.value)
    ElMessage.success('更新成功')
    incomeEditVisible.value = false
    viewManagedDetail({ id: incomeEditForm.value.project_id })
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

// 删除项目收入
const handleDeleteIncome = async (incomeId) => {
  try {
    await api.deleteProjectIncome(incomeId)
    ElMessage.success('已删除')
    if (managedDialogVisible.value && managedDetail.value.id) {
      viewManagedDetail({ id: managedDetail.value.id })
    }
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  getProjects()
  getManagedProjects()
})
</script>

<style scoped>
.projects-container {
  padding: 20px;
}
.text-green {
  color: #67c23a;
  font-weight: bold;
}
.text-red {
  color: #f56c6c;
  font-weight: bold;
}
.project-details {
  max-height: 500px;
  overflow-y: auto;
}

.project-detail-sticky {
  position: sticky;
  top: 0;
  background: var(--el-bg-color);
  z-index: 2;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 12px;
}
.project-detail-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.project-meta {
  flex: 1;
}
.project-name-row {
  display: flex;
  align-items: center;
}
.project-name {
  font-size: 16px;
  font-weight: 700;
}
.project-submeta {
  margin-top: 6px;
  color: #666;
  font-size: 12px;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}
.kpi-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--el-fill-color-blank);
}
.kpi-label {
  font-size: 12px;
  color: #888;
}
.kpi-value {
  margin-top: 6px;
  font-size: 16px;
  font-weight: 700;
}
.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}
.filter-summary {
  margin-left: auto;
  color: #666;
  font-size: 12px;
}
</style>