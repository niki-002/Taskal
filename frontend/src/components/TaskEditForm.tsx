import { useState, type FormEvent } from 'react'

import type { TaskUpdate } from '../types/task'

interface TaskEditFormProps {
  onSubmit: (payload: TaskUpdate) => Promise<void>
}

// タスク編集フォーム（現行実装に合わせ、既存値は入れずに空欄で開く）
export function TaskEditForm({ onSubmit }: TaskEditFormProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [limit, setLimit] = useState('')

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    try {
      await onSubmit({ title: title.trim(), description: description.trim(), limit: limit.trim() })
    } catch (error) {
      alert(error instanceof Error ? error.message : String(error))
    }
  }

  return (
    <section>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          maxLength={200}
          placeholder="タイトル（必須）"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <input
          type="text"
          maxLength={1000}
          placeholder="詳細はこちら"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <input type="date" value={limit} onChange={(e) => setLimit(e.target.value)} />
        <button type="submit">更新</button>
      </form>
    </section>
  )
}
