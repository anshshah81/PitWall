import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PitWall - F1 Strategy Optimizer',
  description: 'Real-time Formula 1 race strategy optimization',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
