import { Link } from 'react-router-dom'

export function Brand() {
  return (
    <Link className="brand" to="/" aria-label="Olly home">
      <span className="brand-mark" aria-hidden="true" />
      <span>Olly</span>
    </Link>
  )
}
