import { Brand } from "./Brand.jsx";
import { NavButton } from "../navigation/NavButton.jsx";

export function Header({ onNavigate, session }) {
  return (
    <header className="site-header">
      <Brand onNavigate={onNavigate} />
      {!session && (
        <NavButton className="pill-button" route="auth" onNavigate={onNavigate}>
          Start review
        </NavButton>
      )}
    </header>
  );
}
