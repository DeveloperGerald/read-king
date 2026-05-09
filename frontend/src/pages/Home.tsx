import { useMemo, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { UploadCloud, BookOpen, FileText, RefreshCw, ChevronLeft } from 'lucide-react'
import { Card, CardDesc, CardTitle } from '@/components/ui/Card'
import { Textarea } from '@/components/ui/Textarea'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { uploadBook, getBooks, type UploadBookResponse, type BookMetaItem } from '@/utils/api'
import { addBook, loadBooks, loadDraft, saveDraft, loadReports } from '@/utils/storage'

export default function Home() {
  const nav = useNavigate()
  const [draft, setDraft] = useState(() => loadDraft())
  const [confirmed, setConfirmed] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [remoteBooks, setRemoteBooks] = useState<BookMetaItem[]>([])
  const [syncing, setSyncing] = useState(false)

  const localBooks = useMemo(() => loadBooks(), [])
  const reports = useMemo(() => loadReports(), [])

  // 合并本地缓存与后端扫描到的书籍，去重并排序
  const books = useMemo(() => {
    const map = new Map<string, { book_id: string; title: string; filename: string; created_at: number | string }>()
    // 先放本地的
    localBooks.forEach((b) => {
      map.set(b.book_id, {
        book_id: b.book_id,
        title: b.title || '',
        filename: b.filename,
        created_at: b.created_at,
      })
    })
    // 后端的覆盖本地的（后端有 title/author/original_filename 信息）
    remoteBooks.forEach((b) => {
      map.set(b.book_id, {
        book_id: b.book_id,
        title: b.title || '',
        filename: b.original_filename || b.book_id,
        created_at: b.created_at || 0,
      })
    })
    return Array.from(map.values()).sort((a, b) => {
      const ta = typeof a.created_at === 'string' ? new Date(a.created_at).getTime() : a.created_at
      const tb = typeof b.created_at === 'string' ? new Date(b.created_at).getTime() : b.created_at
      return tb - ta
    })
  }, [localBooks, remoteBooks])

  async function fetchRemoteBooks() {
    setSyncing(true)
    try {
      const res = await getBooks()
      setRemoteBooks(res.items)
    } catch (e) {
      console.error('failed to sync books:', e)
    } finally {
      setSyncing(false)
    }
  }

  useEffect(() => {
    fetchRemoteBooks()
  }, [])

  async function onUpload() {
    if (!file) return
    setError(null)
    setUploading(true)
    try {
      const res: UploadBookResponse = await uploadBook(file, title, author)
      addBook({
        book_id: res.book_id,
        filename: res.original_filename || res.stored_filename,
        title: title || undefined,
        author: author || undefined,
        created_at: Date.now(),
      })
      nav(`/books/${res.book_id}`, { state: { draft } })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="text-2xl font-semibold tracking-tight">ReadKing</div>
            <div className="mt-1 text-sm text-zinc-400">先写需求，再上传，上传后自动建索引并支持预览与生成。</div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="border-zinc-700 bg-zinc-900/60 text-zinc-200">Backend: /api</Badge>
          </div>
        </div>

        <div className="mt-8 flex justify-center">
          {!confirmed ? (
            <Card className="w-full max-w-2xl">
              <CardTitle>1) 填写书籍信息与生成需求</CardTitle>
              <CardDesc>书名为必填项；需求建议写你想要的结构、风格与重点。</CardDesc>
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="mb-1 text-xs text-zinc-400">书名 (必填)</div>
                    <Input
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="例如：DeepSeek 技术报告"
                    />
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-zinc-400">作者 (可选)</div>
                    <Input
                      value={author}
                      onChange={(e) => setAuthor(e.target.value)}
                      placeholder="作者"
                    />
                  </div>
                </div>
                <div>
                  <div className="mb-1 text-xs text-zinc-400">生成需求</div>
                  <Textarea
                    value={draft.user_requirements}
                    onChange={(e) => setDraft({ ...draft, user_requirements: e.target.value })}
                    placeholder="例如：按章节梳理核心观点，给出行动清单…"
                  />
                </div>
                <div>
                  <div className="mb-1 text-xs text-zinc-400">读后感 / 个人理解</div>
                  <Textarea
                    value={draft.user_feelings}
                    onChange={(e) => setDraft({ ...draft, user_feelings: e.target.value })}
                    placeholder="例如：我在工作中常遇到问题界定不清…"
                  />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <Button
                    variant="primary"
                    disabled={!title.trim()}
                    onClick={() => {
                      saveDraft(draft)
                      setConfirmed(true)
                    }}
                  >
                    保存并进入上传
                  </Button>
                  {!title.trim() ? (
                    <span className="text-xs text-red-400/80">请先填写书名</span>
                  ) : (
                    <span className="text-xs text-zinc-500">保存后会缓存到本地浏览器</span>
                  )}
                </div>
              </div>
            </Card>
          ) : (
            <Card className="w-full max-w-2xl">
              <div className="mb-4">
                <Button
                  variant="ghost"
                  size="sm"
                  className="-ml-2 h-8 text-zinc-400 hover:text-zinc-100"
                  onClick={() => setConfirmed(false)}
                >
                  <ChevronLeft className="mr-1 h-4 w-4" /> 返回修改需求
                </Button>
              </div>
              <CardTitle>2) 上传书籍文件</CardTitle>
              <CardDesc>
                正在为 <span className="text-zinc-100 font-medium">“{title}”</span> 上传文件。
                支持 PDF/TXT。
              </CardDesc>
              <div className="mt-4 space-y-4">
                <div>
                  <div className="mb-1 text-xs text-zinc-400">选择文件</div>
                  <Input
                    type="file"
                    aria-label="book file"
                    disabled={uploading}
                    accept=".pdf,.txt"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <Button onClick={onUpload} disabled={uploading || !file} className="w-full">
                    {uploading ? (
                      <span className="inline-flex items-center gap-2">
                        <Spinner /> 上传中...
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-2">
                        <UploadCloud className="h-4 w-4" /> 开始上传并建索引
                      </span>
                    )}
                  </Button>
                </div>
                {error ? (
                  <div className="rounded-md border border-red-900/50 bg-red-950/30 p-3 text-sm text-red-200">
                    {error}
                  </div>
                ) : null}
              </div>
            </Card>
          )}
        </div>

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardTitle>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2">
                  <BookOpen className="h-4 w-4" /> 最近书籍
                </span>
                <button
                  onClick={fetchRemoteBooks}
                  disabled={syncing}
                  className="rounded p-1 hover:bg-zinc-800 disabled:opacity-50"
                  title="同步后端数据"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </CardTitle>
            <div className="mt-3 space-y-2">
              {books.length === 0 ? <div className="text-sm text-zinc-500">暂无</div> : null}
              {books.map((b) => (
                <button
                  key={b.book_id}
                  onClick={() => nav(`/books/${b.book_id}`, { state: { draft } })}
                  className="flex w-full items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-left hover:bg-zinc-900"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm text-zinc-100">{b.title || b.filename}</div>
                    <div className="flex items-center gap-2 truncate text-xs text-zinc-500">
                      {b.title ? <span className="truncate">{b.filename}</span> : null}
                      {b.title ? <span>•</span> : null}
                      <span className="shrink-0 font-mono">{b.book_id.slice(0, 8)}</span>
                    </div>
                  </div>
                  <Badge className="shrink-0">打开</Badge>
                </button>
              ))}
            </div>
          </Card>
          <Card>
            <CardTitle>
              <span className="inline-flex items-center gap-2">
                <FileText className="h-4 w-4" /> 最近报告
              </span>
            </CardTitle>
            <div className="mt-3 space-y-2">
              {reports.length === 0 ? <div className="text-sm text-zinc-500">暂无</div> : null}
              {reports.map((r) => (
                <button
                  key={r.book_id}
                  onClick={() => nav(`/reports/${r.book_id}`, { state: { draft } })}
                  className="flex w-full items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-left hover:bg-zinc-900"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm text-zinc-100">{r.title || r.filename || `ID: ${r.book_id.slice(0, 8)}`}</div>
                    <div className="flex items-center gap-2 truncate text-xs text-zinc-500">
                      {r.title ? <span className="truncate">{r.filename}</span> : null}
                      {r.title ? <span>•</span> : null}
                      <span className="shrink-0">点击查看报告</span>
                    </div>
                  </div>
                  <Badge className="shrink-0">打开</Badge>
                </button>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
