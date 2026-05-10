import { cn } from '@/lib/utils'

export type TabItem = {
  key: string
  label: string
}

export function Tabs({ items, value, onChange }: { items: TabItem[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="inline-flex rounded-lg border border-border bg-muted/50 p-1">
      {items.map((it) => {
        const active = it.key === value
        return (
          <button
            key={it.key}
            onClick={() => onChange(it.key)}
            className={cn(
              'h-9 rounded-md px-3 text-sm transition-all',
              active 
                ? 'bg-background text-foreground shadow-sm' 
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            {it.label}
          </button>
        )
      })}
    </div>
  )
}

