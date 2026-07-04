export interface Incident {
  id: string
  severity: string
  detected_at: string
  resolved_at: string | null
}

export function filterAndSortIncidents(
  incidents: Incident[], 
  filter: 'all' | 'active' | 'resolved',
  sort: 'newest' | 'oldest' | 'severity'
): Incident[] {
  let result = [...incidents]

  // Filter
  if (filter === 'active') {
    result = result.filter(i => i.resolved_at === null)
  } else if (filter === 'resolved') {
    result = result.filter(i => i.resolved_at !== null)
  }

  // Sort
  result.sort((a, b) => {
    if (sort === 'newest') {
      return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
    } else if (sort === 'oldest') {
      return new Date(a.detected_at).getTime() - new Date(b.detected_at).getTime()
    } else if (sort === 'severity') {
      const severityScore = (s: string) => s === 'critical' ? 3 : s === 'high' ? 2 : s === 'medium' ? 1 : 0
      const scoreDiff = severityScore(b.severity) - severityScore(a.severity)
      // Fallback to newest if severity matches
      if (scoreDiff === 0) {
        return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
      }
      return scoreDiff
    }
    return 0
  })

  return result
}
