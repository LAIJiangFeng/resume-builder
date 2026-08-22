<!-- author: jf -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { AwardEntry, ProjectEntry, WorkEntry } from '@/stores/resume'
import { useResumeStore } from '@/stores/resume'
import {
  parseAiResponse,
  getModuleLabel,
  type ModuleData,
} from '@/services/aiService'
import { optimizeModule } from '@/services/aiOptimizeBackendService'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const props = defineProps<{
  open: boolean
}>()

const resumeStore = useResumeStore()
const selectedModule = ref('')
const isLoading = ref(false)
const streamText = ref('')
const errorMsg = ref('')
const isDone = ref(false)
const appliedModules = ref<Set<string>>(new Set())
type ApplyUndoSnapshot = {
  previousContent: string
  previousWorkDescriptions?: string[]
  previousProjectIntroductions?: string[]
  previousProjectMainWorks?: string[]
  previousAwards?: AwardEntry[]
  previousIntroduction?: string
  hadEntry?: boolean
  createdAwardId?: string
}
type PreferredListType = 'ordered' | 'unordered'
const applyHistory = ref<Record<string, ApplyUndoSnapshot[]>>({})

let abortController: AbortController | null = null

const visibleModules = computed(() =>
  resumeStore.modules.filter((m) => m.visible),
)

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
})

const parsed = computed(() => parseAiResponse(streamText.value))
const renderedSuggestions = computed(() =>
  markdown.render(parsed.value.suggestions || '')
)
const resolvedOptimizedContent = computed(() => {
  const optimized = parsed.value.optimizedContent.trim()
  if (optimized) return optimized
  if (selectedModule.value === 'selfIntro') {
    return parsed.value.suggestions.trim()
  }
  return ''
})
const renderedOptimizedContent = computed(() =>
  markdown.render(resolvedOptimizedContent.value || '')
)
const applySupportedModules = new Set(['skills', 'selfIntro', 'workExperience', 'projectExperience', 'awards'])
const canApplySelectedModule = computed(() => applySupportedModules.has(selectedModule.value))
const canUndoSelectedModule = computed(() => {
  const key = selectedModule.value
  if (!key) return false
  return (applyHistory.value[key]?.length ?? 0) > 0
})

const PROJECT_TECH_KEYWORDS = [
  'SpringBoot',
  'Spring Boot',
  'Spring Cloud',
  'Spring AOP',
  'Spring MVC',
  'MySQL',
  'Redis',
  'Redisson',
  'Redis Lua',
  'Lua',
  'Kafka',
  'RabbitMQ',
  'RocketMQ',
  'Elasticsearch',
  'Nginx',
  'Docker',
  'Kubernetes',
  'K8s',
  'JVM',
  'GC',
  'CAS',
  'SSE',
  'CompletableFuture',
  'ThreadPoolExecutor',
  'Sa-Token',
  'SnailJob',
  'MinIO',
  'IP Hash',
  'TTL',
  'DSL',
  'GitHub Issues',
  'AI Coding',
  '分布式锁',
  '动态令牌桶',
  '双检缓存',
  '本地缓存',
  '热点缓存',
  '缓存预热',
  '覆盖索引',
  '分片',
  '防盗链',
  '签名 URL',
  '对象存储',
  '限流',
  '鉴权',
  '异步',
  '调度',
] as const

const PROJECT_RESULT_PHRASE_REGEX = /从\s*\d+(?:\.\d+)?\s*(?:ms|s|秒|分钟|小时|天|周|月|年|QPS|TPS|%|倍|个|次|项|万|亿)?\s*(?:左右)?\s*(?:降至|降低到|下降到|减少到|优化到|提升至|提升到|提高到)\s*\d+(?:\.\d+)?\s*(?:ms|s|秒|分钟|小时|天|周|月|年|QPS|TPS|%|倍|个|次|项|万|亿)?/gi
const PROJECT_METRIC_REGEX = /\d+(?:\.\d+)?\s*(?:ms|s|秒|分钟|小时|天|周|月|年|QPS|TPS|%|倍|个|次|项|w|W|万|亿|封\/(?:分钟|小时|天)|条\/s|次\/s)/g

function pushApplyHistory(key: string, snapshot: ApplyUndoSnapshot) {
  if (!applyHistory.value[key]) {
    applyHistory.value[key] = []
  }
  applyHistory.value[key].push(snapshot)
}

