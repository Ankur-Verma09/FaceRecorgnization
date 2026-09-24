import React from 'react'
import { Search, X, Calendar, Activity, RotateCcw } from 'lucide-react'

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

      {/* Right Filters, Search, Reset Workspace & Status Header */}
      <div className="flex items-center gap-4">
        {/* Functional Search Bar */}
        <div className="relative flex items-center bg-slate-900/90 rounded-lg border border-slate-800 focus-within:border-cyan-500 transition-colors shadow">
          <Search className="w-4 h-4 text-slate-400 ml-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search people, folders..."
            className="bg-transparent border-none text-sm text-slate-200 placeholder-slate-500 px-3 py-1.5 focus:outline-none w-64"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="mr-2 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {onResetWorkspace && (
          <button
            onClick={onResetWorkspace}
            title="Clear cache and reset workspace for new photo folder"
            className="px-3 py-1.5 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 hover:bg-rose-900 font-bold text-xs flex items-center gap-1.5 transition-all shadow"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset Workspace
          </button>
        )}

        <div className="flex items-center gap-2 pl-4 border-l border-slate-800">
          <span className="text-sm font-black tracking-widest text-emerald-400 uppercase">Status</span>
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-lg shadow-emerald-400/50"></span>
            <span className="text-[10px] font-bold text-emerald-300 uppercase tracking-wider">Connected & Ready</span>
          </div>
        </div>
      </div>
    </header>
  )
}
