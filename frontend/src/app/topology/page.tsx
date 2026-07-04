"use client"

import { useEffect, useMemo, useState } from 'react'
import dynamic from 'next/dynamic'
import { useNetPulseStore } from '@/lib/store'

// React Force Graph requires client-side rendering only due to Canvas
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false })

// Generate a dummy AS topology for the visual scale demonstration 
// (In production, this is fetched from `GET /api/topology/graph`)
const generateMockTopology = (numNodes = 1000) => {
  const nodes = Array.from({ length: numNodes }).map((_, i) => ({
    id: i,
    val: Math.random() * 5 + 1, // Determines size
    name: `AS${i + 10000}`,
    isAnomalous: Math.random() > 0.98
  }))
  
  const links = []
  for (let i = 1; i < numNodes; i++) {
    links.push({
      source: i,
      target: Math.floor(Math.random() * i), // Preferential attachment (scale-free)
      type: Math.random() > 0.8 ? 'provider' : 'peer'
    })
  }
  return { nodes, links }
}

export default function TopologyGraph() {
  const [data, setData] = useState({ nodes: [], links: [] })
  const { incidents } = useNetPulseStore()

  useEffect(() => {
    // Simulate fetching the 5,000 node graph
    setData(generateMockTopology(2000))
  }, [])

  return (
    <div className="w-full h-[calc(100vh-4rem)] bg-zinc-950 relative overflow-hidden">
      <ForceGraph2D
        graphData={data}
        nodeColor={(node: any) => node.isAnomalous ? '#ef4444' : '#3b82f6'}
        nodeRelSize={3}
        linkColor={(link: any) => link.type === 'provider' ? 'rgba(255,255,255,0.2)' : 'rgba(156,163,175,0.1)'}
        linkWidth={(link: any) => link.type === 'provider' ? 1.5 : 0.5}
        backgroundColor="#09090b"
        enableNodeDrag={true}
        enableZoomInteraction={true}
        cooldownTicks={100} // Stop simulating quickly to save CPU
      />
      
      <div className="absolute top-4 right-4 bg-zinc-900/80 backdrop-blur-md p-4 rounded-xl border border-zinc-800 w-72">
        <h3 className="text-white font-medium mb-1">AS Topology Graph</h3>
        <p className="text-zinc-400 text-xs mb-4">Rendering {data.nodes.length.toLocaleString()} AS Nodes and {data.links.length.toLocaleString()} Relationships via WebGL.</p>
        
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2 text-zinc-300">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div> Healthy AS
          </div>
          <div className="flex items-center gap-2 text-zinc-300">
            <div className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,1)]"></div> ML Predicted Instability
          </div>
          <div className="flex items-center gap-2 text-zinc-300 mt-2">
            <div className="w-4 h-0.5 bg-white opacity-40"></div> Provider Edge
          </div>
          <div className="flex items-center gap-2 text-zinc-300">
            <div className="w-4 h-0.5 bg-gray-400 opacity-20"></div> Peer Edge
          </div>
        </div>
      </div>
    </div>
  )
}
