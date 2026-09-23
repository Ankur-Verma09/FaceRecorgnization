import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  FolderOpen,
  Play,
  Copy,
  ArrowRightLeft,
  Link2,
  Users,
  Image as ImageIcon,
  CheckCircle2,
  Library,
  Trash2,
  OctagonX,
  Calendar,
  Layers,
  HardDrive,
  Clock,
  FileImage,
  ChevronRight,
  Maximize2
} from 'lucide-react'

export default function OverviewDashboard({
  stats = {},
  persons = [],
  onNavigate,
  scanStatus,
  onStartScan,
  onCancelScan,
  onExecuteOrganize,
  onDeletePerson,
  searchQuery = '',
  onSelectImageForLightbox
}) {
  const { totalFiles = 0, facesFound = 0, personsCount = 0, scannedCount = 0 } = stats
  const [imagesList, setImagesList] = useState([])
  const [sourceDir, setSourceDir] = useState('')
  const [targetDir, setTargetDir] = useState('')
  const [libraryName, setLibraryName] = useState('')
  const [operationMode, setOperationMode] = useState('copy')

  // Dashboard Insights state
  const [insights, setInsights] = useState({
    total_folders_scanned: 0,
    total_photos: 0,
    total_faces: 0,
    total_persons: 0,
    libraries: [],
    sessions: [],
    time_filtered: {
      last_7_days: { sessions: 0, photos: 0 },
      last_15_days: { sessions: 0, photos: 0 },
      monthly: [],
      yearly: []
    }
  })

  const [activeTimeRange, setActiveTimeRange] = useState('7d') // 'all', '7d', '15d', 'monthly', 'yearly'

  useEffect(() => {
    fetchImages()
    fetchInsights()
  }, [scannedCount, scanStatus.status])

  const fetchImages = async () => {
    try {
      const res = await axios.get('/api/images')
      setImagesList(res.data)
    } catch (err) {
      console.error('Failed to fetch images list:', err)
    }
  }

  const fetchInsights = async () => {
    try {
      const res = await axios.get('/api/dashboard/insights')
      setInsights(res.data)
    } catch (err) {
      console.error('Failed to fetch dashboard insights:', err)
    }
  }

  const handleBrowseFolder = async (targetType) => {
    try {
      const res = await axios.post('/api/utils/select_folder', {
        title: targetType === 'source' ? 'Select Source Photos Folder' : 'Select Target Output Folder'
      })
      if (res.data && res.data.path) {
        if (targetType === 'source') {
          setSourceDir(res.data.path)
        } else {
          setTargetDir(res.data.path)
        }
      }
    } catch (err) {
      console.error('Failed to open folder picker dialog:', err)
    }
  }

  const handleStart = (e) => {
    e.preventDefault()
    if (!sourceDir.trim()) return
    onStartScan({ sourceDir, targetDir, libraryName, operationMode })
  }

  const isScanning = scanStatus.status === 'scanning' || scanStatus.status === 'clustering'
  const isCompleted = scanStatus.status === 'completed'

  const filteredPersons = persons.filter((p) =>
    p.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.person_id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredImages = imagesList.filter((img) =>
    img.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    img.file_path.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Get active time range metrics for display
  const getTimeRangeDisplay = () => {
    const tf = insights.time_filtered || {}
    switch (activeTimeRange) {
      case '7d':
        return { label: 'Last 7 Days', sessions: tf.last_7_days?.sessions || 0, photos: tf.last_7_days?.photos || 0 }
      case '15d':
        return { label: 'Last 15 Days', sessions: tf.last_15_days?.sessions || 0, photos: tf.last_15_days?.photos || 0 }
      case 'monthly':
        const currentMonth = tf.monthly?.[0]
        return { label: `This Month (${currentMonth?.month || 'Current'})`, sessions: currentMonth?.sessions || 0, photos: currentMonth?.photos || 0 }
      case 'yearly':
        const currentYear = tf.yearly?.[0]
        return { label: `This Year (${currentYear?.year || '2026'})`, sessions: currentYear?.sessions || 0, photos: currentYear?.photos || 0 }
      default:
        return { label: 'All Time', sessions: insights.sessions?.length || 0, photos: totalFiles }
    }
  }

  const activeMetrics = getTimeRangeDisplay()

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner & Main Metrics */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">AI Scan Dashboard & Insights</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl leading-relaxed">
            Offline computer vision engine. Real-time folder analytics, library breakdowns, customer event timelines, and face sorting metrics.
          </p>
        </div>

        {/* 4 KPI Summary Metric Cards */}
        <div className="grid grid-cols-4 gap-4">
          <div className="flex items-center gap-3 bg-slate-900/80 p-3.5 rounded-2xl border border-slate-800 shadow">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <HardDrive className="w-5 h-5" />
            </div>
            <div>
              <p className="text-lg font-bold text-white">{insights.total_folders_scanned || (sourceDir ? 1 : 0)}</p>
              <p className="text-[10px] text-slate-400 font-semibold uppercase">Folders Scanned</p>
            </div>
          </div>

          <div className="flex items-center gap-3 bg-slate-900/80 p-3.5 rounded-2xl border border-slate-800 shadow">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <ImageIcon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-lg font-bold text-white">{totalFiles || insights.total_photos || 0}</p>
              <p className="text-[10px] text-slate-400 font-semibold uppercase">Photos Indexed</p>
            </div>
          </div>

          <div className="flex items-center gap-3 bg-slate-900/80 p-3.5 rounded-2xl border border-slate-800 shadow">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <p className="text-lg font-bold text-white">{facesFound || insights.total_faces || 0}</p>
              <p className="text-[10px] text-slate-400 font-semibold uppercase">Faces Found</p>
            </div>
          </div>

          <div className="flex items-center gap-3 bg-slate-900/80 p-3.5 rounded-2xl border border-slate-800 shadow">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Library className="w-5 h-5" />
            </div>
            <div>
              <p className="text-lg font-bold text-white">{insights.libraries?.length || (libraryName ? 1 : 0)}</p>
              <p className="text-[10px] text-slate-400 font-semibold uppercase">Event Libraries</p>
            </div>
          </div>
        </div>
      </div>

      {/* Row 1: Unified Photo Setup & Live Scan Controls */}
      <div className="glazzed-glass rounded-2xl p-6">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-slate-800/60 pb-3">
          <FolderOpen className="w-4 h-4 text-cyan-400" />
          Select Photo Directory & Start AI Event Library Scan
        </h3>

        <form onSubmit={handleStart} className="space-y-4">
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-4">
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center justify-between">
                <span>Source Photos Folder Path</span>
                <button
                  type="button"
                  onClick={() => handleBrowseFolder('source')}
                  className="text-[11px] text-cyan-400 hover:text-cyan-300 font-bold flex items-center gap-1 hover:underline"
                >
                  <FolderOpen className="w-3 h-3" /> Select Folder
                </button>
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={sourceDir}
                  onChange={(e) => setSourceDir(e.target.value)}
                  placeholder="e.g. D:\Photos\Wedding2026"
                  className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 text-xs font-mono"
                  required
                />
                <button
                  type="button"
                  onClick={() => handleBrowseFolder('source')}
                  className="px-3 py-2.5 rounded-xl bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-500/40 text-cyan-300 font-bold text-xs flex items-center gap-1.5 shrink-0 transition-all shadow"
                >
                  <FolderOpen className="w-3.5 h-3.5" /> Browse
                </button>
              </div>
            </div>

            <div className="col-span-4">
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1">
                <Library className="w-3.5 h-3.5 text-purple-400" /> Event Library Name
              </label>
              <input
                type="text"
                value={libraryName}
                onChange={(e) => setLibraryName(e.target.value)}
                placeholder="e.g. Wedding_2026 (Enter custom library name)"
                className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 text-xs font-mono font-bold"
              />
            </div>

            <div className="col-span-4">
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center justify-between">
                <span>Target Output Folder Path (Optional)</span>
                <button
                  type="button"
                  onClick={() => handleBrowseFolder('target')}
                  className="text-[11px] text-emerald-400 hover:text-emerald-300 font-bold flex items-center gap-1 hover:underline"
                >
                  <FolderOpen className="w-3 h-3" /> Select Folder
                </button>
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={targetDir}
                  onChange={(e) => setTargetDir(e.target.value)}
                  placeholder="e.g. D:\Photos\Organized_Events"
                  className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-xs font-mono"
                />
                <button
                  type="button"
                  onClick={() => handleBrowseFolder('target')}
                  className="px-3 py-2.5 rounded-xl bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-500/40 text-emerald-300 font-bold text-xs flex items-center gap-1.5 shrink-0 transition-all shadow"
                >
                  <FolderOpen className="w-3.5 h-3.5" /> Browse
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-400 font-semibold">Mode:</span>
              <button
                type="button"
                onClick={() => setOperationMode('copy')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                  operationMode === 'copy' ? 'bg-cyan-600 text-white shadow' : 'bg-slate-900 text-slate-400 hover:text-white'
                }`}
              >
                <Copy className="w-3.5 h-3.5" /> Copy Files
              </button>
              <button
                type="button"
                onClick={() => setOperationMode('move')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                  operationMode === 'move' ? 'bg-amber-600 text-white shadow' : 'bg-slate-900 text-slate-400 hover:text-white'
                }`}
              >
                <ArrowRightLeft className="w-3.5 h-3.5" /> Move Files
              </button>
              <button
                type="button"
                onClick={() => setOperationMode('symlink')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                  operationMode === 'symlink' ? 'bg-purple-600 text-white shadow' : 'bg-slate-900 text-slate-400 hover:text-white'
                }`}
              >
                <Link2 className="w-3.5 h-3.5" /> Symlink Shortcuts
              </button>
            </div>

            <div className="flex items-center gap-3">
              {isScanning && onCancelScan && (
                <button
                  type="button"
                  onClick={onCancelScan}
                  className="bg-rose-950 hover:bg-rose-900 border border-rose-500/50 text-rose-200 font-bold px-4 py-2.5 rounded-xl text-xs flex items-center gap-2 transition-all"
                >
                  <OctagonX className="w-4 h-4 text-rose-400" />
                  Stop / Cancel Scan
                </button>
              )}

              {isCompleted && (
                <button
                  type="button"
                  onClick={() => onExecuteOrganize({ library_name: libraryName })}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-emerald-600/30 flex items-center gap-2 transition-all"
                >
                  <CheckCircle2 className="w-4 h-4" /> Export to "{libraryName || 'Event_Library'}" Now
                </button>
              )}

              <button
                type="submit"
                disabled={isScanning || !sourceDir.trim()}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-40 text-slate-950 font-black text-xs px-6 py-2.5 rounded-xl shadow-lg shadow-cyan-500/25 flex items-center gap-2 transition-all"
              >
                {isScanning ? (
                  <>
                    <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></div>
                    <span>Processing Scan...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>Start AI Scan</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Live Progress Feed Bar */}
        {scanStatus.status !== 'idle' && (
          <div className="mt-6 pt-4 border-t border-slate-800/60">
            <div className="flex justify-between text-xs font-mono text-slate-300 mb-1.5">
              <span>Status: {scanStatus.status.toUpperCase()} {scanStatus.current_file ? `(${scanStatus.current_file})` : ''}</span>
              <span className="font-bold text-cyan-400">
                {totalFiles > 0 ? Math.round((scannedCount / totalFiles) * 100) : 0}% ({scannedCount}/{totalFiles})
              </span>
            </div>
            <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800">
              <div
                className="h-full bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 rounded-full transition-all duration-300 shadow-md shadow-cyan-500/50"
                style={{ width: `${totalFiles > 0 ? (scannedCount / totalFiles) * 100 : 0}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Row 2: Dashboard Insights Section (Time Filtered Analytics & Library Dividers) */}
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-cyan-400" />
              Scan History & Time-Based Insights
            </h3>
            <p className="text-xs text-slate-400">Filter scanned data and folders by custom date ranges and library events.</p>
          </div>

          {/* Time Range Selector Buttons */}
          <div className="flex items-center bg-slate-900/90 rounded-xl p-1 border border-slate-800 text-xs font-semibold">
            <button
              onClick={() => setActiveTimeRange('7d')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTimeRange === '7d' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              Last 7 Days
            </button>
            <button
              onClick={() => setActiveTimeRange('15d')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTimeRange === '15d' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              Last 15 Days
            </button>
            <button
              onClick={() => setActiveTimeRange('monthly')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTimeRange === 'monthly' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              Monthly Data
            </button>
            <button
              onClick={() => setActiveTimeRange('yearly')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTimeRange === 'yearly' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              Yearly Data
            </button>
            <button
              onClick={() => setActiveTimeRange('all')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTimeRange === 'all' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              All Time
            </button>
          </div>
        </div>

        {/* Selected Time-Range Highlight Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-xl text-purple-400">
              <Calendar className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-white">Metrics for {activeMetrics.label}</h4>
              <p className="text-xs text-slate-400">Summary of total scan sessions and photos processed during this timeframe.</p>
            </div>
          </div>
          <div className="flex items-center gap-8 font-mono">
            <div className="text-right">
              <span className="text-lg font-bold text-cyan-400">{activeMetrics.sessions}</span>
              <p className="text-[10px] uppercase text-slate-500">Scan Sessions</p>
            </div>
            <div className="text-right">
              <span className="text-lg font-bold text-purple-400">{activeMetrics.photos}</span>
              <p className="text-[10px] uppercase text-slate-500">Photos Scanned</p>
            </div>
          </div>
        </div>

        {/* Breakdown of Scanned Images & Folders Divided by Event Library Name */}
        <div className="space-y-4">
          <h4 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            Scanned Images & Folders Divided by Library Name
          </h4>

          {insights.libraries && insights.libraries.length > 0 ? (
            <div className="grid grid-cols-3 gap-4">
              {insights.libraries.map((lib, idx) => (
                <div key={idx} className="glazzed-glass rounded-2xl p-5 border border-slate-800 hover:border-purple-500/50 transition-all space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="text-sm font-bold text-purple-300 font-mono flex items-center gap-2 truncate">
                      <Library className="w-4 h-4 text-purple-400 shrink-0" />
                      {lib.library_name}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300">
                      {lib.session_count} Scans
                    </span>
                  </div>

                  <div className="space-y-1.5 text-xs font-mono text-slate-300">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Source Directory:</span>
                      <span className="text-slate-300 truncate max-w-[150px]" title={lib.source_dir}>{lib.source_dir}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Scanned Photos:</span>
                      <span className="text-cyan-400 font-bold">{lib.total_photos} photos</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Faces Found:</span>
                      <span className="text-emerald-400 font-bold">{lib.total_faces} faces</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800/60 text-[10px] text-slate-500 flex justify-between font-mono">
                    <span>Last Scanned:</span>
                    <span>{lib.last_scanned ? new Date(lib.last_scanned).toLocaleDateString() : 'Recent'}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800/80 text-center text-xs text-slate-500">
              No event libraries recorded yet. Enter an Event Library Name and run a scan above!
            </div>
          )}
        </div>

        {/* Customer / Event Scan Session Timelines */}
        <div className="space-y-4">
          <h4 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
            <Clock className="w-4 h-4 text-emerald-400" />
            Customer Event Timelines (Recent Scan Sessions)
          </h4>

          {insights.sessions && insights.sessions.length > 0 ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] font-mono border-b border-slate-800">
                  <tr>
                    <th className="p-3">Library / Event</th>
                    <th className="p-3">Source Directory</th>
                    <th className="p-3">Photos</th>
                    <th className="p-3">Faces</th>
                    <th className="p-3">Persons</th>
                    <th className="p-3">Scanned Date</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 font-mono text-[11px]">
                  {insights.sessions.map((sess) => (
                    <tr key={sess.session_id} className="hover:bg-cyan-950/20 transition-colors">
                      <td className="p-3 font-bold text-purple-300">{sess.library_name || 'Event Library'}</td>
                      <td className="p-3 text-slate-400 max-w-[200px] truncate" title={sess.source_dir}>{sess.source_dir}</td>
                      <td className="p-3 text-cyan-400 font-bold">{sess.photos_count}</td>
                      <td className="p-3 text-emerald-400 font-bold">{sess.faces_count}</td>
                      <td className="p-3 text-purple-400 font-bold">{sess.persons_count}</td>
                      <td className="p-3 text-slate-400">{sess.scanned_at ? new Date(sess.scanned_at).toLocaleString() : 'Just now'}</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300">
                          {sess.status || 'Completed'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800/80 text-center text-xs text-slate-500">
              No recent customer event scan timelines logged yet.
            </div>
          )}
        </div>
      </div>

      {/* Row 3: Identified People & Scanned Media Tables */}
      <div className="grid grid-cols-12 gap-6">
        {/* Identified People Cards (5 cols) */}
        <div className="col-span-5 glazzed-glass rounded-2xl p-6">
          <div className="flex items-center justify-between border-b border-slate-800/60 pb-3 mb-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Users className="w-4 h-4 text-purple-400" />
              Identified Persons ({filteredPersons.length})
            </h3>
            <button onClick={() => onNavigate('people')} className="text-xs text-cyan-400 hover:underline flex items-center gap-1 font-semibold">
              View All <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {filteredPersons.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No matching person profiles identified.
            </div>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
              {filteredPersons.map((p) => (
                <div key={p.person_id} className="flex items-center justify-between p-3 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-cyan-500/40 transition-all group">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-full border border-cyan-500/50 overflow-hidden bg-slate-950 shrink-0 shadow">
                      <img
                        src={`/api/person_thumbnail/${p.person_id}`}
                        alt={p.display_name}
                        className="w-full h-full object-cover"
                        onError={(e) => { e.target.src = 'https://via.placeholder.com/100?text=Face' }}
                      />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white">{p.display_name}</h4>
                      <p className="text-[10px] text-slate-400 font-mono">{p.face_count} face photos</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onDeletePerson(p.person_id)}
                      title="Delete person profile"
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>

                    <button
                      onClick={() => onNavigate('people')}
                      className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-cyan-600 text-slate-300 hover:text-white text-xs font-semibold transition-all"
                    >
                      Inspect
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Media Table (7 cols) with Lightbox Trigger */}
        <div className="col-span-7 glazzed-glass rounded-2xl p-6">
          <div className="flex items-center justify-between border-b border-slate-800/60 pb-3 mb-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <FileImage className="w-4 h-4 text-cyan-400" />
              Scanned Media Table ({filteredImages.length})
            </h3>
            <span className="text-[10px] font-mono text-slate-400">Click photo to view Lightbox</span>
          </div>

          {filteredImages.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No photo records in local database. Run a folder scan to populate images.
            </div>
          ) : (
            <div className="overflow-x-auto max-h-80 overflow-y-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] font-mono sticky top-0">
                  <tr>
                    <th className="p-2.5">File Name</th>
                    <th className="p-2.5">Faces</th>
                    <th className="p-2.5">Size</th>
                    <th className="p-2.5">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 font-mono text-[11px]">
                  {filteredImages.slice(0, 15).map((img) => (
                    <tr
                      key={img.image_id}
                      onClick={() => onSelectImageForLightbox(img)}
                      className="hover:bg-cyan-950/40 cursor-pointer transition-colors group"
                    >
                      <td className="p-2.5 font-bold text-white max-w-[180px] truncate group-hover:text-cyan-400" title={img.file_name}>
                        {img.file_name}
                      </td>
                      <td className="p-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          img.face_count > 0 ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-400'
                        }`}>
                          {img.face_count} faces
                        </span>
                      </td>
                      <td className="p-2.5 text-slate-400">
                        {(img.file_size / (1024 * 1024)).toFixed(2)} MB
                      </td>
                      <td className="p-2.5">
                        <button className="text-slate-400 group-hover:text-cyan-400 flex items-center gap-1 font-semibold text-[10px]">
                          <Maximize2 className="w-3 h-3" /> Lightbox
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
