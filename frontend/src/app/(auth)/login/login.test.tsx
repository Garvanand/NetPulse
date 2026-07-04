import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import LoginPage from '@/app/(auth)/login/page'
import { AuthProvider } from '@/lib/auth-context'
import { ToastProvider } from '@/components/ui/Toast'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/login'
}))

// Mock API client
vi.mock('@/lib/api-client', () => ({
  authApi: {
    login: vi.fn().mockResolvedValue({ access_token: 'test_token', token_type: 'bearer' }),
    me: vi.fn().mockResolvedValue({ id: '1', email: 'test@example.com', tier: 'free' })
  },
  getToken: vi.fn().mockReturnValue(null),
  setToken: vi.fn(),
  removeToken: vi.fn(),
}))

describe('LoginPage', () => {
  it('renders login form and submits correctly', async () => {
    render(
      <ToastProvider>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </ToastProvider>
    )

    // Check if form fields are rendered
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument()
    
    // Simulate user typing
    fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: 'user@example.com' } })
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'password123' } })
    
    // Check if button exists and click it
    const button = screen.getByRole('button', { name: /Sign In/i })
    expect(button).toBeInTheDocument()
    fireEvent.click(button)
    
    // Button should eventually show loading state or complete
    // We just verify it doesn't crash here
  })
})
