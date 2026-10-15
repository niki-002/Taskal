import { useState, type FormEvent } from 'react'

import type { TaskCreate } from '../types/task'

interface TaskFormProps {
  onSubmit: (payload: TaskCreate) => Promise<void>
}

// タスク作成フォーム
export function TaskForm({ onSubmit }: TaskFormProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [limit, setLimit] = useState('')

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    try {
      await onSubmit({ title: title.trim(), description: description.trim(), limit: limit.trim() })
      setTitle('')
    } catch (error) {
      alert(error instanceof Error ? error.message : String(error))
    }
  }

  return (
    <fieldset id="create_task">
      <form id="create_form" onSubmit={handleSubmit}>
        <input
          className="text"
          type="text"
          maxLength={200}
          required
          placeholder="タイトル（必須）"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <br />
        <input
          className="text"
          type="text"
          maxLength={1000}
          placeholder="詳細はこちら"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <br />
        <input
          className="date"
          type="date"
          required
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
        />
        <br />
        <button className="button" type="submit">
          追加
        </button>
      </form>
    </fieldset>
  )
}
