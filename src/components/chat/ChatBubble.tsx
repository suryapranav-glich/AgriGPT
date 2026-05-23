import React from "react";
import { AgentPill, type AgentType } from "../ui/AgentPill";

function normalizeMarkdown(text: string): string {
  if (!text) return "";
  // Matches spaces followed by * or -, preceded by punctuation or start of string,
  // and followed by ** or a letter/number.
  const inlineBulletRegex = /(?<=[\p{P}]|^)\s+([*\-])\s+(?=\*\*|\p{L}|\p{N})/gu;
  return text.replace(inlineBulletRegex, "\n$1 ");
}

function parseText(text: string): React.ReactNode[] {
  const elements: React.ReactNode[] = [];
  let i = 0;
  let currentText = "";

  while (i < text.length) {
    if (text.startsWith("**", i)) {
      const closeIdx = text.indexOf("**", i + 2);
      if (closeIdx !== -1) {
        if (currentText) {
          elements.push(currentText);
          currentText = "";
        }
        const innerText = text.substring(i + 2, closeIdx);
        elements.push(
          <strong key={i} className="font-bold text-[#1b3d1b]">
            {parseText(innerText)}
          </strong>
        );
        i = closeIdx + 2;
        continue;
      }
    } else if (text.startsWith("*", i)) {
      let closeIdx = -1;
      for (let j = i + 1; j < text.length; j++) {
        if (text[j] === "*") {
          if (text.startsWith("**", j)) {
            j++;
            continue;
          }
          closeIdx = j;
          break;
        }
      }
      if (closeIdx !== -1) {
        if (currentText) {
          elements.push(currentText);
          currentText = "";
        }
        const innerText = text.substring(i + 1, closeIdx);
        elements.push(
          <em key={i} className="italic text-slate-600">
            {parseText(innerText)}
          </em>
        );
        i = closeIdx + 1;
        continue;
      }
    }
    currentText += text[i];
    i++;
  }

  if (currentText) {
    elements.push(currentText);
  }

  return elements;
}

function formatMessageContent(text: string): React.ReactNode[] {
  if (!text) return [];
  const normalizedText = normalizeMarkdown(text);
  const lines = normalizedText.split("\n");
  const elements: React.ReactNode[] = [];
  let currentListItems: React.ReactNode[] = [];
  let listKey = 0;

  const pushCurrentList = () => {
    if (currentListItems.length > 0) {
      elements.push(
        <ul key={`list-${listKey++}`} className="list-disc pl-5 my-3.5 space-y-2 text-slate-800">
          {currentListItems}
        </ul>
      );
      currentListItems = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) {
      pushCurrentList();
      continue;
    }

    const isHR = /^(?:\*{3,}|-{3,}|_{3,})$/.test(line);
    const isBullet = /^[*|-]\s+/.test(line);

    if (isHR) {
      pushCurrentList();
      elements.push(<hr key={`hr-${i}`} className="my-4 border-t border-slate-200" />);
    } else if (isBullet) {
      let content = line.substring(1).trim();
      currentListItems.push(
        <li key={`li-${i}`} className="leading-relaxed text-[13.5px] md:text-[14px]">
          {parseText(content)}
        </li>
      );
    } else {
      pushCurrentList();
      elements.push(
        <p key={`p-${i}`} className="mb-3 last:mb-0 leading-relaxed text-justify text-slate-800 text-[13.5px] md:text-[14px]">
          {parseText(line)}
        </p>
      );
    }
  }
  pushCurrentList();
  return elements;
}

export function ChatBubble({
  role,
  text,
  agent,
  image_base64,
  file_base64,
  file_name,
}: {
  role: "user" | "ai";
  text: string;
  agent?: AgentType;
  image_base64?: string;
  file_base64?: string;
  file_name?: string;
}) {
  const renderAttachment = () => {
    if (image_base64) {
      return (
        <div className="mt-2 rounded-lg overflow-hidden max-w-[260px] border border-gray-250 shadow-sm bg-white">
          <img
            src={image_base64.startsWith("data:") ? image_base64 : `data:image/png;base64,${image_base64}`}
            alt={file_name || "Attachment"}
            className="w-full h-auto object-cover max-h-[180px] block"
          />
        </div>
      );
    }
    if (file_base64 && file_name) {
      return (
        <div className="mt-2 flex items-center gap-2 p-2 rounded-lg bg-gray-50 border border-gray-200 text-xs text-gray-700 max-w-[260px] shadow-sm">
          <span className="text-base">📄</span>
          <span className="font-medium truncate flex-1">{file_name}</span>
          <a
            href={file_base64.startsWith("data:") ? file_base64 : `data:application/octet-stream;base64,${file_base64}`}
            download={file_name}
            className="text-emerald-700 hover:underline hover:text-emerald-800 shrink-0 font-semibold px-1"
          >
            Download
          </a>
        </div>
      );
    }
    return null;
  };

  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[78%] md:max-w-[72%] px-5 py-3.5 rounded-2xl rounded-br-sm shadow-sm flex flex-col gap-1"
          style={{ background: "#f4f8f0", color: "#1e293b", border: "1px solid #e2ecd6" }}
        >
          <div className="text-[13.5px] md:text-[14px] leading-relaxed text-slate-800 break-words">
            {text}
          </div>
          {renderAttachment()}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5 items-start">
      {agent && <AgentPill type={agent} />}
      <div
        className="max-w-[85%] md:max-w-[78%] px-5 py-4 rounded-2xl rounded-bl-sm shadow-[0_2px_12px_rgba(0,0,0,0.03)]"
        style={{ background: "#ffffff", border: "1px solid #e9ede5", color: "#1e293b" }}
      >
        <div className="flex flex-col gap-2">
          {formatMessageContent(text)}
        </div>
        {renderAttachment()}
      </div>
    </div>
  );
}

