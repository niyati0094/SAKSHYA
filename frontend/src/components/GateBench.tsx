import { useState } from 'react';
import { ApiError, apiFetch } from '../api/client';
import type { GateCheckResult } from '../types';

/**
 * Runs the five verification gates against a candidate item without storing
 * anything. A verification pipeline you cannot test is a claim, not a control —
 * this makes the gates demonstrable on demand.
 *
 * The default contents are the failure mode the anchor gate exists for: a
 * factually correct passage turned into a factually wrong question by dropping
 * the population, period and unit the claim depends on.
 */

const DEFAULT_PASSAGE =
  'Among rural households, average monthly per-capita expenditure in 2023-24 ' +
  'was 4,200 rupees, measured over a reference period of 30 days.';

const WEAK_STEM = 'What was average expenditure?';
const STRONG_STEM =
  'Among rural households, what was average monthly per-capita expenditure in ' +
  '2023-24 over a 30 day reference period?';

const OPTIONS = ['4,200 rupees', '8,400 rupees', '2,100 rupees', '6,300 rupees'];

export function GateBench() {
  const [passage, setPassage] = useState(DEFAULT_PASSAGE);
  const [stem, setStem] = useState(WEAK_STEM);
  const [result, setResult] = useState<GateCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch<GateCheckResult>('/questions/check-gates', {
        method: 'POST',
        body: JSON.stringify({ passage, stem, options: OPTIONS, correct_index: 0 }),
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not run the gates.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card gate-bench">
      <h2>Test the gates</h2>
      <p className="muted small">
        Run a candidate question through all five gates. Nothing is saved — this exists so
        the pipeline can be tested rather than taken on trust.
      </p>

      <label className="field">
        <span>Source passage</span>
        <textarea rows={3} value={passage} onChange={(e) => setPassage(e.target.value)} />
      </label>

      <label className="field">
        <span>Candidate question</span>
        <textarea rows={2} value={stem} onChange={(e) => setStem(e.target.value)} />
      </label>

      <div className="bench-presets">
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => {
            setStem(WEAK_STEM);
            setResult(null);
          }}
        >
          Load the flawed version
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => {
            setStem(STRONG_STEM);
            setResult(null);
          }}
        >
          Load the corrected version
        </button>
        <button type="button" className="btn btn-primary" onClick={() => void run()} disabled={busy}>
          {busy ? 'Running gates…' : 'Run all 5 gates'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error small" role="alert">
          {error}
        </div>
      )}

      {result && (
        <div className="bench-result" aria-live="polite">
          <div className={`bench-verdict ${result.passed ? 'ok' : 'fail'}`}>
            {result.passed
              ? '✓ Passed all five gates — publishable'
              : `✗ Rejected by ${result.failed_gate} ${result.failed_gate_name}`}
          </div>

          <ul className="gate-list">
            {result.outcomes.map((outcome) => (
              <li key={outcome.gate} className={outcome.passed ? '' : 'gate-fired'}>
                <span className="gate-code">{outcome.gate}</span>
                <span className="gate-name">{outcome.name}</span>
                <span className="gate-count">{outcome.passed ? 'pass' : 'FAIL'}</span>
              </li>
            ))}
          </ul>

          {result.note && <p className="small bench-note">{result.note}</p>}
        </div>
      )}
    </section>
  );
}
