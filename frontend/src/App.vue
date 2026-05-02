<template>
  <div>
    <header class="topbar">
      <div class="brand" @click="setPage('procurements')">
        <span class="brand-mark">PM</span>
        <span>采购管理系统</span>
      </div>
      <nav class="nav">
        <button v-for="item in navItems" :key="item.key" :class="{ active: page === item.key }" @click="setPage(item.key)">
          <component :is="item.icon" :size="17" />
          {{ item.label }}
        </button>
      </nav>
      <div class="admin-box">
        <span v-if="admin.is_admin" class="admin-name">{{ admin.username }}{{ admin.is_root ? ' · 根管理员' : '' }}</span>
        <button class="ghost" @click="admin.is_admin ? logout() : (showLogin = true)">
          <LogOut v-if="admin.is_admin" :size="16" />
          <LogIn v-else :size="16" />
          {{ admin.is_admin ? '退出' : '登录' }}
        </button>
      </div>
    </header>

    <main class="shell">
      <section class="page-title-row">
        <div>
          <span class="eyebrow">{{ currentNav.eyebrow }}</span>
          <h1>{{ currentNav.title }}</h1>
        </div>
      </section>

      <section v-if="page === 'procurements'" class="view">
        <div class="toolbar">
          <MultiSelect label="年份" :options="meta.years.map(y => ({ label: `${y}年`, value: String(y) }))" v-model="proc.filters.year" @change="reloadProcurements" />
          <MultiSelect label="月份" :options="meta.months.map(m => ({ label: `${m}月`, value: String(m) }))" v-model="proc.filters.month" @change="reloadProcurements" />
          <MultiSelect label="部门" :options="optionMap.department.map(value => ({ label: value, value }))" v-model="proc.filters.department" @change="reloadProcurements" />
          <MultiSelect label="状态" :options="optionMap.status.map(value => ({ label: value, value }))" v-model="proc.filters.status" @change="reloadProcurements" />
          <label class="search-field">搜索<input v-model="proc.filters.keyword" placeholder="物品、人员、工号、原因" @keyup.enter="reloadProcurements" /></label>
          <div class="toolbar-actions">
            <button class="primary" @click="reloadProcurements"><Search :size="16" />查询</button>
            <button @click="resetProcFilters"><RotateCcw :size="16" />重置</button>
            <button v-if="admin.is_admin" class="success" @click="openProcForm()"><Plus :size="16" />新增</button>
          </div>
        </div>

        <div class="kpis">
          <div><span>记录数</span><strong>{{ proc.summary.total_count }}</strong></div>
          <div><span>总金额</span><strong>{{ money(proc.summary.total_amount) }}</strong></div>
          <div><span>待跟进</span><strong>{{ proc.summary.pending_count }}</strong></div>
          <div><span>待跟进金额</span><strong>{{ money(proc.summary.pending_amount) }}</strong></div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <strong>采购明细</strong>
              <span>{{ proc.total }} 条记录</span>
            </div>
            <button v-if="admin.is_admin" class="success" @click="openProcForm()"><Plus :size="16" />新增采购</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>期间</th><th>采购内容</th><th>需求信息</th><th>数量</th><th>单价</th><th>总金额</th><th>原因</th><th>状态</th><th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in proc.items" :key="row.id">
                  <td>{{ row.year }}年{{ row.month }}月<br /><small>{{ row.asset_category }}</small></td>
                  <td><strong>{{ row.item_name }}</strong><br /><small>{{ [row.manufacturer, row.model].filter(Boolean).join(' / ') || '-' }}</small></td>
                  <td>{{ row.department }}<br /><small>{{ row.requester_name }} / {{ row.requester_id }}</small></td>
                  <td>
                    <input v-if="admin.is_admin" class="inline-number" inputmode="numeric" pattern="[0-9]*" :value="row.budget_qty" @input="sanitizeIntegerInput" @change="inlineUpdateProc(row, 'budget_qty', $event.target.value)" />
                    <span v-else>{{ row.budget_qty }}</span>
                  </td>
                  <td class="amount">
                    <input v-if="admin.is_admin" class="inline-number money-input" inputmode="decimal" :value="row.unit_price" @input="sanitizeDecimalInput" @change="inlineUpdateProc(row, 'unit_price', $event.target.value)" />
                    <span v-else>{{ money(row.unit_price) }}</span>
                  </td>
                  <td class="amount strong">{{ money(row.total_price) }}</td>
                  <td class="reason-cell">
                    <textarea v-if="admin.is_admin" class="inline-reason" :value="row.reason" @blur="inlineUpdateProc(row, 'reason', $event.target.value)" @keydown.ctrl.enter="$event.target.blur()" @keydown.meta.enter="$event.target.blur()"></textarea>
                    <span v-else class="clamp" :title="row.reason">{{ row.reason }}</span>
                  </td>
                  <td>
                    <select v-if="admin.is_admin" class="status-select" v-model="row.status" @change="quickUpdateProc(row, { status: row.status })">
                      <option v-for="s in optionMap.status" :key="s" :value="s">{{ s }}</option>
                    </select>
                    <span v-else :class="['status', statusClass(row.status)]">{{ row.status }}</span>
                  </td>
                  <td class="row-actions">
                    <button title="查看" @click="openProcDetail(row.id)"><Eye :size="16" /></button>
                    <button v-if="admin.is_admin" title="编辑" @click="openProcForm(row.id)"><Edit3 :size="16" /></button>
                    <button v-if="admin.is_admin" title="删除" class="danger-text" @click="deleteProc(row.id)"><Trash2 :size="16" /></button>
                  </td>
                </tr>
                <tr v-if="!proc.items.length"><td colspan="9" class="empty">暂无采购数据</td></tr>
              </tbody>
            </table>
          </div>
          <Pagination :page="proc.page" :pages="proc.pages" @change="loadProcurements" />
        </div>
      </section>

      <section v-if="page === 'attachments'" class="view">
        <div class="toolbar">
          <label>年份<select v-model="attachment.filters.year"><option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option></select></label>
          <label>月份<select v-model="attachment.filters.month"><option v-for="m in meta.months" :key="m" :value="m">{{ m }}月</option></select></label>
          <div class="toolbar-actions">
            <button class="primary" @click="reloadAttachments"><Search :size="16" />查询</button>
            <button v-if="admin.is_admin" class="success" @click="showUpload = true"><Upload :size="16" />上传</button>
          </div>
        </div>
        <div class="kpis">
          <div><span>部门数</span><strong>{{ attachment.coverage.total_departments || 0 }}</strong></div>
          <div><span>已上传</span><strong>{{ attachment.coverage.uploaded_departments || 0 }}</strong></div>
          <div><span>缺失</span><strong>{{ attachment.coverage.missing_departments || 0 }}</strong></div>
          <div><span>附件数</span><strong>{{ attachmentFileCount }}</strong></div>
        </div>
        <div class="coverage-meter"><span :style="{ width: `${coveragePercent}%` }"></span><strong>{{ coveragePercent }}%</strong></div>
        <div class="coverage-grid">
          <div v-for="item in attachment.coverage.items" :key="item.department" :class="['coverage-card', item.uploaded ? 'ok' : 'miss']">
            <strong>{{ item.department }}</strong>
            <span>{{ item.uploaded ? `已上传 ${item.file_count} 个附件` : '未上传' }}</span>
          </div>
        </div>
        <div class="file-grid">
          <div v-for="group in attachment.groups" :key="`${group.year}-${group.month}-${group.department}`" class="file-group">
            <div class="file-group-head"><strong>{{ group.year }}年{{ group.month }}月 · {{ group.department }}</strong><span>{{ group.count }} 个</span></div>
            <div v-for="file in group.files" :key="file.id" class="file-row">
              <span class="file-ext">{{ fileExt(file.original_name) }}</span>
              <div><a :href="`/api/attachments/${file.id}/download`">{{ file.original_name }}</a><small>{{ file.description || file.upload_time }} · {{ size(file.file_size) }}</small></div>
              <div class="file-actions">
                <a class="icon-button" :href="`/api/attachments/${file.id}/download`" title="下载"><Download :size="16" /></a>
                <button v-if="admin.is_admin" class="danger-text" title="删除" @click="deleteAttachment(file.id)"><Trash2 :size="16" /></button>
              </div>
            </div>
          </div>
          <div v-if="!attachment.groups.length" class="empty panel">暂无附件数据</div>
        </div>
      </section>

      <section v-if="page === 'reports'" class="view">
        <div class="toolbar">
          <label>年份<select v-model="report.filters.year" @change="reloadReports"><option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option></select></label>
          <MultiSelect label="月份" :options="meta.months.map(m => ({ label: `${m}月`, value: String(m) }))" v-model="report.filters.month" @change="reloadReports" />
          <MultiSelect label="部门" :options="optionMap.department.map(value => ({ label: value, value }))" v-model="report.filters.department" @change="reloadReports" />
          <MultiSelect label="采购种类" :options="optionMap.asset_category.map(value => ({ label: value, value }))" v-model="report.filters.asset_category" @change="reloadReports" />
          <div class="toolbar-actions"><button @click="resetReportFilters"><RotateCcw :size="16" />重置</button></div>
        </div>
        <div class="kpis">
          <div><span>记录数</span><strong>{{ report.overview.total_count || 0 }}</strong></div>
          <div><span>总金额</span><strong>{{ money(report.overview.total_amount) }}</strong></div>
          <div><span>采购数量</span><strong>{{ report.overview.total_qty || 0 }}</strong></div>
          <div><span>待跟进金额</span><strong>{{ money(report.overview.pending_amount) }}</strong></div>
        </div>
        <div class="report-grid">
          <div class="panel chart-panel wide">
            <div class="panel-head">
              <div><strong>月度采购趋势</strong><span>先看总量，再看金额是否集中在某几个月</span></div>
            </div>
            <div ref="trendChart" class="chart trend-chart"></div>
          </div>
          <div class="panel chart-panel">
            <div class="panel-head">
              <div><strong>采购种类占比</strong><span>看竞品、低值易耗、固定资产等结构</span></div>
              <button v-if="admin.is_admin" @click="exportReport('category-distribution')"><Download :size="16" />导出</button>
            </div>
            <div ref="ratioChart" class="chart"></div>
          </div>
          <div class="panel chart-panel">
            <div class="panel-head">
              <div><strong>部门采购排行</strong><span>看哪些部门采购金额最高</span></div>
              <button v-if="admin.is_admin" @click="exportReport('department-ratio')"><Download :size="16" />导出</button>
            </div>
            <div ref="categoryChart" class="chart"></div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-head"><div><strong>部门 x 采购种类交叉分析</strong><span>金额越高，底色越深</span></div><button v-if="admin.is_admin" @click="exportReport('department-category-matrix')"><Download :size="16" />导出</button></div>
          <div class="table-wrap matrix-wrap">
            <table class="matrix-table">
              <thead><tr><th>部门</th><th v-for="category in report.matrix.categories" :key="category">{{ category }}</th><th>合计</th></tr></thead>
              <tbody>
                <tr v-for="row in report.matrix.rows" :key="row.department">
                  <td><strong>{{ row.department }}</strong><br /><small>{{ row.total_count }} 条 / {{ row.total_qty }} 件</small></td>
                  <td v-for="category in report.matrix.categories" :key="category" class="amount matrix-cell" :style="matrixHeatStyle(matrixCell(row, category).total_amount)">
                    <strong>{{ money(matrixCell(row, category).total_amount) }}</strong>
                    <small>{{ matrixCell(row, category).count }} 条</small>
                  </td>
                  <td class="amount strong">{{ money(row.total_amount) }}</td>
                </tr>
                <tr v-if="!report.matrix.rows.length"><td :colspan="report.matrix.categories.length + 2" class="empty">暂无交叉分析数据</td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="panel">
          <div class="panel-head"><strong>部门采购汇总</strong><button v-if="admin.is_admin" @click="exportReport('department-summary')"><Download :size="16" />导出</button></div>
          <div class="table-wrap">
            <table><thead><tr><th>部门</th><th>记录条数</th><th>采购总数</th><th>采购总金额</th></tr></thead><tbody><tr v-for="r in report.summary" :key="r.department"><td>{{ r.department }}</td><td>{{ r.count }}</td><td>{{ r.total_qty }}</td><td class="amount strong">{{ money(r.total_amount) }}</td></tr><tr v-if="!report.summary.length"><td colspan="4" class="empty">暂无报表数据</td></tr></tbody></table>
          </div>
        </div>
      </section>

      <section v-if="page === 'settings'" class="view settings-grid">
        <div class="panel">
          <div class="panel-head"><strong>导入与导出</strong></div>
          <div class="inline-actions">
            <a class="button" href="/api/import/template"><Download :size="16" />模板</a>
            <a v-if="admin.is_admin" class="button" href="/api/import/export-data"><Download :size="16" />导出数据</a>
          </div>
          <input type="file" accept=".xlsx,.xls" @change="importFile = $event.target.files[0]" />
          <button class="primary" @click="importExcel"><Upload :size="16" />导入 Excel</button>
          <div v-if="importResult" class="notice">{{ importResult }}</div>
        </div>
        <div class="panel">
          <div class="panel-head"><strong>下拉选项</strong></div>
          <select v-model="settings.category" @change="loadOptionsByCategory"><option value="asset_category">资产分类</option><option value="department">部门</option><option value="status">采购状态</option></select>
          <div v-for="option in settings.options" :key="option.id" class="option-row">
            <input v-model="option.value" /><input type="number" v-model.number="option.sort_order" />
            <button @click="saveOption(option)"><Save :size="16" /></button>
            <button class="danger-text" @click="deleteOption(option.id)"><Trash2 :size="16" /></button>
          </div>
          <div class="inline-actions"><input v-model="settings.newOption" placeholder="新增选项" /><button class="primary" @click="addOption"><Plus :size="16" />添加</button></div>
        </div>
        <div class="panel">
          <div class="panel-head"><strong>修改密码</strong></div>
          <input type="password" v-model="passwordForm.old_password" placeholder="当前密码" />
          <input type="password" v-model="passwordForm.new_password" placeholder="新密码" />
          <button class="primary" @click="changePassword">修改密码</button>
        </div>
        <div v-if="admin.is_root" class="panel">
          <div class="panel-head"><strong>管理员账号</strong></div>
          <div class="inline-actions"><input v-model="newAdmin.username" placeholder="用户名" /><input type="password" v-model="newAdmin.password" placeholder="密码" /><button class="primary" @click="createAdmin"><Plus :size="16" />添加</button></div>
          <div v-for="user in adminUsers" :key="user.id" class="option-row"><span>{{ user.username }}{{ user.is_root ? ' · 根' : '' }}</span><small>{{ user.created_at }}</small><button class="danger-text" @click="deleteAdmin(user.id)"><Trash2 :size="16" /></button></div>
        </div>
      </section>
    </main>

    <div v-if="toast" :class="['toast', toast.type]">{{ toast.message }}</div>

    <div v-if="showLogin" class="modal-backdrop">
      <form class="modal-card" @submit.prevent="login">
        <h2>管理员登录</h2>
        <input v-model="loginForm.username" placeholder="用户名" />
        <input type="password" v-model="loginForm.password" placeholder="密码" />
        <div class="modal-actions"><button type="button" @click="showLogin = false">取消</button><button class="primary">登录</button></div>
      </form>
    </div>

    <div v-if="procModal.open" class="modal-backdrop">
      <form class="modal-card wide" @submit.prevent="saveProc">
        <h2>{{ procModal.id ? '编辑采购申请' : '新增采购申请' }}</h2>
        <div class="form-grid">
          <label>年份<select v-model.number="procForm.year"><option v-for="y in meta.years" :key="y" :value="y">{{ y }}</option></select></label>
          <label>月份<select v-model.number="procForm.month"><option v-for="m in meta.months" :key="m" :value="m">{{ m }}</option></select></label>
          <label>资产分类<select v-model="procForm.asset_category"><option v-for="c in optionMap.asset_category" :key="c" :value="c">{{ c }}</option></select></label>
          <label>物品名称<input v-model="procForm.item_name" /></label>
          <label>厂家<input v-model="procForm.manufacturer" /></label>
          <label>型号<input v-model="procForm.model" /></label>
          <label>数量<input type="number" v-model.number="procForm.budget_qty" min="1" /></label>
          <label>单价<input type="number" v-model.number="procForm.unit_price" min="0" step="0.01" /></label>
          <label>部门<select v-model="procForm.department"><option v-for="d in optionMap.department" :key="d" :value="d">{{ d }}</option></select></label>
          <label>需求人<input v-model="procForm.requester_name" /></label>
          <label>工号<input v-model="procForm.requester_id" /></label>
          <label>资产编码<input v-model="procForm.asset_code" /></label>
          <label>状态<select v-model="procForm.status"><option v-for="s in optionMap.status" :key="s" :value="s">{{ s }}</option></select></label>
          <label class="span-2">申请原因<textarea v-model="procForm.reason"></textarea></label>
          <label class="span-2">备注<textarea v-model="procForm.remark"></textarea></label>
        </div>
        <div class="modal-actions"><button type="button" @click="procModal.open = false">取消</button><button class="primary">保存</button></div>
      </form>
    </div>

    <div v-if="detailItem" class="modal-backdrop">
      <div class="modal-card wide"><h2>采购详情</h2><div class="detail-grid"><div v-for="(v, k) in detailFields" :key="k"><span>{{ k }}</span><strong>{{ v }}</strong></div></div><div class="modal-actions"><button class="primary" @click="detailItem = null">关闭</button></div></div>
    </div>

    <div v-if="showUpload" class="modal-backdrop">
      <form class="modal-card" @submit.prevent="uploadAttachments"><h2>上传附件</h2><select v-model="uploadForm.year"><option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option></select><select v-model="uploadForm.month"><option v-for="m in meta.months" :key="m" :value="m">{{ m }}月</option></select><select v-model="uploadForm.department"><option v-for="d in optionMap.department" :key="d" :value="d">{{ d }}</option></select><input type="file" multiple @change="uploadForm.files = $event.target.files" /><input v-model="uploadForm.description" placeholder="说明" /><div class="modal-actions"><button type="button" @click="showUpload = false">取消</button><button class="primary">上传</button></div></form>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { BarChart3, Download, Edit3, Eye, LayoutList, LogIn, LogOut, Paperclip, Plus, RotateCcw, Save, Search, Settings, Trash2, Upload } from 'lucide-vue-next'

