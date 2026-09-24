import React from 'react'
import {
  LayoutGrid,
  HardDrive,
  Users,
  Heart,
  UserCheck,
  History,
  Sliders,
  Bell,
  Mail,
  User,
  ShieldCheck
} from 'lucide-react'

export default function Sidebar({ activeTab, setActiveTab, stats = {} }) {
  const { totalFiles = 0, facesFound = 0, personsCount = 0 } = stats

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutGrid },
    { id: 'people', label: 'Identified People', icon: Users, badge: personsCount },
    { id: 'couple', label: 'Groom & Bride Filter', icon: Heart },
    { id: 'groups', label: 'Group Photos', icon: UserCheck },
    { id: 'logs', label: 'Sorting Logs & Undo', icon: History }
  ]

  return (
    <aside className="w-64 h-screen sticky top-0 glazzed-glass-sidebar flex flex-col justify-between z-30 shrink-0 select-none">
      <div>
        {/* App / Profile Header Section */}
        <div className="px-6 py-6 text-center border-b border-slate-800/60">
          <div className="relative inline-block mb-3">
            <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-cyan-400 via-blue-500 to-purple-600 shadow-xl shadow-cyan-500/20 mx-auto flex items-center justify-center p-1">
              <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center">
                <User className="w-10 h-10 text-cyan-400" />
              </div>
            </div>
            <span className="absolute bottom-1 right-1 w-4 h-4 rounded-full bg-emerald-500 border-2 border-slate-900 shadow-md" title="Offline AI Active"></span>
          </div>

          <h2 className="text-base font-bold text-white tracking-wide">FaceOrganizer AI</h2>
          <p className="text-xs text-slate-400 font-medium flex items-center justify-center gap-1 mt-0.5">
            <ShieldCheck className="w-3 h-3 text-cyan-400" />
            Offline ONNX Engine
          </p>

          {/* Quick Metrics Bar Under Avatar */}
          <div className="grid grid-cols-3 gap-1 mt-5 pt-4 border-t border-slate-800/40 text-center">
            <div>
              <p className="text-sm font-bold text-white">{totalFiles > 1000 ? `${(totalFiles/1000).toFixed(1)}k` : totalFiles}</p>
              <p className="text-[10px] uppercase font-semibold text-slate-500">Photos</p>
            </div>
            <div>
              <p className="text-sm font-bold text-cyan-400">{facesFound > 1000 ? `${(facesFound/1000).toFixed(1)}k` : facesFound}</p>
              <p className="text-[10px] uppercase font-semibold text-slate-500">Faces</p>
            </div>
            <div>
              <p className="text-sm font-bold text-purple-400">{personsCount}</p>
              <p className="text-[10px] uppercase font-semibold text-slate-500">People</p>
            </div>
          </div>
        </div>

        {/* Navigation Menu Links */}
        <nav className="py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id

            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full px-6 py-3.5 flex items-center justify-between text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'glazzed-active-tab'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                    isActive ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Footer Branding */}
      <div className="p-6 border-t border-slate-800/60 text-center">
        <h3 className="text-sm font-black tracking-widest text-slate-300 uppercase">Status</h3>
        <p className="text-[10px] text-slate-500 mt-0.5">© 2026 AI Photo Organizer</p>
      </div>
    </aside>
  )
}
