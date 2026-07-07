const API = "";
let token = localStorage.getItem("devtrack_token");
let currentUser = null;
let developers = [];
let selectedDevId = null;
let sortable = null;

const STATUS_LABELS = {
  backlog: "Backlog", todo: "To Do", in_progress: "In Progress",
  testing: "Testing/QA", completed: "Completed"
};

// ── Auth ──────────────────────────────────────────
async function login(email, password) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  if (!res.ok) throw new Error("Invalid credentials");
  const data = await res.json();
  token = data.access_token;
  localStorage.setItem("devtrack_token", token);
  return data;
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401) { logout(); throw new Error("Session expired"); }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

function logout() {
  token = null;
  localStorage.removeItem("devtrack_token");
  document.getElementById("login-screen").classList.remove("hidden");
  document.getElementById("app-shell").classList.add("hidden");
}

function showToast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

function badge(cls, text) {
  return `<span class="badge badge-${cls}">${text}</span>`;
}

let editingUserId = null;

const PAGE_TITLES = {
  dashboard: "Department Dashboard",
  planner: "Queue Planner",
  holidays: "Holiday Calendar",
  reports: "Reports & Notifications",
  tasks: "My Tasks",
  users: "User Management",
  leaves: "Developer Leaves",
  profile: "My Profile",
};

// ── Navigation ────────────────────────────────────
function showPage(page) {
  document.querySelectorAll(".page").forEach(p => p.classList.add("hidden"));
  document.getElementById(`page-${page}`).classList.remove("hidden");
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  document.querySelector(`[data-page="${page}"]`)?.classList.add("active");
  document.getElementById("page-title").textContent = PAGE_TITLES[page] || page;

  if (page === "dashboard") loadDashboard();
  if (page === "planner") loadPlanner();
  if (page === "holidays") loadHolidays();
  if (page === "reports") loadReports();
  if (page === "tasks") loadMyTasks();
  if (page === "users") loadUsers();
  if (page === "leaves") loadLeaves();
  if (page === "profile") loadProfile();
}

function setupNav() {
  const isManager = currentUser?.role === "manager";
  const isDev = currentUser?.role === "developer";
  const isExec = currentUser?.role === "executive";
  document.getElementById("nav-planner").classList.toggle("hidden", !isManager);
  document.getElementById("nav-holidays").classList.toggle("hidden", !isManager);
  document.getElementById("nav-users").classList.toggle("hidden", !isManager);
  document.getElementById("nav-leaves").classList.toggle("hidden", !isManager);
  document.getElementById("nav-reports-admin").classList.toggle("hidden", !(isManager || isExec));
  document.getElementById("nav-tasks").classList.toggle("hidden", !isDev);
  document.getElementById("nav-profile").classList.toggle("hidden", false);
}

// ── Dashboard ───────────────────────────────────
async function loadDashboard() {
  const data = await api("/api/tasks/dashboard/developers");
  const grid = document.getElementById("dev-grid");
  grid.innerHTML = data.map(dev => {
    const leaveBadge = dev.on_leave ? `<span class="warning-flag orange">ON LEAVE</span>` : "";
    const flag = dev.bottleneck_level === "red"
      ? `<span class="warning-flag red">BOTTLENECK</span>`
      : dev.bottleneck_level === "orange"
      ? `<span class="warning-flag orange">HIGH LOAD</span>` : "";
    const active = dev.active_task
      ? `<div class="active-task">
           <strong>${dev.active_task.title}</strong><br>
           ${badge(dev.active_task.status, STATUS_LABELS[dev.active_task.status])}
           ECD: ${dev.active_task.estimated_completion_date || "—"}
         </div>` : `<div class="active-task" style="color:var(--muted)">No active task</div>`;
    return `<div class="dev-card bottleneck-${dev.bottleneck_level}">
      ${leaveBadge}${flag}
      <h3>${dev.name}</h3>
      <div class="stat-row">
        <div class="stat"><div class="label">Remaining</div><div class="value">${dev.remaining_hours}h</div></div>
        <div class="stat"><div class="label">Clear Date</div><div class="value">${dev.clear_date || "—"}</div></div>
        <div class="stat"><div class="label">Tasks</div><div class="value">${dev.tasks.length}</div></div>
      </div>
      ${active}
    </div>`;
  }).join("");
}

