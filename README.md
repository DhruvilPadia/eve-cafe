# 🍃 Eve Café — Full-Stack Ordering App

A production-ready full-stack café ordering system with a polished mobile-first frontend, a real REST API backend, and a persistent SQLite database.

---

## ⚡ Quick Start

```bash
# 1. Clone / unzip the project
cd eve-cafe

# 2. Install Flask (only dependency)
pip install flask

# 3. Run
./start.sh          # macOS / Linux
python3 server.py   # Windows / direct

# 4. Open in browser
#    Customer:  http://localhost:5000/
#    Admin:     http://localhost:5000/  → tap 🔐 Staff
```

**Admin credentials** — `AD.com` / `thisisbusiness`

---

## 🗂 Project Structure

```
eve-cafe/
├── server.py            ← Flask REST API + SQLite backend
├── templates/
│   └── index.html       ← Full-stack frontend (single file, ~1 100 lines)
├── static/              ← Reserved for assets (currently empty)
├── eve_cafe.db          ← SQLite database (auto-created on first run)
├── start.sh             ← Startup script with health checks
├── package.json         ← Metadata (no Node.js deps required)
└── README.md
```

---

## 🏗 Architecture

```
Browser (index.html)
     │
     │  fetch() REST calls
     ▼
Flask Server (server.py)  ←→  SQLite (eve_cafe.db)
     │
     ├─ /api/menu          GET   → categories + items
     ├─ /api/tables        GET   → table availability
     ├─ /api/orders        POST  → place order
     ├─ /api/orders        GET   → list all orders (admin)
     ├─ /api/orders/:id    GET   → order detail + stage log
     ├─ /api/orders/:id/stage  PATCH → advance order stage
     ├─ /api/auth/login    POST  → admin authentication
     ├─ /api/analytics     GET   → dashboard stats
     └─ /api/health        GET   → health check
```

**No Node.js, no npm, no external frontend frameworks needed.**  
The entire frontend runs from a single HTML file served by Flask.

---

## 📦 Database Schema

### `categories`
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | e.g. `bestseller`, `pizza` |
| name | TEXT | Display name |
| emoji | TEXT | Category icon |
| img_url | TEXT | Hero image URL |
| sort_order | INTEGER | Display order |

### `items`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Item ID |
| category_id | TEXT FK | References categories |
| name | TEXT | Item name |
| price | INTEGER | Price in INR paise/rupees |
| emoji | TEXT | Item icon |
| description | TEXT | Full description |
| tags | TEXT | JSON array: `["suggested","chef"]` |
| img_url | TEXT | Item image |
| is_available | INTEGER | 0=off, 1=on |

### `tables`
| Column | Type | Notes |
|---|---|---|
| number | INTEGER PK | 1–12 |
| status | TEXT | `free` or `occupied` |
| seats | INTEGER | Seat count |

### `orders`
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | Format: `EVE-2401` |
| table_num | INTEGER | Table number |
| party_size | INTEGER | Number of guests |
| items_json | TEXT | Full cart snapshot as JSON |
| subtotal | INTEGER | Before tax |
| tax | INTEGER | 5% GST |
| total | INTEGER | Final amount |
| stage | INTEGER | 0–4 (see below) |
| notes | TEXT | Special instructions |
| chips | TEXT | JSON array of chip selections |
| created_at | TEXT | ISO 8601 UTC |
| updated_at | TEXT | ISO 8601 UTC |

### `order_stage_log`
Immutable audit trail — every stage transition is recorded with a timestamp.

### Order Stages
| Stage | Name | Description |
|---|---|---|
| 0 | Confirmed | Order received |
| 1 | Preparing | Kitchen is cooking |
| 2 | Ready | Ready to serve |
| 3 | Served | Delivered to table |
| 4 | Done | Completed, table freed |

---

## 📡 REST API Reference

