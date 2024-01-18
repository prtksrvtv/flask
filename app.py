from flask import Flask, render_template, request, redirect, url_for, session
from flask_mail import Mail, Message
from db_processor import *
from date_format_change import *
from process_format import *
from flask_session import Session
from datetime import timedelta
from dotenv import load_dotenv
import os
import json
import requests


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY']=os.environ['SECRET_KEY']
app.config["SESSION_TYPE"] = "filesystem"
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

Session(app)

@app.route('/', methods = ['POST', 'GET'])
def auth():
   error=None
   if request.method == 'POST':
      result=request.form.to_dict()
      result=db_auth(result)
      for x in result:
         session[x]=result[x]
      if result['flag'] == False:
         error = 'Invalid Credentials. Please try again.'
      else:
         ping="user " + session['username']+ " logged in"
         requests.post(os.environ['TELEGRAM_MESSENGER'], json=json.dumps(ping))
         return redirect(url_for('homepage'))     
   return render_template('login.html', error=error)

@app.route('/homepage')
def homepage():
   return render_template('homepage.html', sync_user=session)

@app.route('/logout')
def logout():
   ping="user " + session['username']+ " logged out"
   requests.post(os.environ['TELEGRAM_MESSENGER'], json=json.dumps(ping))
   session.pop('username',None)
   return redirect(url_for('auth'))

@app.route('/input', methods = ['POST', 'GET'])
def input ():
   #set flag key in session list to None
   session['flag']=None
   #house search API call
   response = requests.get("http://127.1.1.1:8080/db_house_search", params={'school_id':session['school_id']})
   #converting to dictionary
   dictr = response.json()
   #converting to list
   house_list=list(dictr['house_name'].values())
   #product search API call
   response = requests.get("http://127.1.1.1:8080/db_product_search", params={'school_id':session['school_id']})
   #converting to diction
   dictr = response.json()
   #converting to list
   product_list=list(dictr['product_price'].keys())
   #rendering template
   return render_template('student_invoice_input_template.html', items=product_list, house=house_list)

@app.route('/output',methods = ['POST', 'GET'])
def output():
   if request.method == 'POST':
      out = request.form.to_dict()
      global sync
      output=input_template_process(out, session['school_id'])
      sync=output
      return render_template("student_invoice_output_template.html",output = output, image=session['img_url'])
   
@app.route('/print_invoice',methods = ['POST', 'GET'])
def print_invoice():
   if request.method == 'POST':
      output=sync
      if session['flag'] is not None:
         action="EDITED"
         db_delete_invoice(session['flag'])
      else:
         action="GENERATED"
      #save student invoice details API call
      merge_dict={}
      header={}
      products={}
      merge_dict['session']=session
      for x in output.keys():
         if x in ['Roll No.','Name','Class','House','Date', 'Grand Total', 'Word Amount', 'Item Total']:
            header[x]=output[x]
         else:
            products[x]=output[x]
      merge_dict['header']= header
      merge_dict['products']= products
      merge_dict['products']={k:v for k,v in merge_dict['products'].items() if v}
      json_output=json.dumps(merge_dict, indent=4, default=str)
      response = requests.post("http://127.1.1.1:8080/db_save_student_invoice", json=json_output)
      output['Invoice No.']= response.json()
      output['Date']=change_date_format(output['Date'])
      output=output_template_format(output)
      ping="STUDENT INVOICE "+action+ "\nSCHOOL NAME: "+ session['school_name']+"\nINVOICE NO: "+ output['Invoice No.'] +"\n"+ action+ " BY USER: "+session['username']+"\n STUDENT NAME: "+ output['Name']+"\n CLASS: "+ output['Class']+"\n ROLL NO: " +output['Roll No.']+"\n HOUSE: "+ output['House']+"\n INVOICE DATE: " +output['Date']+"\n TOTAL ITEMS: "+ str(output['Item Total'])+"\n TOTAL AMOUNT: " +output['Grand Total']
      #call telegram messenger API
      requests.post(os.environ['TELEGRAM_MESSENGER'], json=json.dumps(ping))
      email_dict={} #email dict to be sent to email messenger api
      email_dict['img_url']=session['img_url']
      email_dict['output']=output
      email_dict['action']=action
      #call email messenger api
      requests.post(os.environ['STUDENT_INVOICE_EMAILER'], json=json.dumps(email_dict))
      return render_template("student_invoice_print_template.html",output = output, image=session['img_url'])
   
@app.route('/search_invoice',methods = ['POST', 'GET'])
def search_invoice():
      return render_template("search_invoice_input_template.html")
      
