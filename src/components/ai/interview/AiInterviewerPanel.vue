<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  ChevronDown,
  FileText,
  History,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Settings,
  Square,
  Timer,
} from 'lucide-vue-next'
import AiConfigDialog from '@/components/ai/AiConfigDialog.vue'
import InterviewSimulationPanel from '@/components/ai/interview/InterviewSimulationPanel.vue'
import ResumePreviewOverlay from '@/components/ai/interview/ResumePreviewOverlay.vue'
import {
  BrowserSpeechTranscriptionSession,
  type SpeechRuntimeState,
  type SpeechSession,
} from '@/services/browserSpeechService'
import { RealtimeTranscriptionSession } from '@/services/realtimeSpeechService'
import { useAiConfigStore } from '@/stores/aiConfig'
import { useResumeStore } from '@/stores/resume'
import {
  getInterviewSessionDetail,
  listInterviewSessions,
  requestInterviewTurn,
  type FinalEvaluation,
  type InterviewCommand,
  type InterviewHistoryItem,
  type InterviewMode,
  type InterviewRequestState,
  type InterviewSessionSummary,
  type InterviewTurnScore,
  type ResumeSnapshot,
} from '@/services/interviewService'
import type { ChatMessage } from '@/components/ai/interview/types'

// author: jf
const TEXT = {
  statusNotStarted: '\u672a\u5f00\u59cb',
  statusFinished: '\u5df2\u7ed3\u675f',
  statusRunning: '\u8fdb\u884c\u4e2d',
  statusPaused: '\u5df2\u6682\u505c',
  unknownError: '\u672a\u77e5\u9519\u8bef',
  modeCandidate: '\u5019\u9009\u4eba\u6a21\u5f0f\uff08AI \u9762\u8bd5\u5b98\uff09',
  modeInterviewer: '\u9762\u8bd5\u5b98\u6a21\u5f0f\uff08AI \u5019\u9009\u4eba\uff09',
  hideResume: '\u6536\u8d77\u7b80\u5386',
  showResume: '\u67e5\u770b\u7b80\u5386',
  totalScore: '\u603b\u5206',
  pass: '\u901a\u8fc7',
  fail: '\u672a\u901a\u8fc7',
  projectInterview: '\u9879\u76ee\u9762\u8bd5',
  switchedToBrowserSpeech: '后端实时语音不可用，已切换为浏览器免费语音识别',
  speechUnavailable: '后端实时语音与浏览器免费语音均不可用',
  speechAutoDisabledNotice: '后端实时语音已因连续失败自动停用，可在语音配置中重新启用。',
  historyPlaceholder: '\u5386\u53f2\u4f1a\u8bdd',
  historyRefresh: '\u5237\u65b0\u5386\u53f2',
  historyLoading: '\u52a0\u8f7d\u4e2d...',
  sessionAlreadyFinished: '\u5f53\u524d\u4f1a\u8bdd\u5df2\u7ed3\u675f\uff0c\u4e0d\u53ef\u7ee7\u7eed\u6216\u53d1\u9001\u6d88\u606f\u3002',
  composerDefaultHint: 'Enter \u53d1\u9001\uff0cCtrl+Enter \u6362\u884c\uff0cCtrl+I \u8bed\u97f3\u5f00\u5173',
  composerListeningHint: '\u8bed\u97f3\u8f93\u5165\u4e2d\uff0c\u70b9\u51fb\u9ea6\u514b\u98ce\u7ed3\u675f',
  composerConnectingHint: '语音连接中，请稍候',
  composerTranscribingHint: '语音转写中，请稍候',
  composerFailedHint: '\u672c\u8f6e\u53d1\u9001\u672a\u5b8c\u6210\uff0c\u8bf7\u6839\u636e\u63d0\u793a\u8c03\u6574\u540e\u91cd\u8bd5',
  composerFinishedHint: '\u5f53\u524d\u4f1a\u8bdd\u5df2\u7ed3\u675f\uff0c\u5982\u9700\u7ee7\u7eed\u8bf7\u5148\u91cd\u7f6e',
  speechRealtimeLabel: '实时语音',
  speechBrowserLabel: '浏览器识别',
  speechPreferredLabel: '后端语音优先',
} as const

const resumeStore = useResumeStore()
const aiConfigStore = useAiConfigStore()

type SpeechEngine = 'realtime' | 'browser'
type SpeechUiState = Exclude<SpeechRuntimeState, 'closed'> | 'idle'

const BACKEND_SPEECH_AUTO_DISABLE_THRESHOLD = 2

const mode = ref<InterviewMode>('candidate')
const durationMinutes = ref(60)
const elapsedSeconds = ref(0)
const sessionStarted = ref(false)
const timerRunning = ref(false)
const isLoading = ref(false)
const isListening = ref(false)
const showResumePreview = ref(false)
const showAiConfig = ref(false)
const historyFieldRef = ref<HTMLElement | null>(null)
const errorMsg = ref('')
const inputText = ref('')
const finalEvaluation = ref<FinalEvaluation | null>(null)
const messages = ref<ChatMessage[]>([])
const memorySummary = ref('')
const requestState = ref<InterviewRequestState>('idle')
const requestStatusText = ref('')
const streamingAssistantMessageId = ref<string | null>(null)
const currentSessionId = ref('')
const sessionHistory = ref<InterviewSessionSummary[]>([])
const selectedSessionId = ref('')
const loadingSessionHistory = ref(false)
const historyMenuOpen = ref(false)
const sessionFinished = ref(false)
const speechUiState = ref<SpeechUiState>('idle')

const totalSeconds = computed(() => Math.max(durationMinutes.value, 1) * 60)
const remainingSeconds = computed(() => Math.max(totalSeconds.value - elapsedSeconds.value, 0))
const timerText = computed(() => {
  const minutes = Math.floor(remainingSeconds.value / 60)
  const seconds = remainingSeconds.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})
