export const ROUTES = {
  home: { id: "home", path: "/" },
  auth: { id: "auth", path: "/review" },
  scoring: { id: "scoring", path: "/scoring" },
  projects: { id: "projects", path: "/projects" },
  projectDetail: { id: "projectDetail", path: "/projects/:projectId" },
  conversation: { id: "conversation", path: "/projects/:projectId/conversations/:conversationId" },
};

const routeByPath = Object.values(ROUTES).reduce((accumulator, route) => {
  if (!route.path.includes(":")) {
    accumulator[route.path] = route.id;
  }
  return accumulator;
}, {});

export function getRouteFromPath(pathname) {
  const normalizedPath = pathname.endsWith("/") && pathname !== "/" ? pathname.slice(0, -1) : pathname;

  const conversationMatch = normalizedPath.match(/^\/projects\/([^/]+)\/conversations\/([^/]+)$/);
  if (conversationMatch) {
    return {
      id: ROUTES.conversation.id,
      params: {
        projectId: decodeURIComponent(conversationMatch[1]),
        conversationId: decodeURIComponent(conversationMatch[2]),
      },
    };
  }

  const projectMatch = normalizedPath.match(/^\/projects\/([^/]+)$/);
  if (projectMatch) {
    return {
      id: ROUTES.projectDetail.id,
      params: { projectId: decodeURIComponent(projectMatch[1]) },
    };
  }

  return { id: routeByPath[normalizedPath] ?? ROUTES.home.id, params: {} };
}

export function getRouteIdFromPath(pathname) {
  return getRouteFromPath(pathname).id;
}

export function getPathForRoute(routeId, params = {}) {
  const route = ROUTES[routeId] ?? ROUTES.home;

  if (route.id === ROUTES.projectDetail.id) {
    return `/projects/${encodeURIComponent(params.projectId ?? "")}`;
  }

  if (route.id === ROUTES.conversation.id) {
    return `/projects/${encodeURIComponent(params.projectId ?? "")}/conversations/${encodeURIComponent(
      params.conversationId ?? "",
    )}`;
  }

  return route.path;
}
