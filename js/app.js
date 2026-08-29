// StockFlow front-end — vanilla JS
// Talks to the Flask JSON API in app.py via the helpers in api.js.

let currentUser = null;
let categoriesCache = [];
let productsCache = [];

const money = (n) => `£${Number(n).toFixed(2)}`;
const dt = (iso) => {
  const d = new Date(iso.replace(" ", "T"));
  return d.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
};

function showToast(message, type = "success") {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = `toast ${type}`;
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => el.classList.add("hidden"), 3200);
}

// ------------------------------------------------------------- auth/boot --

async function boot() {
  try {
    const { user } = await api.get("/api/me");
    currentUser = user;
    enterApp();
  } catch (e) {
    showLogin();
  }
}

function showLogin() {
  document.getElementById("loginScreen").classList.remove("hidden");
  document.getElementById("appShell").classList.add("hidden");
}

function enterApp() {
  document.getElementById("loginScreen").classList.add("hidden");
  document.getElementById("appShell").classList.remove("hidden");
  document.getElementById("sidebarUserName").textContent = currentUser.full_name;
  document.getElementById("sidebarUserRole").textContent = currentUser.role.replace("_", " ");

  const isManager = currentUser.role === "manager";
  document.querySelectorAll(".manager-only").forEach((el) => {
    el.classList.toggle("hidden", !isManager);
  });

  switchView("dashboard");
}

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const errorEl = document.getElementById("loginError");
  errorEl.textContent = "";
  try {
    const { user } = await api.post("/api/login", { username, password });
    currentUser = user;
    document.getElementById("loginForm").reset();
    enterApp();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  await api.post("/api/logout");
  currentUser = null;
  showLogin();
});

// ------------------------------------------------------------ navigation --

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

function switchView(view) {
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("hidden", v.id !== `view-${view}`));

  if (view === "dashboard") loadDashboard();
  if (view === "products") loadProducts();
  if (view === "stock") loadStockView();
  if (view === "reports") loadReports();
  if (view === "users") loadUsers();
}

// ------------------------------------------------------------- dashboard --

async function loadDashboard() {
  const data = await api.get("/api/dashboard");
  document.getElementById("statProductCount").textContent = data.product_count;
  document.getElementById("statStockValue").textContent = money(data.stock_value);
  document.getElementById("statTotalUnits").textContent = data.total_units;
  document.getElementById("statLowStock").textContent = data.low_stock.length;

  const lowStockEl = document.getElementById("lowStockList");
  lowStockEl.innerHTML = data.low_stock.length
    ? data.low_stock.map((p) => `
        <div class="list-row">
          <div><div class="lr-main">${escapeHtml(p.name)}</div><div class="lr-sub">${escapeHtml(p.sku)}</div></div>
          <span class="badge badge-red">${p.current_stock} left</span>
        </div>`).join("")
    : `<div class="list-empty">Nothing low on stock right now.</div>`;

  const recentEl = document.getElementById("recentActivityList");
  recentEl.innerHTML = data.recent_activity.length
    ? data.recent_activity.map((m) => `
        <div class="list-row">
          <div><div class="lr-main">${escapeHtml(m.product_name)}</div><div class="lr-sub">${escapeHtml(m.user_name)} · ${dt(m.created_at)}</div></div>
          <span class="badge ${m.movement_type === 'IN' ? 'badge-green' : 'badge-blue'}">${m.movement_type} ${m.quantity}</span>
        </div>`).join("")
    : `<div class="list-empty">No stock movements logged yet.</div>`;
}

// -------------------------------------------------------------- products --

