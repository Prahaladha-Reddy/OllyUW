import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getProject, listProjects } from "../lib/api.js";

export function useWorkspace(session) {
  const [projects, setProjects] = useState([]);
  const [projectDetails, setProjectDetails] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(new Set());

  const refreshProjects = useCallback(async () => {
    if (!session) {
      setProjects([]);
      setProjectDetails({});
      return;
    }

    setIsLoading(true);
    setError("");
    try {
      const response = await listProjects(session);
      setProjects(response.projects || []);
    } catch (requestError) {
      setError(requestError.message || "Could not load projects.");
    } finally {
      setIsLoading(false);
    }
  }, [session]);

  const loadProjectDetail = useCallback(
    async (projectId, { force = false } = {}) => {
      if (!session || !projectId) return null;
      if (!force && (projectDetails[projectId] || inFlight.current.has(projectId))) {
        return projectDetails[projectId] || null;
      }

      inFlight.current.add(projectId);
      try {
        const detail = await getProject(session, projectId);
        setProjectDetails((current) => ({ ...current, [projectId]: detail }));
        return detail;
      } catch (requestError) {
        setError(requestError.message || "Could not load project.");
        return null;
      } finally {
        inFlight.current.delete(projectId);
      }
    },
    [session, projectDetails],
  );

  const refresh = useCallback(async () => {
    await refreshProjects();
    // Refresh any project details we've already loaded so they stay in sync.
    const loaded = Object.keys(projectDetails);
    await Promise.all(loaded.map((id) => loadProjectDetail(id, { force: true })));
  }, [refreshProjects, projectDetails, loadProjectDetail]);

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  const hasProjects = projects.length > 0;

  return useMemo(
    () => ({
      error,
      hasProjects,
      isLoading,
      projectDetails,
      projects,
      loadProjectDetail,
      refresh,
      refreshProjects,
    }),
    [error, hasProjects, isLoading, projectDetails, projects, loadProjectDetail, refresh, refreshProjects],
  );
}
