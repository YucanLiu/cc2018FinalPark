from flask import Flask, render_template, redirect, url_for, session
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import InputRequired, Email, Length
from flask_sqlalchemy  import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

import geopy.geocoders
from geopy.geocoders import Nominatim, GoogleV3
from geopy.exc import GeocoderTimedOut
from geopy import distance
import ssl
import certifi
from datetime import datetime
from pytz import timezone

from flask_googlemaps import GoogleMaps
from flask_googlemaps import Map

import boto3
import json

### GLOBAL VALUES ###
CREDIT_REPORTED = 3
CREDIT_UNREPORTED = 5
CREDIT_FIND = int(-5)
WELCOME_CREDIT = 10
GOOGLE_MAP_API_KEY = 'AIzaSyChya4BMiH6H57hUkrk_F7DYF54REa6F_o'
MAP_ZOOM_SIZE = 15
est = timezone('EST')
#######

application = Flask(__name__)
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.config['SECRET_KEY'] = 'Thisissupposedtobesecret!'
application.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://cc2018MasterUser:cc2018MasterUser@cc2018finaldb.cfqqmgga1hbh.us-east-1.rds.amazonaws.com:3306/cc2018FinalDB'
bootstrap = Bootstrap(application)
db = SQLAlchemy(application)
login_manager = LoginManager()
login_manager.init_app(application)
login_manager.login_view = 'login'

ctx = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx
geolocator = GoogleV3(api_key=GOOGLE_MAP_API_KEY)

application.config['GOOGLEMAPS_KEY'] = GOOGLE_MAP_API_KEY
GoogleMaps(application)

### Models Section ###
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    emailadr = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(50))

class Historys(db.Model):
        __tablename__ = 'historys'
        id       = db.Column(db.Integer, primary_key=True)
        time     = db.Column(db.DateTime)
        credit   = db.Column(db.Integer)
        type     = db.Column(db.String(20))
        status   = db.Column(db.String(20))
        user_name= db.Column(db.String(20))

class Parking(db.Model):
        __tablename__ = 'parking'
        id       = db.Column(db.Integer, primary_key=True)
        location = db.Column(db.String(255))
        type     = db.Column(db.String(20))
        available= db.Column(db.String(20))
        status   = db.Column(db.String(20))

        def clone(self):
            clone_parking = Parking(id = self.id, location = self.location, type = self.type, available = self.available, status = self.status)
            return clone_parking

######

### Login Manager Section ###
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))
######

### Forms Section ###
class LoginForm(FlaskForm):
    username = StringField('User name', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=50)])
    remember = BooleanField('Remember me')