const timerStatusText = computed(() => {
  if (!sessionStarted.value) return TEXT.statusNotStarted
  if (sessionFinished.value) return TEXT.statusFinished
  if (remainingSeconds.value === 0) return TEXT.statusFinished
  return timerRunning.value ? TEXT.statusRunning : TEXT.statusPaused
})
const interviewStatusText = computed(() => {
  if (!sessionStarted.value) return TEXT.statusNotStarted
  if (sessionFinished.value || remainingSeconds.value === 0) return TEXT.statusFinished
  return TEXT.statusRunning
})
const pauseButtonLabel = computed(() => (timerRunning.value ? '暂停' : '继续'))
const canSend = computed(() => sessionStarted.value && !sessionFinished.value && inputText.value.trim() !== '' && !isLoading.value)
const canStart = computed(() => !sessionStarted.value && !isLoading.value)
const canTogglePause = computed(() => sessionStarted.value && !sessionFinished.value && remainingSeconds.value > 0 && !isLoading.value)
const canFinish = computed(() => sessionStarted.value && !isLoading.value && !sessionFinished.value && messages.value.length > 0)
const canToggleVoice = computed(
  () => sessionStarted.value && !sessionFinished.value && !isLoading.value && speechUiState.value !== 'transcribing'
)
const selectedSessionLabel = computed(() => {
  const selected = sessionHistory.value.find((item) => item.sessionId === selectedSessionId.value)
  return selected ? buildSessionOptionLabel(selected) : TEXT.historyPlaceholder
})
const historyRefreshText = computed(() => (loadingSessionHistory.value ? TEXT.historyLoading : TEXT.historyRefresh))
const composerHintText = computed(() => {
  if (speechUiState.value === 'connecting') return TEXT.composerConnectingHint
  if (speechUiState.value === 'transcribing') return `${resolveSpeechEngineLabel(activeSpeechEngine.value)}处理中，请稍候`
  if (isListening.value) {
    return TEXT.composerListeningHint
  }
  if (['submitting', 'accepted', 'processing', 'responding'].includes(requestState.value)) {
    return requestStatusText.value || TEXT.composerDefaultHint
  }
  if (requestState.value === 'failed') return TEXT.composerFailedHint
  if (sessionFinished.value) return TEXT.composerFinishedHint
  return TEXT.composerDefaultHint
})

const resumeSnapshot = computed<ResumeSnapshot>(() => ({
  basicInfo: resumeStore.basicInfo,
  skillsText: resumeStore.skills,
  workList: resumeStore.workList,
  projectList: resumeStore.projectList,
  educationList: resumeStore.educationList,
  selfIntro: resumeStore.selfIntro,
}))

let ticker: ReturnType<typeof setInterval> | null = null
let speechSession: SpeechSession | null = null
const activeSpeechEngine = ref<SpeechEngine | null>(null)
let switchingSpeechEngine = false
let speechInputPrefix = ''
let speechTranscript = ''
let backendSpeechFailureCount = 0

function newMessageId(): string {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function resetBackendSpeechFailureState() {
  backendSpeechFailureCount = 0
}

function trackBackendSpeechFailure(): boolean {
  if (!aiConfigStore.useBackendSpeech) {
    return false
  }

  backendSpeechFailureCount += 1
  if (backendSpeechFailureCount < BACKEND_SPEECH_AUTO_DISABLE_THRESHOLD) {
    return false
  }

  aiConfigStore.markBackendSpeechUnavailable()
  return true
}

function resolveAssistantLabel(currentMode: InterviewMode): string {
  return currentMode === 'candidate' ? 'AI面试官' : 'AI候选人'
}

function resolveSpeechEngineLabel(engine: SpeechEngine | null): string {
  if (engine === 'realtime') return TEXT.speechRealtimeLabel
  if (engine === 'browser') return TEXT.speechBrowserLabel
  return aiConfigStore.shouldRequestBackendSpeech ? TEXT.speechPreferredLabel : TEXT.speechBrowserLabel
}

function normalizeStatusMessage(message: string, fallback: string): string {
  const cleaned = String(message || '').trim()
  return cleaned || fallback
}

function buildRequestStatusText(command: InterviewCommand, state: InterviewRequestState): string {
  const assistantLabel = resolveAssistantLabel(mode.value)

  if (command === 'start') {
    if (state === 'submitting') return '正在启动面试...'
    if (state === 'accepted') return '面试已启动，正在同步当前简历上下文'
    if (state === 'processing') {
      return mode.value === 'candidate' ? 'AI面试官正在生成第一轮问题...' : 'AI候选人正在生成开场回答...'
    }
    if (state === 'responding') return `${assistantLabel}正在回复...`
    if (state === 'failed') return '面试启动失败，请重试'
    return ''
  }

  if (command === 'finish') {
    if (state === 'submitting') return '正在结束面试...'
    if (state === 'accepted') return '已收到结束指令'
    if (state === 'processing') return '正在生成评分结果与总结...'
    if (state === 'responding') return `${assistantLabel}正在输出评分结果...`
    if (state === 'failed') return '结束并评分失败，请重试'
    return ''
  }

  if (state === 'submitting') return '消息已发送'
  if (state === 'accepted') return '已收到你的回答'
  if (state === 'processing') {
    return mode.value === 'candidate' ? 'AI面试官正在组织下一轮提问...' : 'AI候选人正在组织回答...'
  }
  if (state === 'responding') return `${assistantLabel}正在回复...`
  if (state === 'failed') return '本轮回复失败，请调整后重试'
  return ''
}

function setRequestState(nextState: InterviewRequestState, command: InterviewCommand, message?: string) {
  requestState.value = nextState

  if (nextState === 'idle' || nextState === 'completed') {
    requestStatusText.value = ''
    return
  }

  requestStatusText.value = normalizeStatusMessage(message || '', buildRequestStatusText(command, nextState))
}

function appendMessage(role: 'assistant' | 'user', content: string, score: InterviewTurnScore | null = null) {
  messages.value.push({
    id: newMessageId(),
    role,
    content: content.trim(),
    score,
  })
}

function createAssistantDraftMessage(content: string): string {
  const id = newMessageId()
  messages.value.push({
    id,
    role: 'assistant',
    content: content.trim(),
    score: null,
  })
  return id
}

function updateAssistantMessageById(id: string, content: string, score: InterviewTurnScore | null = null) {
  const target = messages.value.find((item) => item.id === id)
  if (!target) return
  target.content = content
  target.score = score
}

function removeMessageById(id: string) {
  const index = messages.value.findIndex((item) => item.id === id)
  if (index >= 0) messages.value.splice(index, 1)
}

function formatErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error ?? TEXT.unknownError)
}

