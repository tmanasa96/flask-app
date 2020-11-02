import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename

from flask_jsonpify import jsonpify

from io import StringIO

from docx import Document
from docx.shared import Inches

from keras.models import Model

import json

import fitz
import pandas as pd
import re
from operator import itemgetter
import numpy as np

import pickle
import tensorflow as tf
        

__author__ = 'ibininja'


model = pickle.load(open('kmeans22.pkl','rb'))

UPLOAD_FOLDER = 'templates'
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["ALLOWED_FILE_EXTENSIONS"] = ["PDF"]

#new_dataf = pd.read_csv('newf27_10.csv')

def kmeans(labels,new_df,text): #new_df from encoder and text from pre_pro
    new_df['KMeans_cluster'] = labels
     #clustered_data.head(50)
        
    new_df["KMeans_cluster"].replace({1: 3}, inplace=True)
    new_df["KMeans_cluster"].replace({2: 1}, inplace=True)
    new_df["KMeans_cluster"].replace({0: 2}, inplace=True)
  
    final_df = text[["LineText"]]
    final_df["Label"] =  new_df["KMeans_cluster"]

    return final_df

def segmentation(clustered_Data):
        header_list = [] # list containing only headers/footers and other lines
        paraLines_list = pd.DataFrame(columns=['text','label'])
        for i in range(len(clustered_Data)) : 
  # appening the headers and footers to a list
              if clustered_Data.loc[i, "Label"] ==  3:
               header_list.append(clustered_Data.loc[i, "LineText"])
              else:
    # rest of the lines to another list(first and regular lines)
                paraLines_list = paraLines_list.append({'text': clustered_Data.loc[i, "LineText"], 'label': clustered_Data.loc[i, "Label"]}, ignore_index=True)
        count_para = -1 # paragraphs counters starts from -1 
        new_list = pd.DataFrame(columns=['text','counter'])
        for i in range(len(paraLines_list)) :  
             if paraLines_list.loc[i, "label"] ==  1:
                    count_para += 1 # incrementing the counter once it encounters the first line(starts from zero)
                    new_list = new_list.append({'text': '', 'counter': count_para}, ignore_index=True) # appending the newline or empty string once the first line is encountered
                    new_list = new_list.append({'text': paraLines_list.loc[i, "text"], 'counter': count_para}, ignore_index=True)
             else:
                   new_list = new_list.append({'text': paraLines_list.loc[i, "text"], 'counter': count_para}, ignore_index=True)


        paragraphs = [] # new list for storing the paragraphs
        no_of_paragraphs = new_list['counter'].unique() # storing the count of # of pragraphs
        for j in range(len(no_of_paragraphs)): # looping through the each para number
            for k in range(len(new_list)) : #looping through the paragraphs list with counter 
                if new_list.loc[k, "counter"] == no_of_paragraphs[j]:
                    paragraphs.append(new_list.loc[k, "text"])
        return paragraphs

def allowed_filetype(filename):

    # We only want files with a . in the filename
    if not "." in filename:
        return False

    # Split the extension from the filename
    ext = filename.rsplit(".", 1)[1]

    # Check if the extension is in ALLOWED_FILE_EXTENSIONS
    if ext.upper() in app.config["ALLOWED_FILE_EXTENSIONS"]:
        return True
    else:
        return False

@app.route('/')
def index():
    return render_template('upload.html')



@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == "POST":
        
         if request.files:
                
            file = request.files['inputFile'] 
             
            #print(file)
            
            
            if file.filename == "":
                
                print("No file is uploded please uplode a file")
            
                return render_template('upload.html')
        
            if allowed_filetype(file.filename):
            
                filename = secure_filename(file.filename)
                
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'x_test.PDF'))
                
                doc = fitz.open(UPLOAD_FOLDER+"/x_test.PDF")

                

                font_counts = {}

                for page_num in range(0,doc.pageCount):
                     blocks = doc[page_num].getText("dict")["blocks"]
                     for b in blocks:  # iterate through the text blocks
                         if b['type'] == 0:
                            for l in b["lines"]:  # iterate through the text lines
                                for s in l["spans"]:  # iterate through the text spans
                                    identifier = "{0}^{1}^{2}^{3}".format(page_num, s['size'], s['flags'], s['font'])
                                    font_counts[identifier] = font_counts.get(identifier, 0) + 1  # count the fonts usag
                    
                font_counts = sorted(font_counts.items(), key=itemgetter(1), reverse=True)