@app.route('/view_invoice',methods = ['POST', 'GET'])
def view_invoice():
   if request.method == 'POST':
      out = request.form.to_dict()
      #product search API call
      response = requests.get("http://127.1.1.1:8080/db_search_student_invoice", params={'inv_no':out['inv_no'], 'date_of_purchase':out['date_of_purchase']})
      respons=response.json()
      if respons['found'] == False:
         return render_template("student_invoice_not_found.html")
      else:
         respons_header=json.loads(respons['headers'])
         respons_products=json.loads(respons['products'])
         img_url=respons_header['img_url']
         response_products=pd.DataFrame(respons_products)
         response_products.index = pd.RangeIndex(start=1, stop=1+len(response_products), step=1)
         response_products.rename(columns={'product_name':'Product Name', 'size':'Product Size', 'item_quantity':'Item Quantity', 'product_price':'Unit Price', 'total_price':'Total Price'}, inplace=True)
         respons_header=pd.DataFrame(respons_header, columns=respons_header.keys())
         x=datetime.utcfromtimestamp(respons_header['date_of_purchase'][0]/1000)
         respons_header['date_of_purchase'][0] = x.date()
         respons_header['date_of_purchase'][0]=change_date_format(str(respons_header['date_of_purchase'][0])) 
         tc_leave=respons_header['tc_leave'][0]
         word_amount=respons_header['Word Amount'][0]
         word_amount=word_amount[0]
         respons_header.drop(respons_header.iloc[:,6:9], inplace=True, axis=1)
         respons_header.rename(columns={'student_name':'Name', 'class':'Class', 'roll_no':'Roll No.', 'date_of_purchase':'Purchase Date', 'house_name':'House', 'bill_no':'Invoice No.', 'item_quantity':'Total Items', 'total_price':'Total Price'}, inplace=True)
         return render_template("view_student_invoice_template copy.html", header=respons_header.to_html(classes='data', index=False, justify='center').replace('<th>','<th style = "background-color: rgb(173, 171, 171)">'), products=response_products.to_html(classes='data', justify='center').replace('<th>','<th style = "background-color: rgb(173, 171, 171)">'), word_amount=word_amount, tc_leave=tc_leave, image=img_url['0'])
         
@app.route('/principal_bill',methods=['POST','GET'])
def principal_bill():
   return render_template('principal_bill_input_template.html')

@app.route('/generate_bill',methods=['POST','GET'])
def generate_bill():
   if request.method == 'POST':
      out = request.form.to_dict()
      res=db_search(out, session['school_id'])
      result=school_pricipal_bill_process(res, session['school_code'])
      global sync_school_bill
      sync_school_bill=result
      return render_template('principal_bill_output_template.html', result=result, image=session['img_url'])

@app.route('/print_school_bill',methods=['POST','GET'])
def print_school_bill():
   if request.method == 'POST':
      result=sync_school_bill
      msg = Message(
                "BILL TO " +(session['school_name']).upper()+ " PRINCIPAL GENERATED# "+result['Invoice No.'],
                sender =os.environ['SENDER'],
                recipients = [os.environ['RECIPIENTS']]
               )
      msg.body = "Please see the details below."
      msg.html = render_template("pricipal_bill_print_template.html", result=result, image=session['img_url'])
      mail.send(msg)
      ping="BILL TO PRINCIPAL GENERATED"+"\nSCHOOL NAME: "+ session['school_name']+"\nINVOICE NO: "+ result['Invoice No.'] +"\n GENERATED BY USER: "+session['username']+"\n INVOICE DATE: " +result['Date']+"\n TOTAL ITEMS: "+ str(result['Item Total'])+"\n TOTAL AMOUNT: " +result['Grand Total']
      #send_message(ping)
      return render_template("pricipal_bill_print_template.html",result = result, image=session['img_url'])
   
@app.route('/cover_page_input', methods=['POST','GET'])
def cover_page_input():
   h=[]
   for rows in db_house_search(session['school_id']):
      h.append(rows[0])
   return render_template('cover_page_input.html', house=h)

@app.route('/confirm_cover_page', methods=['POST','GET'])
def confirm_cover_page():
   if request.method == 'POST':
      data = request.form.to_dict()
      if data['House'] == 'All':
         result=db_search_all_house_cover(data, session['school_id'])
         result=all_house_cover_process(result)
         result['House']='All'
      else:
         result=db_search_house_cover(data, session['school_id'])
         result=house_cover_process(result)
         result['House']=data['House']
      global sync_cover_data
      sync_cover_data=result
      return render_template("cover_page_house.html", result=result, image=session['img_url'])
   
