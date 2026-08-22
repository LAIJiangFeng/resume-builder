<script setup lang="ts">
// author: jf
import { useResumeStore } from '@/stores/resume'
import { ref, reactive } from 'vue'

const store = useResumeStore()
const collapsed = ref(false)

// Extra optional fields visibility
const extraFields = reactive<Record<string, boolean>>({
  wechat: Boolean(store.basicInfo.wechat),
  currentCity: Boolean(store.basicInfo.currentCity),
  github: Boolean(store.basicInfo.github),
  website: Boolean(store.basicInfo.website),
  blog: Boolean(store.basicInfo.blog),
})

type ExtraFieldKey = 'wechat' | 'currentCity' | 'github' | 'website' | 'blog'

function toggleExtra(key: ExtraFieldKey) {
  const next = !extraFields[key]
  extraFields[key] = next
  if (!next) {
    store.basicInfo[key] = ''
  }
}

function handleAvatarUpload(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    const reader = new FileReader()
    reader.onload = (ev) => {
      store.basicInfo.avatar = ev.target?.result as string
    }
    reader.readAsDataURL(input.files[0])
  }
}

function removeAvatar() {
  store.basicInfo.avatar = ''
}
</script>

<template>
  <section class="editor-section">
    <div class="section-header" @click="collapsed = !collapsed">
      <div class="section-toggle">
        <svg
          class="chevron"
          :class="{ rotated: !collapsed }"
          width="16" height="16" viewBox="0 0 16 16" fill="none"
        >
          <path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <h3>基本信息</h3>
      </div>
    </div>

    <div v-show="!collapsed" class="section-body">
      <!-- Row 1: Name, Phone, Email -->
      <div class="form-grid-3">
        <div class="form-group">
          <label class="form-label">姓名</label>
          <input v-model="store.basicInfo.name" type="text" class="form-input" placeholder="请输入姓名" />
        </div>
        <div class="form-group">
          <label class="form-label">电话</label>
          <input v-model="store.basicInfo.phone" type="text" class="form-input" placeholder="请输入电话" />
        </div>
        <div class="form-group">
          <label class="form-label">邮箱</label>
          <input v-model="store.basicInfo.email" type="email" class="form-input" placeholder="请输入邮箱" />
        </div>
      </div>

      <!-- Row 2: Avatar, Age, Gender -->
      <div class="avatar-age-row">
        <div class="avatar-group">
          <label class="form-label">头像</label>
          <div class="avatar-area">
            <div class="avatar-preview" @click="($refs.avatarInput as HTMLInputElement).click()">
              <img v-if="store.basicInfo.avatar" :src="store.basicInfo.avatar" alt="头像" />
              <svg v-else class="avatar-placeholder" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                <circle cx="12" cy="13" r="4"/>
              </svg>
              <div class="avatar-overlay">上传</div>
            </div>
            <div v-if="store.basicInfo.avatar" class="avatar-actions">
              <button class="btn-icon" title="删除" @click="removeAvatar">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  <line x1="10" y1="11" x2="10" y2="17"/>
                  <line x1="14" y1="11" x2="14" y2="17"/>
                </svg>
              </button>
            </div>
          </div>
          <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="handleAvatarUpload" />
        </div>
        <div class="form-group">
          <label class="form-label">年龄</label>
          <input v-model="store.basicInfo.age" type="text" class="form-input" placeholder="例如：25岁" />
        </div>
        <div class="form-group">
          <label class="form-label">性别</label>
          <select v-model="store.basicInfo.gender" class="form-input">
            <option value="">请选择</option>
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </div>
      </div>

      <!-- Work Years -->
      <div class="form-grid-2">
        <div class="form-group">
          <label class="form-label">工作年限</label>
          <input v-model="store.basicInfo.workYears" type="text" class="form-input" placeholder="例如：4年" />
        </div>
      </div>

      <!-- Job Intent Section -->
      <div class="sub-section-title">求职意向</div>
      <div class="form-grid-3">
        <div class="form-group">
          <label class="form-label">当前状态</label>
          <select v-model="store.basicInfo.currentStatus" class="form-input">
            <option value="">请选择</option>
            <option value="在职-考虑机会">在职-考虑机会</option>
            <option value="在职-暂不考虑">在职-暂不考虑</option>
            <option value="离职-随时到岗">离职-随时到岗</option>
            <option value="在校生">在校生</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">职位名称</label>
          <input v-model="store.basicInfo.jobTitle" type="text" class="form-input" placeholder="例如：全栈开发工程师" />
        </div>
        <div class="form-group">
          <label class="form-label">期望工作地</label>
          <input v-model="store.basicInfo.expectedLocation" type="text" class="form-input" placeholder="例如：深圳" />
        </div>
      </div>
      <div class="form-grid-2">
        <div class="form-group">
          <label class="form-label">期望薪资</label>
          <input v-model="store.basicInfo.expectedSalary" type="text" class="form-input" placeholder="例如：面议 / 15-25K" />
        </div>
      </div>

      <!-- Other Info -->
      <div class="sub-section-title">其他信息</div>
      <div class="form-grid-2">
        <div class="form-group">
          <label class="form-label">最高学历</label>
          <select v-model="store.basicInfo.educationLevel" class="form-input">
            <option value="">请选择</option>
            <option value="大专">大专</option>
            <option value="本科">本科</option>
            <option value="硕士">硕士</option>
            <option value="博士">博士</option>
          </select>
        </div>
      </div>
      <!-- More -->
      <div class="sub-section-title">更多</div>
      <div class="extra-tags">
        <button
          class="extra-tag"
          :class="{ active: extraFields.wechat }"
          @click="toggleExtra('wechat')"
        >
          + 微信号
        </button>
        <button
          class="extra-tag"
          :class="{ active: extraFields.currentCity }"
          @click="toggleExtra('currentCity')"
        >
          + 现居城市
        </button>
        <button
          class="extra-tag"
          :class="{ active: extraFields.github }"
          @click="toggleExtra('github')"
        >
          + GitHub
        </button>
        <button
          class="extra-tag"
          :class="{ active: extraFields.website }"
          @click="toggleExtra('website')"
        >
          + 个人网站
        </button>
        <button
          class="extra-tag"
          :class="{ active: extraFields.blog }"
          @click="toggleExtra('blog')"
        >
          + 博客
        </button>
      </div>

      <!-- Dynamic extra fields -->
      <div class="form-grid-2 extra-fields" v-if="extraFields.wechat || extraFields.currentCity || extraFields.github || extraFields.website || extraFields.blog">
        <div class="form-group" v-if="extraFields.wechat">
          <label class="form-label">微信号</label>
          <input v-model="store.basicInfo.wechat" type="text" class="form-input" placeholder="请输入微信号" />
        </div>
        <div class="form-group" v-if="extraFields.currentCity">
          <label class="form-label">现居城市</label>
          <input v-model="store.basicInfo.currentCity" type="text" class="form-input" placeholder="请输入现居城市" />
        </div>
        <div class="form-group" v-if="extraFields.github">
          <label class="form-label">GitHub</label>
          <input v-model="store.basicInfo.github" type="text" class="form-input" placeholder="例如：github.com/username" />
        </div>
        <div class="form-group" v-if="extraFields.website">
          <label class="form-label">个人网站</label>
          <input v-model="store.basicInfo.website" type="text" class="form-input" placeholder="例如：example.com" />
        </div>
        <div class="form-group" v-if="extraFields.blog">
          <label class="form-label">博客</label>
          <input v-model="store.basicInfo.blog" type="text" class="form-input" placeholder="例如：blog.example.com" />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.editor-section {
  margin-bottom: var(--spacing-lg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: white;
  overflow: hidden;
  transition: box-shadow var(--transition-base);
}
.editor-section:hover {
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg) var(--spacing-xl);
  cursor: pointer;
  user-select: none;
  transition: background var(--transition-fast);
}
.section-header:hover {
  background: var(--gray-50);
}