async function loadProducts() {
  const [{ products }, { categories }] = await Promise.all([
    api.get("/api/products"),
    api.get("/api/categories"),
  ]);
  productsCache = products;
  categoriesCache = categories;

  const tbody = document.querySelector("#productsTable tbody");
  const isManager = currentUser.role === "manager";
  tbody.innerHTML = products.map((p) => `
    <tr class="${p.low_stock ? 'row-low' : ''}">
      <td>${escapeHtml(p.sku)}</td>
      <td>${escapeHtml(p.name)}</td>
      <td>${escapeHtml(p.category_name)}</td>
      <td>${money(p.price)}</td>
      <td>${p.current_stock}${p.low_stock ? ' <span class="badge badge-red">low</span>' : ''}</td>
      <td>${p.reorder_threshold}</td>
      ${isManager ? `<td class="actions">
        <button class="icon-btn" title="Edit" onclick="openProductModal(${p.id})"><i class="fa-solid fa-pen"></i></button>
        <button class="icon-btn" title="Delete" onclick="deleteProduct(${p.id}, '${escapeHtml(p.name).replace(/'/g, "\\'")}')"><i class="fa-solid fa-trash"></i></button>
      </td>` : ''}
    </tr>`).join("");
}

document.getElementById("addProductBtn").addEventListener("click", () => openProductModal(null));

function openProductModal(productId) {
  const editing = productId !== null;
  const product = editing ? productsCache.find((p) => p.id === productId) : null;
  const categoryOptions = categoriesCache.map((c) =>
    `<option value="${c.id}" ${product && product.category_id === c.id ? "selected" : ""}>${escapeHtml(c.name)}</option>`
  ).join("");

  showModal(`
    <h2>${editing ? "Edit Product" : "Add Product"}</h2>
    <form id="productForm">
      <label for="pSku">SKU</label>
      <input id="pSku" value="${product ? escapeHtml(product.sku) : ''}" required>
      <label for="pName">Name</label>
      <input id="pName" value="${product ? escapeHtml(product.name) : ''}" required>
      <label for="pCategory">Category</label>
      <select id="pCategory" required>${categoryOptions}</select>
      <label for="pPrice">Price (£)</label>
      <input id="pPrice" type="number" step="0.01" min="0" value="${product ? product.price : ''}" required>
      <label for="pStock">Current Stock ${editing ? '<span style="font-weight:400;color:var(--gray-light)">(use Log Stock to change this)</span>' : ''}</label>
      <input id="pStock" type="number" min="0" value="${product ? product.current_stock : 0}" ${editing ? "disabled" : ""}>
      <label for="pThreshold">Reorder Threshold</label>
      <input id="pThreshold" type="number" min="0" value="${product ? product.reorder_threshold : 5}" required>
      <p class="form-error" id="productError"></p>
      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">${editing ? "Save Changes" : "Add Product"}</button>
      </div>
    </form>
  `);

  document.getElementById("productForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById("productError");
    const payload = {
      sku: document.getElementById("pSku").value.trim(),
      name: document.getElementById("pName").value.trim(),
      category_id: Number(document.getElementById("pCategory").value),
      price: Number(document.getElementById("pPrice").value),
      reorder_threshold: Number(document.getElementById("pThreshold").value),
    };
    if (!editing) payload.current_stock = Number(document.getElementById("pStock").value);

    try {
      if (editing) {
        await api.put(`/api/products/${productId}`, payload);
        showToast("Product updated.");
      } else {
        await api.post("/api/products", payload);
        showToast("Product added.");
      }
      closeModal();
      loadProducts();
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });
}