const Pagination = defineComponent({
  props: { page: Number, pages: Number },
  emits: ['change'],
  setup(props, { emit }) {
    const input = ref(props.page || 1)
    const pages = computed(() => Math.max(1, props.pages || 1))
    const visible = computed(() => {
      const set = new Set([1, pages.value, props.page - 1, props.page, props.page + 1].filter(n => n >= 1 && n <= pages.value))
      return [...set].sort((a, b) => a - b)
    })
    const go = page => emit('change', Math.min(Math.max(1, Number(page) || 1), pages.value))
    return () => h('div', { class: 'pager' }, [
      h('button', { disabled: props.page <= 1, onClick: () => go(props.page - 1) }, '上一页'),
      ...visible.value.map(n => h('button', { class: { active: n === props.page }, onClick: () => go(n) }, String(n))),
      h('button', { disabled: props.page >= pages.value, onClick: () => go(props.page + 1) }, '下一页'),
      h('span', '跳至'),
      h('input', { type: 'number', min: 1, max: pages.value, value: input.value, onInput: e => input.value = e.target.value, onKeydown: e => e.key === 'Enter' && go(input.value) }),
      h('button', { onClick: () => go(input.value) }, '跳转'),
    ])
  },
})

const MultiSelect = defineComponent({
  props: {
    label: String,
    options: { type: Array, default: () => [] },
    modelValue: { type: Array, default: () => [] },
  },
  emits: ['update:modelValue', 'change'],
  setup(props, { emit }) {
    const open = ref(false)
    const root = ref(null)
    const selected = value => props.modelValue.includes(value)
    const toggle = value => {
      const next = selected(value)
        ? props.modelValue.filter(item => item !== value)
        : [...props.modelValue, value]
      emit('update:modelValue', next)
      emit('change')
    }
    const clear = () => {
      emit('update:modelValue', [])
      emit('change')
    }
    const labelText = computed(() => {
      if (!props.modelValue.length) return '全部'
      const labels = props.options.filter(item => props.modelValue.includes(item.value)).map(item => item.label)
      return labels.length <= 2 ? labels.join('、') : `已选 ${labels.length} 项`
    })
    const handleBlur = event => {
      if (!event.currentTarget.contains(event.relatedTarget)) open.value = false
    }
    return () => h('div', { ref: root, class: 'multi-filter', tabindex: -1, onFocusout: handleBlur }, [
      h('span', { class: 'field-label' }, props.label),
      h('button', { type: 'button', class: { open: open.value }, onClick: () => open.value = !open.value }, labelText.value),
      open.value && h('div', { class: 'multi-menu' }, [
        h('div', { class: 'multi-menu-actions' }, [
          h('button', { type: 'button', onClick: clear }, '清空'),
          h('button', {
            type: 'button',
            onClick: () => {
              emit('update:modelValue', props.options.map(item => item.value))
              emit('change')
            },
          }, '全选'),
        ]),
        ...props.options.map(item => h('label', { class: 'check-row' }, [
          h('input', { type: 'checkbox', checked: selected(item.value), onChange: () => toggle(item.value) }),
          h('span', item.label),
        ])),
      ]),
    ])
  },
})