function mergeSpeechToInput() {
  const transcript = speechTranscript.trim()
  if (!transcript) {
    inputText.value = speechInputPrefix
    return
  }
  inputText.value = speechInputPrefix ? `${speechInputPrefix}\n${transcript}` : transcript
}

function buildSpeechCallbacks(engine: SpeechEngine) {
  return {
    onPartialText(text: string) {
      speechTranscript = text
      mergeSpeechToInput()
    },
    onFinalText(_segment: string, mergedText: string) {
      speechTranscript = mergedText
      mergeSpeechToInput()
    },
    onError(message: string) {
      if (engine === 'realtime') {
        void handleRealtimeSpeechError(message)
        return
      }
      errorMsg.value = message
      stopSpeechSafely(false)
    },
    onStateChange(state: SpeechRuntimeState) {
      speechUiState.value = state === 'closed' ? 'idle' : state
      isListening.value = state === 'connected' || state === 'connecting'
    },
  }
}

async function createSpeechSession(engine: SpeechEngine): Promise<SpeechSession> {
  if (engine === 'realtime') {
    return new RealtimeTranscriptionSession({
      language: 'zh',
      callbacks: buildSpeechCallbacks('realtime'),
    })
  }

  return new BrowserSpeechTranscriptionSession({
    language: 'zh-CN',
    callbacks: buildSpeechCallbacks('browser'),
  })
}

async function activateSpeechEngine(engine: SpeechEngine) {
  const session = await createSpeechSession(engine)
  speechSession = session
  activeSpeechEngine.value = engine
  speechUiState.value = 'connecting'
  try {
    await session.start()
    if (engine === 'realtime') {
      resetBackendSpeechFailureState()
      aiConfigStore.clearBackendSpeechUnavailable()
    }
  } catch (error) {
    speechSession = null
    activeSpeechEngine.value = null
    speechUiState.value = 'idle'
    throw error
  }
}

async function stopSpeech(clearSpeechText: boolean) {
  const session = speechSession
  speechSession = null

  if (session) {
    await session.stop({ silent: clearSpeechText })
  }

  isListening.value = false
  speechUiState.value = 'idle'
  if (clearSpeechText) {
    speechTranscript = ''
    inputText.value = speechInputPrefix
  }
  speechInputPrefix = ''
  activeSpeechEngine.value = null
}

function stopSpeechSafely(clearSpeechText: boolean) {
  void stopSpeech(clearSpeechText).catch(() => {
    isListening.value = false
    speechUiState.value = 'idle'
    activeSpeechEngine.value = null
  })
}

async function trySwitchToBrowserSpeech(reason: string, trackBackendFailure = false): Promise<boolean> {
  if (switchingSpeechEngine) {
    return false
  }

  switchingSpeechEngine = true
  const backendSpeechAutoDisabled = trackBackendFailure ? trackBackendSpeechFailure() : false
  const autoDisabledNotice = backendSpeechAutoDisabled ? `\n${TEXT.speechAutoDisabledNotice}` : ''
  try {
    const preservedInput = inputText.value.trim()
    await stopSpeech(false)
    speechInputPrefix = preservedInput
    speechTranscript = ''
    inputText.value = preservedInput
    await activateSpeechEngine('browser')
    errorMsg.value = `${TEXT.switchedToBrowserSpeech}\n${reason}${autoDisabledNotice}`
    return true
  } catch (fallbackError) {
    const fallbackMessage = formatErrorMessage(fallbackError)
    errorMsg.value = `${TEXT.speechUnavailable}\n${reason}${autoDisabledNotice}\n${fallbackMessage}`
    return false
  } finally {
    switchingSpeechEngine = false
  }
}

async function handleRealtimeSpeechError(message: string) {
  if (activeSpeechEngine.value === 'realtime') {
    const switched = await trySwitchToBrowserSpeech(message, true)
    if (switched) {
      return
    }
    if (errorMsg.value) {
      stopSpeechSafely(false)
      return
    }
  }

  errorMsg.value = message
  stopSpeechSafely(false)
}

async function startSpeech() {
  if (!sessionStarted.value || isLoading.value || speechSession) return

  errorMsg.value = ''
  speechInputPrefix = inputText.value.trim()
  speechTranscript = ''
  speechUiState.value = 'idle'
  mergeSpeechToInput()

  if (!aiConfigStore.shouldRequestBackendSpeech) {
    try {
      await activateSpeechEngine('browser')
      return
    } catch (error) {
      const message = formatErrorMessage(error)
      errorMsg.value = message
      return
    }
  }

  try {
    await activateSpeechEngine('realtime')
  } catch (error) {
    const realtimeMessage = formatErrorMessage(error)
    const switched = await trySwitchToBrowserSpeech(realtimeMessage, true)
    if (switched) {
      return
    }

    isListening.value = false
    speechUiState.value = 'idle'
    speechTranscript = ''
    inputText.value = speechInputPrefix
    speechInputPrefix = ''
    activeSpeechEngine.value = null
    if (!errorMsg.value) {
      errorMsg.value = `${TEXT.speechUnavailable}\n${realtimeMessage}`
    }
  }
}

function resetSession() {
  stopSpeechSafely(true)
  resetBackendSpeechFailureState()
  messages.value = []
  finalEvaluation.value = null
  memorySummary.value = ''
  errorMsg.value = ''
  requestState.value = 'idle'
  requestStatusText.value = ''
  elapsedSeconds.value = 0
  sessionStarted.value = false
  timerRunning.value = false
  streamingAssistantMessageId.value = null
  inputText.value = ''
  currentSessionId.value = ''
  selectedSessionId.value = ''
  isListening.value = false
  sessionFinished.value = false
  speechUiState.value = 'idle'
  activeSpeechEngine.value = null
}

