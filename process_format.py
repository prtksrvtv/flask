from babel.numbers import format_currency
from datetime import date
import sqlite3 as sql
from numtoword import number_to_word
from date_format_change import *

def input_template_process(out):
    con = sql.connect('prikaway.db')
    cur = con.cursor()
    cur.execute("select * from products")
    rows=cur.fetchall()
    ter={}
    s=q=0
    for x in out.keys():
       if x not in ['Name','Class','Roll No.', 'Date', 'House']:
          if out[x]=='':
             continue
          for y in rows:
             if x==y[1]:
                ter[x]=([int(out[x]),y[2],int(out[x])*y[2]])
                s+=int(out[x])*y[2]
                q+=int(out[x])
       else:
          ter[x]=out[x]
    ter['Grand Total']=s
    ter['Item Total']=q
    ter['Word Amount']=number_to_word(s)
    return(ter)

def output_template_format(out):
    for x in out.keys():
       if x not in ['Name','Class','Roll No.', 'Date', 'House', 'Grand Total', 'Word Amount', 'Item Total','Invoice No.']:
         out[x][1]=format_currency(out[x][1], 'INR', format=u'#,##0\xa0¤', locale='en_IN', currency_digits=False)
         out[x][2]=format_currency(out[x][2], 'INR', format=u'#,##0\xa0¤', locale='en_IN', currency_digits=False)  
    out['Grand Total']=format_currency(out['Grand Total'], 'INR', format=u'#,##0\xa0¤', locale='en_IN', currency_digits=False)
    return(out)

def school_pricipal_bill_process(res):
   result={}
   s=q=0
   for x in res:
      result[x[0]]=([format_currency(x[1], 'INR', format=u'#,##0\xa0¤', locale='en_IN', currency_digits=False),x[2],format_currency(x[3], 'INR', format=u'#,##0\xa0¤', locale='en_IN', currency_digits=False)])      
      s=s+x[3]
      q=q+x[2]
   result['Date']=change_date_format(str(date.today()))
   result['Invoice No.']=str(abs(hash('PWPL/RW/'+str(date.today()))))
   result['Grand Total']=format_currency(s, 'INR', format=u'#,##0\xa0¤', locale='en_IN', currency_digits=False)
   result['Item Total']=q
   result['Word Amount']=number_to_word(s)
   return result
