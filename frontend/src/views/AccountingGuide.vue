<template>
  <div class="ag-shell">
    <div class="ag-nav">
      <div class="ag-nav-hd">会计规则指引</div>
      <a
        v-for="m in modules"
        :key="m.id"
        class="ag-nav-item"
        :class="{ active: activeModule === m.id }"
        @click.prevent="scrollToModule(m.id)"
      >{{ m.icon }} {{ m.title }}</a>
    </div>

    <div class="ag-main" v-loading="loading">
      <div class="ag-topbar">
        <div>
          <div class="ag-topbar-title">会计规则指引</div>
          <div class="ag-topbar-sub">面向零基础 · 用实际数据一步步讲解</div>
        </div>
        <div class="ag-filters">
          <el-select v-model="year" size="small" style="width:100px" @change="query">
            <el-option v-for="y in years" :key="y" :label="String(y)" :value="y" />
          </el-select>
          <el-select v-model="quarter" size="small" style="width:90px" @change="query">
            <el-option v-for="q in [1,2,3,4]" :key="q" :label="'第'+q+'季度'" :value="q" />
          </el-select>
        </div>
      </div>

      <template v-if="data">
        <div class="ag-info-bar">
          <span><b>{{ data.profile.name }}</b></span>
          <el-tag :type="data.profile.taxpayer_type === 'small_scale' ? 'warning' : 'primary'" size="small">{{ data.profile.taxpayer_label }}</el-tag>
          <el-tag type="info" size="small">{{ data.profile.income_label }}</el-tag>
          <span style="color:var(--text-placeholder)">{{ data.period.label }}</span>
        </div>

        <div class="ag-content">
          <!-- Module 1: 进销存基础 -->
          <div id="module-1" class="ag-module">
            <div class="ag-m-title"><span class="ag-m-num">1</span> 进销存基础</div>

            <div class="ag-card ag-card-info">
              <div class="ag-card-title">核心公式：利润是怎么算出来的？</div>
              <p class="ag-formula-lg">营业收入 − 营业成本 − 费用 = 利润</p>
              <p>这个公式是所有会计的基础。做生意赚钱的四步逻辑：</p>
              <p><b>① 卖货收钱</b>（营业收入）→ <b>② 减掉进货成本</b>（营业成本）→ <b>③ 减掉日常开销</b>（费用）→ <b>④ 剩下的就是利润</b></p>
            </div>

            <div class="ag-card ag-card-hl">
              <div class="ag-card-title">{{ data.period.label }} 你的经营数据</div>
              <table class="ag-table">
                <tr><td>📦 营业收入（卖货收回的钱）</td><td><b>{{ fmt(data.module_1_basics.revenue) }}</b></td></tr>
                <tr><td>📉 营业成本（这些东西当初进货花了多少钱）</td><td><b>− {{ fmt(data.module_1_basics.cost) }}</b></td></tr>
                <tr v-if="data.module_1_basics.expenses.length">
                  <td>📋 费用合计</td><td><b>− {{ fmt(data.module_1_basics.total_expenses) }}</b></td>
                </tr>
                <tr v-for="e in data.module_1_basics.expenses" :key="e.category">
                  <td style="padding-left:32px;font-size:13px">└ {{ e.category }}</td>
                  <td style="font-size:13px;color:var(--text-secondary)">− {{ fmt(e.amount) }}</td>
                </tr>
                <tr class="ag-table-hl">
                  <td>💰 利润</td>
                  <td>
                    <span :class="data.module_1_basics.profit >= 0 ? 'ag-positive' : 'ag-negative'">
                      {{ fmt(data.module_1_basics.profit) }}
                    </span>
                  </td>
                </tr>
              </table>
              <p class="ag-tip">利润是正数 → 赚钱了；利润是负数 → 亏钱了</p>
            </div>

            <div class="ag-card">
              <div class="ag-card-title">这些数字是怎么来的？</div>
              <p><b>营业收入</b> = 所有已开票的销售单金额之和（不含增值税）</p>
              <p><b>营业成本</b> = 对应卖出去的货，当初进货时花的钱（移动加权平均成本，详见模块 7）</p>
              <p><b>费用</b> = 管理费用（房租/工资/水电）+ 销售费用（广告/运输）+ 财务费用（手续费/利息）</p>
              <p class="ag-tip">收入和成本的数据来源：你每次录入采购/销售单时，系统自动记账并生成凭证。点"财务报表 → 利润表"可以看到完整的利润表。</p>
            </div>
          </div>

          <!-- Module 2: 增值税 -->
          <div id="module-2" class="ag-module">
            <div class="ag-m-title"><span class="ag-m-num">2</span> 增值税（VAT）</div>

            <div class="ag-card ag-card-info">
              <div class="ag-card-title">增值税是什么？——「代收代付」的钱</div>
              <p>你卖东西给客户时，发票上的税额 → <b>替税务局收的</b>；你进货时，供应商发票上的税额 → <b>你已经垫付的</b>。</p>
              <p class="ag-formula">应交增值税 = 销项税（你收的）− 进项税（你垫的）</p>
              <p>增值税本质是<b>负债</b>，不是你的收入也不是你的费用。你只是「中转站」——从客户那收到税钱，扣掉自己垫的，余额上交给税务局。</p>
              <p class="ag-tip">⚠️ 增值税<b>不进入利润表</b>！如果把增值税当费用，利润就会虚低，老板看报表还以为亏了一大笔钱。</p>
            </div>

            <div class="ag-card ag-card-hl">
              <div class="ag-card-title">{{ data.period.label }} 你的增值税情况</div>
              <table class="ag-table">
                <tr><td>纳税人类型</td><td><b>{{ data.module_2_vat.taxpayer_type_label }}</b><span v-if="data.module_2_vat.taxpayer_type === 'small_scale'" class="ag-tag-tax">小规模普票季度≤30万免税</span></td></tr>
                <tr v-if="data.module_2_vat.taxpayer_type === 'general'">
                  <td>销项税额</td><td><b>{{ fmt(data.module_2_vat.output_tax) }}</b></td>
                </tr>
                <tr v-if="data.module_2_vat.taxpayer_type === 'general'">
                  <td>进项税额</td><td><b>{{ fmt(data.module_2_vat.input_tax) }}</b></td>
                </tr>
                <tr v-if="data.module_2_vat.taxpayer_type === 'general' && data.module_2_vat.carry_forward">
                  <td>期初留抵</td><td><b>{{ fmt(data.module_2_vat.carry_forward) }}</b></td>
                </tr>
                <tr>
                  <td>本季度发票总额（含税）</td>
                  <td><b>{{ fmt(data.module_2_vat.quarterly_total) }}</b>
                    <span v-if="data.module_2_vat.is_under_threshold && data.module_2_vat.taxpayer_type === 'small_scale'" class="ag-tag-ok">≤30万，普票免税！</span>
                  </td>
                </tr>
                <tr v-if="data.module_2_vat.taxpayer_type === 'small_scale'">
                  <td>其中：普通发票收入</td>
                  <td><b>{{ fmt(data.module_2_vat.ordinary_revenue) }}</b>
                    <span v-if="data.module_2_vat.is_under_threshold" class="ag-tag-ok">免税</span>
                  </td>
                </tr>
                <tr v-if="data.module_2_vat.taxpayer_type === 'small_scale'">
                  <td>其中：专用发票收入</td>
                  <td><b>{{ fmt(data.module_2_vat.special_revenue) }}</b>
                    <span class="ag-tag-tax">减按1%征收</span>
                  </td>
                </tr>
                <tr class="ag-table-hl">
                  <td>应缴增值税</td>
                  <td><b>{{ fmt(data.module_2_vat.vat_payable) }}</b>
                    <span v-if="data.module_2_vat.reduction_item" style="color:var(--text-placeholder);font-weight:400;font-size:12px">（{{ data.module_2_vat.reduction_item }}）</span>
                  </td>
                </tr>
              </table>
            </div>

            <div class="ag-card">
              <div class="ag-card-title">小规模纳税人增值税规则（你的类型）</div>
              <p v-if="data.module_2_vat.taxpayer_type === 'small_scale'">你是<b>小规模纳税人</b>，增值税的计算分为两种情况：</p>
              <ul>
                <li><b>季度总销售额 ≤ 30 万：</b>普通发票的收入<b>免税</b>（税率为 0），专用发票收入按 <b>1%</b> 交税</li>
                <li><b>季度总销售额 > 30 万：</b>所有发票收入都按 <b>1%</b> 交税</li>
              </ul>
              <p class="ag-tip">注意：免税门槛看的是<b>季度总销售额</b>（普票+专票合计），但只要超了 30 万，连普票也要按 1% 缴税。</p>
            </div>

            <div class="ag-card" v-if="data.module_2_vat.taxpayer_type === 'general'">
              <div class="ag-card-title">一般纳税人增值税规则（你的类型）</div>
              <p>你是一般纳税人，增值税按 <b>销项 − 进项</b> 计算：</p>
              <ul>
                <li>销项税 = 你开发票时向客户收取的税</li>
                <li>进项税 = 供应商向你收取的税（必须取得专用发票才能抵扣）</li>
                <li>当月销项 > 进项 → 差额上缴。当月进项 > 销项 → 差额留抵下期</li>
              </ul>
              <p class="ag-tip">一般纳税人取得普通发票不能抵扣进项税，只有增值税专用发票可以抵扣。</p>
            </div>
          </div>

          <!-- Module 3: 企业所得税 -->
          <div id="module-3" class="ag-module">
            <div class="ag-m-title"><span class="ag-m-num">3</span> 企业所得税</div>

            <div class="ag-card ag-card-info">
              <div class="ag-card-title">企业所得税是什么？——「赚了钱才交」的税</div>
              <p>只要公司今年有利润，就要按利润的一定比例给国家交税。和增值税不同：</p>
              <ul>
                <li>增值税 = 每笔交易都要交（不管赚不赚钱）</li>
                <li>企业所得税 = 只有<b>赚钱了</b>才交（亏损了不交）</li>
              </ul>
            </div>

            <div class="ag-card ag-card-hl">
              <div class="ag-card-title">{{ data.period.label }} 企业所得税计算过程（逐步推导）</div>
              <div class="ag-steps">
                <div
                  v-for="(step, idx) in data.module_3_income_tax.steps"
                  :key="idx"
                  class="ag-step"
                  :class="'ag-step-' + step.cls"
                >
                  <div class="ag-step-dot"></div>
                  <div class="ag-step-body">
                    <div class="ag-step-row">
                      <span class="ag-step-label">{{ step.label }}</span>
                      <span class="ag-step-value">{{ typeof step.value === 'number' ? fmt(step.value) : step.value }}</span>
                    </div>
                    <div class="ag-step-explain">{{ step.explain }}</div>
                  </div>
                </div>
              </div>
            </div>

            <div class="ag-card">
              <div class="ag-card-title">税率说明</div>
              <ul>
                <li><b>一般企业</b>：法定税率 25%</li>
                <li><b>小型微利企业</b>：年利润 ≤ 300 万，实际税率 <b>5%</b>（25% × 减按 20% → 实际 5%）</li>
                <li><b>个体工商户</b>：不缴企业所得税（缴个人所得税，本系统不处理个税）</li>
              </ul>
              <p class="ag-tip">企业所得税按<b>季度预缴</b>，次年 5 月 31 日前<b>年度汇算清缴</b>多退少补。</p>
            </div>
          </div>

          <!-- Module 4: 附加税 -->
          <div id="module-4" class="ag-module">
            <div class="ag-m-title"><span class="ag-m-num">4</span> 附加税</div>

            <div class="ag-card ag-card-info">
              <div class="ag-card-title">附加税 = 「附在增值税身上」的税</div>
              <p>附加税以为基数：你交了多少增值税，就按这个金额的固定比例再交附加税。增值税是 0 → 附加税也是 0。</p>
            </div>

            <div class="ag-card ag-card-hl">
              <div class="ag-card-title">你的附加税明细（基数：本月应缴增值税 {{ fmt(data.module_4_surcharge.vat_payable) }} 元）</div>
              <table class="ag-table">
                <tr v-for="item in data.module_4_surcharge.breakdown" :key="item.name">
                  <td>{{ item.name }}</td>
                  <td>{{ item.rate }}</td>
                  <td><b>{{ fmt(item.amount) }}</b></td>
                  <td style="font-size:12px;color:var(--text-placeholder)">{{ item.law }}</td>
                </tr>
                <tr class="ag-table-hl">
                  <td>附加税合计</td>
                  <td>{{ data.module_4_surcharge.effective_rate }}（法定 {{ data.module_4_surcharge.full_rate }}）</td>
                  <td><b>{{ fmt(data.module_4_surcharge.total) }}</b></td>
                  <td>
                    <span v-if="data.module_4_surcharge.is_halved" class="ag-tag-ok">减半征收</span>
                    <span v-else class="ag-tag-tax">全额征收</span>
                  </td>
                </tr>
              </table>
              <p class="ag-tip" style="margin-top:8px">{{ data.module_4_surcharge.reduction_note }}</p>
            </div>

            <div class="ag-card">
              <div class="ag-card-title">三项附加税详解</div>
              <ul>
                <li><b>城市建设维护税（7%）</b>—— 修路、修桥、市政维护的钱</li>
                <li><b>教育费附加（3%）</b>—— 办学校、办教育的钱</li>
                <li><b>地方教育附加（2%）</b>—— 地方政府办教育的补充资金</li>
              </ul>
              <p class="ag-tip">附加税在利润表上属于"税金及附加"科目，会影响利润。它和增值税不同——附加税是真正的<b>费用</b>。</p>
            </div>
          </div>

          <!-- Module 5: 月末结账 -->
          <div id="module-5" class="ag-module">
            <div class="ag-m-title"><span class="ag-m-num">5</span> 月末结账</div>

            <div class="ag-card ag-card-info">
              <div class="ag-card-title">月结就是「关账」——这个月的账本锁上，开始算下个月</div>
              <p>每个月最后一天，必须按 <b>5 步流程</b>逐一执行。跳过任何一步都会导致报表数据不完整。</p>
              <p class="ag-tip">月结操作入口：财务报表 → 选择月结期间 → 点击"执行月结"</p>
            </div>

            <div class="ag-card">
              <div class="ag-card-title">五步月结流程</div>
              <div v-for="step in data.module_5_month_close.steps" :key="step.order" style="margin-bottom:20px;padding:16px;background:var(--bg-page);border-radius:10px">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                  <span class="ag-step-num">{{ step.order }}</span>
                  <span class="ag-step-title">{{ step.title }}</span>
                  <span class="ag-card-code">BR：{{ step.br }}</span>
                </div>
                <p style="font-size:14px;color:var(--text-regular);margin:4px 0"><b>做什么：</b>{{ step.what }}</p>
                <p style="font-size:14px;color:var(--text-regular);margin:4px 0"><b>为什么：</b>{{ step.why }}</p>
                <p style="font-size:14px;color:var(--text-regular);margin:4px 0;white-space:pre-line"><b>怎么做：</b>{{ step.how }}</p>
                <p class="ag-step-meta">系统行为：{{ step.trigger }}</p>
              </div>
            </div>

            <div class="ag-card ag-card-warn">
              <div class="ag-card-title">重要提醒</div>
              <p>{{ data.module_5_month_close.note }}</p>
            </div>

            <div class="ag-card">
              <div class="ag-card-title">年度税务日历（全年税务关键节点一览）</div>
              <div style="overflow-x:auto">
                <table class="ag-table">
                  <tr style="font-weight:700;color:var(--text-primary)">
                    <td>时间</td>
                    <td>事项</td>
                    <td>截止日期</td>
                    <td>紧急</td>
                  </tr>
                  <tr v-for="(item, idx) in data.module_5_month_close.tax_calendar" :key="idx" :class="{ 'ag-table-urgent': item.urgent }">
                    <td>{{ item.period }}</td>
                    <td>{{ item.task }}</td>
                    <td>{{ item.deadline }}</td>
                    <td><span v-if="item.urgent" style="color:var(--danger);font-weight:600">⚠ 勿错过</span><span v-else style="color:var(--text-placeholder)">—</span></td>
                  </tr>
                </table>
              </div>
            </div>
          </div>

          <!-- Module 6: 费用分类 -->
          <div id="module-6" class="ag-module">
            <div class="ag-m-title"><span class="ag-m-num">6</span> 费用分类</div>

            <div class="ag-card ag-card-info">
              <div class="ag-card-title">费用不是「花了钱」那么简单</div>
              <p>会计上把费用分成三大类 + 两类税务费用，分清楚了报表才有参考价值：</p>
            </div>

            <div v-for="cat in data.module_6_expenses.categories" :key="cat.code" class="ag-card">
              <div class="ag-card-title">{{ cat.name }} <span class="ag-card-code">{{ cat.code }}</span></div>
              <p><b>是什么：</b>{{ cat.what }}</p>
              <p><b>常见例子：</b>{{ cat.examples.join('、') }}</p>
              <p class="ag-tip">{{ cat.tip }}</p>
            </div>

            <div class="ag-card ag-card-warn">
              <div class="ag-card-title">新手最容易犯的 3 个错误</div>
              <div v-for="(m, idx) in data.module_6_expenses.common_mistakes" :key="idx" class="ag-mistake">
                <div class="ag-mistake-title">❌ 错误 {{ idx + 1 }}：{{ m.mistake }}</div>
                <div class="ag-mistake-fix">✅ 正确做法：{{ m.correct }}</div>
              </div>
            </div>
          </div>

          <!-- Module 7: 库存成本 -->
          <div id="module-7" class="ag-module">
            <div class="ag-m-title"><span class="ag-m-num">7</span> 库存成本（移动加权平均法）</div>

            <div class="ag-card ag-card-info">
              <div class="ag-card-title">为什么不能简单地用进价算成本？</div>
              <p>同一件商品，你 1 月进价 5 元，3 月进价 8 元，5 月进价 6 元——那现在仓库里这批货的平均成本是多少？</p>
              <p>系统用「<b>移动加权平均法</b>」自动计算：<b>每次进货后都重新算一次均价。</b></p>
              <p class="ag-formula">{{ data.module_7_cogs.method_explain }}</p>
            </div>

            <div class="ag-card ag-card-hl">
              <div class="ag-card-title">举例说明</div>
              <div class="ag-cogs-demo">
                <div class="ag-cogs-row">{{ data.module_7_cogs.example.before.desc }}</div>
                <div class="ag-cogs-row">→ 库存 {{ data.module_7_cogs.example.before.qty }} 个 × {{ data.module_7_cogs.example.before.unit_price }} 元 = {{ data.module_7_cogs.example.before.total }} 元</div>
                <div class="ag-cogs-row" style="margin-top:8px">{{ data.module_7_cogs.example.purchase.desc }}</div>
                <div class="ag-cogs-row">→ 新增 {{ data.module_7_cogs.example.purchase.qty }} 个 × {{ data.module_7_cogs.example.purchase.unit_price }} 元 = {{ data.module_7_cogs.example.purchase.total }} 元</div>
                <div class="ag-cogs-calc">新均价 = {{ data.module_7_cogs.example.calc }}</div>
                <div class="ag-cogs-row" style="margin-top:8px">{{ data.module_7_cogs.example.after.desc }}</div>
              </div>
            </div>

            <div class="ag-card">
              <div class="ag-card-title">卖出时怎么算？</div>
              <p>{{ data.module_7_cogs.sale_principle }}</p>
            </div>

            <div class="ag-card ag-card-warn">
              <div class="ag-card-title">四条核心规则</div>
              <ul>
                <li v-for="rule in data.module_7_cogs.rules" :key="rule">{{ rule }}</li>
              </ul>
            </div>
          </div>

          <!-- Module 8: 红冲/冲销 -->
          <div id="module-8" class="ag-module">
            <div class="ag-m-title"><span class="ag-m-num">8</span> 红冲/冲销 —— 为什么不能直接删？</div>

            <div class="ag-card ag-card-info">
              <div class="ag-card-title">{{ data.module_8_reversal.principle }}</div>
              <p style="font-size:15px;color:var(--primary);font-weight:600;margin-top:8px">{{ data.module_8_reversal.analogy }}</p>
            </div>

            <div v-for="t in data.module_8_reversal.types" :key="t.name" class="ag-card">
              <div class="ag-card-title">{{ t.name }} <span class="ag-card-code">{{ t.br }}</span></div>
              <p><b>接口：</b><code style="background:var(--bg-page);padding:2px 6px;border-radius:4px;font-size:13px">{{ t.route }}</code></p>
              <p>{{ t.what }}</p>
              <p v-if="t.path" class="ag-tip">{{ t.path }}</p>
            </div>

            <div class="ag-card">
              <div class="ag-card-title">这些表永远不能直接改</div>
              <table class="ag-table">
                <tr style="font-weight:700;color:var(--text-primary)">
                  <td>表名</td>
                  <td>说明</td>
                </tr>
                <tr v-for="imm in data.module_8_reversal.immutable_tables" :key="imm.table">
                  <td><code style="background:var(--bg-page);padding:2px 6px;border-radius:4px;font-size:13px">{{ imm.table }}</code></td>
                  <td>{{ imm.desc }}</td>
                </tr>
              </table>
            </div>
          </div>

          <!-- Module 9: 三大报表 -->
          <div id="module-9" class="ag-module">
            <div class="ag-m-title"><span class="ag-m-num">9</span> 三大财务报表</div>

            <div class="ag-card ag-card-info">
              <div class="ag-card-title">老板看报表就三件事：赚多少？欠多少？钱在哪？</div>
              <p>三张表各自回答一个问题，合在一起就是公司完整的财务状况。</p>
            </div>

            <div v-for="r in data.module_9_statements.reports" :key="r.name" class="ag-card">
              <div class="ag-card-title">{{ r.name }}（{{ r.alt_name }}）<span class="ag-card-code">{{ r.code }}</span></div>

              <div class="ag-report-purpose">
                <p>{{ r.purpose }}</p>
              </div>

              <div class="ag-report-formula">
                <p class="ag-formula-lg">{{ r.formula }}</p>
                <p class="ag-tip">{{ r.formula_explain }}</p>
              </div>

              <div v-if="r.structure" class="ag-report-structure">
                <div v-for="(s, si) in r.structure" :key="si" class="ag-bs-item">
                  <div class="ag-bs-side">{{ s.side || s.line }}</div>
                  <div class="ag-bs-detail">
                    <div>{{ s.items || s.explain }}</div>
                    <div v-if="s.examples" style="font-size:12px;margin-top:2px">{{ s.examples }}</div>
                    <div v-if="s.value !== undefined" style="font-weight:700;color:var(--primary);margin-top:2px">{{ fmt(s.value) }}</div>
                  </div>
                </div>
              </div>

              <p class="ag-report-tip"><b>怎么看：</b>{{ r.how_to_read }}</p>
              <p class="ag-report-tip"><b>和别的表的关系：</b>{{ r.link }}</p>
              <div class="ag-report-page">系统入口：{{ r.system_page }}</div>
            </div>

            <div class="ag-card ag-card-hl">
              <div class="ag-card-title">{{ data.module_9_statements.linkage.title }}</div>
              <p>{{ data.module_9_statements.linkage.text }}</p>

              <div class="ag-linkage-diagram">
                <div class="ag-ld-box">
                  利润表
                  <small>净利润：{{ fmt(data.module_9_statements.net_profit) }}</small>
                </div>
                <div class="ag-ld-arrow">→</div>
                <div class="ag-ld-box">
                  资产负债表
                  <small>未分配利润增加 {{ fmt(data.module_9_statements.net_profit) }}</small>
                </div>
                <div class="ag-ld-arrow">→</div>
                <div class="ag-ld-box">
                  现金流量表
                  <small>解释现金变动</small>
                </div>
              </div>
            </div>
          </div>

          <div class="ag-footer">
            <p>数据来源：本系统实时业务数据</p>
            <p>仅供参考，正式报税请以税务局系统为准</p>
          </div>
        </div>
      </template>

      <el-empty v-if="!data && !loading" description="暂无数据，请选择账本和期间" :image-size="160" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import accountingGuideApi from '../api/accountingGuide'