function popApplyHistory(key: string): ApplyUndoSnapshot | undefined {
  const history = applyHistory.value[key]
  if (!history || history.length === 0) return undefined
  const snapshot = history.pop()
  if (history.length === 0) {
    delete applyHistory.value[key]
  }
  return snapshot
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function removeLeadingModuleTitle(markdownText: string, moduleKey: string): string {
  const label = getModuleLabel(moduleKey).trim()
  if (!label) return markdownText.trim()

  const lines = markdownText.split(/\r?\n/)
  let start = 0
  const plainTitle = new RegExp(`^${escapeRegExp(label)}[：:]?$`)
  const mdHeading = new RegExp(`^#{1,6}\\s*${escapeRegExp(label)}[：:]?$`)
  const boldTitle = new RegExp(`^\\*\\*\\s*${escapeRegExp(label)}\\s*\\*\\*[：:]?$`)

  while (start < lines.length && !lines[start]?.trim()) start++
  while (start < lines.length) {
    const current = lines[start]?.trim() ?? ''
    if (plainTitle.test(current) || mdHeading.test(current) || boldTitle.test(current)) {
      start++
      while (start < lines.length && !lines[start]?.trim()) start++
      continue
    }
    break
  }

  return lines.slice(start).join('\n').trim()
}

function stripMarkdownDecorators(line: string): string {
  return line
    .replace(/\*\*/g, '')
    .replace(/__/g, '')
    .replace(/`/g, '')
    .replace(/^\s*[-*+]\s*/, '')
    .replace(/^\s*[*_]+\s*/, '')
    .replace(/^\s*\d+\.\s*/, '')
    .replace(/^\\+#{1,6}(?:\s+|(?=\S))/, '')
    .replace(/^#{1,6}(?:\s+|(?=\S))/, '')
    .replace(/\s*#{1,6}\s*$/, '')
    .replace(/^\s*[*_]+/, '')
    .replace(/[*_]+\s*$/, '')
    .trim()
}

function normalizeListMarkerSpacing(line: string): string {
  return line
    .replace(/^(#{1,6})(?=\S)/, '$1 ')
    .replace(/^([-*+])(?=\S)/, '$1 ')
    .replace(/^(\d+)\.(?=\S)/, '$1. ')
}

function normalizeHeadingLineCandidate(line: string): string {
  return normalizeListMarkerSpacing(line.trim())
    .replace(/^\s*[-*+]\s*/, '')
    .replace(/^\s*[*_]+\s*/, '')
    .replace(/^\\+(#{1,6})(?=\S)/, '$1 ')
    .replace(/^\\+(#{1,6})\s+/, '$1 ')
    .replace(/^(#{1,6})(?=\S)/, '$1 ')
}

function normalizeMarkdownListContent(markdownText: string): string {
  const lines = markdownText.replace(/\r\n/g, '\n').split('\n')
  const out: string[] = []
  let lastListIndex = -1

  for (const rawLine of lines) {
    const trimmed = normalizeListMarkerSpacing(rawLine.trim())
    if (!trimmed) continue

    const plain = stripMarkdownDecorators(trimmed).replace(/[：:]$/, '')
    const headingCandidate = normalizeHeadingLineCandidate(trimmed)
    const isSectionHeading = /^#{1,6}\s*/.test(headingCandidate)
      || /^\*\*[^*]+[:：]?\*\*$/.test(trimmed)
      || /^(项目介绍|项目简介|主要工作|核心职责|工作内容|职责|成果|技术栈)$/.test(plain)
    if (isSectionHeading) {
      out.push(trimmed)
      lastListIndex = -1
      continue
    }

    const isListItem = /^([-*+]\s+|\d+\.\s+)/.test(trimmed)
    if (isListItem) {
      out.push(trimmed)
      lastListIndex = out.length - 1
      continue
    }

    if (lastListIndex >= 0) {
      out[lastListIndex] = `${out[lastListIndex]} ${trimmed}`.replace(/\s+/g, ' ').trim()
    } else {
      out.push(trimmed)
    }
  }

  return out.join('\n').trim()
}

function renumberOrderedMarkdownList(markdownText: string): string {
  const lines = markdownText.replace(/\r\n/g, '\n').split('\n')
  let index = 1
  const out = lines.map((line) => {
    const match = line.match(/^(\s*)\d+\.\s+(.+)$/)
    if (!match) return line
    const indent = match[1] ?? ''
    const body = match[2] ?? ''
    return `${indent}${index++}. ${body}`
  })
  return out.join('\n')
}

function mergeShortSkillsListItems(markdownText: string): string {
  const lines = markdownText.replace(/\r\n/g, '\n').split('\n')
  const out: string[] = []
  const levelRegex = /^(掌握|熟悉|了解)\s*/

  const getItemInfo = (line: string): { marker: string; body: string; level: string; shortScore: number } | null => {
    const match = line.match(/^(\s*(?:[-*+]\s+|\d+\.\s+))(.*)$/)
    if (!match) return null
    const marker = match[1] ?? ''
    const body = (match[2] ?? '').trim()
    const level = body.match(levelRegex)?.[1] ?? ''
    const bodyWithoutLevel = level ? body.replace(levelRegex, '').trim() : body
    const shortScore = stripMarkdownDecorators(bodyWithoutLevel).replace(/[，。；、,.;:\s]/g, '').length
    return { marker, body, level, shortScore }
  }

  for (const rawLine of lines) {
    const current = rawLine.trim()
    if (!current) continue

    const currentInfo = getItemInfo(current)
    if (!currentInfo || out.length === 0) {
      out.push(current)
      continue
    }

    const prevIndex = out.length - 1
    const prevLine = out[prevIndex] ?? ''
    const prevInfo = getItemInfo(prevLine)
    if (!prevInfo) {
      out.push(current)
      continue
    }

    const sameListType = /^(\s*[-*+]\s+)/.test(prevInfo.marker) === /^(\s*[-*+]\s+)/.test(currentInfo.marker)
    const sameLevel = Boolean(prevInfo.level) && prevInfo.level === currentInfo.level
    const shouldMergeByLength = prevInfo.shortScore <= 24 || currentInfo.shortScore <= 24
    const mergedBodyLength = stripMarkdownDecorators(`${prevInfo.body}${currentInfo.body}`).replace(/\s+/g, '').length
    const canMerge = sameListType && sameLevel && shouldMergeByLength && mergedBodyLength <= 90

    if (!canMerge) {
      out.push(current)
      continue
    }

    const currentBodyWithoutLevel = currentInfo.level
      ? currentInfo.body.replace(levelRegex, '').trim()
      : currentInfo.body
    const prevBody = prevInfo.body.replace(/[，。；;]\s*$/, '')
    out[prevIndex] = `${prevInfo.marker}${prevBody}；${currentBodyWithoutLevel}`
  }

  return renumberOrderedMarkdownList(out.join('\n').trim())
}

function createBoldToken(raw: string, tokenMap: Record<string, string>): string {
  const key = `@@BOLD_TOKEN_${Object.keys(tokenMap).length}@@`
  tokenMap[key] = raw
  return key
}

function protectBoldTokens(text: string, tokenMap: Record<string, string>): string {
  return text.replace(/\*\*[^*]+\*\*/g, (match) => createBoldToken(match, tokenMap))
}

function wrapRegexMatchesAsBoldToken(text: string, regex: RegExp, tokenMap: Record<string, string>): string {
  return text.replace(regex, (match) => createBoldToken(`**${match}**`, tokenMap))
}

function wrapKeywordsAsBoldToken(text: string, keywords: readonly string[], tokenMap: Record<string, string>): string {
  let output = text
  const sortedKeywords = [...keywords].sort((a, b) => b.length - a.length)
  for (const keyword of sortedKeywords) {
    const regex = new RegExp(escapeRegExp(keyword), 'gi')
    output = output.replace(regex, (match) => createBoldToken(`**${match}**`, tokenMap))
  }
  return output
}

function restoreBoldTokens(text: string, tokenMap: Record<string, string>): string {
  let output = text
  for (const [token, raw] of Object.entries(tokenMap)) {
    output = output.split(token).join(raw)
  }
  return output
}

function enhanceProjectMainWorkLineBold(lineBody: string): string {
  const tokenMap: Record<string, string> = {}
  let working = protectBoldTokens(lineBody, tokenMap)
  working = wrapRegexMatchesAsBoldToken(working, PROJECT_RESULT_PHRASE_REGEX, tokenMap)
  working = wrapRegexMatchesAsBoldToken(working, PROJECT_METRIC_REGEX, tokenMap)
  working = wrapKeywordsAsBoldToken(working, PROJECT_TECH_KEYWORDS, tokenMap)
  return restoreBoldTokens(working, tokenMap)
}

function enhanceProjectMainWorkBold(markdownText: string): string {
  const lines = markdownText.replace(/\r\n/g, '\n').split('\n')
  const enhancedLines = lines.map((line) => {
    const itemMatch = line.match(/^(\s*(?:[-*+]\s+|\d+\.\s+))(.*)$/)
    if (!itemMatch) return line
    const prefix = itemMatch[1] ?? ''
    const body = itemMatch[2] ?? ''
    if (!body.trim()) return line
    return `${prefix}${enhanceProjectMainWorkLineBold(body)}`
  })
  return enhancedLines.join('\n')
}

function removeMarkdownStrongMarkers(markdownText: string): string {
  return markdownText
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
}

function normalizeProjectIntroductionSingleLine(markdownText: string): string {
  const noStrong = removeMarkdownStrongMarkers(markdownText)
    .replace(/建设目标[:：]?\s*/g, '')
    .replace(/建设目的[:：]?\s*/g, '')
  const lines = noStrong.replace(/\r\n/g, '\n').split('\n')
  const normalizedLines = lines
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/^[-*+]\s+/, '').replace(/^\d+\.\s+/, '').trim())
    .filter(Boolean)
  return normalizedLines.join(' ').replace(/\s+/g, ' ').trim()
}

function parseProjectOptimizedContent(markdownText: string): { introduction: string; mainWork: string } {
  const rawLines = markdownText.replace(/\r\n/g, '\n').split('\n')
  const lines = rawLines.filter((line) => {
    const plain = stripMarkdownDecorators(line)
    return !/^(项目名称|项目名|角色|岗位|时间|项目链接|链接)\s*[:：]/.test(plain)
  })

  const isIntroHeading = (line: string): boolean => {
    const plain = stripMarkdownDecorators(line).replace(/[：:]$/, '')
    return plain === '项目介绍' || plain === '项目简介'
  }
  const isWorkHeading = (line: string): boolean => {
    const plain = stripMarkdownDecorators(line).replace(/[：:]$/, '')
    return plain === '主要工作' || plain === '核心职责' || plain === '工作内容' || plain === '职责'
  }

  const introIdx = lines.findIndex(isIntroHeading)
  const workIdx = lines.findIndex(isWorkHeading)

  let introRaw = ''
  let workRaw = ''

  if (introIdx >= 0 && workIdx >= 0) {
    if (introIdx < workIdx) {
      introRaw = lines.slice(introIdx + 1, workIdx).join('\n').trim()
      workRaw = lines.slice(workIdx + 1).join('\n').trim()
    } else {
      workRaw = lines.slice(workIdx + 1, introIdx).join('\n').trim()
      introRaw = lines.slice(introIdx + 1).join('\n').trim()
    }
  } else if (workIdx >= 0) {
    const beforeWork = lines.slice(0, workIdx).join('\n').trim()
    introRaw = beforeWork
    workRaw = lines.slice(workIdx + 1).join('\n').trim()
  } else {
    const firstListItemIdx = lines.findIndex((line) => /^([-*+]\s+|\d+\.\s+)/.test(line.trim()))
    if (firstListItemIdx > 0) {
      introRaw = lines.slice(0, firstListItemIdx).join('\n').trim()
      workRaw = lines.slice(firstListItemIdx).join('\n').trim()
    } else {
      workRaw = lines.join('\n').trim()
    }
  }

  return {
    introduction: normalizeMarkdownListContent(introRaw),
    mainWork: normalizeMarkdownListContent(workRaw),
  }
}

function isProjectMetadataLine(line: string, projectList: ProjectEntry[]): boolean {
  const plain = stripMarkdownDecorators(line).replace(/[：:]$/, '').trim()
  if (!plain) return false

  if (/^项目经历\s*\d+$/i.test(plain)) return true
  if (/^(项目名称|项目名|角色|岗位|时间|项目链接|链接)\s*[:：]/.test(plain)) return true

  const projectNames = projectList.map((p) => p.name.trim()).filter(Boolean)
  const hasProjectName = projectNames.some((name) => plain.includes(name))
  const isProjectNameOnly = projectNames.some((name) => plain === name)
  const hasDateRange = /(?:19|20)\d{2}[./-]\d{1,2}\s*(?:[~～\-—–至到]+\s*(?:(?:19|20)\d{2}[./-]\d{1,2}|至今|现在))/.test(plain)
  const hasMetaSeparator = /[|｜•·]/.test(plain)

  return hasProjectName && (isProjectNameOnly || hasDateRange || hasMetaSeparator)
}

function parseProjectOptimizedSections(markdownText: string, projectList: ProjectEntry[]): Array<{ introduction: string; mainWork: string }> {
  const lines = markdownText
    .replace(/\r\n/g, '\n')
    .replace(/(^|\n)\s*\\+(#{1,6})(?=\S)/g, '$1$2 ')
    .replace(/(^|\n)\s*\\+(#{1,6})\s+/g, '$1$2 ')
    .replace(/([^\n])\s+(#{1,6})\s*(?=\S)/g, '$1\n$2 ')
    .split('\n')
  const projectNames = projectList.map((p) => p.name.trim()).filter(Boolean)

  const sectionStartIndexes: number[] = []
  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i]?.trim()
    if (!raw) continue

    const plain = stripMarkdownDecorators(raw)
    const hasProjectName = projectNames.some((name) => plain.includes(name))
    const isProjectNameOnly = projectNames.some((name) => plain === name)
    const hasDateRange = /(?:19|20)\d{2}[./-]\d{1,2}\s*(?:[~～\-—–至到]+\s*(?:(?:19|20)\d{2}[./-]\d{1,2}|至今|现在))/.test(plain)
    const hasMetaSeparator = /[|｜•·]/.test(plain)
    const headingCandidate = normalizeHeadingLineCandidate(raw)
    const isSectionHeading = /^#{1,6}\s*项目经历\s*\d+/i.test(headingCandidate) || /^项目经历\s*\d+[：:]?$/i.test(plain)

    if (isSectionHeading || (hasProjectName && (isProjectNameOnly || hasDateRange || hasMetaSeparator || /^#{1,6}\s*/.test(headingCandidate)))) {
      sectionStartIndexes.push(i)
    }
  }

  const uniqStartIndexes = Array.from(new Set(sectionStartIndexes)).sort((a, b) => a - b)
  if (uniqStartIndexes.length === 0) {
    const single = parseProjectOptimizedContent(markdownText)
    return single.introduction || single.mainWork ? [single] : []
  }

  const sections: Array<{ introduction: string; mainWork: string }> = []
  for (let i = 0; i < uniqStartIndexes.length; i++) {
    const start = uniqStartIndexes[i]
    const end = uniqStartIndexes[i + 1] ?? lines.length
    const block = lines.slice(start, end)

    let contentStart = 0
    while (contentStart < block.length) {
      const current = block[contentStart]?.trim() ?? ''
      if (!current) {
        contentStart++
        continue
      }
      if (isProjectMetadataLine(current, projectList)) {
        contentStart++
        continue
      }
      break
    }

    const parsed = parseProjectOptimizedContent(block.slice(contentStart).join('\n'))
    if (parsed.introduction || parsed.mainWork) {
      sections.push(parsed)
    }
  }

  return sections
}

function isWorkMetadataLine(line: string, workList: WorkEntry[]): boolean {
  const plain = stripMarkdownDecorators(line).replace(/[：:]$/, '').trim()
  if (!plain) return false

  if (/^工作经历\s*\d+$/i.test(plain)) return true
  if (/^(公司|单位|部门|职位|岗位|任职时间|时间)\s*[:：]/.test(plain)) return true

  const companyNames = workList.map((w) => w.company.trim()).filter(Boolean)
  const hasCompany = companyNames.some((name) => plain.includes(name))
  const isCompanyOnly = companyNames.some((name) => plain === name)
  const hasDateRange = /(?:19|20)\d{2}[./-]\d{1,2}\s*(?:[~～\-—–至到]+\s*(?:(?:19|20)\d{2}[./-]\d{1,2}|至今|现在))/.test(plain)
  const hasMetaSeparator = /[|｜•·]/.test(plain)

  return hasCompany && (isCompanyOnly || hasDateRange || hasMetaSeparator)
}

function parseWorkOptimizedContent(markdownText: string, workList: WorkEntry[]): string[] {
  const lines = markdownText
    .replace(/\r\n/g, '\n')
    .replace(/(^|\n)\s*\\+(#{1,6})(?=\S)/g, '$1$2 ')
    .replace(/(^|\n)\s*\\+(#{1,6})\s+/g, '$1$2 ')
    .replace(/([^\n])\s+(#{1,6})\s*(?=\S)/g, '$1\n$2 ')
    .split('\n')
  const companyNames = workList.map((w) => w.company.trim()).filter(Boolean)

  const sectionStartIndexes: number[] = []
  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i]?.trim()
    if (!raw) continue

    const plain = stripMarkdownDecorators(raw)
    const hasCompany = companyNames.some((name) => plain.includes(name))
    const isCompanyOnly = companyNames.some((name) => plain === name)
    const hasDateRange = /(?:19|20)\d{2}[./-]\d{1,2}\s*(?:[~～\-—–至到]+\s*(?:(?:19|20)\d{2}[./-]\d{1,2}|至今|现在))/.test(plain)
    const hasMetaSeparator = /[|｜•·]/.test(plain)
    const headingCandidate = normalizeHeadingLineCandidate(raw)
    const isSectionHeading = /^#{1,6}\s*工作经历\s*\d+/i.test(headingCandidate) || /^工作经历\s*\d+[：:]?$/i.test(plain)

    if (isSectionHeading || (hasCompany && (isCompanyOnly || hasDateRange || hasMetaSeparator || /^#{1,6}\s*/.test(headingCandidate)))) {
      sectionStartIndexes.push(i)
    }
  }

  const uniqStartIndexes = Array.from(new Set(sectionStartIndexes)).sort((a, b) => a - b)
  if (uniqStartIndexes.length === 0) {
    const normalized = normalizeMarkdownListContent(markdownText)
    return normalized ? [normalized] : []
  }

  const sections: string[] = []
  for (let i = 0; i < uniqStartIndexes.length; i++) {
    const start = uniqStartIndexes[i]
    const end = uniqStartIndexes[i + 1] ?? lines.length
    const block = lines.slice(start, end)

    let contentStart = 0
    while (contentStart < block.length) {
      const current = block[contentStart]?.trim() ?? ''
      if (!current) {
        contentStart++
        continue
      }
      if (isWorkMetadataLine(current, workList)) {
        contentStart++
        continue
      }
      break
    }

    const normalized = normalizeMarkdownListContent(block.slice(contentStart).join('\n'))
    if (normalized) {
      sections.push(normalized)
    }
  }

  return sections
}

type ParsedAwardSection = {
  name: string
  date: string
  description: string
}

function normalizeAwardDate(rawDate: string): string {
  const trimmed = rawDate.trim()
  if (!trimmed) return ''

  const strictMonth = trimmed.match(/^((?:19|20)\d{2})-(0[1-9]|1[0-2])$/)
  if (strictMonth) return strictMonth[0]

  const compactMonth = trimmed.match(/^((?:19|20)\d{2})(0[1-9]|1[0-2])$/)
  if (compactMonth) return `${compactMonth[1]}-${compactMonth[2]}`

  const looseMonth = trimmed.match(/((?:19|20)\d{2})\s*[年./-]\s*(0?[1-9]|1[0-2])(?:\s*月)?/)
  if (looseMonth) {
    const year = looseMonth[1]
    const month = looseMonth[2]
    if (year && month) {
      return `${year}-${month.padStart(2, '0')}`
    }
  }

  return ''
}

function parseAwardFieldLine(line: string): { field: 'name' | 'date' | 'description'; value: string } | null {
  const plain = stripMarkdownDecorators(line).trim()
  if (!plain) return null

  const nameMatch = plain.match(/^(?:奖项名称|奖项|名称)\s*[：:]\s*(.+)$/)
  if (nameMatch?.[1]) {
    return { field: 'name', value: nameMatch[1].trim() }
  }

  const dateMatch = plain.match(/^(?:获奖时间|时间|日期)\s*[：:]\s*(.+)$/)
  if (dateMatch?.[1]) {
    return { field: 'date', value: dateMatch[1].trim() }
  }

  const descriptionMatch = plain.match(/^(?:描述|说明|奖项描述)\s*[：:]\s*(.*)$/)
  if (descriptionMatch) {
    return { field: 'description', value: descriptionMatch[1]?.trim() ?? '' }
  }

  return null
}

function parseInlineAwardNameAndDate(line: string): { name: string; date: string } | null {
  const trimmed = line.trim()
  if (!/^([-*+]\s+|\d+\.\s+)/.test(trimmed)) return null
  const plain = stripMarkdownDecorators(trimmed)
  if (!plain || /[：:]/.test(plain)) return null

  const dateMatch = plain.match(/((?:19|20)\d{2}\s*[年./-]\s*(?:0?[1-9]|1[0-2])(?:\s*月)?)/)
  const normalizedDate = normalizeAwardDate(dateMatch?.[1] ?? '')
  let name = plain
  if (dateMatch?.[0]) {
    name = name.replace(dateMatch[0], '')
  }
  name = name
    .replace(/[()（）[\]【】]/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()

  if (!name) return null
  return {
    name,
    date: normalizedDate,
  }
}

function parseAwardOptimizedSections(markdownText: string): ParsedAwardSection[] {
  const lines = markdownText.replace(/\r\n/g, '\n').split('\n')
  const sections: ParsedAwardSection[] = []
  let current: ParsedAwardSection = { name: '', date: '', description: '' }

  const appendDescription = (line: string) => {
    const trimmed = line.trim()
    if (!trimmed) return
    current.description = current.description ? `${current.description}\n${trimmed}` : trimmed
  }

  const hasCurrentContent = (): boolean => {
    if (current.name.trim() || current.date.trim()) return true
    return Boolean(stripMarkdownDecorators(current.description).trim())
  }

  const flush = () => {
    if (!hasCurrentContent()) {
      current = { name: '', date: '', description: '' }
      return
    }
    sections.push({
      name: current.name.trim(),
      date: current.date.trim(),
      description: current.description.trim(),
    })
    current = { name: '', date: '', description: '' }
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) continue

    const plain = stripMarkdownDecorators(line).replace(/[：:]$/, '').trim()
    const isDivider = /^[-=]{3,}$/.test(line)
    const isSectionHeading = /^#{1,6}\s*/.test(line) && /^(奖项|荣誉)/.test(plain)
    if (isDivider || isSectionHeading) {
      flush()
      continue
    }

    const field = parseAwardFieldLine(line)
    if (field) {
      if (field.field === 'name' && current.name.trim()) {
        flush()
      }
      if (field.field === 'name') {
        current.name = field.value
      } else if (field.field === 'date') {
        const normalizedDate = normalizeAwardDate(field.value)
        if (normalizedDate) {
          current.date = normalizedDate
        }
      } else if (field.field === 'description') {
        appendDescription(field.value)
      }
      continue
    }

    const inlineAward = parseInlineAwardNameAndDate(line)
    if (inlineAward && !current.description.trim()) {
      if (current.name.trim()) {
        flush()
      }
      current.name = inlineAward.name
      if (inlineAward.date) {
        current.date = inlineAward.date
      }
      continue
    }

    appendDescription(line)
  }

  flush()

  if (sections.length > 0) {
    return sections
  }

  const fallbackAwards = lines
    .map((line) => parseInlineAwardNameAndDate(line))
    .filter((entry): entry is { name: string; date: string } => Boolean(entry?.name))
    .map((entry) => ({
      name: entry.name,
      date: entry.date,
      description: '',
    }))

  if (fallbackAwards.length > 0) {
    return fallbackAwards
  }

  const normalizedDescription = normalizeMarkdownListContent(markdownText)
  if (!normalizedDescription) return []
  return [{
    name: '',
    date: '',
    description: normalizedDescription,
  }]
}

function detectPreferredListTypeFromHtml(html: string): PreferredListType | null {
  const firstListTagMatch = html.match(/<(ol|ul)\b/i)
  if (!firstListTagMatch?.[1]) return null
  return firstListTagMatch[1].toLowerCase() === 'ol' ? 'ordered' : 'unordered'
}

function normalizeMarkdownListType(markdownText: string, preferredListType: PreferredListType | null): string {
  if (!preferredListType) return markdownText

  const lines = markdownText.replace(/\r\n/g, '\n').split('\n')
  let orderedIndex = 1

  const normalizedLines = lines.map((line) => {
    const indent = line.match(/^\s*/)?.[0] ?? ''
    const trimmed = line.trim()
    if (!trimmed) return line

    const unorderedMatch = trimmed.match(/^[-*+]\s+(.+)$/)
    const orderedMatch = trimmed.match(/^\d+\.\s+(.+)$/)
    const itemContent = unorderedMatch?.[1] ?? orderedMatch?.[1]
    if (!itemContent) return line

    if (preferredListType === 'ordered') {
      const normalized = `${indent}${orderedIndex}. ${itemContent}`
      orderedIndex++
      return normalized
    }
    return `${indent}- ${itemContent}`
  })

  return normalizedLines.join('\n')
}

function forceHtmlListType(html: string, preferredListType: PreferredListType | null): string {
  if (!preferredListType) return html
  if (preferredListType === 'ordered') {
    return html.replace(/<ul(\s|>)/gi, '<ol$1').replace(/<\/ul>/gi, '</ol>')
  }
  return html.replace(/<ol(\s|>)/gi, '<ul$1').replace(/<\/ol>/gi, '</ul>')
}

function extractPreferredFontSizeFromHtml(html: string): string | null {
  const inlineFontSizeMatch = html.match(/font-size\s*:\s*([^;"']+)/i)
  if (inlineFontSizeMatch?.[1]) {
    const size = inlineFontSizeMatch[1].trim()
    if (/^\d+(\.\d+)?(px|rem|em|%)$/i.test(size)) {
      return size
    }
  }

  const fontTagSizeMatch = html.match(/<font[^>]*\ssize=["']?([1-7])["']?[^>]*>/i)
  if (fontTagSizeMatch?.[1]) {
    const sizeMap: Record<string, string> = {
      '1': '10px',
      '2': '13px',
      '3': '16px',
      '4': '18px',
      '5': '24px',
      '6': '32px',
      '7': '48px',
    }
    return sizeMap[fontTagSizeMatch[1]] ?? null
  }

  return null
}

function applyPreferredFontSizeToHtml(html: string, preferredFontSize: string | null): string {
  if (!preferredFontSize) return html
  return `<div data-ai-preserved-font-size="true" style="font-size:${preferredFontSize};">${html}</div>`
}

function renderWorkSectionWithOriginalStyle(sectionMarkdown: string, originalHtml: string): string {
  const preferredListType = detectPreferredListTypeFromHtml(originalHtml) ?? 'unordered'
  const preferredFontSize = extractPreferredFontSizeFromHtml(originalHtml)
  const normalizedListMarkdown = normalizeMarkdownListType(sectionMarkdown, preferredListType)
  const rendered = markdown.render(normalizedListMarkdown)
  const listTypeFixed = forceHtmlListType(rendered, preferredListType)
  return applyPreferredFontSizeToHtml(listTypeFixed, preferredFontSize)
}

function renderProjectMainWorkWithOriginalStyle(sectionMarkdown: string, originalHtml: string): string {
  const preferredListType = detectPreferredListTypeFromHtml(originalHtml) ?? 'ordered'
  const preferredFontSize = extractPreferredFontSizeFromHtml(originalHtml)
  const normalizedListMarkdown = normalizeMarkdownListType(sectionMarkdown, preferredListType)
  const rendered = markdown.render(normalizedListMarkdown)
  const listTypeFixed = forceHtmlListType(rendered, preferredListType)
  return applyPreferredFontSizeToHtml(listTypeFixed, preferredFontSize)
}

function renderAwardDescriptionWithOriginalStyle(sectionMarkdown: string, originalHtml: string): string {
  const preferredListType = detectPreferredListTypeFromHtml(originalHtml)
  const preferredFontSize = extractPreferredFontSizeFromHtml(originalHtml)
  const normalizedListMarkdown = normalizeMarkdownListType(sectionMarkdown, preferredListType)
  const rendered = markdown.render(normalizedListMarkdown)
  const listTypeFixed = forceHtmlListType(rendered, preferredListType)
  return applyPreferredFontSizeToHtml(listTypeFixed, preferredFontSize)
}

function getModuleData(): ModuleData {
  return {
    basicInfo: { ...resumeStore.basicInfo },
    educationList: resumeStore.educationList.map((e) => ({ ...e })),
    skills: resumeStore.skills,
    workList: resumeStore.workList.map((w) => ({ ...w })),
    projectList: resumeStore.projectList.map((p) => ({ ...p })),
    awardList: resumeStore.awardList.map((a) => ({ ...a })),
    selfIntro: resumeStore.selfIntro,
  }
}

async function handleOptimize() {
  if (!selectedModule.value) return

  isLoading.value = true
  streamText.value = ''
  errorMsg.value = ''
  isDone.value = false

  abortController = new AbortController()

  await optimizeModule(
    selectedModule.value,
    getModuleData(),
    {
      onChunk(text) {
        streamText.value = text
      },
      onDone(fullText) {
        const parsedSections = parseAiResponse(fullText)
        console.info('[ai-optimize][parsed-sections]', {
          moduleKey: selectedModule.value,
          suggestions: parsedSections.suggestions,
          optimizedContent: parsedSections.optimizedContent,
        })
        streamText.value = fullText
        isLoading.value = false
        isDone.value = true
      },
      onError(err) {
        errorMsg.value = err
        isLoading.value = false
      },
    },
    abortController.signal,
  )
}

function handleStop() {
  abortController?.abort()
  abortController = null
  isLoading.value = false
  if (streamText.value) {
    isDone.value = true
  }
}

function handleApply() {
  if (!resolvedOptimizedContent.value || !selectedModule.value) return

  const optimizedContent = removeLeadingModuleTitle(resolvedOptimizedContent.value, selectedModule.value).trim()
  const content = markdown.render(optimizedContent)
  const key = selectedModule.value
  let applied = false
  let undoSnapshot: ApplyUndoSnapshot | null = null

  switch (key) {
    case 'skills':
      undoSnapshot = { previousContent: resumeStore.skills }
      resumeStore.skills = markdown.render(mergeShortSkillsListItems(optimizedContent))
      applied = true
      break
    case 'selfIntro':
      undoSnapshot = { previousContent: resumeStore.selfIntro }
      resumeStore.selfIntro = content
      applied = true
      break
    case 'workExperience':
      if (resumeStore.workList.length > 0 && resumeStore.workList[0]) {
        undoSnapshot = {
          previousContent: resumeStore.workList[0].description,
          previousWorkDescriptions: resumeStore.workList.map((w) => w.description),
        }
        const workSections = parseWorkOptimizedContent(optimizedContent, resumeStore.workList)
        const maxApplyCount = Math.min(workSections.length, resumeStore.workList.length)

        for (let i = 0; i < maxApplyCount; i++) {
          const section = workSections[i]?.trim()
          if (!section) continue
          const target = resumeStore.workList[i]
          if (!target) continue
          target.description = renderWorkSectionWithOriginalStyle(section, target.description)
          applied = true
        }

        if (!applied && content.trim()) {
          const firstWork = resumeStore.workList[0]
          if (firstWork) {
            firstWork.description = renderWorkSectionWithOriginalStyle(optimizedContent, firstWork.description)
            applied = true
          }
        }
      }
      break
    case 'projectExperience':
      if (resumeStore.projectList.length > 0 && resumeStore.projectList[0]) {
        const target = resumeStore.projectList[0]
        undoSnapshot = {
          previousContent: target.mainWork,
          previousIntroduction: target.introduction,
          previousProjectIntroductions: resumeStore.projectList.map((p) => p.introduction),
          previousProjectMainWorks: resumeStore.projectList.map((p) => p.mainWork),
        }

        const projectSections = parseProjectOptimizedSections(optimizedContent, resumeStore.projectList)
        const maxApplyCount = Math.min(projectSections.length, resumeStore.projectList.length)

        for (let i = 0; i < maxApplyCount; i++) {
          const section = projectSections[i]
          const project = resumeStore.projectList[i]
          if (!section || !project) continue

          if (section.introduction) {
            const introSingleLine = normalizeProjectIntroductionSingleLine(section.introduction)
            if (introSingleLine) {
              project.introduction = markdown.render(introSingleLine)
            }
            applied = true
          }
          if (section.mainWork) {
            const enhancedMainWork = enhanceProjectMainWorkBold(section.mainWork)
            project.mainWork = renderProjectMainWorkWithOriginalStyle(enhancedMainWork, project.mainWork)
            applied = true
          }
        }

        if (!applied && content.trim()) {
          const enhancedMainWork = enhanceProjectMainWorkBold(optimizedContent)
          target.mainWork = renderProjectMainWorkWithOriginalStyle(enhancedMainWork, target.mainWork)
          applied = true
        }
      }
      break
    case 'awards':
      undoSnapshot = {
        previousContent: resumeStore.awardList[0]?.description ?? '',
        previousAwards: resumeStore.awardList.map((award) => ({ ...award })),
      }
      const parsedAwards = parseAwardOptimizedSections(optimizedContent)
      if (parsedAwards.length > 0) {
        const now = Date.now()
        const nextAwards = parsedAwards.map((award, index) => {
          const existing = resumeStore.awardList[index]
          const normalizedDescription = normalizeMarkdownListContent(award.description)
          const renderedDescription = normalizedDescription
            ? renderAwardDescriptionWithOriginalStyle(
              normalizedDescription,
              existing?.description ?? '',
            )
            : ''
          const normalizedDate = normalizeAwardDate(award.date)
          return {
            id: existing?.id ?? `ai_award_${now}_${index + 1}`,
            name: award.name || existing?.name || `奖项 ${index + 1}`,
            date: normalizedDate || existing?.date || '',
            description: renderedDescription,
          }
        })
        resumeStore.awardList.splice(0, resumeStore.awardList.length, ...nextAwards)
        applied = true
      } else if (content.trim()) {
        const existing = resumeStore.awardList[0]
        const fallbackId = existing?.id ?? `ai_award_${Date.now()}_1`
        const fallbackName = existing?.name || '荣誉奖项'
        resumeStore.awardList.splice(0, resumeStore.awardList.length, {
          id: fallbackId,
          name: fallbackName,
          date: existing?.date ?? '',
          description: content,
        })
        applied = true
      }
      break
    default:
      break
  }

  if (!applied) {
    errorMsg.value = `「${getModuleLabel(key)}」暂不支持一键应用，请先复制后手动调整。`
    return
  }

  if (undoSnapshot) {
    pushApplyHistory(key, undoSnapshot)
  }
  appliedModules.value.add(key)
  errorMsg.value = ''
  resumeStore.saveToStorage()
}

function handleUndoApply() {
  const key = selectedModule.value
  if (!key) return
  const snapshot = popApplyHistory(key)
  if (!snapshot) return

  switch (key) {
    case 'skills':
      resumeStore.skills = snapshot.previousContent
      break
    case 'selfIntro':
      resumeStore.selfIntro = snapshot.previousContent
      break
    case 'workExperience':
      if (snapshot.previousWorkDescriptions?.length) {
        const restoreCount = Math.min(snapshot.previousWorkDescriptions.length, resumeStore.workList.length)
        for (let i = 0; i < restoreCount; i++) {
          const target = resumeStore.workList[i]
          if (!target) continue
          target.description = snapshot.previousWorkDescriptions[i] ?? ''
        }
      } else if (resumeStore.workList.length > 0 && resumeStore.workList[0]) {
        resumeStore.workList[0].description = snapshot.previousContent
      }
      break
    case 'projectExperience':
      if (snapshot.previousProjectMainWorks?.length || snapshot.previousProjectIntroductions?.length) {
        const restoreCount = Math.min(
          snapshot.previousProjectMainWorks?.length ?? 0,
          snapshot.previousProjectIntroductions?.length ?? 0,
          resumeStore.projectList.length,
        )
        for (let i = 0; i < restoreCount; i++) {
          const target = resumeStore.projectList[i]
          if (!target) continue
          target.mainWork = snapshot.previousProjectMainWorks?.[i] ?? ''
          target.introduction = snapshot.previousProjectIntroductions?.[i] ?? ''
        }
      } else if (resumeStore.projectList.length > 0 && resumeStore.projectList[0]) {
        resumeStore.projectList[0].mainWork = snapshot.previousContent
        if (snapshot.previousIntroduction !== undefined) {
          resumeStore.projectList[0].introduction = snapshot.previousIntroduction
        }
      }
      break
    case 'awards':
      if (snapshot.previousAwards) {
        resumeStore.awardList.splice(
          0,
          resumeStore.awardList.length,
          ...snapshot.previousAwards.map((award) => ({ ...award })),
        )
      } else if (snapshot.hadEntry === false) {
        const createdId = snapshot.createdAwardId
        if (createdId) {
          const index = resumeStore.awardList.findIndex((a) => a.id === createdId)
          if (index > -1) {
            resumeStore.awardList.splice(index, 1)
          }
        }
      } else if (resumeStore.awardList.length > 0 && resumeStore.awardList[0]) {
        resumeStore.awardList[0].description = snapshot.previousContent
      }
      break
    default:
      break
  }

  appliedModules.value.delete(key)
  errorMsg.value = ''
  resumeStore.saveToStorage()
}

function handleClose() {
  handleStop()
  emit('close')
}

function handleReset() {
  streamText.value = ''
  errorMsg.value = ''
  isDone.value = false
  appliedModules.value.delete(selectedModule.value)
}
</script>

<template>
  <teleport v-if="props.open" to="body">
    <div class="panel-overlay" @click.self="handleClose">
      <aside class="optimize-panel">
        <!-- Header -->
        <div class="panel-header">
          <div class="panel-header-left">
            <span class="panel-icon" aria-hidden="true">
              <svg class="icon-md" viewBox="0 0 24 24">
                <path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3z" />
                <path d="M19 14l.9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14z" />
                <path d="M5 15l.7 1.6L7.3 17l-1.6.7L5 19.3l-.7-1.6L2.7 17l1.6-.7L5 15z" />
              </svg>
            </span>
            <h3 class="panel-title">AI 优化建议</h3>
          </div>
          <div class="panel-header-right">
            <button class="close-btn" @click="handleClose" aria-label="关闭">
              <svg class="icon-sm" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M18 6L6 18" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Module selector -->
        <div class="selector-section">
          <label class="selector-label">选择要优化的模块</label>
          <select v-model="selectedModule" class="module-select">
            <option value="" disabled>请选择模块...</option>
            <option v-for="mod in visibleModules" :key="mod.key" :value="mod.key">
              {{ mod.label }}
            </option>
          </select>

          <div class="action-row">
            <button
              v-if="!isLoading"
              class="btn-optimize"
              :disabled="!selectedModule"
              @click="handleOptimize"
            >
              <svg class="icon-xs" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 19l4.5-1.5L20 7a2.8 2.8 0 1 0-4-4L5.5 13.5 4 18l1 1z" />
                <path d="M13 6l5 5" />
              </svg>
              <span>开始优化</span>
            </button>
            <button v-else class="btn-stop" @click="handleStop">
              <svg class="icon-xs" viewBox="0 0 24 24" aria-hidden="true">
                <rect x="7" y="7" width="10" height="10" rx="1.8" />
              </svg>
              <span>停止生成</span>
            </button>

            <button
              v-if="isDone"
              class="btn-reset"
              @click="handleReset"
            >
              <svg class="icon-xs" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 11a8 8 0 1 0 2.3 5.7" />
                <path d="M20 4v7h-7" />
              </svg>
              <span>重新生成</span>
            </button>
          </div>

        </div>

        <!-- Results area -->
        <div class="results-area">
          <!-- Error -->
          <div v-if="errorMsg" class="error-card">
            <span class="error-icon" aria-hidden="true">
              <svg class="icon-sm" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" />
                <path d="M15 9l-6 6M9 9l6 6" />
              </svg>
            </span>
            <p class="error-text">{{ errorMsg }}</p>
          </div>

          <!-- Loading / Streaming -->
          <div v-if="isLoading && !streamText" class="loading-card">
            <div class="loading-dots">
              <span></span><span></span><span></span>
            </div>
            <p class="loading-text">AI 正在分析中...</p>
          </div>

          <!-- Suggestions -->
          <div v-if="parsed.suggestions" class="result-card suggestions-card">
            <h4 class="result-card-title">
              <svg class="icon-xs" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M9 18h6" />
                <path d="M10 22h4" />
                <path d="M12 2a7 7 0 0 0-4.7 12.2c1 .9 1.7 2.1 1.7 3.4h6c0-1.3.6-2.5 1.6-3.4A7 7 0 0 0 12 2z" />
              </svg>
              <span>优化建议</span>
            </h4>
            <div class="result-content markdown-content" v-html="renderedSuggestions"></div>
          </div>

          <!-- Optimized content -->
          <div v-if="resolvedOptimizedContent" class="result-card content-card">
            <div class="result-card-header">
              <h4 class="result-card-title">
                <svg class="icon-xs" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M14 3h7v7" />
                  <path d="M10 14L21 3" />
                  <path d="M5 7v14h14v-5" />
                </svg>
                <span>优化后内容</span>
              </h4>
              <div class="result-card-actions">
                <button
                  v-if="isDone && canApplySelectedModule && !appliedModules.has(selectedModule)"
                  class="btn-apply"
                  @click="handleApply"
                >
                  <svg class="icon-xs" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                  <span>应用此内容</span>
                </button>
                <button
                  v-if="isDone && canApplySelectedModule && appliedModules.has(selectedModule) && canUndoSelectedModule"
                  class="btn-undo"
                  @click="handleUndoApply"
                >
                  <svg class="icon-xs" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M3 12a9 9 0 1 0 2.6-6.4" />
                    <path d="M3 4v4h4" />
                  </svg>
                  <span>撤回应用</span>
                </button>
                <span v-if="appliedModules.has(selectedModule)" class="applied-tag">已应用</span>
                <span v-if="isDone && !canApplySelectedModule" class="applied-tag">仅查看结果</span>
              </div>
            </div>
            <div class="result-content markdown-content" v-html="renderedOptimizedContent"></div>
          </div>

          <!-- Stream cursor -->
          <span v-if="isLoading && streamText" class="stream-cursor">▌</span>
        </div>
      </aside>
    </div>
  </teleport>
</template>

<style scoped>
.panel-overlay {
  position: fixed;
  inset: 0;
  background: transparent;
  z-index: 900;
  display: block;
  pointer-events: none;
  animation: fadeIn 0.18s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.optimize-panel {
  --preview-panel-width: 812px;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: calc(100vw - var(--preview-panel-width));
  min-width: 560px;
  max-width: 100vw;
  height: 100vh;
  background: var(--surface-disabled);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  pointer-events: auto;
  animation: slideIn 0.25s ease;
  box-shadow: var(--shadow-xl);
}

.optimize-panel::-webkit-scrollbar {
  width: 10px;
}

.optimize-panel::-webkit-scrollbar-thumb {
  background: var(--neutral-track);
}

.optimize-panel::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}

@keyframes slideIn {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}

/* ---- Header ---- */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--surface-base);
  flex-shrink: 0;
}

.panel-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-icon {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.icon-md {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: var(--primary-500);
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.icon-sm {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.icon-xs {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.panel-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.close-btn {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 8px;
  background: var(--surface-soft);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: var(--primary-50);
  color: var(--primary-500);
}

/* ---- Selector ---- */
.selector-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--surface-base);
  flex-shrink: 0;
}

.selector-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-600);
  margin-bottom: 6px;
  display: block;
}

.module-select {
  width: 100%;
  height: 40px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--surface-soft);
  appearance: auto;
}

.module-select:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px var(--theme-focus-ring);
}

.action-row {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.btn-optimize {
  flex: 1;
  height: 38px;
  border: none;
  border-radius: 8px;
  background: var(--primary-500);
  color: var(--text-inverse);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: background 0.15s;
}

.btn-optimize:hover:not(:disabled) {
  background: var(--primary-600);
}

.btn-optimize:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-stop {
  flex: 1;
  height: 38px;
  border: none;
  border-radius: 8px;
  background: var(--accent-red);
  color: var(--text-inverse);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.btn-stop:hover {
  background: var(--accent-red-strong);
}

.btn-reset {
  height: 38px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--surface-base);
  color: var(--gray-600);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-reset:hover {
  border-color: var(--primary-500);
  color: var(--primary-500);
}

/* ---- Results ---- */
.results-area {
  flex: 1 0 auto;
  min-height: auto;
  overflow: visible;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.error-card {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
  background: var(--surface-danger);
  border: 1px solid var(--border-danger);
}

.error-icon {
  color: var(--accent-red-strong);
  flex-shrink: 0;
}

.error-text {
  font-size: 13px;
  color: var(--accent-red-strong);
  line-height: 1.5;
  word-break: break-all;
}

.loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 16px;
}

.loading-dots {
  display: flex;
  gap: 6px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary-500);
  animation: bounce 1.2s infinite ease-in-out;
}

.loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.loading-dots span:nth-child(3) { animation-delay: 0.3s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.loading-text {
  font-size: 13px;
  color: var(--text-secondary);
}

/* ---- Result Cards ---- */
.result-card {
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  overflow: hidden;
}

.result-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 0;
}

.result-card-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.suggestions-card .result-card-title {
  padding: 12px 14px 0;
}

.result-card-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.result-content {
  padding: 10px 14px 14px;
  font-size: 13px;
  color: var(--gray-700);
  line-height: 1.75;
  word-break: break-word;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin: 0 0 8px;
  color: var(--text-primary);
  line-height: 1.45;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2) {
  font-size: 15px;
  font-weight: 700;
}

.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  font-size: 14px;
  font-weight: 700;
}

.markdown-content :deep(p) {
  margin: 0 0 10px;
}

.markdown-content :deep(ol),
.markdown-content :deep(ul) {
  margin: 0 0 10px;
  padding-left: 20px;
}

.markdown-content :deep(li) {
  margin-bottom: 8px;
}

.markdown-content :deep(strong) {
  color: var(--text-primary);
  font-weight: 700;
}

.markdown-content :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  background: var(--primary-50);
  color: var(--primary-500);
  border-radius: 4px;
  padding: 0 4px;
}

.markdown-content :deep(a) {
  color: var(--primary-500);
  text-decoration: underline;
  word-break: break-all;
}

.btn-apply {
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--primary-500);
  border-radius: 7px;
  background: var(--primary-500);
  color: var(--text-inverse);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.btn-apply:hover {
  background: var(--primary-600);
  border-color: var(--primary-600);
}

.btn-undo {
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 7px;
  background: var(--surface-base);
  color: var(--gray-600);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.btn-undo:hover {
  border-color: var(--primary-500);
  color: var(--primary-500);
}

.applied-tag {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-500);
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--primary-50);
}

.stream-cursor {
  color: var(--primary-500);
  font-weight: 700;
  animation: blink 0.7s steps(2, start) infinite;
}

@keyframes blink {
  to { visibility: hidden; }
}

@media (max-width: 720px) {
  .panel-overlay {
    background: var(--overlay-backdrop-soft);
    pointer-events: auto;
  }

  .optimize-panel {
    inset: 0;
    width: 100vw;
    max-width: 100vw;
    min-width: 0;
    height: 100dvh;
    border-right: none;
    border-left: 1px solid var(--border-color);
  }

  .panel-header,
  .selector-section {
    padding-inline: 16px;
  }

  .results-area {
    padding: 14px 16px calc(20px + env(safe-area-inset-bottom));
  }

  .action-row {
    flex-wrap: wrap;
  }

  .btn-optimize,
  .btn-stop,
  .btn-reset {
    min-width: 0;
    flex: 1 1 150px;
    height: 42px;
  }

  .result-card-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .result-card-actions {
    width: 100%;
    align-items: stretch;
    flex-wrap: wrap;
  }

  .btn-apply,
  .btn-undo {
    flex: 1 1 150px;
    justify-content: center;
    height: 38px;
  }

  .applied-tag {
    min-height: 34px;
    display: inline-flex;
    align-items: center;
  }
}

@media (max-width: 1480px) and (min-width: 721px) {
  .optimize-panel {
    --preview-panel-width: 640px;
    min-width: 420px;
  }
}

@media (max-width: 460px) {
  .panel-header {
    padding: 14px 14px;
  }

  .selector-section {
    padding: 14px;
  }

  .results-area {
    padding: 12px 14px calc(18px + env(safe-area-inset-bottom));
  }

  .result-content {
    padding: 10px 12px 12px;
    font-size: 13px;
  }

  .suggestions-card .result-card-title,
  .result-card-header {
    padding-inline: 12px;
  }
}
</style>
