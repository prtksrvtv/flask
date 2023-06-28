from flask import Flask, render_template, request, redirect, url_for
from flask_mail import Mail, Message
from numtoword import number_to_word
from db_processor import *
import sqlite3 as sql
from date_format_change import *
import pandas as pd
from email.mime.text import MIMEText
from pretty_html_table import build_table

app = Flask(__name__)
mail = Mail(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'prateeksrivastava9@gmail.com'
app.config['MAIL_PASSWORD'] = 'wkygpbmrekiknxzw'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)


def db_connect():
    con = sql.connect('prikaway.db')
    cur = con.cursor()
    return cur

@app.route('/', methods = ['POST', 'GET'])
def auth():
   error=None
   if request.method == 'POST':
      if request.form['username']!='rukaifu@gmail.com' or request.form['password']!='12345':
         error = 'Invalid Credentials. Please try again.'
      else:
         return redirect(url_for('homepage'))     
   return render_template('login.html', error=error)

@app.route('/homepage')
def homepage():
   return render_template('homepage.html')
   

@app.route('/input', methods = ['POST', 'GET'])
def input ():
   cur=db_connect()
   cur.execute("select item_name from products")
   y=z=[]
   for rows in cur.fetchall():
      y.append(rows[0])  
   return render_template('student_invoice_input_template.html', items=y)

@app.route('/output',methods = ['POST', 'GET'])
def output():
   if request.method == 'POST':
      out = request.form.to_dict()
      global sync
      output=input_template_process(out)
      output['Date']=change_date_format(output['Date'])
      sync=output
      return render_template("student_invoice_output_template.html",output = output)
   
@app.route('/print_invoice',methods = ['POST', 'GET'])
def print_invoice():
   if request.method == 'POST':
      output=sync
      output['Invoice No.']= db_injector(output)
      df=pd.DataFrame.from_dict(output)
      msg = Message(
                output['Invoice No.'],
                sender ='Tera BAAP',
                recipients = ['cc.prikaway@gmail.com']
               )
      
      msg.body = " Please see the details below."
      msg.html = render_template("student_invoice_print_template.html", output=output)
      mail.send(msg)
      return render_template("student_invoice_print_template.html",output = output)
   
def input_template_process(out):
    cur=db_connect()
    cur.execute("select * from products")
    rows=cur.fetchall()
    ter={}
    s=0
    for x in out.keys():
       if x not in ['Name','Class','Roll No.', 'Date', 'House']:
          if out[x]=='':
             continue
          for y in rows:
             if x==y[1]:
                ter[x]=([int(out[x]),y[2],int(out[x])*y[2]])
                s+=int(out[x])*y[2]
       else:
          ter[x]=out[x]
    ter['Grand Total']=s
    ter['Word Amount']=number_to_word(s)
    return(ter)

if __name__ == '__main__':
   app.run(debug = True)