async function deleteProduct(id, name) {
  if (!confirm(`Delete "${name}"? This also removes its stock movement history.`)) return;
  try {
    await api.del(`/api/products/${id}`);
    showToast("Product deleted.");
    loadProducts();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ---------------------------------------------------------- log stock ---

async function loadStockView() {
  const [{ products }, { movements }] = await Promise.all([
    api.get("/api/products"),
    api.get("/api/stock-movements?limit=30"),
  ]);
  productsCache = products;

  const select = document.getElementById("stockProduct");
  select.innerHTML = products.map((p) => `<option value="${p.id}">${escapeHtml(p.name)} (${escapeHtml(p.sku)}) — ${p.current_stock} in stock</option>`).join("");

  const tbody = document.querySelector("#movementsTable tbody");
  tbody.innerHTML = movements.length
    ? movements.map((m) => `
        <tr>
          <td>${dt(m.created_at)}</td>
          <td>${escapeHtml(m.product_name)}</td>
          <td><span class="badge ${m.movement_type === 'IN' ? 'badge-green' : 'badge-blue'}">${m.movement_type}</span></td>
          <td>${m.quantity}</td>
          <td>${escapeHtml(m.reason)}</td>
          <td>${escapeHtml(m.user_name)}</td>
          <td>${m.note ? escapeHtml(m.note) : '—'}</td>
        </tr>`).join("")
    : `<tr><td colspan="7" class="list-empty">No stock movements logged yet.</td></tr>`;
}

document.getElementById("stockForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("stockError");
  errorEl.textContent = "";
  const payload = {
    product_id: Number(document.getElementById("stockProduct").value),
    movement_type: document.querySelector('input[name="movement_type"]:checked').value,
    quantity: Number(document.getElementById("stockQuantity").value),
    reason: document.getElementById("stockReason").value,
    note: document.getElementById("stockNote").value.trim(),
  };
  try {
    await api.post("/api/stock-movements", payload);
    showToast("Stock movement logged.");
    document.getElementById("stockForm").reset();
    loadStockView();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

// ------------------------------------------------------------- reports --

async function loadReports() {
  const { top_products } = await api.get("/api/reports/top-products?limit=10");
  const tbody = document.querySelector("#topProductsTable tbody");
  tbody.innerHTML = top_products.length
    ? top_products.map((p, i) => `
        <tr>
          <td>${i + 1}</td>
          <td>${escapeHtml(p.name)}</td>
          <td>${escapeHtml(p.sku)}</td>
          <td>${p.units_sold}</td>
          <td>${money(p.revenue)}</td>
        </tr>`).join("")
    : `<tr><td colspan="5" class="list-empty">No sales logged yet — log some "Stock Out / Sale" movements to see this fill in.</td></tr>`;
}

// --------------------------------------------------------------- staff --

async function loadUsers() {
  const { users } = await api.get("/api/users");
  const tbody = document.querySelector("#usersTable tbody");
  tbody.innerHTML = users.map((u) => `
    <tr>
      <td>${escapeHtml(u.full_name)}</td>
      <td>${escapeHtml(u.username)}</td>
      <td><span class="badge ${u.role === 'manager' ? 'badge-blue' : 'badge-gray'}">${u.role.replace('_', ' ')}</span></td>
      <td>${dt(u.created_at)}</td>
    </tr>`).join("");
}

document.getElementById("addUserBtn").addEventListener("click", () => {
  showModal(`
    <h2>Add Staff Account</h2>
    <form id="userForm">
      <label for="uFullName">Full Name</label>
      <input id="uFullName" required>
      <label for="uUsername">Username</label>
      <input id="uUsername" required>
      <label for="uPassword">Password</label>
      <input id="uPassword" type="password" minlength="8" required>
      <label for="uRole">Role</label>
      <select id="uRole" required>
        <option value="sales_assistant">Sales Assistant</option>
        <option value="manager">Manager</option>
      </select>
      <p class="form-error" id="userError"></p>
      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Add Account</button>
      </div>
    </form>
  `);

  document.getElementById("userForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById("userError");
    const payload = {
      full_name: document.getElementById("uFullName").value.trim(),
      username: document.getElementById("uUsername").value.trim(),
      password: document.getElementById("uPassword").value,
      role: document.getElementById("uRole").value,
    };
    try {
      await api.post("/api/users", payload);
      showToast("Staff account created.");
      closeModal();
      loadUsers();
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });
});

// --------------------------------------------------------------- modal --

function showModal(html) {
  document.getElementById("modalBox").innerHTML = html;
  document.getElementById("modalOverlay").classList.remove("hidden");
}
function closeModal() {
  document.getElementById("modalOverlay").classList.add("hidden");
  document.getElementById("modalBox").innerHTML = "";
}
document.getElementById("modalOverlay").addEventListener("click", (e) => {
  if (e.target.id === "modalOverlay") closeModal();
});

// --------------------------------------------------------------- utils --

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

boot();
