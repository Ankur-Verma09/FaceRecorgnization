import React, { useState, useEffect } from 'react'
import axios from 'axios'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import OverviewDashboard from './components/OverviewDashboard'
import PersonGallery from './components/PersonGallery'
import CoupleFilterWizard from './components/CoupleFilterWizard'
import GroupPhotosManager from './components/GroupPhotosManager'
import Lightbox from './components/Lightbox'
import ExportProgressModal from './components/ExportProgressModal'
import { RotateCcw, CheckCircle2, AlertCircle } from 'lucide-react'

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedImageForLightbox, setSelectedImageForLightbox] = useState(null)
  const [scanStatus, setScanStatus] = useState({
    status: 'idle',
    scanned_count: 0,
    total_files: 0,
    current_file: '',
    total_faces_found: 0,
    persons_count: 0,
    message: ''
  })
  const [exportStatus, setExportStatus] = useState({
    status: 'idle',
    exported_count: 0,
    total_files: 0,
    current_file: '',
    target_dir: ''
  })
  const [persons, setPersons] = useState([])
  const [selectedForCouple, setSelectedForCouple] = useState([])
  const [lastManifestId, setLastManifestId] = useState(null)
  const [notification, setNotification] = useState(null)
  const [scanOptions, setScanOptions] = useState({
    sourceDir: '',
    targetDir: '',
    libraryName: '',
    operationMode: 'copy'
  })

  const [manifests, setManifests] = useState([])

  // WebSocket for real-time scan and export progress stream
  useEffect(() => {
    let ws
    let reconnectTimer
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/progress`

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(wsUrl)
        ws.onopen = () => {
          console.log('WebSocket connected')
        }
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)
          if (data.status === 'exporting' || data.status === 'export_completed') {
            setExportStatus(data)
            if (data.manifest_id) {
              setLastManifestId(data.manifest_id)
              fetchManifests() // Refresh manifests on completion
            }
          } else {
            setScanStatus(data)
            if (data.status === 'completed') {
              fetchPersons()
            }
          }
        }
        ws.onclose = () => {
          console.warn('WebSocket disconnected. Attempting to reconnect...')
          reconnectTimer = setTimeout(connectWebSocket, 3000)
        }
        ws.onerror = (err) => {
          console.error('WebSocket error:', err)
          ws.close()
        }
      } catch (err) {
        console.warn('WebSocket connection error:', err)
      }
    }

    connectWebSocket()

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (ws) {
        ws.onclose = null // Prevent reconnect on unmount
        ws.close()
      }
    }
  }, [])

  const fetchPersons = async () => {
    try {
      const res = await axios.get('/api/persons')
      setPersons(res.data)
    } catch (err) {
      console.error('Failed to fetch persons:', err)
    }
  }

  const fetchManifests = async () => {
    try {
      const res = await axios.get('/api/organize/manifests')
      setManifests(res.data)
    } catch (err) {
      console.error('Failed to fetch manifests:', err)
    }
  }

  useEffect(() => {
    fetchPersons()
    fetchManifests()
  }, [])

  // Listen for unmerge events from PersonGallery child component
  useEffect(() => {
    const handler = () => fetchPersons()
    window.addEventListener('unmerge-complete', handler)
    return () => window.removeEventListener('unmerge-complete', handler)
  }, [])

  const handleStartScan = async ({ sourceDir, targetDir, libraryName, operationMode }) => {
    setScanOptions({ sourceDir, targetDir, libraryName: libraryName || '', operationMode })
    try {
      await axios.post('/api/scan/start', { source_dir: sourceDir, library_name: libraryName || '' })
      setScanStatus((prev) => ({ ...prev, status: 'scanning', message: '' }))
    } catch (err) {
      showNotification('error', err.response?.data?.detail || 'Failed to start folder scan.')
    }
  }

  const handleCancelScan = async () => {
    try {
      await axios.post('/api/scan/cancel')
      setScanStatus((prev) => ({ ...prev, status: 'cancelled', message: 'Scan stopped by user.' }))
      showNotification('success', 'Stopped scan process.')
    } catch (err) {
      showNotification('error', 'Failed to cancel scan.')
    }
  }

  const handleRenamePerson = async (personId, newName) => {
    try {
      await axios.post('/api/persons/rename', { person_id: personId, new_name: newName })
      fetchPersons()
      showNotification('success', `Renamed profile to "${newName}"`)
    } catch (err) {
      showNotification('error', 'Failed to rename person.')
    }
  }

  const handleDeletePerson = async (personId) => {
    try {
      await axios.post('/api/persons/delete', { person_id: personId })
      fetchPersons()
      showNotification('success', 'Deleted identified person profile.')
    } catch (err) {
      showNotification('error', 'Failed to delete person profile.')
    }
  }

  const handleMergePersons = async (sourceId, targetId) => {
    try {
      await axios.post('/api/persons/merge', { source_person_id: sourceId, target_person_id: targetId })
      fetchPersons()
      showNotification('success', 'Merged person profiles successfully.')
    } catch (err) {
      showNotification('error', 'Failed to merge profiles.')
    }
  }

  const handleRecluster = async (distanceThreshold) => {
    try {
      const res = await axios.post('/api/persons/recluster', { distance_threshold: distanceThreshold })
      fetchPersons()
      showNotification('success', `Re-clustered faces into ${res.data.persons_count} person profiles matching pose angles!`)
    } catch (err) {
      showNotification('error', 'Failed to recluster faces.')
    }
  }

  const handleResetWorkspace = async () => {
    if (window.confirm('Are you sure you want to clear cache and reset workspace for a new photo folder?')) {
      try {
        await axios.post('/api/workspace/reset')
        setPersons([])
        setManifests([])
        setLastManifestId(null)
        setScanStatus({
          status: 'idle',
          scanned_count: 0,
          total_files: 0,
          current_file: '',
          total_faces_found: 0,
          persons_count: 0,
          message: ''
        })
        showNotification('success', 'Workspace reset complete. Ready for new photo scan.')
      } catch (err) {
        showNotification('error', 'Failed to reset workspace.')
      }
    }
  }

  const handleDeleteFace = async (faceId) => {
    try {
      await axios.post('/api/faces/delete', { face_id: faceId })
      fetchPersons()
      showNotification('success', 'Deleted false positive face detection.')
    } catch (err) {
      showNotification('error', 'Failed to delete face.')
    }
  }

  const handleReassignFace = async (faceId, targetPersonId) => {
    try {
      await axios.post('/api/faces/reassign', { face_id: faceId, target_person_id: targetPersonId })
      fetchPersons()
      showNotification('success', 'Reassigned face to person profile.')
    } catch (err) {
      showNotification('error', 'Failed to reassign face.')
    }
  }

  const handleExecuteOrganize = async (customParams = {}) => {
    const targetDir = customParams.target_dir || scanOptions.targetDir || (scanOptions.sourceDir ? `${scanOptions.sourceDir}_Organized` : '')
    const libName = customParams.library_name !== undefined ? customParams.library_name : (scanOptions.libraryName || '')
    if (!targetDir) {
      showNotification('error', 'Please specify or browse to a Target Export Directory.')
      return
    }
    try {
      const payload = {
        target_dir: targetDir,
        library_name: libName,
        operation_mode: scanOptions.operationMode,
        couple_pair: customParams.couple_pair || (selectedForCouple.length === 2 ? selectedForCouple : null),
        couple_folder_name: customParams.couple_folder_name || 'Groom_and_Bride',
        group_threshold: 3
      }

      setExportStatus({ status: 'exporting', exported_count: 0, total_files: 0, current_file: '', target_dir: targetDir })
      await axios.post('/api/organize/execute', payload)
    } catch (err) {
      showNotification('error', err.response?.data?.detail || 'Organization failed.')
    }
  }

  const handleUndo = async (manifestId) => {
    const targetManifestId = typeof manifestId === 'string' ? manifestId : lastManifestId;
    if (!targetManifestId) return
    try {
      const res = await axios.post('/api/organize/undo', { manifest_id: targetManifestId })
      showNotification('success', `Undo complete! Restored ${res.data.restored_count} files.`)
      if (targetManifestId === lastManifestId) setLastManifestId(null)
      fetchManifests()
    } catch (err) {
      showNotification('error', 'Failed to undo operation.')
    }
  }

  const showNotification = (type, message) => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 5000)
  }

  const getHeaderTitles = () => {
    switch (activeTab) {
      case 'dashboard':
        return { title: 'Dashboard', subtitle: 'Home > Dashboard' }
      case 'scan':
        return { title: 'Folder Scanning', subtitle: 'Home > Folder Scan & Identification' }
      case 'people':
        return { title: 'Identified People Gallery', subtitle: 'Home > Identified Persons' }
      case 'couple':
        return { title: 'Groom & Bride Couple Selector', subtitle: 'Home > Custom Couple Filter' }
      case 'groups':
        return { title: 'Group & Scenery Manager', subtitle: 'Home > Group Photo Settings' }
      case 'logs':
        return { title: 'Sorting Audit Logs & Undo', subtitle: 'Home > Organization Manifests' }
      default:
        return { title: 'Dashboard', subtitle: 'Home > Dashboard' }
    }
  }

  const titles = getHeaderTitles()

  const stats = {
    totalFiles: scanStatus.total_files,
    facesFound: scanStatus.total_faces_found,
    personsCount: persons.length,
    scannedCount: scanStatus.scanned_count
  }

  return (
    <div className="flex min-h-screen bg-[#070c18] text-slate-100 font-sans selection:bg-cyan-500 selection:text-slate-950">
      {/* Left Sidebar Navigation */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} stats={stats} />

      {/* Right Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          title={titles.title}
          subtitle={titles.subtitle}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onResetWorkspace={handleResetWorkspace}
        />

        {/* Top Notification Toast */}
        {notification && (
          <div className="fixed top-20 right-8 z-50 animate-bounce">
            <div
              className={`px-5 py-3 rounded-xl shadow-2xl border flex items-center gap-3 text-sm font-semibold glazzed-glass ${
                notification.type === 'success'
                  ? 'border-emerald-500/50 text-emerald-300'
                  : 'border-rose-500/50 text-rose-300'
              }`}
            >
              {notification.type === 'success' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-rose-400" />
              )}
              <span>{notification.message}</span>
            </div>
          </div>
        )}

        {/* Dynamic Page Views */}
        <main className="flex-1 p-8 overflow-y-auto">
          {activeTab === 'dashboard' && (
            <OverviewDashboard
              stats={stats}
              persons={persons}
              onNavigate={setActiveTab}
              scanStatus={scanStatus}
              onStartScan={handleStartScan}
              onCancelScan={handleCancelScan}
              onExecuteOrganize={handleExecuteOrganize}
              onDeletePerson={handleDeletePerson}
              searchQuery={searchQuery}
              onSelectImageForLightbox={setSelectedImageForLightbox}
            />
          )}

          {activeTab === 'people' && (
            <PersonGallery
              persons={persons.filter((p) => p.display_name.toLowerCase().includes(searchQuery.toLowerCase()))}
              onRenamePerson={handleRenamePerson}
              onMergePersons={handleMergePersons}
              onDeletePerson={handleDeletePerson}
              onRecluster={handleRecluster}
              selectedForCouple={selectedForCouple}
              setSelectedForCouple={setSelectedForCouple}
            />
          )}

          {activeTab === 'couple' && (
            <CoupleFilterWizard
              persons={persons}
              selectedForCouple={selectedForCouple}
              onExecuteOrganize={handleExecuteOrganize}
            />
          )}

          {activeTab === 'groups' && (
            <GroupPhotosManager onExecuteOrganize={handleExecuteOrganize} />
          )}

          {activeTab === 'logs' && (
            <div className="glazzed-glass rounded-2xl p-8 max-w-4xl mx-auto space-y-4">
              <h2 className="text-xl font-bold text-white">Sorting Audit Trail</h2>
              <p className="text-xs text-slate-400">All file moves, copies, and symlink operations are recorded in SQLite manifests for 1-click reversal.</p>
              
              {manifests.length > 0 ? (
                <div className="space-y-3 mt-6">
                  {manifests.map((manifest) => (
                    <div key={manifest.manifest_id} className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-bold text-white mb-1">Manifest ID: <span className="text-cyan-400 font-mono text-xs">{manifest.manifest_id}</span></p>
                        <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-slate-400">
                          <span>Target: <span className="text-slate-300">{manifest.target_dir}</span></span>
                          <span className="w-1 h-1 rounded-full bg-slate-700"></span>
                          <span>Mode: <span className="text-purple-400 uppercase font-bold">{manifest.operation_mode}</span></span>
                          <span className="w-1 h-1 rounded-full bg-slate-700"></span>
                          <span>Time: <span className="text-emerald-400">{new Date(manifest.created_at).toLocaleString()}</span></span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleUndo(manifest.manifest_id)}
                        className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-amber-600 text-slate-300 hover:text-white font-bold text-xs flex items-center justify-center gap-2 transition-all border border-slate-700 hover:border-amber-500"
                      >
                        <RotateCcw className="w-3.5 h-3.5" /> Undo This Action
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic mt-6 bg-slate-900/50 p-6 rounded-xl text-center border border-slate-800">No sorting manifests have been generated yet.</p>
              )}
            </div>
          )}
        </main>

        {/* Lightbox Modal Component */}
        {selectedImageForLightbox && (
          <Lightbox
            image={selectedImageForLightbox}
            persons={persons}
            onClose={() => setSelectedImageForLightbox(null)}
            onDeleteFace={handleDeleteFace}
            onReassignFace={handleReassignFace}
          />
        )}

        {/* Real-time Export Progress Modal */}
        {exportStatus.status !== 'idle' && (
          <ExportProgressModal
            exportStatus={exportStatus}
            onClose={() => setExportStatus({ status: 'idle', exported_count: 0, total_files: 0, current_file: '', target_dir: '' })}
          />
        )}
      </div>

      {/* Bottom Floating Bar for Undo */}
      {lastManifestId && (
        <div className="fixed bottom-6 right-6 z-50">
          <button
            onClick={handleUndo}
            className="bg-amber-600 hover:bg-amber-500 text-white font-bold px-5 py-3 rounded-xl shadow-2xl border border-amber-400/40 flex items-center gap-2 text-sm transition-all shadow-amber-600/30"
          >
            <RotateCcw className="w-4 h-4" />
            Undo Last Photo Sorting Action
          </button>
        </div>
      )}
    </div>
  )
}
