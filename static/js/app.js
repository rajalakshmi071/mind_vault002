const grid = document.querySelector("#notes-grid");
const template = document.querySelector("#note-template");
const dialog = document.querySelector("#note-dialog");
const form = document.querySelector("#note-form");
const search = document.querySelector("#search-input");
const subjectFilter = document.querySelector("#subject-filter");
const toast = document.querySelector("#toast");
let editingId = null;
let searchTimer;
let toastTimer;

async function api(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { "Content-Type": "application/json", ...options.headers } });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}

function notify(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2700);
}

function prettyDate(value) {
  const date = new Date(`${value.replace(" ", "T")}Z`);
  return Number.isNaN(date.getTime()) ? "JUST NOW" : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date).toUpperCase();
}

function renderNotes(notes) {
  grid.replaceChildren();
  for (const note of notes) {
    const card = template.content.firstElementChild.cloneNode(true);
    card.querySelector(".note-subject").textContent = note.subject;
    card.querySelector(".note-date").textContent = prettyDate(note.created_at);
    card.querySelector(".note-title").textContent = note.title;
    card.querySelector(".note-content").textContent = note.content || "No details added yet.";
    card.querySelector(".note-updated").textContent = `UPDATED ${prettyDate(note.updated_at)}`;
    const tags = card.querySelector(".note-tags");
    for (const value of note.tags) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = value;
      tags.append(tag);
    }
    card.querySelector(".edit-note").addEventListener("click", () => openDialog(note));
    card.querySelector(".delete-note").addEventListener("click", () => removeNote(note));
    grid.append(card);
  }
  grid.hidden = notes.length === 0;
  document.querySelector("#empty-state").hidden = notes.length !== 0;
  document.querySelector("#result-count").textContent = `${notes.length} ${notes.length === 1 ? "entry" : "entries"} shown`;
  const filtered = Boolean(search.value.trim() || subjectFilter.value);
  document.querySelector("#empty-title").textContent = filtered ? "No matching thoughts" : "Your vault is ready";
  document.querySelector("#empty-copy").textContent = filtered ? "Try another search or clear the subject filter." : "Save the first idea you want to remember.";
  document.querySelector("#empty-create").hidden = filtered;
}

async function loadNotes() {
  const params = new URLSearchParams();
  if (search.value.trim()) params.set("q", search.value.trim());
  if (subjectFilter.value) params.set("subject", subjectFilter.value);
  grid.setAttribute("aria-busy", "true");
  try {
    renderNotes(await api(`/api/notes?${params}`));
  } catch (error) {
    notify(error.message);
    document.querySelector("#result-count").textContent = "Notes could not be loaded";
  } finally {
    grid.setAttribute("aria-busy", "false");
  }
}

async function loadDashboard() {
  try {
    const [stats, subjects] = await Promise.all([api("/api/stats"), api("/api/subjects")]);
    document.querySelector("#note-count").textContent = stats.note_count;
    document.querySelector("#subject-count").textContent = stats.subject_count;
    document.querySelector("#learning-score").textContent = stats.learning_score;
    document.querySelector("#sidebar-note-count").textContent = stats.note_count;
    document.querySelector("#score-engine").textContent = stats.score_engine === "c" ? "Calculated by the C knowledge engine" : "Python fallback · compile C engine for native scoring";
    const selected = subjectFilter.value;
    subjectFilter.replaceChildren(new Option("All subjects", ""));
    for (const subject of subjects) subjectFilter.add(new Option(subject, subject));
    if (subjects.includes(selected)) subjectFilter.value = selected;
    await loadNotes();
  } catch (error) {
    notify(error.message);
  }
}

function openDialog(note = null) {
  editingId = note?.id ?? null;
  document.querySelector("#dialog-title").textContent = note ? "Edit your thought" : "Capture a thought";
  document.querySelector("#note-title").value = note?.title ?? "";
  document.querySelector("#note-subject").value = note?.subject ?? "General";
  document.querySelector("#note-tags").value = note?.tags.join(", ") ?? "";
  document.querySelector("#note-content").value = note?.content ?? "";
  document.querySelector("#save-note").firstChild.textContent = note ? "Update note " : "Save note ";
  dialog.showModal();
  document.querySelector("#note-title").focus();
}

