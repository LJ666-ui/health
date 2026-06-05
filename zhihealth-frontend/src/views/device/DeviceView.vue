<template>
  <div class="device-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>设备管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增设备</el-button>
        </div>
      </template>

      <el-form :inline="true" class="search-form">
        <el-form-item label="设备名称">
          <el-input v-model="searchForm.deviceName" placeholder="请输入设备名称" clearable />
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="searchForm.deviceType" placeholder="请选择类型" clearable>
            <el-option label="智能手环" value="smartband" />
            <el-option label="血压计" value="blood_pressure_monitor" />
            <el-option label="体重秤" value="weight_scale" />
            <el-option label="血糖仪" value="glucose_meter" />
            <el-option label="血氧仪" value="pulse_oximeter" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
            <el-option label="维护中" value="maintenance" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="deviceName" label="设备名称" width="150" />
        <el-table-column prop="deviceCode" label="设备编号" width="140" />
        <el-table-column prop="deviceType" label="设备类型" width="120">
          <template #default="{ row }">
            {{ getDeviceTypeName(row.deviceType) }}
          </template>
        </el-table-column>
        <el-table-column prop="userId" label="绑定用户" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastOnlineTime" label="最后在线时间" width="170" />
        <el-table-column prop="batteryLevel" label="电量" width="80">
          <template #default="{ row }">
            <el-progress 
              :percentage="row.batteryLevel || 0" 
              :color="getBatteryColor(row.batteryLevel)"
              :stroke-width="6"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :icon="View" @click="handleView(row)">查看</el-button>
            <el-button type="primary" link :icon="Edit" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.pageNum"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end;"
        @size-change="loadData"
        @current-change="loadData"
      />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="550px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="设备名称" prop="deviceName">
          <el-input v-model="form.deviceName" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="设备编号" prop="deviceCode">
          <el-input v-model="form.deviceCode" placeholder="请输入设备编号" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="设备类型" prop="deviceType">
          <el-select v-model="form.deviceType" placeholder="请选择设备类型">
            <el-option label="智能手环" value="smartband" />
            <el-option label="血压计" value="blood_pressure_monitor" />
            <el-option label="体重秤" value="weight_scale" />
            <el-option label="血糖仪" value="glucose_meter" />
            <el-option label="血氧仪" value="pulse_oximeter" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定用户" prop="userId">
          <el-input-number v-model="form.userId" :min="1" placeholder="请输入用户ID" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="请输入备注信息" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDeviceList, createDevice, updateDevice, deleteDevice } from '@/api/device'

const tableData = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新增设备')
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)

const searchForm = reactive({
  deviceName: '',
  deviceType: '',
  status: ''
})

const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

const form = reactive({
  id: null,
  deviceName: '',
  deviceCode: '',
  deviceType: '',
  userId: null,
  remark: ''
})

const rules = {
  deviceName: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  deviceCode: [{ required: true, message: '请输入设备编号', trigger: 'blur' }],
  deviceType: [{ required: true, message: '请选择设备类型', trigger: 'change' }]
}

function getDeviceTypeName(type) {
  const map = {
    smartband: '智能手环',
    blood_pressure_monitor: '血压计',
    weight_scale: '体重秤',
    glucose_meter: '血糖仪',
    pulse_oximeter: '血氧仪'
  }
  return map[type] || type
}

function getStatusType(status) {
  const map = { online: 'success', offline: 'info', maintenance: 'warning' }
  return map[status] || ''
}

function getStatusName(status) {
  const map = { online: '在线', offline: '离线', maintenance: '维护中' }
  return map[status] || status
}

function getBatteryColor(level) {
  if (level > 60) return '#67c23a'
  if (level > 20) return '#e6a23c'
  return '#f56c6c'
}

async function loadData() {
  try {
    const res = await getDeviceList({ ...searchForm, pageNum: pagination.pageNum, pageSize: pagination.pageSize })
    if (res.code === 200) {
      tableData.value = res.data.records || []
      pagination.total = res.data.total || 0
    }
  } catch (error) {
    console.error('加载设备列表失败:', error)
  }
}

function handleSearch() {
  pagination.pageNum = 1
  loadData()
}

function resetSearch() {
  Object.assign(searchForm, { deviceName: '', deviceType: '', status: '' })
  handleSearch()
}

function handleAdd() {
  isEdit.value = false
  dialogTitle.value = '新增设备'
  Object.assign(form, { id: null, deviceName: '', deviceCode: '', deviceType: '', userId: null, remark: '' })
  dialogVisible.value = true
}

function handleEdit(row) {
  isEdit.value = true
  dialogTitle.value = '编辑设备'
  Object.assign(form, row)
  dialogVisible.value = true
}

function handleView(row) {
  ElMessageBox.alert(
    `<p><strong>设备名称：</strong>${row.deviceName}</p>
         <p><strong>设备编号：</strong>${row.deviceCode}</p>
         <p><strong>设备类型：</strong>${getDeviceTypeName(row.deviceType)}</p>
         <p><strong>绑定用户：</strong>${row.userId || '未绑定'}</p>
         <p><strong>最后在线：</strong>${row.lastOnlineTime || '-'}</p>
         <p><strong>电量：</strong>${row.batteryLevel || 0}%</p>`,
    '设备详情',
    { dangerouslyUseHTMLString: true }
  )
}

async function handleSubmit() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true

      const url = isEdit.value ? '/device/update' : '/device/add'
      const method = isEdit.value ? 'put' : 'post'

      try {
        const res = isEdit.value ? await updateDevice(form.id, form) : await createDevice(form)

        if (res.code === 200) {
          ElMessage.success(isEdit.value ? '更新成功' : '添加成功')
          dialogVisible.value = false
          loadData()
        } else {
          ElMessage.error(res.msg || '操作失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '操作失败')
      }

      submitLoading.value = false
    }
  })
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除设备"${row.deviceName}"吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteDevice(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.device-container {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .search-form {
    margin-bottom: 16px;
  }
}
</style>
