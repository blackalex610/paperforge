import React, { useCallback, useEffect, useRef, useState } from 'react';
import SceneRenderer from './components/SceneRenderer';
import { renderMathText } from './components/MathRenderer';
import type { Paper, Question } from './types';

const REPO_URL = 'https://github.com/blackalex610/paperforge';
const MAX_SEED = 2 ** 32 - 1;

const FORMATS = [
  { code: 'nvo2026', label: '2026 paper', hint: '24 items, with a short-answer block' },
  { code: 'classic', label: '2024–25 paper', hint: '23 items, 20 multiple choice' },
];

const LEVELS = [
  { code: 'easy', label: 'Easy' },
  { code: 'medium', label: 'Medium' },
  { code: 'actual', label: 'Real exam' },
  { code: 'extra_hard', label: 'Extra hard' },
];

const KIND_LABEL: Record<Question['kind'], string> = {
  mc: 'multiple choice',
  short: 'short answer',
  open: 'extended, marked by parts',
};

interface Params { blueprint: string; difficulty: string; seed: number; key: boolean }

const randomSeed = () => crypto.getRandomValues(new Uint32Array(1))[0] % 1_000_000;

function readParams(): Params {
  const q = new URLSearchParams(window.location.search);
  const seed = Number(q.get('seed'));
  return {
    blueprint: FORMATS.some((f) => f.code === q.get('format')) ? q.get('format')! : 'nvo2026',
    difficulty: LEVELS.some((l) => l.code === q.get('level')) ? q.get('level')! : 'actual',
    seed: Number.isInteger(seed) && seed >= 0 && seed <= MAX_SEED && q.has('seed') ? seed : randomSeed(),
    key: q.get('key') === '1',
  };
}

function writeParams(p: Params) {
  const q = new URLSearchParams({ format: p.blueprint, level: p.difficulty, seed: String(p.seed) });
  if (p.key) q.set('key', '1');
  window.history.replaceState(null, '', `?${q}`);
}

const apiUrl = (p: Params) =>
  `/api/generate?blueprint=${p.blueprint}&difficulty=${p.difficulty}&seed=${p.seed}`;

/** Keys are plain text; lift the exponents so „x^2” reads as x². */
const SUPERSCRIPT: Record<string, string> = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴' };
const prettyKey = (s: string) => s.replace(/\^(\d)/g, (_, d: string) => SUPERSCRIPT[d] ?? `^${d}`);

// ─── the paper ──────────────────────────────────────────────────────────────

const Options: React.FC<{ q: Question; showKey: boolean }> = ({ q, showKey }) => {
  const opts = (q.options ?? []).map((o) => {
    const m = /^([А-Г])\)\s*(.*)$/s.exec(o);
    return m ? { letter: m[1], text: m[2] } : { letter: '', text: o };
  });
  const longest = Math.max(...opts.map((o) => o.text.replace(/\\[a-z]+|[{}$]/g, '').length));
  return (
    <ol className={`options ${longest > 26 ? 'options-stacked' : ''}`}>
      {opts.map((o) => {
        const correct = showKey && o.letter === q.correct_answer;
        return (
          <li key={o.letter} className={correct ? 'is-correct' : undefined}>
            <span className="letter">{o.letter})</span>
            <span>{renderMathText(o.text)}</span>
            {correct && <span className="sr-only"> (correct)</span>}
          </li>
        );
      })}
    </ol>
  );
};

const KeyNote: React.FC<{ q: Question }> = ({ q }) => {
  const answers = Array.isArray(q.correct_answer) ? q.correct_answer : [q.correct_answer ?? ''];
  const letters = q.open_parts ?? [];
  return (
    <div className="key">
      {q.kind !== 'mc' && (
        <p className="key-answer">
          {answers.map((a, i) => (
            <span key={i}>
              {letters[i] && <b>{letters[i]}) </b>}
              {prettyKey(a)}
            </span>
          ))}
        </p>
      )}
      {q.solution && (
        <details open={q.kind !== 'open'}>
          <summary>{q.kind === 'open' ? 'Marking scheme' : 'Worked answer'}</summary>
          <div className="key-solution">{renderMathText(q.solution)}</div>
        </details>
      )}
      {q.partial_credit && (
        <p className="key-partial">
          Part marks:{' '}
          {Object.entries(q.partial_credit).map(([ans, pts]) => `„${ans}” earns ${pts}`).join('; ')}
        </p>
      )}
    </div>
  );
};

