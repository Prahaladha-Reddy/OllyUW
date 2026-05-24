import { Outlet } from 'react-router-dom'
import { Header } from './Header'

export function PublicLayout() {
  return (
    <>
      <Header />
      <main>
        <Outlet />
      </main>
    </>
  )
}