const navItems = [
  { key: 'procurements', label: '采购列表', title: '采购列表', eyebrow: 'Procurement', icon: LayoutList },
  { key: 'attachments', label: '附件管理', title: '附件管理', eyebrow: 'Attachments', icon: Paperclip },
  { key: 'reports', label: '透视报表', title: '透视报表', eyebrow: 'Reports', icon: BarChart3 },
  { key: 'settings', label: '系统设置', title: '系统设置', eyebrow: 'Settings', icon: Settings },
]

const page = ref('procurements')
const currentNav = computed(() => navItems.find(item => item.key === page.value) || navItems[0])
const admin = reactive({ is_admin: false, is_root: false, username: '' })
const showLogin = ref(false)
const loginForm = reactive({ username: 'admin', password: '' })
const toast = ref(null)
let toastTimer = null
let reportReloadTimer = null

const optionMap = reactive({ asset_category: [], department: [], status: [] })
const meta = reactive({ years: [], months: Array.from({ length: 12 }, (_, i) => i + 1) })
const yearOptions = computed(() => meta.years.length ? meta.years : Array.from({ length: new Date().getFullYear() - 2021 }, (_, i) => new Date().getFullYear() - i))

const proc = reactive({
  items: [], page: 1, per_page: 20, pages: 1, total: 0,
  filters: { year: [String(new Date().getFullYear())], month: [], department: [], status: [], keyword: '' },
  summary: { total_count: 0, total_amount: 0, pending_count: 0, pending_amount: 0 },
})
const procModal = reactive({ open: false, id: null })
const procForm = reactive({})
const detailItem = ref(null)