function buildHistory(excludeLastMessageId?: string): InterviewHistoryItem[] {
  const source = excludeLastMessageId
    ? messages.value.filter((item) => item.id !== excludeLastMessageId)
    : messages.value
  return source.map((item) => ({
    role: item.role,
    content: item.content,
    score: item.score,
  }))
}


function buildSessionOptionLabel(item: InterviewSessionSummary): string {
  const modeLabel = item.mode === 'candidate' ? '候选人' : '面试官'
  const statusLabel = item.status === 'finished' ? '结束' : '进行中'
  const scoreLabel = item.totalScore == null ? '' : ` · ${item.totalScore}分`
  const normalizedTime = item.updatedAt.replace('T', ' ')
  const timeLabel = `${normalizedTime.slice(5, 10)} ${normalizedTime.slice(11, 16)}`
  return `${timeLabel} · ${modeLabel} · ${statusLabel}${scoreLabel}`
}

function applySessionDetail(detail: Awaited<ReturnType<typeof getInterviewSessionDetail>>) {
  mode.value = detail.mode
  durationMinutes.value = Math.max(15, Math.min(120, detail.durationMinutes || 60))
  elapsedSeconds.value = Math.max(0, Math.min(detail.elapsedSeconds || 0, durationMinutes.value * 60))
  messages.value = detail.messages.map((item) => ({
    id: newMessageId(),
    role: item.role,
    content: item.content,
    score: item.score,
  }))
  memorySummary.value = detail.memorySummary || ''
  finalEvaluation.value = detail.finalEvaluation
  requestState.value = 'idle'
  requestStatusText.value = ''
  currentSessionId.value = detail.sessionId
  selectedSessionId.value = detail.sessionId
  sessionStarted.value = detail.messages.length > 0
  timerRunning.value = false
  streamingAssistantMessageId.value = null
  inputText.value = ''
  errorMsg.value = ''
  sessionFinished.value = detail.status === 'finished' || Boolean(detail.finalEvaluation)
}

async function refreshSessionHistory(preferredSessionId?: string) {
  loadingSessionHistory.value = true
  try {
    const sessions = await listInterviewSessions(30)
    sessionHistory.value = sessions

    const targetSessionId =
      preferredSessionId ||
      currentSessionId.value ||
      selectedSessionId.value ||
      sessions[0]?.sessionId ||
      ''

    selectedSessionId.value = sessions.some((item) => item.sessionId === targetSessionId) ? targetSessionId : sessions[0]?.sessionId || ''
  } catch (error) {
    errorMsg.value = formatErrorMessage(error)
  } finally {
    loadingSessionHistory.value = false
  }
}

async function restoreSessionById(sessionId: string, refreshHistory = false) {
  const targetSessionId = sessionId.trim()
  if (!targetSessionId) return

  if (isListening.value) {
    await stopSpeech(false)
  }

  const detail = await getInterviewSessionDetail(targetSessionId)
  applySessionDetail(detail)
  if (refreshHistory) {
    await refreshSessionHistory(targetSessionId)
  }
}

async function initializeSessionHistory() {
  await refreshSessionHistory()
  const firstSessionId = selectedSessionId.value
  if (!firstSessionId) return

  try {
    await restoreSessionById(firstSessionId)
  } catch (error) {
    errorMsg.value = formatErrorMessage(error)
  }
}

async function handleSessionSelectionChange() {
  const targetSessionId = selectedSessionId.value.trim()
  if (!targetSessionId || targetSessionId === currentSessionId.value) return

  try {
    await restoreSessionById(targetSessionId)
  } catch (error) {
    errorMsg.value = formatErrorMessage(error)
  }
}

function handleHistoryMenuToggle() {
  if (loadingSessionHistory.value || sessionHistory.value.length === 0) return
  historyMenuOpen.value = !historyMenuOpen.value
}

function handleHistoryOptionSelect(sessionId: string) {
  selectedSessionId.value = sessionId
  historyMenuOpen.value = false
  void handleSessionSelectionChange()
}

function handleRefreshSessionHistory() {
  historyMenuOpen.value = false
  void refreshSessionHistory(selectedSessionId.value || currentSessionId.value)
}
async function runInterview(command: InterviewCommand, userInput?: string) {
  if (isLoading.value) return
  if (command === 'continue' && sessionFinished.value) {
    errorMsg.value = TEXT.sessionAlreadyFinished
    return
  }

  isLoading.value = true
  errorMsg.value = ''
  setRequestState('submitting', command)
  const draftMessageId = createAssistantDraftMessage(requestStatusText.value || buildRequestStatusText(command, 'submitting'))
  streamingAssistantMessageId.value = draftMessageId
  let hasStreamedAssistantReply = false

  try {
    const response = await requestInterviewTurn(
      {
        mode: mode.value,
        command,
        sessionId: currentSessionId.value || undefined,
        userInput,
        history: buildHistory(draftMessageId),
        resumeSnapshot: resumeSnapshot.value,
        durationMinutes: durationMinutes.value,
        elapsedSeconds: elapsedSeconds.value,
        memorySummary: memorySummary.value,
      },
      undefined,
      {
        onAccepted(message) {
          setRequestState('accepted', command, message)
          updateAssistantMessageById(draftMessageId, requestStatusText.value, null)
        },
        onProcessing(message) {
          setRequestState('processing', command, message)
          updateAssistantMessageById(draftMessageId, requestStatusText.value, null)
        },
        onAssistantReplyChunk(text) {
          hasStreamedAssistantReply = true
          setRequestState('responding', command)
          updateAssistantMessageById(draftMessageId, text)
        },
      }
    )

    updateAssistantMessageById(draftMessageId, response.assistantReply, response.turnScore)
    setRequestState('completed', command)
    if (response.sessionId) {
      currentSessionId.value = response.sessionId
      selectedSessionId.value = response.sessionId
    }
    if (response.memorySummary) memorySummary.value = response.memorySummary
    if (response.finalEvaluation) finalEvaluation.value = response.finalEvaluation
    if (response.nextAction === 'finish' || command === 'finish') {
      timerRunning.value = false
      sessionFinished.value = true
    }
    void refreshSessionHistory(currentSessionId.value)
  } catch (error: unknown) {
    if (!hasStreamedAssistantReply) {
      removeMessageById(draftMessageId)
    }
    setRequestState('failed', command)
    errorMsg.value = formatErrorMessage(error)
  } finally {
    if (streamingAssistantMessageId.value === draftMessageId) {
      streamingAssistantMessageId.value = null
    }
    isLoading.value = false
  }
}

