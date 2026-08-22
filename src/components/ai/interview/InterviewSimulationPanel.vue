<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import type { InterviewMode, InterviewRequestState } from '@/services/interviewService'
import type { ChatMessage } from '@/components/ai/interview/types'

// author: jf
const props = defineProps<{
  mode: InterviewMode
  messages: ChatMessage[]
  isLoading: boolean
  errorMsg: string
  inputText: string
  canSend: boolean
  isListening: boolean
  requestState: InterviewRequestState
  requestStatusText: string
  composerHintText: string
  streamingAssistantMessageId: string | null
  sessionStarted: boolean
  canToggleVoice: boolean
  sessionFinished: boolean
  speechState: 'idle' | 'connecting' | 'connected' | 'transcribing'
}>()

const emit = defineEmits<{
  (e: 'update:inputText', value: string): void
  (e: 'send'): void
  (e: 'toggleVoice'): void
}>()

const chatListRef = ref<HTMLElement | null>(null)
const answerInputRef = ref<HTMLTextAreaElement | null>(null)
const shouldFollowLatestMessage = ref(true)
const FOLLOW_LATEST_THRESHOLD = 48
const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
})

const assistantName = computed(() => (props.mode === 'candidate' ? 'AI面试官' : 'AI候选人'))
const isComposerBusy = computed(() =>
  props.isLoading || ['submitting', 'accepted', 'processing', 'responding'].includes(props.requestState)
)
const visibleMessages = computed(() => props.messages.filter((item) => resolveMessageContent(item)))
const composerPlaceholder = computed(() => {
  if (!props.sessionStarted) {
    return '等待开始'
  }
  if (props.sessionFinished) {
    return '当前会话已结束'
  }
  return props.mode === 'candidate'
    ? '输入你的回答，AI 面试官会继续追问'
    : '输入你希望候选人回答的内容或追问方向'
})

function normalizeAssistantContent(content: string): string {
  const text = content?.trim() || ''
  if (!text) return ''

  try {
    const jsonText = (() => {
      if (text.startsWith('{') && text.endsWith('}')) return text
      const first = text.indexOf('{')
      const last = text.lastIndexOf('}')
      if (first >= 0 && last > first) return text.slice(first, last + 1)
      return ''
    })()

    if (!jsonText) return text
    const parsed = JSON.parse(jsonText) as { assistantReply?: unknown }
    if (typeof parsed.assistantReply === 'string' && parsed.assistantReply.trim()) {
      return parsed.assistantReply
    }
  } catch {
    // 不是合法 JSON 时保留原始内容。
  }

  return text
}

function resolveMessageContent(item: ChatMessage): string {
  return item.role === 'assistant' ? normalizeAssistantContent(item.content) : item.content.trim()
}

function renderMarkdown(content: string): string {
  return markdown.render(normalizeAssistantContent(content))
}

function handleInputKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') return
  if ((event as KeyboardEvent & { isComposing?: boolean }).isComposing) return

  if (event.ctrlKey) {
    return
  }

  event.preventDefault()
  if (props.canSend) emit('send')
}

function handleComposerSubmit() {
  if (props.canSend) emit('send')
}

function syncTextareaHeight() {
  const textarea = answerInputRef.value
  if (!textarea) return

  const isCompactViewport = window.matchMedia('(max-width: 768px)').matches
  const isNarrowViewport = window.matchMedia('(max-width: 480px)').matches
  const minHeight = props.sessionFinished ? 40 : isNarrowViewport ? 42 : isCompactViewport ? 42 : 48
  const maxHeight = props.sessionFinished ? (isCompactViewport ? 60 : 82) : isCompactViewport ? 92 : 140

  textarea.style.height = '0px'
  textarea.style.height = `${Math.min(Math.max(textarea.scrollHeight, minHeight), maxHeight)}px`
}

function scrollToBottom() {
  if (!chatListRef.value) return
  chatListRef.value.scrollTop = chatListRef.value.scrollHeight
}

function handleChatScroll() {
  const chatList = chatListRef.value
  if (!chatList) return

  const distanceToBottom = chatList.scrollHeight - chatList.scrollTop - chatList.clientHeight
  shouldFollowLatestMessage.value = distanceToBottom <= FOLLOW_LATEST_THRESHOLD
}

function isPendingAssistantMessage(item: ChatMessage): boolean {
  return (
    item.role === 'assistant' &&
    props.streamingAssistantMessageId === item.id &&
    ['submitting', 'accepted', 'processing'].includes(props.requestState)
  )
}

