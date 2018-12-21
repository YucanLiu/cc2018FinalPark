from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Email, Length
from flask_sqlalchemy  import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import geopy.geocoders
from geopy.geocoders import Nominatim
import ssl
import certifi

application = Flask(__name__)
application.config['SECRET_KEY'] = 'Thisissupposedtobesecret!'
application.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://cc2018MasterUser:cc2018MasterUser@cc2018finaldb.cfqqmgga1hbh.us-east-1.rds.amazonaws.com:3306/cc2018FinalDB'
bootstrap = Bootstrap(application)
db = SQLAlchemy(application)

ctx = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx
geolocator = Nominatim(scheme='http')

class Parking(db.Model):
        __tablename__ = 'parking'
        id       = db.Column(db.Integer, primary_key=True)
        location = db.Column(db.String(255))
        type     = db.Column(db.String(20))
        available= db.Column(db.String(20))
        status   = db.Column(db.String(20))

@application.route('/')
def index():
    file = open('data.csv')
    i = 0
    for line in file:
        if i == 0:
            print("first line")
            i += 1
            continue
        else:
            cur_line = line.split(',')
            print(cur_line)
            cur_loc = str(cur_line[4]) + ',' + str(cur_line[0])
            new_parking = Parking(location=cur_loc, type="meter", available="no", status=cur_line[5])
            i+=1
            db.session.add(new_parking)
            db.session.commit()
    return '<h1>Building database</h1>'

if __name__ == '__main__':
    application.run(debug=True)