function handleModeSwitch(nextMode: InterviewMode) {
  if (mode.value === nextMode) return
  mode.value = nextMode
  resetSession()
}

function adjustDuration(delta: number) {
  const next = Math.max(15, Math.min(120, durationMinutes.value + delta))
  if (next === durationMinutes.value) return
  durationMinutes.value = next
  if (!sessionStarted.value) {
    elapsedSeconds.value = 0
  } else {
    elapsedSeconds.value = Math.max(0, Math.min(elapsedSeconds.value, totalSeconds.value - 1))
  }
}

function handleStart() {
  if (!canStart.value) return
  currentSessionId.value = ''
  selectedSessionId.value = ''
  sessionStarted.value = true
  timerRunning.value = true
  sessionFinished.value = false
  void runInterview('start')
}

function handleTogglePause() {
  if (!sessionStarted.value || sessionFinished.value || remainingSeconds.value === 0 || isLoading.value) return
  timerRunning.value = !timerRunning.value
}

function handleFinish() {
  if (!canFinish.value) return
  timerRunning.value = false
  void runInterview('finish')
}

function handleReset() {
  resetSession()
}

async function handleSend() {
  const text = inputText.value.trim()
  if (sessionFinished.value) {
    errorMsg.value = TEXT.sessionAlreadyFinished
    return
  }
  if (!canSend.value || !text) return

  if (isListening.value) {
    await stopSpeech(false)
  }

  const finalText = inputText.value.trim()
  if (!finalText) return

  appendMessage('user', finalText)
  inputText.value = ''
  speechInputPrefix = ''
  speechTranscript = ''
  void runInterview('continue', finalText)
}

async function handleToggleVoice() {
  if (!canToggleVoice.value) return

  if (isListening.value) {
    await stopSpeech(false)
    return
  }

  await startSpeech()
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if (!event.ctrlKey || event.altKey || event.shiftKey || event.metaKey) return
  if (event.key.toLowerCase() !== 'i') return
  event.preventDefault()
  void handleToggleVoice()
}

function handleOpenAiConfig() {
  showAiConfig.value = true
}

function handleResumeToggle() {
  showResumePreview.value = !showResumePreview.value
}

function handleDocumentPointerDown(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target) return
  if (historyFieldRef.value && !historyFieldRef.value.contains(target)) {
    historyMenuOpen.value = false
  }
}

watch(remainingSeconds, (value) => {
  if (!sessionStarted.value) return
  if (value !== 0) return
  timerRunning.value = false
  if (!finalEvaluation.value && !isLoading.value) {
    void runInterview('finish')
  }
})

onMounted(() => {
  void initializeSessionHistory()
  window.addEventListener('keydown', handleGlobalKeydown)
  document.addEventListener('mousedown', handleDocumentPointerDown)
  ticker = setInterval(() => {
    if (!sessionStarted.value || !timerRunning.value) return
    if (remainingSeconds.value <= 0) return
    elapsedSeconds.value += 1
  }, 1000)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
  document.removeEventListener('mousedown', handleDocumentPointerDown)
  if (ticker) {
    clearInterval(ticker)
    ticker = null
  }
  stopSpeechSafely(true)
})
</script>

