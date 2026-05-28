import { FolderUp, UploadCloud } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

const supportedExtensions = [
  '.pdf', '.docx', '.pptx', '.xlsx', '.csv', '.tsv',
  '.json', '.yaml', '.yml', '.toml',
  '.txt', '.md', '.html', '.xml',
]
const maxFileSize = 50 * 1024 * 1024

export function UploadArea({ disabled, onUpload }) {
  const fileInputRef = useRef(null)
  const folderInputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (folderInputRef.current) {
      folderInputRef.current.setAttribute('webkitdirectory', '')
      folderInputRef.current.setAttribute('directory', '')
    }
  }, [])

  function validateFiles(fileList) {
    const files = Array.from(fileList)
    const invalid = files.find((file) => {
      const name = file.name.toLowerCase()
      return !supportedExtensions.some((extension) => name.endsWith(extension))
    })

    if (invalid) {
      setError(`${invalid.name} is not a supported file type.`)
      return []
    }

    const oversized = files.find((file) => file.size > maxFileSize)
    if (oversized) {
      setError(`${oversized.name} exceeds the 50 MB file limit.`)
      return []
    }

    setError('')
    return files
  }

  function handleFiles(fileList, { preservePaths = false } = {}) {
    const files = validateFiles(fileList)
    if (!files.length) {
      return
    }

    onUpload({
      files,
      relativePaths: files.map((file) => (
        preservePaths && file.webkitRelativePath ? file.webkitRelativePath : file.name
      )),
    })
  }

  return (
    <div
      className={`upload-area ${isDragging ? 'is-dragging' : ''} ${disabled ? 'is-disabled' : ''}`}
      onDragOver={(event) => {
        event.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setIsDragging(false)
        if (!disabled) {
          handleFiles(event.dataTransfer.files)
        }
      }}
    >
      <UploadCloud size={32} strokeWidth={1.8} />
      <h3>Drop files here or browse from your machine</h3>
      <p>
        Supported: PDF, DOCX, PPTX, XLSX, CSV, JSON, YAML, TOML, TXT, MD, HTML, XML.
        Max 50 MB per file.
      </p>
      <div className="computer-upload-actions">
        <button className="dark-button" type="button" disabled={disabled} onClick={() => fileInputRef.current?.click()}>
          <UploadCloud size={16} />
          Browse files
        </button>
        <button
          className="secondary-button"
          type="button"
          disabled={disabled}
          onClick={() => folderInputRef.current?.click()}
        >
          <FolderUp size={16} />
          Browse folder
        </button>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        hidden
        accept={supportedExtensions.join(',')}
        onChange={(event) => {
          handleFiles(event.target.files)
          event.target.value = ''
        }}
      />
      <input
        ref={folderInputRef}
        type="file"
        multiple
        hidden
        accept={supportedExtensions.join(',')}
        onChange={(event) => {
          handleFiles(event.target.files, { preservePaths: true })
          event.target.value = ''
        }}
      />
      {error && <p className="upload-error">{error}</p>}
    </div>
  )
}
