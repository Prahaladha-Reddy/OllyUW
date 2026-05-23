import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

const supportedExtensions = [".pdf", ".docx", ".pptx", ".csv", ".json", ".yaml", ".yml", ".toml", ".txt", ".md"];
const maxFileSize = 50 * 1024 * 1024;

export function UploadArea({ disabled, onUpload }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState("");

  function validateFiles(fileList) {
    const files = Array.from(fileList);
    const invalid = files.find((file) => {
      const name = file.name.toLowerCase();
      return !supportedExtensions.some((extension) => name.endsWith(extension));
    });

    if (invalid) {
      setError(`${invalid.name} is not a supported file type.`);
      return [];
    }

    const oversized = files.find((file) => file.size > maxFileSize);
    if (oversized) {
      setError(`${oversized.name} exceeds the 50 MB file limit.`);
      return [];
    }

    setError("");
    return files;
  }

  function handleFiles(fileList) {
    const files = validateFiles(fileList);
    if (files.length) {
      onUpload(files);
    }
  }

  return (
    <div
      className={`upload-area ${isDragging ? "is-dragging" : ""} ${disabled ? "is-disabled" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        if (!disabled) {
          handleFiles(event.dataTransfer.files);
        }
      }}
    >
      <UploadCloud size={32} strokeWidth={1.8} />
      <h3>Drop files here or click to browse</h3>
      <p>Supported: PDF, DOCX, PPTX, CSV, JSON, YAML, TOML, TXT, MD. Max 50 MB per file.</p>
      <button className="dark-button" type="button" disabled={disabled} onClick={() => inputRef.current?.click()}>
        Browse files
      </button>
      <input
        ref={inputRef}
        type="file"
        multiple
        hidden
        accept={supportedExtensions.join(",")}
        onChange={(event) => handleFiles(event.target.files)}
      />
      {error && <p className="upload-error">{error}</p>}
    </div>
  );
}
