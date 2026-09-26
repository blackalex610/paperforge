/**
 * Text with inline `$…$` and display `$$…$$` maths, rendered with KaTeX.
 *
 * The generator keeps Bulgarian prose outside the dollar signs and maths
 * inside (the verifier enforces it), so a plain split on the delimiters is
 * all the parsing this needs.
 */
import React from 'react';
import katex from 'katex';

const MACROS = { '\\tg': '\\tan', '\\ctg': '\\cot' };

function tex(formula: string, display: boolean): string {
  return katex.renderToString(formula, {
    displayMode: display, throwOnError: false, macros: MACROS,
  });
}

function renderLine(line: string, lineKey: number): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /\$\$([^$]+)\$\$|\$([^$]+)\$/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(line))) {
    if (m.index > last) out.push(line.slice(last, m.index));
    const display = m[1] !== undefined;
    out.push(
      <span
        key={`${lineKey}-${k++}`}
        className={display ? 'math-display' : 'math'}
        dangerouslySetInnerHTML={{ __html: tex(display ? m[1] : m[2], display) }}
      />,
    );
    last = m.index + m[0].length;
  }
  if (last < line.length) out.push(line.slice(last));
  return out;
}

export function renderMathText(input: string | null | undefined): React.ReactNode {
  if (!input) return null;
  const lines = input.split('\n');
  return lines.map((line, i) => (
    <React.Fragment key={i}>
      {renderLine(line, i)}
      {i < lines.length - 1 && <br />}
    </React.Fragment>
  ));
}

export const MathText: React.FC<{ text: string | null | undefined }> = ({ text }) => (
  <>{renderMathText(text)}</>
);