// ── Queue Planner ───────────────────────────────
async function loadPlanner() {
  developers = await api("/api/developers");
  const list = document.getElementById("dev-list");
  list.innerHTML = developers.map(d =>
    `<button class="${d.id === selectedDevId ? 'active' : ''}" onclick="selectDeveloper(${d.id})">${d.name}</button>`
  ).join("");
  if (!selectedDevId && developers.length) selectDeveloper(developers[0].id);
  else if (selectedDevId) renderQueue(selectedDevId);
}

async function selectDeveloper(id) {
  selectedDevId = id;
  document.querySelectorAll("#dev-list button").forEach((b, i) => {
    b.classList.toggle("active", developers[i]?.id === id);
  });
  await renderQueue(id);
}

async function renderQueue(devId) {
  const tasks = await api(`/api/tasks?assignee_id=${devId}`);
  const container = document.getElementById("task-queue");
  container.innerHTML = tasks.map(t => `
    <div class="task-item" data-id="${t.id}">
      <div>
        <strong>#${t.queue_order} ${t.title}</strong>
        <div class="task-meta">
          ${badge(t.priority_weight, t.priority_weight)}
          ${badge(t.status, STATUS_LABELS[t.status])}
          ${t.effort_hours}h · Start: ${t.start_date || "—"} · ECD: ${t.estimated_completion_date || "—"}
        </div>
      </div>
      <button class="btn btn-sm btn-secondary" onclick="editTask(${t.id})">Edit</button>
      ${currentUser?.role === "manager" ? `<button class="btn btn-sm btn-danger" onclick="deleteTask(${t.id}, '${t.title.replace(/'/g, "\\'")}')">Delete</button>` : ""}
    </div>
  `).join("") || `<p style="color:var(--muted)">No tasks in queue.</p>`;

  if (sortable) sortable.destroy();
  if (currentUser?.role === "manager" && tasks.length) {
    sortable = Sortable.create(container, {
      animation: 150,
      ghostClass: "sortable-ghost",
      chosenClass: "sortable-chosen",
      onEnd: async () => {
        const items = [...container.querySelectorAll(".task-item")].map((el, i) => ({
          task_id: parseInt(el.dataset.id),
          queue_order: i + 1,
        }));
        await api("/api/tasks/reorder", {
          method: "POST",
          body: { assignee_id: devId, tasks: items },
        });
        showToast("Queue reordered — timelines recalculated");
        renderQueue(devId);
        loadDashboard();
      },
    });
  }
}

// ── My Tasks (Developer) ────────────────────────
async function loadMyTasks() {
  const tasks = await api("/api/tasks");
  document.getElementById("my-tasks-table").innerHTML = `
    <table>
      <thead><tr><th>#</th><th>Task</th><th>Status</th><th>Est.</th><th>Actual</th><th>ECD</th><th></th></tr></thead>
      <tbody>${tasks.map(t => `<tr>
        <td>${t.queue_order}</td>
        <td>${t.title}</td>
        <td>${badge(t.status, STATUS_LABELS[t.status])}</td>
        <td>${t.effort_hours}h</td>
        <td>${t.actual_hours != null ? t.actual_hours + "h" : "—"}</td>
        <td>${t.estimated_completion_date || "—"}</td>
        <td><button class="btn btn-sm btn-secondary" onclick="editTask(${t.id})">Update</button></td>
      </tr>`).join("")}</tbody>
    </table>`;
}

// ── Holidays ────────────────────────────────────
async function loadHolidays() {
  const holidays = await api("/api/holidays");
  document.getElementById("holidays-table").innerHTML = `
    <table>
      <thead><tr><th>Date</th><th>Name</th><th></th></tr></thead>
      <tbody>${holidays.map(h => `<tr>
        <td>${h.date}</td><td>${h.name}</td>
        <td><button class="btn btn-sm btn-danger" onclick="deleteHoliday(${h.id})">Remove</button></td>
      </tr>`).join("")}</tbody>
    </table>`;
}

async function deleteHoliday(id) {
  if (!confirm("Remove this holiday? Timelines will be recalculated.")) return;
  await api(`/api/holidays/${id}`, { method: "DELETE" });
  showToast("Holiday removed");
  loadHolidays();
}

// ── Reports ─────────────────────────────────────
async function loadReports() {
  const isManager = currentUser?.role === "manager";
  document.getElementById("report-settings-form").classList.toggle("hidden", !isManager);
  document.getElementById("report-schedule-heading")?.classList.toggle("hidden", !isManager);
  document.getElementById("report-recipients-section")?.classList.toggle("hidden", !isManager);

  if (isManager) {
    const settings = await api("/api/reports/settings");
    document.getElementById("report-frequency").value = settings.frequency;
    await loadRecipients();
  }

  const notifications = isManager || currentUser?.role === "executive"
    ? await api("/api/notifications")
    : [];
  document.getElementById("notifications-table").innerHTML = notifications.length
    ? `<table><thead><tr><th>Time</th><th>Subject</th><th>Recipients</th></tr></thead>
       <tbody>${notifications.map(n => `<tr>
         <td>${new Date(n.created_at).toLocaleString()}</td>
         <td>${n.subject}</td>
         <td style="font-size:0.8rem">${n.recipients}</td>
       </tr>`).join("")}</tbody></table>`
    : `<p style="color:var(--muted)">No notifications yet. Alerts are logged when SMTP is disabled.</p>`;
}

async function loadRecipients() {
  const all = await api("/api/reports/recipients");
  const status = all.filter(r => r.recipient_type === "status_alert");
  const scheduled = all.filter(r => r.recipient_type === "scheduled_report");
  document.getElementById("status-recipients-list").innerHTML = renderRecipientList(status);
  document.getElementById("scheduled-recipients-list").innerHTML = renderRecipientList(scheduled);
}

function renderRecipientList(recipients) {
  if (!recipients.length) return `<p style="color:var(--muted);font-size:0.85rem">No recipients configured.</p>`;
  return `<table><thead><tr><th>Email</th><th>Name</th><th></th></tr></thead>
    <tbody>${recipients.map(r => `<tr>
      <td>${r.email}</td><td>${r.name || "—"}</td>
      <td><button class="btn btn-sm btn-danger" onclick="removeRecipient(${r.id})">Remove</button></td>
    </tr>`).join("")}</tbody></table>`;
}

async function removeRecipient(id) {
  if (!confirm("Remove this email recipient?")) return;
  await api(`/api/reports/recipients/${id}`, { method: "DELETE" });
  showToast("Recipient removed");
  loadRecipients();
}

// ── User Management ─────────────────────────────
async function loadUsers() {
  const users = await api("/api/users");
  document.getElementById("users-table").innerHTML = `
    <table>
      <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Phone</th><th>Department</th><th>Status</th><th></th></tr></thead>
      <tbody>${users.map(u => `<tr>
        <td>${u.name}</td>
        <td>${u.email}</td>
        <td>${badge(u.role, u.role)}</td>
        <td>${u.phone || "—"}</td>
        <td>${u.department || "—"}</td>
        <td>${u.is_active ? badge("completed", "Active") : badge("backlog", "Inactive")}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="editUser(${u.id})">Edit</button>
          ${u.id !== currentUser.id ? `<button class="btn btn-sm btn-danger" onclick="deleteUser(${u.id}, '${u.name.replace(/'/g, "\\'")}')">Delete</button>` : ""}
        </td>
      </tr>`).join("")}</tbody>
    </table>`;
}

function openUserModal() {
  editingUserId = null;
  document.getElementById("user-modal-title").textContent = "Add User";
  document.getElementById("user-form").reset();
  document.getElementById("user-password-group").classList.remove("hidden");
  document.getElementById("user-password-label").textContent = "Password";
  document.getElementById("user-password-input").required = true;
  document.getElementById("user-active-group").classList.add("hidden");
  document.getElementById("user-role-input").disabled = false;
  document.getElementById("user-email-input").disabled = false;
  document.getElementById("user-modal").classList.remove("hidden");
}

async function editUser(id) {
  const user = await api(`/api/users/${id}`);
  editingUserId = id;
  document.getElementById("user-modal-title").textContent = "Edit User";
  document.getElementById("user-name-input").value = user.name;
  document.getElementById("user-email-input").value = user.email;
  document.getElementById("user-role-input").value = user.role;
  document.getElementById("user-phone-input").value = user.phone || "";
  document.getElementById("user-department-input").value = user.department || "";
  document.getElementById("user-bio-input").value = user.bio || "";
  document.getElementById("user-password-input").value = "";
  document.getElementById("user-password-input").required = false;
  document.getElementById("user-password-label").textContent = "New Password (optional)";
  document.getElementById("user-active-group").classList.remove("hidden");
  document.getElementById("user-active-input").checked = user.is_active;
  document.getElementById("user-modal").classList.remove("hidden");
}

function closeUserModal() {
  document.getElementById("user-modal").classList.add("hidden");
  editingUserId = null;
}

async function saveUser(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById("user-name-input").value,
    email: document.getElementById("user-email-input").value,
    role: document.getElementById("user-role-input").value,
    phone: document.getElementById("user-phone-input").value || null,
    department: document.getElementById("user-department-input").value || null,
    bio: document.getElementById("user-bio-input").value || null,
  };
  const password = document.getElementById("user-password-input").value;
  if (password) payload.password = password;

  if (editingUserId) {
    payload.is_active = document.getElementById("user-active-input").checked;
    await api(`/api/users/${editingUserId}`, { method: "PATCH", body: payload });
    showToast("User updated");
  } else {
    if (!password) { showToast("Password is required for new users"); return; }
    await api("/api/users", { method: "POST", body: payload });
    showToast("User created — they can now log in with their email");
  }
  closeUserModal();
  loadUsers();
}

