/**
 * MarkdownText — lightweight inline Markdown renderer for AgriGPT AI output.
 *
 * Handles:
 *  - **bold** and *italic* inline spans
 *  - Numbered lists  (1. 2. 3.)  — all items collected into ONE <ol>
 *  - Bullet lists    (lines starting with -  •  or *)
 *  - Plain paragraphs / blank-line separation
 *
 * No external dependencies — pure React JSX.
 */

import React from "react";

// ── inline renderer ──────────────────────────────────────────────────────────

function renderInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} style={{ fontWeight: 600, color: "#1a1a1a" }}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return (
        <em key={i} style={{ fontStyle: "italic" }}>
          {part.slice(1, -1)}
        </em>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

// ── block parser ─────────────────────────────────────────────────────────────

type Block =
  | { type: "bullet";  items: string[] }
  | { type: "ordered"; items: string[] }
  | { type: "paragraph"; text: string };

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.split("\n");
  const blocks: Block[] = [];

  let currentBullet:  string[] | null = null;
  let currentOrdered: string[] | null = null;

  // Separate helpers — so flushing one list type doesn't reset the other
  const flushBullet = () => {
    if (currentBullet) {
      blocks.push({ type: "bullet", items: currentBullet });
      currentBullet = null;
    }
  };
  const flushOrdered = () => {
    if (currentOrdered) {
      blocks.push({ type: "ordered", items: currentOrdered });
      currentOrdered = null;
    }
  };
  const flushAll = () => { flushBullet(); flushOrdered(); };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    // ── Numbered list item: "1. text" / "2.  text"
    const orderedMatch = line.match(/^\s*\d+\.\s+(.+)$/);
    if (orderedMatch) {
      flushBullet();                          // close any open bullet list
      // ↳ intentionally do NOT flush ordered — keep accumulating into same <ol>
      if (!currentOrdered) currentOrdered = [];
      currentOrdered.push(orderedMatch[1]);
      continue;
    }

    // ── Bullet item: "- text" / "• text" / "* text" (single asterisk only)
    const bulletMatch =
      line.match(/^\s*[-•]\s+(.+)$/) ||
      line.match(/^\s*\*(?!\*)\s+(.+)$/);
    if (bulletMatch) {
      flushOrdered();                         // close any open ordered list
      if (!currentBullet) currentBullet = [];
      currentBullet.push(bulletMatch[1]);
      continue;
    }

    // ── Blank line
    // Gemini puts blank lines between numbered tips — ignore them when inside
    // a list so numbering isn't broken.  Outside a list, just skip (paragraph
    // separation happens naturally when the next plain line is processed).
    if (line.trim() === "") {
      continue;
    }

    // ── Plain text line — close any open list, then merge into paragraph
    flushAll();
    const last = blocks[blocks.length - 1];
    if (last?.type === "paragraph") {
      last.text += " " + line.trim();
    } else {
      blocks.push({ type: "paragraph", text: line.trim() });
    }
  }

  flushAll();
  return blocks;
}

// ── main component ────────────────────────────────────────────────────────────

interface MarkdownTextProps {
  children: string;
  style?: React.CSSProperties;
}

export function MarkdownText({ children, style }: MarkdownTextProps) {
  const blocks = parseBlocks(children);

  const baseStyle: React.CSSProperties = {
    fontSize: 13,
    color: "#1a1a1a",
    lineHeight: 1.7,
    ...style,
  };

  return (
    <div style={baseStyle}>
      {blocks.map((block, bi) => {
        if (block.type === "bullet") {
          return (
            <ul
              key={bi}
              style={{ margin: "6px 0", paddingLeft: 18, listStyleType: "disc" }}
            >
              {block.items.map((item, ii) => (
                <li key={ii} style={{ marginBottom: 4 }}>
                  {renderInline(item)}
                </li>
              ))}
            </ul>
          );
        }

        if (block.type === "ordered") {
          return (
            <ol
              key={bi}
              style={{ margin: "6px 0", paddingLeft: 20, listStyleType: "decimal" }}
            >
              {block.items.map((item, ii) => (
                <li key={ii} style={{ marginBottom: 4 }}>
                  {renderInline(item)}
                </li>
              ))}
            </ol>
          );
        }

        return (
          <p key={bi} style={{ margin: "4px 0" }}>
            {renderInline(block.text)}
          </p>
        );
      })}
    </div>
  );
}
