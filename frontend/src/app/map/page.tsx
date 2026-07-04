"use client"

import { useEffect, useMemo, useState } from 'react'
import Map, { Source, Layer, Marker } from 'react-map-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { motion, AnimatePresence } from 'framer-motion'
import { useNetPulseStore } from '@/lib/store'

// We will use a standard dark basemap
const MAPTILER_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

// Mock probe data if backend isn't sending enough for a dense demo
const INITIAL_PROBES = Array.from({ length: 500 }).map((_, i) => ({
  id: `probe-${i}`,
  longitude: (Math.random() - 0.5) * 360,
  latitude: (Math.random() - 0.5) * 160,
  health: Math.random() > 0.95 ? 'degraded' : 'healthy'
}))

export default function LiveMap() {
  const { incidents, connect, disconnect } = useNetPulseStore()
  
  // Ensure we connect to WS on mount
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  const [viewState, setViewState] = useState({
    longitude: 0,
    latitude: 20,
    zoom: 2
  })

  // Convert probe array to GeoJSON for WebGL rendering (60fps scale)
  const probeGeoJSON = useMemo(() => ({
    type: 'FeatureCollection' as const,
    features: INITIAL_PROBES.map(p => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [p.longitude, p.latitude] },
      properties: { id: p.id, health: p.health }
    }))
  }), [])

  // Render active incidents as pulsating HTML markers
  const activeIncidents = useMemo(() => {
    return incidents.filter(i => !i.resolved_at).slice(0, 10)
  }, [incidents])

  return (
    <div className="w-full h-[calc(100vh-4rem)] relative bg-zinc-950">
      <Map
        {...viewState}
        onMove={evt => setViewState(evt.viewState)}
        mapStyle={MAPTILER_STYLE}
        interactiveLayerIds={['probes']}
        cursor="crosshair"
      >
        <Source type="geojson" data={probeGeoJSON}>
          <Layer
            id="probes"
            type="circle"
            paint={{
              'circle-radius': 4,
              'circle-color': [
                'match',
                ['get', 'health'],
                'healthy', '#10b981', // Emerald 500
                'degraded', '#f59e0b', // Amber 500
                '#ef4444' // Red 500
              ],
              'circle-opacity': 0.8
            }}
          />
        </Source>

        {/* Render Pulsating Markers for Incidents */}
        <AnimatePresence>
          {activeIncidents.map((incident, idx) => {
            // In reality, incident coordinates come from metadata. 
            // Mocking coordinates for demo purposes if not present:
            const lng = incident.incident_metadata?.lng || (Math.random() - 0.5) * 180
            const lat = incident.incident_metadata?.lat || (Math.random() - 0.5) * 90
            
            return (
              <Marker key={incident.id} longitude={lng} latitude={lat} anchor="center">
                <motion.div
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: [1, 2, 3], opacity: [0.8, 0.4, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="w-12 h-12 bg-red-500 rounded-full blur-md"
                />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-red-500 rounded-full shadow-[0_0_10px_rgba(239,68,68,1)]" />
              </Marker>
            )
          })}
        </AnimatePresence>
      </Map>
      
      {/* Legend / Overlay */}
      <div className="absolute top-4 left-4 bg-zinc-900/80 backdrop-blur-md p-4 rounded-xl border border-zinc-800">
        <h3 className="text-white font-medium mb-3">Live Network Map</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2 text-zinc-300">
            <div className="w-3 h-3 rounded-full bg-emerald-500"></div> Healthy Probes (475)
          </div>
          <div className="flex items-center gap-2 text-zinc-300">
            <div className="w-3 h-3 rounded-full bg-amber-500"></div> High Latency (25)
          </div>
          <div className="flex items-center gap-2 text-zinc-300">
            <div className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,1)]"></div> Active Anomalies ({activeIncidents.length})
          </div>
        </div>
      </div>
    </div>
  )
}
