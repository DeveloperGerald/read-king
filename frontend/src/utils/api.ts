export type UploadBookResponse = {
  book_id: string
  original_filename: string
  stored_filename: string
  stored_path: string
  content_type: string | null
}

export type IndexStatusResponse = {
  book_id: string
  status: string
  updated_at: string
  total_chars: number | null
  total_chunks: number | null
  error: string | null
}

export type GenerateReportRequest = {
  user_requirements: string
  user_feelings: string
  report_style?: string
}

export type ReportStatusResponse = {
  book_id: string
  status: string
  updated_at: string
  error: string | null
  report_path: string | null
  outline_path: string | null
}

export type BookMetaItem = {
  book_id: string
  title: string | null
  author: string | null
  original_filename: string | null
  created_at: string | null
}

export type BookListResponse = {
  items: BookMetaItem[]
  total: number
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!text) {
    return {} as T
  }
  return JSON.parse(text) as T
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await parseJson<{ detail?: string }>(res)
    if (data && typeof data.detail === 'string' && data.detail.trim()) {
      return data.detail
    }
  } catch {
    void 0
  }
  return `${res.status} ${res.statusText}`
}

export async function uploadBook(file: File, title?: string, author?: string): Promise<UploadBookResponse> {
  const fd = new FormData()
  fd.append('file', file)
  if (title) fd.append('title', title)
  if (author) fd.append('author', author)
  const res = await fetch('/api/upload', {
    method: 'POST',
    body: fd,
  })
  if (!res.ok) throw new Error(await parseError(res))
  return parseJson<UploadBookResponse>(res)
}

export async function getBooks(): Promise<BookListResponse> {
  const res = await fetch('/api/books')
  if (!res.ok) throw new Error(await parseError(res))
  return parseJson<BookListResponse>(res)
}

export async function getBookMeta(bookId: string): Promise<BookMetaItem> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/meta`)
  if (!res.ok) throw new Error(await parseError(res))
  return parseJson<BookMetaItem>(res)
}

export async function startIndex(bookId: string): Promise<IndexStatusResponse> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/index`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(await parseError(res))
  return parseJson<IndexStatusResponse>(res)
}

export async function getIndexStatus(bookId: string): Promise<IndexStatusResponse> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/index/status`)
  if (!res.ok) throw new Error(await parseError(res))
  return parseJson<IndexStatusResponse>(res)
}

/*
export async function previewContext(bookId: string, body: GenerateReportRequest): Promise<string> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/workflow/context`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.text()
}

export async function previewPrompt(bookId: string, body: GenerateReportRequest): Promise<string> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/workflow/prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.text()
}
*/

/*
export async function generateOutline(bookId: string, body: GenerateReportRequest): Promise<string> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/workflow/outline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.text()
}
*/

export async function startReport(bookId: string, body: GenerateReportRequest, force: boolean = false): Promise<ReportStatusResponse> {
  const url = `/api/books/${encodeURIComponent(bookId)}/report${force ? '?force=true' : ''}`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return parseJson<ReportStatusResponse>(res)
}

export async function getReportStatus(bookId: string): Promise<ReportStatusResponse> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/report/status`)
  if (!res.ok) throw new Error(await parseError(res))
  return parseJson<ReportStatusResponse>(res)
}

export async function getReportMarkdown(bookId: string): Promise<string> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/report/file`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.text()
}

export async function getOutlineMarkdown(bookId: string): Promise<string> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/report/outline`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.text()
}

export async function deleteBook(bookId: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await parseError(res))
  return parseJson(res)
}

export async function deleteReport(bookId: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/report`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await parseError(res))
  return parseJson(res)
}
