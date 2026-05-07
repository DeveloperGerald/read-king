import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { UploadCloud, BookOpen, FileText } from 'lucide-react'
import { Card, CardDesc, CardTitle } from '@/components/ui/Card'
import { Textarea } from '@/components/ui/Textarea'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { uploadBook, type UploadBookResponse } from '@/utils/api'
import { addBook, loadBooks, loadDraft, saveDraft, loadReports } from '@/utils/storage'

export default function Home() {
  const nav = useNavigate()
  const [draft, setDraft] = useState(() => loadDraft())
  const [confirmed, setConfirmed] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const books = useMemo(() => loadBooks(), [])
  const reports = useMemo(() => loadReports(), [])

  const canUpload = confirmed

  async function onUpload() {
    if (!file) return
    setError(null)
    setUploading(true)
    try {
      const res: UploadBookResponse = await uploadBook(file)
      addBook({ book_id: res.book_id, filename: res.original_filename || res.stored_filename, created_at: Date.now() })
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

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardTitle>1) 填写生成需求</CardTitle>
            <CardDesc>建议写你想要的结构、风格与重点；也可以为空。</CardDesc>
            <div className="mt-4 space-y-3">
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
                  variant={confirmed ? 'secondary' : 'primary'}
                  onClick={() => {
                    saveDraft(draft)
                    setConfirmed(true)
                  }}
                >
                  {confirmed ? '已保存' : '保存并进入上传'}
                </Button>
                <div className="text-xs text-zinc-500">保存后会缓存到本地浏览器</div>
              </div>
            </div>
          </Card>

          <Card>
            <CardTitle>2) 上传书籍（自动建索引）</CardTitle>
            <CardDesc>支持 PDF/TXT（后端当前允许 .pdf/.txt）。</CardDesc>
            <div className="mt-4 space-y-3">
              <Input
                type="file"
                aria-label="book file"
                disabled={!canUpload || uploading}
                accept=".pdf,.txt"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <div className="flex items-center justify-between gap-3">
                <Button onClick={onUpload} disabled={!canUpload || uploading || !file}>
                  {uploading ? (
                    <span className="inline-flex items-center gap-2">
                      <Spinner /> 上传中
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      <UploadCloud className="h-4 w-4" /> 上传并进入处理页
                    </span>
                  )}
                </Button>
                {!canUpload ? <Badge className="text-zinc-400">先保存需求</Badge> : null}
              </div>
              {error ? <div className="rounded-md border border-red-900/50 bg-red-950/30 p-3 text-sm text-red-200">{error}</div> : null}
            </div>
          </Card>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardTitle>
              <span className="inline-flex items-center gap-2">
                <BookOpen className="h-4 w-4" /> 最近书籍
              </span>
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
                    <div className="truncate text-sm text-zinc-100">{b.filename}</div>
                    <div className="truncate text-xs text-zinc-500">{b.book_id}</div>
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
                    <div className="truncate text-sm text-zinc-100">book_id: {r.book_id}</div>
                    <div className="truncate text-xs text-zinc-500">点击查看报告</div>
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
