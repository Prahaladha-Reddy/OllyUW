import { Trash2 } from "lucide-react";
import { formatDateTime, formatFileSize } from "../../utils/format.js";

export function FileList({ files, onDeleteFile }) {
  if (!files.length) {
    return (
      <div className="empty-panel">
        <h3>No files uploaded yet</h3>
        <p>Upload the evidence package to start building the underwriting file.</p>
      </div>
    );
  }

  return (
    <div className="file-list">
      {files.map((file) => (
        <div className="file-row" key={file.id}>
          <div>
            <span className={`status-dot status-${file.status}`} />
            <div>
              <strong>{file.original_name}</strong>
              <p>
                {formatFileSize(file.file_size)} - {formatDateTime(file.created_at)}
              </p>
              {file.error_message && <p className="row-error">{file.error_message}</p>}
            </div>
          </div>
          {file.status !== "processing" && (
            <button className="icon-text-button" type="button" onClick={() => onDeleteFile(file)}>
              <Trash2 size={16} />
              Delete
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
