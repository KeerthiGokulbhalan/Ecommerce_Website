from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import bcrypt

app = Flask(__name__)
app.secret_key = "your_secret_key"

from models.db import get_db_connection

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products LIMIT 6")
    products = cursor.fetchall()
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        address = request.form.get('address')
        phone = request.form.get('phone')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (Username, Password, Email) VALUES (%s, %s, %s)", (username, password, email))
            user_id = cursor.lastrowid

            cursor.execute("INSERT INTO users_details (UserID, FirstName, LastName, Address, PhoneNumber) VALUES (%s, %s, %s, %s, %s)",
                           (user_id, first_name, last_name, address, phone))

            cursor.execute("INSERT INTO user_roles (UserID, RoleID) VALUES (%s, 1)", (user_id,))
            conn.commit()
            flash("✅ Registration successful! Please log in.")
            return redirect(url_for('login'))

        except Exception as e:
            conn.rollback()
            flash(f"❌ Registration failed: {str(e)}")

        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE Email = %s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password, user['Password'].encode('utf-8')):
            session['user_id'] = user['UserID']
            session['username'] = user['Username']

            cursor.execute("""
                SELECT r.RoleName 
                FROM user_roles ur
                JOIN roles r ON ur.RoleID = r.RoleID
                WHERE ur.UserID = %s
            """, (user['UserID'],))
            role = cursor.fetchone()
            session['role'] = role['RoleName'] if role else 'customer'

            flash("✅ Logged in successfully!")
            return redirect(url_for('home'))
        else:
            flash("❌ Invalid email or password.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('home'))

@app.route('/products')
def products():
    category = request.args.get('category')
    brand = request.args.get('brand')
    search = request.args.get('search')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT p.ProductID, p.ProductName, p.Description, p.Price 
        FROM products p
        LEFT JOIN product_category_mapping pcm ON p.ProductID = pcm.ProductID
        LEFT JOIN categories c ON pcm.CategoryID = c.CategoryID
        LEFT JOIN product_brand_mapping pbm ON p.ProductID = pbm.ProductID
        LEFT JOIN brands b ON pbm.BrandID = b.BrandID
        WHERE 1=1
    """

    params = []

    if category:
        query += " AND c.CategoryName LIKE %s"
        params.append(f"%{category}%")

    if brand:
        query += " AND b.BrandName LIKE %s"
        params.append(f"%{brand}%")

    if search:
        query += " AND p.ProductName LIKE %s OR p.Description LIKE %s"
        params.extend([f"%{search}%", f"%{search}%"])

    cursor.execute(query, tuple(params))
    results = cursor.fetchall()

    cursor.execute("SELECT DISTINCT CategoryName FROM categories")
    categories = [row['CategoryName'] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT BrandName FROM brands")
    brands = [row['BrandName'] for row in cursor.fetchall()]

    return render_template('products.html', products=results, categories=categories, brands=brands)

@app.route('/cart/add/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT CartID FROM cart WHERE UserID = %s ORDER BY CreatedAt DESC LIMIT 1", (session['user_id'],))
    cart = cursor.fetchone()

    if not cart:
        cursor.execute("INSERT INTO cart (UserID) VALUES (%s)", (session['user_id'],))
        conn.commit()
        cart_id = cursor.lastrowid
    else:
        cart_id = cart[0]

    try:
        cursor.execute("INSERT INTO cart_items (CartID, ProductID, Quantity) VALUES (%s, %s, 1)",
                       (cart_id, product_id))
        conn.commit()
        flash("✅ Item added to cart!")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Error adding item to cart: {str(e)}")

    return redirect(url_for('products'))

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.ProductID, p.ProductName, p.Price, ci.Quantity,
               p.Price * ci.Quantity AS TotalPrice
        FROM cart_items ci
        JOIN cart c ON ci.CartID = c.CartID
        JOIN products p ON ci.ProductID = p.ProductID
        WHERE c.UserID = %s
    """, (session['user_id'],))

    cart_items = cursor.fetchall()
    total = sum(item['TotalPrice'] for item in cart_items)

    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/cart/update', methods=['POST'])
def update_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE cart_items ci
        JOIN cart c ON ci.CartID = c.CartID
        SET ci.Quantity = %s
        WHERE c.UserID = %s AND ci.ProductID = %s
    """, (quantity, session['user_id'], product_id))

    conn.commit()
    return redirect(url_for('view_cart'))

@app.route('/cart/remove', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product_id = request.form.get('product_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE ci FROM cart_items ci
        JOIN cart c ON ci.CartID = c.CartID
        WHERE c.UserID = %s AND ci.ProductID = %s
    """, (session['user_id'], product_id))

    conn.commit()
    return redirect(url_for('view_cart'))

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.ProductID, p.ProductName, p.Price, ci.Quantity
        FROM cart_items ci
        JOIN cart c ON ci.CartID = c.CartID
        JOIN products p ON ci.ProductID = p.ProductID
        WHERE c.UserID = %s
    """, (session['user_id'],))

    cart_items = cursor.fetchall()
    total = sum(item['Price'] * item['Quantity'] for item in cart_items)

    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/place-order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    full_name = request.form.get('full_name')
    address = request.form.get('address')
    city = request.form.get('city')
    zip_code = request.form.get('zip_code')
    phone = request.form.get('phone')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.ProductID, p.Price, ci.Quantity
        FROM cart_items ci
        JOIN cart c ON ci.CartID = c.CartID
        JOIN products p ON ci.ProductID = p.ProductID
        WHERE c.UserID = %s
    """, (user_id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        flash("Your cart is empty.")
        return redirect(url_for('home'))

    total_amount = sum(item['Price'] * item['Quantity'] for item in cart_items)

    try:
        cursor.execute("INSERT INTO orders (UserID, StatusID) VALUES (%s, 1)", (user_id,))
        order_id = cursor.lastrowid

        for item in cart_items:
            cursor.execute("INSERT INTO order_items (OrderID, ProductID, Quantity, UnitPrice) VALUES (%s, %s, %s, %s)",
                           (order_id, item['ProductID'], item['Quantity'], item['Price']))

        cursor.execute("""
            DELETE ci FROM cart_items ci
            JOIN cart c ON ci.CartID = c.CartID
            WHERE c.UserID = %s
        """, (user_id,))

        conn.commit()
        flash("✅ Your order has been placed successfully!")
    except Exception as e:
        conn.rollback()
        flash("❌ There was an error placing your order.")
        print("Error:", e)
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('home'))

@app.route('/orders')
def order_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT o.OrderID, o.OrderDate, os.StatusName, SUM(oi.Quantity * oi.UnitPrice) AS Total
        FROM orders o
        JOIN order_status os ON o.StatusID = os.StatusID
        JOIN order_items oi ON o.OrderID = oi.OrderID
        WHERE o.UserID = %s
        GROUP BY o.OrderID
        ORDER BY o.OrderDate DESC
    """, (session['user_id'],))

    orders = cursor.fetchall()
    return render_template('order_history.html', orders=orders)

@app.route('/order/<int:order_id>')
def view_order_details(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT oi.*, p.ProductName
        FROM order_items oi
        JOIN products p ON oi.ProductID = p.ProductID
        WHERE oi.OrderID = %s
    """, (order_id,))
    items = cursor.fetchall()

    cursor.execute("SELECT * FROM orders WHERE OrderID = %s", (order_id,))
    order = cursor.fetchone()

    return render_template('order_details.html', items=items, order=order)

if __name__ == '__main__':
    app.run(debug=True)