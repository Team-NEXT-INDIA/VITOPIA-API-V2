import json
from flask import Flask, jsonify, request
import mysql.connector
import pymysql
from datetime import timedelta
from datetime import datetime, date
from dateutil.parser import parse


app = Flask(__name__)


# MySQL configurations
host = 'localhost'
user = 'root3'
password = 'root'
db = 'master_vitopia'

# Connect to the database
def connect_to_database():
    connection = pymysql.connect(host=host,
                                 user=user,
                                 password=password,
                                 db=db,
                                 cursorclass=pymysql.cursors.DictCursor)
    return connection



class TimedeltaEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return json.JSONEncoder.default(self, obj)
    
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

# Function to insert transaction details into the success_transactions table
def insert_success_transaction(transaction_details):
    connection = connect_to_database()
    cursor = connection.cursor()
    query = "INSERT INTO success_transactions (CURRENCY, TXNAMOUNT, GATEWAYNAME, RESPMSG, BANKNAME, PAYMENTMODE, MID, RESPCODE, TXNID, ORDERID, STATUS, BANKTXNID, TXNDATE, CHECKSUMHASH, SKU) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    values = (transaction_details['CURRENCY'], transaction_details['TXNAMOUNT'], transaction_details['GATEWAYNAME'], transaction_details['RESPMSG'], transaction_details['BANKNAME'], transaction_details['PAYMENTMODE'], transaction_details['MID'], transaction_details['RESPCODE'], transaction_details['TXNID'], transaction_details['ORDERID'], transaction_details['STATUS'], transaction_details['BANKTXNID'], transaction_details['TXNDATE'], transaction_details['CHECKSUMHASH'], transaction_details['SKU'], )
    
    cursor.execute(query, values)
    connection.commit()
    return cursor.rowcount


def insert_order(order_details):
    connection = connect_to_database()
    cursor = connection.cursor()
    query = "INSERT INTO orders (SKU, ORDERID,TXNAMOUNT, PAYMENTMODE, TXNDATE, EMAIL) VALUES (%s,%s , %s,%s, %s, %s)"
    values = ( order_details['SKU'], order_details['ORDERID'], order_details['TXNAMOUNT'], order_details['PAYMENTMODE'], order_details['TXNDATE'], order_details['EMAIL'])
    cursor.execute(query, values)
    connection.commit()
    return cursor.rowcount

def insert_failed_transaction(transaction_details):
    connection = connect_to_database()
    cursor = connection.cursor()
    query = "INSERT INTO failed_transactions ( CURRENCY,TXNAMOUNT,  GATEWAYNAME, RESPMSG, BANKNAME, PAYMENTMODE, MID, RESPCODE, TXNID, ORDERID, STATUS, BANKTXNID, TXNDATE, CHECKSUMHASH) VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,  %s)"
    values = ( transaction_details['CURRENCY'], transaction_details['TXNAMOUNT'], transaction_details['GATEWAYNAME'], transaction_details['RESPMSG'], transaction_details['BANKNAME'], transaction_details['PAYMENTMODE'], transaction_details['MID'], transaction_details['RESPCODE'], transaction_details['TXNID'], transaction_details['ORDERID'], transaction_details['STATUS'], transaction_details['BANKTXNID'], transaction_details['TXNDATE'], transaction_details['CHECKSUMHASH'])
    cursor.execute(query, values)
    connection.commit()
    return cursor.rowcount


@app.route('/orders', methods=['POST'])
def get_orders():
    email = request.json['email']
    print(email)
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute(f"SELECT CURRENCY, TXNAMOUNT, GATEWAYNAME, RESPMSG, BANKNAME, PAYMENTMODE, MID, RESPCODE, TXNID, ORDERID, STATUS, BANKTXNID, TXNDATE, CHECKSUMHASH, SKU FROM success_transactions WHERE ORDERID LIKE 'ORDERID_{email}%'")
    orders = cursor.fetchall()
    products = []
    for order in orders:
        SKU = order["SKU"]
        cursor.execute(f"SELECT * FROM products WHERE SKU = '{SKU}'")
        product = cursor.fetchone()
        products.append(product)    

    return jsonify({ "orders": orders, "products": products })

@app.route('/save-failed-transaction', methods=['POST'])
def save_failed_transaction():
    failed_transaction_details = request.get_json()
    result = insert_failed_transaction(failed_transaction_details)
    return jsonify({"message": "Failed Transaction details stored in success_transactions table", "rowcount": result}) 