const attachment = reactive({ filters: { year: new Date().getFullYear(), month: new Date().getMonth() + 1 }, coverage: { items: [] }, groups: [] })
const showUpload = ref(false)
const uploadForm = reactive({ year: new Date().getFullYear(), month: new Date().getMonth() + 1, department: '', files: null, description: '' })

const report = reactive({
  filters: { year: new Date().getFullYear(), month: [], department: [], asset_category: [] },
  overview: {},
  summary: [],
  ratio: [],
  category: [],
  trend: [],
  matrix: { categories: [], rows: [] },
})
const trendChart = ref(null)
const ratioChart = ref(null)
const categoryChart = ref(null)
let trendInstance = null
let ratioInstance = null
let categoryInstance = null

const settings = reactive({ category: 'asset_category', options: [], newOption: '' })
const passwordForm = reactive({ old_password: '', new_password: '' })
const newAdmin = reactive({ username: '', password: '' })
const adminUsers = ref([])
const importFile = ref(null)
const importResult = ref('')

const coveragePercent = computed(() => attachment.coverage.total_departments ? Math.round(attachment.coverage.uploaded_departments / attachment.coverage.total_departments * 100) : 0)
const attachmentFileCount = computed(() => attachment.groups.reduce((sum, group) => sum + Number(group.count || 0), 0))
const detailFields = computed(() => detailItem.value ? {
  '采购期间': `${detailItem.value.year}年${detailItem.value.month}月`,
  '资产分类': detailItem.value.asset_category,
  '物品名称': detailItem.value.item_name,
  '需求部门': detailItem.value.department,
  '需求人': `${detailItem.value.requester_name} / ${detailItem.value.requester_id}`,
  '总金额': money(detailItem.value.total_price),
  '采购状态': detailItem.value.status,
  '申请原因': detailItem.value.reason,
  '备注': detailItem.value.remark || '-',
} : {})

