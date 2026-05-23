import { Brand } from "./Brand.jsx";
import { NavButton } from "../navigation/NavButton.jsx";

export function Header({ onNavigate, session, onSignOut }) {
  return (
    <header className="site-header">
      <Brand onNavigate={onNavigate} />
      {session ? (
        <button className="pill-button" type="button" onClick={onSignOut}>
          Sign out
        </button>
      ) : (
        <NavButton className="pill-button" route="auth" onNavigate={onNavigate}>
          Start review
        </NavButton>
      )}
    </header>
  );
}
