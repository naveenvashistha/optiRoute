/**
 * Standardizes LaTeX delimiters before they reach the Markdown parser.
 * Uses negative lookbehinds (?<!\\) to safely ignore valid Matrix line breaks like \\[4pt]
 */
export const preprocessLaTeX = (content) => {
  if (!content) return "";
  return content
    .replace(/(?<!\\)\\\[/g, "$$$")
    .replace(/(?<!\\)\\\]/g, "$$$")
    .replace(/(?<!\\)\\\(/g, "$")
    .replace(/(?<!\\)\\\)/g, "$");
};