import { defineStore } from 'pinia'
import { ref } from 'vue'
import { accountApi } from '@/api/account'
import type { Account, AccountCreateData, AccountUpdateData } from '@/api/account'
import { ElMessage } from 'element-plus'

export const useAccountStore = defineStore('account', () => {
  // State
  const accounts = ref<Account[]>([])
  const loading = ref(false)
  const currentAccount = ref<Account | null>(null)

  // Actions
  const fetchAccounts = async () => {
    loading.value = true
    try {
      const data = await accountApi.getList()
      accounts.value = data
      return data
    } catch (error) {
      return []
    } finally {
      loading.value = false
    }
  }

  const createAccount = async (data: AccountCreateData) => {
    try {
      const result = await accountApi.create(data)
      ElMessage.success('创建成功')
      await fetchAccounts()
      return result
    } catch (error) {
      return null
    }
  }

  const updateAccount = async (id: string, data: AccountUpdateData) => {
    try {
      const result = await accountApi.update(id, data)
      ElMessage.success('更新成功')
      await fetchAccounts()
      return result
    } catch (error) {
      return null
    }
  }

  const deleteAccount = async (id: string) => {
    try {
      await accountApi.delete(id)
      ElMessage.success('删除成功')
      await fetchAccounts()
      return true
    } catch (error) {
      return false
    }
  }

  return {
    accounts,
    loading,
    currentAccount,
    fetchAccounts,
    createAccount,
    updateAccount,
    deleteAccount,
  }
})
