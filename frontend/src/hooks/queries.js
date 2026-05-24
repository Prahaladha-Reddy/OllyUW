import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import * as api from '../lib/api'

// ── Queries ──────────────────────────────────────────────────────────────────

export function useProjects() {
  const { session } = useAuth()
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => api.listProjects(session),
    enabled: !!session,
    select: (data) => data.projects ?? [],
  })
}

export function useProject(projectId) {
  const { session } = useAuth()
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(session, projectId),
    enabled: !!session && !!projectId,
  })
}

export function useMessages(projectId, conversationId) {
  const { session } = useAuth()
  return useQuery({
    queryKey: ['messages', projectId, conversationId],
    queryFn: () => api.listMessages(session, projectId, conversationId),
    enabled: !!session && !!projectId && !!conversationId,
    staleTime: 0,
    select: (data) => {
      const msgs = data.messages ?? []
      const seen = new Set()
      return msgs.filter((m) => {
        if (seen.has(m.id)) return false
        seen.add(m.id)
        return true
      })
    },
  })
}

// ── Mutations ─────────────────────────────────────────────────────────────────

export function useCreateProject() {
  const { session } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body) => api.createProject(session, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export function useDeleteProject() {
  const { session } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (projectId) => api.deleteProject(session, projectId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export function useCreateConversation(projectId) {
  const { session } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body) => api.createConversation(session, projectId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project', projectId] }),
  })
}

export function useDeleteConversation(projectId) {
  const { session } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (conversationId) => api.deleteConversation(session, projectId, conversationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project', projectId] }),
  })
}

export function useUploadProjectFiles(projectId) {
  const { session } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (files) => api.uploadProjectFiles(session, projectId, files),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project', projectId] }),
  })
}

export function useDeleteProjectFile(projectId) {
  const { session } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (fileId) => api.deleteProjectFile(session, projectId, fileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project', projectId] }),
  })
}

export function useUploadConversationFiles(projectId, conversationId) {
  const { session } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (files) => api.uploadConversationFiles(session, projectId, conversationId, files),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project', projectId] }),
  })
}

export function useSendMessage(projectId, conversationId) {
  const { session } = useAuth()
  return useMutation({
    mutationFn: (payload) =>
      api.sendConversationMessage(session, projectId, conversationId, payload),
  })
}
