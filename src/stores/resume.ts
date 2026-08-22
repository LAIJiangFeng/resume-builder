// author: jf
import { defineStore } from 'pinia'
import { reactive, ref, watch } from 'vue'
import {
  activateStoredResume,
  createStoredResume,
  duplicateStoredResume,
  listStoredResumes,
  loadStoredResume,
  removeStoredResume,
  updateStoredResume,
  type ResumeSummary,
  type StoredResume,
} from '@/services/resumeService'
import { normalizeResumeTemplateKey, type ResumeTemplateKey } from '@/templates/resume'

export interface BasicInfo {
  name: string
  phone: string
  email: string
  age: string
  gender: string
  location: string
  jobTitle: string
  educationLevel: string
  avatar: string
  workYears: string
  currentStatus: string
  expectedLocation: string
  expectedSalary: string
  website: string
  wechat: string
  currentCity: string
  github: string
  blog: string
}

export interface EducationEntry {
  id: string
  school: string
  college: string
  major: string
  degree: string
  startDate: string
  endDate: string
  gpa: string
  description: string
  type: string
  location: string
}

export interface WorkEntry {
  id: string
  company: string
  department: string
  position: string
  startDate: string
  endDate: string
  location: string
  description: string
}

export interface ProjectEntry {
  id: string
  name: string
  role: string
  startDate: string
  endDate: string
  link: string
  introduction: string
  mainWork: string
}

export interface AwardEntry {
  id: string
  name: string
  date: string
  description: string
}

export interface ModuleConfig {
  key: string
  label: string
  icon: string
  visible: boolean
}

export interface ResumeDocument {
  [key: string]: unknown
  modules: ModuleConfig[]
  selectedTemplateKey: ResumeTemplateKey
  basicInfo: BasicInfo
  educationList: EducationEntry[]
  skills: string
  workList: WorkEntry[]
  projectList: ProjectEntry[]
  awardList: AwardEntry[]
  selfIntro: string
}

type MoveDirection = 'up' | 'down'
type SaveMode = 'auto' | 'manual'

const LEGACY_STORAGE_KEY = 'resume-builder-data'
const AUTO_SAVE_DELAY_MS = 500
const SAVE_LOADING_MIN_MS = 450
const DEFAULT_MODULE_ORDER = [
  'basicInfo',
  'education',
  'skills',
  'workExperience',
  'projectExperience',
  'awards',
  'selfIntro',
] as const

const DEFAULT_MODULES: ModuleConfig[] = [
  { key: 'basicInfo', label: '基本信息', icon: '👤', visible: true },
  { key: 'education', label: '教育经历', icon: '🎓', visible: true },
  { key: 'skills', label: '专业技能', icon: '⚡', visible: true },
  { key: 'workExperience', label: '工作经历', icon: '💼', visible: true },
  { key: 'projectExperience', label: '项目经历', icon: '📁', visible: true },
  { key: 'awards', label: '荣誉奖项', icon: '🏆', visible: false },
  { key: 'selfIntro', label: '个人简介', icon: '📝', visible: false },
]

let idCounter = 0

function genId(): string {
  return `item_${Date.now()}_${++idCounter}`
}

function createDefaultBasicInfo(): BasicInfo {
  return {
    name: '',
    phone: '',
    email: '',
    age: '',
    gender: '',
    location: '',
    jobTitle: '',
    educationLevel: '',
    avatar: '',
    workYears: '',
    currentStatus: '',
    expectedLocation: '',
    expectedSalary: '',
    website: '',
    wechat: '',
    currentCity: '',
    github: '',
    blog: '',
  }
}

function createDefaultEducation(): EducationEntry {
  return {
    id: genId(),
    school: '',
    college: '',
    major: '',
    degree: '',
    startDate: '',
    endDate: '',
    gpa: '',
    description: '',
    type: '',
    location: '',
  }
}

function createDefaultWork(): WorkEntry {
  return {
    id: genId(),
    company: '',
    department: '',
    position: '',
    startDate: '',
    endDate: '',
    location: '',
    description: '',
  }
}

function createDefaultProject(): ProjectEntry {
  return {
    id: genId(),
    name: '',
    role: '',
    startDate: '',
    endDate: '',
    link: '',
    introduction: '',
    mainWork: '',
  }
}

