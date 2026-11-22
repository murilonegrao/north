export type Role = 'admin' | 'curator' | 'viewer'
export type Stage = 'totp' | 'change_password' | 'enroll_totp' | 'ok'
export type JobStatus = 'queued' | 'running' | 'succeeded' | 'attention' | 'failed' | 'cancelled'

export interface AdminUser {
  id: number
  username: string
  role: Role
  has_totp: boolean
  disabled: boolean
  must_change_password: boolean
  last_login_at: string | null
  created_at: string
}

export interface SessionState {
  user: AdminUser
  stage: Stage
  csrf: string
}

export interface Job {
  id: number
  kind: string
  title: string
  params: Record<string, unknown>
  status: JobStatus
  error: string | null
  requested_by: string | null
  schedule_id: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  heartbeat_at: string | null
  cancel_requested: boolean
  log_lines: number
}

export interface JobDetail extends Job {
  result: Record<string, unknown>
  logs: { id: number; at: string; line: string }[]
}

export interface JobParam {
  name: string
  kind: 'text' | 'bool'
  default: string | boolean
  help: string
}

export interface JobKind {
  name: string
  title: string
  description: string
  min_role: Role
  allowed: boolean
  params: JobParam[]
}

export interface ScheduleRow {
  id: string
  kind: string
  title: string
  params: Record<string, unknown>
  every_hours: number
  paused: boolean
  next_run_at: string
  last_job_id: number | null
}

export interface StateCounts {
  scope: string
  institutions: number
  institutions_accredited: number
  campuses_sevp_authorized: number
  programs: number
  programs_stem_opt: number
  programs_with_tuition: number
  open_tasks: Record<string, number>
}

export interface CountryOverview {
  total: Record<string, number>
  states: StateCounts[]
  source_files: Record<string, { file_version: string; sha256: string; scopes: number }>
}

export interface Overview {
  countries: Record<string, CountryOverview>
  worker: { connected: boolean; last_heartbeat_at: string | null; last_job_started_at: string | null }
  jobs: Job[]
  jobs_needing_attention: number
  schedules: ScheduleRow[]
}

export interface AuditRow {
  id: number
  at: string
  actor: string
  action: string
  target: string | null
  detail: Record<string, unknown>
  ip: string | null
}
