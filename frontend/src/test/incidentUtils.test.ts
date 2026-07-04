import { describe, it, expect } from 'vitest'
import { filterAndSortIncidents, Incident } from '../lib/incidentUtils'

const mockData: Incident[] = [
  { id: '1', severity: 'low', detected_at: '2023-01-01T10:00:00Z', resolved_at: '2023-01-01T11:00:00Z' },
  { id: '2', severity: 'critical', detected_at: '2023-01-02T10:00:00Z', resolved_at: null },
  { id: '3', severity: 'medium', detected_at: '2023-01-03T10:00:00Z', resolved_at: null },
]

describe('filterAndSortIncidents', () => {
  it('filters active incidents', () => {
    const result = filterAndSortIncidents(mockData, 'active', 'newest')
    expect(result.length).toBe(2)
    expect(result.map(i => i.id)).toContain('2')
    expect(result.map(i => i.id)).toContain('3')
  })

  it('filters resolved incidents', () => {
    const result = filterAndSortIncidents(mockData, 'resolved', 'newest')
    expect(result.length).toBe(1)
    expect(result[0].id).toBe('1')
  })

  it('sorts by newest', () => {
    const result = filterAndSortIncidents(mockData, 'all', 'newest')
    expect(result[0].id).toBe('3') // Jan 3
    expect(result[1].id).toBe('2') // Jan 2
    expect(result[2].id).toBe('1') // Jan 1
  })

  it('sorts by severity', () => {
    const result = filterAndSortIncidents(mockData, 'all', 'severity')
    expect(result[0].id).toBe('2') // critical
    expect(result[1].id).toBe('3') // medium
    expect(result[2].id).toBe('1') // low
  })
})
