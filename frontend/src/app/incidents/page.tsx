"use client"

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { AlertTriangle, Info, Clock, Activity, BrainCircuit } from 'lucide-react'

// Dummy data for testing the UI
const MOCK_INCIDENTS = [
  {
    id: 'inc-1',
    severity: 'critical',
    detected_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(), // 5 mins ago
    resolved_at: null,
    explanation: 'A massive BGP route leak occurred from AS3356 affecting transit routes globally, causing severe packet loss across multiple probe targets.',
    incident_metadata: {
      asn: 3356,
      signals: {
        gnn_score: 0.98,
        latency_z_score: 5.2,
        bgp_churn_count: 145
      }
    }
  },
  {
    id: 'inc-2',
    severity: 'medium',
    detected_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2 hours ago
    resolved_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    explanation: 'Transient edge jitter detected due to localized ISP maintenance in AS701. No cascading topological failure predicted.',
    incident_metadata: {
      asn: 701,
      signals: {
        gnn_score: 0.24,
        latency_z_score: 4.1,
        bgp_churn_count: 0
      }
    }
  }
]

// Dummy time-series data for the chart
const CHART_DATA = Array.from({ length: 30 }).map((_, i) => ({
  time: `10:${i.toString().padStart(2, '0')}`,
  latency: i > 15 ? 180 + Math.random() * 40 : 40 + Math.random() * 10
}))

import { filterAndSortIncidents } from '@/lib/incidentUtils'

export default function IncidentsDashboard() {
  const [selectedId, setSelectedId] = useState<string | null>(MOCK_INCIDENTS[0].id)
  const [filter, setFilter] = useState<'all' | 'active' | 'resolved'>('all')
  const [sort, setSort] = useState<'newest' | 'oldest' | 'severity'>('newest')
  
  const selected = MOCK_INCIDENTS.find(i => i.id === selectedId)
  const displayedIncidents = filterAndSortIncidents(MOCK_INCIDENTS, filter, sort)

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-zinc-950 text-white overflow-hidden">
      
      {/* Left Pane: List */}
      <div className="w-1/3 border-r border-zinc-800 flex flex-col bg-zinc-900/50">
        <div className="p-4 border-b border-zinc-800 bg-zinc-900">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              Detected Incidents
            </h2>
          </div>
          <div className="flex gap-2 mb-2">
            <select 
              className="bg-zinc-800 border border-zinc-700 text-xs p-2 rounded text-zinc-300 outline-none flex-1"
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
            >
              <option value="all">All Statuses</option>
              <option value="active">Active Only</option>
              <option value="resolved">Resolved</option>
            </select>
            <select 
              className="bg-zinc-800 border border-zinc-700 text-xs p-2 rounded text-zinc-300 outline-none flex-1"
              value={sort}
              onChange={(e) => setSort(e.target.value as any)}
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="severity">Highest Severity</option>
            </select>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {displayedIncidents.map((inc) => (
            <motion.button
              key={inc.id}
              onClick={() => setSelectedId(inc.id)}
              whileHover={{ scale: 0.98 }}
              className={`w-full text-left p-4 rounded-xl border transition-colors ${
                selectedId === inc.id 
                  ? 'bg-zinc-800 border-zinc-600' 
                  : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <span className={`px-2 py-1 text-xs font-bold rounded-md ${
                  inc.severity === 'critical' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
                }`}>
                  {inc.severity.toUpperCase()}
                </span>
                <span className="text-zinc-500 text-xs">
                  {new Date(inc.detected_at).toLocaleTimeString()}
                </span>
              </div>
              <h3 className="font-medium text-sm">AS{inc.incident_metadata.asn} Anomaly</h3>
              <p className="text-zinc-400 text-xs mt-1 truncate">{inc.explanation}</p>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Right Pane: Detail */}
      <div className="w-2/3 flex flex-col relative">
        <AnimatePresence mode="wait">
          {selected ? (
            <motion.div 
              key={selected.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="p-8 h-full overflow-y-auto"
            >
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h1 className="text-3xl font-bold mb-2">AS{selected.incident_metadata.asn} Investigation</h1>
                  <div className="flex items-center gap-4 text-sm text-zinc-400">
                    <span className="flex items-center gap-1"><Clock className="w-4 h-4"/> Detected: {new Date(selected.detected_at).toLocaleString()}</span>
                    <span className="flex items-center gap-1">
                      <Activity className="w-4 h-4"/> 
                      Status: {selected.resolved_at ? <span className="text-emerald-400">Resolved</span> : <span className="text-red-400 animate-pulse">Active</span>}
                    </span>
                  </div>
                </div>
              </div>

              {/* LLM Explanation Card */}
              <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/10 border border-indigo-500/30 rounded-2xl p-6 mb-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-6 opacity-10">
                  <BrainCircuit className="w-24 h-24" />
                </div>
                <h3 className="text-indigo-300 font-semibold mb-3 flex items-center gap-2">
                  <BrainCircuit className="w-5 h-5" />
                  Anthropic Root Cause Analysis
                </h3>
                <p className="text-zinc-200 leading-relaxed relative z-10">
                  {selected.explanation}
                </p>
              </div>

              {/* Signal Metrics */}
              <div className="grid grid-cols-3 gap-4 mb-8">
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                  <p className="text-zinc-500 text-sm mb-1">GNN Prediction Score</p>
                  <p className={`text-2xl font-bold ${selected.incident_metadata.signals.gnn_score > 0.8 ? 'text-red-400' : 'text-zinc-300'}`}>
                    {(selected.incident_metadata.signals.gnn_score * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                  <p className="text-zinc-500 text-sm mb-1">Latency Z-Score</p>
                  <p className="text-2xl font-bold text-amber-400">
                    {selected.incident_metadata.signals.latency_z_score.toFixed(1)}σ
                  </p>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                  <p className="text-zinc-500 text-sm mb-1">BGP Churn (Window)</p>
                  <p className="text-2xl font-bold text-zinc-300">
                    {selected.incident_metadata.signals.bgp_churn_count} events
                  </p>
                </div>
              </div>

              {/* Chart */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 h-80">
                <h3 className="text-zinc-300 font-medium mb-4 flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  Telemetry Timeline (Probe Context)
                </h3>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={CHART_DATA}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} />
                    <XAxis dataKey="time" stroke="#a1a1aa" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#a1a1aa" fontSize={12} tickLine={false} axisLine={false} unit="ms" />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                      itemStyle={{ color: '#e4e4e7' }}
                    />
                    <ReferenceLine x="10:15" stroke="#ef4444" strokeDasharray="3 3" label={{ position: 'top', value: 'Incident Detected', fill: '#ef4444', fontSize: 12 }} />
                    <Line type="monotone" dataKey="latency" stroke="#3b82f6" strokeWidth={2} dot={false} activeDot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

            </motion.div>
          ) : (
            <div className="h-full flex items-center justify-center text-zinc-500 flex-col gap-4">
              <Info className="w-12 h-12 opacity-50" />
              <p>Select an incident to view investigation details.</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
