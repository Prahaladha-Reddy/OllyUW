import { useEffect, useState } from "react";
import { Header } from "./components/layout/Header.jsx";
import { AuthPage } from "./pages/AuthPage.jsx";
import { ConversationView } from "./pages/ConversationView.jsx";
import { HomePage } from "./pages/HomePage.jsx";
import { ProjectDetail } from "./pages/ProjectDetail.jsx";
import { ProjectsDashboard } from "./pages/ProjectsDashboard.jsx";
import { ScoringPage } from "./pages/ScoringPage.jsx";
import { supabase } from "./lib/supabase.js";
import { getPathForRoute, getRouteFromPath } from "./routing/routes.js";

const protectedRoutes = new Set(["projects", "projectDetail", "conversation"]);

export default function App() {
  const [currentRoute, setCurrentRoute] = useState(() => getRouteFromPath(window.location.pathname));
  const [authLoading, setAuthLoading] = useState(true);
  const [session, setSession] = useState(null);
  const route = currentRoute.id;
  const params = currentRoute.params;

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setAuthLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    function handlePopState() {
      setCurrentRoute(getRouteFromPath(window.location.pathname));
      window.scrollTo({ top: 0, behavior: "auto" });
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (authLoading) {
      return;
    }

    if (protectedRoutes.has(route) && !session) {
      navigate("auth", {}, { replace: true });
      return;
    }

    if (route === "auth" && session) {
      navigate("projects", {}, { replace: true });
    }
  }, [authLoading, route, session]);

  function navigate(nextRoute, nextParams = {}, options = {}) {
    const nextPath = getPathForRoute(nextRoute, nextParams);

    if (window.location.pathname !== nextPath) {
      if (options.replace) {
        window.history.replaceState({}, "", nextPath);
      } else {
        window.history.pushState({}, "", nextPath);
      }
    }

    setCurrentRoute(getRouteFromPath(nextPath));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleSignOut() {
    supabase.auth.signOut().then(() => navigate("home", {}, { replace: true }));
  }

  const isProtectedRoute = protectedRoutes.has(route);
  const isProtectedLoading = authLoading && isProtectedRoute;
  const isProtectedBlocked = !authLoading && isProtectedRoute && !session;

  return (
    <>
      <Header onNavigate={navigate} session={session} onSignOut={handleSignOut} />
      <main>
        {isProtectedLoading && (
          <section className="page section-light state-page">
            <div className="state-panel">
              <h2>Loading workspace</h2>
              <p>Checking your session.</p>
            </div>
          </section>
        )}
        {route === "scoring" && <ScoringPage onNavigate={navigate} />}
        {route === "home" && <HomePage onNavigate={navigate} />}
        {route === "auth" && <AuthPage session={session} onNavigate={navigate} />}
        {!isProtectedLoading && !isProtectedBlocked && route === "projects" && (
          <ProjectsDashboard session={session} onNavigate={navigate} />
        )}
        {!isProtectedLoading && !isProtectedBlocked && route === "projectDetail" && (
          <ProjectDetail projectId={params.projectId} session={session} onNavigate={navigate} />
        )}
        {!isProtectedLoading && !isProtectedBlocked && route === "conversation" && (
          <ConversationView
            conversationId={params.conversationId}
            projectId={params.projectId}
            session={session}
            onNavigate={navigate}
          />
        )}
      </main>
    </>
  );
}