async function removeNote(note) {
  if (!window.confirm(`Delete “${note.title}”? This cannot be undone.`)) return;
  try {
    await api(`/api/notes/${note.id}`, { method: "DELETE" });
    notify("Note removed from your vault.");
    await loadDashboard();
  } catch (error) {
    notify(error.message);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = new FormData(form);
  const note = {
    title: values.get("title"), subject: values.get("subject"), content: values.get("content"),
    tags: values.get("tags").split(",").map((tag) => tag.trim()).filter(Boolean),
  };
  const button = document.querySelector("#save-note");
  button.disabled = true;
  try {
    await api(editingId ? `/api/notes/${editingId}` : "/api/notes", {
      method: editingId ? "PUT" : "POST", body: JSON.stringify(note),
    });
    dialog.close();
    notify(editingId ? "Your note has been updated." : "Thought captured in your vault.");
    await loadDashboard();
  } catch (error) {
    notify(error.message);
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#create-note").addEventListener("click", () => openDialog());
document.querySelector("#empty-create").addEventListener("click", () => openDialog());
document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
document.querySelector("#cancel-dialog").addEventListener("click", () => dialog.close());
subjectFilter.addEventListener("change", loadNotes);
document.querySelector("#clear-filters").addEventListener("click", () => { search.value = ""; subjectFilter.value = ""; loadNotes(); });
search.addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadNotes, 220); });
document.querySelector("#notification-button").addEventListener("click", () => notify("You’re all caught up."));
document.querySelector("#menu-toggle").addEventListener("click", (event) => {
  const open = document.querySelector("#sidebar").classList.toggle("open");
  event.currentTarget.setAttribute("aria-expanded", String(open));
});
document.querySelectorAll("[data-section]").forEach((button) => button.addEventListener("click", () => {
  const section = button.dataset.section;
  if (!["home", "notes"].includes(section)) { notify(`${button.textContent.trim()} is planned for a later milestone.`); return; }
  document.querySelectorAll("[data-section]").forEach((item) => item.classList.toggle("active", item === button));
  document.querySelector("#current-section").textContent = section === "notes" ? "MY NOTES" : "OVERVIEW";
  document.querySelector("#sidebar").classList.remove("open");
  document.querySelector("#menu-toggle").setAttribute("aria-expanded", "false");
  if (section === "notes") document.querySelector("#notes-heading").scrollIntoView({ behavior: "smooth" });
  else window.scrollTo({ top: 0, behavior: "smooth" });
}));
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); search.focus(); }
});
document.querySelector("#today-label").textContent = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" }).format(new Date()).toUpperCase();

function startStarfield() {
  const canvas = document.querySelector("#starfield");
  const context = canvas.getContext("2d");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let stars = [];
  let width = 0;
  let height = 0;
  let frame = 0;
  function draw() {
    context.clearRect(0, 0, width, height);
    for (const star of stars) {
      context.fillStyle = `rgba(157, 210, 255, ${star.alpha})`;
      context.beginPath();
      context.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
      context.fill();
      if (!reduceMotion.matches) { star.y += 0.04; star.x += star.drift; if (star.y > height) star.y = 0; }
    }
    if (!reduceMotion.matches) frame = requestAnimationFrame(draw);
  }
  function resize() {
    const ratio = Math.min(devicePixelRatio || 1, 1.5);
    width = innerWidth; height = innerHeight;
    canvas.width = Math.floor(width * ratio); canvas.height = Math.floor(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    stars = Array.from({ length: Math.min(65, Math.floor(width * height / 18000)) }, () => ({
      x: Math.random() * width, y: Math.random() * height, radius: Math.random() * 1.1 + 0.2,
      alpha: Math.random() * 0.35 + 0.12, drift: (Math.random() - 0.5) * 0.07,
    }));
    draw();
  }
  addEventListener("resize", resize, { passive: true });
  reduceMotion.addEventListener("change", () => { cancelAnimationFrame(frame); draw(); });
  resize();
}

loadDashboard();
startStarfield();