<template>
  <section class="ai-interviewer-panel">
    <header class="interview-hero">
      <div class="interview-identity">
        <span class="interview-identity-mark" aria-hidden="true">AI</span>
        <div class="interview-identity-copy">
          <strong>简历 AI 面试</strong>
          <span v-if="finalEvaluation">
            {{ TEXT.projectInterview }} · {{ finalEvaluation.totalScore }}分 ·
            {{ finalEvaluation.passed ? TEXT.pass : TEXT.fail }}
          </span>
          <span v-else>
            {{ mode === 'candidate' ? '面试官追问' : '候选人模拟' }} · {{ interviewStatusText }}
          </span>
        </div>
      </div>

      <div class="interview-command-bar" aria-label="面试操作">
        <div class="topbar-mode-switch" aria-label="面试模式">
          <button
            type="button"
            :class="{ active: mode === 'candidate' }"
            :aria-pressed="mode === 'candidate'"
            @click="handleModeSwitch('candidate')"
          >
            面试官追问
          </button>
          <button
            type="button"
            :class="{ active: mode === 'interviewer' }"
            :aria-pressed="mode === 'interviewer'"
            @click="handleModeSwitch('interviewer')"
          >
            候选人模拟
          </button>
        </div>

        <button
          type="button"
          class="topbar-action topbar-resume-action"
          :class="{ active: showResumePreview }"
          @click="handleResumeToggle"
        >
          <FileText :size="15" :stroke-width="1.9" aria-hidden="true" />
          {{ showResumePreview ? TEXT.hideResume : TEXT.showResume }}
        </button>

        <button
          type="button"
          class="topbar-action topbar-config-action"
          @click="handleOpenAiConfig"
        >
          <Settings :size="15" :stroke-width="1.9" aria-hidden="true" />
          语音配置
        </button>

        <div class="topbar-duration" aria-label="面试时长">
          <button type="button" aria-label="减少五分钟" @click="adjustDuration(-5)">-5</button>
          <span>
            <Timer :size="15" :stroke-width="1.9" aria-hidden="true" />
            {{ durationMinutes }} 分钟
          </span>
          <button type="button" aria-label="增加五分钟" @click="adjustDuration(5)">+5</button>
        </div>

        <button
          v-if="sessionStarted"
          type="button"
          class="topbar-action topbar-pause-action"
          :disabled="!canTogglePause"
          @click="handleTogglePause"
        >
          <Pause v-if="timerRunning" :size="15" :stroke-width="1.9" aria-hidden="true" />
          <Play v-else :size="15" :stroke-width="1.9" aria-hidden="true" />
          {{ pauseButtonLabel }}
        </button>

        <button
          type="button"
          class="topbar-action topbar-reset-action"
          :disabled="isLoading"
          @click="handleReset"
        >
          <RotateCcw :size="15" :stroke-width="1.9" aria-hidden="true" />
          重置
        </button>

        <button
          v-if="sessionStarted"
          type="button"
          class="topbar-action topbar-finish-action danger"
          :disabled="!canFinish"
          @click="handleFinish"
        >
          <Square :size="14" :stroke-width="1.9" aria-hidden="true" />
          结束并评分
        </button>
      </div>

      <div class="interview-hero-tools">
        <div ref="historyFieldRef" class="history-field" aria-label="历史会话">
          <History :size="16" :stroke-width="1.8" aria-hidden="true" />
          <button
            class="history-select"
            type="button"
            :disabled="loadingSessionHistory"
            :aria-expanded="historyMenuOpen"
            aria-haspopup="listbox"
            @click="handleHistoryMenuToggle"
          >
            <span class="history-select-text">{{ selectedSessionLabel }}</span>
            <ChevronDown class="history-select-arrow" :size="17" :stroke-width="2.1" aria-hidden="true" />
          </button>
          <div v-if="historyMenuOpen" class="history-options" role="listbox">
            <button
              v-for="item in sessionHistory"
              :key="item.sessionId"
              class="history-option"
              :class="{ active: item.sessionId === selectedSessionId }"
              type="button"
              role="option"
              :aria-selected="item.sessionId === selectedSessionId"
              @click="handleHistoryOptionSelect(item.sessionId)"
            >
              {{ buildSessionOptionLabel(item) }}
            </button>
          </div>
        </div>
        <button
          class="history-refresh-btn"
          :class="{ loading: loadingSessionHistory }"
          type="button"
          :disabled="loadingSessionHistory"
          :title="historyRefreshText"
          aria-label="刷新历史"
          :aria-busy="loadingSessionHistory"
          @click="handleRefreshSessionHistory"
        >
          <RefreshCw :size="16" :stroke-width="1.9" aria-hidden="true" />
        </button>
        <span
          class="interview-status-pill"
          :class="{
            active: sessionStarted && !sessionFinished && remainingSeconds > 0,
            finished: sessionFinished || remainingSeconds === 0,
          }"
        >
          <span class="interview-status-dot" aria-hidden="true" />
          {{ interviewStatusText }}
        </span>
      </div>
    </header>

    <div class="interview-layout">
      <div class="workspace">
        <InterviewSimulationPanel
          :mode="mode"
          :messages="messages"
          :is-loading="isLoading"
          :error-msg="errorMsg"
          :input-text="inputText"
          :can-send="canSend"
          :is-listening="isListening"
          :request-state="requestState"
          :request-status-text="requestStatusText"
          :composer-hint-text="composerHintText"
          :streaming-assistant-message-id="streamingAssistantMessageId"
          :session-started="sessionStarted"
          :can-toggle-voice="canToggleVoice"
          :session-finished="sessionFinished"
          :speech-state="speechUiState"
          @update:input-text="inputText = $event"
          @send="handleSend"
          @toggle-voice="handleToggleVoice"
        />

        <ResumePreviewOverlay v-if="showResumePreview" @close="showResumePreview = false" />
      </div>
    </div>

    <button
      v-if="!sessionStarted"
      class="session-start-fab"
      type="button"
      :disabled="isLoading"
      @click="handleStart"
    >
      <Play :size="20" :stroke-width="2" aria-hidden="true" />
      {{ isLoading ? '正在启动...' : '开始面试' }}
    </button>

    <div
      v-else
      class="session-timer-fab"
      :class="{ running: timerRunning, finished: sessionFinished || remainingSeconds === 0 }"
      role="timer"
      aria-live="polite"
    >
      <span class="session-timer-dot" aria-hidden="true" />
      <Timer :size="16" :stroke-width="1.9" aria-hidden="true" />
      <strong>{{ timerText }}</strong>
      <span>{{ timerStatusText }}</span>
    </div>

    <AiConfigDialog v-if="showAiConfig" @close="showAiConfig = false" />
  </section>
</template>

<style scoped>
.ai-interviewer-panel {
  position: relative;
  flex: 1;
  min-width: 0;
  height: 100%;
  overflow: hidden;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--app-background);
}

.interview-hero {
  position: relative;
  z-index: 30;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 58px;
  border: 1px solid var(--border-control);
  border-radius: 24px;
  background: var(--surface-translucent);
  padding: 10px 12px;
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(18px);
  overflow: visible;
}

.interview-hero-tools {
  margin-left: auto;
  max-width: 690px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex: 1 1 520px;
  flex-wrap: wrap;
  gap: 8px;
}

.history-field {
  position: relative;
  z-index: 35;
  min-width: 218px;
  max-width: 360px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  flex: 1 1 260px;
  gap: 8px;
  border: 1px solid var(--border-control);
  border-radius: 999px;
  background: var(--surface-glass);
  color: var(--text-secondary);
  padding: 0 12px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease;
}

.history-field:focus-within {
  border-color: var(--primary-500);
  background: var(--surface-base);
  box-shadow: 0 0 0 4px var(--theme-focus-ring);
}

.history-select {
  width: 100%;
  min-width: 0;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 560;
  outline: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
}

.history-select:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.history-select-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-select-arrow {
  flex: 0 0 17px;
  width: 17px;
  height: 17px;
  color: var(--gray-700);
  transform-origin: center;
  transition: color 0.18s ease, transform 0.18s ease;
}

.history-select[aria-expanded='true'] .history-select-arrow {
  color: var(--primary-500);
  transform: rotate(180deg);
}

.history-options {
  position: absolute;
  top: calc(100% + 7px);
  left: 0;
  z-index: 50;
  width: min(360px, calc(100vw - 36px));
  max-height: min(260px, 48vh);
  overflow-y: auto;
  overflow-x: hidden;
  border: 1px solid var(--border-control);
  border-radius: 16px;
  background: var(--surface-glass-strong);
  box-shadow: var(--shadow-dialog);
  padding: 6px;
}

