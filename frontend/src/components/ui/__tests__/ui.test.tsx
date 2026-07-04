import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardTitle, CardHeader, CardContent } from '@/components/ui/Card'

describe('UI Primitives', () => {
  it('renders Button correctly', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: /Click me/i })).toBeInTheDocument()
  })

  it('renders Badge correctly', () => {
    render(<Badge variant="destructive">Error</Badge>)
    expect(screen.getByText('Error')).toHaveClass('bg-destructive')
  })

  it('renders Card correctly', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
        </CardHeader>
        <CardContent>Content</CardContent>
      </Card>
    )
    expect(screen.getByText('Title')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
  })
})