@app.route('/print_house_cover_page',methods=['POST','GET'])
def print_house_cover_page():
   if request.method == 'POST':
      result=sync_cover_data
      msg = Message(
                "COVER PAGE TO SAINIK SCHOOL REWARI PRINCIPAL GENERATED# "+result['Invoice No.'],
                sender =os.environ['SENDER'],
                recipients = [os.environ['RECIPIENTS']]
               )
      msg.body = " Please see the details below."
      msg.html = render_template("cover_page_print.html", result=result, image=session['img_url'])
      mail.send(msg)
      ping="COVER PAGE GENERATED"+"\nSCHOOL NAME: "+ session['school_name']+"\n GENERATED BY USER: "+session['username']+"\n TOTAL ITEMS: "+ str(result['Item Total'])+"\n TOTAL AMOUNT: " +result['Grand Total']
      #send_message(ping)
      return render_template("cover_page_print.html",result = result, image=session['img_url'])

@app.route('/delete_invoice_input', methods=['POST', 'GET'])
def delete_invoice_input():
   return render_template("delete_invoice_input_template.html")

@app.route('/delete_invoice_confirmed', methods=['POST', 'GET'])
def delete_invoice_confirmed():
   if request.method == 'POST':
      data=request.form.to_dict()
      result= db_delete_invoice(data)
      if result=="S":
         msg = Message(
                "STUDENT INVOICE# "+data['inv_no']+ "DELETED",
                sender =os.environ['SENDER'],
                recipients = [os.environ['RECIPIENTS']]
               )
         msg.body = " Student Invoice has been deleted from the database. Please note that this action is irreversible and if it was done by mistake then a new invoice needs to be generated"
         mail.send(msg)
         result="INVOICE NO. "+data['inv_no']+"DELETED FROM DATABASE"
         ping=result+"\n DELETED BY USER: "+session['username']
         #send_message(ping)
         return render_template("delete_invoice_confirmed.html", result=result)
      if result=="NF":
         return render_template("student_invoice_not_found.html")

@app.route('/change_invoice_status_input', methods=['POST', 'GET'])
def change_invoice_status_input():
      return render_template("change_invoice_status_input.html")

@app.route('/change_invoice_status_confirmed', methods=['POST', 'GET'])
def change_invoice_status_confirmed():
   if request.method == 'POST':
      data=request.form.to_dict()
      result= db_change_invoice_status(data)
      if result=="S":
         msg = Message(
                "STUDENT INVOICE# "+data['bill_no']+ "SET AS TC/LEAVE "+str(data['tc_leave'])+ " IN THE DATABASE",
                sender =os.environ['SENDER'],
                recipients = [os.environ['RECIPIENTS']]
               )
         msg.body = " Student Invoice TC/Leave status has been changed"
         mail.send(msg)
         result="INVOICE NO. "+data['bill_no']+" MARKED AS TC/LEAVE "+str(data['tc_leave'])+ " IN THE DATABASE"
         #send_message(result+" BY USER "+session['username'])
         return render_template("change_invoice_status_confirmed.html", result=result)
      if result=="NF":
         result="INVOICE DOES NOT EXISTS IN DATABSE. CHECK DETAILS AND TRY AGAIN"
         return render_template("change_invoice_status_confirmed.html", result=result)

@app.route('/select_raashan_tender', methods=['POST', 'GET'])
def select_raashan_tender():
   return render_template('select_raashan_tender.html')

@app.route('/input_raashan_details', methods=['POST', 'GET'])
def input_raashan_details():
   if request.method == 'POST':
      data=request.form.to_dict()
      session['tender_no']=data['tender']
      items=db_raashan_product_search(data['tender'])
      return render_template('input_raashan_details.html', items=items)
   
@app.route('/confirm_raashan_details', methods=['POST', 'GET'])
def confirm_raashan_details():
   if request.method == 'POST':
      data=request.form.to_dict()
      result=check_raashan_details(data, session['tender_no'])
      global sync_raashan
      sync_raashan=result
      return render_template('confirm_raashan_details.html', result=result, image=session)

@app.route('/print_raashan_bill', methods=['POST', 'GET'])
def print_raashan_bill():
   if request.method == 'POST':
      result=sync_raashan
      save_raashan_line_items(result, session['tender_no'])
      result['start_date']=change_date_format(result['start_date'])
      result['end_date']=change_date_format(result['end_date'])
      result['inv_date']=change_date_format(result['inv_date'])
      msg = Message(
                "RAASHAN BILL TO SAINIK SCHOOL GOPALGANJ PRINCIPAL GENERATED# "+str(result['Invoice No.']),
                sender =os.environ['SENDER'],
                recipients = [os.environ['RECIPIENTS']]
               )
      msg.body = " Please see the details below."
      msg.html = render_template("print_raashan_bill.html", result=result, image=session)
      mail.send(msg)
      ping="RAASHAN BILL TO SAINIK SCHOOL GOPALGANJ PRINCIPAL GENERATED# "+"\nINVOICE NO: "+ str(result['Invoice No.']) +"\n GENERATED BY USER: "+session['username']+"\n TOTAL AMOUNT: " +str(result['Grand Total'])
      #send_message(ping)
      return render_template('print_raashan_bill.html', result=result, image=session)

