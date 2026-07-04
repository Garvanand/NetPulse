"use client"
import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"

export interface Toast {
  id: string;
  title: string;
  description?: string;
  type?: "default" | "success" | "error";
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const addToast = React.useCallback((toast: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => removeToast(id), 5000);
  }, []);

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 50, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
              className={`
                pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all
                ${toast.type === 'error' ? 'bg-destructive text-destructive-foreground border-destructive' : ''}
                ${toast.type === 'success' ? 'bg-success text-success-foreground border-success' : ''}
                ${toast.type === 'default' || !toast.type ? 'bg-background border-border text-foreground' : ''}
              `}
            >
              <div className="grid gap-1">
                {toast.title && <div className="text-sm font-semibold">{toast.title}</div>}
                {toast.description && <div className="text-sm opacity-90">{toast.description}</div>}
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="absolute right-2 top-2 rounded-md p-1 opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}
