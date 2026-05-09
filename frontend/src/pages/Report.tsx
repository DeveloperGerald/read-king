import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Copy, Download, RefreshCw } from 'lucide-react'
import { Card, CardDesc, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { Tabs } from '@/components/ui/Tabs'
import { MarkdownView } from '@/components/MarkdownView'
import { getOutlineMarkdown, getReportMarkdown, getReportStatus, getBookMeta, regenerateReport } from '@/utils/api'
import { downloadTextFile } from '@/utils/download'
import { loadDraft } from '@/utils/storage'
import { useInterval } from '@/hooks/useInterval'

type RouteState = { draft?: { user_requirements: string; user_feelings: string } }

function statusColor(status: string) {
  if (status === 'completed') return 'border-emerald-800 bg-emerald-950/40 text-emerald-200'
  if (status === 'failed') return 'border-red-900 bg-red-950/30 text-red-200'
  if (status === 'generating') return 'border-blue-900 bg-blue-950/30 text-blue-200'
  return 'border-zinc-800 bg-zinc-900 text-zinc-200'
}

export default function Report() {
  const { bookId } = useParams()
  const nav = useNavigate()
  const location = useLocation()
  const state = (location.state || {}) as RouteState
  const _draft = useMemo(() => state.draft ?? loadDraft(), [state.draft])

  const [status, setStatus] = useState<{
    status: string
    updated_at?: string
    error?: string | null
    report_path?: string | null
    outline_path?: string | null
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
      const jobs: PromiseSettledResult<string>[] = []
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
      await regenerateReport(bookId, {
        user_requirements: _draft.user_requirements || '',
        user_feelings: _draft.user_feelings || '',
      })
      await refresh()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setStatus({ status: 'failed', error: e instanceof Error ? e.message : String(e) })
    } finally {
      setRegenerating(false)
    }
  }, [bookId, _draft.user_feelings, _draft.user_requirements, refresh])

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="text-sm text-zinc-400">报告</div>
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
              <Badge className={statusColor(status?.status || 'unknown')}>
                {status?.status === 'generating' ? (
                  <span className="inline-flex items-center gap-1.5">
                    <Spinner className="h-3 w-3" /> 报告生成中...
                  </span>
                ) : (
                  status?.status || 'unknown'
                )}
              </Badge>
              {status?.error ? <Badge className="border-red-900 bg-red-950/30 text-red-200">{status.error}</Badge> : null}
            </div>
          </div>
          <div className="flex items-center gap-2">
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
            <div className="mt-4 h-[620px] overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              {outline ? <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-zinc-200">{outline}</pre> : <div className="text-sm text-zinc-500">暂无</div>}
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
              {processing ? <Badge className="border-blue-900 bg-blue-950/30 text-blue-200">生成中…</Badge> : null}
            </div>

            {err ? <div className="mt-4 rounded-md border border-red-900/50 bg-red-950/30 p-3 text-sm text-red-200">{err}</div> : null}
            <div className="mt-4 h-[620px] overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-5">
              {!markdown && processing ? <div className="text-sm text-zinc-500">等待生成完成…</div> : null}
              {!markdown && !processing ? <div className="text-sm text-zinc-500">暂无内容</div> : null}
              {markdown && tab === 'raw' ? (
                <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-zinc-200">{markdown}</pre>
              ) : null}
              {markdown && tab === 'render' ? <MarkdownView markdown={markdown} /> : null}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
