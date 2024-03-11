from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient('localhost', 27017, username='root', password='1234')

db = client.flask_db
todos = db.todos

todos.insert_one({'content': 'Hello', 'degree': 'IT'})