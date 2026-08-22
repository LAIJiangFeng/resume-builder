<!-- author: jf -->
<script setup lang="ts">
import type { AuthUser } from '@/services/authService'

type ThemeMode = 'light' | 'porcelain-jade' | 'dark'

const props = defineProps<{
  themeMode: ThemeMode
  currentUser: AuthUser | null
}>()

const emit = defineEmits<{
  (e: 'set-theme', mode: ThemeMode): void
  (e: 'logout'): void
}>()

const themeOptions: Array<{ mode: ThemeMode; label: string }> = [
  { mode: 'light', label: '浅色' },
  { mode: 'porcelain-jade', label: '青瓷' },
  { mode: 'dark', label: '曜石' },
]

function selectTheme(mode: ThemeMode) {
  if (props.themeMode === mode) return
  emit('set-theme', mode)
}
</script>

<template>
  <main class="account-settings-panel">
    <section class="account-shell" data-account-settings="ready">
      <section v-if="props.currentUser" class="profile-card" aria-labelledby="profile-name">
        <span class="profile-avatar" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />
            <path d="M4 21a8 8 0 0 1 16 0" />
          </svg>
        </span>
        <div class="profile-copy">
          <div class="profile-name-row">
            <h1 id="profile-name">{{ props.currentUser.displayName }}</h1>
            <span class="role-badge">{{ props.currentUser.role === 'admin' ? '管理员' : '用户' }}</span>
          </div>
          <p>{{ props.currentUser.username }}</p>
        </div>
      </section>

      <section class="settings-list" aria-label="账户设置">
        <div class="setting-row">
          <span class="setting-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 3v2m0 14v2M5 5l1.4 1.4M17.6 17.6 19 19M3 12h2m14 0h2M5 19l1.4-1.4M17.6 6.4 19 5" />
              <circle cx="12" cy="12" r="4" />
            </svg>
          </span>
          <strong>外观</strong>
          <div class="theme-toggle-group" role="radiogroup" aria-label="主题模式">
            <button
              v-for="option in themeOptions"
              :key="option.mode"
              class="theme-toggle-option"
              :class="{ active: props.themeMode === option.mode }"
              type="button"
              role="radio"
              :aria-checked="props.themeMode === option.mode"
              @click="selectTheme(option.mode)"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <div class="setting-divider" aria-hidden="true" />

        <div class="setting-row logout-row">
          <span class="setting-icon danger" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5" />
              <path d="m16 16 4-4-4-4M20 12H9" />
            </svg>
          </span>
          <strong>退出登录</strong>
          <button class="logout-btn" type="button" @click="emit('logout')">退出</button>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.account-settings-panel,
.account-settings-panel * {
  box-sizing: border-box;
}

.account-settings-panel {
  flex: 1;
  width: 100%;
  min-width: 0;
  height: 100%;
  overflow: auto;
  padding: clamp(28px, 5vh, 56px) 20px 80px;
  background: var(--app-background);
  color: var(--text-primary);
  font-family: var(--font-sans);
}

.account-shell {
  width: 100%;
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.account-shell:not(:has(.profile-card))::before {
  content: '账户信息加载中';
  min-height: 96px;
  padding: 24px;
  border: 1px solid var(--border-color);
  border-radius: 22px;
  background: var(--surface-raised);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
}

.profile-card {
  min-height: 144px;
  padding: 26px 28px;
  border: 1px solid var(--border-color);
  border-radius: 26px;
  background: var(--surface-raised);
  box-shadow: var(--shadow-lg);
  display: flex;
  align-items: center;
  gap: 18px;
}

.profile-avatar {
  width: 68px;
  height: 68px;
  flex: 0 0 auto;
  border-radius: 22px;
  background: var(--primary-500);
  color: var(--text-inverse);
  box-shadow: var(--shadow-brand);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.profile-avatar svg {
  width: 30px;
  height: 30px;
}

.profile-avatar path,
.setting-icon path,
.setting-icon circle {
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.profile-copy {
  min-width: 0;
}

.profile-name-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.profile-name-row h1 {
  margin: 0;
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.role-badge {
  min-height: 26px;
  padding: 0 9px;
  border: 1px solid var(--primary-100);
  border-radius: 999px;
  background: var(--primary-50);
  color: var(--primary-600);
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.profile-copy p {
  margin: 7px 0 0;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-list {
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 24px;
  background: var(--surface-raised);
  box-shadow: var(--shadow-md);
}

.setting-row {
  min-height: 82px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
}

.setting-row > strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 650;
}

.setting-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: var(--primary-50);
  color: var(--primary-600);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.setting-icon.danger {
  background: var(--accent-red-soft);
  color: var(--accent-red);
}

.setting-icon svg {
  width: 20px;
  height: 20px;
}

.setting-divider {
  height: 1px;
  margin-left: 76px;
  background: var(--gray-100);
}

.theme-toggle-group {
  width: 288px;
  padding: 4px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: var(--gray-50);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
}

.theme-toggle-option {
  height: 36px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.theme-toggle-option:hover,
.theme-toggle-option:focus-visible {
  color: var(--text-primary);
  outline: none;
}

.theme-toggle-option.active {
  background: var(--primary-500);
  color: var(--text-inverse);
  box-shadow: var(--shadow-brand);
}

.logout-btn {
  min-width: 104px;
  height: 38px;
  padding: 0 15px;
  border: 1px solid var(--border-danger);
  border-radius: 11px;
  background: var(--surface-base);
  color: var(--accent-red-strong);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.logout-btn:hover,
.logout-btn:focus-visible {
  border-color: var(--border-danger-hover);
  background: var(--accent-red-soft);
  box-shadow: var(--shadow-danger);
  outline: none;
}

@media (max-width: 760px) {
  .account-settings-panel {
    padding: 16px 12px calc(92px + env(safe-area-inset-bottom));
    background: var(--app-background);
  }

  .account-shell {
    gap: 12px;
  }

  .profile-card {
    min-height: 112px;
    padding: 20px;
    border-radius: 22px;
  }

  .profile-avatar {
    width: 56px;
    height: 56px;
    border-radius: 18px;
  }

  .profile-avatar svg {
    width: 25px;
    height: 25px;
  }

  .profile-name-row h1 {
    font-size: 20px;
  }

  .settings-list {
    border-radius: 20px;
  }

  .setting-row {
    min-height: 74px;
    grid-template-columns: 40px minmax(0, 1fr) auto;
    gap: 11px;
    padding: 14px;
  }

  .setting-icon {
    width: 40px;
    height: 40px;
    border-radius: 13px;
  }

  .setting-divider {
    margin-left: 65px;
  }

  .theme-toggle-group {
    width: min(170px, 48vw);
  }

  .logout-btn {
    min-width: 88px;
  }
}

@media (max-width: 390px) {
  .settings-list .setting-row:first-child {
    grid-template-columns: 40px minmax(0, 1fr);
  }

  .settings-list .setting-row:first-child .theme-toggle-group {
    grid-column: 2;
    width: 100%;
  }
}
</style>