import { formatMoney } from '../utils/format'
import { handleError } from '../utils/errorHandler'
import { currentYear, currentQuarter, generateYears } from '../utils/date'

const year = ref(currentYear())
const quarter = ref(currentQuarter())
const years = ref([])
const data = ref(null)
const loading = ref(false)
const activeModule = ref('module-1')

const modules = [
  { id: 'module-1', icon: '①', title: '进销存基础' },
  { id: 'module-2', icon: '②', title: '增值税' },
  { id: 'module-3', icon: '③', title: '企业所得税' },
  { id: 'module-4', icon: '④', title: '附加税' },
  { id: 'module-5', icon: '⑤', title: '月末结账' },
  { id: 'module-6', icon: '⑥', title: '费用分类' },
  { id: 'module-7', icon: '⑦', title: '库存成本' },
  { id: 'module-8', icon: '⑧', title: '红冲/冲销' },
  { id: 'module-9', icon: '⑨', title: '三大报表' },
]

const fmt = (v) => formatMoney(v)

const genYears = () => {
  years.value = generateYears(-3, 0)
}

const query = async () => {
  loading.value = true
  try {
    data.value = await accountingGuideApi.getAccountingGuide(year.value, quarter.value)
  } catch (e) {
    handleError(e, { defaultMsg: '获取会计规则指引失败' })
    data.value = null
  } finally {
    loading.value = false
  }
}