async function deleteUser(id, name) {
  if (!confirm(`Delete user "${name}"? This cannot be undone.`)) return;
  try {
    await api(`/api/users/${id}`, { method: "DELETE" });
    showToast("User deleted");
    loadUsers();
  } catch (err) {
    showToast(err.message);
  }
}

// ── Developer Leaves ────────────────────────────
async function loadLeaves() {
  const [leaves, devs] = await Promise.all([
    api("/api/leaves"),
    api("/api/developers"),
  ]);
  document.getElementById("leave-developer").innerHTML = devs.map(d =>
    `<option value="${d.id}">${d.name}</option>`
  ).join("");
  document.getElementById("leaves-table").innerHTML = leaves.length
    ? `<table><thead><tr><th>Developer</th><th>From</th><th>To</th><th>Reason</th><th></th></tr></thead>
       <tbody>${leaves.map(l => `<tr>
         <td>${l.user_name}</td>
         <td>${l.start_date}</td>
         <td>${l.end_date}</td>
         <td>${l.reason || "—"}</td>
         <td><button class="btn btn-sm btn-danger" onclick="deleteLeave(${l.id})">Remove</button></td>
       </tr>`).join("")}</tbody></table>`
    : `<p style="color:var(--muted)">No leaves recorded.</p>`;
}