# Extracting Most Used font and size combo in each page

                total_read=0

                mst_usd_pg_fnt = []

                for page_num in range(0,doc.pageCount):
                    flg=False
                    for itm in font_counts:
                        if int(itm[0].split("^")[0]) == page_num and flg == False:
                            mst_usd_pg_fnt.append(itm[0])
                            flg=True


                number_of_pages = doc.pageCount

                df = pd.DataFrame(columns=['LineText','BlockwiseNumber','VerticalSpaceLength','IsHorizontalTab','IsStartCap','IsEndDot','IsStartSpace','NormSize',
                                       'DocPageNumber','FontWeight','LineLength','LineIdentifier','identifier'])
                def flags_decomposer(flags):
                     """Make font flags human readable."""
                     l = 0
   
                     if flags & 2 ** 1:
                         l = 1
 
                     if flags & 2 ** 4:
                         l = 2
        
                     return l

            for page_number in range(number_of_pages):
                page = doc.loadPage(page_number)
                blocks = page.getText("dict")["blocks"]#rawdict")
                lists={}
                previous_id=''
                previous_text=''
                vertical_line_length=0.0
                p_space=0.0
                lists=[]
                count=0
                prev_blocknum=0.00
                prev_bbox3num=0.00
    
                for b in blocks:
                    block_num = b["bbox"][3]
                    if b['type'] == 0:
        
                       for idx,l in enumerate(b["lines"]):
               
                            for s in l["spans"]:
                                if s["text"].startswith(' ') == True:#not required starts with
                                    a_space=1
                                else:
                                    a_space=0
                     
                                if re.match(r'[ \t]',s["text"]) == True:
                                     a_horizontaltab=1
                                else:
                                     a_horizontaltab=0
                
                                if(idx==previous_id) and (idx!=0) and (previous_id!=0):
                                    s["text"]=previous_text + s["text"]
                    
                                v_len=s["bbox"][3]-vertical_line_length
                
                                append=0
                                if(idx==previous_id) and ((s["bbox"][3]-vertical_line_length)<0 and (s["bbox"][3]-vertical_line_length)>-1) :
                                    if previous_text not in s["text"]:
                                        s["text"]=previous_text + s["text"]

                                startchar=s["text"].replace("'", "")
            
                                startchar=startchar.strip('"')
                                startchar=startchar.strip()
               
                                if startchar[:1].isupper():#not required starts with
                                    startcaps=1
                                else:
                                    startcaps=0
                                if startchar[:1].isdigit():
                                    start_digit=1
                                else:
                                    start_digit=0

                                if startchar[:1] == '*':
                                    start_asterisk=1
                                else:
                                    start_asterisk=0

                                if startchar[:1] == '"':
                                    start_parenthesis=1
                                else:
                                    start_parenthesis=0

                                if s["text"].strip().endswith('.') == True:#not required starts with
                                    endwithdot=1
                                else:
                                    endwithdot=0
                                if len(s["text"])>1:
                                    size= s["size"]
                                else:
                                    size=0
                    
                                if len(s["text"])>1:
                                    flags=flags_decomposer(s["flags"])
                                else:
                                    flags =''
                    
                                lists.append([page_number,previous_id,idx,previous_text,s["text"],v_len,startcaps,endwithdot,a_space,
                                              a_horizontaltab,size,flags,"{0}^{1}^{2}^{3}´{4}".format(page_number, s['size'], s['flags'], s['font'], s['bbox']),start_digit,start_asterisk,start_parenthesis,s['bbox'][3],
                                              block_num])
                                if  len(s["text"].strip())>0: #and (s["bbox"][3]
                                    vertical_line_length=s["bbox"][3]
  
                                if  len(s["text"].strip())>0:
                                    p_space=v_len#s["bbox"][3]-vertical_line_length

                                previous_id=idx
                
                                previous_text=s["text"] 
                                prev_bbox3num=s['bbox'][3]
                                prev_blocknum=block_num
                                # print(block_num)
    

                vertical_len_pre=0.0

                final_list=[]
 
                dupl = []
                for index,x in enumerate(lists):
        
                     if x[4] not in dupl:
            
                        a_row=pd.Series([x[4],x[2],x[5],x[9],x[6],x[7],x[8],x[10],x[0],x[11],len(x[4]),x[12],x[13],x[14],x[15],x[16],x[17]],
                                          index=['LineText','BlockwiseNumber','VerticalSpaceLength','IsHorizontalTab','IsStartCap','IsEndDot','IsStartSpace','NormSize',
                                          'DocPageNumber','FontWeight','LineLength','LineIdentifier','start_digit','start_asterisk','start_parenthesis','sbox3','blocknum'])
                        row_df = pd.DataFrame([a_row])
                        df=df.append(row_df)

    


            df['Identifier'] =df.index+1

            df['LineText'].replace(' ', np.nan, inplace=True)
            df.dropna(subset=['LineText'], inplace=True)
            df[['Label','LineBoundingBox']] = df.LineIdentifier.str.split("´",expand=True)
            df['LineBoundingBox'] = df['LineBoundingBox'].str.replace('(','')
            df['LineBoundingBox'] = df['LineBoundingBox'].str.replace(')','')
            df[['LtoR','DtoU','RtoL','UtoD']] = df.LineBoundingBox.str.split(",",expand=True)

            df['LtoR'] = df['LtoR'].astype(float)
            df['DtoU'] = df['DtoU'].astype(float)
            df['UtoD'] = df['UtoD'].astype(float)
            df['RtoL'] = df['RtoL'].astype(float)


            df['DtoU_last']=""
            df['DtoU_next']=""
            df['LtoR_last']=""
            df['LtoR_next']=""
            df['RtoL_last']=""
            df['RtoL_next']=""
            df['UtoD_next']=""
            df['UtoD_last']=""

            for i in range(len(df)):
                if i<len(df)-1:
                      df['LtoR_next'].values[i]=df['LtoR'].values[i+1] - df['LtoR'].values[i]
                      df['UtoD_next'].values[i]=df['UtoD'].values[i+1] - df['UtoD'].values[i]
                      df['DtoU_next'].values[i]=df['DtoU'].values[i+1] - df['DtoU'].values[i]
                      df['RtoL_next'].values[i]=df['RtoL'].values[i+1] - df['RtoL'].values[i]
                if i!=0 :
                      df['DtoU_last'].values[i]=df['DtoU'].values[i] - df['DtoU'].values[i-1]
                      df['LtoR_last'].values[i]=df['LtoR'].values[i] - df['LtoR'].values[i-1]
                      df['RtoL_last'].values[i]=df['RtoL'].values[i] - df['RtoL'].values[i-1]
                      df['UtoD_last'].values[i]=df['UtoD'].values[i] - df['UtoD'].values[i-1]

            df['LtoR']=pd.to_numeric(df['LtoR'].fillna(0))
            df['DtoU']=pd.to_numeric(df['DtoU'].fillna(0))
            df['RtoL']=pd.to_numeric(df['RtoL'].fillna(0))   
            df['UtoD']=pd.to_numeric(df['UtoD'].fillna(0))
            df['LtoR_last']=pd.to_numeric(df['LtoR_last'].fillna(0))
            df['LtoR_next']=pd.to_numeric(df['LtoR_next'].fillna(0))
            df['DtoU_next']=pd.to_numeric(df['DtoU_next'].fillna(0))
            df['DtoU_last']=pd.to_numeric(df['DtoU_last'].fillna(0))
            df['UtoD_last']=pd.to_numeric(df['UtoD_last'].fillna(0))
            df['UtoD_next']=pd.to_numeric(df['UtoD_next'].fillna(0))
            df['RtoL_last']=pd.to_numeric(df['RtoL_last'].fillna(0))
            df['RtoL_next']=pd.to_numeric(df['RtoL_next'].fillna(0))




            df['FontWeight'] = df['FontWeight'].fillna(0)




            #calculate min and max
            min_LtoR = np.min(df['LtoR'])
            min_DtoU = np.min(df['DtoU'])
            min_UtoD = np.min(df['UtoD'])
            min_RtoL = np.min(df['RtoL'])
            min_LtoR_last=np.min(df['LtoR_last'])
            min_LtoR_next=np.min(df['LtoR_next'])
            min_DtoU_next=np.min(df['DtoU_next'])
            min_DtoU_last=np.min(df['DtoU_last'])
            min_UtoD_last=np.min(df['UtoD_last'])
            min_UtoD_next=np.min(df['UtoD_next'])
            min_RtoL_last=np.min(df['RtoL_last'])
            min_RtoL_next=np.min(df['RtoL_next'])
            min_ver_length= np.min(df['VerticalSpaceLength'])


            max_LtoR= np.max(df['LtoR'])
            max_DtoU=np.max(df['DtoU'])
            max_UtoD=np.max(df['UtoD'])
            max_RtoL=np.max(df['RtoL'])
            max_LtoR_last=np.max(df['LtoR_last'])
            max_LtoR_next=np.max(df['LtoR_next'])
            max_DtoU_last=np.max(df['DtoU_last'])
            max_DtoU_next=np.max(df['DtoU_next'])
            max_UtoD_last=np.max(df['UtoD_last'])
            max_UtoD_next=np.max(df['UtoD_next'])
            max_RtoL_last=np.max(df['RtoL_last'])
            max_RtoL_next=np.max(df['RtoL_next'])
            max_ver_length= np.max(df['VerticalSpaceLength'])
            min_normsize=np.min(df['NormSize'])
            max_normsize=np.max(df['NormSize'])

            df['FontWeight'] = df['FontWeight'].fillna(0.00)

            df.loc[df['BlockwiseNumber'] > 1, 'BlockwiseNumber'] = 1

            def numberofcaps(df):
                no_of_caps = sum(1 for c in df['LineText'] if c.isupper())
                return no_of_caps

            def numberofcommas(df):
                no_of_commas = sum(1 for c in df['LineText'].strip() if c == ',')
                return no_of_commas

            def endwithcomma(df):
                endswithcomma = 0
                if df['LineText'].strip().endswith(',') == True:
                     endswithcomma = 1
                return endswithcomma

