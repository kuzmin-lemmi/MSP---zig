import { useState } from 'react'
import './ResultView.css'

interface Job {
  id: string
  state: 'queued' | 'running' | 'done' | 'error'
  created_at: string
  started_at?: string
  finished_at?: string
  queue_position?: number
  running_for_ms?: number
  result?: {
    verdict: 'OK' | 'WA' | 'CE' | 'RE' | 'TLE'
    stdout: string
    stderr: string
    compile_log: string
    time_ms: number
    test_results: Array<{
      test_num: number
      passed: boolean
      expected: string
      actual: string
      time_ms: number
    }>
  }
  error_message?: string
}

interface ResultViewProps {
  job: Job
  onCancel: (jobId: string) => void
  onSelect: () => void
  isActive: boolean
}

function ResultView({ job, onCancel, onSelect, isActive }: ResultViewProps) {
  const [expanded, setExpanded] = useState(isActive)

  const verdictColors = {
    'OK': '#10b981',
    'WA': '#f59e0b',
    'CE': '#ef4444',
    'RE': '#eab308',
    'TLE': '#ff9800'
  }

  const verdictLabels = {
    'OK': '✅ Accepted',
    'WA': '❌ Wrong Answer',
    'CE': '⚠️ Compile Error',
    'RE': '💥 Runtime Error',
    'TLE': '⏱️ Timeout'
  }

  return (
    <div className={`result-view ${expanded ? 'expanded' : ''}`} onClick={onSelect}>
      <div className="result-header">
        <div className="job-status">
          <span className={`status-badge job-${job.state}`}>{job.state.toUpperCase()}</span>
          <span className="job-time">
            {job.finished_at ? `${job.result?.time_ms?.toFixed(2)}ms` : ''}
          </span>
        </div>
        <div className="job-actions">
          {job.state === 'queued' && job.queue_position !== undefined && (
            <span className="queue-position">Position: {job.queue_position + 1}</span>
          )}
          {job.state === 'running' && job.running_for_ms !== undefined && (
            <span className="running-time">Running for {job.running_for_ms}ms</span>
          )}
          {(job.state === 'queued' || job.state === 'running') && (
            <button onClick={() => onCancel(job.id)} className="cancel-btn">
              ✕ Cancel
            </button>
          )}
        </div>
      </div>

      {(expanded || job.state === 'done' || job.state === 'error') && (
        <div className="result-details">
          {job.result && job.result.compile_log && (
            <div className="compile-log">
              <h4>Compilation Output:</h4>
              <pre>{job.result.compile_log}</pre>
            </div>
          )}

          {job.result && job.result.stderr && (
            <div className="stderr">
              <h4>Stderr:</h4>
              <pre>{job.result.stderr}</pre>
            </div>
          )}

          {job.result && job.result.test_results && job.result.test_results.length > 0 && (
            <div className="test-results">
              <h4>Test Results:</h4>
              <div className="tests-grid">
                {job.result.test_results.map(test => (
                  <div key={test.test_num} className={`test-result ${test.passed ? 'passed' : 'failed'}`}>
                    <span className="test-number">#{test.test_num}</span>
                    <span className={`verdict-badge ${job.result?.verdict}`}>
                      {verdictLabels[job.result.verdict]}
                    </span>
                    <div className="test-io">
                      <div className="test-input">
                        <span className="label">Input:</span>
                        <pre>{test.expected.substring(0, Math.min(20, test.expected.length))}</pre>
                      </div>
                      <div className="test-output">
                        <span className="label">Output:</span>
                        <pre>{test.actual.substring(0, Math.min(20, test.actual.length))}</pre>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {job.state === 'error' && job.error_message && (
            <div className="error-message">
              <h4>Error:</h4>
              <p>{job.error_message}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ResultView
