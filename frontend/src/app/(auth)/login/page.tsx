"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { motion } from "framer-motion"

import { Button } from "@/components/ui/Button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { useAuth } from "@/lib/auth-context"
import { useToast } from "@/components/ui/Toast"

export default function LoginPage() {
  const [email, setEmail] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [isLoading, setIsLoading] = React.useState(false)
  const { login } = useAuth()
  const { addToast } = useToast()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    
    try {
      const formData = new FormData()
      formData.append("username", email)
      formData.append("password", password)
      
      await login(formData)
      addToast({ title: "Welcome back!", type: "success" })
    } catch (err: any) {
      addToast({ 
        title: "Login Failed", 
        description: err.message || "Invalid credentials",
        type: "error"
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl text-center">Sign In to NetPulse</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="email">Email</label>
                <input 
                  id="email"
                  type="email" 
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="name@example.com"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="password">Password</label>
                <input 
                  id="password"
                  type="password" 
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <Button type="submit" className="w-full" isLoading={isLoading}>
                Sign In
              </Button>
            </form>
            <div className="mt-4 text-center text-sm text-muted-foreground">
              Don't have an account?{" "}
              <Link href="/signup" className="text-primary hover:underline">
                Sign up
              </Link>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
