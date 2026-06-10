"""
Eve Café – Backend Server
Flask + SQLite | REST API

Endpoints:
  GET  /api/menu                     → all categories + items
  GET  /api/menu/<category_id>       → items in one category
  GET  /api/tables                   → all tables with status
  POST /api/tables/<n>/reserve       → mark table as occupied
  POST /api/tables/<n>/free          → mark table as free

  POST /api/orders                   → place new order
  GET  /api/orders                   → all orders (admin)
  GET  /api/orders/<order_id>        → single order detail
  PATCH /api/orders/<order_id>/stage → advance order stage

  POST /api/auth/login               → admin login
  POST /api/auth/logout              → admin logout

  GET  /api/analytics                → dashboard stats
  GET  /api/health                   → health check
"""

import sqlite3, json, uuid, os
from datetime import datetime, timezone
from flask import Flask, jsonify, request, g, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'eve-cafe-secret-2024'

DB_PATH = os.path.join(os.path.dirname(__file__), 'eve_cafe.db')

# ─────────────────────────────────────────
# CORS MIDDLEWARE (manual)
# ─────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PATCH,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return jsonify({}), 200

# ─────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop('db', None)
    if db: db.close()

def db():
    return get_db()

# ─────────────────────────────────────────
# SCHEMA + SEED
# ─────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    emoji       TEXT,
    img_url     TEXT,
    sort_order  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY,
    category_id TEXT REFERENCES categories(id),
    name        TEXT NOT NULL,
    price       INTEGER NOT NULL,
    emoji       TEXT,
    description TEXT,
    tags        TEXT DEFAULT '[]',
    img_url     TEXT,
    is_available INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tables (
    number      INTEGER PRIMARY KEY,
    status      TEXT DEFAULT 'free',  -- free | occupied
    seats       INTEGER DEFAULT 4
);

