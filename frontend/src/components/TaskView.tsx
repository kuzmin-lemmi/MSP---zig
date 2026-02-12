import { useEffect, useState } from 'react'
import './TaskView.css'

interface Task {
  id: string
  title: string
  statement: string
  meta: {
    time_limit_ms: number
    memory_mb: number
  }
}

interface TaskViewProps {
  task: Task
}

function TaskView({ task }: TaskViewProps) {
  const [statement, setStatement] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function fetchStatement() {
      setLoading(true)
      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}/tasks/${task.id}`)
        const data = await response.json()
        setStatement(data.statement)
      } catch (error) {
        console.error('Failed to fetch statement:', error)
      } finally {
        setLoading(false)
      }
    }

    if (task.statement) {
      setStatement(task.statement)
    } else {
      fetchStatement()
    }
  }, [task])

  if (loading) {
    return <div className="task-view loading">Loading...</div>
  }

  return (
    <div className="task-view">
      <div className="task-header">
        <h1>{task.title}</h1>
        <div className="task-meta">
          <span className="time-limit">⏱️ {task.meta.time_limit_ms}ms</span>
          <span className="memory-limit">💾 {task.meta.memory_mb}MB</span>
        </div>
      </div>
      <div className="statement-content">
        <pre>{statement}</pre>
      </div>
    </div>
  )
}

export default TaskView
