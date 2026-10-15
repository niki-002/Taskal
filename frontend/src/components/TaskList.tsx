import type { ReactNode } from 'react'

import type { Task, TaskUpdate } from '../types/task'
import { TaskItem } from './TaskItem'

interface TaskListProps {
  tasks: Task[]
  onUpdate: (taskId: number, payload: TaskUpdate) => Promise<void>
  onDelete: (taskId: number) => Promise<void>
  // 一覧の上に表示する操作（再読み込みボタンなど）
  actions?: ReactNode
}

export function TaskList({ tasks, onUpdate, onDelete, actions }: TaskListProps) {
  return (
    <fieldset id="read_task">
      <h2>タスク一覧</h2>
      <div className="row">{actions}</div>
      <br />
      <ul id="task_list" className="list">
        {tasks.map((task) => (
          <TaskItem key={task.id} task={task} onUpdate={onUpdate} onDelete={onDelete} />
        ))}
      </ul>
    </fieldset>
  )
}