function isStreamingAssistantMessage(item: ChatMessage): boolean {
  return item.role === 'assistant' && props.streamingAssistantMessageId === item.id && props.requestState === 'responding'
}

watch(
  () => ({
    inputText: props.inputText,
    requestState: props.requestState,
    messages: visibleMessages.value.map((item) => `${item.id}:${resolveMessageContent(item)}`).join('\u0001'),
  }),
  async () => {
    await nextTick()
    syncTextareaHeight()
    if (shouldFollowLatestMessage.value) {
      scrollToBottom()
    }
  }
)

onMounted(() => {
  syncTextareaHeight()
})
</script>

<template>
  <section class="simulation-panel">
    <section class="card qa-card">
      <p v-if="errorMsg" class="error-text">{{ errorMsg }}</p>

      <div ref="chatListRef" class="chat-list" @scroll="handleChatScroll">
        <article
          v-for="item in visibleMessages"
          :key="item.id"
          class="chat-item"
          :class="[
            item.role === 'assistant' ? 'assistant' : 'user',
            {
              pending: isPendingAssistantMessage(item),
              streaming: isStreamingAssistantMessage(item),
            },
          ]"
        >
          <p class="chat-role">{{ item.role === 'assistant' ? assistantName : '你' }}</p>
          <template v-if="item.role === 'assistant'">
            <div v-if="isPendingAssistantMessage(item)" class="assistant-status">
              <span class="assistant-status-orb" aria-hidden="true" />
              <span class="assistant-status-text">{{ requestStatusText || resolveMessageContent(item) }}</span>
            </div>
            <template v-else>
              <div class="chat-markdown markdown-content" v-html="renderMarkdown(item.content)" />
              <span v-if="isStreamingAssistantMessage(item)" class="stream-cursor" aria-hidden="true">▌</span>
            </template>
          </template>
          <p v-else class="chat-content">{{ resolveMessageContent(item) }}</p>
          <p v-if="item.score" class="score-tip">本轮评分 {{ item.score.score }} · {{ item.score.comment }}</p>
        </article>
      </div>

      <form v-if="sessionStarted" class="composer" @submit.prevent="handleComposerSubmit">
        <div
          class="composer-shell"
          :class="{
            busy: isComposerBusy,
            listening: isListening,
            disabled: isLoading || sessionFinished,
          }"
        >
          <textarea
            ref="answerInputRef"
            :value="inputText"
            class="answer-input"
            rows="1"
            :placeholder="composerPlaceholder"
            :disabled="isLoading || sessionFinished"
            @input="emit('update:inputText', ($event.target as HTMLTextAreaElement).value)"
            @keydown="handleInputKeydown"
          />
          <div class="composer-footer">
            <div class="composer-meta">
              <p class="composer-hint">{{ composerHintText }}</p>
            </div>
            <div class="composer-actions">
              <button
                type="button"
                class="icon-btn voice-btn"
                :class="{ active: isListening || speechState === 'transcribing' }"
                :disabled="!canToggleVoice"
                :aria-label="isListening ? '停止语音输入' : '开始语音输入'"
                @click="emit('toggleVoice')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M12 3a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3Zm-6 8a1 1 0 1 1 2 0 4 4 0 0 0 8 0 1 1 0 1 1 2 0 5.99 5.99 0 0 1-5 5.91V20h2a1 1 0 1 1 0 2H9a1 1 0 1 1 0-2h2v-3.09A5.99 5.99 0 0 1 6 11Z"
                  />
                </svg>
              </button>
              <button type="submit" class="icon-btn send-btn" :disabled="!canSend" aria-label="发送回答">
                <span v-if="isComposerBusy" class="send-spinner" aria-hidden="true" />
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4.5 12 19 4.5l-3 15-4.5-5-5 4 1.5-6.5Z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </form>
    </section>
  </section>
</template>

