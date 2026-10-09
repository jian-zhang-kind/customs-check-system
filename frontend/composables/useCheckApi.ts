import axios, { type AxiosError } from "axios"
import type {
  ApiEnvelope,
  CaseCreateBody,
  CaseInfo,
  CaseStatus,
  DocumentInfo,
  DocType,
  HypergraphSnapshot,
  LoadDemoData,
  PageData,
  PhotoInfo,
  PhotoKind,
  ReportSummary,
  RiskItem,
  RunData,
} from "~/types/api"

const DEMO_STORAGE_KEY = "customs-load-demo"

export function useCheckApi() {
  const config = useRuntimeConfig()
  const http = axios.create({
    baseURL: config.public.apiBase,
    timeout: 60000,
  })

  async function loadDemo(): Promise<LoadDemoData> {
    const response = await http.post<ApiEnvelope<LoadDemoData>>("/cases/load-demo")
    return unwrap(response.data)
  }

  async function getCase(caseId: number): Promise<CaseInfo> {
    const response = await http.get<ApiEnvelope<CaseInfo>>(`/cases/${caseId}`)
    return unwrap(response.data)
  }

  async function getReport(caseId: number): Promise<ReportSummary> {
    const response = await http.get<ApiEnvelope<ReportSummary>>(`/cases/${caseId}/report`)
    return unwrap(response.data)
  }

  async function getRiskItems(caseId: number): Promise<PageData<RiskItem>> {
    const response = await http.get<ApiEnvelope<PageData<RiskItem>>>(`/cases/${caseId}/risk-items`, {
      params: { page: 1, page_size: 100 },
    })
    return unwrap(response.data)
  }

  async function getHypergraph(caseId: number): Promise<HypergraphSnapshot> {
    const response = await http.get<ApiEnvelope<HypergraphSnapshot>>(`/cases/${caseId}/hypergraph`)
    return unwrap(response.data)
  }

  async function createCase(body: CaseCreateBody): Promise<CaseInfo> {
    const payload: CaseCreateBody = { case_no: body.case_no.trim() }
    const title = body.title?.trim()
    const destination = body.destination_country?.trim()
    const remark = body.remark?.trim()
    if (title) payload.title = title
    if (destination) payload.destination_country = destination
    if (remark) payload.remark = remark
    const response = await http.post<ApiEnvelope<CaseInfo>>("/cases", payload)
    return unwrap(response.data)
  }

  async function listCases(query: {
    page: number
    page_size: number
    status?: CaseStatus
    is_demo?: boolean
  }): Promise<PageData<CaseInfo>> {
    const response = await http.get<ApiEnvelope<PageData<CaseInfo>>>("/cases", { params: query })
    return unwrap(response.data)
  }

  async function listDocuments(caseId: number): Promise<PageData<DocumentInfo>> {
    const response = await http.get<ApiEnvelope<PageData<DocumentInfo>>>(`/cases/${caseId}/documents`, {
      params: { page: 1, page_size: 100 },
    })
    return unwrap(response.data)
  }

  async function uploadDocument(caseId: number, docType: DocType, file: File): Promise<DocumentInfo> {
    const form = new FormData()
    form.append("doc_type", docType)
    form.append("file", file, file.name)
    const response = await http.post<ApiEnvelope<DocumentInfo>>(`/cases/${caseId}/documents`, form)
    return unwrap(response.data)
  }

  async function listPhotos(caseId: number): Promise<PageData<PhotoInfo>> {
    const response = await http.get<ApiEnvelope<PageData<PhotoInfo>>>(`/cases/${caseId}/photos`, {
      params: { page: 1, page_size: 100 },
    })
    return unwrap(response.data)
  }

  async function uploadPhoto(caseId: number, kind: PhotoKind, file: File): Promise<PhotoInfo> {
    const form = new FormData()
    form.append("kind", kind)
    form.append("file", file, file.name)
    const response = await http.post<ApiEnvelope<PhotoInfo>>(`/cases/${caseId}/photos`, form)
    return unwrap(response.data)
  }

  async function runCase(caseId: number, force = false): Promise<RunData> {
    const response = await http.post<ApiEnvelope<RunData>>(
      `/cases/${caseId}/run`,
      force ? { force: true } : undefined,
    )
    return unwrap(response.data)
  }

  return {
    loadDemo,
    getCase,
    getReport,
    getRiskItems,
    getHypergraph,
    createCase,
    listCases,
    listDocuments,
    uploadDocument,
    listPhotos,
    uploadPhoto,
    runCase,
  }
}

export function saveDemoResult(data: LoadDemoData) {
  if (!import.meta.client) {
    return
  }
  sessionStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(data))
}

export function readDemoResult(caseId: number): LoadDemoData | null {
  if (!import.meta.client) {
    return null
  }
  const raw = sessionStorage.getItem(DEMO_STORAGE_KEY)
  if (!raw) {
    return null
  }
  try {
    const parsed = JSON.parse(raw) as LoadDemoData
    return parsed.case_id === caseId ? parsed : null
  } catch {
    return null
  }
}

export function messageFromError(
  error: unknown,
  serverFallback = "演示生成失败，请重试",
): { status: number | null; text: string } {
  if (!axios.isAxiosError(error)) {
    return { status: null, text: serverFallback }
  }
  const axiosError = error as AxiosError<ApiEnvelope<unknown>>
  if (!axiosError.response) {
    return { status: null, text: "网络异常，请确认本机接口已启动后重试" }
  }
  const status = axiosError.response.status
  const message = axiosError.response.data?.message
  if (status === 400) {
    return { status, text: message || "参数错误" }
  }
  if (status >= 500) {
    return { status, text: serverFallback }
  }
  return { status, text: message || "请求失败" }
}

function unwrap<T>(envelope: ApiEnvelope<T>): T {
  if (envelope.code !== 0 || envelope.data == null) {
    throw new Error(envelope.message || "请求失败")
  }
  return envelope.data
}
