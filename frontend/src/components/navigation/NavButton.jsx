import { getPathForRoute } from "../../routing/routes.js";

export function NavButton({ children, className, onNavigate, route, ...props }) {
  return (
    <a
      className={className}
      href={getPathForRoute(route)}
      onClick={(event) => {
        event.preventDefault();
        onNavigate(route);
      }}
      {...props}
    >
      {children}
    </a>
  );
}