<style scoped>
.simulation-panel {
  --interview-chat-font-size: 13px;
  --interview-chat-meta-font-size: clamp(11px, 1.75vw, 12px);
  --interview-code-font-size: 12.5px;
  flex: 1;
  width: 100%;
  max-width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.card {
  border-radius: 22px;
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  padding: 14px;
}

.qa-card {
  flex: 1 1 0;
  width: 100%;
  max-width: 100%;
  height: auto;
  min-width: 0;
  min-height: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  border-radius: 24px;
  padding: 16px;
  box-shadow: var(--shadow-lg);
}

.question-spotlight {
  padding: 16px 18px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  background: var(--surface-gradient);
  box-shadow: var(--shadow-md);
}

.question-spotlight p {
  margin: 0;
  color: var(--primary-500);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.3;
}

.question-spotlight h2 {
  display: -webkit-box;
  margin: 10px 0 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: clamp(19px, 2vw, 25px);
  font-weight: 650;
  letter-spacing: -0.02em;
  line-height: 1.38;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
}

.spotlight-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.spotlight-tags span {
  min-height: 26px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--primary-50);
  color: var(--primary-500);
  font-size: 11px;
  font-weight: 700;
}

.error-text {
  border: 1px solid var(--border-danger);
  border-radius: 8px;
  background: var(--surface-danger);
  color: var(--text-danger);
  font-size: 12px;
  font-weight: 600;
  padding: 8px 10px;
}

.chat-list {
  flex: 1;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--border-color);
  border-radius: 18px;
  background: var(--surface-soft);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  overflow-x: hidden;
}

.chat-empty {
  color: var(--text-secondary);
  font-size: 12px;
  text-align: center;
  margin: auto 0;
}

.chat-item {
  flex: 0 0 auto;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  min-width: 0;
  overflow: hidden;
  border-radius: 15px;
  padding: 10px 11px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.chat-item.assistant {
  background: var(--surface-base);
  border: 1px solid var(--border-color);
}

.chat-item.assistant.pending {
  border-color: var(--primary-200);
  box-shadow: var(--shadow-brand);
}

.chat-item.user {
  background: var(--primary-50);
  border: 1px solid var(--primary-200);
}

.chat-role {
  color: var(--text-secondary);
  font-size: var(--interview-chat-meta-font-size);
  font-weight: 700;
}

.chat-content {
  max-width: 100%;
  color: var(--text-primary);
  font-size: var(--interview-chat-font-size);
  line-height: 1.62;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.chat-markdown {
  max-width: 100%;
  box-sizing: border-box;
  min-width: 0;
  color: var(--text-primary);
  font-size: var(--interview-chat-font-size);
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.65;
}

.assistant-status {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--gray-600);
  font-size: var(--interview-chat-font-size);
  font-weight: 600;
}

.assistant-status-orb {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--primary-500);
  box-shadow: 0 0 0 8px var(--theme-focus-ring);
  animation: pulse 1.3s ease-in-out infinite;
}

.assistant-status-text {
  min-width: 0;
  word-break: break-word;
}

.markdown-content :deep(p) {
  margin: 0 0 8px;
  max-width: 100%;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0 0 8px;
  padding-left: 18px;
}

.markdown-content :deep(li) {
  margin-bottom: 4px;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.markdown-content :deep(pre) {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  margin: 10px 0;
  padding: 12px;
  border: 1px solid color-mix(in srgb, var(--accent-green) 34%, transparent);
  border-radius: 12px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--accent-green) 12%, transparent), transparent 34%),
    var(--surface-code);
  color: var(--text-on-code);
  overflow-x: auto;
  overflow-y: hidden;
  overscroll-behavior-inline: contain;
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--text-on-code) 6%, transparent);
}

.markdown-content :deep(code) {
  max-width: 100%;
  font-family: 'Fira Code', 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: var(--interview-code-font-size);
  overflow-wrap: anywhere;
  word-break: break-word;
}

.markdown-content :deep(pre code) {
  display: block;
  min-width: 100%;
  width: max-content;
  white-space: pre;
  overflow-wrap: normal;
  word-break: normal;
}

.markdown-content :deep(p code),
.markdown-content :deep(li code) {
  border: 1px solid color-mix(in srgb, var(--accent-green) 22%, transparent);
  background: var(--accent-green-soft);
  color: var(--text-success);
  padding: 2px 6px;
  border-radius: 6px;
  font-weight: 700;
}

.markdown-content :deep(blockquote) {
  margin: 8px 0;
  padding: 6px 10px;
  border-left: 3px solid var(--primary-500);
  background: var(--primary-50);
  color: var(--gray-700);
}

.markdown-content :deep(a) {
  color: var(--primary-500);
}

.score-tip {
  color: var(--primary-500);
  font-size: 12px;
  font-weight: 600;
  background: var(--bg-sidebar);
  border-radius: 8px;
  padding: 6px 8px;
}