.history-option {
  width: 100%;
  min-height: 34px;
  display: flex;
  align-items: center;
  border: 0;
  border-radius: 11px;
  background: transparent;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 560;
  line-height: 1.35;
  text-align: left;
  padding: 7px 9px;
  cursor: pointer;
  white-space: normal;
  overflow-wrap: anywhere;
}

.history-option:hover,
.history-option.active {
  background: var(--primary-50);
  color: var(--primary-500);
}

.history-refresh-btn {
  width: 38px;
  height: 38px;
  padding: 0;
  border-radius: 999px;
  border: 1px solid var(--border-control);
  background: var(--surface-glass);
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease;
}

.history-refresh-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--primary-500);
  background: var(--surface-base);
  color: var(--primary-500);
  box-shadow: var(--shadow-brand);
}

.history-refresh-btn:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.history-refresh-btn.loading svg {
  animation: refreshSpin 0.8s linear infinite;
}

@keyframes refreshSpin {
  to {
    transform: rotate(360deg);
  }
}

.interview-status-pill {
  min-width: 90px;
  height: 38px;
  border-radius: 999px;
  border: 1px solid var(--border-control);
  background: var(--surface-glass);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 13px;
  white-space: nowrap;
}

.interview-status-pill.active {
  border-color: var(--border-success);
  background: var(--accent-green-soft);
  color: var(--text-success);
}

.interview-status-pill.finished {
  border-color: color-mix(in srgb, var(--accent-orange) 28%, transparent);
  background: var(--accent-orange-soft);
  color: var(--accent-orange);
}

.interview-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 4px color-mix(in srgb, currentColor 16%, transparent);
}

.final-banner {
  display: flex;
  align-items: center;
  flex: 1 1 auto;
  flex-wrap: wrap;
  gap: 7px;
  min-width: 0;
}

.final-score-chip,
.final-result-chip,
.final-type-chip {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid var(--border-success);
  border-radius: 999px;
  background: var(--accent-green-soft);
  color: var(--text-success);
  font-size: 12px;
  font-weight: 650;
  padding: 0 10px;
  white-space: nowrap;
}

.final-score-chip svg,
.final-result-chip svg,
.final-type-chip svg {
  color: var(--text-success);
}

.final-banner.fail .final-score-chip,
.final-banner.fail .final-result-chip,
.final-banner.fail .final-type-chip {
  border-color: color-mix(in srgb, var(--accent-orange) 28%, transparent);
  background: var(--accent-orange-soft);
  color: var(--text-warning);
}

.final-banner.fail .final-score-chip svg,
.final-banner.fail .final-result-chip svg,
.final-banner.fail .final-type-chip svg {
  color: var(--text-warning);
}

.interview-layout {
  position: relative;
  z-index: 10;
  flex: 1;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 224px;
  gap: 12px;
}

