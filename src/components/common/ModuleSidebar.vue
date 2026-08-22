<!-- author: jf -->
<script setup lang="ts">
import { computed } from 'vue'
import { resolvePrimaryMenuPath, type PrimaryMenuKey } from '@/router/menuRoutes'

const props = withDefaults(
  defineProps<{
    collapsed?: boolean
    activeMenu?: PrimaryMenuKey
    canManageKnowledgeBase?: boolean
  }>(),
  {
    collapsed: false,
    activeMenu: 'resume-editor',
    canManageKnowledgeBase: false,
  }
)

const emit = defineEmits<{
  (e: 'toggle-collapse'): void
  (e: 'select-menu', key: PrimaryMenuKey): void
}>()

const primaryMenus: Array<{ key: PrimaryMenuKey; label: string; path: string; iconPath: string }> = [
  {
    key: 'resume-editor',
    label: '简历编辑',
    path: resolvePrimaryMenuPath('resume-editor'),
    iconPath:
      'M15 3H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8Zm0 0v5h5M9 13h6M9 17h4',
  },
  {
    key: 'ai-interviewer',
    label: 'AI 面试',
    path: resolvePrimaryMenuPath('ai-interviewer'),
    iconPath:
      'M9 3h6M12 3v3m-6 4h12a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-3l-3 2-3-2H6a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2Zm3 3h.01M15 15h.01',
  },
  {
    key: 'knowledge-base',
    label: '知识库',
    path: resolvePrimaryMenuPath('knowledge-base'),
    iconPath:
      'M6 5.5A2.5 2.5 0 0 1 8.5 3H18v15.5A2.5 2.5 0 0 0 15.5 16H6Zm0 0v11A2.5 2.5 0 0 0 8.5 19H18M10 7h4M10 10h4M10 13h3',
  },
  {
    key: 'account-settings',
    label: '账号设置',
    path: resolvePrimaryMenuPath('account-settings'),
    iconPath: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4 21a8 8 0 0 1 16 0',
  },
]

const visiblePrimaryMenus = computed(() =>
  primaryMenus.filter((menu) => menu.key !== 'knowledge-base' || props.canManageKnowledgeBase)
)
const mobileMenuStyle = computed(() => ({
  '--visible-menu-count': String(visiblePrimaryMenus.value.length),
}))

function handleMenuClick(event: MouseEvent, key: PrimaryMenuKey) {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  emit('select-menu', key)
}
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: props.collapsed }">
    <div class="brand">
      <div class="brand-left">
        <span class="brand-logo-wrap" aria-hidden="true">
          <img class="brand-logo" src="/favicon.svg?v=modern-blue" alt="" />
        </span>
        <span class="brand-text">Resume Builder</span>
      </div>
      <div class="brand-actions">
        <button
          class="collapse-btn"
          type="button"
          :aria-label="props.collapsed ? '展开侧边菜单' : '收起侧边菜单'"
          :title="props.collapsed ? '展开' : '收缩'"
          :data-tip="props.collapsed ? '展开' : '收缩'"
          @click="emit('toggle-collapse')"
        >
          {{ props.collapsed ? '>' : '<' }}
        </button>
      </div>
    </div>

    <ul class="primary-menu-list" :style="mobileMenuStyle">
      <li v-for="menu in visiblePrimaryMenus" :key="menu.key" class="primary-menu-item">
        <a
          class="primary-menu-btn"
          :href="menu.path"
          :class="{ active: props.activeMenu === menu.key }"
          :aria-current="props.activeMenu === menu.key ? 'page' : undefined"
          :title="menu.label"
          @click="handleMenuClick($event, menu.key)"
        >
          <span class="menu-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path :d="menu.iconPath" />
            </svg>
          </span>
          <span class="menu-label">{{ menu.label }}</span>
        </a>
      </li>
    </ul>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 70px;
  min-width: 70px;
  background: var(--sidebar-background);
  padding: 18px 10px;
  display: flex;
  flex-direction: column;
  gap: 34px;
  border-right: 1px solid var(--sidebar-border);
  overflow-y: auto;
  box-shadow: inset -1px 0 0 var(--sidebar-inset);
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding: 0;
}

.brand-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.brand-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.brand-logo-wrap {
  width: 40px;
  height: 40px;
  border-radius: 15px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
  background: var(--surface-base);
  box-shadow: 0 0 0 1px var(--primary-200), var(--shadow-md);
}

.brand-logo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.brand-text {
  display: none;
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-700);
}

.collapse-btn {
  display: none;
  position: relative;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: var(--primary-50);
  color: var(--primary-500);
  font-size: 14px;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.18s ease, color 0.18s ease;
}

