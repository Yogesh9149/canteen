from flask import Flask, render_template, request, jsonify, send_file, url_for
import razorpay
import sqlite3
import pandas as pd
from io import BytesIO
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# Database
def init_db():
    conn = sqlite3.connect('stock.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY, index_no TEXT, desc TEXT, balance INTEGER, vat TEXT)''')
    conn.commit()
    conn.close()

init_db()

def query_stock():
    conn = sqlite3.connect('stock.db')
    rows = conn.execute('SELECT * FROM stock').fetchall()
    conn.close()
    return rows

# Razorpay client (test keys)
rzp = razorpay.Client(auth=("YOUR_ID", "YOUR_SECRET"))

# Google Drive auth
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file('service.json', scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)
DRIVE_FOLDER_ID = 'YOUR_FOLDER_ID'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stock')
def api_stock():
    rows = query_stock()
    return jsonify([dict(id=r[0], index=r[1], desc=r[2], balance=r[3], vat=r[4]) for r in rows])

@app.route('/api/update', methods=['POST'])
def api_update():
    data = request.json
    conn = sqlite3.connect('stock.db')
    for item in data:
        conn.execute('UPDATE stock SET balance=? WHERE id=?', (item['balance'], item['id']))
    conn.commit()
    conn.close()
    return jsonify(status='ok')

@app.route('/api/pay', methods=['POST'])
def api_pay():
    amount = int(request.json.get('amount')) * 100
    resp = rzp.order.create({'amount': amount, 'currency': 'INR', 'receipt': 'rcpt_'+str(amount)})
    return jsonify(order_id=resp['id'], key="YOUR_ID")

@app.route('/api/share_drive')
def api_share_drive():
    df = pd.DataFrame(query_stock(), columns=['id','index','desc','balance','vat'])
    excel = BytesIO()
    df.to_excel(excel, index=False)
    excel.seek(0)
    file = drive.files().create(
        body={'name': 'stock.xlsx', 
              'parents': [DRIVE_FOLDER_ID]},
        media_body=BytesIO(excel.read()), fields='id,webViewLink').execute()
    return jsonify(link=file['webViewLink'])

@app.route('/download')
def download():
    df = pd.DataFrame(query_stock(), columns=['id','index','desc','balance','vat'])
    buf = BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return send_file(buf, attachment_filename='stock.xlsx', as_attachment=True)

if __name__=='__main__':
    app.run(debug=True)
