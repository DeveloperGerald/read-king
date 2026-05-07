import { cn } from '@/lib/utils'

export type TabItem = {
  key: string
  label: string
}

export function Tabs({ items, value, onChange }: { items: TabItem[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="inline-flex rounded-lg border border-zinc-800 bg-zinc-950 p-1">
      {items.map((it) => {
        const active = it.key === value
        return (
          <button
            key={it.key}
            onClick={() => onChange(it.key)}
            className={cn(
              'h-9 rounded-md px-3 text-sm transition-colors',
              active ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200'
            )}
          >
            {it.label}
          </button>
        )
      })}
    </div>
  )
}