.collapse-btn::after {
  content: attr(data-tip);
  position: absolute;
  left: 50%;
  top: -8px;
  transform: translate(-50%, -100%);
  background: var(--primary-700);
  color: var(--text-inverse);
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  padding: 5px 8px;
  border-radius: 6px;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.16s ease;
  z-index: 6;
}

.collapse-btn::before {
  content: '';
  position: absolute;
  left: 50%;
  top: -8px;
  transform: translateX(-50%);
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid var(--primary-700);
  opacity: 0;
  transition: opacity 0.16s ease;
  pointer-events: none;
  z-index: 6;
}

.collapse-btn:hover::after,
.collapse-btn:hover::before,
.collapse-btn:focus-visible::after,
.collapse-btn:focus-visible::before {
  opacity: 1;
}

.collapse-btn:hover {
  background: var(--primary-100);
  color: var(--primary-600);
}

.menu-caption {
  display: none;
  color: var(--text-tertiary);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  padding: 0 6px;
}

.primary-menu-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.primary-menu-btn {
  width: 50px;
  height: 48px;
  border: 1px solid color-mix(in srgb, var(--primary-500) 18%, transparent);
  background: var(--sidebar-item);
  border-radius: 17px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.primary-menu-btn:hover {
  border-color: color-mix(in srgb, var(--primary-500) 34%, transparent);
  background: var(--surface-base);
  transform: translateY(-1px);
}

.primary-menu-btn.active {
  border-color: var(--primary-500);
  background: var(--primary-500);
  box-shadow: var(--shadow-brand);
}

.menu-icon {
  width: 28px;
  height: 28px;
  border-radius: 0;
  background: transparent;
  color: var(--sidebar-icon);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.menu-icon svg {
  width: 16px;
  height: 16px;
}

.menu-icon path {
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.primary-menu-btn.active .menu-icon {
  color: var(--text-inverse);
}

.menu-label {
  display: none;
  color: var(--sidebar-icon);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.sidebar.collapsed {
  width: 70px;
  min-width: 70px;
  padding: 18px 10px;
}

.sidebar.collapsed .brand-text,
.sidebar.collapsed .menu-caption,
.sidebar.collapsed .menu-label {
  display: none;
}

.sidebar.collapsed .brand {
  justify-content: center;
}

.sidebar.collapsed .primary-menu-btn {
  justify-content: center;
  padding: 10px 6px;
}

.sidebar.collapsed .menu-icon {
  width: 28px;
  height: 28px;
}

@media (max-width: 960px) {
  .sidebar {
    width: 70px;
    min-width: 70px;
    padding: 18px 10px;
  }

  .brand {
    justify-content: center;
  }

  .brand-text,
  .menu-caption,
  .menu-label,
  .collapse-btn {
    display: none;
  }

  .primary-menu-btn {
    justify-content: center;
    padding: 0;
  }

  .menu-icon {
    width: 28px;
    height: 28px;
  }
}

@media (max-width: 760px) {
  .sidebar,
  .sidebar.collapsed {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 120;
    width: auto;
    min-width: 0;
    height: calc(72px + env(safe-area-inset-bottom));
    padding: 6px 8px calc(7px + env(safe-area-inset-bottom));
    border-right: none;
    border-top: 1px solid var(--sidebar-border);
    background: var(--mobile-nav-background);
    backdrop-filter: blur(14px);
    overflow: visible;
    box-shadow: var(--shadow-lg);
  }

  .brand,
  .brand-text,
  .menu-caption,
  .collapse-btn {
    display: none;
  }

  .primary-menu-list {
    width: 100%;
    height: 100%;
    display: grid;
    grid-template-columns: repeat(var(--visible-menu-count, 4), minmax(0, 1fr));
    align-items: center;
    justify-items: center;
    gap: 4px;
    margin: 0;
    padding: 0;
  }

  .primary-menu-item {
    width: 100%;
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .primary-menu-btn,
  .sidebar.collapsed .primary-menu-btn {
    width: min(74px, 100%);
    height: 100%;
    min-height: 46px;
    justify-content: center;
    flex-direction: column;
    gap: 2px;
    padding: 4px 2px;
    border-radius: 13px;
    border-color: color-mix(in srgb, var(--primary-500) 18%, transparent);
    background: var(--sidebar-item-mobile);
  }

  .primary-menu-btn.active {
    background: var(--primary-500);
    box-shadow: var(--shadow-brand);
  }

  .menu-icon,
  .sidebar.collapsed .menu-icon {
    width: 23px;
    height: 23px;
  }

  .menu-label,
  .sidebar.collapsed .menu-label {
    display: block;
    width: 100%;
    color: var(--sidebar-icon);
    font-size: 10.5px;
    line-height: 1.1;
    text-align: center;
    overflow: visible;
    text-overflow: clip;
    white-space: nowrap;
  }

  .primary-menu-btn.active .menu-label {
    color: var(--text-inverse);
  }
}
</style>
