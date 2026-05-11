const apiBase = "/api/tasks";

// localStorageに保存したログイントークンを取り出す
function getToken() {
  return localStorage.getItem("access_token");
}

// ログイン必須APIに付けるheadersを作る
function getAuthHeaders() {
  const token = getToken();
  if (!token) {
    throw new Error("ログインしてください");
  }
  return {
    "Authorization": `Bearer ${token}`,
  };
}

// データ取得(リスト)
async function getTasks() {
  const response = await fetch(apiBase, {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error("Failed to get tasks");
  }
  const result = await response.json();
  return result;
}

// データ取得(単体)
async function getTask(task_id) {
  const response = await fetch(`${apiBase}/${task_id}`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error("Failed to get task");
  }
  const result = await response.json();
  return result;
}

// データ登録API
async function createTask(payload) {
  const response = await fetch(apiBase, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders()
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to create task");
  }
  const result = await response.json();
  return result;
}

// データ更新API
async function updatetask(payload, task_id) {
  const response = await fetch(`${apiBase}/${task_id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders()
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error("Failed to update task");
  }
  const result = await response.json();
  return result;
}

// データ削除API 
async function deleteTask(task_id) {
  const response = await fetch(`${apiBase}/${task_id}`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error("Failed to delete task");
  }
  return;
}

// 画面描画関数
function renderTasks(tasks) {
  const list = document.getElementById("task_list");
  list.innerHTML = "";

  for (const task of tasks) {
    const li = document.createElement("li");
    li.className = "item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = task.done_flag;

    // title, description, limit はユーザー入力から来る可能性あり。もしそのまま innerHTML に入れると、悪意あるHTMLやScriptが混ざった場合に危険
    const content = document.createElement("div");
    const title = document.createElement("div")
    title.textContent = task.done_flag ? `✅ ${task.title}` : task.title;
    content.appendChild(title)

    const update_button = document.createElement("button");
    update_button.className = "update";
    update_button.textContent = "編集";
    update_button.addEventListener("click", async () => {
      if (li.querySelector("#update_form")) return;

      const section = document.createElement("section")
      const form = document.createElement("form")
      const title = document.createElement("input")
      const description = document.createElement("input")
      const limit = document.createElement("input")
      const button = document.createElement("button")
      section.id = "page-update"
      form.id = "update_form"
      title.id = "new_title"
      title.type = "text"
      title.maxLength = "200"
      title.required 
      title.placeholder = "タイトル（必須）"
      description.id = "new_description"
      description.type = "text"
      description.maxLength = "1000" 
      description.placeholder = "詳細はこちら"
      limit.id = "new_limit"
      limit.type = "date"
      button.id = "new_submitButton"
      button.type = "submit"
      button.textContent = "更新"
      form.append(title, description, limit, button)
      section.appendChild(form)

      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const newTitle = title.value.trim();
        const newDescription = description.value.trim();
        const newLimit = limit.value.trim();

        try {
          await updatetask(
            {title: newTitle, description: newDescription, limit: newLimit},
            task.id
          );
          await reload();
        } catch(error) {
          alert(error.message);
        }
      });

      li.appendChild(section)
    })

    const delete_button = document.createElement("button");
    delete_button.className = "secondary";
    delete_button.textContent = "削除";
    delete_button.addEventListener("click", async () => {
      if (!confirm("削除しますか？")) return;
      try {
        await deleteTask(task.id);
        await reload();
      } catch (error) {
        alert(error.message);
      }
    });

    li.appendChild(checkbox);
    li.appendChild(content);
    li.appendChild(update_button);
    li.appendChild(delete_button);
    list.appendChild(li);
  }
}

// 再読み込み関数
async function reload() {
  try {
    const tasks = await getTasks();
    renderTasks(tasks);
  } catch(error) {
    alert(error.message);
  }
}

// 新規登録処理
document.getElementById("create_form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("title").value.trim();
  const description = document.getElementById("description").value.trim();
  const limit = document.getElementById("limit").value.trim();

  try {
    await createTask({title, description, limit});
    document.getElementById("title").value = "";
    await reload();
  } catch (error) {
    alert(error.message);
  }
});

reload();

// 再読み込みボタン処理
document.getElementById("reload_button").addEventListener("click", reload);
