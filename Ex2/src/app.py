from flask import Flask, render_template, redirect, url_for
import os
import time

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/create')
def create_file():
    timestamp = str(time.time())
    with open(f"/data/file_{timestamp}.txt", "w") as f:
        f.write(f"File created at {timestamp}")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

