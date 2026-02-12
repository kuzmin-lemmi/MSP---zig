import { useState } from 'react'
import './CodeEditor.css'

interface CodeEditorProps {
  code: string
  onChange: (code: string) => void
  language: string
}

function CodeEditor({ code, onChange, language }: CodeEditorProps) {
  const [localCode, setLocalCode] = useState(code)

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalCode(e.target.value)
    onChange(e.target.value)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault()
      const start = e.target.selectionStart
      const end = e.target.selectionEnd
      const value = localCode
      
      const newValue = value.substring(0, start) + '  ' + value.substring(end)
      e.target.value = newValue
      e.target.selectionStart = e.target.selectionEnd = start + 4
      e.target.selectionEnd = e.target.selectionEnd + 4
      onChange(newValue)
      e.preventDefault()
    }
  }

  return (
    <div className="code-editor">
      <textarea
        value={localCode}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        className="code-input"
        spellCheck={false}
        placeholder="Write your Zig code here..."
      />
      <div className="editor-status">
        <span className="language">{language.toUpperCase()}</span>
        <span className="line-count">{localCode.split('\n').length} lines</span>
      </div>
    </div>
  )
}

export default CodeEditor
