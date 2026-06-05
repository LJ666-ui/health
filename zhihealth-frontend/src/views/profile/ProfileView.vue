<template>
  <div class="profile-container">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover" class="profile-card">
          <div class="profile-header">
            <el-avatar :size="80" icon="UserFilled" />
            <h2>{{ userStore.username }}</h2>
            <el-tag :type="getRoleType(userStore.role)" size="large">{{ getRoleName(userStore.role) }}</el-tag>
          </div>

          <el-descriptions :column="1" border size="small" style="margin-top: 20px;">
            <el-descriptions-item label="用户ID">{{ userStore.userInfo?.id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ userStore.userInfo?.phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ userStore.userInfo?.email || '-' }}</el-descriptions-item>
            <el-descriptions-item label="注册时间">{{ userStore.userInfo?.createTime || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="基本信息" name="basic">
            <el-form 
              ref="profileFormRef"
              :model="profileForm" 
              :rules="rules"
              label-width="100px"
              style="max-width: 500px;"
            >
              <el-form-item label="真实姓名" prop="realName">
                <el-input v-model="profileForm.realName" placeholder="请输入真实姓名" />
              </el-form-item>

              <el-form-item label="手机号" prop="phone">
                <el-input v-model="profileForm.phone" placeholder="请输入手机号" />
              </el-form-item>

              <el-form-item label="邮箱" prop="email">
                <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
              </el-form-item>

              <el-form-item label="性别" prop="gender">
                <el-radio-group v-model="profileForm.gender">
                  <el-radio value="male">男</el-radio>
                  <el-radio value="female">女</el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="出生日期" prop="birthday">
                <el-date-picker
                  v-model="profileForm.birthday"
                  type="date"
                  placeholder="选择出生日期"
                  value-format="YYYY-MM-DD"
                  style="width: 100%;"
                />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" :loading="saveLoading" @click="handleSaveProfile">
                  保存修改
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="修改密码" name="password">
            <el-form 
              ref="passwordFormRef"
              :model="passwordForm" 
              :rules="passwordRules"
              label-width="100px"
              style="max-width: 500px;"
            >
              <el-form-item label="当前密码" prop="oldPassword">
                <el-input v-model="passwordForm.oldPassword" type="password" show-password />
              </el-form-item>

              <el-form-item label="新密码" prop="newPassword">
                <el-input v-model="passwordForm.newPassword" type="password" show-password />
              </el-form-item>

              <el-form-item label="确认密码" prop="confirmPassword">
                <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" :loading="changeLoading" @click="handleChangePassword">
                  修改密码
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="通知设置" name="notification">
            <div class="notification-settings">
              <div class="setting-item">
                <div class="setting-info">
                  <h4>邮件通知</h4>
                  <p>接收预警、系统消息等邮件通知</p>
                </div>
                <el-switch v-model="notificationSettings.email" />
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <h4>短信通知</h4>
                  <p>接收紧急预警短信提醒</p>
                </div>
                <el-switch v-model="notificationSettings.sms" />
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <h4>站内信通知</h4>
                  <p>接收系统公告和活动推送</p>
                </div>
                <el-switch v-model="notificationSettings.system" />
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <h4>微信通知</h4>
                  <p>通过微信服务号接收通知</p>
                </div>
                <el-switch v-model="notificationSettings.wechat" />
              </div>

              <el-button type="primary" @click="handleSaveNotification" style="margin-top: 20px;">
                保存设置
              </el-button>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { getUserInfo, updateUser, changePassword } from '@/api/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const activeTab = ref('basic')
const profileFormRef = ref(null)
const passwordFormRef = ref(null)
const saveLoading = ref(false)
const changeLoading = ref(false)

const profileForm = reactive({
  realName: '',
  phone: '',
  email: '',
  gender: '',
  birthday: ''
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const notificationSettings = reactive({
  email: true,
  sms: true,
  system: true,
  wechat: false
})

const rules = {
  realName: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }],
  email: [{ type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }]
}

const passwordRules = {
  oldPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

function getRoleType(role) {
  const map = { admin: 'danger', doctor: 'warning', user: '' }
  return map[role] || ''
}

function getRoleName(role) {
  const map = { admin: '管理员', doctor: '医生', user: '普通用户' }
  return map[role] || role
}

async function handleSaveProfile() {
  if (!profileFormRef.value) return

  await profileFormRef.value.validate(async (valid) => {
    if (valid) {
      saveLoading.value = true
      
      try {
        const res = await api.put('/user/profile', profileForm)
        
        if (res.code === 200) {
          ElMessage.success('个人信息更新成功')
          Object.assign(userStore.userInfo, profileForm)
        } else {
          ElMessage.error(res.msg || '更新失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '更新失败')
      }

      saveLoading.value = false
    }
  })
}

async function handleChangePassword() {
  if (!passwordFormRef.value) return

  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      changeLoading.value = true
      
      try {
        const res = await changePassword({
          oldPassword: passwordForm.oldPassword,
          newPassword: passwordForm.newPassword
        })

        if (res.code === 200) {
          ElMessage.success('密码修改成功')
          Object.assign(passwordForm, { oldPassword: '', newPassword: '', confirmPassword: '' })
        } else {
          ElMessage.error(res.msg || '密码修改失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '密码修改失败')
      }

      changeLoading.value = false
    }
  })
}

function handleSaveNotification() {
  ElMessage.success('通知设置已保存')
}

onMounted(() => {
  if (userStore.userInfo) {
    Object.assign(profileForm, {
      realName: userStore.userInfo.realName || '',
      phone: userStore.userInfo.phone || '',
      email: userStore.userInfo.email || '',
      gender: userStore.userInfo.gender || '',
      birthday: userStore.userInfo.birthday || ''
    })
  }
})
</script>

<style lang="scss" scoped>
.profile-container {
  .profile-card {
    .profile-header {
      text-align: center;
      padding: 20px 0;

      h2 {
        margin: 16px 0 12px;
        font-size: 22px;
      }
    }
  }

  .notification-settings {
    .setting-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 0;
      border-bottom: 1px solid #ebeef5;

      &:last-child {
        border-bottom: none;
      }

      .setting-info {
        h4 {
          font-size: 15px;
          margin-bottom: 4px;
        }

        p {
          font-size: 13px;
          color: #999;
        }
      }
    }
  }
}
</style>
