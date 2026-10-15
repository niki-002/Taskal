import type { Task, TaskCreate, TaskUpdate } from '../types/task'
import type { ApiRequest } from './client'

const TASKS_PATH = '/tasks'

// データ取得(リスト)
export function getTasks(request: ApiRequest): Promise<Task[]> {
  return request<Task[]>(TASKS_PATH, { errorMessage: 'Failed to get tasks' })
}

// データ取得(単体)
export function getTask(request: ApiRequest, taskId: number): Promise<Task> {
  return request<Task>(`${TASKS_PATH}/${taskId}`, { errorMessage: 'Failed to get task' })
}

// データ登録
export function createTask(request: ApiRequest, payload: TaskCreate): Promise<Task> {
  return request<Task>(TASKS_PATH, {
    method: 'POST',
    body: payload,
    errorMessage: 'Failed to create task',
  })
}

// データ更新
export function updateTask(
  request: ApiRequest,
  taskId: number,
  payload: TaskUpdate,
): Promise<Task> {
  return request<Task>(`${TASKS_PATH}/${taskId}`, {
    method: 'PUT',
    body: payload,
    errorMessage: 'Failed to update task',
  })
}

// データ削除
export function deleteTask(request: ApiRequest, taskId: number): Promise<void> {
  return request<void>(`${TASKS_PATH}/${taskId}`, {
    method: 'DELETE',
    errorMessage: 'Failed to delete task',
  })
}
