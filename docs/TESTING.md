# NetPulse Manual QA Checklist

Since the interactive visual elements (MapLibre WebGL map, ForceGraph2D Canvas) are heavily reliant on browser APIs and WebGL contexts, they cannot be fully unit-tested in Node.js via Vitest. Please execute the following manual QA checklist when making changes to the UI layer.

## 1. Live Map (`/map`)
- [ ] **Render Accuracy**: Verify that upon loading, healthy probes are rendered as green dots globally. Zooming in should keep them crisp without artifacts.
- [ ] **Incident Pulse**: Trigger an incident (via backend REST API or WebSocket mock). Verify that a pulsating red blur effect (Framer Motion) appears exactly over the affected coordinate.
- [ ] **Performance**: Rapidly pan and zoom across the map. The frame rate should stay at 60 FPS. `react-map-gl` manages LOD automatically for points.
- [ ] **Popover**: Hovering or clicking a pulsating node should show a brief tooltip or detail context without throwing errors.

## 2. AS Topology Graph (`/topology`)
- [ ] **Initial Layout**: The Canvas should load the force-directed graph. Wait ~3-5 seconds for the cooldown ticks to finish. The layout should stabilize and nodes should stop moving rapidly.
- [ ] **Highlighting**: Verify that anomalous nodes (e.g., node 1000) are brightly colored (red) and stand out from the rest of the blue AS graph.
- [ ] **Interactivity**: Drag a node; it should move fluidly and tug its attached edges. Zoom in/out via scroll wheel should be smooth.
- [ ] **Scale Limits**: Confirm in the top-right overlay that it is rendering the tested scale (e.g., 2,000 nodes, 2,000 links).

## 3. Incident Dashboard (`/incidents`)
- [ ] **List Selection**: Clicking a "Critical" incident in the left pane should instantly (via Framer Motion) slide the right detail pane into view.
- [ ] **LLM Detail**: Read the Anthropic explanation text. It should cleanly wrap and be highly legible inside the gradient card.
- [ ] **Recharts Visibility**: The line chart at the bottom should show the mock latency pattern with the red dashed line marking the exact point of incident detection.
- [ ] **Empty State**: Refreshing without selecting an incident should show the `Info` icon and "Select an incident to view investigation details" cleanly centered.

## 4. WebSockets (`useNetPulseStore`)
- [ ] **Reconnection**: Open the browser dev tools. Disable the network (Offline mode). The console should show WebSocket errors. Re-enable the network; the store should automatically reconnect within 3 seconds.
