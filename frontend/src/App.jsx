import { useEffect, useState } from "react";
import { Header } from "./components/layout/Header.jsx";
import { AuthPage } from "./pages/AuthPage.jsx";
import { HomePage } from "./pages/HomePage.jsx";
import { ScoringPage } from "./pages/ScoringPage.jsx";
import { supabase } from "./lib/supabase.js";
import { getPathForRoute, getRouteIdFromPath } from "./routing/routes.js";

export default function App() {
  const [route, setRoute] = useState(() => getRouteIdFromPath(window.location.pathname));
  const [session, setSession] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      if (nextSession) {
        navigate("home");
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    function handlePopState() {
      setRoute(getRouteIdFromPath(window.location.pathname));
      window.scrollTo({ top: 0, behavior: "auto" });
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function navigate(nextRoute) {
    const nextPath = getPathForRoute(nextRoute);

    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, "", nextPath);
    }

    setRoute(nextRoute);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleSignOut() {
    supabase.auth.signOut().then(() => navigate("home"));
  }

  return (
    <>
      <Header onNavigate={navigate} session={session} onSignOut={handleSignOut} />
      <main>
        {route === "auth" && <AuthPage session={session} onNavigate={navigate} />}
        {route === "scoring" && <ScoringPage onNavigate={navigate} />}
        {route === "home" && <HomePage onNavigate={navigate} />}
      </main>
    </>
  );
}
