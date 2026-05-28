export const ROUTES = {
  home: { id: 'home', path: '/' },
  auth: { id: 'auth', path: '/review' },
  computer: { id: 'computer', path: '/computer' },
}

const routeByPath = Object.values(ROUTES).reduce((accumulator, route) => {
  accumulator[route.path] = route.id
  return accumulator
}, {})

export function getRouteFromPath(pathname) {
  const normalizedPath = pathname.endsWith('/') && pathname !== '/' ? pathname.slice(0, -1) : pathname
  return { id: routeByPath[normalizedPath] ?? ROUTES.home.id, params: {} }
}

export function getRouteIdFromPath(pathname) {
  return getRouteFromPath(pathname).id
}

export function getPathForRoute(routeId) {
  const route = ROUTES[routeId] ?? ROUTES.home
  return route.path
}
