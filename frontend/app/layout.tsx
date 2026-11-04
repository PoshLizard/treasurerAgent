import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";
import { CubeIcon } from "./ui/icons";
import { CurrentNavLinks, NavLinks } from "./ui/nav";
import { ToastProvider } from "./ui/toast";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "Treasurer Agent", template: "%s · Treasurer Agent" },
  description: "Receipt processing and funding research for a student organization treasurer",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} antialiased`}
    >
      <body className="min-h-dvh bg-paper font-sans text-ink">
        <ToastProvider>
          <div className="flex min-h-dvh flex-col md:flex-row">
            <aside className="border-b border-ink bg-sand md:sticky md:top-0 md:h-dvh md:w-60 md:shrink-0 md:border-b-0 md:border-r">
              <div className="flex items-center gap-2.5 px-4 py-3 md:px-5 md:py-6">
                <CubeIcon />
                <span className="font-semibold tracking-tight">Treasurer Agent</span>
              </div>
              <nav aria-label="Main" className="px-2 pb-2 md:px-3">
                {/* Reading the URL waits for the request on /receipts/[id], so render plain links until then */}
                <Suspense fallback={<NavLinks pathname={null} />}>
                  <CurrentNavLinks />
                </Suspense>
              </nav>
            </aside>
            <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 md:px-10 md:py-10">{children}</main>
          </div>
        </ToastProvider>
      </body>
    </html>
  );
}