const Item: React.FC<{ q: Question; showKey: boolean }> = ({ q, showKey }) => {
  const total = q.points.reduce((a, b) => a + b, 0);
  const split = q.points.length > 1 ? ` (${q.points.join(' + ')})` : '';
  return (
    <li className={`item item-${q.kind}`} id={`q${q.number}`}>
      <div className="item-body">
        <span className="num">{q.number}.</span>
        <div className="stem">{renderMathText(q.question)}</div>
        {q.diagram_config && <SceneRenderer scene={q.diagram_config} />}
        {q.kind === 'mc' && <Options q={q} showKey={showKey} />}
        {q.kind === 'short' && <p className="answer-line">Отговор: <span /></p>}
        {showKey && <KeyNote q={q} />}
      </div>
      <aside className="margin-note" aria-label={`Build notes for item ${q.number}`}>
        <span>{total} т.{split}, {KIND_LABEL[q.kind]}</span>
        <code title="The template that wrote this item">{q.template}</code>
      </aside>
    </li>
  );
};

const Sheet: React.FC<{ paper: Paper; showKey: boolean }> = ({ paper, showKey }) => {
  const part1 = paper.questions.filter((q) => q.section === 'part1');
  const part2 = paper.questions.filter((q) => q.section === 'part2');
  const p1pts = part1.reduce((s, q) => s + q.points.reduce((a, b) => a + b, 0), 0);
  const render = (qs: Question[]) =>
    qs.map((q) => (
      <React.Fragment key={q.number}>
        {paper.scale_notice_before === q.number && (
          <li className="scale-notice" role="note">{paper.scale_notice}</li>
        )}
        <Item q={q} showKey={showKey} />
      </React.Fragment>
    ));

  return (
    <article className="sheet" lang="bg" aria-label="Generated exam paper">
      <header className="sheet-head">
        <p>Национално външно оценяване по математика, VII клас</p>
        <h2>{paper.blueprint_label} <span>· {paper.difficulty_label}</span></h2>
      </header>
      <section>
        <h3>Първа част <span>{paper.part1_minutes} минути, {p1pts} точки</span></h3>
        <ol className="items">{render(part1)}</ol>
      </section>
      <section>
        <h3>Втора част <span>{paper.part2_minutes} минути, {paper.total_points - p1pts} точки</span></h3>
        <p className="part2-note">Запишете решенията с необходимите обосновки.</p>
        <ol className="items">{render(part2)}</ol>
      </section>
    </article>
  );
};

// ─── the page ───────────────────────────────────────────────────────────────

