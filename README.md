# E-Commerce Website - DBMS Mini Project

## 🛠️ Technologies Used

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python + Flask
- **Database:** MySQL (normalized up to 4NF)
- **Authentication:** Session-based with password hashing

## 📁 Folder Structure

See above.

## 🧱 Features Implemented

- User Registration & Login
- Role-Based Access (Customer only)
- Product Listing with Dynamic Display
- Shopping Cart Management
- Checkout Process with Mock Order Placement

## 🗃️ Database Schema

Tables:

- users
- users_details
- roles
- user_roles
- products
- brands
- categories
- product_brand_mapping
- product_category_mapping
- cart
- cart_items
- orders
- order_items
- order_status

## ⚙️ Setup Instructions

1. Clone the repo
2. Install dependencies: `pip install flask mysql-connector-python bcrypt`
3. Import schema into MySQL
4. Update `config.py` with your DB credentials
5. Run: `python app.py`
6. Visit: http://localhost:5000
