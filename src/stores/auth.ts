// author: jf
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  authenticateUser,
  clearStoredAuthSession,
  getPermissionLabels,
  hasPermission,
  loadStoredAuthSession,
  requestPasswordResetEmailCode,
  requestRegistrationEmailCode,
  registerUser,
  resetPasswordWithEmailCode,
  saveStoredAuthSession,
  type AuthSession,
  type AuthUser,
} from '@/services/authService'

export const useAuthStore = defineStore('auth', () => {
  const currentSession = ref<AuthSession | null>(loadStoredAuthSession())
  const currentUser = computed<AuthUser | null>(() => currentSession.value?.user ?? null)

  const isAuthenticated = computed(() => currentUser.value !== null)
  const isAdmin = computed(() => currentUser.value?.role === 'admin')
  const canManageKnowledgeBase = computed(() => hasPermission(currentUser.value, 'knowledge_admin'))
  const permissionLabels = computed(() => getPermissionLabels(currentUser.value))

  async function login(username: string, password: string): Promise<boolean> {
    const session = await authenticateUser(username, password)
    if (!session) return false
    currentSession.value = session
    saveStoredAuthSession(session)
    return true
  }

  async function sendRegistrationEmailCode(email: string) {
    return requestRegistrationEmailCode(email)
  }

  async function sendPasswordResetEmailCode(email: string) {
    return requestPasswordResetEmailCode(email)
  }

  async function resetPassword(email: string, verificationCode: string, newPassword: string): Promise<void> {
    await resetPasswordWithEmailCode(email, verificationCode, newPassword)
  }

  async function register(
    displayName: string,
    email: string,
    verificationCode: string,
    password: string,
  ): Promise<boolean> {
    const session = await registerUser(displayName, email, verificationCode, password)
    currentSession.value = session
    saveStoredAuthSession(session)
    return true
  }

  function logout() {
    currentSession.value = null
    clearStoredAuthSession()
  }

  return {
    currentSession,
    currentUser,
    isAuthenticated,
    isAdmin,
    canManageKnowledgeBase,
    permissionLabels,
    login,
    sendRegistrationEmailCode,
    sendPasswordResetEmailCode,
    resetPassword,
    register,
    logout,
  }
})