class RegisterForm(FlaskForm):
    emailadr = StringField('Email (Real email address)', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('User name (4-15 characters)', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password (8-50 characters)', validators=[InputRequired(), Length(min=8, max=50)])

class ReportParkingForm(FlaskForm):
    location = StringField('Location', validators=[InputRequired(), Length(max=255)])
    type = SelectField('P@rking Type', choices=[('Street', 'Street Parking'), ('meter', 'Meter Parking')], validators=[InputRequired()])
    available = SelectField('Current Available', choices=[('yes', 'Available'), ('no', 'Unavailable')], validators=[InputRequired()])
    status = SelectField('P@rking Status', choices=[('Active', 'Active'), ('Inactive', 'Inactive')], validators=[InputRequired()])

class FindParkingForm(FlaskForm):
    location = StringField('Location', validators=[InputRequired(), Length(max=255)])
    miles = FloatField('Within Miles', validators=[InputRequired()])
    type = SelectField('P@rking Type', choices=[('all', 'ALL Parking'), ('Street', 'Street Parking'), ('meter', 'Meter Parking')], validators=[InputRequired()])

class SendToPhoneForm(FlaskForm):
    phone = StringField('Phone Number', validators=[InputRequired(), Length(max=15)])
######

### APP Routes ###
@application.route('/')
def index():
    return render_template('index.html')

@application.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    notice = ''
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('dashboard'))
            else:
                notice = 'Wrong Username or Password, please try again!'

        #return '<h1>' + form.username.data + ' ' + form.password.data + '</h1>'
    return render_template('login.html', form=form, notice=notice)

@application.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = Users(username=form.username.data, emailadr=form.emailadr.data, password=hashed_password)
        db.session.add(new_user)
        welcome = Historys(time=datetime.now(est), credit=WELCOME_CREDIT, type='new user welcome', status='Done', user_name=form.username.data)
        db.session.add(welcome)
        db.session.commit()
        db.session.close()

        # return '<h1>New user has been created!</h1>'
        #return '<h1>' + form.username.data + ' ' + form.email.data + ' ' + form.password.data + '</h1>'
        return redirect(url_for('login'))

    return render_template('signup.html', form=form)

@application.route('/dashboard')
@login_required
def dashboard():
    historys = Historys.query.filter_by(user_name=current_user.username).order_by(Historys.time.desc()).all()
    credit = get_credit(historys)
    return render_template('dashboard.html', name=current_user.username, historys=historys, credit = credit)

def get_credit(historys):
    credit = 0
    for his in historys:
        # his.location = geolocator.reverse(his.location, addressdetails=False)
        credit += int(his.credit)
    return credit

@application.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@application.route('/report_a_park', methods=['GET', 'POST'])
@login_required
def report_a_park():
    form = ReportParkingForm()
    notice = ''

    if form.validate_on_submit():
        # print(form.location.data)
        location = do_geocode(form.location.data)
        # print((location.latitude, location.longitude))
        if location == None:
            notice = 'Invalid Input! Please Try again! NOTE: The app is only supporting NYC for now.'
            return render_template('report_a_park.html', form=form, name=current_user.username, notice=notice)
        else:
            long_lat = str(location.latitude) + ',' + str(location.longitude)
            num = Parking.query.filter_by(location=long_lat).count()
            score = CREDIT_UNREPORTED
            # current location is not recorded in the database
            if num == 0:
                new_parking = Parking(location=long_lat, type=form.type.data, available=form.available.data, status=form.status.data)
                print(long_lat, new_parking)
                db.session.add(new_parking)
            else: # current location is recorded in the database
                parking = Parking.query.filter_by(location=long_lat).first()
                parking.type = form.type.data
                parking.available = form.available.data
                parking.status = form.status.data
                score = CREDIT_REPORTED

            # add the current historys to the database
            cur_history = Historys(time=datetime.now(est), credit=score, type='report', status='Done', user_name=current_user.username)
            db.session.add(cur_history)

            # commit to DB
            db.session.commit()
            db.session.close()

        return redirect(url_for('dashboard'))

    return render_template('report_a_park.html', form=form, name=current_user.username, notice=notice)

@application.route('/find_a_park', methods=['GET', 'POST'])
@login_required
def find_a_park():
    form = FindParkingForm()
    notice = ''

    if form.validate_on_submit():
        # find the user's credit
        historys = Historys.query.filter_by(user_name=current_user.username).order_by(Historys.time.desc()).all()
        credit = get_credit(historys)
        if credit < 5:
            notice = 'Insufficient credit! Please report some P@rking!'
            return render_template('find_a_park.html', form=form, name=current_user.username, notice=notice)

        # print(form.location.data)
        location = do_geocode(form.location.data)
        # print((location.latitude, location.longitude))
        if location == None or str(geolocator.reverse(str(location.latitude) + ',' + str(location.longitude))[-3]) != 'New York, NY, USA':
            notice = 'Invalid Input, please Try again! NOTE: The app is only supporting NYC for now.'
            return render_template('find_a_park.html', form=form, name=current_user.username, notice=notice)
        else:
            # map markers
            map_markers = []

            target = str(location.latitude) + ',' + str(location.longitude)
            all_parkings = Parking.query.filter_by().all()

            # final result for table display
            results = []
            for parking in all_parkings:
                if (form.type.data != 'all' and parking.type != form.type.data) or parking.available == 'no':
                    # print(parking)
                    # print(parking.type != form.type.data)
                    # print(parking.available == 'no')
                    # print(parking.status)
                    continue
                else:
                    cur = parking.location
                    dis = distance.distance(target, cur).miles
                    # print('cur',cur,'dis',dis)
                    if dis < form.miles.data:
                        cur_park = parking.clone()

                        # add to map markers
                        cur_long_lat = cur_park.location.split(",")

                        # translate the long_lat to real address
                        cur_park.location = geolocator.reverse(parking.location)[0]
                        # print(str(geolocator.reverse(parking.location)[-3])=='New York, NY, USA')

                        map_markers.append({
                            'icon': 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
                            'lat':  float(cur_long_lat[0]),
                            'lng':  float(cur_long_lat[1]),
                            'infobox': "<b>"+str(cur_park.type)+" parking: "+str(cur_park.location)+"</b>"
                        })

                        results.append(cur_park)

            if len(results) > 0: # found at least one result
                cur_history = Historys(time=datetime.now(est), credit=CREDIT_FIND, type='find', status='Done', user_name=current_user.username)
                db.session.add(cur_history)
                # commit to DB
                db.session.commit()


            # add the current location to the map
            map_markers.append({
                'icon': 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
                'lat':  location.latitude,
                'lng':  location.longitude,
                'infobox': "<b>Your location</b>"
            })

            mymap = Map(
                identifier="view-side",
                lat=location.latitude,
                lng=location.longitude,
                zoom=MAP_ZOOM_SIZE,
                markers=map_markers,
                style='height:50vh; width:100%;',
                fit_markers_to_bounds = True
            )

            search_results = toJSON(results)

            session['search_results'] = search_results
            session['markers'] = map_markers

            return render_template('find_result.html', name=current_user.username, results=results, gmap=mymap, form=SendToPhoneForm())

    return render_template('find_a_park.html', form=form, name=current_user.username, notice=notice)

@application.route('/find_result', methods=['GET', 'POST'])
@login_required
def find_result():
    form = SendToPhoneForm()

    if form.validate_on_submit():

        results = session['search_results']
        map_markers = session['markers']
        # print(map_markers)

        kc = boto3.client('kinesis',
                          region_name = 'us-east-1',
                          aws_access_key_id="AKIAIT5KESPT4OXJ7WYQ",
                          aws_secret_access_key="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")

        pk = "park1"

        record = {}

        record['phone'] = form.phone.data
        record['search_results'] = []
        for res in results:
            record['search_results'].append(str(res['type']) + ' parking: ' +res['location'])
        record['PartitionKey'] = pk
        print(record)


        kc.put_record(StreamName='park', Data=json.dumps(record), PartitionKey=pk)

        location = map_markers[-1]

        mymap = Map(
            identifier="view-side",
            lat=location['lat'],
            lng=location['lng'],
            zoom=MAP_ZOOM_SIZE,
            markers=map_markers,
            style='height:50vh; width:100%;',
            fit_markers_to_bounds = True
        )

        return render_template('find_result.html', name=current_user.username, results=results, gmap=mymap, form=form)

    return redirect(url_for('dashboard'))
######

def do_geocode(address):
    try:
        return geolocator.geocode(address, timeout=10)
    except GeocoderTimedOut:
        return do_geocode(address)

def toJSON(results):
    res = []
    for result in results:
        res.append({
            'id': result.id,
            'location': str(result.location),
            'type': result.type,
            'available': result.available,
            'status': result.status
        })
    return res

if __name__ == '__main__':
    application.run(debug=True)
