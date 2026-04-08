const apiBase = "/api/tasks";

// データ取得
async function getTasks() {
  try {
    const response = await fetch(apiBase);
    if (!response.ok) {
      throw new Error("Failed to get tasks");
    }
    const result = await response.json();
    console.log(result);
  } catch(error) {
    console.log(error.message);
  }  
}

// データ登録API
async function createTask(payload) {
  try {
    const response = await fetch(apiBase, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error("Failed to create task");
    }
    const reslut = response.json(); 
    console.log(reslut);
  } catch(error) {
    console.log(error.message);
  } 
}

// データ削除API 
async function deleteTask(id) {
  try {
    const response = await fetch(`${apiBase}/${id}`,
      {"method": "delete"}
    );
    if (!response.ok) {
      throw new Error("Failed to delete task");
    }
    const reslut = response.json();
    console.log(reslut);
  } catch(error) {
    console.log(error.message);
  }
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
    checkbox.checked = task.is_done;
    // チェック入れたときの挙動
    // checkbox.addEventListener("change", async () => {
    //   try {
    //     await updateTask(t.id, {
    //       title: t.title,
    //       description: t.description,
    //       due_date: t.due_date,
    //       is_done: checkbox.checked,
    //     });
    //     await reload();
    //   } catch (e) {
    //     alert(e.message);
    //     checkbox.checked = !checkbox.checked;
    //   }
    // });

    // title, description, due_date はユーザー入力から来る可能性あり。もしそのまま innerHTML に入れると、悪意あるHTMLやScriptが混ざった場合に危険
    const content = document.createElement("div");
    const title = t.is_done ? `✅ ${escapeHtml(t.title)}` : escapeHtml(t.title);
    // const desc = t.description ? `<div>${escapeHtml(t.description)}</div>` : "";
    // const due = t.due_date ? `期限: ${escapeHtml(t.due_date)}` : "期限: -";
    content.innerHTML = `
      <div><strong>${title}</strong></div>
    `;

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
    li.appendChild(delete_button);
    list.appendChild(li);
  }
}

// 再読み込み関数
async function reload() {
  const tasks = await getTasks();
  renderTasks(tasks);
}

// 新規登録処理
document.getElementById("createForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("title").value.trim();

  try {
    await createTask({ title });
    document.getElementById("title").value = "";
    await reload();
  } catch (error) {
    alert(error.message);
  }
});

reload();

// 再読み込みボタン処理
document.getElementById("reload_button").addEventListener("click", reload);