@app.route('/analytics', methods=['POST','GET'])
def analytics():
   error=None
   if request.method == 'POST':
      data=request.form.to_dict()
      if data['otp'] == str(8092):
         return redirect(url_for('looker_dashboard'))
      else:
         error = 'Invalid Credentials. Please try again.'
   return render_template('enter_otp.html', error=error)

@app.route('/looker_dashboard', methods=['POST','GET'])
def looker_dashboard():
   return render_template('looker.html')

@app.route('/inventory_input', methods = ['POST', 'GET'])
def inventory_input ():
   y=[]
   for rows in db_product_search(session['school_id']):
      y.append(rows[1])
   return render_template('stock_input_template.html', items=y)

@app.route('/inventory_output',methods = ['POST', 'GET'])
def inventory_output():
   if request.method == 'POST':
      out = request.form.to_dict()
      output={}
      for x in out:
         if out[x] == '':
            continue
         else:   
            output[x]=out[x].split(",")
      stock_input(output,session['school_id'])
      msg = Message(
                "STOCK INPUT SUCCESSFUL",
                sender =os.environ['SENDER'],
                recipients = [os.environ['RECIPIENTS']]
               )
      ping="STOCK SUCCESSFULLY ENTERED \n BY USER: "+session['username']+"\n FOR SCHOOL: "+session['school_name']+"\n PLEASE READ IN THE FORMAT 'ITEM NAME':['SIZE:QUANTITY'] \n"+str(output)
      msg.body = ping
      mail.send(msg)
      #send_message(ping)
      return render_template("stock_input_success.html")

@app.route('/inventory_view',methods = ['POST', 'GET'])
def inventory_view():
   output=view_stock(session['school_id'])
   msg = Message(
                "INVENTORY VIEWED BY USER: "+session['username'],
                sender =os.environ['SENDER'],
                recipients = [os.environ['RECIPIENTS']]
               )
   ping="INVENTORY VIEWED BY USER: "+session['username']+'\n'+str(output)
   msg.body = ping
   mail.send(msg)
   send_message(ping)
   return render_template('stock_view_template.html', output=output, image=session['img_url'])

@app.route('/inventory_modify',methods = ['POST', 'GET'])
def inventory_modify():
   y=[]
   for rows in db_product_search(session['school_id']):
      y.append(rows[1])
   return render_template('stock_modify_template.html', items=y)

@app.route('/inventory_modify_task',methods = ['POST', 'GET'])
def inventory_modify_task():
   if request.method == 'POST':
      out = request.form.to_dict()
      output={}
      for x in out:
         if out[x] == '':
            continue
         else:   
            output[x]=out[x].split(",")
      stock_modify(output,session['school_id'])
      msg = Message(
                "STOCK MODIFY SUCCESSFUL",
                sender =os.environ['SENDER'],
                recipients = [os.environ['RECIPIENTS']]
               )
      ping="STOCK SUCCESSFULLY MODIFIED \n BY USER: "+session['username']+"\n FOR SCHOOL: "+session['school_name']+"\n PLEASE READ IN THE FORMAT 'ITEM NAME':['SIZE:QUANTITY'] \n"+str(output)
      msg.body = ping
      mail.send(msg)
      send_message(ping)
      return render_template("stock_input_success.html")

@app.route('/edit_invoice', methods=['POST', 'GET'])
def edit_invoice_input():
      return render_template("edit_invoice_input_template.html")

@app.route('/edit_invoice_details', methods=['POST', 'GET'])
def edit_invoice_details():
   if request.method == 'POST':
      out=request.form.to_dict()
      output=db_search_student_invoice(out)
      if output == 'NF':
         return render_template("student_invoice_not_found.html")
      else:
         h=[]
         y=[]
         for rows in db_house_search(session['school_id']):
            h.append(rows[0])
         for rows in db_product_search(session['school_id']):
            y.append(rows[1])
         session['flag']=out  
         return render_template("student_invoice_edit_template.html", out=output, items=y, house=h)

if __name__ == '__main__':
   app.run(debug = True)