import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { X, Trash2, UserCheck, ShieldAlert, FileImage, Calendar, HardDrive } from 'lucide-react'

export default function Lightbox({ image, persons, onClose, onDeleteFace, onReassignFace }) {
  const [faces, setFaces] = useState([])
  const [selectedFace, setSelectedFace] = useState(null)
  const [targetPersonId, setTargetPersonId] = useState('')

  useEffect(() => {
    if (image?.image_id) {
      fetchFaces(image.image_id)
    }
  }, [image])

  const fetchFaces = async (imageId) => {
    try {
      const res = await axios.get(`/api/images/${imageId}/faces`)
      setFaces(res.data)
    } catch (err) {
      console.error('Failed to fetch image faces:', err)
    }
  }

  const handleDelete = async (faceId) => {
    await onDeleteFace(faceId)
    fetchFaces(image.image_id)
    setSelectedFace(null)
  }

  const handleReassign = async (faceId) => {
    if (targetPersonId) {
      await onReassignFace(faceId, targetPersonId)
      fetchFaces(image.image_id)
      setSelectedFace(null)
    }
  }

  if (!image) return null

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md flex items-center justify-center p-6 animate-fadeIn">
      <div className="relative w-full max-w-6xl max-h-[90vh] glazzed-glass rounded-2xl border border-slate-700/60 overflow-hidden flex flex-col shadow-2xl">
        {/* Lightbox Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileImage className="w-5 h-5 text-cyan-400" />
            <div>
              <h3 className="text-sm font-bold text-white max-w-lg truncate">{image.file_name}</h3>
              <p className="text-[10px] text-slate-400 font-mono">{image.file_path}</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white flex items-center justify-center transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Lightbox Body */}
        <div className="grid grid-cols-12 flex-1 overflow-hidden">
          {/* Main Image Stage with SVG Bounding Box Overlays */}
          <div className="col-span-8 bg-black/80 p-4 flex items-center justify-center relative overflow-hidden">
            <div className="relative max-h-full max-w-full inline-block">
              <img
                src={`/api/image?path=${encodeURIComponent(image.file_path)}`}
                alt={image.file_name}
                className="max-h-[70vh] max-w-full object-contain rounded"
              />

              {/* Face Bounding Box SVG Overlays */}
              {faces.map((f) => {
                // Calculate percentage coordinates
                const left = (f.bbox_x / image.width) * 100
                const top = (f.bbox_y / image.height) * 100
                const width = (f.bbox_w / image.width) * 100
                const height = (f.bbox_h / image.height) * 100
                const isSelected = selectedFace?.face_id === f.face_id

                return (
                  <div
                    key={f.face_id}
                    onClick={() => setSelectedFace(f)}
                    style={{
                      left: `${left}%`,
                      top: `${top}%`,
                      width: `${width}%`,
                      height: `${height}%`
                    }}
                    className={`absolute border-2 cursor-pointer transition-all ${
                      isSelected
                        ? 'border-cyan-400 bg-cyan-400/20 shadow-lg shadow-cyan-400/50 z-20 scale-105'
                        : 'border-emerald-400/80 hover:border-cyan-400 hover:bg-cyan-400/10 z-10'
                    }`}
                  >
                    <span className="absolute -top-5 left-0 bg-slate-900/90 border border-emerald-500/50 text-emerald-300 font-mono text-[9px] font-bold px-1.5 py-0.5 rounded shadow">
                      {f.person_id || 'Face'} ({(f.confidence * 100).toFixed(0)}%)
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Right Inspector & Manual Override Panel */}
          <div className="col-span-4 p-6 border-l border-slate-800 space-y-6 overflow-y-auto bg-slate-900/40">
            {/* Metadata Section */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-slate-800 pb-2">
                Photo Metadata
              </h4>
              <div className="space-y-2 text-xs font-mono text-slate-300">
                <div className="flex justify-between">
                  <span className="text-slate-500">Resolution:</span>
                  <span>{image.width} × {image.height} px</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">File Size:</span>
                  <span>{(image.file_size / (1024 * 1024)).toFixed(2)} MB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Faces Found:</span>
                  <span className="text-cyan-400 font-bold">{faces.length}</span>
                </div>
                {image.datetime_taken && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Date Taken:</span>
                    <span>{image.datetime_taken}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Selected Face Manual Override */}
            {selectedFace ? (
              <div className="p-4 rounded-xl bg-slate-900/80 border border-cyan-500/40 space-y-4">
                <div className="flex items-center gap-3">
                  <img
                    src={`/api/thumbnail/${selectedFace.face_id}`}
                    alt="Face crop"
                    className="w-12 h-12 rounded-full border border-cyan-400 object-cover"
                    onError={(e) => { e.target.src = 'https://via.placeholder.com/100?text=Face' }}
                  />
                  <div>
                    <h5 className="text-xs font-bold text-white">{selectedFace.person_id || 'Unassigned Face'}</h5>
                    <p className="text-[10px] text-emerald-400 font-mono">
                      Confidence: {(selectedFace.confidence * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* Reassign Person Selector */}
                <div className="space-y-2">
                  <label className="block text-[11px] font-semibold text-slate-300">Reassign to Person Profile</label>
                  <select
                    value={targetPersonId}
                    onChange={(e) => setTargetPersonId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
                  >
                    <option value="">Select target person...</option>
                    {persons.map((p) => (
                      <option key={p.person_id} value={p.person_id}>
                        {p.display_name} ({p.person_id})
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleReassign(selectedFace.face_id)}
                    disabled={!targetPersonId}
                    className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white font-bold text-xs py-2 rounded-lg transition-all"
                  >
                    Reassign Face Profile
                  </button>
                </div>

                {/* Delete False Positive Button */}
                <button
                  onClick={() => handleDelete(selectedFace.face_id)}
                  className="w-full bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-500/40 font-bold text-xs py-2 rounded-lg transition-all flex items-center justify-center gap-2"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete False Positive Face
                </button>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500">
                Click any face bounding box on the image to reassign or delete.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
