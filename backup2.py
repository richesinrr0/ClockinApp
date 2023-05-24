from flask import Flask, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from io import BytesIO
import base64


app = Flask(__name__)

# the name of the database; add path if necessary
db_name = 'test_database'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# this variable, db, used for all SQLAlchemy commands
db = SQLAlchemy(app)

# each table in the database needs a class to be created for it
# db.Model is required
# identify all columns by name and data type
class time_chart(db.Model):
    __tablename__ = 'time' 
    entry_id = db.Column(db.String, primary_key=True) #create entry id-in to pull when clocking out  9734in
    #active = db.Column(db.Integer) #1 for active (clocked in) 0 for not active (not clocked in)
    emp_ssn = db.Column(db.String) #last four ssn
    emp_first_name = db.Column(db.String)
    emp_last_name = db.Column(db.String)
    ref_clock = db.Column(db.Integer)
    clock_in = db.Column(db.String)
    clock_out = db.Column(db.String) #edit (update) table when emp clocks out
    total_hours = db.Column(db.Integer)

    #select first from table where first_name == ross and last_name == richesin and clockout == null

employees = {
    '9746': 
        {'password': 'Viperrox15',
        'first_name': 'Ross',
        'last_name': 'Richesin'}
}

def generate_figure(y_hours):
    #y_hours = list(map(lambda x: x.replace('null', 0), y_hours))

    fig, ax = plt.subplots(figsize=(150,30))
    size = 150
    font = {'size': size}
    plt.rc('font', **font)

    x = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    right_side = ax.spines["right"]
    right_side.set_visible(False)
    top = ax.spines["top"]
    top.set_visible(False)
    left_side = ax.spines["left"]
    left_side.set_visible(False)
    plt.yticks([]) 
    plt.bar(x,y_hours,color='#e0f1ff')
    #e0f1ff
    #f0f8ff
    for label in (ax.get_xticklabels()):
        label.set_fontsize(size)
    for i in range(len(y_hours)):
        if y_hours[i] != 0 and y_hours[i]:
            plt.text(i, y_hours[i] +.25, f'{y_hours[i]} hours', ha = 'center')
    
    figfile = BytesIO()
    plt.savefig(figfile, format='png')
    figfile.seek(0)  # rewind to beginning of file
    figdata_png = base64.b64encode(figfile.getvalue())
    return figdata_png

def get_hours(ssn):
    cur_date = datetime.now()
    ref_date = cur_date - timedelta(days=7)
    int_ref_date = int(ref_date.strftime("%Y%m%d%H%M%S"))

    conn = sqlite3.connect('time_database') 
    c = conn.cursor()

    c.execute(f' SELECT total_hours, ref_clock FROM time_record WHERE emp_ssn = "{ssn}" and ref_clock > "{int_ref_date}" ')
     #stored as string - so add a new column to database that stores dates as ints 
     #(2022-09-28 becomes 20220928) and just index

    entries = c.fetchall()
    conn.commit()
    c.close()

    print('entries', entries)
    #need to make list with total hours for each day

    y_list =[0,0,0,0,0,0,0]
    for total_hours, ref in entries:
        y_list[ref[-1]] += total_hours

    return y_list



@app.route('/login')
def login():
    return render_template('login.html', fill='')


@app.route('/time', methods = ['GET','POST'])
def data():
    global ssn
    try:
        if request.method == 'POST':

            if request.form.get('action') == 'Submit':
                form_data = request.form
                ssn, password = form_data['ssn'], form_data['password']
                print(ssn,password)
                if ssn in employees.keys():
                    if employees[ssn]['password'] == password:
                        
                        return render_template('test.html', name=employees[ssn]['first_name'])
                else:
                    return render_template('login.html', fill='Incorrect SSN or Password')
            
            #put in clockin time into sql database then out on clockout
            if request.form.get('action')=='Clock-in':
                print(ssn)
                clockin = datetime.now()#.isoformat()
                
                conn = sqlite3.connect('time_database') 
                c = conn.cursor()

                c.execute(f' SELECT entry_id FROM time_record WHERE emp_ssn = "{ssn}";')
                num_entries = len(c.fetchall()) + 1
          
                entry_id = ssn + str(num_entries)

                c.close()

                ref_clock = str(clockin.strftime("%Y%m%d%H%M%S")) + str(datetime.today().weekday())
                ref_clock = int(ref_clock)
                #week day is last digit
                print(int(ref_clock))

                c = conn.cursor()
                c.execute('''
                        INSERT INTO time_record (entry_id, emp_ssn, emp_first_name, emp_last_name, ref_clock,
                        clock_in, clock_out, total_hours)

                                VALUES
                                (?,?,?,?,?,?,?,?)''',(entry_id, ssn, employees[ssn]['first_name'], employees[ssn]['last_name'], ref_clock, clockin, 'null', 'null'))

                        
                conn.commit()
                c.close()

                return render_template('test.html', name=employees[ssn]['first_name'])
        
            elif request.form.get('action')=='Clock-out':

                conn = sqlite3.connect('time_database') 
                c = conn.cursor()
                c.execute(f' SELECT clock_in FROM time_record WHERE emp_ssn = "{ssn}" and clock_out="null";')

                clockin_str = c.fetchone()[0] # tuple
                c.close()

                clockin = datetime.fromisoformat(clockin_str)
                clockout = datetime.now()

                total_time = clockout - clockin
                total = total_time.total_seconds()
                total_hours = round(total/3600, 4)

                #conn = sqlite3.connect('time_database') 
                c = conn.cursor()
                c.execute("UPDATE time_record SET clock_out=?, total_hours=? WHERE emp_ssn=? and clock_out='null'", (clockout, total_hours, ssn))
                conn.commit()
                c.close()


                return render_template('test.html', hours = round(total_hours,3), name=employees[ssn]['first_name'])
            

        elif request.method == 'GET':
            return f"The URL is accessed directly. Try going to '/login' to login"

    except Exception as e:
        # e holds description of the error
        error_text = '<p>The error:<br>' + str(e) + '</p>'
        hed = '<h1>Something is broken.</h1>'
        return hed + error_text 



if __name__ == '__main__':
    app.run(debug=True)