# message= "In contrast to possible Changes In the National context"
            df['Num_of_caps'] = df.apply (lambda row: numberofcaps(row), axis=1)
            df['Ends_with_comma'] = df.apply (lambda row: endwithcomma(row), axis=1)
            df['Number_of_commas'] = df.apply (lambda row: numberofcommas(row), axis=1)

            min_Num_of_caps=np.min(df['Num_of_caps'])
            max_Num_of_caps=np.max(df['Num_of_caps'])

            min_Number_of_commas=np.min(df['Number_of_commas'])
            max_Number_of_commas=np.max(df['Number_of_commas'])


            min_LineLength=np.min(df['LineLength'])
            max_LineLength=np.max(df['LineLength'])

#removed minmax for few columns as values are going to e power values and effectig autoencoder

            for i in range(len(df)):
              #  i = j+1
              df['LtoR'].values[i]=(df['LtoR'].values[i] - min_LtoR) / (max_LtoR - min_LtoR)
              df['DtoU'].values[i]=(df['DtoU'].values[i] - min_DtoU) / (max_DtoU - min_DtoU)
              df['UtoD'].values[i]=(df['UtoD'].values[i] - min_UtoD) / (max_UtoD - min_UtoD)
              df['RtoL'].values[i]=(df['RtoL'].values[i]  - min_RtoL) / (max_RtoL - min_RtoL)
              df['LineLength'].values[i]=((df['LineLength'].values[i]  - min_LineLength) / (max_LineLength - min_LineLength))
              df['LtoR_last'].values[i]=(df['LtoR_last'].values[i] - min_LtoR_last) / (max_LtoR_last - min_LtoR_last)
              df['LtoR_next'].values[i]=(df['LtoR_next'].values[i] - min_LtoR_next) / (max_LtoR_next - min_LtoR_next)
              df['DtoU_last'].values[i]=(df['DtoU_last'].values[i] - min_DtoU_last) / (max_DtoU_last - min_DtoU_last)
              df['DtoU_next'].values[i]=(df['DtoU_next'].values[i] - min_DtoU_next) / (max_DtoU_next - min_DtoU_next)
              df['UtoD_last'].values[i]=(df['UtoD_last'].values[i] - min_UtoD_last) / (max_UtoD_last - min_UtoD_last)
              df['UtoD_next'].values[i]=(df['UtoD_next'].values[i] - min_UtoD_next) / (max_UtoD_next - min_UtoD_next)
              df['RtoL_last'].values[i]=(df['RtoL_last'].values[i] - min_RtoL_last) / (max_RtoL_last - min_RtoL_last)
              df['RtoL_next'].values[i]=(df['RtoL_next'].values[i] - min_RtoL_next) / (max_RtoL_next - min_RtoL_next)
              df['VerticalSpaceLength'].values[i]=((df['VerticalSpaceLength'].values[i]  - min_ver_length) / (max_ver_length - min_ver_length))
              df['NormSize'].values[i]=((df['NormSize'].values[i]  - min_normsize) / (max_normsize - min_normsize))
              df['Number_of_commas'].values[i]=((df['Number_of_commas'].values[i]  - min_Number_of_commas) / (max_Number_of_commas - min_Number_of_commas))
              df['Num_of_caps'].values[i]=((df['Num_of_caps'].values[i]  - min_Num_of_caps) / (max_Num_of_caps - min_Num_of_caps))




            #Calculate Median 
            median_LtoR_next= df['LtoR_next'].median()
            median_LtoR_last= df['LtoR_last'].median()
            median_DtoU_next= df['DtoU_next'].median()
            median_DtoU_last= df['DtoU_last'].median()
            median_UtoD_last= df['UtoD_last'].median()
            median_UtoD_next= df['UtoD_next'].median()
            median_RtoL_last= df['RtoL_last'].median()
            median_RtoL_next= df['RtoL_next'].median()
            median_Number_of_commas= df['Number_of_commas'].median()
            median_Num_of_caps= df['Num_of_caps'].median()

 

            for i in range(len(df)):
                if df['LtoR_last'].values[i]<0:
                    df['LtoR_last'].values[i]=median_LtoR_last
            
                if df['LtoR_next'].values[i]<0:
                    df['LtoR_next'].values[i]=median_LtoR_next
        
                if df['DtoU_next'].values[i]<0:
                    df['DtoU_next'].values[i]=median_DtoU_next
 
                if df['DtoU_last'].values[i]<0:
                    df['DtoU_last'].values[i]=median_DtoU_last
           
                if df['UtoD_last'].values[i]<0:
                    df['UtoD_last'].values[i]=median_UtoD_last
         
                if df['UtoD_next'].values[i]<0:
                    df['UtoD_next'].values[i]=median_UtoD_next
        
                if df['RtoL_last'].values[i]<0:
                    df['RtoL_last'].values[i]=median_RtoL_last

                if df['RtoL_next'].values[i]<0:
                     df['RtoL_next'].values[i]=median_RtoL_next     
        
                if df['Number_of_commas'].values[i]<0:
                     df['Number_of_commas'].values[i]=median_Number_of_commas
  
                if df['Num_of_caps'].values[i]<0:
                     df['Num_of_caps'].values[i]=median_Num_of_caps
   

 
            df.reset_index(level=0, inplace=True) 
 
            df= df.fillna(0)



            df['Identifier'] = df.index+1

   
            text_length=15 

            df_features = df[['Identifier','LineText','BlockwiseNumber', 'VerticalSpaceLength','IsStartCap', 'IsEndDot', 'IsStartSpace','NormSize',
                       'FontWeight', 'LineLength','start_digit', 'start_asterisk', 'start_parenthesis','LtoR', 'DtoU', 'RtoL', 'UtoD', 'DtoU_last',
                        'DtoU_next', 'LtoR_last', 'LtoR_next', 'RtoL_last', 'RtoL_next', 'UtoD_next', 'UtoD_last','Num_of_caps','Ends_with_comma','Number_of_commas']]
            text =  df_features[["LineText"]]

            

            df_final =   df_features[['Identifier','LineText']]
 
            df_features_enc = df_features.drop(columns=['Identifier','LineText','BlockwiseNumber','LtoR', 'RtoL','DtoU', 'UtoD','RtoL_last','RtoL_next','DtoU_last','UtoD_last'])
            
            autoencoder= tf.keras.models.load_model('autoencoder_large.hdf5')  #loading autoencoder

            encoder = Model(autoencoder.input, autoencoder.layers[3].output)            

            encoded_train = pd.DataFrame(encoder.predict( df_features_enc))  
  
            encoded_train = encoded_train.add_prefix('feature_')   

            encoded_train_df = pd.DataFrame(data=encoded_train, columns=['feature_0', 'feature_1', 'feature_2','feature_3','feature_4'])      

            data = encoded_train_df.fillna(0) 

            #new_df = pd.DataFrame(data=encoded_train)

            

            with open('kmeans22.pkl', 'rb') as f:
                     model = pickle.load(f)
            model.fit(data)

            cluster_label = model.predict(data)
                
            rturn = kmeans(cluster_label, df_final,text)
                
            segmented = segmentation(rturn)

            return json.dumps(segmented)
                 
            #document = Document()

            #for i in  segmented:

                #document.add_paragraph(segmented)
   
            #f = open(document, "r")

            #document_seg = f.read()

 
            
     
            #f = StringIO()
               
            #document.save(f)
   
            #length = f.tell()
 
            #f.seek(0)
            
            #return send_file(f, as_attachment=True, attachment_filename='segmentation.doc')
            #cluster_data = kmeans(cluster_label,df_final,text)
 
       #return render_template("download.html", text= document_seg)
             


            #json_data =  rturn.to_json(orient='values')
            #return jsonpify(json_data)

    else:             
        return "this file type is not allowed"
            
          
#app.route('/download', methods=["GET"])
#df download():
#n send_file(word)

if __name__ == '__main__':
    app.run(debug=True)