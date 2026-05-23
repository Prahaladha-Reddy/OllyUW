import { getPathForRoute } from "../../routing/routes.js";

export function NavButton({ children, className, onNavigate, params, route, ...props }) {
  return (
    <a
      className={className}
      href={getPathForRoute(route, params)}
      onClick={(event) => {
        event.preventDefault();
        onNavigate(route, params);
      }}
      {...props}
    >
      {children}
    </a>
  );
}
