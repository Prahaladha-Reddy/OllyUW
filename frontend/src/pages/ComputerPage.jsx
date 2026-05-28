import { Folder, LockKeyhole, Monitor, Plug } from 'lucide-react'
import { useMemo, useState } from 'react'
import { UploadArea } from '../components/workspace/UploadArea'
import {
  useComputer,
  useComputerConnections,
  useComputerFiles,
  useCreateComputerFolder,
  useUploadComputerFiles,
  useVaultItems,
} from '../hooks/queries'
import { formatDateTime, formatRelativeDate } from '../utils/format'

const suggestedWorkflows = [
  {
    title: 'Persistent research desk',
    description: 'Keep source files, notes, and browser state in one place while the agent iterates.',
  },
  {
    title: 'Inbox to drafts',
    description: 'Upload a directory, let the computer preserve the structure, and keep outputs nearby.',
  },
  {
    title: 'App-connected operator',
    description: 'Save the app connections the agent needs so repeated work does not start from zero.',
  },
]

export function ComputerPage() {
  const {
    data: computer,
    isLoading: computerLoading,
    error: computerError,
  } = useComputer()
  const { data: files = [], isLoading: filesLoading, error: filesError } = useComputerFiles()
  const { data: connections = [], isLoading: connectionsLoading, error: connectionsError } = useComputerConnections()
  const { data: vaultItems = [], isLoading: vaultLoading, error: vaultError } = useVaultItems()
  const uploadFiles = useUploadComputerFiles()
  const createFolder = useCreateComputerFolder()

  const [folderName, setFolderName] = useState('')
  const [actionError, setActionError] = useState('')
  const [actionSuccess, setActionSuccess] = useState('')

  const isLoading = computerLoading || filesLoading || connectionsLoading || vaultLoading
  const error = computerError || filesError || connectionsError || vaultError
  const isWorking = uploadFiles.isPending || createFolder.isPending
  const displayFiles = useMemo(() => buildDisplayFiles(files), [files])

  async function handleUpload(payload) {
    setActionError('')
    setActionSuccess('')
    try {
      const result = await uploadFiles.mutateAsync(payload)
      const count = result?.files?.length ?? payload.files.length
      setActionSuccess(`${count} file${count === 1 ? '' : 's'} uploaded.`)
    } catch (requestError) {
      setActionError(requestError.message || 'Could not upload files.')
    }
  }

  async function handleCreateFolder(event) {
    event.preventDefault()
    const trimmed = folderName.trim()
    if (!trimmed) {
      setActionError('Folder name is required.')
      return
    }

    setActionError('')
    setActionSuccess('')
    try {
      await createFolder.mutateAsync({ name: trimmed })
      setFolderName('')
      setActionSuccess(`Folder "${trimmed}" created.`)
    } catch (requestError) {
      setActionError(requestError.message || 'Could not create folder.')
    }
  }

  if (isLoading) {
    return (
      <div className="state-panel">
        <h2>Loading your computer</h2>
        <p>Resolving persistent state, files, connected apps, and saved vault items.</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="workspace-alert">
        {error.message || 'Could not load the computer state.'}
      </div>
    )
  }

  return (
    <div>
      <div className="workspace-header">
        <div>
          <p className="eyebrow">Second Computer</p>
          <h1>Your AI&apos;s persistent machine</h1>
          <p>
            Files, connected apps, and saved state live here. You are not opening a new chat. You
            are resuming the same computer.
          </p>
        </div>
      </div>

      <section className="workspace-section computer-primary-section">
        <div className="workspace-section-heading">
          <div>
            <h2>Upload files and folders</h2>
            <p>Start here. Upload files, upload a full folder, or create an empty folder.</p>
          </div>
          <div className="workspace-actions">
            <form className="computer-folder-form" onSubmit={handleCreateFolder}>
              <input
                className="computer-folder-input"
                type="text"
                value={folderName}
                onChange={(event) => setFolderName(event.target.value)}
                placeholder="New folder name"
                disabled={isWorking}
              />
              <button className="secondary-button" type="submit" disabled={isWorking}>
                Create folder
              </button>
            </form>
          </div>
        </div>

        {actionError && <p className="workspace-alert">{actionError}</p>}
        {actionSuccess && <p className="workspace-success">{actionSuccess}</p>}

        <UploadArea disabled={isWorking} onUpload={handleUpload} />
      </section>

      <div className="project-grid computer-summary-grid">
        <SummaryCard
          eyebrow="Status"
          title={computer?.status === 'online' ? 'Online' : 'Sleeping'}
          detail={`Last active ${formatRelativeDate(computer?.last_active)}`}
          icon={<Monitor size={16} />}
        />
        <SummaryCard
          eyebrow="Files"
          title={`${files.length}`}
          detail="Files and folders currently tracked"
          icon={<Folder size={16} />}
        />
        <SummaryCard
          eyebrow="Apps"
          title={`${connections.length}`}
          detail="Connected app records saved"
          icon={<Plug size={16} />}
        />
        <SummaryCard
          eyebrow="Persistence"
          title={`${vaultItems.length}`}
          detail="Vault items saved for future sessions"
          icon={<LockKeyhole size={16} />}
        />
      </div>

      <section className="workspace-section">
        <div className="workspace-section-heading">
          <div>
            <h2>File system</h2>
            <p>The current contents of your computer.</p>
          </div>
        </div>

        {displayFiles.length === 0 ? (
          <div className="empty-panel computer-empty-panel">
            <h3>No files or folders yet</h3>
            <p>Upload files, upload a directory tree, or create an empty folder to start shaping the machine.</p>
          </div>
        ) : (
          <div className="file-list computer-file-list">
            {displayFiles.map((file) => (
              <div className="file-row" key={file.id}>
                <div>
                  <span className={`status-dot status-${file.file_type === 'folder' ? 'ready' : 'completed'}`} />
                  <div className="computer-file-meta">
                    <strong>{file.displayPath}</strong>
                    <p>{file.file_type} - updated {formatRelativeDate(file.updated_at)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="workspace-section">
        <div className="workspace-section-heading">
          <div>
            <h2>Connected apps and vault</h2>
            <p>Persistent sessions and saved credentials are the difference between chat and a machine.</p>
          </div>
        </div>
        <div className="project-grid computer-state-grid">
          <StateCard
            title="Connected apps"
            description={
              connections.length
                ? `${connections.length} app connection${connections.length === 1 ? '' : 's'} saved`
                : 'No connected apps yet'
            }
            detail={
              connections.length
                ? connections.slice(0, 3).map((connection) => connection.provider).join(', ')
                : 'Composio or similar connectors will appear here.'
            }
            icon={<Plug size={16} />}
          />
          <StateCard
            title="Vault"
            description={`${vaultItems.length} persisted item${vaultItems.length === 1 ? '' : 's'}`}
            detail={
              vaultItems.length
                ? `Most recent update ${formatDateTime(vaultItems[vaultItems.length - 1].updated_at)}`
                : 'Cookies, credentials, bookmarks, and local storage will be tracked here.'
            }
            icon={<LockKeyhole size={16} />}
          />
        </div>
      </section>

      <section className="workspace-section">
        <div className="workspace-section-heading">
          <div>
            <h2>Suggested workflows</h2>
            <p>The shell should answer what you can do before you type a prompt.</p>
          </div>
        </div>
        <div className="project-grid computer-state-grid">
          {suggestedWorkflows.map((workflow) => (
            <div className="project-card-shell" key={workflow.title}>
              <div className="project-card">
                <span>Workflow</span>
                <h3>{workflow.title}</h3>
                <p>{workflow.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function buildDisplayFiles(files) {
  const byId = new Map(files.map((file) => [file.id, file]))

  function pathFor(file) {
    const parts = [file.name]
    let current = file
    while (current.parent_folder_id) {
      const parent = byId.get(current.parent_folder_id)
      if (!parent) break
      parts.unshift(parent.name)
      current = parent
    }
    return parts.join('/')
  }

  return [...files]
    .map((file) => ({ ...file, displayPath: pathFor(file) }))
    .sort((left, right) => {
      if (left.file_type !== right.file_type) {
        return left.file_type === 'folder' ? -1 : 1
      }
      return left.displayPath.localeCompare(right.displayPath)
    })
}

function SummaryCard({ eyebrow, title, detail, icon }) {
  return (
    <div className="project-card-shell">
      <div className="project-card">
        <span>{eyebrow}</span>
        <h3 className="computer-card-title">
          {icon}
          {title}
        </h3>
        <p>{detail}</p>
      </div>
    </div>
  )
}

function StateCard({ title, description, detail, icon }) {
  return (
    <div className="project-card-shell">
      <div className="project-card">
        <span>{title}</span>
        <h3 className="computer-card-title">
          {icon}
          {description}
        </h3>
        <p>{detail}</p>
      </div>
    </div>
  )
}
