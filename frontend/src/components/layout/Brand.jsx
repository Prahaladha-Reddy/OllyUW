import { Link } from 'react-router-dom'

export function Brand() {
  return (
    <Link className="brand" to="/" aria-label="OllyUW home">
      <span className="brand-mark" aria-hidden="true" />
      <span>OllyUW</span>
    </Link>
  )
}