async function deleteLeave(id) {
  if (!confirm("Remove this leave? Timelines will be recalculated.")) return;
  await api(`/api/leaves/${id}`, { method: "DELETE" });
  showToast("Leave removed — timelines updated");
  loadLeaves();
  loadDashboard();
}

// ── My Profile ──────────────────────────────────
async function loadProfile() {
  const user = await api("/api/users/me");
  document.getElementById("profile-name").value = user.name;
  document.getElementById("profile-email").value = user.email;
  document.getElementById("profile-phone").value = user.phone || "";
  document.getElementById("profile-department").value = user.department || "";
  document.getElementById("profile-bio").value = user.bio || "";
  document.getElementById("profile-password").value = "";
}

async function saveProfile(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById("profile-name").value,
    email: document.getElementById("profile-email").value,
    phone: document.getElementById("profile-phone").value || null,
    department: document.getElementById("profile-department").value || null,
    bio: document.getElementById("profile-bio").value || null,
  };
  const password = document.getElementById("profile-password").value;
  if (password) payload.password = password;
  const updated = await api("/api/users/me", { method: "PATCH", body: payload });
  currentUser = updated;
  document.getElementById("user-name").textContent = updated.name;
  showToast("Profile saved");
}

// ── Task Modal ──────────────────────────────────
let editingTaskId = null;

