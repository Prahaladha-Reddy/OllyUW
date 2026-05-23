export const ROUTES = {
  home: { id: "home", path: "/" },
  auth: { id: "auth", path: "/review" },
  scoring: { id: "scoring", path: "/scoring" },
};

const routeByPath = Object.values(ROUTES).reduce((accumulator, route) => {
  accumulator[route.path] = route.id;
  return accumulator;
}, {});

export function getRouteIdFromPath(pathname) {
  const normalizedPath = pathname.endsWith("/") && pathname !== "/" ? pathname.slice(0, -1) : pathname;
  return routeByPath[normalizedPath] ?? ROUTES.home.id;
}

export function getPathForRoute(routeId) {
  return ROUTES[routeId]?.path ?? ROUTES.home.path;
}
