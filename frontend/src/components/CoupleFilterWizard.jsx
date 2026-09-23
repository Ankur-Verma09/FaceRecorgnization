import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Heart, FolderHeart, Sparkles, CheckCircle2, ArrowRight, X, Search, Users, FolderOpen, Folder } from 'lucide-react'

export default function CoupleFilterWizard({ persons, selectedForCouple, onExecuteOrganize }) {
  const [folderName, setFolderName] = useState('Groom_and_Bride')
  const [targetDir, setTargetDir] = useState('')
  const [libraryName, setLibraryName] = useState('')
  // Local selection — independent from the parent tab; pre-filled if parent already has a selection
  const [localSelected, setLocalSelected] = useState(selectedForCouple || [])
  const [searchTerm, setSearchTerm] = useState('')

  // Sync if parent pre-selected couple
  useEffect(() => {
    if (selectedForCouple && selectedForCouple.length > 0 && localSelected.length === 0) {
      setLocalSelected(selectedForCouple)
    }
  }, [selectedForCouple]) // eslint-disable-line react-hooks/exhaustive-deps

  const selectedPersonObjects = persons.filter((p) => localSelected.includes(p.person_id))
  const filteredPersons = persons.filter((p) =>
    p.display_name.toLowerCase().includes(searchTerm.toLowerCase())
  )

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

  const toggleSelect = (personId) => {
    if (localSelected.includes(personId)) {
      setLocalSelected(localSelected.filter((id) => id !== personId))
    } else {
      if (localSelected.length < 2) {
        setLocalSelected([...localSelected, personId])
      } else {
        setLocalSelected([localSelected[0], personId])
      }
    }
  }

  const clearSlot = (idx) => {
    const next = [...localSelected]
    next.splice(idx, 1)
    setLocalSelected(next)
  }

  const handleExecute = () => {
    if (localSelected.length !== 2) return
    onExecuteOrganize({
      couple_pair: localSelected,
      couple_folder_name: folderName.trim() || 'Groom_and_Bride',
      target_dir: targetDir.trim() || undefined,
      library_name: libraryName.trim()
    })
  }

  const effectiveCoupleFolder = folderName.trim() || 'Groom_and_Bride'
  const effectiveBase = targetDir.trim()
    ? (libraryName.trim() ? `${targetDir.trim()}/${libraryName.trim()}` : targetDir.trim())
    : '[Target_Folder]'

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 my-6">
      {/* Header */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 flex items-center gap-4">
        <div className="p-3 bg-pink-500/10 border border-pink-500/20 rounded-xl text-pink-400 shrink-0">
          <Heart className="w-6 h-6 fill-current" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Groom &amp; Bride / Couple Pair Filter</h2>
          <p className="text-sm text-slate-400">
            Pick 2 people below. The app will group solo photos of each person AND joint photos featuring both into one dedicated couple folder.
          </p>
        </div>
      </div>

      {/* Selected 2 Persons Preview */}
      <div className="grid grid-cols-2 gap-6">
        {[0, 1].map((idx) => {
          const person = selectedPersonObjects[idx]
          return (
            <div
              key={idx}
              className={`p-5 rounded-2xl border flex items-center gap-4 transition-all relative ${
                person
                  ? 'bg-pink-950/20 border-pink-500/40 shadow-lg shadow-pink-500/10'
                  : 'bg-slate-900/50 border-slate-800 border-dashed text-slate-500'
              }`}
            >
              {person ? (
                <>
                  <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-pink-500 shadow-md bg-slate-900 shrink-0">
                    <img
                      src={`/api/person_thumbnail/${person.person_id}`}
                      alt={person.display_name}
                      className="w-full h-full object-cover"
                      onError={(e) => { e.target.onerror = null; e.target.src = 'https://via.placeholder.com/64?text=?' }}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-xs text-pink-400 font-semibold uppercase tracking-wider">
                      {idx === 0 ? 'Person 1 (e.g. Groom)' : 'Person 2 (e.g. Bride)'}
                    </span>
                    <h3 className="text-base font-bold text-white truncate">{person.display_name}</h3>
                    <p className="text-xs text-slate-400 font-mono">
                      {person.photo_count ?? person.face_count ?? 0} photo{(person.photo_count ?? person.face_count ?? 0) !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <button
                    onClick={() => clearSlot(idx)}
                    className="absolute top-3 right-3 p-1.5 rounded-full bg-slate-800/80 hover:bg-rose-600 text-slate-400 hover:text-white transition-all"
                    title="Remove selection"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </>
              ) : (
                <div className="w-full text-center py-4">
                  <Users className="w-7 h-7 text-slate-600 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-500">
                    {idx === 0 ? 'Select Person 1 below ↓' : 'Select Person 2 below ↓'}
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Inline Person Picker Grid */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <div className="px-6 pt-5 pb-3 border-b border-slate-800 flex items-center gap-3">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search persons by name…"
            className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-500 focus:outline-none"
          />
          {localSelected.length > 0 && (
            <span className="text-xs text-pink-400 font-semibold bg-pink-950/40 px-2.5 py-1 rounded-full">
              {localSelected.length}/2 selected
            </span>
          )}
        </div>

        {persons.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-sm">
            No identified persons yet. Run a folder scan first.
          </div>
        ) : (
          <div className="p-5 grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-4 max-h-80 overflow-y-auto">
            {filteredPersons.map((person) => {
              const isSelected = localSelected.includes(person.person_id)
              const selIdx = localSelected.indexOf(person.person_id)

              return (
                <button
                  key={person.person_id}
                  onClick={() => toggleSelect(person.person_id)}
                  className={`relative flex flex-col items-center gap-2 p-3 rounded-xl border transition-all ${
                    isSelected
                      ? 'border-pink-500 bg-pink-950/30 shadow-lg shadow-pink-500/20 scale-105'
                      : 'border-slate-800 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-800/50'
                  }`}
                >
                  {/* Selection badge */}
                  {isSelected && (
                    <div className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-pink-600 text-white text-[10px] font-black flex items-center justify-center shadow-lg">
                      {selIdx + 1}
                    </div>
                  )}

                  <div className={`w-14 h-14 rounded-full overflow-hidden border-2 shadow-md bg-slate-800 ${
                    isSelected ? 'border-pink-500' : 'border-slate-700'
                  }`}>
                    <img
                      src={`/api/person_thumbnail/${person.person_id}`}
                      alt={person.display_name}
                      className="w-full h-full object-cover"
                      onError={(e) => { e.target.onerror = null; e.target.src = 'https://via.placeholder.com/56?text=?' }}
                    />
                  </div>

                  <p className={`text-[11px] font-semibold text-center truncate w-full ${
                    isSelected ? 'text-pink-300' : 'text-slate-300'
                  }`}>
                    {person.display_name}
                  </p>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {person.photo_count ?? person.face_count ?? 0} photo{(person.photo_count ?? person.face_count ?? 0) !== 1 ? 's' : ''}
                  </span>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Target Directory & Folder Configuration */}
      <div className="glass-card rounded-2xl border border-slate-800 p-6 space-y-5">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <FolderHeart className="w-5 h-5 text-pink-400" />
          Export Destination &amp; Folder Settings
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Target Directory */}
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
                className="flex-1 bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-pink-500 text-xs font-mono"
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

          {/* Library Name (Optional) */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Folder className="w-3.5 h-3.5 text-indigo-400" />
              Event Library Subfolder (Optional)
            </label>
            <input
              type="text"
              value={libraryName}
              onChange={(e) => setLibraryName(e.target.value)}
              placeholder="Leave blank for no subfolder"
              className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-pink-500 text-xs font-mono"
            />
          </div>

          {/* Couple Folder Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Heart className="w-3.5 h-3.5 text-pink-400" />
              Couple Subfolder Name
            </label>
            <input
              type="text"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              placeholder="Groom_and_Bride"
              className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-pink-500 text-xs font-mono"
            />
          </div>
        </div>

        {/* Live Folder Hierarchy Preview */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 text-xs text-slate-400 space-y-2">
          <p className="font-semibold text-slate-200 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-pink-400" />
            Live Destination Folder Preview:
          </p>
          <ul className="list-disc list-inside space-y-1 text-slate-300 font-mono text-[11px] truncate">
            <li><span className="text-pink-400">{effectiveBase}/{effectiveCoupleFolder}/Solo_{selectedPersonObjects[0]?.display_name || 'Person_1'}</span></li>
            <li><span className="text-pink-400">{effectiveBase}/{effectiveCoupleFolder}/Solo_{selectedPersonObjects[1]?.display_name || 'Person_2'}</span></li>
            <li><span className="text-pink-400">{effectiveBase}/{effectiveCoupleFolder}/Couple_Photos</span></li>
          </ul>
        </div>
      </div>

      {/* Execute Button */}
      <button
        onClick={handleExecute}
        disabled={localSelected.length !== 2}
        className="w-full bg-gradient-to-r from-pink-600 via-purple-600 to-indigo-600 hover:from-pink-500 hover:to-indigo-500 disabled:opacity-40 text-white font-bold py-4 px-6 rounded-xl shadow-lg shadow-pink-600/30 flex items-center justify-center gap-3 transition-all text-base"
      >
        <CheckCircle2 className="w-5 h-5" />
        <span>Organize Groom &amp; Bride Couple Photos</span>
        <ArrowRight className="w-5 h-5" />
      </button>
    </div>
  )
}
