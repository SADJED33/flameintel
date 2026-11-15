"use client";
import { Button, Drawer } from "./ui";
import type { Source } from "@/lib/types";

/** Right-hand glass drawer with the exact retrieved passage behind a [S#] citation. */
export default function SourceDrawer({ source, onClose }: { source: Source | undefined; onClose: () => void }) {
  return (
    <Drawer open={!!source} onClose={onClose} label={source ? `Source ${source.id}` : "Source"}>
      {source && (
        <>
          <div className="flex items-start gap-3 border-b border-white/15 p-4">
            <span className="rounded-full bg-mint px-2.5 py-1 text-sm font-semibold text-black">{source.id}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{source.psi}{source.acronym ? ` · ${source.acronym}` : ""}</p>
              {source.title && <p className="line-clamp-2 text-xs text-ink-mute">{source.title}</p>}
            </div>
            <button onClick={onClose} className="rounded-md p-1.5 text-ink-dim transition-colors hover:bg-white/10 hover:text-white" aria-label="Close source panel" autoFocus>
              <svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg>
            </button>
          </div>
          <dl className="grid grid-cols-[96px_1fr] gap-x-3 gap-y-1.5 border-b border-white/15 px-4 py-3 text-xs">
            <dt className="text-ink-mute">Document type</dt><dd>{source.doc_type}</dd>
            <dt className="text-ink-mute">File</dt><dd className="break-all font-mono text-[11px]">{source.file}</dd>
            <dt className="text-ink-mute">{/^p(age)?\s*\d+/i.test(source.loc) ? "Page" : "Location"}</dt><dd>{source.loc}</dd>
            <dt className="text-ink-mute">Distance</dt>
            <dd><span className="num font-medium">{source.distance.toFixed(3)}</span> <span className="text-ink-mute">retrieval distance, lower = closer to the question</span></dd>
          </dl>
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            <p className="eyebrow mb-2">Exact retrieved passage</p>
            <pre className="whitespace-pre-wrap break-words font-mono text-[12px] leading-relaxed text-ink-dim">{source.text}</pre>
          </div>
          <div className="border-t border-white/15 p-3">
            <Button href={`/investigations/${source.psi}`} size="sm" className="w-full">Open {source.psi} details</Button>
          </div>
        </>
      )}
    </Drawer>
  );
}