.workspace {
  position: relative;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.workspace > :first-child {
  flex: 1 1 0;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 0;
}

.interview-dock {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dock-card {
  border: 1px solid var(--border-color);
  border-radius: 20px;
  background: var(--surface-raised);
  padding: 12px;
  box-shadow: var(--shadow-lg);
}

.dock-card.dark-card {
  border-color: var(--primary-200);
  background: var(--primary-50);
  color: var(--text-primary);
}

.dock-card-head {
  display: flex;
  gap: 12px;
  align-items: center;
}

.dock-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border-radius: 15px;
  background: var(--surface-base);
  color: var(--primary-500);
}

.dock-icon svg,
.dock-mode-btn svg {
  width: 20px;
  height: 20px;
  display: block;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.dock-card strong,
.dock-card h2 {
  display: block;
  margin: 0;
  color: inherit;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.25;
}

.dock-card span,
.dock-card p {
  display: block;
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.dock-card .dock-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 0;
  color: var(--primary-500);
}

.dock-card:not(.dark-card) h2 {
  color: var(--text-primary);
}

.dock-primary-btn {
  width: 100%;
  min-height: 38px;
  margin-top: 12px;
  border: 0;
  border-radius: 14px;
  background: var(--primary-500);
  color: var(--text-inverse);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.dock-primary-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.dock-mode-list {
  display: grid;
  gap: 7px;
  margin-top: 10px;
}

.dock-mode-btn {
  min-height: 36px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: var(--surface-soft);
  color: var(--gray-600);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.dock-mode-btn.active,
.dock-mode-btn:hover {
  border-color: var(--primary-500);
  background: var(--primary-50);
  color: var(--primary-500);
}

.dock-timer {
  display: grid;
  grid-template-columns: 1fr 1.3fr 1fr;
  gap: 6px;
  margin-top: 12px;
}

.dock-timer button,
.dock-timer strong,
.dock-actions button {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 800;
}

.dock-timer button,
.dock-actions button {
  border: 1px solid var(--border-color);
  background: var(--surface-soft);
  color: var(--gray-600);
  cursor: pointer;
}

.dock-timer strong {
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  color: var(--text-primary);
}

.dock-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  margin-top: 10px;
}

.dock-actions .danger {
  border-color: var(--primary-500);
  background: var(--primary-500);
  color: var(--text-inverse);
}

.dock-actions button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.interview-floating-tools {
  position: fixed;
  right: 24px;
  bottom: calc(clamp(190px, 24vh, 280px) + env(safe-area-inset-bottom));
  z-index: 260;
  pointer-events: none;
}

.floating-actions-stack {
  display: inline-flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: auto;
}

.floating-action-anchor {
  position: relative;
}

.floating-action-btn {
  width: 52px;
  height: 52px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid var(--primary-500);
  background: var(--primary-500);
  color: var(--text-inverse);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-brand);
  transition: transform 0.16s ease, box-shadow 0.16s ease, background-color 0.16s ease, border-color 0.16s ease;
}

.floating-action-btn:hover,
.floating-action-btn.active {
  transform: translateY(-1px);
  border-color: var(--primary-500);
  background: var(--primary-500);
  box-shadow: var(--shadow-brand);
}

.console-action-btn {
  background: var(--primary-500);
  border-color: var(--primary-500);
}

.console-action-btn:hover,
.console-action-btn.active {
  background: var(--primary-500);
  border-color: var(--primary-500);
}

.floating-action-btn svg {
  width: 21px;
  height: 21px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.floating-popover {
  position: absolute;
  right: calc(100% + 12px);
  bottom: 0;
  width: min(360px, calc(100vw - 112px));
  max-height: min(72dvh, 520px);
  overflow: auto;
  border: 1px solid var(--border-color);
  border-radius: 18px;
  background: var(--surface-glass-strong);
  box-shadow: var(--shadow-floating);
  padding: 14px;
  backdrop-filter: blur(14px);
}

.floating-popover-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 800;
}

.mode-popover {
  width: min(310px, calc(100vw - 112px));
}

.mode-option-list {
  margin-top: 12px;
  display: grid;
  gap: 8px;
}

.mode-option-btn {
  min-height: 40px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  color: var(--gray-600);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.35;
  padding: 9px 10px;
  text-align: left;
  cursor: pointer;
}

.mode-option-btn.active {
  border-color: var(--primary-500);
  background: var(--primary-500);
  color: var(--text-inverse);
}

.controls-popover {
  width: min(380px, calc(100vw - 112px));
}

.console-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.console-helper {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 12px;
}

.console-status-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 5px 10px;
  background: var(--surface-soft);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 800;
}

.console-status-pill.active {
  background: var(--accent-green-soft);
  color: var(--text-success);
}

.console-timer-row {
  margin-top: 14px;
  display: grid;
  grid-template-columns: auto 1fr 1.2fr 1fr;
  gap: 6px;
  align-items: center;
}

.console-label {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.console-mini-btn,
.console-timer-value,
.console-btn {
  min-height: 36px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.console-mini-btn,
.console-btn {
  border: 1px solid var(--border-color);
  background: var(--surface-soft);
  color: var(--gray-600);
  cursor: pointer;
}

.console-timer-value {
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  color: var(--text-primary);
}

.console-action-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.console-btn.primary {
  border-color: var(--primary-500);
  background: var(--primary-500);
  color: var(--text-inverse);
}

.console-btn.danger {
  border-color: var(--primary-500);
  background: var(--primary-500);
  color: var(--text-inverse);
}

.console-btn.ghost {
  background: var(--surface-base);
}

.console-finish-btn {
  grid-column: 1 / -1;
  min-height: 40px;
}

.console-mini-btn:disabled,
.console-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (min-width: 861px) {
  .interview-floating-tools {
    display: none;
  }
}

@media (max-width: 860px) {
  .ai-interviewer-panel {
    padding: 10px;
    gap: 7px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .interview-hero {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    padding: 10px;
  }

  .interview-hero-tools {
    width: 100%;
    max-width: none;
    flex: 0 0 auto;
    margin-left: 0;
    justify-content: flex-start;
  }

  .history-field {
    max-width: none;
    flex: 1 1 260px;
  }

  .interview-layout {
    flex: 1 1 auto;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    min-height: 0;
    display: flex;
    overflow: hidden;
  }

  .interview-dock {
    display: none;
  }
}

@media (max-width: 600px) {
  .ai-interviewer-panel {
    padding: 20px 12px calc(10px + env(safe-area-inset-bottom));
    overflow: hidden;
    background: var(--app-background);
  }

  .interview-hero {
    min-height: 0;
    border-radius: 20px;
    padding: 10px;
  }

  .interview-hero-tools {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr);
    gap: 6px;
  }

  .history-field {
    grid-column: 1 / -1;
    width: 100%;
    min-width: 0;
    height: 30px;
    gap: 6px;
    padding: 0 8px;
  }

  .history-select {
    height: 28px;
    font-size: 12px;
    text-overflow: ellipsis;
  }

  .history-select-arrow {
    flex-basis: 15px;
    width: 15px;
    height: 15px;
  }

  .history-options {
    top: calc(100% + 5px);
    width: 100%;
    max-height: 210px;
    border-radius: 13px;
    padding: 5px;
  }

  .history-option {
    min-height: 30px;
    border-radius: 9px;
    font-size: 12px;
    line-height: 1.28;
    padding: 6px 8px;
  }

  .history-refresh-btn {
    width: 30px;
    height: 30px;
  }

  .history-refresh-btn svg {
    width: 14px;
    height: 14px;
  }

  .interview-status-pill {
    width: 100%;
    min-width: 0;
    height: 30px;
    font-size: 10.5px;
    gap: 5px;
    padding: 0 8px;
  }

  .interview-status-dot {
    width: 6px;
    height: 6px;
  }

  .final-banner {
    grid-column: 1 / -1;
    width: 100%;
    max-width: none;
  }

  .final-score-chip,
  .final-result-chip,
  .final-type-chip {
    min-height: 30px;
    font-size: 11px;
    padding: 0 8px;
  }

  .workspace {
    flex: 1 1 auto;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    display: flex;
    min-height: 0;
    overflow: hidden;
  }

  .workspace > :first-child {
    flex: 1 1 0;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    min-height: 0;
  }

  .interview-floating-tools {
    right: 8px;
    bottom: calc(150px + env(safe-area-inset-bottom));
  }

  .floating-actions-stack {
    gap: 6px;
  }

  .floating-action-btn {
    width: 40px;
    height: 40px;
  }

  .floating-action-btn svg {
    width: 18px;
    height: 18px;
  }

  .floating-popover {
    right: calc(100% + 7px);
    width: min(292px, calc(100vw - 60px));
    max-height: min(72dvh, 540px);
    padding: 8px;
    border-radius: 12px;
  }

  .mode-popover,
  .controls-popover {
    width: min(292px, calc(100vw - 60px));
  }

  .console-header {
    flex-direction: column;
    gap: 8px;
  }

  .console-status-pill {
    width: 100%;
    text-align: center;
  }

  .console-timer-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 8px;
    gap: 5px;
  }

  .console-label {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .console-mini-btn,
  .console-timer-value,
  .console-btn {
    min-width: 0;
    font-size: 10.5px;
    min-height: 30px;
    border-radius: 8px;
  }

  .console-action-grid {
    gap: 6px;
    margin-top: 8px;
  }

  .console-finish-btn {
    min-height: 34px;
  }
}
</style>
<style scoped src="./AiInterviewerPanel.chatgpt.css"></style>
