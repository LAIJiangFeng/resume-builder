<!-- author: jf -->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Check, FileText, ShieldCheck, X } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'accept'): void
}>()

const dialogRef = ref<HTMLElement | null>(null)
let previousActiveElement: HTMLElement | null = null
let previousBodyOverflow = ''
let isScrollLocked = false

function restorePageScroll() {
  if (!isScrollLocked) return
  document.body.style.overflow = previousBodyOverflow
  isScrollLocked = false
}

function closeDialog() {
  emit('close')
}

function acceptTerms() {
  emit('accept')
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (!props.open) return

  if (event.key === 'Escape') {
    event.preventDefault()
    closeDialog()
    return
  }

  if (event.key !== 'Tab' || !dialogRef.value) return

  const focusableElements = Array.from(
    dialogRef.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  )
  if (focusableElements.length === 0) return

  const firstElement = focusableElements[0]
  const lastElement = focusableElements[focusableElements.length - 1]
  if (event.shiftKey && document.activeElement === firstElement) {
    event.preventDefault()
    lastElement?.focus()
  } else if (!event.shiftKey && document.activeElement === lastElement) {
    event.preventDefault()
    firstElement?.focus()
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      previousActiveElement = document.activeElement instanceof HTMLElement ? document.activeElement : null
      previousBodyOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      isScrollLocked = true
      await nextTick()
      dialogRef.value?.focus()
      return
    }

    restorePageScroll()
    if (previousActiveElement?.isConnected) previousActiveElement.focus()
    previousActiveElement = null
  },
)

