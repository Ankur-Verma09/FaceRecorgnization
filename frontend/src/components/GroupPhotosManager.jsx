import React, { useState } from 'react'
import axios from 'axios'
import { Users, Image, FolderOpen, Folder, Sparkles, CheckCircle2, ArrowRight } from 'lucide-react'

export default function GroupPhotosManager({ onExecuteOrganize }) {
  const [targetDir, setTargetDir] = useState('')
  const [libraryName, setLibraryName] = useState('')
  const [groupFolderName, setGroupFolderName] = useState('Group_Photos')
  const [sceneryFolderName, setSceneryFolderName] = useState('Scenery_and_Objects')
  const [groupThreshold, setGroupThreshold] = useState(3)

  const handleBrowseFolder = async () => {
    try {
      const res = await axios.post('/api/utils/select_folder', { title: 'Select Target Export Directory' })
      if (res.data?.path) {
        setTargetDir(res.data.path)
      }
    } catch (err) {
      console.error('Folder selection failed:', err)
    }
  }

  const handleExecute = () => {
    onExecuteOrganize({
      target_dir: targetDir.trim() || undefined,
      library_name: libraryName.trim(),
      group_folder_name: groupFolderName.trim() || 'Group_Photos',
      scenery_folder_name: sceneryFolderName.trim() || 'Scenery_and_Objects',
      group_threshold: groupThreshold
    })
  }

  const effectiveBase = targetDir.trim()
    ? (libraryName.trim() ? `${targetDir.trim()}/${libraryName.trim()}` : targetDir.trim())
    : '[Target_Export_Folder]'

  const effectiveGroupFolder = groupFolderName.trim() || 'Group_Photos'
  const effectiveSceneryFolder = sceneryFolderName.trim() || 'Scenery_and_Objects'

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 my-6">
      {/* Header */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 flex items-center gap-4">
        <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400 shrink-0">
          <Users className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Group &amp; Scenery Photo Export Settings</h2>
          <p className="text-sm text-slate-400">
            Customize target export folders and threshold rules for group crowd photos and non-face scenery photos.
          </p>
        </div>
      </div>

      {/* Overview Feature Cards */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-3">
          <div className="flex items-center gap-2 text-indigo-400 font-bold text-base">
            <Users className="w-5 h-5" />
            <span>Group Photos Rule</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Photos containing <strong className="text-indigo-300">{groupThreshold}+ people</strong> (family groups, wedding guests, crowd shots) will be routed directly to your chosen group folder.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-3">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-base">
            <Image className="w-5 h-5" />
            <span>Scenery &amp; Objects Rule</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Photos with <strong className="text-emerald-300">0 faces detected</strong> (landscapes, venue decorations, rings, food, details) will be routed to your chosen scenery folder.
          </p>
        </div>
      </div>

      {/* Target Directory & Custom Folder Settings */}
      <div className="glass-card rounded-2xl border border-slate-800 p-6 space-y-5">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <FolderOpen className="w-5 h-5 text-cyan-400" />
          Export Destination &amp; Folder Naming Options
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Target Directory (Input + Browse) */}
          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <FolderOpen className="w-3.5 h-3.5 text-cyan-400" />
              Target Export Directory (Where to save output)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={targetDir}
                onChange={(e) => setTargetDir(e.target.value)}
                placeholder="Leave blank to use default scan export location"
                className="flex-1 bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs font-mono"
              />
              <button
                type="button"
                onClick={handleBrowseFolder}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-bold border border-slate-700 flex items-center gap-1.5 shrink-0 transition-all"
              >
                <FolderOpen className="w-4 h-4" />
                Browse…
              </button>
            </div>
          </div>

          {/* Event Library Name (Optional) */}
          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Folder className="w-3.5 h-3.5 text-indigo-400" />
              Event Library Subfolder (Optional)
            </label>
            <input
              type="text"
              value={libraryName}
              onChange={(e) => setLibraryName(e.target.value)}
              placeholder="Leave blank for no subfolder"
              className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs font-mono"
            />
          </div>

          {/* Group Photos Folder Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-indigo-400" />
              Group Photos Folder Name
            </label>
            <input
              type="text"
              value={groupFolderName}
              onChange={(e) => setGroupFolderName(e.target.value)}
              placeholder="Group_Photos"
              className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs font-mono"
            />
          </div>

          {/* Scenery Photos Folder Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Image className="w-3.5 h-3.5 text-emerald-400" />
              Scenery &amp; Objects Folder Name
            </label>
            <input
              type="text"
              value={sceneryFolderName}
              onChange={(e) => setSceneryFolderName(e.target.value)}
              placeholder="Scenery_and_Objects"
              className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs font-mono"
            />
          </div>

          {/* Group Threshold Selector */}
          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-purple-400" />
              Group Threshold (Minimum faces to classify as Group)
            </label>
            <div className="flex items-center gap-4 bg-slate-900/90 border border-slate-700 rounded-xl p-3">
              {[2, 3, 4, 5].map((cnt) => (
                <button
                  key={cnt}
                  type="button"
                  onClick={() => setGroupThreshold(cnt)}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-lg border transition-all ${
                    groupThreshold === cnt
                      ? 'bg-indigo-600 border-indigo-500 text-white shadow'
                      : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white'
                  }`}
                >
                  {cnt}+ People
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Live Folder Hierarchy Preview */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 text-xs text-slate-400 space-y-2">
          <p className="font-semibold text-slate-200 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Live Destination Folder Preview:
          </p>
          <ul className="list-disc list-inside space-y-1 text-slate-300 font-mono text-[11px] truncate">
            <li><span className="text-indigo-400">{effectiveBase}/{effectiveGroupFolder}</span> ({groupThreshold}+ faces)</li>
            <li><span className="text-emerald-400">{effectiveBase}/{effectiveSceneryFolder}</span> (0 faces)</li>
          </ul>
        </div>
      </div>

      {/* Execute Button */}
      <button
        onClick={handleExecute}
        className="w-full bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white font-bold py-4 px-6 rounded-xl shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-3 transition-all text-base"
      >
        <CheckCircle2 className="w-5 h-5" />
        <span>Execute Full Photo Organization Now</span>
        <ArrowRight className="w-5 h-5" />
      </button>
    </div>
  )
}