function Segmented<T extends string>({ name, value, options, onChange }: {
  name: string; value: T; options: { code: string; label: string; hint?: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <fieldset className="segmented">
      <legend>{name}</legend>
      <div>
        {options.map((o) => (
          <label key={o.code} title={o.hint}>
            <input type="radio" name={name} value={o.code} checked={value === o.code}
                   onChange={() => onChange(o.code as T)} />
            <span>{o.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function App() {
  const [params, setParams] = useState<Params>(readParams);
  const [seedDraft, setSeedDraft] = useState(String(params.seed));
  const [paper, setPaper] = useState<Paper | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [roundTrip, setRoundTrip] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const request = useRef(0);

  const { blueprint, difficulty, seed } = params;
  useEffect(() => {
    const id = ++request.current;
    const p = { blueprint, difficulty, seed, key: false };
    setLoading(true);
    setError(null);
    const t0 = performance.now();
    fetch(apiUrl(p))
      .then(async (r) => {
        const body = await r.json();
        if (!r.ok) throw new Error(body.error ?? `HTTP ${r.status}`);
        return body as Paper;
      })
      .then((body) => {
        if (id !== request.current) return;
        setPaper(body);
        setRoundTrip(Math.round(performance.now() - t0));
      })
      .catch((e: Error) => id === request.current && setError(e.message))
      .finally(() => id === request.current && setLoading(false));
  }, [blueprint, difficulty, seed]);

  useEffect(() => writeParams(params), [params]);

  const update = useCallback((patch: Partial<Params>) => {
    setParams((p) => ({ ...p, ...patch }));
    if (patch.seed !== undefined) setSeedDraft(String(patch.seed));
  }, []);

  const submitSeed = (e: React.FormEvent) => {
    e.preventDefault();
    const n = Number(seedDraft);
    if (Number.isInteger(n) && n >= 0 && n <= MAX_SEED) update({ seed: n });
    else setSeedDraft(String(params.seed));
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch { /* clipboard blocked: the URL bar has the same link */ }
  };

  return (
    <>
      <header className="masthead">
        <div className="wrap">
          <h1>PaperForge</h1>
          <p className="lede">
            Writes Bulgaria’s national 7th-grade maths exam (НВО) from scratch: {paper?.meta.template_count ?? 127} item
            templates, answer keys computed rather than typed, and figures that are checked before
            they are drawn. The paper below was written for you just now.
          </p>
        </div>
      </header>

      <main className="wrap">
        <form className="controls" onSubmit={submitSeed}>
          <Segmented name="Format" value={params.blueprint} options={FORMATS}
                     onChange={(v) => update({ blueprint: v })} />
          <Segmented name="Level" value={params.difficulty} options={LEVELS}
                     onChange={(v) => update({ difficulty: v })} />
          <label className="seed">
            <span>Seed</span>
            <input inputMode="numeric" value={seedDraft} aria-describedby="seed-hint"
                   onChange={(e) => setSeedDraft(e.target.value.replace(/\D/g, ''))}
                   onBlur={submitSeed} />
          </label>
          <button type="button" className="primary" onClick={() => update({ seed: randomSeed() })}>
            New paper
          </button>
          <label className="toggle">
            <input type="checkbox" checked={params.key} onChange={(e) => update({ key: e.target.checked })} />
            <span>Answer key</span>
          </label>
        </form>

        <p className="receipt" id="seed-hint" aria-live="polite">
          {error ? (
            <span className="receipt-error">The generator refused this request: {error}</span>
          ) : paper ? (
            <>
              Built and verified in <b>{paper.meta.generation_ms} ms</b>
              {roundTrip !== null && <> ({roundTrip} ms round trip)</>} from seed <b>{paper.meta.seed}</b>.
              The same seed always gives the same paper.{' '}
              <button type="button" className="link" onClick={copyLink}>
                {copied ? 'Link copied' : 'Copy link to this paper'}
              </button>{' '}
              <a href={apiUrl({ ...params, key: true })} target="_blank" rel="noreferrer">View the JSON</a>
            </>
          ) : (
            'Writing a paper…'
          )}
        </p>

        <div className={`desk ${loading ? 'is-loading' : ''}`} aria-busy={loading}>
          {paper && <Sheet paper={paper} showKey={params.key} />}
        </div>

        <section className="explainer" aria-labelledby="how">
          <h2 id="how">How a paper gets written</h2>
          <ol className="pipeline">
            <li>
              <h3>Blueprint</h3>
              <p>Each exam year’s format is data: positions, topics, points (65 + 35) and item kinds,
                validated when the module loads. A new format is one entry, not new code.</p>
            </li>
            <li>
              <h3>Templates</h3>
              <p>127 templates, each a parameter space plus the code that turns one sample into a stem,
                a key, distractors from the eight wrong-answer families in the real papers, and a figure.
                Bad draws are rejected, never rounded.</p>
            </li>
            <li>
              <h3>Verifier</h3>
              <p>Every item and then the whole paper must pass: Bulgarian prose outside the maths,
                one correct option, balanced answer letters, no repeated figure, no label touching a line.
                A failure resamples the slot.</p>
            </li>
            <li>
              <h3>Paper</h3>
              <p>A deterministic function of blueprint, level and seed, so any paper is reproducible
                from its link and cacheable at the edge forever.</p>
            </li>
          </ol>
          <dl className="facts">
            <div><dt>1,400+</dt><dd>tests, including every Part 2 key re-derived by an independent parser</dd></div>
            <div><dt>10<sup>61</sup></dt><dd>distinct Part 1 combinations in the 2026 format, a counted lower bound</dd></div>
            <div><dt>500 / 500</dt><dd>generated figures passed a visual review with no faults</dd></div>
            <div><dt>0</dt><dd>runtime dependencies: the engine is the Python standard library</dd></div>
          </dl>
          <p className="source">
            Source, design notes and the realism study: <a href={REPO_URL}>{REPO_URL.replace('https://', '')}</a>.
            Part of <a href="https://smartnvo.vercel.app">SmartNVO</a>.
          </p>
        </section>
      </main>
    </>
  );
}
