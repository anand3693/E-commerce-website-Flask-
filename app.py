from flask import Flask, redirect, request,flash, url_for, render_template,session
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

app= Flask(__name__)
app.secret_key='secret key  '

UPLOAD_FOLDER='static/upload'

app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER
users = {}
merchant={}
admin={
    'username':'admin',
    'password':'admin1234'
}
carts={}
products=[]
orders=[]



@app.route('/', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phoneno=request.form['phoneno']
        password = request.form['password']
        
        if not username or not email or not phoneno or not password:
            return 'All fields are required'   

        if username in users:
            return'Username already exists. Please choose another.'
        
        if '@' not in email:
            return 'Enter a valid email'
        
        if not phoneno.isdigit() or len(phoneno) !=10:
            return'Enter a valid Phone number'
        
        users[username] = {
            'email':email,
            'phoneno':phoneno,
            'password':password,
            'status' : 'Pending'
        }
        print(f'Current users: {users}')
        return redirect('/login')

    
    return render_template('user/sign_in.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            return'Enter a password'
        if username in users:
            if users[username]['password'] == password:
                if users[username]['status'] != 'Approved':
                    return 'Your account is not approved yet.'
                session['username']=username
                return redirect(url_for('pro'))
            else:
                return 'Incorrect password for user'

        elif username in merchant:
            if merchant[username]['password'] == password:
                if merchant[username]['status'] != 'Approved':
                    return 'Your merchant account is not approved yet.'
                session['merchant'] = username
                return redirect(url_for('shop'))
            else:
                return 'Incorrect password for merchant'
        elif username == admin['username']:
            if password == admin['password']:
                return redirect(url_for('admin_dashboard'))  
            else:
                return 'You are not admin!!' 
        
        else:
            return 'Username not found'

    return render_template('user/login_page.html')


@app.route('/products')
def pro():
    available_products=[p for p in products if p['stock']>0]
    return render_template('user/products.html',products=available_products)



@app.route('/products/add_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])

   
    product = next((p for p in products if str(p['id']) == product_id), None)
    if not product:
        return 'Product not found'

   
    if product['stock'] < quantity:
        return 'Not enough stock available'

    
    cart = session.get('cart', {})

    
    if product_id in cart:
        cart[product_id]['quantity'] += quantity
    else:
        cart[product_id] = {
            'id' : product['id'],
            'name': product['name'],
            'price': product['price'],
            'image': product['image'],
            'quantity': quantity
        }

    
    product['stock'] -= quantity

    session['cart'] = cart
    return redirect(url_for('view_cart'))


@app.route('/cart')
def view_cart():
    cart = session.get('cart',{})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('user/view_cart.html', cart=cart, total=total)


@app.route('/cart/remove', methods=['POST'])
def remove_from_cart():
    product_id = request.form['product_id']
    cart = session.get('cart', {})

    
    if product_id in cart:
        removed_quantity = cart[product_id]['quantity']
        product = next((p for p in products if str(p['id']) == product_id), None)
        if product:
            product['stock'] += removed_quantity
        del cart[product_id]

    session['cart'] = cart
    return redirect(url_for('view_cart'))

@app.route('/buy', methods=['POST'])
def buy():
    cart = session.get('cart', {})
    if not cart:
        return "Your cart is empty."

    # Create a new order
    order_id = str(uuid.uuid4())[:8]
    order_items = []
    total = 0

    for product_id, item in cart.items():
        product = next((p for p in products if str(p['id']) == product_id), None)
        if not product:
            return f"Product with ID {product_id} not found"

        subtotal = product['price'] * item['quantity']
        total += subtotal
        order_items.append({
            'id' : item['id'],
            'name': product['name'],
            'quantity': item['quantity'],
            'price': product['price'],
            'subtotal': subtotal
        })

    order = {
        'id': order_id,
        'items': order_items,
        'total': total,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Completed',
        'user': session.get('username', 'Guest')
    }

    orders.append(order)

    # print(f"Order placed! Current orders list:\n{orders}")

    session.pop('cart', None)
    return render_template('user/success.html', order_id=order_id)

# @app.route('/products/buy/success')
# def success():
#     return render_template('success.html')




@app.route('/products/history')
def history():
    return render_template('user/history.html',orders=orders)

@app.route('/merchant_sign_in', methods=['GET','POST'])
def merchant_signin():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phoneno = request.form['phoneno']
        shopname = request.form['shopname']
        address = request.form['address']
        password = request.form['password']
        
        if not username or not email or not phoneno or not shopname or not address or not password:
            return 'All fields are required'

        if username in merchant:
            return 'Username already exixts. Please choose another'
        
        if '@' not in email:
            return'Enter a valid email'
        
        if not phoneno.isdigit() or len(phoneno) != 10:
            return 'Enter a valid Phone Number'
        merchant[username]={
            'email':email,
            'phoneno':phoneno,
            'shopname':shopname,
            'address':address,
            'password':password,
            'status' :'Pending'
        }
        print(f'Current merchants:{merchant}')
        return redirect('/login')
    return render_template('merchant/shop_sign_in.html')


@app.route('/merchant/orders')
def merchant_view_orders():
    merchant_username = session.get('merchant')
    if not merchant_username:
        return redirect('/login')
   
    merchant_orders = []

    for order in orders:
        # Filter items for this merchant only
        merchant_items = []
        merchant_total = 0
        for item in order['items']:
            # Find the product by name in your products list (better to do by id if you add it)
            product = next((p for p in products if p['id'] == item['id']), None)
            if product and product.get('merchant') == merchant_username:
                merchant_items.append(item)
                merchant_total += item['subtotal']

        if merchant_items:
            # Copy the order and replace items with only merchant's items
            filtered_order = order.copy()
            filtered_order['items'] = merchant_items
            filtered_order['total'] = merchant_total
            merchant_orders.append(filtered_order)

    return render_template('merchant_orders.html', orders=merchant_orders)

@app.route('/shop', methods=['GET', 'POST'])
def shop():
    merchant_username = session.get('merchant')
    if not merchant_username:
        return redirect('/login')
    
    shop_name = merchant.get(merchant_username, {}).get('shopname', 'Merchant')
    
    if request.method == 'POST':
        # Process restock quantities
        for product in products:
            if product.get('merchant') == merchant_username:
                restock_qty = request.form.get(f'restock_{product["id"]}')
                if restock_qty and restock_qty.isdigit():
                    qty = int(restock_qty)
                    if qty > 0:
                        current_stock = product['stock']
                        if product['stock'] + qty <=100:
                            product['stock'] += qty
                        else:
                            flash(f"Cannot restock '{product['name']}' with {qty} units. Maximum stock limit is 100. Current stock: {current_stock}")
        return redirect('/shop')

   
    merchant_products = [p for p in products if p.get('merchant') == merchant_username]

    
    merchant_orders = []
    for order in orders:
        merchant_items = []
        merchant_total = 0
        for item in order['items']:
            product = next((p for p in products if p['id'] == item['id']), None)
            if product and product.get('merchant') == merchant_username:
                merchant_items.append(item)
                merchant_total += item['subtotal']
        if merchant_items:
            filtered_order = order.copy()
            filtered_order['items'] = merchant_items
            filtered_order['total'] = merchant_total
            merchant_orders.append(filtered_order)

    return render_template(
        'merchant/shop.html',
        products=merchant_products,
        orders=merchant_orders,  
        shop_name=shop_name
    )


@app.route('/add_product',methods=['GET','POST'])
def add_product():
    if request.method =='POST':
        merchant_username=session.get('merchant')

        if not merchant_username:
            return 'Unauthorized: Please log in as a merchant'
        
        

        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        image = request.files.get('image')

        filename=''
        if image and image.filename!='':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
       
        # if not price.isdigit() or price <0:
        #     return"Enter a valid price"
        

        product={
            'id': str(uuid.uuid4())[:8],
            'name': name,
            'description' : description,
            'price' : price,
            'stock' : stock,
            'image' : filename,
            'merchant': merchant_username
            }
        products.append(product)
        print(f'Current Products:{products}')
        return redirect('/shop')

    return render_template('merchant/add_products.html')



@app.route('/edit_products/<product_id>', methods = ['GET','POST'])
def edit_product(product_id):
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        return'Error,Product not found '
    if request.method == 'POST':
        product['name'] = request.form['productName']
        product['description'] = request.form['productDescription']
        product['price'] = float(request.form['productPrice'])
        product['stock'] = int(request.form['productStock'])
        product['image'] = request.files.get('image')

        

        return redirect('/shop')

    return render_template('merchant/edit_products.html', product = product)


@app.route('/delete_product/<product_id>', methods=['GET'])
def delete_product(product_id):
    global products
    products = [p for p in products if p['id'] != product_id]
    return redirect('/shop')


@app.route('/admin_dashboard')
def admin_dashboard():
    pending_user={u: info for u, info in users.items() if info['status'] == 'Pending'}
    pending_merchants={m: info for m, info in merchant.items() if info['status'] == 'Pending'}
    return render_template('admin/admin_dashboard.html',pending_users= pending_user,pending_merchants= pending_merchants)

@app.route('/approve_user/<username>')
def approve_user(username):
    if username in users:
        users[username]['status'] = 'Approved'
    return redirect('/view_users')

@app.route('/delete_user/<username>')
def delete_user(username):
    users.pop(username, None)
    return redirect('/view_users')

@app.route('/approve_merchant/<username>')
def approve_merchant(username):
    if username in merchant:
        merchant[username]['status'] = 'Approved'
    return redirect('/view_merchants')

@app.route('/delete_merchant/<username>')
def delete_merchant(username):
    merchant.pop(username, None)
    return redirect('/view_merchants')

@app.route('/view_products')
def view_products():
    return render_template('admin/view_products.html', products=products)

@app.route('/view_orders')
def view_orders():
    return render_template('admin/view_orders.html', orders=orders)

@app.route('/view_users')
def view_users():
    return render_template('admin/view_users.html', users = users)

@app.route('/view_merchants')
def view_merchants():
    return render_template('admin/view_merchants.html', merchants = merchant)

if __name__=='__main__':
    app.run(debug=True)