onMounted(async () => {
  await Promise.all([checkAdmin(), loadMetadata(), loadAllOptions()])
  uploadForm.department = optionMap.department[0] || ''
  window.addEventListener('resize', resizeCharts)
  await loadProcurementPage()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  disposeCharts()
})

function notify(message, type = 'info') {
  toast.value = { message, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => toast.value = null, 2800)
}

async function request(url, options = {}) {
  const res = await fetch(url, options)
  const text = await res.text()
  const data = text ? JSON.parse(text) : {}
  if (!res.ok) throw new Error(data.msg || data.message || '请求失败')
  return data
}

function money(value) {
  return `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function size(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

function fileExt(filename) {
  const parts = String(filename || '').split('.')
  return parts.length > 1 ? parts.pop().slice(0, 4).toUpperCase() : 'FILE'
}

function statusClass(status) {
  if (status === '已完成') return 'done'
  if (status === '采购中') return 'progress'
  return 'pending'
}

async function checkAdmin() {
  const data = await request('/admin/check')
  Object.assign(admin, data)
}

async function login() {
  try {
    const data = await request('/admin/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(loginForm) })
    Object.assign(admin, { is_admin: true, username: data.username, is_root: data.is_root })
    showLogin.value = false
    notify('登录成功', 'success')
    if (page.value === 'settings') await loadSettingsPage()
  } catch (error) { notify(error.message, 'danger') }
}

async function logout() {
  await request('/admin/logout', { method: 'POST' })
  Object.assign(admin, { is_admin: false, username: '', is_root: false })
  notify('已退出管理模式')
}

async function loadMetadata() {
  const data = await request('/api/procurements/filter-metadata')
  meta.years = data.years
  meta.months = data.months
}

async function loadAllOptions() {
  for (const category of ['asset_category', 'department', 'status']) {
    const data = await request(`/api/options/${category}`)
    optionMap[category] = data.map(item => item.value)
  }
}

function paramsFromFilters(filters) {
  const params = new URLSearchParams()
  for (const key of ['year', 'month', 'department', 'status']) {
    for (const value of filters[key] || []) params.append(key, value)
  }
  if (filters.keyword) params.set('keyword', filters.keyword)
  return params
}

async function loadProcurementPage() {
  await Promise.all([loadProcurements(1), loadProcSummary()])
}

async function reloadProcurements() {
  await loadProcurementPage()
}

async function loadProcurements(nextPage = proc.page) {
  proc.page = nextPage
  const params = paramsFromFilters(proc.filters)
  params.set('page', proc.page)
  params.set('per_page', proc.per_page)
  const data = await request(`/api/procurements?${params}`)
  Object.assign(proc, { items: data.items, total: data.total, page: data.page, pages: data.pages })
}

async function loadProcSummary() {
  const data = await request(`/api/procurements/summary?${paramsFromFilters(proc.filters)}`)
  proc.summary = data
}

function resetProcFilters() {
  Object.assign(proc.filters, { year: [], month: [], department: [], status: [], keyword: '' })
  reloadProcurements()
}

function emptyProcForm() {
  return {
    year: new Date().getFullYear(), month: new Date().getMonth() + 1,
    asset_category: optionMap.asset_category[0] || '', item_name: '', manufacturer: '', model: '',
    budget_qty: 1, unit_price: 0, department: optionMap.department[0] || '', requester_name: '', requester_id: '',
    asset_code: '', reason: '', remark: '', status: optionMap.status[0] || '已申请',
  }
}

async function openProcForm(id = null) {
  procModal.id = id
  Object.assign(procForm, id ? await request(`/api/procurements/${id}`) : emptyProcForm())
  procModal.open = true
}

async function saveProc() {
  try {
    const url = procModal.id ? `/api/procurements/${procModal.id}` : '/api/procurements'
    const method = procModal.id ? 'PUT' : 'POST'
    await request(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(procForm) })
    procModal.open = false
    notify('采购记录已保存', 'success')
    await reloadProcurements()
  } catch (error) { notify(error.message, 'danger') }
}

async function quickUpdateProc(row, updates) {
  try {
    const updated = await request(`/api/procurements/${row.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updates) })
    Object.assign(row, updated)
    await loadProcSummary()
  } catch (error) { notify(error.message, 'danger') }
}