### Health
```
GET /api/health
→ { status: "ok", db: "...", time: "..." }
```

### Menu
```
GET /api/menu
→ { categories: [...], total_items: 37 }

GET /api/menu/:category_id
→ { id, name, items: [...] }

GET /api/menu/item/:item_id
→ { id, name, price, tags, ... }

PATCH /api/menu/item/:item_id/availability
→ { id, is_available: true/false }
```

### Tables
```
GET /api/tables
→ { tables: [{ number, status, seats }, ...] }

POST /api/tables/:num/reserve
→ { table: 3, status: "occupied" }

POST /api/tables/:num/free
→ { table: 3, status: "free" }
```

### Orders
```
POST /api/orders
Body: { table_num, party_size, items: [{id, qty}], notes, chips }
→ 201 { order_id, total, subtotal, tax, items, stage, created_at }

GET /api/orders?stage=0&table=3
→ { orders: [...], count: N }

GET /api/orders/:id
→ { ...order, stage_log: [{stage, changed_at}] }

PATCH /api/orders/:id/stage
→ { order_id, stage, stage_name }
```

### Auth
```
POST /api/auth/login
Body: { username, password }
→ { success: true, username, token }

POST /api/auth/logout
→ { success: true }
```

### Analytics
```
GET /api/analytics
→ {
    total_orders, total_revenue, live_orders,
    occupied_tables, avg_order_value,
    top_items: [{ name, count }],
    stage_breakdown: { Confirmed, Preparing, Ready, Served, Done }
  }
```

---

## 🎨 Customer Flow

```
Entry Screen
    → Party size selector
        → Table selection (live occupancy from API)
            → Menu categories
                → Item grid (filter by Suggested / Chef Special)
                    → Item detail (add to cart)
                        → Cart / Final order review
                            → Customize (chips + notes)
                                → Place order (POST /api/orders)
                                    → Thank You screen (animated)
```

## 🔐 Admin Flow

```
Staff button (bottom-right) → Admin login
    → Dashboard
        ├── Live Orders (auto-refreshes every 8s)
        │       → Advance stage button (PATCH /api/orders/:id/stage)
        ├── Analytics (revenue, top items, stage breakdown)
        └── Tables (live status + free button)
```

---

## 🌱 Seeded Data

- **12 categories**: Best Seller, Soups, Breakfast, Salads, Breads, Nibbles, Small Plates, Sushi, Pizza, Large Plates, Desserts, Chef Special
- **37 menu items** with descriptions, prices, tags, and Unsplash images
- **12 tables** (all free on first run)
- **1 admin account**: `AD.com` / `thisisbusiness`

---

## 🛠 Customization

**Add menu items**: Insert rows into `items` table in `eve_cafe.db` (or extend `SEED_ITEMS` in `server.py`).

**Change admin password**: Update the `admins` table:
```sql
UPDATE admins SET password='yournewpassword' WHERE username='AD.com';
```

**Change port**:
```bash
./start.sh 8080
# or
PORT=8080 python3 server.py
```

**Reset database** (reseed everything):
```bash
rm eve_cafe.db && python3 server.py
```

---

## 🔧 Requirements

- Python 3.8+
- Flask 2.0+ (`pip install flask`)
- No other dependencies

---

## 📱 Features

| Feature | Status |
|---|---|
| Mobile-first responsive UI | ✅ |
| Real-time table availability | ✅ |
| Full menu from database | ✅ |
| Cart with qty management | ✅ |
| Order placement via API | ✅ |
| GST calculation (5%) | ✅ |
| Admin login | ✅ |
| Live order dashboard | ✅ |
| Stage progression with audit log | ✅ |
| Analytics (revenue, top items) | ✅ |
| Table management | ✅ |
| Item availability toggle | ✅ |
| Auto table free on order done | ✅ |
| Toast notifications | ✅ |
| Loading skeletons | ✅ |
| Animated thank-you screen | ✅ |
