import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import CodeEditor from './components/CodeEditor'
import TaskList from './components/TaskList'
import TaskView from './components/TaskView'
import ResultView from './components/ResultView'
import './App.css'

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

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function App() {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [tasks, setTasks] = useState<any[]>([])
  const [selectedTask, setSelectedTask] = useState<any | null>(null)
  const [editorCode, setEditorCode] = useState('const std = @import("std");\npub fn main() !void {\n  try std.io.getStdOut().writer().print("Hello, World!", .{});\n}')

  useEffect(() => {
    fetchTasks()
    const interval = setInterval(() => {
      if (currentJobId) {
        fetchJobStatus(currentJobId)
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [currentJobId])

  async function fetchTasks() {
    try {
      const response = await fetch(`${API_BASE}/tasks`)
      const data = await response.json()
      setTasks(data)
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
    }
  }

  async function fetchJobStatus(jobId: string) {
    try {
      const response = await fetch(`${API_BASE}/jobs/${jobId}`)
      const data = await response.json()
      
      setJobs(prev => {
        const index = prev.findIndex(j => j.id === jobId)
        if (index !== -1) {
          const newJobs = [...prev]
          newJobs[index] = data
          return newJobs
        }
        return prev
      })
      
      if (data.state === 'done' && data.result) {
        setEditorCode(data.result.test_results[data.result.test_results.length - 1]?.actual || data.result.stdout || '')
      }
    } catch (error) {
      console.error('Failed to fetch job status:', error)
    }
  }

  async function submitSolution() {
    if (!selectedTask || !editorCode) {
      alert('Please select a task and write code')
      return
    }

    setCurrentJobId(null)

    try {
      const response = await fetch(`${API_BASE}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: selectedTask.id,
          code: editorCode,
          mode: 'check'
        })
      })

      const data = await response.json()
      setCurrentJobId(data.job_id)
      
      const newJob: Job = {
        id: data.job_id,
        state: 'queued',
        created_at: new Date().toISOString(),
        result: undefined
      }

      setJobs(prev => [...prev, newJob])
    } catch (error) {
      console.error('Failed to submit:', error)
      alert('Failed to submit solution')
    }
  }

  async function cancelJob(jobId: string) {
    try {
      const response = await fetch(`${API_BASE}/jobs/${jobId}`, {
        method: 'DELETE'
      })

      const data = await response.json()
      if (data.cancelled) {
        setJobs(prev => prev.filter(j => j.id !== jobId))
        if (currentJobId === jobId) {
          setCurrentJobId(null)
        }
      }
    } catch (error) {
      console.error('Failed to cancel job:', error)
    }
  }

  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route path="/" element={
            <div className="container">
              <header className="header">
                <h1>🦎 Zig Exercise Trainer</h1>
                <nav>
                  <button onClick={() => setSelectedTask(null)} className={selectedTask ? '' : 'active'}>
                    📋 Tasks
                  </button>
                  <button onClick={() => setSelectedTask(jobs.find(j => j.id === currentJobId)?.request?.task_id || null)} className="active">
                    📊 Results
                  </button>
                </nav>
              </header>

              <main className="main">
                {selectedTask && (
                  <div className="task-panel">
                    <TaskView task={selectedTask} />
                    <CodeEditor
                      code={editorCode}
                      onChange={setEditorCode}
                      language="zig"
                    />
                    <div className="actions">
                      <button onClick={submitSolution} className="submit-btn">
                        ✅ Check
                      </button>
                    </div>
                  </div>
                )}

                {!selectedTask && (
                  <div className="tasks-list">
                    <h2>Available Tasks</h2>
                    <TaskList
                      tasks={tasks}
                      onSelect={setSelectedTask}
                      currentJobId={currentJobId}
                    />
                  </div>
                )}

                {jobs.length > 0 && (
                  <div className="results-panel">
                    <h2>Recent Jobs</h2>
                    <div className="jobs-grid">
                      {jobs.slice().reverse().map(job => (
                        <ResultView
                          key={job.id}
                          job={job}
                          onCancel={cancelJob}
                          onSelect={() => setCurrentJobId(job.id)}
                          isActive={currentJobId === job.id}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </main>
            </div>
          } />
          <Route path="/task/:taskId" element={
            <div className="container">
              <TaskView task={selectedTask || tasks[0]} />
              <CodeEditor
                code={editorCode}
                onChange={setEditorCode}
                language="zig"
              />
              <div className="actions">
                <button onClick={submitSolution} className="submit-btn">
                  ✅ Check
                </button>
              </div>
            </div>
          } />
        </Routes>
      </div>
  )
}

export default App
