import { useState } from 'react'

import type { Task, TaskUpdate } from '../types/task'
import { TaskEditForm } from './TaskEditForm'

interface TaskItemProps {
  task: Task
  onUpdate: (taskId: number, payload: TaskUpdate) => Promise<void>
  onDelete: (taskId: number) => Promise<void>
}

export function TaskItem({ task, onUpdate, onDelete }: TaskItemProps) {
  const [isEditing, setIsEditing] = useState(false)

  const handleUpdate = async (payload: TaskUpdate) => {
    await onUpdate(task.id, payload)
    setIsEditing(false)
  }

  const handleDelete = async () => {
    if (!confirm('削除しますか？')) return
    try {
      await onDelete(task.id)
    } catch (error) {
      alert(error instanceof Error ? error.message : String(error))
    }
  }

  return (
    <li className="item">
      {/* 完了状態の更新は未実装（現行実装と同じく表示のみ） */}
      <input type="checkbox" defaultChecked={task.done_flag} />
      <div>
        <div>{task.done_flag ? `✅ ${task.title}` : task.title}</div>
      </div>
      <button className="button" type="button" onClick={() => setIsEditing((prev) => !prev)}>
        編集
      </button>
      <button className="button" type="button" onClick={handleDelete}>
        削除
      </button>
      {isEditing && <TaskEditForm onSubmit={handleUpdate} />}
    </li>
  )
}
