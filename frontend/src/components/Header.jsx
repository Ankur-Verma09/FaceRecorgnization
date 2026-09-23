import React from 'react'
import { Search, ArrowRight, Calendar, ChevronDown, Activity, RotateCcw } from 'lucide-react'

export default function Header({
  title = 'Dashboard',
  subtitle = 'Home > Dashboard',
  searchQuery = '',
  setSearchQuery,
  onResetWorkspace
}) {
  return (
    <header className="w-full glass-card border-b border-slate-800/80 px-8 py-4 flex items-center justify-between sticky top-0 z-20">
      {/* Center Title & Breadcrumbs */}
      <div>
        <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
          {title}
        </h1>
        <p className="text-xs text-slate-400 font-medium">{subtitle}</p>
      </div>

      {/* Right Filters, Reset Workspace & Status Header */}
      <div className="flex items-center gap-4">
        {onResetWorkspace && (
          <button
            onClick={onResetWorkspace}
            title="Clear cache and reset workspace for new photo folder"
            className="px-3 py-1.5 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 hover:bg-rose-900 font-bold text-xs flex items-center gap-1.5 transition-all shadow"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset Workspace
          </button>
        )}

        <div className="flex items-center bg-slate-900/90 rounded-lg p-1 border border-slate-800 text-xs font-semibold">
          <button className="px-3 py-1.5 rounded-md bg-slate-800 text-white shadow">Today</button>
          <button className="px-3 py-1.5 rounded-md text-slate-400 hover:text-white">Yesterday</button>
          <div className="px-3 py-1.5 text-slate-300 flex items-center gap-1.5 border-l border-slate-800 ml-1">
            <Calendar className="w-3.5 h-3.5 text-cyan-400" />
            <span>Sept 23, 2026</span>
          </div>
        </div>

        <div className="flex items-center gap-2 pl-4 border-l border-slate-800">
          <span className="text-sm font-black tracking-widest text-emerald-400 uppercase">Status</span>
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-lg shadow-emerald-400/50" title="Offline AI Engine Active"></span>
        </div>
      </div>
    </header>
  )
}
