// medseas — minimal local-storage dashboard.
// No backend yet: everything lives in this browser only.

const TASKS_KEY = "medseas.tasks";
const NOTES_KEY = "medseas.notes";

function load(key) {
  try {
    return JSON.parse(localStorage.getItem(key)) || [];
  } catch {
    return [];
  }
}

function save(key, data) {
  localStorage.setItem(key, JSON.stringify(data));
}

// ---- Tasks ----
let tasks = load(TASKS_KEY);

function renderTasks() {
  const list = document.getElementById("task-list");
  list.innerHTML = "";

  if (tasks.length === 0) {
    list.innerHTML = '<li class="empty">No tasks yet.</li>';
    return;
  }

  tasks.forEach((task, i) => {
    const li = document.createElement("li");
    if (task.done) li.classList.add("done");

    const span = document.createElement("span");
    span.className = "task-text";
    span.textContent = task.text;
    span.addEventListener("click", () => {
      tasks[i].done = !tasks[i].done;
      save(TASKS_KEY, tasks);
      renderTasks();
    });

    const removeBtn = document.createElement("button");
    removeBtn.className = "remove-btn";
    removeBtn.textContent = "×";
    removeBtn.addEventListener("click", () => {
      tasks.splice(i, 1);
      save(TASKS_KEY, tasks);
      renderTasks();
    });

    li.append(span, removeBtn);
    list.appendChild(li);
  });
}

document.getElementById("task-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("task-input");
  const text = input.value.trim();
  if (!text) return;
  tasks.push({ text, done: false });
  save(TASKS_KEY, tasks);
  input.value = "";
  renderTasks();
});

// ---- Notes ----
let notes = load(NOTES_KEY);

function renderNotes() {
  const list = document.getElementById("note-list");
  list.innerHTML = "";

  if (notes.length === 0) {
    list.innerHTML = '<li class="empty">No notes yet.</li>';
    return;
  }

  notes.forEach((note, i) => {
    const li = document.createElement("li");

    const span = document.createElement("span");
    span.className = "note-text";
    span.textContent = note;

    const removeBtn = document.createElement("button");
    removeBtn.className = "remove-btn";
    removeBtn.textContent = "×";
    removeBtn.addEventListener("click", () => {
      notes.splice(i, 1);
      save(NOTES_KEY, notes);
      renderNotes();
    });

    li.append(span, removeBtn);
    list.appendChild(li);
  });
}

document.getElementById("note-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("note-input");
  const text = input.value.trim();
  if (!text) return;
  notes.unshift(text);
  save(NOTES_KEY, notes);
  input.value = "";
  renderNotes();
});

renderTasks();
renderNotes();