const scrollToModule = (id) => {
  activeModule.value = id
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const onScroll = () => {
  for (let i = modules.length - 1; i >= 0; i--) {
    const el = document.getElementById(modules[i].id)
    if (el && el.getBoundingClientRect().top <= 160) {
      activeModule.value = modules[i].id
      break
    }
  }
}

onMounted(() => {
  genYears()
  query()
  document.querySelector('.ag-main')?.addEventListener('scroll', onScroll)
})
</script>

<style scoped>
.ag-shell { display: flex; height: 100%; overflow: hidden; }
.ag-nav { width: 180px; flex-shrink: 0; background: var(--bg-card); border-right: 1px solid var(--border-lighter); padding: 16px 10px; overflow-y: auto; }
.ag-nav-hd { font-size: 14px; font-weight: 700; color: var(--primary); padding: 0 6px 12px; border-bottom: 1px solid var(--border-lighter); margin-bottom: 8px; }
.ag-nav-item { display: block; padding: 7px 10px; border-radius: 8px; font-size: 13px; color: var(--text-secondary); cursor: pointer; text-decoration: none; transition: all 0.15s; margin: 2px 0; }
.ag-nav-item:hover { background: var(--primary-light); color: var(--primary); }
.ag-nav-item.active { background: var(--primary); color: #fff; font-weight: 600; }
.ag-main { flex: 1; overflow-y: auto; padding: 0; }
.ag-topbar { position: sticky; top: 0; z-index: 10; background: var(--bg-page); padding: 20px 32px 16px; border-bottom: 1px solid var(--border-lighter); display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
.ag-topbar-title { font-size: 18px; font-weight: 800; color: var(--text-primary); }
.ag-topbar-sub { font-size: 13px; color: var(--text-placeholder); }
.ag-filters { margin-left: auto; display: flex; gap: 8px; }
.ag-content { padding: 0 32px 60px; }
.ag-info-bar { margin: 16px 0 8px; padding: 10px 16px; background: var(--bg-card); border: 1px solid var(--border-lighter); border-radius: 10px; display: flex; align-items: center; gap: 10px; font-size: 13px; flex-wrap: wrap; }
.ag-module { padding-top: 24px; margin-bottom: 8px; }
.ag-m-title { font-size: 20px; font-weight: 800; color: var(--text-primary); padding-bottom: 12px; margin-bottom: 16px; border-bottom: 2px solid var(--primary); display: flex; align-items: center; gap: 10px; }
.ag-m-num { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 8px; background: var(--primary); color: #fff; font-size: 15px; font-weight: 700; flex-shrink: 0; }
.ag-card { background: var(--bg-card); border: 1px solid var(--border-lighter); border-radius: 12px; padding: 20px 24px; margin-bottom: 14px; line-height: 1.8; }
.ag-card-title { font-size: 15px; font-weight: 700; color: var(--text-primary); margin-bottom: 10px; }
.ag-card p { font-size: 14px; color: var(--text-regular); margin: 6px 0; }
.ag-card ul { margin: 6px 0; padding-left: 20px; }
.ag-card li { font-size: 14px; color: var(--text-regular); margin: 4px 0; }
.ag-card-info { border-left: 4px solid var(--primary); background: var(--primary-light); }
.ag-card-hl { border-left: 4px solid var(--success); background: #f0faf0; }
.ag-card-warn { border-left: 4px solid var(--warning); background: #fef9e7; }
.ag-formula { font-family: 'Consolas','Monaco',monospace; font-size: 15px !important; padding: 4px 0; }
.ag-formula-lg { font-family: 'Consolas','Monaco',monospace; font-size: 16px !important; padding: 8px 0; font-weight: 600; }
.ag-positive { color: var(--success); }
.ag-negative { color: var(--danger); }
.ag-source { font-size: 12px !important; color: var(--text-placeholder) !important; margin-top: 4px; }
.ag-tip { font-size: 12px; color: var(--text-placeholder); font-style: italic; }
.ag-table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 14px; }
.ag-table td { padding: 8px 12px; border-bottom: 1px solid var(--border-lighter); }
.ag-table td:first-child { color: var(--text-secondary); width: 220px; }
.ag-table-hl td { background: var(--primary-light); font-weight: 700; }
.ag-table-urgent { background: #fef2f2; }
.ag-cell-pass { color: var(--success); font-weight: 600; }
.ag-cell-fail { color: var(--danger); font-weight: 600; }
.ag-tag-ok { display: inline; margin-left: 8px; padding: 2px 8px; border-radius: 4px; font-size: 12px; background: var(--success-light); color: var(--success); }
.ag-tag-tax { display: inline; margin-left: 8px; padding: 2px 8px; border-radius: 4px; font-size: 12px; background: var(--warning-light); color: var(--warning); }
.ag-steps { display: flex; flex-direction: column; gap: 2px; }
.ag-step { display: flex; gap: 14px; padding: 12px 0; border-bottom: 1px dashed var(--border-lighter); }
.ag-step:last-child { border-bottom: none; }
.ag-step-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
.ag-step-positive .ag-step-dot { background: var(--success); }
.ag-step-negative .ag-step-dot { background: var(--danger); }
.ag-step-subtotal .ag-step-dot { background: var(--warning); }
.ag-step-rate .ag-step-dot { background: var(--primary); }
.ag-step-reduction .ag-step-dot { background: var(--info); }
.ag-step-result .ag-step-dot { background: var(--primary); width: 16px; height: 16px; }
.ag-step-info .ag-step-dot { background: var(--primary); }
.ag-step-num { width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0; background: var(--primary); color: #fff; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; margin-top: 2px; }
.ag-step-body { flex: 1; }
.ag-step-row { display: flex; justify-content: space-between; align-items: baseline; }
.ag-step-label { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.ag-step-value { font-family: 'Consolas','Monaco',monospace; font-size: 16px; font-weight: 700; }
.ag-step-result .ag-step-value { font-size: 20px; color: var(--primary); }
.ag-step-explain { font-size: 13px; color: var(--text-placeholder); margin-top: 4px; line-height: 1.6; }
.ag-step-title { font-size: 15px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px; }
.ag-step-meta { font-size: 12px !important; color: var(--text-placeholder) !important; }
.ag-mistake { margin: 12px 0; padding: 12px; border-radius: 8px; background: rgba(255,255,255,0.5); }
.ag-mistake-title { font-size: 13px; color: var(--danger); font-weight: 600; }
.ag-mistake-fix { font-size: 13px; color: var(--success); font-weight: 600; margin-top: 2px; }
.ag-cogs-demo { background: var(--bg-page); border-radius: 10px; padding: 16px 20px; display: flex; flex-direction: column; gap: 8px; }
.ag-cogs-row { font-size: 14px; color: var(--text-regular); }
.ag-cogs-calc { padding: 10px 14px; border-radius: 8px; background: var(--primary-light); color: var(--primary); font-weight: 700; font-family: 'Consolas','Monaco',monospace; }
.ag-footer { text-align: center; padding: 40px 0 20px; font-size: 13px; color: var(--text-placeholder); }
.ag-card-code { font-size: 11px; color: var(--text-placeholder); margin-left: 8px; font-weight: 400; }
.ag-report-purpose { margin: 12px 0; }
.ag-report-purpose p { margin: 4px 0; }
.ag-report-formula { margin: 12px 0; padding: 12px; background: var(--bg-page); border-radius: 8px; }
.ag-report-structure { margin: 12px 0; }
.ag-report-tip { font-size: 13px; color: var(--text-secondary); margin: 8px 0; }
.ag-report-page { font-size: 12px; color: var(--primary); margin-top: 8px; padding: 6px 12px; background: var(--primary-light); border-radius: 6px; display: inline-block; }
.ag-bs-item { padding: 8px 0; border-bottom: 1px dashed var(--border-lighter); display: flex; gap: 12px; align-items: flex-start; }
.ag-bs-item:last-child { border-bottom: none; }
.ag-bs-side { font-weight: 600; font-size: 14px; color: var(--text-primary); min-width: 160px; }
.ag-bs-detail { font-size: 13px; color: var(--text-placeholder); flex: 1; }
.ag-linkage-diagram { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 20px; padding: 20px; background: var(--bg-page); border-radius: 12px; flex-wrap: wrap; }
.ag-ld-box { background: var(--bg-card); border: 2px solid var(--primary); border-radius: 10px; padding: 14px 20px; text-align: center; font-weight: 700; font-size: 15px; min-width: 140px; }
.ag-ld-box small { display: block; font-size: 12px; color: var(--text-placeholder); font-weight: 400; margin-top: 4px; }
.ag-ld-arrow { font-size: 24px; font-weight: 800; color: var(--primary); }

.ag-nav::-webkit-scrollbar { width: 4px; }
.ag-nav::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 2px; }
.ag-main::-webkit-scrollbar { width: 6px; }
.ag-main::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }
</style>