onMounted(() => window.addEventListener('keydown', handleWindowKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
  restorePageScroll()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="terms-dialog">
      <div v-if="open" class="terms-dialog-layer" @click.self="closeDialog">
        <section
          ref="dialogRef"
          class="terms-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="terms-dialog-title"
          aria-describedby="terms-dialog-summary"
          tabindex="-1"
        >
          <header class="terms-dialog-header">
            <div class="terms-dialog-heading">
              <span class="terms-dialog-icon" aria-hidden="true">
                <FileText :size="22" stroke-width="1.8" />
              </span>
              <div>
                <span class="terms-dialog-eyebrow">USER AGREEMENT · V1.0</span>
                <h2 id="terms-dialog-title">Resume Studio 服务条款</h2>
              </div>
            </div>
            <button class="terms-dialog-close" type="button" aria-label="关闭服务条款" @click="closeDialog">
              <X :size="20" stroke-width="1.9" aria-hidden="true" />
            </button>
          </header>

          <div class="terms-dialog-content">
            <p id="terms-dialog-summary" class="terms-dialog-summary">
              欢迎使用 Resume Studio。请在创建账号前阅读以下条款，它说明了你在使用简历编辑、AI
              优化和 AI 面试等服务时享有的权利与需要承担的责任。
            </p>

            <div class="terms-dialog-notice">
              <ShieldCheck :size="20" stroke-width="1.8" aria-hidden="true" />
              <div>
                <strong>生效日期：2026 年 8 月 17 日</strong>
                <span>继续注册即表示你已阅读、理解并同意本条款。</span>
              </div>
            </div>

            <ol class="terms-sections">
              <li>
                <span class="terms-section-number">01</span>
                <div>
                  <h3>协议接受与服务范围</h3>
                  <p>
                    Resume Studio 为求职者提供简历创建、编辑、预览与导出，以及 AI 简历优化、AI
                    面试、知识库等相关能力。你完成注册、登录或实际使用服务，即视为接受本条款；如不同意，请停止注册或使用。
                  </p>
                </div>
              </li>
              <li>
                <span class="terms-section-number">02</span>
                <div>
                  <h3>账号注册与安全</h3>
                  <p>
                    你应使用本人可正常接收邮件的邮箱完成验证，并保证注册信息真实、准确、有效。邮箱验证码仅用于身份验证，请勿转发；因主动泄露密码、验证码或未妥善保管登录设备造成的风险，由你自行承担。
                  </p>
                </div>
              </li>
              <li>
                <span class="terms-section-number">03</span>
                <div>
                  <h3>用户内容与必要授权</h3>
                  <p>
                    你对上传或填写的简历、项目经历、面试回答及其他内容保留合法权利。为向你提供存储、展示、导出、分析和 AI
                    处理能力，你授予 Resume Studio 在服务所必需范围内处理这些内容的非独占、可撤回授权。你应确保相关内容来源合法且不侵犯他人权益。
                  </p>
                </div>
              </li>
              <li>
                <span class="terms-section-number">04</span>
                <div>
                  <h3>AI 生成内容说明</h3>
                  <p>
                    AI 生成的简历建议、面试问题、评分和反馈仅作为求职辅助，可能存在遗漏、偏差或不准确之处，不构成录用承诺或法律、财务等专业意见。你应在提交简历、参加面试或作出重要决定前自行核验并修改。
                  </p>
                </div>
              </li>
              <li>
                <span class="terms-section-number">05</span>
                <div>
                  <h3>使用规范</h3>
                  <p>
                    你不得利用本服务发布违法或侵权内容、冒用他人身份、批量滥用验证码、干扰系统运行、探测或绕过安全措施，也不得未经授权抓取、复制、转售服务或将其用于攻击、欺诈及其他损害他人权益的行为。
                  </p>
                </div>
              </li>
              <li>
                <span class="terms-section-number">06</span>
                <div>
                  <h3>数据与隐私保护</h3>
                  <p>
                    为完成账号认证和产品功能，服务可能处理你的邮箱、昵称、简历内容、面试记录及必要的设备与操作信息。我们仅在提供服务、保障安全、排查故障和履行法定义务所需的范围内处理，并采取合理措施保护数据安全。
                  </p>
                </div>
              </li>
              <li>
                <span class="terms-section-number">07</span>
                <div>
                  <h3>知识产权</h3>
                  <p>
                    Resume Studio 的程序、界面、标识、文档及服务设计所包含的知识产权归其合法权利人所有。本条款不会转让前述权利，也不会影响你对本人原创内容依法享有的权利。
                  </p>
                </div>
              </li>
              <li>
                <span class="terms-section-number">08</span>
                <div>
                  <h3>服务调整与责任边界</h3>
                  <p>
                    我们可能因维护、升级、安全风险或不可抗力调整或暂时中断部分服务，并将尽合理努力降低影响。对于超出合理控制范围的中断，以及因你未核验 AI
                    内容、违规使用或第三方服务异常造成的损失，将在适用法律允许的范围内承担责任。
                  </p>
                </div>
              </li>
              <li>
                <span class="terms-section-number">09</span>
                <div>
                  <h3>协议更新、终止与联系</h3>
                  <p>
                    条款更新后将通过产品页面等合理方式提示，更新内容自标明日期起生效。你可停止使用服务；对于严重违规或危害安全的行为，我们有权限制或终止相关服务。如对条款有疑问，可通过 Resume Studio
                    项目公开的维护渠道联系我们。
                  </p>
                </div>
              </li>
            </ol>
          </div>

          <footer class="terms-dialog-footer">
            <span>阅读完成后，可同意条款并继续注册。</span>
            <div class="terms-dialog-actions">
              <button class="terms-dialog-secondary" type="button" @click="closeDialog">返回注册</button>
              <button class="terms-dialog-primary" type="button" @click="acceptTerms">
                <Check :size="17" stroke-width="2.2" aria-hidden="true" />
                同意并继续
              </button>
            </div>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.terms-dialog-layer {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.58);
  backdrop-filter: blur(10px);
}

.terms-dialog {
  position: relative;
  display: flex;
  width: min(760px, 100%);
  max-height: min(820px, calc(100dvh - 48px));
  overflow: hidden;
  flex-direction: column;
  border: 1px solid var(--border-color, #dbe3ef);
  border-radius: 28px;
  outline: none;
  background: var(--surface-base, #fff);
  box-shadow: 0 30px 90px rgba(15, 23, 42, 0.28);
}

.terms-dialog::before {
  position: absolute;
  z-index: 1;
  top: 0;
  right: 0;
  left: 0;
  height: 4px;
  background: var(--primary-500, #2563eb);
  content: '';
}

.terms-dialog-header {
  position: relative;
  display: flex;
  flex: 0 0 auto;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 28px 30px 22px;
  border-bottom: 1px solid var(--border-soft, #edf1f6);
}

.terms-dialog-heading {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 14px;
}

.terms-dialog-icon {
  display: grid;
  width: 46px;
  height: 46px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--primary-500, #2563eb) 18%, transparent);
  border-radius: 14px;
  background: var(--primary-50, #eff6ff);
  color: var(--primary-500, #2563eb);
}

.terms-dialog-eyebrow {
  display: block;
  margin-bottom: 5px;
  color: var(--primary-500, #2563eb);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.terms-dialog h2 {
  margin: 0;
  color: var(--text-primary, #0f172a);
  font-size: clamp(22px, 3vw, 28px);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.2;
}

.terms-dialog-close {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--border-color, #dbe3ef);
  border-radius: 12px;
  background: var(--surface-base, #fff);
  color: var(--text-secondary, #475569);
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    color 0.18s ease,
    background 0.18s ease;
}

.terms-dialog-close:hover,
.terms-dialog-close:focus-visible {
  border-color: color-mix(in srgb, var(--primary-500, #2563eb) 38%, transparent);
  background: var(--primary-50, #eff6ff);
  color: var(--primary-500, #2563eb);
}

.terms-dialog-content {
  min-height: 0;
  padding: 24px 30px 8px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: var(--border-color, #cbd5e1) transparent;
  scrollbar-width: thin;
}

.terms-dialog-summary {
  margin: 0;
  color: var(--text-secondary, #475569);
  font-size: 15px;
  line-height: 1.8;
}

.terms-dialog-notice {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin: 20px 0 8px;
  padding: 15px 16px;
  border: 1px solid color-mix(in srgb, var(--primary-500, #2563eb) 18%, transparent);
  border-radius: 16px;
  background: var(--primary-50, #eff6ff);
  color: var(--primary-500, #2563eb);
}

.terms-dialog-notice svg {
  flex: 0 0 auto;
  margin-top: 1px;
}

.terms-dialog-notice div {
  display: grid;
  gap: 3px;
}

.terms-dialog-notice strong {
  color: var(--text-primary, #0f172a);
  font-size: 13px;
  font-weight: 700;
}

.terms-dialog-notice span {
  color: var(--text-secondary, #475569);
  font-size: 13px;
  line-height: 1.5;
}

.terms-sections {
  margin: 0;
  padding: 0;
  list-style: none;
}

.terms-sections li {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 14px;
  padding: 20px 0;
  border-bottom: 1px solid var(--border-soft, #edf1f6);
}

.terms-sections li:last-child {
  border-bottom: 0;
}

.terms-section-number {
  display: grid;
  width: 34px;
  height: 26px;
  place-items: center;
  border-radius: 8px;
  background: var(--surface-soft, #f8fafc);
  color: var(--text-tertiary, #64748b);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.terms-sections h3 {
  margin: 1px 0 7px;
  color: var(--text-primary, #0f172a);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.4;
}

.terms-sections p {
  margin: 0;
  color: var(--text-secondary, #475569);
  font-size: 14px;
  line-height: 1.78;
}

.terms-dialog-footer {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 30px;
  border-top: 1px solid var(--border-soft, #edf1f6);
  background: color-mix(in srgb, var(--surface-soft, #f8fafc) 70%, var(--surface-base, #fff));
}

.terms-dialog-footer > span {
  color: var(--text-tertiary, #64748b);
  font-size: 12px;
  line-height: 1.5;
}

.terms-dialog-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 10px;
}

.terms-dialog-secondary,
.terms-dialog-primary {
  display: inline-flex;
  height: 42px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 17px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.terms-dialog-secondary {
  border: 1px solid var(--border-color, #dbe3ef);
  background: var(--surface-base, #fff);
  color: var(--text-secondary, #475569);
}

.terms-dialog-primary {
  border: 1px solid var(--primary-500, #2563eb);
  background: var(--primary-500, #2563eb);
  color: #fff;
  box-shadow: 0 10px 24px color-mix(in srgb, var(--primary-500, #2563eb) 24%, transparent);
}

.terms-dialog-secondary:hover,
.terms-dialog-secondary:focus-visible {
  border-color: var(--primary-500, #2563eb);
  color: var(--primary-500, #2563eb);
}

.terms-dialog-primary:hover,
.terms-dialog-primary:focus-visible {
  transform: translateY(-1px);
  background: var(--primary-600, #1d4ed8);
  box-shadow: 0 14px 28px color-mix(in srgb, var(--primary-500, #2563eb) 30%, transparent);
}

.terms-dialog-close:focus-visible,
.terms-dialog-secondary:focus-visible,
.terms-dialog-primary:focus-visible {
  outline: 2px solid var(--primary-500, #2563eb);
  outline-offset: 3px;
}

.terms-dialog-enter-active,
.terms-dialog-leave-active {
  transition: opacity 0.2s ease;
}

.terms-dialog-enter-active .terms-dialog,
.terms-dialog-leave-active .terms-dialog {
  transition:
    transform 0.22s ease,
    opacity 0.2s ease;
}

.terms-dialog-enter-from,
.terms-dialog-leave-to {
  opacity: 0;
}

.terms-dialog-enter-from .terms-dialog,
.terms-dialog-leave-to .terms-dialog {
  opacity: 0;
  transform: translateY(12px) scale(0.985);
}

@media (max-width: 620px) {
  .terms-dialog-layer {
    align-items: end;
    padding: 12px;
  }

  .terms-dialog {
    max-height: calc(100dvh - 24px);
    border-radius: 22px;
  }

  .terms-dialog-header {
    padding: 23px 20px 18px;
  }

  .terms-dialog-icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
  }

  .terms-dialog-eyebrow {
    font-size: 9px;
  }

  .terms-dialog-content {
    padding: 20px 20px 4px;
  }

  .terms-sections li {
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 10px;
    padding: 17px 0;
  }

  .terms-section-number {
    width: 30px;
  }

  .terms-dialog-footer {
    align-items: stretch;
    padding: 14px 20px 18px;
  }

  .terms-dialog-footer > span {
    display: none;
  }

  .terms-dialog-actions {
    display: grid;
    width: 100%;
    grid-template-columns: 1fr 1.35fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .terms-dialog-enter-active,
  .terms-dialog-leave-active,
  .terms-dialog-enter-active .terms-dialog,
  .terms-dialog-leave-active .terms-dialog {
    transition-duration: 0.01ms !important;
  }
}
</style>
