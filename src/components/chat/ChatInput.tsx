import { Paperclip, Mic, ArrowUp, X } from "lucide-react";
import React, { useState, useRef } from "react";

export function ChatInput({
  onSend,
  listening,
  onMic,
}: {
  onSend: (message: string, imageBase64?: string, fileBase64?: string, fileName?: string) => void;
  listening?: boolean;
  onMic?: () => void;
}) {
  const [v, setV] = useState("");
  const [fileData, setFileData] = useState<{ name: string; type: string; base64: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      alert("File size exceeds 5MB limit.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setFileData({
        name: file.name,
        type: file.type,
        base64: reader.result as string,
      });
    };
    reader.onerror = () => {
      console.error("Error reading file");
    };
    reader.readAsDataURL(file);
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleSend = () => {
    if (!v.trim() && !fileData) return;

    let imageBase64: string | undefined;
    let fileBase64: string | undefined;
    let fileName: string | undefined;

    if (fileData) {
      fileName = fileData.name;
      const isImage = fileData.type.startsWith("image/") || /\.(jpg|jpeg|png|webp|gif)$/i.test(fileData.name);
      if (isImage) {
        imageBase64 = fileData.base64;
      } else {
        fileBase64 = fileData.base64;
      }
    }

    onSend(v, imageBase64, fileBase64, fileName);
    setV("");
    setFileData(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col w-full">
      {/* File Preview */}
      {fileData && (
        <div className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 border border-gray-200 mb-2 max-w-max text-xs text-gray-700 shadow-sm animate-fade-in">
          {fileData.type.startsWith("image/") ? (
            <img
              src={fileData.base64}
              alt="Upload Preview"
              className="w-10 h-10 rounded object-cover border border-gray-200"
            />
          ) : (
            <span className="text-xl">📄</span>
          )}
          <div className="flex flex-col truncate max-w-[150px]">
            <span className="font-semibold truncate text-[11px]">{fileData.name}</span>
            <span className="text-[9px] text-gray-500">Ready to upload</span>
          </div>
          <button
            onClick={() => {
              setFileData(null);
              if (fileInputRef.current) {
                fileInputRef.current.value = "";
              }
            }}
            className="p-1 hover:bg-gray-200 rounded-full text-gray-500 hover:text-gray-800 transition-colors"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* Input row */}
      <div
        className="flex items-center gap-2 rounded-xl px-2 py-1.5 w-full shadow-sm"
        style={{ background: "#fff", border: "1px solid #e5e7eb" }}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/*,.pdf,.txt"
          className="hidden"
        />
        <button
          onClick={triggerFileSelect}
          className="p-2 rounded-md hover:bg-[#f7f8f6] transition-colors"
        >
          <Paperclip size={16} strokeWidth={1.75} style={{ color: "#6b7280" }} />
        </button>
        {onMic && (
          <button
            className="p-2 rounded-md hover:bg-[#f7f8f6] relative transition-colors"
            onClick={onMic}
          >
            {listening ? (
              <span
                className="w-3 h-3 rounded-full block animate-pulse"
                style={{ background: "#e24b4a" }}
              />
            ) : (
              <Mic size={16} strokeWidth={1.75} style={{ color: "#6b7280" }} />
            )}
          </button>
        )}
        <input
          value={v}
          onChange={(e) => setV(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSend();
            }
          }}
          placeholder={listening ? "Listening..." : "Ask anything in your language..."}
          className="flex-1 bg-transparent outline-none px-2 text-[14px]"
          style={{ color: "#1a1a1a" }}
        />
        <button
          onClick={handleSend}
          className="w-8 h-8 rounded-md flex items-center justify-center transition-transform active:scale-95 cursor-pointer"
          style={{ background: "#3b6d11", color: "#fff" }}
        >
          <ArrowUp size={16} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}

