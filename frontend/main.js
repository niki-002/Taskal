const apiBase = "/api/tasks";

function escapeHtml(s) {
  return (s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchTasks() {
  const res = await fetch(apiBase);
  if (!res.ok) throw new Error("Failed to load tasks");
  return await res.json();
}

async function createTask(payload) {
  const res = await fetch(apiBase, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create task");
  return await res.json();
}

async function updateTask(id, payload) {
  const res = await fetch(`${apiBase}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update task");
  return await res.json();
}

async function deleteTask(id) {
  const res = await fetch(`${apiBase}/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete task");
}

function renderTasks(tasks) {
  const list = document.getElementById("taskList");
  list.innerHTML = "";

  for (const t of tasks) {
    const li = document.createElement("li");
    li.className = "item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = t.is_done;

    checkbox.addEventListener("change", async () => {
      try {
        await updateTask(t.id, {
          title: t.title,
          description: t.description,
          due_date: t.due_date,
          is_done: checkbox.checked,
        });
        await reload();
      } catch (e) {
        alert(e.message);
        checkbox.checked = !checkbox.checked;
      }
    });

    const content = document.createElement("div");
    const title = t.is_done ? `✅ ${escapeHtml(t.title)}` : escapeHtml(t.title);
    const desc = t.description ? `<div>${escapeHtml(t.description)}</div>` : "";
    const due = t.due_date ? `期限: ${escapeHtml(t.due_date)}` : "期限: -";
    content.innerHTML = `
      <div><strong>${title}</strong></div>
      ${desc}
      <div class="meta">${due}</div>
    `;

    const delBtn = document.createElement("button");
    delBtn.className = "secondary";
    delBtn.textContent = "削除";
    delBtn.addEventListener("click", async () => {
      if (!confirm("削除しますか？")) return;
      try {
        await deleteTask(t.id);
        await reload();
      } catch (e) {
        alert(e.message);
      }
    });

    li.appendChild(checkbox);
    li.appendChild(content);
    li.appendChild(delBtn);
    list.appendChild(li);
  }
}

async function reload() {
  const tasks = await fetchTasks();
  renderTasks(tasks);
}

document.getElementById("reloadBtn").addEventListener("click", reload);

document.getElementById("createForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("title").value.trim();
  const description = document.getElementById("description").value.trim() || null;
  const due_date = document.getElementById("dueDate").value || null;

  try {
    await createTask({ title, description, due_date });
    document.getElementById("title").value = "";
    document.getElementById("description").value = "";
    document.getElementById("dueDate").value = "";
    await reload();
  } catch (err) {
    alert(err.message);
  }
});

reload();