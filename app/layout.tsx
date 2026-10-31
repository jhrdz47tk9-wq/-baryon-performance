import './globals.css'

export const metadata = { title: 'BARYON Performance', description: 'OEE y EBITDA normalizado' }

export default function Layout({ children }: { children: React.ReactNode }) {
  const pilotUrl = process.env.BARYON_PILOT_URL
  return <html lang="es"><body>
    <header>BARYON <small>PERFORMANCE · OEE / EBITDA</small>
      {pilotUrl && pilotUrl.startsWith('https://') &&
        <nav><a href={pilotUrl}>Evaluar y guardar un caso sintético</a></nav>}
    </header>
    {children}
  </body></html>
}
