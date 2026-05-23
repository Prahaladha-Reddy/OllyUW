import { useCallback, useEffect, useMemo, useState } from "react";
import { getProject, listProjects } from "../lib/api.js";

export function useWorkspace(session) {
  const [projects, setProjects] = useState([]);
  const [projectDetails, setProjectDetails] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!session) {
      setProjects([]);
      setProjectDetails({});
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await listProjects(session);
      const nextProjects = response.projects || [];
      setProjects(nextProjects);

      const detailPairs = await Promise.all(
        nextProjects.map(async (project) => {
          try {
            return [project.id, await getProject(session, project.id)];
          } catch {
            return [project.id, null];
          }
        }),
      );

      setProjectDetails(
        detailPairs.reduce((accumulator, [projectId, detail]) => {
          if (detail) {
            accumulator[projectId] = detail;
          }
          return accumulator;
        }, {}),
      );
    } catch (requestError) {
      setError(requestError.message || "Could not load projects.");
    } finally {
      setIsLoading(false);
    }
  }, [session]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const hasProjects = projects.length > 0;

  return useMemo(
    () => ({
      error,
      hasProjects,
      isLoading,
      projectDetails,
      projects,
      refresh,
    }),
    [error, hasProjects, isLoading, projectDetails, projects, refresh],
  );
}