@app.route('/save-transaction', methods=['POST'])
def save_transaction():
    transaction_details = request.get_json()
    result = insert_success_transaction(transaction_details)
    return jsonify({"message": "Transaction details stored in success_transactions table", "rowcount": result})

@app.route('/save-order', methods=['POST'])
def save_order():
    order_details = request.get_json()
    result = insert_order(order_details)
    return jsonify({"message": "Order details stored in orders table", "rowcount": result})

@app.route('/events', methods=['GET'])
def get_all_events():
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute('''SELECT * FROM events''')
    events = cursor.fetchall()
    for event in events:
        start_time = event['start_time']
        end_time = event['end_time']
        duration = end_time - start_time
        event['duration'] = str(duration)
    connection.close()
    return json.dumps(events, cls=TimedeltaEncoder)
    

@app.route('/featured-events', methods=['GET'])
def get_featured_events():
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute('''SELECT * FROM events WHERE featured = true;''')
    events = cursor.fetchall()
    for event in events:
        start_time = event['start_time']
        end_time = event['end_time']
        duration = end_time - start_time
        event['duration'] = str(duration)
    connection.close()
    return json.dumps(events, cls=TimedeltaEncoder)
    
    
    


# Endpoint to get event by id
@app.route('/events/<int:id>', methods=['GET'])
def get_event_by_id(id):
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute('''SELECT * FROM events WHERE id = {}'''.format(id))
    event = cursor.fetchone()
    connection.close()
    return jsonify(event)

# Endpoint to create a new event
@app.route('/events', methods=['POST'])
def create_event():
    data = request.get_json()
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute('''INSERT INTO events (title, subtitle, description, image, avatar, btn_link, start_time, end_time, venue) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''', (data['title'], data['subtitle'], data['description'], data['image'], data['avatar'], data['btn_link'], data['start_time'], data['end_time'], data['venue']))
    connection.commit()
    connection.close()
    return jsonify({'message': 'Event created successfully.'})


# Add a new user
@app.route("/users", methods=["POST"])
def add_user():
    data = request.get_json()
    name = data["name"]
    email = data["email"]
    registration_number = data["registration_number"]
    created_at = data["created_at"]
    is_active = data["is_active"]
    image = data["image"],

    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Users (name, email, registration_number, created_at, is_active, image) VALUES (%s, %s, %s)", (name, email, registration_number, created_at, is_active, image))
    connection.commit()

    return jsonify({"message": "User added successfully."}), 201


@app.route("/slider_images", methods=['GET'])
def get_slider_images():
    # Connect to the database
    connection = connect_to_database()
    cursor = connection.cursor()

    # Retrieve the slider images data from the database
    
    cursor.execute('''SELECT * FROM slider_images''')
    slider_images = cursor.fetchall()
    connection.close()
    return json.dumps(slider_images)

# Get all products
@app.route("/products", methods=["GET"])
def get_products():
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute('''SELECT * FROM Products''')
    products = cursor.fetchall()
    connection.close()
    return json.dumps(products, default=str)

@app.route("/tickets", methods=["GET"])
def get_tickets():
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute('''SELECT * FROM Products WHERE SKU LIKE 'TICKET_%' ''')
    tickets = cursor.fetchall()
    connection.close()
    return json.dumps(tickets, default=str)


# Add a new product
@app.route("/products", methods=["POST"])
def add_product():
    data = request.get_json()

    name = data["name"]
    description = data["description"]
    price = data["price"]
    image = data["image"]
    sku = data["SKU"]

    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Products (name, description, price, image, SKU) VALUES (%s, %s, %s, %s, %s)", (name, description, price, image, sku))
    connection.commit()

    return jsonify({"message": "Product added successfully."}), 201




# Update a product
@app.route("/products/<int:id>", methods=["PUT"])
def update_product(id):
    data = request.get_json()

    name = data["name"]
    description = data["description"]
    price = data["price"]
    image = data["image"]
    sku = data["SKU"]
    
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute("UPDATE Products SET name = %s, description = %s, price = %s, sku = %s, image = %s WHERE id = %s", (name, description, price, image, id, sku))
    connection.commit()

    return jsonify({"message": "Product updated successfully."})


# Delete a product
@app.route("/products/<int:id>", methods=["DELETE"])
def delete_product(id):
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM Products WHERE id = %s", (id,))
    connection.commit()

    return jsonify({"message": "Product deleted successfully."})

if __name__ == "__main__":
    app.run(port= 1080,debug=True)