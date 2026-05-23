import { getPathForRoute } from "../../routing/routes.js";

export function Brand({ onNavigate }) {
  return (
    <a
      className="brand"
      href={getPathForRoute("home")}
      onClick={(event) => {
        event.preventDefault();
        onNavigate("home");
      }}
      aria-label="OllyUW home"
    >
      <span className="brand-mark" aria-hidden="true" />
      <span>OllyUW</span>
    </a>
  );
}