function sanitizeIntegerInput(event) {
  event.target.value = event.target.value.replace(/\D/g, '')
}

function sanitizeDecimalInput(event) {
  let value = event.target.value.replace(/[^\d.]/g, '')
  const firstDot = value.indexOf('.')
  if (firstDot !== -1) {
    value = value.slice(0, firstDot + 1) + value.slice(firstDot + 1).replace(/\./g, '')
  }
  event.target.value = value
}

async function inlineUpdateProc(row, field, rawValue) {
  let value = String(rawValue ?? '').trim()
  if (field === 'budget_qty') {
    value = Number(value)
    if (!Number.isInteger(value) || value <= 0) {
      notify('数量必须是大于 0 的整数', 'warning')
      await loadProcurements(proc.page)
      return
    }
  }
  if (field === 'unit_price') {
    value = Number(value)
    if (Number.isNaN(value) || value < 0) {
      notify('单价必须是大于等于 0 的数字', 'warning')
      await loadProcurements(proc.page)
      return
    }
  }
  if (field === 'reason' && !value) {
    notify('申请原因不能为空', 'warning')
    await loadProcurements(proc.page)
    return
  }
  if (row[field] === value) return
  try {
    const updated = await request(`/api/procurements/${row.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [field]: value }),
    })
    Object.assign(row, updated)
    await loadProcSummary()
  } catch (error) {
    notify(error.message, 'danger')
    await loadProcurements(proc.page)
  }
}

async function openProcDetail(id) {
  detailItem.value = await request(`/api/procurements/${id}`)
}

async function deleteProc(id) {
  if (!confirm('确定删除该采购记录？')) return
  await request(`/api/procurements/${id}`, { method: 'DELETE' })
  notify('采购记录已删除', 'success')
  await reloadProcurements()
}

async function loadAttachmentPage() {
  await Promise.all([loadCoverage(), loadAttachments()])
}

async function reloadAttachments() {
  await loadAttachmentPage()
}

async function loadCoverage() {
  const { year, month } = attachment.filters
  attachment.coverage = await request(`/api/attachments/coverage?year=${year}&month=${month}`)
}

async function loadAttachments() {
  const params = new URLSearchParams()
  if (attachment.filters.year) params.set('year', attachment.filters.year)
  if (attachment.filters.month) params.set('month', attachment.filters.month)
  attachment.groups = await request(`/api/attachments?${params}`)
}

async function uploadAttachments() {
  try {
    const files = Array.from(uploadForm.files || [])
    if (!files.length) return notify('请选择文件', 'warning')
    for (const file of files) {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('year', uploadForm.year)
      fd.append('month', uploadForm.month)
      fd.append('department', uploadForm.department)
      if (uploadForm.description) fd.append('description', uploadForm.description)
      const res = await fetch('/api/attachments/upload', { method: 'POST', body: fd })
      if (!res.ok) throw new Error((await res.json()).msg || '上传失败')
    }
    showUpload.value = false
    notify('附件上传完成', 'success')
    await reloadAttachments()
  } catch (error) { notify(error.message, 'danger') }
}

async function deleteAttachment(id) {
  if (!confirm('确定删除该附件？')) return
  await request(`/api/attachments/${id}`, { method: 'DELETE' })
  notify('附件已删除', 'success')
  await reloadAttachments()
}

function reportParams() {
  const params = new URLSearchParams()
  params.set('year', report.filters.year)
  for (const key of ['month', 'department', 'asset_category']) {
    for (const value of report.filters[key] || []) params.append(key, value)
  }
  return params.toString()
}

async function loadReports() {
  clearTimeout(reportReloadTimer)
  const params = reportParams()
  const [overview, summary, ratio, category, trend, matrix] = await Promise.all([
    request(`/api/reports/overview?${params}`),
    request(`/api/reports/department-summary?${params}`),
    request(`/api/reports/department-ratio?${params}`),
    request(`/api/reports/category-distribution?${params}`),
    request(`/api/reports/monthly-trend?${params}`),
    request(`/api/reports/department-category-matrix?${params}`),
  ])
  Object.assign(report, { overview, summary, ratio, category, trend, matrix })
  await nextTick()
  scheduleRenderCharts()
}

function reloadReports() {
  clearTimeout(reportReloadTimer)
  reportReloadTimer = setTimeout(() => {
    if (page.value === 'reports') loadReports()
  }, 120)
}

function resetReportFilters() {
  clearTimeout(reportReloadTimer)
  Object.assign(report.filters, { year: new Date().getFullYear(), month: [], department: [], asset_category: [] })
  loadReports()
}

function matrixCell(row, category) {
  return row.cells?.[category] || { count: 0, total_qty: 0, total_amount: 0 }
}

const matrixMaxAmount = computed(() => {
  const amounts = report.matrix.rows.flatMap(row => report.matrix.categories.map(category => matrixCell(row, category).total_amount))
  return Math.max(0, ...amounts)
})

function matrixHeatStyle(amount) {
  if (!amount || !matrixMaxAmount.value) return {}
  const alpha = Math.min(0.24, 0.05 + (amount / matrixMaxAmount.value) * 0.19)
  return { background: `rgba(15, 108, 120, ${alpha})` }
}

function chartTextStyle() {
  return { color: '#657386', fontFamily: '"Avenir Next", "PingFang SC", "Microsoft YaHei", sans-serif' }
}

function emptyChartGraphic(show) {
  return show ? {
    type: 'text',
    left: 'center',
    top: 'middle',
    style: { text: '暂无图表数据', fill: '#8b98a8', fontSize: 14 },
  } : null
}

function renderCharts() {
  const textStyle = chartTextStyle()
  const trendEmpty = !report.trend.some(item => Number(item.total_amount || 0) || Number(item.pending_amount || 0) || Number(item.count || 0))
  const ratioData = report.category.map(item => ({ name: item.category || '未分类', value: item.total_amount || 0, count: item.count || 0 }))
  const rankData = report.ratio.slice(0, 12)
  const ratioEmpty = !ratioData.some(item => Number(item.value || 0))
  const categoryEmpty = !rankData.length
  if (trendChart.value) {
    trendInstance = ensureChartInstance(trendInstance, trendChart.value)
    trendInstance.setOption({
      color: ['#0f6c78', '#d58a13', '#687386'],
      graphic: emptyChartGraphic(trendEmpty),
      grid: { left: 54, right: 28, top: 58, bottom: 38 },
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          const rows = params.map(item => {
            const value = item.seriesName === '记录数' ? `${item.value} 条` : money(item.value)
            return `${item.marker}${item.seriesName}：${value}`
          })
          return [`${params[0]?.axisValue || ''}`, ...rows].join('<br/>')
        },
      },
      legend: { top: 14, right: 20, textStyle, data: ['采购金额', '待跟进金额', '记录数'] },
      xAxis: { type: 'category', boundaryGap: false, axisTick: { show: false }, axisLabel: textStyle, data: report.trend.map(item => `${item.month}月`) },
      yAxis: [
        { type: 'value', name: '金额', axisLabel: { formatter: value => `${Math.round(value / 10000)}万`, ...textStyle }, splitLine: { lineStyle: { color: '#e8eef5' } } },
        { type: 'value', name: '记录数', axisLabel: textStyle, splitLine: { show: false } },
      ],
      series: [
        { name: '采购金额', type: 'line', smooth: true, symbolSize: 7, areaStyle: { opacity: 0.08 }, data: report.trend.map(item => item.total_amount) },
        { name: '待跟进金额', type: 'line', smooth: true, symbolSize: 7, data: report.trend.map(item => item.pending_amount) },
        { name: '记录数', type: 'bar', yAxisIndex: 1, barWidth: 16, itemStyle: { borderRadius: [4, 4, 0, 0] }, data: report.trend.map(item => item.count) },
      ],
    }, true)
  }
  if (ratioChart.value) {
    ratioInstance = ensureChartInstance(ratioInstance, ratioChart.value)
    ratioInstance.setOption({
      color: ['#0f6c78', '#23856c', '#d58a13', '#687386', '#3f7fb5', '#b45b6a', '#7c6aa8'],
      graphic: emptyChartGraphic(ratioEmpty),
      tooltip: {
        trigger: 'item',
        formatter: item => `${item.marker}${item.name}<br/>金额：${money(item.value)}<br/>占比：${item.percent}%<br/>条数：${item.data.count} 条`,
      },
      legend: { type: 'scroll', bottom: 4, textStyle },
      series: [{
        name: '采购种类',
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        label: { formatter: '{b}\n{d}%', color: '#172331' },
        data: ratioData,
      }],
    }, true)
  }
  if (categoryChart.value) {
    categoryInstance = ensureChartInstance(categoryInstance, categoryChart.value)
    categoryInstance.setOption({
      color: ['#0f6c78'],
      graphic: emptyChartGraphic(categoryEmpty),
      grid: { left: 86, right: 34, top: 26, bottom: 34 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: value => money(value) },
      xAxis: { type: 'value', axisLabel: { formatter: value => `${Math.round(value / 10000)}万`, ...textStyle }, splitLine: { lineStyle: { color: '#e8eef5' } } },
      yAxis: { type: 'category', inverse: true, axisTick: { show: false }, axisLabel: textStyle, data: rankData.map(item => item.name || '未填写部门') },
      series: [
        { name: '采购金额', type: 'bar', barWidth: 16, itemStyle: { borderRadius: [0, 4, 4, 0] }, data: rankData.map(item => item.value) },
      ],
    }, true)
  }
}

function ensureChartInstance(instance, element) {
  if (instance && instance.getDom() !== element) {
    instance.dispose()
    instance = null
  }
  return instance || echarts.init(element)
}

function scheduleRenderCharts() {
  requestAnimationFrame(() => {
    renderCharts()
    requestAnimationFrame(resizeCharts)
  })
}

function resizeCharts() {
  trendInstance?.resize()
  ratioInstance?.resize()
  categoryInstance?.resize()
}

function disposeCharts() {
  trendInstance?.dispose()
  ratioInstance?.dispose()
  categoryInstance?.dispose()
  trendInstance = null
  ratioInstance = null
  categoryInstance = null
}

function exportReport(type) {
  window.location.href = `/api/reports/export?type=${type}&${reportParams()}`
}

async function loadSettingsPage() {
  await loadOptionsByCategory()
  if (admin.is_root) await loadAdminUsers()
}

async function loadOptionsByCategory() {
  settings.options = await request(`/api/options/${settings.category}`)
}

async function addOption() {
  if (!settings.newOption.trim()) return
  await request('/api/options', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category: settings.category, value: settings.newOption.trim() }) })
  settings.newOption = ''
  await loadOptionsByCategory()
}

async function saveOption(option) {
  await request(`/api/options/${option.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value: option.value, sort_order: option.sort_order }) })
  notify('选项已保存', 'success')
}