function createEmptyResumeDocument(): ResumeDocument {
  return {
    modules: DEFAULT_MODULES.map((module) => ({ ...module })),
    selectedTemplateKey: 'default',
    basicInfo: createDefaultBasicInfo(),
    educationList: [createDefaultEducation()],
    skills: '',
    workList: [createDefaultWork()],
    projectList: [createDefaultProject()],
    awardList: [],
    selfIntro: '',
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export const useResumeStore = defineStore('resume', () => {
  const initialDocument = createEmptyResumeDocument()
  const modules = reactive<ModuleConfig[]>(initialDocument.modules)
  const basicInfo = reactive<BasicInfo>(initialDocument.basicInfo)
  const educationList = reactive<EducationEntry[]>(initialDocument.educationList)
  const skills = ref(initialDocument.skills)
  const workList = reactive<WorkEntry[]>(initialDocument.workList)
  const projectList = reactive<ProjectEntry[]>(initialDocument.projectList)
  const awardList = reactive<AwardEntry[]>(initialDocument.awardList)
  const selfIntro = ref(initialDocument.selfIntro)
  const selectedTemplateKey = ref<ResumeTemplateKey>(initialDocument.selectedTemplateKey)
  const documentVersion = ref(0)

  const resumeList = ref<ResumeSummary[]>([])
  const currentResumeId = ref<string | null>(null)
  const currentResumeName = ref('我的简历')
  const isInitialized = ref(false)
  const isLoading = ref(false)
  const isManaging = ref(false)
  const nextAutoSaveAt = ref<number | null>(null)
  const lastSavedAt = ref<number | null>(null)
  const lastSaveMode = ref<SaveMode | null>(null)
  const isSaving = ref(false)
  const saveError = ref('')

  let saveTimer: ReturnType<typeof setTimeout> | null = null
  let saveLoadingTimer: ReturnType<typeof setTimeout> | null = null
  let suppressAutoSave = true
  let saveQueue: Promise<void> = Promise.resolve()
  let pendingSaveMode: SaveMode | null = null
  let pendingSaveDocument: ResumeDocument | null = null

  function toggleModule(key: string) {
    const mod = modules.find((module) => module.key === key)
    if (mod) mod.visible = !mod.visible
  }

  function setTemplate(key: ResumeTemplateKey) {
    selectedTemplateKey.value = key
  }

  function canMoveModule(key: string, direction: MoveDirection): boolean {
    if (key === 'basicInfo') return false
    const index = modules.findIndex((module) => module.key === key)
    if (index < 0 || !modules[index]?.visible) return false
    return direction === 'up' ? index > 1 : index < modules.length - 1
  }

  function moveModule(key: string, direction: MoveDirection) {
    if (!canMoveModule(key, direction)) return
    const index = modules.findIndex((module) => module.key === key)
    const target = direction === 'up' ? index - 1 : index + 1
    const current = modules[index]
    const next = modules[target]
    if (!current || !next) return
    modules[index] = next
    modules[target] = current
  }

  function reorderModule(sourceKey: string, targetKey: string) {
    if (sourceKey === targetKey || sourceKey === 'basicInfo') return
    const sourceIndex = modules.findIndex((module) => module.key === sourceKey)
    const targetIndex = modules.findIndex((module) => module.key === targetKey)
    if (sourceIndex < 0 || targetIndex < 0) return
    const [sourceModule] = modules.splice(sourceIndex, 1)
    if (!sourceModule) return
    let nextIndex = targetKey === 'basicInfo' ? 1 : targetIndex
    if (sourceIndex < targetIndex) nextIndex -= 1
    modules.splice(Math.max(1, Math.min(nextIndex, modules.length)), 0, sourceModule)
  }

  function isDefaultModuleOrder(): boolean {
    return modules.every((module, index) => module.key === DEFAULT_MODULE_ORDER[index])
  }

  function resetModuleOrder() {
    const indexMap = new Map<string, number>()
    DEFAULT_MODULE_ORDER.forEach((key, index) => indexMap.set(key, index))
    const sorted = [...modules].sort((left, right) => {
      const leftIndex = indexMap.get(left.key) ?? Number.MAX_SAFE_INTEGER
      const rightIndex = indexMap.get(right.key) ?? Number.MAX_SAFE_INTEGER
      return leftIndex - rightIndex
    })
    modules.splice(0, modules.length, ...sorted)
  }

  function isModuleVisible(key: string): boolean {
    return modules.find((module) => module.key === key)?.visible ?? false
  }

  function addEducation() {
    educationList.push(createDefaultEducation())
  }

  function removeEducation(id: string) {
    const index = educationList.findIndex((entry) => entry.id === id)
    if (index > -1) educationList.splice(index, 1)
  }

  function addWork() {
    workList.push(createDefaultWork())
  }

  function removeWork(id: string) {
    const index = workList.findIndex((entry) => entry.id === id)
    if (index > -1) workList.splice(index, 1)
  }

  function addProject() {
    projectList.push(createDefaultProject())
  }

  function removeProject(id: string) {
    const index = projectList.findIndex((entry) => entry.id === id)
    if (index > -1) projectList.splice(index, 1)
  }

  function canMoveProject(id: string, direction: MoveDirection): boolean {
    const index = projectList.findIndex((entry) => entry.id === id)
    if (index < 0) return false
    return direction === 'up' ? index > 0 : index < projectList.length - 1
  }

  function moveProject(id: string, direction: MoveDirection) {
    if (!canMoveProject(id, direction)) return
    const index = projectList.findIndex((entry) => entry.id === id)
    const target = direction === 'up' ? index - 1 : index + 1
    const current = projectList[index]
    const next = projectList[target]
    if (!current || !next) return
    projectList[index] = next
    projectList[target] = current
  }

  function addAward() {
    awardList.push({ id: genId(), name: '', date: '', description: '' })
  }

  function removeAward(id: string) {
    const index = awardList.findIndex((entry) => entry.id === id)
    if (index > -1) awardList.splice(index, 1)
  }

  function toResumeDocument(): ResumeDocument {
    return {
      modules: modules.map((module) => ({ ...module })),
      selectedTemplateKey: selectedTemplateKey.value,
      basicInfo: { ...basicInfo },
      educationList: educationList.map((entry) => ({ ...entry })),
      skills: skills.value,
      workList: workList.map((entry) => ({ ...entry })),
      projectList: projectList.map((entry) => ({ ...entry })),
      awardList: awardList.map((entry) => ({ ...entry })),
      selfIntro: selfIntro.value,
    }
  }

  function exportResumeData(): string {
    return JSON.stringify(toResumeDocument(), null, 2)
  }

  function normalizeModules(value: unknown): ModuleConfig[] {
    const rawModules = Array.isArray(value) ? value : []
    const byKey = new Map<string, Partial<ModuleConfig>>()
    rawModules.forEach((item) => {
      if (!isRecord(item)) return
      const key = String(item.key ?? '').trim()
      if (key) byKey.set(key, item)
    })
    const orderedKeys = [
      'basicInfo',
      ...rawModules
        .map((item) => isRecord(item) ? String(item.key ?? '').trim() : '')
        .filter((key) => key && key !== 'basicInfo'),
      ...DEFAULT_MODULE_ORDER,
    ]
    const seen = new Set<string>()
    const normalized: ModuleConfig[] = []
    orderedKeys.forEach((key) => {
      if (seen.has(key)) return
      const fallback = DEFAULT_MODULES.find((module) => module.key === key)
      if (!fallback) return
      seen.add(key)
      const raw = byKey.get(key)
      normalized.push({
        ...fallback,
        label: typeof raw?.label === 'string' && raw.label.trim() ? raw.label : fallback.label,
        icon: typeof raw?.icon === 'string' ? raw.icon : fallback.icon,
        visible: typeof raw?.visible === 'boolean' ? raw.visible : fallback.visible,
      })
    })
    return normalized
  }

  function normalizeEntryList<T extends { id: string }>(value: unknown, fallback: () => T, allowEmpty = false): T[] {
    const entries = Array.isArray(value)
      ? value.filter(isRecord).map((entry) => ({ ...entry, id: String(entry.id ?? '').trim() || genId() } as T))
      : []
    if (entries.length > 0 || allowEmpty) return entries
    return [fallback()]
  }

  function normalizeDocument(value: unknown): ResumeDocument {
    const source = isRecord(value) ? value : {}
    const empty = createEmptyResumeDocument()
    return {
      modules: normalizeModules(source.modules),
      selectedTemplateKey: normalizeResumeTemplateKey(source.selectedTemplateKey ?? source.selectedTemplateId),
      basicInfo: { ...empty.basicInfo, ...(isRecord(source.basicInfo) ? source.basicInfo : {}) } as BasicInfo,
      educationList: normalizeEntryList<EducationEntry>(source.educationList, createDefaultEducation),
      skills: typeof source.skills === 'string' ? source.skills : '',
      workList: normalizeEntryList<WorkEntry>(source.workList, createDefaultWork),
      projectList: normalizeEntryList<ProjectEntry>(source.projectList, createDefaultProject),
      awardList: normalizeEntryList<AwardEntry>(source.awardList, () => ({
        id: genId(),
        name: '',
        date: '',
        description: '',
      }), true),
      selfIntro: typeof source.selfIntro === 'string' ? source.selfIntro : '',
    }
  }

  function applyDocument(value: unknown) {
    const document = normalizeDocument(value)
    suppressAutoSave = true
    modules.splice(0, modules.length, ...document.modules)
    Object.assign(basicInfo, createDefaultBasicInfo(), document.basicInfo)
    educationList.splice(0, educationList.length, ...document.educationList)
    skills.value = document.skills
    workList.splice(0, workList.length, ...document.workList)
    projectList.splice(0, projectList.length, ...document.projectList)
    awardList.splice(0, awardList.length, ...document.awardList)
    selfIntro.value = document.selfIntro
    selectedTemplateKey.value = document.selectedTemplateKey
    documentVersion.value += 1
    queueMicrotask(() => {
      suppressAutoSave = false
    })
  }

  function markSavingState() {
    isSaving.value = true
    if (saveLoadingTimer) clearTimeout(saveLoadingTimer)
    saveLoadingTimer = setTimeout(() => {
      if (!pendingSaveMode) isSaving.value = false
      saveLoadingTimer = null
    }, SAVE_LOADING_MIN_MS)
  }

  function mergeResumeSummary(resume: StoredResume) {
    const summary: ResumeSummary = {
      resumeId: resume.resumeId,
      name: resume.name,
      active: resume.active,
      createdAt: resume.createdAt,
      updatedAt: resume.updatedAt,
    }
    const index = resumeList.value.findIndex((item) => item.resumeId === summary.resumeId)
    if (index >= 0) resumeList.value.splice(index, 1, summary)
    else resumeList.value.unshift(summary)
    if (summary.active) {
      resumeList.value = resumeList.value.map((item) => ({
        ...item,
        active: item.resumeId === summary.resumeId,
      }))
    }
  }

  async function refreshResumeList(): Promise<ResumeSummary[]> {
    resumeList.value = await listStoredResumes()
    return resumeList.value
  }

  function readLegacyDocument(): ResumeDocument | null {
    if (typeof window === 'undefined') return null
    try {
      const raw = window.localStorage.getItem(LEGACY_STORAGE_KEY)
      if (!raw) return null
      return normalizeDocument(JSON.parse(raw))
    } catch {
      return null
    }
  }

  function clearLegacyDocument() {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.removeItem(LEGACY_STORAGE_KEY)
    } catch {
      // 旧缓存清理失败不会改变 MySQL 已成为唯一事实源的行为。
    }
  }

  async function initializeResumes() {
    if (isInitialized.value || isLoading.value) return
    isLoading.value = true
    saveError.value = ''
    try {
      let summaries = await refreshResumeList()
      if (summaries.length === 0) {
        const legacyDocument = readLegacyDocument()
        const created = await createStoredResume(
          legacyDocument ? '我的简历' : '我的简历',
          legacyDocument ?? createEmptyResumeDocument(),
        )
        await activateStoredResume(created.resumeId)
        clearLegacyDocument()
        summaries = await refreshResumeList()
      }
      const active = summaries.find((item) => item.active) ?? summaries[0]
      if (!active) throw new Error('当前账号没有可用简历')
      const resume = active.active ? await loadStoredResume(active.resumeId) : await activateStoredResume(active.resumeId)
      currentResumeId.value = resume.resumeId
      currentResumeName.value = resume.name
      applyDocument(resume.data)
      mergeResumeSummary({ ...resume, active: true })
      lastSavedAt.value = resume.updatedAt ? Date.parse(resume.updatedAt) || Date.now() : Date.now()
      lastSaveMode.value = 'auto'
      clearLegacyDocument()
      isInitialized.value = true
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : '简历加载失败'
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function performSave() {
    while (pendingSaveMode && pendingSaveDocument) {
      const mode = pendingSaveMode
      const document = pendingSaveDocument
      pendingSaveMode = null
      pendingSaveDocument = null
      const resumeId = currentResumeId.value
      if (!resumeId) continue
      markSavingState()
      try {
        const saved = await updateStoredResume(resumeId, currentResumeName.value, document)
        mergeResumeSummary(saved)
        nextAutoSaveAt.value = null
        lastSavedAt.value = Date.now()
        lastSaveMode.value = mode
        saveError.value = ''
      } catch (error) {
        saveError.value = error instanceof Error ? error.message : '简历保存失败'
        throw error
      }
    }
    if (!saveLoadingTimer) isSaving.value = false
    else {
      clearTimeout(saveLoadingTimer)
      saveLoadingTimer = setTimeout(() => {
        isSaving.value = false
        saveLoadingTimer = null
      }, SAVE_LOADING_MIN_MS)
    }
  }

  function saveToStorage(mode: SaveMode = 'manual'): Promise<void> {
    if (!isInitialized.value || !currentResumeId.value) return Promise.resolve()
    if (mode === 'manual' && saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    pendingSaveDocument = toResumeDocument()
    if (mode === 'manual' || pendingSaveMode !== 'manual') pendingSaveMode = mode
    nextAutoSaveAt.value = null
    saveQueue = saveQueue.catch(() => undefined).then(performSave)
    return saveQueue
  }

  async function importResumeData(raw: string) {
    const parsed = JSON.parse(raw) as unknown
    applyDocument(parsed)
    await saveToStorage('manual')
  }

  async function switchResume(resumeId: string) {
    if (!resumeId || resumeId === currentResumeId.value || isManaging.value) return
    isManaging.value = true
    saveError.value = ''
    try {
      if (currentResumeId.value) await saveToStorage('manual')
      const activated = await activateStoredResume(resumeId)
      currentResumeId.value = activated.resumeId
      currentResumeName.value = activated.name
      applyDocument(activated.data)
      mergeResumeSummary(activated)
      await refreshResumeList()
      lastSavedAt.value = activated.updatedAt ? Date.parse(activated.updatedAt) || Date.now() : Date.now()
      lastSaveMode.value = 'auto'
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : '简历切换失败'
      throw error
    } finally {
      isManaging.value = false
    }
  }

  async function createResume(name: string) {
    isManaging.value = true
    try {
      if (currentResumeId.value) await saveToStorage('manual')
      const created = await createStoredResume(name, createEmptyResumeDocument())
      const activated = await activateStoredResume(created.resumeId)
      currentResumeId.value = activated.resumeId
      currentResumeName.value = activated.name
      applyDocument(activated.data)
      await refreshResumeList()
      saveError.value = ''
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : '简历创建失败'
      throw error
    } finally {
      isManaging.value = false
    }
  }

  async function renameCurrentResume(name: string) {
    const resumeId = currentResumeId.value
    if (!resumeId) return
    const safeName = name.trim()
    if (!safeName) throw new Error('简历名称不能为空')
    isManaging.value = true
    try {
      await saveToStorage('manual')
      const saved = await updateStoredResume(resumeId, safeName, toResumeDocument())
      if (saved.name.trim() !== safeName) throw new Error('简历名称未正确保存，请重试')
      mergeResumeSummary(saved)
      const summaries = await refreshResumeList()
      const renamed = summaries.find((item) => item.resumeId === resumeId)
      if (!renamed || renamed.name.trim() !== safeName) throw new Error('简历名称未正确同步，请重试')
      currentResumeName.value = renamed.name
      lastSavedAt.value = Date.now()
      lastSaveMode.value = 'manual'
      saveError.value = ''
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : '简历重命名失败'
      throw error
    } finally {
      isManaging.value = false
    }
  }

  async function duplicateCurrentResume() {
    const resumeId = currentResumeId.value
    if (!resumeId) return
    isManaging.value = true
    try {
      await saveToStorage('manual')
      const copy = await duplicateStoredResume(resumeId)
      const activated = await activateStoredResume(copy.resumeId)
      currentResumeId.value = activated.resumeId
      currentResumeName.value = activated.name
      applyDocument(activated.data)
      await refreshResumeList()
      saveError.value = ''
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : '简历复制失败'
      throw error
    } finally {
      isManaging.value = false
    }
  }

  async function deleteCurrentResume() {
    const resumeId = currentResumeId.value
    if (!resumeId) return
    isManaging.value = true
    try {
      await saveToStorage('manual')
      await removeStoredResume(resumeId)
      const summaries = await refreshResumeList()
      const active = summaries.find((item) => item.active) ?? summaries[0]
      if (!active) throw new Error('当前账号没有可用简历')
      const resume = active.active ? await loadStoredResume(active.resumeId) : await activateStoredResume(active.resumeId)
      currentResumeId.value = resume.resumeId
      currentResumeName.value = resume.name
      applyDocument(resume.data)
      saveError.value = ''
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : '简历删除失败'
      throw error
    } finally {
      isManaging.value = false
    }
  }

  function resetForLogout() {
    if (saveTimer) clearTimeout(saveTimer)
    if (saveLoadingTimer) clearTimeout(saveLoadingTimer)
    saveTimer = null
    saveLoadingTimer = null
    pendingSaveMode = null
    pendingSaveDocument = null
    suppressAutoSave = true
    resumeList.value = []
    currentResumeId.value = null
    currentResumeName.value = '我的简历'
    isInitialized.value = false
    isLoading.value = false
    isManaging.value = false
    nextAutoSaveAt.value = null
    lastSavedAt.value = null
    lastSaveMode.value = null
    isSaving.value = false
    saveError.value = ''
    applyDocument(createEmptyResumeDocument())
  }

  watch(
    [
      () => JSON.stringify(basicInfo),
      () => JSON.stringify(educationList),
      skills,
      () => JSON.stringify(workList),
      () => JSON.stringify(projectList),
      () => JSON.stringify(awardList),
      selfIntro,
      selectedTemplateKey,
      () => JSON.stringify(modules),
      documentVersion,
    ],
    () => {
      if (suppressAutoSave || !isInitialized.value || !currentResumeId.value) return
      if (saveTimer) clearTimeout(saveTimer)
      nextAutoSaveAt.value = Date.now() + AUTO_SAVE_DELAY_MS
      saveTimer = setTimeout(() => {
        saveTimer = null
        void saveToStorage('auto').catch(() => undefined)
      }, AUTO_SAVE_DELAY_MS)
    },
    { deep: true },
  )

  return {
    modules,
    selectedTemplateKey,
    basicInfo,
    educationList,
    skills,
    workList,
    projectList,
    awardList,
    selfIntro,
    resumeList,
    currentResumeId,
    currentResumeName,
    isInitialized,
    isLoading,
    isManaging,
    saveError,
    initializeResumes,
    refreshResumeList,
    switchResume,
    createResume,
    renameCurrentResume,
    duplicateCurrentResume,
    deleteCurrentResume,
    resetForLogout,
    toggleModule,
    setTemplate,
    canMoveModule,
    moveModule,
    reorderModule,
    isDefaultModuleOrder,
    resetModuleOrder,
    isModuleVisible,
    addEducation,
    removeEducation,
    addWork,
    removeWork,
    addProject,
    removeProject,
    canMoveProject,
    moveProject,
    addAward,
    removeAward,
    exportResumeData,
    importResumeData,
    saveToStorage,
    autoSaveDelayMs: AUTO_SAVE_DELAY_MS,
    nextAutoSaveAt,
    lastSavedAt,
    lastSaveMode,
    isSaving,
  }
})
