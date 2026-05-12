import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { FileText, RefreshCw, Wand2, Sun, Moon } from 'lucide-react'
import { Card, CardDesc, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { Tabs } from '@/components/ui/Tabs'
import { useTheme } from '@/hooks/useTheme'
import {
  type GenerateReportRequest,
  getIndexStatus,
  getBookMeta,
  startIndex,
  startReport,
} from '@/utils/api'
import { addReport, loadDraft } from '@/utils/storage'
import { useInterval } from '@/hooks/useInterval'

type RouteState = {
  draft?: GenerateReportRequest
}

function statusColor(status: string) {
  if (status === 'completed') return 'border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
  if (status === 'failed') return 'border-destructive/20 bg-destructive/10 text-destructive'
  if (status === 'indexing' || status === 'processing') return 'border-primary/20 bg-primary/10 text-primary'
  return 'border-border bg-muted text-muted-foreground'
}

export default function Book() {
  const { bookId } = useParams()
  const nav = useNavigate()
  const { isDark, toggleTheme } = useTheme()
  const location = useLocation()
  const state = (location.state || {}) as RouteState
  const draft = useMemo(() => state.draft ?? loadDraft(), [state.draft])

  const [indexStatus, setIndexStatus] = useState<{ status: string; updated_at?: string; error?: string | null } | null>(null)
  const [bookMeta, setBookMeta] = useState<{ title?: string | null; author?: string | null; original_filename?: string | null } | null>(null)
  const [loadingIndex, setLoadingIndex] = useState(false)
  const [previewErr, setPreviewErr] = useState<string | null>(null)

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

  const handleRetryIndex = useCallback(async () => {
    if (!bookId) return
    setLoadingIndex(true)
    try {
      const started = await startIndex(bookId)
      setIndexStatus(started)
    } catch (e) {
      setIndexStatus({ status: 'failed', error: e instanceof Error ? e.message : String(e) })
    } finally {
      setLoadingIndex(false)
    }
  }, [bookId])

  const onGenerateReport = useCallback(() => {
    if (!bookId) return
    nav(`/reports/${bookId}`, { state: { draft } })
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

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="text-sm text-muted-foreground">书籍处理</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-lg font-semibold text-foreground">
                {bookMeta?.title || bookMeta?.original_filename || bookId}
              </span>
              {bookMeta?.author ? <span className="text-sm text-muted-foreground">by {bookMeta.author}</span> : null}
              {bookMeta?.title && bookMeta?.original_filename ? (
                <span className="text-xs text-muted-foreground/60">({bookMeta.original_filename})</span>
              ) : null}
            </div>
            <div className="mt-1 font-mono text-xs text-muted-foreground/50">{bookId}</div>
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
              {indexStatus?.error ? <Badge className="border-destructive/20 bg-destructive/10 text-destructive">{indexStatus.error}</Badge> : null}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleTheme}
              className="h-9 w-9 p-0"
              title={isDark ? '切换到浅色模式' : '切换到深色模式'}
            >
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" onClick={() => nav('/')}>
              返回工作台
            </Button>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="lg:col-span-1">
            <CardTitle>索引状态</CardTitle>
            <CardDesc>上传后自动触发。索引完成后即可生成报告。</CardDesc>
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
                {indexStatus?.error ? <Badge className="border-destructive/20 bg-destructive/10 text-destructive">{indexStatus.error}</Badge> : null}
              </div>

              <Button onClick={handleRetryIndex} disabled={!bookId || loadingIndex} size="sm" variant="secondary">
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

          <Card className="lg:col-span-1">
            <CardTitle>报告操作</CardTitle>
            <CardDesc>点击下方按钮进入 AI 读书报告页面。</CardDesc>
            <div className="mt-6 flex flex-col gap-3">
              <Button
                className="w-full"
                disabled={!canFetchPreview}
                onClick={onGenerateReport}
              >
                <span className="inline-flex items-center gap-2">
                  <Wand2 className="h-4 w-4" /> 进入报告生成页
                </span>
              </Button>
              
              {previewErr ? <div className="mt-2 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">{previewErr}</div> : null}
              {!canFetchPreview ? (
                <div className="mt-2 text-xs text-muted-foreground">提示：索引完成后才能生成报告。</div>
              ) : null}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
