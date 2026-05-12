import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Copy, Download, RefreshCw, Sun, Moon } from 'lucide-react'
import { Card, CardDesc, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { Tabs } from '@/components/ui/Tabs'
import { MarkdownView } from '@/components/MarkdownView'
import { getOutlineMarkdown, getReportMarkdown, getReportStatus, getBookMeta, startReport } from '@/utils/api'
import { downloadTextFile } from '@/utils/download'
import { loadDraft } from '@/utils/storage'
import { useInterval } from '@/hooks/useInterval'
import { useTheme } from '@/hooks/useTheme'

type RouteState = { draft?: { user_requirements: string; user_feelings: string } }

function statusColor(status: string) {
  if (status === 'completed') return 'border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
  if (status === 'failed') return 'border-destructive/20 bg-destructive/10 text-destructive'
  if (status === 'generating') return 'border-primary/20 bg-primary/10 text-primary'
  return 'border-border bg-muted text-muted-foreground'
}

export default function Report() {
  const { bookId } = useParams()
  const nav = useNavigate()
  const { isDark, toggleTheme } = useTheme()
  const location = useLocation()
  const state = (location.state || {}) as RouteState
  const _draft = useMemo(() => state.draft ?? loadDraft(), [state.draft])

  const [status, setStatus] = useState<{
    status: string
    updated_at?: string
    error?: string | null
    report_path?: string | null
    outline_path?: string | null
    current_step?: string | null
    total_steps?: number
    completed_steps?: number
  } | null>(null)
  const [bookMeta, setBookMeta] = useState<{ title?: string | null; author?: string | null; original_filename?: string | null } | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(false)
  const [tab, setTab] = useState<'outline' | 'render' | 'raw'>('render')
  const [outline, setOutline] = useState<string | null>(null)
  const [markdown, setMarkdown] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const processing = status?.status === 'generating'
  const [regenerating, setRegenerating] = useState(false)

  const refresh = useCallback(async () => {
    if (!bookId) return
    setLoadingStatus(true)
    setErr(null)
    try {
      const st = await getReportStatus(bookId)
      setStatus(st)
      const tasks: Array<Promise<string>> = []
      const kinds: Array<'outline' | 'report'> = []

      if (st.outline_path) {
        tasks.push(getOutlineMarkdown(bookId))
        kinds.push('outline')
      }
      if (st.report_path) {
        tasks.push(getReportMarkdown(bookId))
        kinds.push('report')
      }

      if (tasks.length) {
        const results = await Promise.allSettled(tasks)
        results.forEach((r, idx) => {
          const kind = kinds[idx]
          if (r.status === 'fulfilled') {
            if (kind === 'outline') setOutline(r.value)
            if (kind === 'report') setMarkdown(r.value)
          }
        })
      } else {
        setOutline(null)
        setMarkdown(null)
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setStatus({ status: 'failed', error: e instanceof Error ? e.message : String(e) })
    } finally {
      setLoadingStatus(false)
    }
  }, [bookId])

  useEffect(() => {
    refresh()
    if (bookId) {
      getBookMeta(bookId)
        .then(setBookMeta)
        .catch((e) => console.error('failed to fetch book meta:', e))
    }
  }, [bookId, refresh])

  const isTerminal = status?.status === 'completed' || status?.status === 'failed'

  useInterval(() => {
    if (bookId) refresh()
  }, bookId && !isTerminal ? 1500 : null)

  const onRegenerate = useCallback(async () => {
    if (!bookId) return
    if (!window.confirm('确定要重新生成报告吗？这会覆盖已有报告。')) return
    setRegenerating(true)
    setErr(null)
    setOutline(null)
    setMarkdown(null)
    setStatus({ status: 'generating' })
    try {
      await startReport(
        bookId,
        {
          user_requirements: _draft.user_requirements || '',
          user_feelings: _draft.user_feelings || '',
        },
        true
      )
      await refresh()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setStatus({ status: 'failed', error: e instanceof Error ? e.message : String(e) })
    } finally {
      setRegenerating(false)
    }
  }, [bookId, _draft.user_feelings, _draft.user_requirements, refresh])

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="text-sm text-muted-foreground">报告</div>
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
            <div className="mt-2 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Badge className={statusColor(status?.status || 'unknown')}>
                  {status?.status === 'generating' ? (
                    <span className="inline-flex items-center gap-1.5">
                      <Spinner className="h-3 w-3" /> {status.current_step || '报告生成中...'}
                    </span>
                  ) : (
                    status?.status || 'unknown'
                  )}
                </Badge>
                {status?.error ? <Badge className="border-destructive/20 bg-destructive/10 text-destructive">{status.error}</Badge> : null}
              </div>
              {status?.status === 'generating' && status.total_steps ? (
                <div className="flex w-72 flex-col gap-1.5">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-primary/10">
                    <div
                      className="h-full bg-primary transition-all duration-500 ease-out"
                      style={{ width: `${Math.min(100, Math.round(((status.completed_steps || 0) / status.total_steps) * 100))}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] font-medium text-muted-foreground/80">
                    <span>生成进度: {Math.round(((status.completed_steps || 0) / status.total_steps) * 100)}%</span>
                    <span>{status.completed_steps} / {status.total_steps} 阶段</span>
                  </div>
                </div>
              ) : null}
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
            <Button variant="ghost" onClick={() => nav('/')}>返回工作台</Button>
            {bookId ? (
              <Button variant="secondary" onClick={() => nav(`/books/${bookId}`, { state: { draft: _draft } })}>
                返回书籍
              </Button>
            ) : null}
            <Button variant="secondary" onClick={onRegenerate} disabled={!bookId || regenerating || processing}>
              <span className="inline-flex items-center gap-2">
                {regenerating ? <Spinner /> : <RefreshCw className="h-4 w-4" />} 重新生成
              </span>
            </Button>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-1">
            <CardTitle>大纲</CardTitle>
            <CardDesc>即使正文生成失败，也会展示已落盘的 outline。</CardDesc>
            <div className="mt-4 h-[620px] overflow-auto rounded-lg border border-border bg-background p-4 shadow-inner">
              {outline ? <MarkdownView markdown={outline} /> : <div className="text-sm text-muted-foreground">暂无</div>}
            </div>
          </Card>

          <Card className="lg:col-span-2">
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>正文</CardTitle>
                <CardDesc>支持渲染查看、复制与下载。</CardDesc>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  disabled={!markdown}
                  onClick={() => {
                    if (!markdown) return
                    navigator.clipboard.writeText(markdown)
                  }}
                >
                  <span className="inline-flex items-center gap-2">
                    <Copy className="h-4 w-4" /> 复制 Markdown
                  </span>
                </Button>
                <Button
                  variant="secondary"
                  disabled={!markdown}
                  onClick={() => {
                    if (!markdown) return
                    downloadTextFile(`${bookId ?? 'report'}.md`, markdown)
                  }}
                >
                  <span className="inline-flex items-center gap-2">
                    <Download className="h-4 w-4" /> 下载 .md
                  </span>
                </Button>
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between gap-3">
              <Tabs
                items={[
                  { key: 'render', label: '渲染' },
                  { key: 'raw', label: '原文' },
                ]}
                value={tab}
                onChange={(v) => setTab(v as typeof tab)}
              />
              {processing ? <Badge className="border-primary/20 bg-primary/10 text-primary">生成中…</Badge> : null}
            </div>

            {err ? <div className="mt-4 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">{err}</div> : null}
            <div className="mt-4 h-[620px] overflow-auto rounded-lg border border-border bg-background p-5 shadow-inner">
              {!markdown && processing ? <div className="text-sm text-muted-foreground">等待生成完成…</div> : null}
              {!markdown && !processing ? <div className="text-sm text-muted-foreground">暂无内容</div> : null}
              {markdown && tab === 'raw' ? (
                <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-foreground/80">{markdown}</pre>
              ) : null}
              {markdown && tab === 'render' ? <MarkdownView markdown={markdown} /> : null}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