async function deleteOption(id) {
  if (!confirm('确定删除该选项？')) return
  await request(`/api/options/${id}`, { method: 'DELETE' })
  await loadOptionsByCategory()
}

async function changePassword() {
  await request('/api/admin/change-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(passwordForm) })
  Object.assign(passwordForm, { old_password: '', new_password: '' })
  notify('密码已修改', 'success')
}

async function loadAdminUsers() {
  adminUsers.value = await request('/api/admin/users')
}

async function createAdmin() {
  await request('/api/admin/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newAdmin) })
  Object.assign(newAdmin, { username: '', password: '' })
  await loadAdminUsers()
}

async function deleteAdmin(id) {
  if (!confirm('确定删除该管理员？')) return
  await request(`/api/admin/users/${id}`, { method: 'DELETE' })
  await loadAdminUsers()
}

async function importExcel() {
  if (!importFile.value) return notify('请选择文件', 'warning')
  const fd = new FormData()
  fd.append('file', importFile.value)
  const res = await fetch('/api/import/excel', { method: 'POST', body: fd })
  const data = await res.json()
  if (!res.ok) return notify(data.msg || '导入失败', 'danger')
  importResult.value = `成功导入 ${data.imported} 条，错误 ${data.total_errors} 条`
  notify('导入完成', data.total_errors ? 'warning' : 'success')
}

async function setPage(nextPageName) {
  if (page.value === 'reports' && nextPageName !== 'reports') disposeCharts()
  page.value = nextPageName
  if (nextPageName === 'procurements') await loadProcurementPage()
  if (nextPageName === 'attachments') await loadAttachmentPage()
  if (nextPageName === 'reports') await loadReports()
  if (nextPageName === 'settings') await loadSettingsPage()
}
</script>
