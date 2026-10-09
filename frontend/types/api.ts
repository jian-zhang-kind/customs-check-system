export type CaseStatus = "pending" | "running" | "completed" | "failed"
export type Verdict = "pass" | "warning" | "fail"
export type RuleOutcome = "matched" | "conflict" | "hard" | "insufficient_evidence"
export type DocType = "declaration" | "invoice" | "packing" | "contract"
export type PhotoKind = "mark" | "packing"

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T | null
}

export interface CaseInfo {
  id: number
  case_no: string
  remark: string | null
  status: CaseStatus
  is_demo: boolean
  demo_type: string | null
  destination_country: string | null
  title: string | null
  created_at: string
  updated_at: string
}

export interface HsRuleView {
  rule_id: string
  verdict: Verdict
  rule_outcome: RuleOutcome
  description?: string | null
  risk_level?: string | null
  regulation_name?: string | null
  publish_date?: string | null
  source_url?: string | null
  excerpt?: string | null
  chunk_id?: string | null
  jurisdiction?: string | null
}

export interface ReportSummary {
  id: number
  case_id: number
  status: CaseStatus
  summary_verdict: Verdict | null
  debate_triggered: boolean
  created_at: string
  hs_cn: HsRuleView | null
  hs_dest: HsRuleView | null
  disclaimer?: string
}

export interface LoadDemoData {
  case_id: number
  case: CaseInfo
  report: ReportSummary
}

export interface RunData {
  case_id: number
  status: CaseStatus
  report: ReportSummary
}

export interface CaseCreateBody {
  case_no: string
  title?: string
  destination_country?: string
  remark?: string
}

export interface DocumentInfo {
  id: number
  case_id: number
  doc_type: DocType
  filename: string
  storage_path: string
  ocr_source: string | null
  created_at: string
}

export interface PhotoInfo {
  id: number
  case_id: number
  kind: PhotoKind
  filename: string
  storage_path: string
  ocr_source: string | null
  created_at: string
}

export interface RiskItem {
  id: number
  case_id: number
  report_id: number
  rule_id: string
  verdict: Verdict
  rule_outcome: RuleOutcome
  risk_level: string | null
  description: string | null
  source_url: string | null
  regulation_name?: string | null
  excerpt?: string | null
  edge_id?: number | null
  chunk_id?: string | null
}

export interface PageData<T> {
  list: T[]
  total: number
  page: number
  page_size: number
}

export interface HyperedgeMember {
  edge_id: number
  node_id: number
  slot_name: string
}

export interface Hyperedge {
  edge_id: number
  case_id: number
  constraint_type: string
  rule_id: string
  members: HyperedgeMember[]
}

export interface HypergraphSnapshot {
  case_id: number
  nodes: Array<{
    node_id: number
    case_id: number
    document_id: number | null
    field_name: string
    field_value: string | null
  }>
  edges: Hyperedge[]
}
