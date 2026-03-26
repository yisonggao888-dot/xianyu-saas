<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAccountStore } from '@/stores/account'
import type { Account } from '@/api/account'
import { Plus } from '@element-plus/icons-vue'

const accountStore = useAccountStore()
const dialogVisible = ref(false)
const dialogTitle = ref('添加账号')
const isEdit = ref(false)
const currentId = ref('')

const form = ref({
  name: '',
  cookies: '',
})

const formRef = ref()

const rules = {
  name: [{ required: true, message: '请输入账号名称', trigger: 'blur' }],
  cookies: [{ required: true, message: '请输入Cookie', trigger: 'blur' }],
}

onMounted(() => {
  accountStore.fetchAccounts()
})

const handleAdd = () => {
  dialogTitle.value = '添加账号'
  isEdit.value = false
  currentId.value = ''
  form.value = { name: '', cookies: '' }
  dialogVisible.value = true
}

const handleEdit = (row: Account) => {
  dialogTitle.value = '编辑账号'
  isEdit.value = true
  currentId.value = row.id
  form.value = { name: row.name, cookies: '' }
  dialogVisible.value = true
}

const handleDelete = (row: Account) => {
  ElMessageBox.confirm(
    `确定要删除账号 "${row.name}" 吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    await accountStore.deleteAccount(row.id)
  })
}

const handleToggleStatus = async (row: Account) => {
  const newStatus = row.status === 'active' ? 'paused' : 'active'
  await accountStore.updateAccount(row.id, { status: newStatus })
  ElMessage.success(`${newStatus === 'active' ? '启动' : '暂停'}成功`)
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  if (isEdit.value) {
    await accountStore.updateAccount(currentId.value, form.value)
  } else {
    await accountStore.createAccount(form.value)
  }
  dialogVisible.value = false
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    active: 'success',
    paused: 'info',
    error: 'danger',
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    active: '运行中',
    paused: '已暂停',
    error: '异常',
  }
  return map[status] || status
}
</script>

<template>
  <div class="account-list">
    <div class="page-header">
      <h2>闲鱼账号管理</h2>
      <el-button type="primary" :icon="Plus" @click="handleAdd">添加账号</el-button>
    </div>
    
    <el-table 
      :data="accountStore.accounts" 
      style="width: 100%" 
      border
      v-loading="accountStore.loading"
    >
      <el-table-column prop="name" label="账号名称" width="150" />
      
      <el-table-column prop="xianyu_nickname" label="闲鱼昵称" width="150" />
      
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="last_online_at" label="最后在线" width="180" />
      
      <el-table-column prop="message_count_this_month" label="本月消息" width="100" />
      
      <el-table-column prop="ai_enabled" label="AI客服" width="100">
        <template #default="{ row }">
          <el-switch 
            v-model="row.ai_enabled"
            @change="accountStore.updateAccount(row.id, { ai_enabled: $event })"
          />
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button
            :type="row.status === 'active' ? 'warning' : 'success'"
            size="small"
            @click="handleToggleStatus(row)"
          >
            {{ row.status === 'active' ? '暂停' : '启动' }}
          </el-button>
          <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="账号名称" prop="name" required>
          <el-input v-model="form.name" placeholder="给这个账号起个名字" />
        </el-form-item>
        
        <el-form-item label="Cookie" prop="cookies" :required="!isEdit">
          <el-input
            v-model="form.cookies"
            type="textarea"
            :rows="5"
            :placeholder="isEdit ? '留空表示不修改' : '粘贴闲鱼网页端的Cookie'"
          />
        </el-form-item>
        
        <el-form-item>
          <el-alert
            title="如何获取Cookie？"
            type="info"
            description="登录闲鱼网页版，按F12打开开发者工具，在Application -> Cookies中找到并复制"
            :closable="false"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}
</style>
