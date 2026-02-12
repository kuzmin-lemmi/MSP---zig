import { useState } from 'react'
import './TaskList.css'

interface Task {
  id: string
  title: string
  module: string
  time_limit_ms: number
}

interface TaskListProps {
  tasks: Task[]
  onSelect: (task: Task | null) => void
  currentJobId: string | null
}

function TaskList({ tasks, onSelect, currentJobId }: TaskListProps) {
  return (
    <div className="task-list">
      <h2>Select a Task</h2>
      <div className="tasks-grid">
        {tasks.map(task => (
          <div
            key={task.id}
            className={`task-card ${currentJobId === task.id ? 'running' : ''}`}
            onClick={() => onSelect(task)}
          >
            <h3>{task.title}</h3>
            <div className="task-meta">
              <span className="module">{task.module}</span>
              <span className="time-limit">{task.time_limit_ms}ms</span>
            </div>
            <div className="task-status">
              {currentJobId === task.id && <span className="status-badge">Running</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default TaskList