async function editTask(id) {
  const task = await api(`/api/tasks/${id}`);
  editingTaskId = id;
  const isManager = currentUser?.role === "manager";
  document.getElementById("modal-title").textContent = "Edit Task";
  document.getElementById("task-title").value = task.title;
  document.getElementById("task-description").value = task.description || "";
  document.getElementById("task-effort").value = task.effort_hours;
  document.getElementById("task-actual").value = task.actual_hours ?? "";
  document.getElementById("task-status").value = task.status;
  document.getElementById("task-priority").value = task.priority_weight;

  if (isManager) {
    const devs = await api("/api/developers");
    document.getElementById("task-assignee").innerHTML = devs.map(d =>
      `<option value="${d.id}" ${d.id === task.assignee_id ? "selected" : ""}>${d.name}</option>`
    ).join("");
    document.getElementById("task-assignee-group").classList.remove("hidden");
    document.getElementById("delete-task-btn").classList.remove("hidden");
  } else {
    document.getElementById("task-assignee-group").classList.add("hidden");
    document.getElementById("delete-task-btn").classList.add("hidden");
  }
  document.getElementById("task-modal").classList.remove("hidden");
}

async function openNewTaskModal() {
  editingTaskId = null;
  document.getElementById("modal-title").textContent = "New Task";
  document.getElementById("task-form").reset();
  document.getElementById("task-assignee-group").classList.remove("hidden");
  const devs = await api("/api/developers");
  document.getElementById("task-assignee").innerHTML = devs.map(d =>
    `<option value="${d.id}" ${d.id === selectedDevId ? "selected" : ""}>${d.name}</option>`
  ).join("");
  document.getElementById("task-modal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("task-modal").classList.add("hidden");
  document.getElementById("delete-task-btn").classList.add("hidden");
  editingTaskId = null;
}

async function deleteTask(id, title) {
  if (!confirm(`Delete task "${title}"? This will reschedule the developer's remaining queue.`)) return;
  await api(`/api/tasks/${id}`, { method: "DELETE" });
  showToast("Task deleted — timelines updated");
  if (selectedDevId) renderQueue(selectedDevId);
  loadDashboard();
}

async function deleteTaskFromModal() {
  if (!editingTaskId) return;
  const title = document.getElementById("task-title").value;
  await deleteTask(editingTaskId, title);
  closeModal();
}

async function saveTask(e) {
  e.preventDefault();
  const payload = {
    title: document.getElementById("task-title").value,
    description: document.getElementById("task-description").value,
    effort_hours: parseFloat(document.getElementById("task-effort").value),
    status: document.getElementById("task-status").value,
    priority_weight: document.getElementById("task-priority").value,
  };
  const actual = document.getElementById("task-actual").value;
  if (actual !== "") payload.actual_hours = parseFloat(actual);

  if (editingTaskId) {
    if (currentUser?.role === "manager") {
      payload.assignee_id = parseInt(document.getElementById("task-assignee").value);
    }
    await api(`/api/tasks/${editingTaskId}`, { method: "PATCH", body: payload });
    showToast("Task updated — timelines recalculated");
  } else {
    payload.assignee_id = parseInt(document.getElementById("task-assignee").value);
    await api("/api/tasks", { method: "POST", body: payload });
    showToast("Task created — stakeholders notified");
  }
  closeModal();
  if (selectedDevId) renderQueue(selectedDevId);
  loadDashboard();
  if (currentUser?.role === "developer") loadMyTasks();
}

// ── Init ────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("login-form").addEventListener("submit", async e => {
    e.preventDefault();
    try {
      await login(
        document.getElementById("email").value,
        document.getElementById("password").value
      );
      currentUser = await api("/api/auth/me");
      document.getElementById("login-screen").classList.add("hidden");
      document.getElementById("app-shell").classList.remove("hidden");
      document.getElementById("user-name").textContent = currentUser.name;
      document.getElementById("user-role").textContent = currentUser.role;
      setupNav();
      showPage("dashboard");
    } catch (err) {
      showToast(err.message);
    }
  });

  document.getElementById("logout-btn").addEventListener("click", logout);
  document.querySelectorAll(".nav-item").forEach(n =>
    n.addEventListener("click", () => showPage(n.dataset.page))
  );
  document.getElementById("task-form").addEventListener("submit", saveTask);
  document.getElementById("delete-task-btn")?.addEventListener("click", deleteTaskFromModal);
  document.getElementById("add-task-btn")?.addEventListener("click", openNewTaskModal);
  document.getElementById("add-user-btn")?.addEventListener("click", openUserModal);
  document.getElementById("user-form")?.addEventListener("submit", saveUser);
  document.getElementById("profile-form")?.addEventListener("submit", saveProfile);

  document.getElementById("leave-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    await api("/api/leaves", {
      method: "POST",
      body: {
        user_id: parseInt(document.getElementById("leave-developer").value),
        start_date: document.getElementById("leave-start").value,
        end_date: document.getElementById("leave-end").value,
        reason: document.getElementById("leave-reason").value || null,
        notes: document.getElementById("leave-notes").value || null,
      },
    });
    e.target.reset();
    showToast("Leave added — developer timelines pushed forward");
    loadLeaves();
    loadDashboard();
  });

  document.getElementById("status-recipient-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    await api("/api/reports/recipients", {
      method: "POST",
      body: {
        email: document.getElementById("status-recipient-email").value,
        name: document.getElementById("status-recipient-name").value || null,
        recipient_type: "status_alert",
      },
    });
    e.target.reset();
    showToast("Status alert recipient added");
    loadRecipients();
  });

  document.getElementById("scheduled-recipient-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    await api("/api/reports/recipients", {
      method: "POST",
      body: {
        email: document.getElementById("scheduled-recipient-email").value,
        name: document.getElementById("scheduled-recipient-name").value || null,
        recipient_type: "scheduled_report",
      },
    });
    e.target.reset();
    showToast("Scheduled report recipient added");
    loadRecipients();
  });

  document.getElementById("holiday-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    await api("/api/holidays", {
      method: "POST",
      body: {
        name: document.getElementById("holiday-name").value,
        date: document.getElementById("holiday-date").value,
      },
    });
    e.target.reset();
    showToast("Holiday added — timelines recalculated");
    loadHolidays();
  });

  document.getElementById("report-settings-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    await api("/api/reports/settings", {
      method: "PUT",
      body: { frequency: document.getElementById("report-frequency").value },
    });
    showToast("Report schedule updated");
  });

  document.getElementById("download-pdf")?.addEventListener("click", async () => {
    const res = await api("/api/reports/pdf");
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "devtrack-report.pdf";
    a.click();
  });

  if (token) {
    try {
      currentUser = await api("/api/auth/me");
      document.getElementById("login-screen").classList.add("hidden");
      document.getElementById("app-shell").classList.remove("hidden");
      document.getElementById("user-name").textContent = currentUser.name;
      document.getElementById("user-role").textContent = currentUser.role;
      setupNav();
      showPage("dashboard");
    } catch {
      logout();
    }
  }
});
