import React from 'react'
import { Image, Users, Cpu, CheckCircle2, Loader2, OctagonX, AlertCircle } from 'lucide-react'

export default function LiveScannerDashboard({ scanStatus, onCancelScan }) {
  const {
    status,
    scanned_count = 0,
    total_files = 0,
    current_file = '',
    total_faces_found = 0,
    persons_count = 0,
    message = ''
  } = scanStatus || {}

  const isScanning = status === 'scanning' || status === 'clustering'
  const isCancelled = status === 'cancelled'
  const isError = status === 'error'
  const isCompleted = status === 'completed'

  const percent = total_files > 0 ? Math.min(100, Math.round((scanned_count / total_files) * 100)) : 0

  return (
    <div className="w-full max-w-4xl mx-auto glass-card rounded-2xl p-8 border border-slate-800 shadow-2xl my-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
            {isCompleted && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
            {isCancelled && <OctagonX className="w-6 h-6 text-amber-400" />}
            {isError && <AlertCircle className="w-6 h-6 text-rose-400" />}
            {isScanning && <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />}
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">
              {status === 'scanning' && 'Scanning & Detecting Faces...'}
              {status === 'clustering' && 'Clustering Face Embeddings...'}
              {status === 'completed' && 'Face Identification Complete!'}
              {status === 'cancelled' && 'Scan Stopped by User'}
              {status === 'error' && 'Scan Failed'}
              {status === 'idle' && 'Ready for Photo Scan'}
            </h2>
            <p className="text-sm text-slate-400 font-mono">
              {message || (current_file ? `Processing: ${current_file}` : 'Local ONNX SFace 512D Vector Analysis')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Stop / Cancel Scan Button */}
          {isScanning && onCancelScan && (
            <button
              onClick={onCancelScan}
              className="bg-rose-950/80 hover:bg-rose-900 border border-rose-500/50 text-rose-200 font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-2 transition-all shadow shadow-rose-900/30"
            >
              <OctagonX className="w-4 h-4 text-rose-400" />
              Stop / Cancel Scan
            </button>
          )}

          <div className="text-right">
            <span className="text-3xl font-extrabold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              {percent}%
            </span>
            <p className="text-xs text-slate-400 font-mono">{scanned_count} / {total_files} photos</p>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden mb-8 border border-slate-800 p-0.5">
        <div
          className={`h-full rounded-full transition-all duration-300 shadow-lg ${
            isCancelled
              ? 'bg-amber-500 shadow-amber-500/50'
              : isError
              ? 'bg-rose-500 shadow-rose-500/50'
              : 'bg-gradient-to-r from-cyan-400 via-indigo-500 to-purple-500 shadow-cyan-500/50'
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-cyan-500/10 text-cyan-400">
            <Image className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Scanned Photos</p>
            <p className="text-2xl font-bold text-white">{scanned_count}</p>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-purple-500/10 text-purple-400">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Faces Detected</p>
            <p className="text-2xl font-bold text-white">{total_faces_found}</p>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Identified Persons</p>
            <p className="text-2xl font-bold text-white">{persons_count}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
