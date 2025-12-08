import { useRef, useState } from "react";
import type { FC, ChangeEvent, DragEvent, ReactNode } from "react";

interface FileUploadProps {
  // Accept either a single File or an array of Files. When the user selects/drops
  // only one file we'll pass the single File to the handler (matches callers
  // like JobPostsForm.handleFileSelect which expect a single File).
  onFileSelect: (files: File | File[]) => void;
  children: ReactNode; // Accepts any JSX as button content
  className?: string; // Allows parent to pass custom styles
}

const FileUpload: FC<FileUploadProps> = ({ onFileSelect, children, className }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleUploadClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      // Always pass an array of File objects for consistency across callers.
      // Callers that expect a single File can use files[0].
      onFileSelect(files);
    }
    // Clear the input value to allow the same files to be selected again
    if (e.target.value) {
      e.target.value = "";
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length > 0) {
      // Always pass an array of File objects for consistency across callers.
      onFileSelect(files);
    }
  };

  return (
    <div
      className={`${className} ${isDragging ? "border-blue-600 bg-blue-50" : ""} flex items-center justify-center`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <button
        type="button"
        className="flex flex-col items-center justify-center w-full h-full"
        onClick={handleUploadClick}
      >
        {children}
      </button>
      <input
        ref={fileInputRef}
        type="file"
  accept=".pdf,.doc,.docx,.csv"
        style={{ display: "none" }}
        onChange={handleFileChange}
        multiple
      />
    </div>
  );
};

export default FileUpload;