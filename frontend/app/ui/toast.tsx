"use client";
import { createContext, useCallback, useContext, useRef, useState } from "react";

const TOAST_MS = 7000;

type Toast = { id: number; message: string };

const ToastContext = createContext<(message: string) => void>(() => {});

// Any component under this provider can call useToast()("message") to pop up an error
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback((message: string) => {
    const id = nextId.current++;
    setToasts((current) => [...current, { id, message }]);
    setTimeout(() => dismiss(id), TOAST_MS);
  }, [dismiss]);

  return (
    <ToastContext value={showToast}>
      {children}
      <div className="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col gap-2 sm:left-auto sm:w-96">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="alert"
            className="pointer-events-auto flex items-start gap-3 border-2 border-error bg-panel p-3 shadow-[4px_4px_0_0_var(--color-error)] motion-safe:animate-toast-in"
          >
            <span className="mt-1.5 size-2.5 shrink-0 bg-error" aria-hidden="true" />
            <p className="flex-1 text-sm break-words">{toast.message}</p>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              aria-label="Dismiss"
              className="-m-1 px-2 text-lg leading-none text-muted hover:text-ink"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext>
  );
}

export const useToast = () => useContext(ToastContext);
