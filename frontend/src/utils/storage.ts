export type SavedDraft = {
  user_requirements: string
  user_feelings: string
}

export type SavedBook = {
  book_id: string
  filename: string
  created_at: number
}

export type SavedReport = {
  book_id: string
  created_at: number
}

const KEY_DRAFT = 'rk:draft'
const KEY_BOOKS = 'rk:books'
const KEY_REPORTS = 'rk:reports'

export function loadDraft(): SavedDraft {
  try {
    const raw = localStorage.getItem(KEY_DRAFT)
    if (!raw) return { user_requirements: '', user_feelings: '' }
    const data = JSON.parse(raw) as Partial<SavedDraft>
    return {
      user_requirements: typeof data.user_requirements === 'string' ? data.user_requirements : '',
      user_feelings: typeof data.user_feelings === 'string' ? data.user_feelings : '',
    }
  } catch {
    return { user_requirements: '', user_feelings: '' }
  }
}

export function saveDraft(d: SavedDraft) {
  localStorage.setItem(KEY_DRAFT, JSON.stringify(d))
}

export function loadBooks(): SavedBook[] {
  try {
    const raw = localStorage.getItem(KEY_BOOKS)
    if (!raw) return []
    const data = JSON.parse(raw) as SavedBook[]
    if (!Array.isArray(data)) return []
    return data
      .filter((x) => x && typeof x.book_id === 'string')
      .slice(0, 30)
  } catch {
    return []
  }
}

export function addBook(b: SavedBook) {
  const list = loadBooks()
  const next = [b, ...list.filter((x) => x.book_id !== b.book_id)].slice(0, 30)
  localStorage.setItem(KEY_BOOKS, JSON.stringify(next))
}

export function loadReports(): SavedReport[] {
  try {
    const raw = localStorage.getItem(KEY_REPORTS)
    if (!raw) return []
    const data = JSON.parse(raw) as SavedReport[]
    if (!Array.isArray(data)) return []
    return data.filter((x) => x && typeof x.book_id === 'string').slice(0, 30)
  } catch {
    return []
  }
}

export function addReport(r: SavedReport) {
  const list = loadReports()
  const next = [r, ...list.filter((x) => x.book_id !== r.book_id)].slice(0, 30)
  localStorage.setItem(KEY_REPORTS, JSON.stringify(next))
}

