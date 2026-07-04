import { create } from 'zustand'

export interface NetPulseIncident {
  id: string
  severity: string
  detected_at: string
  resolved_at: string | null
  explanation: string | null
  incident_metadata: any
}

export interface NetPulseMeasurement {
  id: string
  probe_id: number
  target: string
  rtt_ms: number
  packet_loss: number
  timestamp: string
}

interface NetPulseState {
  incidents: NetPulseIncident[]
  measurements: NetPulseMeasurement[]
  socket: WebSocket | null
  isConnected: boolean
  
  // Actions
  connect: () => void
  disconnect: () => void
  addIncident: (incident: NetPulseIncident) => void
  addMeasurement: (measurement: NetPulseMeasurement) => void
  setIncidents: (incidents: NetPulseIncident[]) => void
}

export const useNetPulseStore = create<NetPulseState>((set, get) => ({
  incidents: [],
  measurements: [],
  socket: null,
  isConnected: false,

  connect: () => {
    const { socket } = get()
    if (socket?.readyState === WebSocket.OPEN) return

    // In a real app, use environment variables for WS URL
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/events'
    const newSocket = new WebSocket(wsUrl)

    newSocket.onopen = () => {
      set({ socket: newSocket, isConnected: true })
    }

    newSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'incident') {
          get().addIncident(data.payload)
        } else if (data.type === 'measurement') {
          get().addMeasurement(data.payload)
        }
      } catch (e) {
        console.error('Failed to parse websocket message', e)
      }
    }

    newSocket.onclose = () => {
      set({ socket: null, isConnected: false })
      // Auto-reconnect after 3 seconds
      setTimeout(() => get().connect(), 3000)
    }
  },

  disconnect: () => {
    const { socket } = get()
    if (socket) {
      socket.close()
      set({ socket: null, isConnected: false })
    }
  },

  addIncident: (incident) => set((state) => ({ 
    incidents: [incident, ...state.incidents].slice(0, 100) // Keep last 100
  })),

  addMeasurement: (measurement) => set((state) => ({
    measurements: [measurement, ...state.measurements].slice(0, 1000) // Keep last 1000
  })),

  setIncidents: (incidents) => set({ incidents })
}))