CREATE TABLE IF NOT EXISTS orders (
    id          TEXT PRIMARY KEY,
    table_num   INTEGER,
    party_size  INTEGER DEFAULT 1,
    items_json  TEXT NOT NULL,
    subtotal    INTEGER NOT NULL,
    tax         INTEGER NOT NULL,
    total       INTEGER NOT NULL,
    stage       INTEGER DEFAULT 0,
    notes       TEXT DEFAULT '',
    chips       TEXT DEFAULT '[]',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_stage_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    TEXT REFERENCES orders(id),
    stage       INTEGER,
    changed_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    id          TEXT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL
);
"""

SEED_CATEGORIES = [
    ('bestseller','Best Seller','🏆','https://images.unsplash.com/photo-1547592166-23ac45744acd?w=300&q=70',1),
    ('soup','Soups','🍲','https://images.unsplash.com/photo-1476718406336-bb5a9690ee2a?w=300&q=70',2),
    ('breakfast','All Day Breakfast','🍳','https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?w=300&q=70',3),
    ('salads','Salads','🥗','https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=300&q=70',4),
    ('breads','Between Breads','🥪','https://images.unsplash.com/photo-1528736235302-52922df5c122?w=300&q=70',5),
    ('nibbles','Bar Nibbles','🍟','https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=300&q=70',6),
    ('smallplates','Small Plates','🍜','https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?w=300&q=70',7),
    ('sushi','Sushi','🍣','https://images.unsplash.com/photo-1562802378-063ec186a863?w=300&q=70',8),
    ('pizza','Stone Oven Pizza','🍕','https://images.unsplash.com/photo-1513104890138-7c749659a591?w=300&q=70',9),
    ('largeplates','Large Plates','🍖','https://images.unsplash.com/photo-1544025162-d76694265947?w=300&q=70',10),
    ('desserts','Desserts','🍰','https://images.unsplash.com/photo-1488477181946-6428a0291777?w=300&q=70',11),
    ('chefspecial',"Chef Special",'👨‍🍳','https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=300&q=70',12),
]

SEED_ITEMS = [
    (101,'bestseller','Seasonal Cilantro, Crispy Tofu',525,'🌿','Crispy tofu paired with seasonal cilantro offers a fresh, savory, and high-protein plant-based meal.','["suggested"]','https://images.unsplash.com/photo-1547592166-23ac45744acd?w=400&q=70'),
    (102,'bestseller','Toasted Butter, Wild Mushroom',525,'🍄','Wild mushrooms sautéed in rich butter on toasted artisan bread.','["chef"]','https://images.unsplash.com/photo-1506084868230-bb9d95c24759?w=400&q=70'),
    (103,'bestseller','Dumpling Soup',525,'🥟','Delicate dumplings in a clear, aromatic broth with fresh herbs and a hint of sesame.','["suggested"]','https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=400&q=70'),
    (104,'bestseller','Chicken Dumpling Soup',525,'🍗','Juicy chicken-filled dumplings in a rich, slow-simmered broth.','["suggested","chef"]','https://images.unsplash.com/photo-1547592180-85f173990554?w=400&q=70'),
    (105,'bestseller','Veg Dumpling Soup',525,'🥬','Light vegetable dumplings in a clear herb broth.','["suggested"]','https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=400&q=70'),
    (201,'soup','Tomato Bisque',380,'🍅','Velvety slow-roasted tomato soup with a swirl of cream and fresh basil.','["suggested"]','https://images.unsplash.com/photo-1476718406336-bb5a9690ee2a?w=400&q=70'),
    (202,'soup','French Onion Soup',420,'🧅','Classic caramelized onion soup topped with a melted Gruyère crust.','["chef"]','https://images.unsplash.com/photo-1547592166-23ac45744acd?w=400&q=70'),
    (203,'soup','Mushroom Velouté',395,'🍄','Silky wild mushroom velouté with truffle oil, crème fraîche, and chive garnish.','["suggested","chef"]','https://images.unsplash.com/photo-1506084868230-bb9d95c24759?w=400&q=70'),
    (301,'breakfast','Eggs Benedict',420,'🍳','Perfectly poached eggs on a toasted English muffin with house-smoked ham and rich hollandaise.','["suggested"]','https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?w=400&q=70'),
    (302,'breakfast','Avocado Toast',360,'🥑','Sourdough toast, smashed avocado, cherry tomatoes, microgreens and everything bagel spice.','["suggested","chef"]','https://images.unsplash.com/photo-1603046891744-76e6300f82ef?w=400&q=70'),
    (303,'breakfast','Full English',495,'🥓','Sausages, bacon, eggs your way, grilled tomato, mushrooms, baked beans, and toast.','["chef"]','https://images.unsplash.com/photo-1519984388953-d2406bc725e1?w=400&q=70'),
    (401,'salads','Caesar Salad',340,'🥗','Romaine lettuce, house-made Caesar dressing, parmesan shavings, and garlic croutons.','["suggested"]','https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&q=70'),
    (402,'salads','Greek Salad',320,'🫑','Tomatoes, cucumbers, olives, red onion, feta cheese and oregano in olive oil.','["suggested"]','https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=400&q=70'),
    (403,'salads','Warm Duck Salad',525,'🦆','Sliced duck breast with mixed greens, orange segments, toasted walnuts and honey-balsamic glaze.','["chef"]','https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&q=70'),
    (501,'breads','Bean & Guac Burger',485,'🍔','Smoky black bean patty with guacamole, crispy lettuce and roasted tomato on a brioche bun.','["suggested"]','https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&q=70'),
    (502,'breads',"Eve's Fried Chicken Burger",595,'🍗','Crispy buttermilk-fried chicken with slaw, pickles and smoky sriracha mayo on a toasted bun.','["chef"]','https://images.unsplash.com/photo-1553979459-d2229ba7433b?w=400&q=70'),
    (503,'breads','Shrimp Po Boy',625,'🦐','Louisiana-style crispy shrimp with remoulade sauce, shredded lettuce and tomato on a soft hoagie roll.','["suggested"]','https://images.unsplash.com/photo-1528736235302-52922df5c122?w=400&q=70'),
    (504,'breads',"Good OL' Chicken Dog",575,'🌭','All-beef hot dog topped with crispy fried chicken, pickled jalapeños and house mustard.','["suggested","chef"]','https://images.unsplash.com/photo-1600555379765-f4f2c17b8b91?w=400&q=70'),
    (601,'nibbles','Truffle Fries',320,'🍟','Crispy shoestring fries tossed in truffle oil, parmesan and fresh herbs.','["suggested"]','https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&q=70'),
    (602,'nibbles','Calamari Fritti',420,'🦑','Light and crispy squid rings with lemon aioli and marinara dipping sauce.','["chef"]','https://images.unsplash.com/photo-1562802378-063ec186a863?w=400&q=70'),
    (603,'nibbles','Bruschetta Trio',380,'🍞','Three toasted baguette slices with classic tomato, mushroom pâté and roasted pepper toppings.','["suggested","chef"]','https://images.unsplash.com/photo-1572441713132-c542fc4fe282?w=400&q=70'),
    (701,'smallplates','Burrata & Heritage Tomatoes',520,'🫙','Fresh burrata with heirloom tomatoes, basil oil and flaky sea salt.','["chef"]','https://images.unsplash.com/photo-1569569970363-df7b6160d111?w=400&q=70'),
    (702,'smallplates','Crispy Duck Spring Rolls',480,'🥢','Shredded duck confit with water chestnuts, glass noodles and hoisin dipping sauce.','["suggested"]','https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=400&q=70'),
    (801,'sushi','Dragon Roll',680,'🍣','Prawn tempura roll topped with avocado, unagi and spicy mayo.','["chef"]','https://images.unsplash.com/photo-1562802378-063ec186a863?w=400&q=70'),
    (802,'sushi','Salmon Nigiri (x6)',580,'🐟','Six pieces of hand-pressed shari rice with fresh Atlantic salmon.','["suggested"]','https://images.unsplash.com/photo-1583623025817-d180a2221d0a?w=400&q=70'),
    (803,'sushi','Veggie Rainbow Roll',520,'🌈','Cucumber, avocado, mango and pickled carrot roll with ponzu dressing.','["suggested","chef"]','https://images.unsplash.com/photo-1617196034183-421b4040ed20?w=400&q=70'),
    (901,'pizza','Margherita',520,'🍕','San Marzano tomato, fior di latte mozzarella, fresh basil and extra virgin olive oil.','["suggested"]','https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400&q=70'),
    (902,'pizza','Truffle & Wild Mushroom',680,'🍄','Wild mushroom blend, truffle cream, fontina, thyme and a drizzle of black truffle oil.','["chef"]','https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400&q=70'),
    (903,'pizza','Spicy Nduja',620,'🌶️','Calabrian nduja, crushed tomato, fior di latte, roasted peppers and wild rocket.','["suggested","chef"]','https://images.unsplash.com/photo-1571997478779-2adcbbe9ab2f?w=400&q=70'),
    (1001,'largeplates','48hr Braised Short Rib',980,'🥩','Slow-braised wagyu short rib with creamy mash, rainbow chard and a red wine jus.','["chef"]','https://images.unsplash.com/photo-1544025162-d76694265947?w=400&q=70'),
    (1002,'largeplates','Pan-Seared Sea Bass',860,'🐟','Crispy-skinned sea bass with celeriac purée, samphire and a saffron beurre blanc.','["suggested"]','https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400&q=70'),
    (1003,'largeplates','Cauliflower Steak',680,'🥦','Whole roasted cauliflower steak with harissa, pomegranate, pistachios and labneh.','["suggested","chef"]','https://images.unsplash.com/photo-1512058564366-18510be2db19?w=400&q=70'),
    (1101,'desserts','Crème Brûlée',380,'🍮','Classic vanilla crème brûlée with a caramelized sugar crust. Served with fresh berries.','["suggested","chef"]','https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400&q=70'),
    (1102,'desserts','Warm Chocolate Fondant',420,'🍫','Dark chocolate fondant with a molten center, served with vanilla bean ice cream.','["chef"]','https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=400&q=70'),
    (1103,'desserts','Mango Pavlova',395,'🥭','Crisp meringue topped with whipped cream, fresh mango, passionfruit and mint.','["suggested"]','https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=400&q=70'),
    (1201,'chefspecial',"Chef's Tasting Plate",1200,'🍽️','A curated selection of our finest small bites chosen daily by our Executive Chef.','["chef"]','https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&q=70'),
    (1202,'chefspecial','Signature Wagyu Tartare',880,'🥩','Hand-cut wagyu beef tartare with quail egg, truffle mayo, capers and sourdough crisps.','["chef"]','https://images.unsplash.com/photo-1544025162-d76694265947?w=400&q=70'),
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    for stmt in SCHEMA.strip().split(';'):
        s = stmt.strip()
        if s: conn.execute(s)

    # Seed if empty
    if not conn.execute("SELECT 1 FROM categories LIMIT 1").fetchone():
        conn.executemany(
            "INSERT OR IGNORE INTO categories VALUES (?,?,?,?,?)", SEED_CATEGORIES)
        conn.executemany(
            "INSERT OR IGNORE INTO items (id,category_id,name,price,emoji,description,tags,img_url) VALUES (?,?,?,?,?,?,?,?)",
            SEED_ITEMS)
        # 12 tables
        for i in range(1, 13):
            conn.execute("INSERT OR IGNORE INTO tables (number,status,seats) VALUES (?,?,?)",
                         (i, 'free', 4))
        # Admin user
        conn.execute(
            "INSERT OR IGNORE INTO admins (id,username,password) VALUES (?,?,?)",
            (str(uuid.uuid4()), 'AD.com', 'thisisbusiness'))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def err(msg, code=400):
    return jsonify({'error': msg}), code

# ─────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'db': DB_PATH, 'time': now_iso()})

# ─────────────────────────────────────────
# MENU
# ─────────────────────────────────────────
@app.route('/api/menu')
def get_menu():
    d = db()
    cats = rows_to_list(d.execute(
        "SELECT * FROM categories ORDER BY sort_order").fetchall())
    items = rows_to_list(d.execute(
        "SELECT * FROM items WHERE is_available=1 ORDER BY id").fetchall())
    for item in items:
        item['tags'] = json.loads(item['tags'] or '[]')
    for cat in cats:
        cat['items'] = [i for i in items if i['category_id'] == cat['id']]
    return jsonify({'categories': cats, 'total_items': len(items)})

@app.route('/api/menu/<category_id>')
def get_category(category_id):
    d = db()
    cat = row_to_dict(d.execute(
        "SELECT * FROM categories WHERE id=?", (category_id,)).fetchone())
    if not cat:
        return err('Category not found', 404)
    items = rows_to_list(d.execute(
        "SELECT * FROM items WHERE category_id=? AND is_available=1 ORDER BY id",
        (category_id,)).fetchall())
    for item in items:
        item['tags'] = json.loads(item['tags'] or '[]')
    cat['items'] = items
    return jsonify(cat)

@app.route('/api/menu/item/<int:item_id>')
def get_item(item_id):
    d = db()
    item = row_to_dict(d.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone())
    if not item:
        return err('Item not found', 404)
    item['tags'] = json.loads(item['tags'] or '[]')
    return jsonify(item)

# Admin: toggle availability
@app.route('/api/menu/item/<int:item_id>/availability', methods=['PATCH'])
def toggle_availability(item_id):
    d = db()
    item = d.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item:
        return err('Item not found', 404)
    new_val = 0 if item['is_available'] else 1
    d.execute("UPDATE items SET is_available=? WHERE id=?", (new_val, item_id))
    d.commit()
    return jsonify({'id': item_id, 'is_available': bool(new_val)})

# ─────────────────────────────────────────
# TABLES
# ─────────────────────────────────────────
@app.route('/api/tables')
def get_tables():
    tables = rows_to_list(db().execute("SELECT * FROM tables ORDER BY number").fetchall())
    return jsonify({'tables': tables})

@app.route('/api/tables/<int:num>/reserve', methods=['POST'])
def reserve_table(num):
    d = db()
    t = d.execute("SELECT * FROM tables WHERE number=?", (num,)).fetchone()
    if not t:
        return err('Table not found', 404)
    if t['status'] == 'occupied':
        return err('Table already occupied', 409)
    d.execute("UPDATE tables SET status='occupied' WHERE number=?", (num,))
    d.commit()
    return jsonify({'table': num, 'status': 'occupied'})

@app.route('/api/tables/<int:num>/free', methods=['POST'])
def free_table(num):
    d = db()
    d.execute("UPDATE tables SET status='free' WHERE number=?", (num,))
    d.commit()
    return jsonify({'table': num, 'status': 'free'})

# ─────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────
@app.route('/api/orders', methods=['POST'])
def place_order():
    body = request.get_json(silent=True) or {}
    table_num  = body.get('table_num')
    party_size = body.get('party_size', 1)
    items_raw  = body.get('items', [])    # [{id, qty}]
    notes      = body.get('notes', '')
    chips      = body.get('chips', [])

    if not table_num:
        return err('table_num is required')
    if not items_raw:
        return err('Order must have at least one item')

    d = db()
    # Resolve items from DB
    resolved = []
    subtotal = 0
    for entry in items_raw:
        item = row_to_dict(d.execute(
            "SELECT * FROM items WHERE id=? AND is_available=1",
            (entry['id'],)).fetchone())
        if not item:
            return err(f"Item {entry['id']} not found or unavailable")
        qty = max(1, int(entry.get('qty', 1)))
        item['tags'] = json.loads(item['tags'] or '[]')
        line_total = item['price'] * qty
        subtotal += line_total
        resolved.append({**item, 'qty': qty, 'line_total': line_total})

    tax   = round(subtotal * 0.05)
    total = subtotal + tax

    order_num = 2400 + d.execute("SELECT COUNT(*) FROM orders").fetchone()[0] + 1
    order_id = 'EVE-' + str(order_num)
    ts = now_iso()

    d.execute(
        "INSERT INTO orders (id,table_num,party_size,items_json,subtotal,tax,total,stage,notes,chips,created_at,updated_at) VALUES (?,?,?,?,?,?,?,0,?,?,?,?)",
        (order_id, table_num, party_size, json.dumps(resolved),
         subtotal, tax, total, notes, json.dumps(chips), ts, ts))

    d.execute("INSERT INTO order_stage_log (order_id,stage,changed_at) VALUES (?,0,?)",
              (order_id, ts))

    # Mark table occupied
    d.execute("UPDATE tables SET status='occupied' WHERE number=?", (table_num,))
    d.commit()

    return jsonify({
        'order_id': order_id,
        'table_num': table_num,
        'total': total,
        'subtotal': subtotal,
        'tax': tax,
        'items': resolved,
        'stage': 0,
        'created_at': ts
    }), 201

@app.route('/api/orders')
def list_orders():
    stage_filter = request.args.get('stage')
    table_filter = request.args.get('table')
    d = db()
    q = "SELECT * FROM orders"
    params = []
    clauses = []
    if stage_filter is not None:
        clauses.append("stage=?")
        params.append(int(stage_filter))
    if table_filter:
        clauses.append("table_num=?")
        params.append(int(table_filter))
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY created_at DESC"
    orders = rows_to_list(d.execute(q, params).fetchall())
    for o in orders:
        o['items'] = json.loads(o['items_json'])
        o['chips'] = json.loads(o['chips'] or '[]')
        del o['items_json']
    return jsonify({'orders': orders, 'count': len(orders)})

@app.route('/api/orders/<order_id>')
def get_order(order_id):
    d = db()
    o = row_to_dict(d.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone())
    if not o:
        return err('Order not found', 404)
    o['items'] = json.loads(o['items_json'])
    o['chips'] = json.loads(o['chips'] or '[]')
    del o['items_json']
    stages = rows_to_list(d.execute(
        "SELECT stage,changed_at FROM order_stage_log WHERE order_id=? ORDER BY stage",
        (order_id,)).fetchall())
    o['stage_log'] = stages
    return jsonify(o)

@app.route('/api/orders/<order_id>/stage', methods=['PATCH'])
def advance_stage(order_id):
    d = db()
    o = row_to_dict(d.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone())
    if not o:
        return err('Order not found', 404)
    if o['stage'] >= 4:
        return err('Order already completed')
    new_stage = o['stage'] + 1
    ts = now_iso()
    d.execute("UPDATE orders SET stage=?, updated_at=? WHERE id=?",
              (new_stage, ts, order_id))
    d.execute("INSERT INTO order_stage_log (order_id,stage,changed_at) VALUES (?,?,?)",
              (order_id, new_stage, ts))
    # If Done, free the table
    if new_stage == 4:
        d.execute("UPDATE tables SET status='free' WHERE number=?", (o['table_num'],))
    d.commit()
    stage_names = ['Confirmed','Preparing','Ready','Served','Done']
    return jsonify({'order_id': order_id, 'stage': new_stage,
                    'stage_name': stage_names[new_stage]})

# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST'])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get('username', '').strip()
    password = body.get('password', '').strip()
    d = db()
    admin = d.execute("SELECT * FROM admins WHERE username=? AND password=?",
                      (username, password)).fetchone()
    if not admin:
        return err('Invalid credentials', 401)
    return jsonify({'success': True, 'username': username,
                    'token': f"eve-token-{admin['id'][:8]}"})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    return jsonify({'success': True})

# ─────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────
@app.route('/api/analytics')
def analytics():
    d = db()
    total_orders  = d.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_revenue = d.execute("SELECT COALESCE(SUM(total),0) FROM orders").fetchone()[0]
    live_orders   = d.execute("SELECT COUNT(*) FROM orders WHERE stage < 4").fetchone()[0]
    occupied_tabs = d.execute("SELECT COUNT(*) FROM tables WHERE status='occupied'").fetchone()[0]
    avg_order_val = round(float(total_revenue) / total_orders, 2) if total_orders else 0

    top_items_raw = d.execute("SELECT items_json FROM orders").fetchall()
    item_counts = {}
    for row in top_items_raw:
        try:
            for item in json.loads(row[0] or '[]'):
                name = item.get('name', '?')
                item_counts[name] = item_counts.get(name, 0) + int(item.get('qty', 1))
        except Exception:
            pass
    top_items = sorted(item_counts.items(), key=lambda x: -x[1])[:5]

    stage_names = ['Confirmed','Preparing','Ready','Served','Done']
    stage_breakdown = {}
    for i, sname in enumerate(stage_names):
        cnt = d.execute("SELECT COUNT(*) FROM orders WHERE stage=?", (i,)).fetchone()[0]
        stage_breakdown[sname] = cnt

    return jsonify({
        'total_orders': total_orders,
        'total_revenue': int(total_revenue),
        'live_orders': live_orders,
        'occupied_tables': occupied_tabs,
        'avg_order_value': avg_order_val,
        'top_items': [{'name': k, 'count': v} for k, v in top_items],
        'stage_breakdown': stage_breakdown
    })

# ─────────────────────────────────────────
# SERVE FRONTEND
# ─────────────────────────────────────────
@app.route('/')
def serve_index():
    return send_from_directory('templates', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🍃 Eve Café running at http://localhost:{port}")
    print("   Admin: AD.com / thisisbusiness")
    print(f"   API:   http://localhost:{port}/api/health\n")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
