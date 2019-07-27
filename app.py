from flask import Flask, request, render_template, flash, redirect, url_for, session, logging
import sqlite3 as sql
from wtforms import Form, StringField, TextAreaField, PasswordField, IntegerField, RadioField, DateTimeField, SelectField, DateField, validators
from passlib.hash import sha256_crypt
from functools import wraps


app = Flask(__name__)

rate = 500



@app.route('/')
def index():
	return render_template('home.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/contact')
def contact():
	return render_template('contact.html')


@app.route('/bookings/<string:id>')
def booking(id):
	return render_template('bookings.html', id=id)

class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=1, max=50)])
	email = StringField('Email', [validators.Email()])
	phone = IntegerField('Phone', [validators.NumberRange(min=1000000000, max=9999999999, message='Phone not valid!')])
	password = PasswordField('Password', [
			validators.DataRequired(),
			validators.EqualTo('confirm', message='Passwords do not match!')
		])
	confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		phone = form.phone.data
		password = sha256_crypt.encrypt(str(form.password.data))

		conn = sql.connect('PetDayCare.db')
		conn.row_factory = sql.Row
		cur = conn.cursor()
		cur.execute("SELECT * FROM users WHERE username = ?", (username, ))
		if cur.fetchone() is not None:
			flash("That username is already taken!", 'danger')
			return render_template('register.html', form=form)
		else:
			cur.execute("INSERT INTO users(name,username,email,phone,password) VALUES(?, ?, ?, ?, ?)", (name, username, email, phone, password))
			id = cur.execute("SELECT * FROM users WHERE username = ?", (username, )).fetchone()
			cur.execute("INSERT INTO payments(amount,username) VALUES(?,?)", (0,id['username']))
		conn.commit()
		conn.close()
		flash("You are now registered and can log in", 'success')
		return redirect(url_for('login'))
	return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password_candidate = request.form['password']
		conn = sql.connect('PetDayCare.db')
		conn.row_factory = sql.Row
		cur = conn.cursor()
		user = cur.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
		if user is not None:
			password = user['password']
			if sha256_crypt.verify(password_candidate, password):
				msg = 'Login Successful'
				session['logged_in'] = True
				session['username'] = username

				flash('You are now logged in','success')
				return redirect(url_for('dashboard'))
			else:
				error = 'Invalid Passoword!'
				return render_template('login.html', error=error)
			cur.close()
		else:
			error = 'No Username Found'
			return render_template('login.html', error=error)
	return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You are not logged in, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
	return render_template('dashboard.html')

class PetForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	breed = StringField('Breed', [validators.Length(min=1, max=50)])
	type = RadioField('Type', choices=[('dog','Dog'),('cat','Cat')])

@app.route('/dashboard/add_remove', methods=['GET', 'POST'])
@is_logged_in
def change():
	form = PetForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		breed = form.breed.data
		type = form.type.data
		con = sql.connect('PetDayCare.db')
		con.row_factory = sql.Row
		cur = con.cursor()
		data = cur.execute('SELECT * FROM users WHERE username = ?', (session['username'], )).fetchone()
		cur.execute("INSERT INTO pets(name,breed,type,userid) VALUES(?, ?, ?, ?)", (name, breed, type, data['ID']))
		con.commit()
		con.close()
		flash("Your Pet is successfully added!", 'success')
		return redirect(url_for('dashboard'))
	return render_template('change.html', form=form)

class BookForm(Form):
	name = SelectField('Name', coerce=int)
	date = StringField('date')
	start = StringField('start')
	end = StringField('end')

@app.route('/dashboard/booking', methods=['GET', 'POST'])
@is_logged_in
def book():
	form = BookForm(request.form)
	con = sql.connect('PetDayCare.db')
	con.row_factory = sql.Row
	cur = con.cursor()
	data = cur.execute('SELECT * FROM users WHERE username = ?', (session['username'], )).fetchone()
	available_dogs = cur.execute('SELECT id,name FROM pets WHERE userid = ?', (data['ID'], )).fetchall()
	form.name.choices = available_dogs
	if request.method == 'POST' and form.validate():
		name = form.name.data
		date = form.date.data
		start = form.start.data.split(':')[0]
		end = form.end.data.split(':')[0]
		for i in range(int(start),int(end)+1):
			confirm = cur.execute('SELECT * FROM checking WHERE date = ? AND hour = ?', (date, i)).fetchone()
			if confirm is not None and confirm['count'] == 5 :
				flash("Slot Unavailabe!", 'danger')
				return render_template('booking.html', form=form)
		for i in range(int(start),int(end)+1):
			check = cur.execute('SELECT * FROM checking WHERE date = ? AND hour = ?', (date, i, )).fetchone()
			if check is None:
				cur.execute('INSERT INTO checking(date,hour,count) VALUES(?, ?, ?)', (date, i, 1))
			else:
				cur.execute('UPDATE checking SET count = ? WHERE date = ? AND hour = ?', (check['count']+1,date,i, ))
		usrid = cur.execute('SELECT * FROM users WHERE username = ?',(session['username'],)).fetchone()
		pid =  cur.execute('SELECT * FROM pets WHERE userid = ?',(usrid['ID'],)).fetchone()
		cur.execute('INSERT INTO bookings(name,date,start,end,petid,userid) VALUES(?, ?, ?, ?, ?, ?)', (name, date, start+':00', end+':00', pid['ID'], usrid['ID']))
		duration = int(end) - int(start)
		amount = duration * rate
		amt = cur.execute('SELECT * from payments WHERE username = ?',(usrid['username'], )).fetchone()
		cur.execute('UPDATE payments SET amount = ? WHERE username = ?', (amt['amount']+amount,usrid['username']))
		con.commit()
		con.close()
		flash("Booking done successfully!", 'success')
		return redirect(url_for('dashboard'))
	return render_template('booking.html', form=form)

@app.route('/dashboard/payments')
@is_logged_in
def show_payments():
	con = sql.connect('PetDayCare.db')
	con.row_factory = sql.Row
	cur = con.cursor()
	amt = cur.execute('SELECT * FROM payments WHERE username = ?',(session['username'],)).fetchone()
	con.close()
	return render_template('payment.html', amount=amt['amount'])

@app.route('/dashboard/view_booking')
@is_logged_in
def view_bookings():
	con = sql.connect('PetDayCare.db')
	con.row_factory = sql.Row
	cur = con.cursor()
	cur = con.cursor()
	data = cur.execute('SELECT * FROM bookings').fetchall()
	con.close()
	return render_template('view_booking.html', data=data)

class ManageBookingForm(Form):
	username = StringField('username')
	amount = IntegerField('amount')

@app.route('/dashboard/manage_payment', methods=['GET', 'POST'])
@is_logged_in
def manage_payment():
	form = ManageBookingForm(request.form)
	if request.method == 'POST' and form.validate():
		username = form.username.data
		amount = form.amount.data
		con = sql.connect('PetDayCare.db')
		con.row_factory = sql.Row
		cur = con.cursor()
		cur = con.cursor()
		data = cur.execute('SELECT * FROM payments WHERE username = ?',(username,)).fetchone()
		if data['amount'] == 0:
			flash('Amount is already 0', "danger")
			return redirect(url_for('manage_payment'))
		amt = data['amount'] - amount
		cur.execute('UPDATE payments SET amount = ? WHERE username = ?', (amt,username))
		flash("Amount successfully updated! Remaining amount is: "+str(amt), "info")
		con.commit()
		con.close()
		return render_template('manage_payment.html', form=form)
	return render_template('manage_payment.html', form=form)

if __name__=='__main__':
	app.secret_key='secret123'
	app.run(debug=True)