.section-toggle {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}
.section-toggle h3 {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.chevron {
  color: var(--text-secondary);
  transition: transform var(--transition-base);
  transform: rotate(0deg);
}
.chevron.rotated {
  transform: rotate(90deg);
}

.section-body {
  padding: 0 var(--spacing-xl) var(--spacing-xl);
}

/* Sub-section titles */
.sub-section-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-xs);
  border-bottom: 1px solid var(--gray-100);
}

/* Form layouts */
.form-grid-3 {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--spacing-md) var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.form-grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--spacing-md) var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.avatar-age-row {
  display: grid;
  grid-template-columns: auto 1fr 1fr;
  gap: var(--spacing-md) var(--spacing-lg);
  align-items: start;
  margin-bottom: var(--spacing-md);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-label {
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-input {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: 0.88rem;
  color: var(--text-primary);
  background: white;
  transition: all var(--transition-fast);
  outline: none;
}
.form-input:focus {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 3px var(--primary-50);
}
.form-input::placeholder {
  color: var(--gray-400);
}

/* Avatar */
.avatar-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.avatar-area {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-xs);
}

.avatar-preview {
  width: 72px;
  height: 90px;
  border-radius: var(--radius-md);
  border: 2px dashed var(--gray-300);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: border-color var(--transition-base);
}
.avatar-preview:hover {
  border-color: var(--primary-400);
}
.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-placeholder {
  width: 32px;
  height: 32px;
  color: var(--gray-400);
  opacity: 0.6;
}
.avatar-overlay {
  position: absolute;
  inset: 0;
  background: var(--overlay-backdrop-strong);
  color: var(--text-on-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  opacity: 0;
  transition: opacity var(--transition-fast);
}
.avatar-preview:hover .avatar-overlay {
  opacity: 1;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.btn-icon {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--gray-200);
  background: white;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.75rem;
  transition: all var(--transition-fast);
}
.btn-icon:hover {
  background: var(--gray-100);
  border-color: var(--gray-300);
}

/* Extra Tags */
.extra-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.extra-tag {
  padding: var(--spacing-xs) var(--spacing-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: white;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.extra-tag:hover {
  border-color: var(--primary-300);
  color: var(--primary-600);
}
.extra-tag.active {
  background: var(--primary-50);
  border-color: var(--primary-300);
  color: var(--primary-600);
}

.extra-fields {
  margin-top: var(--spacing-sm);
}
</style>