.stream-cursor {
  display: inline-block;
  color: var(--primary-500);
  font-weight: 700;
  animation: blink 0.9s steps(1, end) infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

@keyframes pulse {
  50% {
    transform: scale(1.15);
    opacity: 0.85;
  }
}

.composer {
  flex-shrink: 0;
}

.composer-shell {
  border: 1px solid var(--border-color);
  border-radius: 20px;
  background: var(--surface-gradient-vertical);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow-lg);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.composer-shell:focus-within {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 4px var(--theme-focus-ring), var(--shadow-xl);
}

.composer-shell.busy {
  border-color: var(--primary-200);
}

.composer-shell.listening {
  border-color: var(--primary-500);
}

.composer-shell.disabled {
  opacity: 0.82;
}

.answer-input {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: var(--interview-chat-font-size) !important;
  line-height: 1.7;
  min-height: 104px;
  max-height: 220px;
  resize: none;
  padding: 0;
}

.answer-input::placeholder {
  color: var(--text-tertiary);
}

.answer-input:focus {
  outline: none;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.composer-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.composer-hint {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.composer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-btn {
  width: 42px;
  height: 42px;
  border-radius: 999px;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.icon-btn svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.voice-btn {
  border-color: var(--border-color);
  background: var(--surface-base);
  color: var(--text-secondary);
  cursor: pointer;
}

.voice-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
}

.voice-btn.active {
  border-color: var(--primary-500);
  background: var(--theme-focus-ring);
  color: var(--primary-500);
}

.send-btn {
  border: none;
  background: var(--primary-500);
  color: var(--text-inverse);
  cursor: pointer;
  box-shadow: var(--shadow-brand);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px) scale(1.01);
}

.send-btn:disabled,
.voice-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.send-spinner {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid color-mix(in srgb, var(--text-inverse) 26%, transparent);
  border-top-color: var(--text-inverse);
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .simulation-panel {
    --interview-chat-font-size: clamp(11.5px, 3.1vw, 12.5px);
    --interview-chat-meta-font-size: clamp(10.5px, 2.8vw, 11.5px);
    --interview-code-font-size: clamp(11px, 2.9vw, 12px);
    gap: 5px;
    width: 100%;
    max-width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
  }

  .card {
    padding: 6px;
  }

  .composer-shell {
    padding: 6px;
    border-radius: 12px;
    gap: 5px;
  }

  .answer-input {
    min-height: 48px;
    max-height: 86px;
    line-height: 1.35;
  }

  .answer-input::placeholder {
    color: var(--text-tertiary);
    font-size: var(--interview-chat-meta-font-size);
  }

  .composer-footer {
    flex-direction: row;
    align-items: flex-end;
    gap: 5px;
  }

  .composer-meta {
    flex: 1;
    width: 100%;
    gap: 4px;
  }

  .composer-hint {
    font-size: 10px;
    line-height: 1.35;
  }

  .composer-actions {
    flex-shrink: 0;
    justify-content: flex-end;
    gap: 5px;
  }

  .qa-card {
    gap: 6px;
    flex: 1 1 0;
    width: 100%;
    max-width: 100%;
    height: auto;
    min-width: 0;
    min-height: 0;
    border-radius: 22px;
    padding: 12px;
  }

  .question-spotlight {
    padding: 14px;
    border-radius: 18px;
  }

  .question-spotlight h2 {
    font-size: 18px;
    -webkit-line-clamp: 3;
  }

  .chat-list {
    min-height: 0;
    border-radius: 10px;
    padding: 6px;
    gap: 6px;
  }

  .chat-item {
    border-radius: 10px;
    padding: 7px 8px;
    gap: 5px;
  }

  .composer-shell.disabled {
    gap: 5px;
    padding: 6px;
  }

  .composer-shell.disabled .answer-input {
    min-height: 28px;
    max-height: 38px;
  }
}

@media (max-width: 480px) {
  .chat-list {
    padding: 8px;
  }

  .chat-item {
    padding: 8px;
  }

  .composer-actions {
    justify-content: flex-end;
  }

  .icon-btn {
    width: 34px;
    height: 34px;
  }

  .icon-btn svg {
    width: 16px;
    height: 16px;
  }

  .send-btn {
    flex: 0 0 40px;
    border-radius: 999px;
  }

  .answer-input {
    min-height: 40px;
    max-height: 76px;
  }
}
</style>
<style scoped src="./InterviewSimulationPanel.chatgpt.css"></style>
