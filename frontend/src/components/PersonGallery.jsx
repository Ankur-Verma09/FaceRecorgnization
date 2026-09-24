import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  UserCheck, Edit2, Check, Merge, Heart, Trash2, Sliders, RefreshCw,
  GitMerge, Undo2, ChevronDown, ChevronUp, Users, Search, X, FolderOpen
} from 'lucide-react'

export default function PersonGallery({
  persons,
  onRenamePerson,
  onMergePersons,
  onDeletePerson,
  onRecluster,
  selectedForCouple,
  setSelectedForCouple
}) {
  const [editingId, setEditingId] = useState(null)
  const [nameInput, setNameInput] = useState('')
  const [selectedMergeIds, setSelectedMergeIds] = useState([])
  const [threshold, setThreshold] = useState(0.48)
  const [isReclustering, setIsReclustering] = useState(false)
  const [mergeGroups, setMergeGroups] = useState([])
  const [showMerged, setShowMerged] = useState(true)

  const [searchQuery, setSearchQuery] = useState('')
  const [sortOrder, setSortOrder] = useState('Name A-Z')

  const [personToDelete, setPersonToDelete] = useState(null)
  const [albumPerson, setAlbumPerson] = useState(null)
  const [albumImages, setAlbumImages] = useState([])

  const fetchMergeGroups = useCallback(async () => {
    try {
      const res = await axios.get('/api/persons/merge_groups')
      setMergeGroups(res.data || [])
    } catch (err) {
      console.error('Failed to fetch merge groups:', err)
    }
  }, [])

  useEffect(() => {
    fetchMergeGroups()
  }, [fetchMergeGroups])

  const handleStartRename = (person) => {
    setEditingId(person.person_id)
    setNameInput(person.display_name)
  }

  const handleSaveRename = (personId) => {
    if (nameInput.trim()) {
      onRenamePerson(personId, nameInput.trim())
    }
    setEditingId(null)
  }

  const toggleCoupleSelect = (personId) => {
    if (selectedForCouple.includes(personId)) {
      setSelectedForCouple(selectedForCouple.filter((id) => id !== personId))
    } else {
      if (selectedForCouple.length < 2) {
        setSelectedForCouple([...selectedForCouple, personId])
      } else {
        setSelectedForCouple([selectedForCouple[0], personId])
      }
    }
  }

  const toggleMergeSelect = (personId) => {
    if (selectedMergeIds.includes(personId)) {
      setSelectedMergeIds(selectedMergeIds.filter((id) => id !== personId))
    } else {
      if (selectedMergeIds.length < 2) {
        setSelectedMergeIds([...selectedMergeIds, personId])
      }
    }
  }

  const handleExecuteMerge = async () => {
    if (selectedMergeIds.length === 2) {
      await onMergePersons(selectedMergeIds[0], selectedMergeIds[1])
      setSelectedMergeIds([])
      fetchMergeGroups()
    }
  }

  const handleReclusterClick = async () => {
    setIsReclustering(true)
    await onRecluster(threshold)
    setIsReclustering(false)
    fetchMergeGroups()
  }

  const handleUnmerge = async (groupId) => {
    try {
      await axios.post('/api/persons/unmerge', { group_id: groupId })
      fetchMergeGroups()
      await onRecluster && window.dispatchEvent(new CustomEvent('refresh-persons'))
      const evt = new CustomEvent('unmerge-complete')
      window.dispatchEvent(evt)
    } catch (err) {
      console.error('Unmerge failed:', err)
    }
  }

  const handleOpenAlbum = async (person) => {
    setAlbumPerson(person)
    setAlbumImages([])
    try {
      const res = await axios.get(`/api/persons/${person.person_id}/images`)
      setAlbumImages(res.data)
    } catch(err) {
      console.error(err)
    }
  }

  const handleDetachImage = async (imageId) => {
     try {
        const res = await axios.get(`/api/images/${imageId}/faces`)
        const face = res.data.find(f => f.person_id === albumPerson.person_id)
        if (face) {
            await axios.post('/api/faces/delete', { face_id: face.face_id })
            handleOpenAlbum(albumPerson)
        }
     } catch (err) { console.error(err) }
  }

  const handleReassignImage = async (imageId, e) => {
     const targetPersonId = e.target.value
     if (!targetPersonId) return
     try {
        const res = await axios.get(`/api/images/${imageId}/faces`)
        const face = res.data.find(f => f.person_id === albumPerson.person_id)
        if (face) {
            await axios.post('/api/faces/reassign', { face_id: face.face_id, target_person_id: targetPersonId })
            handleOpenAlbum(albumPerson)
        }
     } catch (err) { console.error(err) }
  }

  const mergeGroupsByTarget = mergeGroups.reduce((acc, mg) => {
    const key = mg.target_person_id
    if (!acc[key]) {
      acc[key] = {
        target_person_id: mg.target_person_id,
        target_display_name: mg.current_target_name || mg.target_display_name,
        target_thumbnail: mg.target_thumbnail,
        absorbed: []
      }
    }
    acc[key].absorbed.push(mg)
    return acc
  }, {})

  const mergeGroupList = Object.values(mergeGroupsByTarget)

  const filteredPersons = persons.filter(p => p.display_name.toLowerCase().includes(searchQuery.toLowerCase()))
  const sortedPersons = filteredPersons.sort((a, b) => {
    if (sortOrder === 'Name A-Z') return a.display_name.localeCompare(b.display_name)
    const countA = a.photo_count ?? a.face_count ?? 0
    const countB = b.photo_count ?? b.face_count ?? 0
    if (sortOrder === 'Most Photos') return countB - countA
    if (sortOrder === 'Least Photos') return countA - countB
    return 0
  })

  return (
    <div className="w-full max-w-6xl mx-auto my-6 space-y-6">
      {/* Top Header & Controls */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <UserCheck className="w-6 h-6 text-cyan-400" />
              Identified Individual Persons ({persons.length})
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Click Avatar to View Album. Use ♥ to select a Couple pair. Use "Select to Merge" for duplicates.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {selectedMergeIds.length === 2 && (
              <button
                onClick={handleExecuteMerge}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition-all"
              >
                <Merge className="w-4 h-4" />
                Merge 2 Selected Profiles
              </button>
            )}

            {selectedForCouple.length > 0 && (
              <div className="bg-pink-950/60 border border-pink-500/40 text-pink-300 text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2">
                <Heart className="w-4 h-4 text-pink-400 fill-current" />
                {selectedForCouple.length} / 2 Selected for Couple Folder
              </div>
            )}
          </div>
        </div>

        {/* Search and Sort */}
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search persons..." 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-9 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>
          <select 
            value={sortOrder}
            onChange={e => setSortOrder(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-500 transition-colors min-w-[160px]"
          >
            <option>Name A-Z</option>
            <option>Most Photos</option>
            <option>Least Photos</option>
          </select>
        </div>

        {/* Pose Angle & Multi-Angle Cluster Tolerance Slider */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <Sliders className="w-5 h-5 text-cyan-400 shrink-0" />
            <div>
              <p className="text-xs font-bold text-white">Multi-Angle Pose Match Sensitivity</p>
              <p className="text-[11px] text-slate-400">
                If the same person at different angles is split into separate profiles, increase sensitivity to auto-merge them.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-400 font-mono">Strict (0.38)</span>
              <input
                type="range"
                min="0.38"
                max="0.52"
                step="0.02"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-32 accent-cyan-400 cursor-pointer"
              />
              <span className="text-[10px] text-slate-400 font-mono">Multi-Angle ({threshold})</span>
            </div>

            <button
              onClick={handleReclusterClick}
              disabled={isReclustering}
              className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-black text-xs px-4 py-2 rounded-lg shadow flex items-center gap-2 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isReclustering ? 'animate-spin' : ''}`} />
              {isReclustering ? 'Re-clustering...' : 'Auto-Merge Pose Angles'}
            </button>
          </div>
        </div>
      </div>

      {/* Person Cards Grid */}
      {sortedPersons.length === 0 ? (
        <div className="glass-card p-12 rounded-2xl text-center border border-slate-800">
          <p className="text-slate-400 text-base">No persons found matching your criteria.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
          {sortedPersons.map((person) => {
            const isSelectedCouple = selectedForCouple.includes(person.person_id)
            const isSelectedMerge = selectedMergeIds.includes(person.person_id)

            return (
              <div
                key={person.person_id}
                className={`glass-card glass-card-hover rounded-2xl p-4 border transition-all duration-300 flex flex-col items-center relative group ${
                  isSelectedCouple
                    ? 'border-pink-500 shadow-xl shadow-pink-500/20 bg-pink-950/20'
                    : isSelectedMerge
                    ? 'border-indigo-500 shadow-xl shadow-indigo-500/20 bg-indigo-950/20'
                    : 'border-slate-800'
                }`}
              >
                {/* Delete Person Button Top Left */}
                <button
                  onClick={() => setPersonToDelete(person.person_id)}
                  title="Delete identified person profile"
                  className="absolute top-3 left-3 p-1.5 rounded-full bg-slate-900/80 hover:bg-rose-600 text-slate-400 hover:text-white opacity-0 group-hover:opacity-100 transition-all z-10"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>

                {/* Couple Select Heart Badge Top Right */}
                <button
                  onClick={() => toggleCoupleSelect(person.person_id)}
                  title="Select for Groom & Bride Couple Filter"
                  className={`absolute top-3 right-3 p-2 rounded-full transition-all z-10 ${
                    isSelectedCouple
                      ? 'bg-pink-600 text-white scale-110 shadow-lg shadow-pink-600/50'
                      : 'bg-slate-900/80 text-slate-400 hover:text-pink-400 hover:bg-slate-800'
                  }`}
                >
                  <Heart className={`w-4 h-4 ${isSelectedCouple ? 'fill-current' : ''}`} />
                </button>

                {/* Avatar Cropped Thumbnail */}
                <div 
                  className="w-24 h-24 rounded-full overflow-hidden border-2 border-slate-700 shadow-lg my-2 bg-slate-900 flex items-center justify-center cursor-pointer hover:border-cyan-400 transition-colors"
                  onClick={() => handleOpenAlbum(person)}
                  title="Click to view album"
                >
                  <img
                    src={`/api/person_thumbnail/${person.person_id}?t=${Date.now()}`}
                    alt={person.display_name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.target.onerror = null
                      e.target.src = 'https://via.placeholder.com/150?text=Face'
                    }}
                  />
                  <div className="absolute inset-0 bg-black/40 hidden group-hover:flex items-center justify-center rounded-full pointer-events-none">
                    <FolderOpen className="w-8 h-8 text-white opacity-80" />
                  </div>
                </div>

                {/* Person Display Name Inline Editor */}
                <div className="w-full text-center mt-2">
                  {editingId === person.person_id ? (
                    <div className="flex items-center gap-1 justify-center">
                      <input
                        type="text"
                        value={nameInput}
                        onChange={(e) => setNameInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSaveRename(person.person_id)}
                        className="bg-slate-900 border border-cyan-500 rounded px-2 py-1 text-xs text-white font-semibold text-center focus:outline-none w-28"
                        autoFocus
                      />
                      <button
                        onClick={() => handleSaveRename(person.person_id)}
                        className="p-1 bg-emerald-600 text-white rounded hover:bg-emerald-500"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center gap-1.5 cursor-pointer" onClick={() => handleStartRename(person)}>
                      <h3 className="text-sm font-bold text-slate-100 hover:text-cyan-400 truncate max-w-[120px]">
                        {person.display_name}
                      </h3>
                      <Edit2 className="w-3.5 h-3.5 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  )}

                  <span className="inline-block mt-2 bg-slate-900/80 border border-slate-700 text-cyan-400 font-mono text-xs px-2.5 py-1 rounded-full">
                    {person.photo_count ?? person.face_count ?? 0} photo{(person.photo_count ?? person.face_count ?? 0) !== 1 ? 's' : ''}
                  </span>
                </div>

                {/* Merge Select Button */}
                <button
                  onClick={() => toggleMergeSelect(person.person_id)}
                  className={`w-full mt-4 text-xs font-semibold py-1.5 rounded-lg border transition-all ${
                    isSelectedMerge
                      ? 'bg-indigo-600 border-indigo-500 text-white'
                      : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {isSelectedMerge ? 'Selected to Merge' : 'Select to Merge'}
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Merged Groups Section */}
      {mergeGroupList.length > 0 && (
        <div className="glass-card rounded-2xl border border-indigo-500/30 bg-indigo-950/10 overflow-hidden">
          <button
            onClick={() => setShowMerged((v) => !v)}
            className="w-full flex items-center justify-between px-6 py-4 hover:bg-indigo-950/20 transition-colors"
          >
            <div className="flex items-center gap-3">
              <GitMerge className="w-5 h-5 text-indigo-400" />
              <div className="text-left">
                <h3 className="text-base font-bold text-white">
                  Merged Groups <span className="ml-2 text-xs font-normal text-indigo-300 bg-indigo-900/60 px-2 py-0.5 rounded-full">{mergeGroups.length} merge{mergeGroups.length !== 1 ? 's' : ''}</span>
                </h3>
                <p className="text-xs text-slate-400">Persons that were manually merged. Click "Unmerge" to reverse.</p>
              </div>
            </div>
            {showMerged ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
          </button>

          {showMerged && (
            <div className="px-6 pb-6 space-y-4">
              {mergeGroupList.map((group) => (
                <div
                  key={group.target_person_id}
                  className="rounded-xl border border-indigo-500/20 bg-slate-900/60 overflow-hidden"
                >
                  <div className="flex items-center gap-4 px-5 py-4 bg-indigo-900/20 border-b border-indigo-500/20">
                    <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-indigo-400 bg-slate-800 shrink-0">
                      {group.target_thumbnail ? (
                        <img
                          src={`/api/person_thumbnail/${group.target_person_id}?t=${Date.now()}`}
                          alt={group.target_display_name}
                          className="w-full h-full object-cover"
                          onError={(e) => { e.target.onerror = null; e.target.src = 'https://via.placeholder.com/50?text=?' }}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-indigo-300">
                          <Users className="w-5 h-5" />
                        </div>
                      )}
                    </div>
                    <div>
                      <p className="text-xs text-indigo-300 font-semibold uppercase tracking-wider">Surviving Profile</p>
                      <p className="text-sm font-bold text-white">{group.target_display_name || group.target_person_id}</p>
                    </div>
                  </div>

                  <div className="divide-y divide-slate-800/60">
                    {group.absorbed.map((mg) => (
                      <div key={mg.group_id} className="flex items-center justify-between px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-2 h-2 rounded-full bg-indigo-400 opacity-60 ml-1" />
                          <div>
                            <p className="text-xs text-slate-400">Absorbed profile:</p>
                            <p className="text-sm font-semibold text-slate-200">{mg.source_display_name || mg.source_person_id}</p>
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono ml-2">
                            {new Date(mg.merged_at).toLocaleDateString()} {new Date(mg.merged_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>

                        <button
                          onClick={() => handleUnmerge(mg.group_id)}
                          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-amber-600 border border-slate-700 hover:border-amber-500 text-slate-300 hover:text-white transition-all"
                        >
                          <Undo2 className="w-3.5 h-3.5" />
                          Unmerge
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Confirmation Modal for Delete */}
      {personToDelete && (
        <div className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-rose-500/50 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-2">Delete Person Profile?</h3>
            <p className="text-sm text-slate-300 mb-6">Are you sure you want to delete this person? This action cannot be undone, and associated faces will be detached.</p>
            <div className="flex justify-end gap-3">
              <button 
                onClick={() => setPersonToDelete(null)}
                className="px-4 py-2 text-sm font-semibold text-slate-300 hover:text-white bg-slate-800 rounded-lg"
              >Cancel</button>
              <button
                onClick={() => {
                  onDeletePerson(personToDelete);
                  setPersonToDelete(null);
                }}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-sm font-bold rounded-lg"
              >Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Album Modal */}
      {albumPerson && (
        <div className="fixed inset-0 z-[60] bg-black/80 flex items-center justify-center p-6 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-6xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
              <div className="flex items-center gap-4">
                <img src={`/api/person_thumbnail/${albumPerson.person_id}`} className="w-10 h-10 rounded-full object-cover border border-slate-700" alt="" />
                <div>
                  <h3 className="text-lg font-bold text-white">{albumPerson.display_name} Album</h3>
                  <p className="text-xs text-slate-400">{albumImages.length} photos</p>
                </div>
              </div>
              <button onClick={() => setAlbumPerson(null)} className="p-2 text-slate-400 hover:text-white rounded-full hover:bg-slate-800"><X className="w-5 h-5"/></button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1 bg-slate-900/50 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {albumImages.map(img => (
                <div key={img.image_id} className="group relative rounded-xl overflow-hidden border border-slate-800 bg-black aspect-square flex flex-col">
                   <img src={`/api/image?path=${encodeURIComponent(img.file_path)}`} className="w-full h-full object-cover" alt="" />
                   
                   <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent p-3 pt-6 flex flex-col justify-end">
                     <p className="text-[10px] text-white truncate font-mono" title={img.file_name}>{img.file_name}</p>
                     <p className="text-[9px] text-slate-400">{img.datetime_taken || 'Unknown Date'}</p>
                   </div>
                   
                   <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-center items-center gap-2 p-4">
                     <button 
                        onClick={() => handleDetachImage(img.image_id)}
                        className="w-full py-1.5 px-3 bg-rose-600/80 hover:bg-rose-500 text-white text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1"
                     >
                       <Trash2 className="w-3 h-3" /> Detach
                     </button>
                     <select 
                       onChange={(e) => handleReassignImage(img.image_id, e)}
                       value=""
                       className="w-full py-1.5 px-3 bg-slate-800 text-white text-xs rounded-lg border border-slate-600"
                     >
                       <option value="">Reassign to...</option>
                       {persons.filter(p => p.person_id !== albumPerson.person_id).map(p => (
                         <option key={p.person_id} value={p.person_id}>{p.display_name}</option>
                       ))}
                     </select>
                   </div>
                </div>
              ))}
              {albumImages.length === 0 && (
                <div className="col-span-full py-12 text-center text-slate-500 text-sm">
                  No photos found or loading...
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
