import React from 'react'
import axios from 'axios'
import { FolderOutput, CheckCircle2, Loader2, X, FolderOpen } from 'lucide-react'

export default function ExportProgressModal({ exportStatus, onClose }) {
  if (!exportStatus || exportStatus.status === 'idle') return null

  const { status, exported_count = 0, total_files = 0, current_file = '', target_dir = '' } = exportStatus
  const isExporting = status === 'exporting'
  const isCompleted = status === 'export_completed'
  
  // When completed, force 100%; during exporting calculate percentage
  const percent = isCompleted ? 100 : (total_files > 0 ? Math.min(100, Math.round((exported_count / total_files) * 100)) : 0)
  const displayExportedCount = isCompleted ? total_files : exported_count

  const handleOpenFolder = async () => {
    if (!target_dir) return
    try {
      await axios.post('/api/utils/open_folder', { path: target_dir })
    } catch (err) {
      console.error('Failed to open folder:', err)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-6 animate-fadeIn">
      <div className="relative w-full max-w-lg glazzed-glass rounded-2xl border border-slate-700/80 p-8 shadow-2xl space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
              {isCompleted ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-400" />
              ) : (
                <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
              )}
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">
                {isExporting ? 'Exporting Photos to Library...' : 'Photo Export Complete!'}
              </h3>
              <p className="text-xs text-slate-400 font-mono truncate max-w-xs">{target_dir}</p>
            </div>
          </div>

          {isCompleted && (
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Progress Bar & Counter */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs font-mono text-slate-300">
            <span>{isExporting ? `Exporting: ${current_file}` : 'All photos exported successfully!'}</span>
            <span className="font-bold text-emerald-400">{percent}%</span>
          </div>
          <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 via-emerald-400 to-teal-400 rounded-full transition-all duration-300 shadow-md shadow-emerald-500/50"
              style={{ width: `${percent}%` }}
            />
          </div>
          <p className="text-xs text-right text-slate-400 font-mono">
            {displayExportedCount} / {total_files} files processed
          </p>
        </div>

        {/* Action Controls */}
        {isCompleted && (
          <div className="pt-2 flex items-center justify-end gap-3">
            {target_dir && (
              <button
                onClick={handleOpenFolder}
                className="px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center gap-2 transition-all shadow-lg shadow-cyan-600/30"
              >
                <FolderOpen className="w-4 h-4" />
                Open Output Folder in Explorer
              </button>
            )}
            <button
              onClick={onClose}
              className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition-all"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
