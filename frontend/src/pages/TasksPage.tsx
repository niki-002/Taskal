import { useCallback, useEffect, useState } from 'react'

import { createTask, deleteTask, getTasks, updateTask } from '../api/tasks'
import { LogoutButton } from '../components/LogoutButton'
import { ReloadButton } from '../components/ReloadButton'
import { TaskForm } from '../components/TaskForm'
import { TaskList } from '../components/TaskList'
import { useApi } from '../hooks/useApi'
import type { Task, TaskCreate, TaskUpdate } from '../types/task'

export function TasksPage() {
  const request = useApi()
  const [tasks, setTasks] = useState<Task[]>([])

  // 再読み込み
  const reload = useCallback(async () => {
    try {
      setTasks(await getTasks(request))
    } catch (error) {
      alert(error instanceof Error ? error.message : String(error))
    }
  }, [request])

  // 画面表示時に読み込む
  useEffect(() => {
    let ignore = false
    getTasks(request)
      .then((result) => {
        if (!ignore) setTasks(result)
      })
      .catch((error: unknown) => {
        if (!ignore) alert(error instanceof Error ? error.message : String(error))
      })
    return () => {
      ignore = true
    }
  }, [request])

  const handleCreate = async (payload: TaskCreate) => {
    await createTask(request, payload)
    await reload()
  }

  const handleUpdate = async (taskId: number, payload: TaskUpdate) => {
    await updateTask(request, taskId, payload)
    await reload()
  }

  const handleDelete = async (taskId: number) => {
    await deleteTask(request, taskId)
    await reload()
  }

  return (
    <>
      <title>Taskal</title>
      <header className="header">
        <h1>Taskal</h1>
        <LogoutButton />
      </header>

      <TaskForm onSubmit={handleCreate} />

      <TaskList
        tasks={tasks}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
        actions={<ReloadButton onClick={() => void reload()} />}
      />
    </>
  )
}
