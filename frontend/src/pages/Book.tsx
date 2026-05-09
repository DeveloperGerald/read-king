import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { FileText, RefreshCw, Wand2 } from 'lucide-react'
import { Card, CardDesc, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { Tabs } from '@/components/ui/Tabs'
import {
  type GenerateReportRequest,
  getIndexStatus,
  getBookMeta,
  previewContext,
  previewPrompt,
  generateOutline,
  startIndex,
  regenerateReport,
  startReport,
} from '@/utils/api'
import { addReport, loadDraft } from '@/utils/storage'
import { useInterval } from '@/hooks/useInterval'

type RouteState = {
  draft?: GenerateReportRequest
}

function statusColor(status: string) {
  if (status === 'completed') return 'border-emerald-800 bg-emerald-950/40 text-emerald-200'
  if (status === 'failed') return 'border-red-900 bg-red-950/30 text-red-200'
  if (status === 'indexing' || status === 'processing') return 'border-blue-900 bg-blue-950/30 text-blue-200'
  return 'border-zinc-800 bg-zinc-900 text-zinc-200'
}

export default function Book() {
  const { bookId } = useParams()
  const nav = useNavigate()
  const location = useLocation()
  const state = (location.state || {}) as RouteState
  const draft = useMemo(() => state.draft ?? loadDraft(), [state.draft])

  const [indexStatus, setIndexStatus] = useState<{ status: string; updated_at?: string; error?: string | null } | null>(null)
  const [bookMeta, setBookMeta] = useState<{ title?: string | null; author?: string | null; original_filename?: string | null } | null>(null)
  const [loadingIndex, setLoadingIndex] = useState(false)
  const [tab, setTab] = useState<'context' | 'prompt' | 'outline'>('context')
  const [context, setContext] = useState<string | null>(null)
  const [prompt, setPrompt] = useState<string | null>(null)
  const [outline, setOutline] = useState<string | null>(null)
  const [previewErr, setPreviewErr] = useState<string | null>(null)
  const [busyPreview, setBusyPreview] = useState(false)
  const [reporting, setReporting] = useState(false)

  const canFetchPreview = indexStatus?.status === 'completed'

  const refreshIndex = useCallback(async () => {
    if (!bookId) return
    try {
      const st = await getIndexStatus(bookId)
      setIndexStatus(st)
    } catch (e) {
      setIndexStatus({ status: 'failed', error: e instanceof Error ? e.message : String(e) })
    }
  }, [bookId])

  const ensureIndexStarted = useCallback(async () => {
    if (!bookId) return
    setLoadingIndex(true)
    try {
      const current = await getIndexStatus(bookId)
      setIndexStatus(current)
      if (current.status !== 'completed' && current.status !== 'indexing') {
        const started = await startIndex(bookId)
        setIndexStatus(started)
      }
    } catch {
      try {
        const started = await startIndex(bookId)
        setIndexStatus(started)
      } catch (e2) {
        setIndexStatus({ status: 'failed', error: e2 instanceof Error ? e2.message : String(e2) })
      }
    } finally {
      setLoadingIndex(false)
    }
  }, [bookId])

  const loadTab = useCallback(async (which: typeof tab) => {
    if (!bookId) return
    if (!canFetchPreview) return
    setPreviewErr(null)
    setBusyPreview(true)
    const body: GenerateReportRequest = {
      user_requirements: draft.user_requirements || '',
      user_feelings: draft.user_feelings || '',
    }
    try {
      if (which === 'context') {
        const t = await previewContext(bookId, body)
        setContext(t)
      } else if (which === 'prompt') {
        const t = await previewPrompt(bookId, body)
        setPrompt(t)
      } else {
        const t = await generateOutline(bookId, body)
        setOutline(t)
      }
    } catch (e) {
      setPreviewErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyPreview(false)
    }
  }, [bookId, canFetchPreview, draft.user_feelings, draft.user_requirements])

  const onGenerateReport = useCallback(async () => {
    if (!bookId) return
    setReporting(true)
    try {
      await startReport(bookId, {
        user_requirements: draft.user_requirements || '',
        user_feelings: draft.user_feelings || '',
      })
      addReport({
        book_id: bookId,
        filename: bookMeta?.original_filename || '',
        title: bookMeta?.title || undefined,
        created_at: Date.now(),
      })
      nav(`/reports/${bookId}`, { state: { draft } })
    } catch (e) {
      setPreviewErr(e instanceof Error ? e.message : String(e))
    } finally {
      setReporting(false)
    }
  }, [bookId, draft, nav])

  const onRegenerateReport = useCallback(async () => {
    if (!bookId) return
    if (!window.confirm('确定要重新生成报告吗？这会覆盖已有报告。')) return
    setReporting(true)
    try {
      await regenerateReport(bookId, {
        user_requirements: draft.user_requirements || '',
        user_feelings: draft.user_feelings || '',
      })
      addReport({
        book_id: bookId,
        filename: bookMeta?.original_filename || '',
        title: bookMeta?.title || undefined,
        created_at: Date.now(),
      })
      nav(`/reports/${bookId}`, { state: { draft } })
    } catch (e) {
      setPreviewErr(e instanceof Error ? e.message : String(e))
    } finally {
      setReporting(false)
    }
  }, [bookId, draft, nav])

  useEffect(() => {
    ensureIndexStarted()
    if (bookId) {
      getBookMeta(bookId)
        .then(setBookMeta)
        .catch((e) => console.error('failed to fetch book meta:', e))
    }
  }, [bookId, ensureIndexStarted])

  const isIndexTerminal = indexStatus?.status === 'completed' || indexStatus?.status === 'failed'

  useInterval(
    () => {
      if (bookId) refreshIndex()
    },
    bookId && !isIndexTerminal ? 1200 : null
  )

  useEffect(() => {
    if (!canFetchPreview) return
    if (tab === 'context' && context === null) loadTab('context')
    if (tab === 'prompt' && prompt === null) loadTab('prompt')
  }, [canFetchPreview, context, loadTab, prompt, tab])

  const content = tab === 'context' ? context : tab === 'prompt' ? prompt : outline

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="text-sm text-zinc-400">书籍处理</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-lg font-semibold text-zinc-100">
                {bookMeta?.title || bookMeta?.original_filename || bookId}
              </span>
              {bookMeta?.author ? <span className="text-sm text-zinc-400">by {bookMeta.author}</span> : null}
              {bookMeta?.title && bookMeta?.original_filename ? (
                <span className="text-xs text-zinc-500">({bookMeta.original_filename})</span>
              ) : null}
            </div>
            <div className="mt-1 font-mono text-xs text-zinc-500">{bookId}</div>
            <div className="mt-2 flex items-center gap-2">
              <Badge className={statusColor(indexStatus?.status || 'unknown')}>
                {indexStatus?.status === 'indexing' ? (
                  <span className="inline-flex items-center gap-1.5">
                    <Spinner className="h-3 w-3" /> 索引中...
                  </span>
                ) : (
                  indexStatus?.status || 'unknown'
                )}
              </Badge>
              {indexStatus?.error ? <Badge className="border-red-900 bg-red-950/30 text-red-200">{indexStatus.error}</Badge> : null}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => nav('/')}>
              返回工作台
            </Button>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-1">
            <CardTitle>索引</CardTitle>
            <CardDesc>上传后自动触发。未完成前预览不可用。</CardDesc>
            <div className="mt-4 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Badge className={statusColor(indexStatus?.status || 'unknown')}>
                  {indexStatus?.status === 'indexing' ? (
                    <span className="inline-flex items-center gap-1.5">
                      <Spinner className="h-3 w-3" /> 构建索引中
                    </span>
                  ) : (
                    indexStatus?.status || 'unknown'
                  )}
                </Badge>
                {indexStatus?.error ? <Badge className="border-red-900 bg-red-950/30 text-red-200">{indexStatus.error}</Badge> : null}
              </div>

              <Button onClick={ensureIndexStarted} disabled={!bookId || loadingIndex} size="sm" variant="secondary">
                {loadingIndex ? (
                  <span className="inline-flex items-center gap-2">
                    <Spinner /> 启动中
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2">
                    <RefreshCw className="h-4 w-4" /> 重试建索引
                  </span>
                )}
              </Button>
            </div>
          </Card>

          <Card className="lg:col-span-2">
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>预览</CardTitle>
                <CardDesc>context/prompt 不调用 LLM；outline 会调用 LLM。</CardDesc>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  disabled={!canFetchPreview || reporting}
                  onClick={onGenerateReport}
                >
                  {reporting ? (
                    <span className="inline-flex items-center gap-2">
                      <Spinner /> 生成中
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      <Wand2 className="h-4 w-4" /> 生成报告
                    </span>
                  )}
                </Button>
                <Button variant="secondary" disabled={!canFetchPreview || reporting} onClick={onRegenerateReport}>
                  {reporting ? (
                    <span className="inline-flex items-center gap-2">
                      <Spinner /> 生成中
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      <Wand2 className="h-4 w-4" /> 重新生成
                    </span>
                  )}
                </Button>
                <Button variant="ghost" disabled={!bookId} onClick={() => nav(`/reports/${bookId}`, { state: { draft } })}>
                  <span className="inline-flex items-center gap-2">
                    <FileText className="h-4 w-4" /> 查看报告
                  </span>
                </Button>
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between gap-3">
              <Tabs
                items={[
                  { key: 'context', label: 'Context' },
                  { key: 'prompt', label: 'Prompt' },
                  { key: 'outline', label: 'Outline' },
                ]}
                value={tab}
                onChange={(v) => setTab(v as typeof tab)}
              />
              <Button
                variant="ghost"
                disabled={!canFetchPreview || busyPreview}
                onClick={() => loadTab(tab)}
              >
                {busyPreview ? (
                  <span className="inline-flex items-center gap-2">
                    <Spinner /> 加载中
                  </span>
                ) : (
                  '重新加载'
                )}
              </Button>
            </div>

            {previewErr ? <div className="mt-4 rounded-md border border-red-900/50 bg-red-950/30 p-3 text-sm text-red-200">{previewErr}</div> : null}
            {!canFetchPreview ? (
              <div className="mt-4 rounded-md border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-500">索引完成后才能预览。</div>
            ) : null}
            <div className="mt-4 h-[520px] overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              {busyPreview && !content ? <div className="text-sm text-zinc-500">加载中…</div> : null}
              {!busyPreview && !content ? <div className="text-sm text-zinc-500">暂无内容</div> : null}
              {content ? <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-zinc-200">{content}</pre> : null}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
