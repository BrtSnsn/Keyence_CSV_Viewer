import streamlit as st
import pandas as pd
import re
from io import BytesIO
# import numpy as np
import plotly.express as px
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource

st.set_page_config(
    page_title="Keyence quick loadout",
    page_icon="🎁",
    layout="wide",
    # initial_sidebar_state='auto'
)
df_result = pd.DataFrame([])
makeupdf = pd.DataFrame([])

config = {'displayModeBar': True}

datafr = st.checkbox('interactieve dataframe? --> als dit te groot is dan kost dit veel geheugen')
extra = st.checkbox('grafieken? -> zouden altijd ok moeten zijn tenzij in combo met bovenstaande dataframe')

selector_slot = st.empty()
c1, c2 = st.columns(2)

graph_slot = c1.empty()

selector2_slot = c2.empty()
graph2_slot = c2.empty()

msgbox = st.container()

csv = st.file_uploader("Drag & Drop keyence csv file", type={"csv"})

if csv is not None:
        # lees de csv file in
        df = pd.read_csv(csv, sep=';', decimal=',', dtype={'Lot No.': object})

        df.drop(df.loc[df['Judgment'] == 'Fail'].index, inplace=True)
        df.reset_index(inplace=True, drop=True)
        df.loc[:, 'Lot No.'] = df.loc[:, 'Lot No.'].astype(str)
        
        # zet de angle waarden (graden) om in een simpel decimaal getal
        def minutes_to_midnight(anglestring):
            deg, minutes, seconds, _ = re.split('[dms]', anglestring)
            return float(deg) + float(minutes) / 60 + float(seconds) / (60 * 60)

        # Waar de column header start met ANGLE -> graden omzetten via angle omzetting
        for eachcol in [c for c in df.columns if c[:5] == "ANGLE"]:
            df.loc[:, eachcol] = df.loc[:, eachcol].apply(minutes_to_midnight)

        # check of de datum&tijd ingegeven is in een bepaalde kolom
        # niet meer nodig als de QR code scan in orde is
        df_tol = df.iloc[0:3, :]
        df = df[df.iloc[:, 3].str.startswith(('os', 'nos'), na=False)]


        df = df.dropna(subset=['Measurement time', 'Serial Counter'], thresh=2)
        df = df.dropna(thresh=8)
        df = df.drop_duplicates(subset='Serial Counter', keep='last').reset_index(drop=True)
        
        df_time = df.iloc[:, 3]
        df_time = df_time.dropna()

        # Voeg datetime & osnos toe aan de originele dataframe
        try:
            # df_tol.loc[:, 'Serial Counter'] = ['Design', 'Upper', 'Lower']
            df_tol.loc[:, 'Serial Counter'] = ['0101991200', '0101991201', '0101991202']
            df_result = pd.concat([df_tol, df], axis=0)
            df_result.reset_index(inplace=True, drop=True)
            df_result = df_result.loc[:, ~df_result.columns.isin(['Program name', 'Measurement time', 'Lot No.', 'Judgment', 'Name', 'Number '])]
            df_result.set_index('Serial Counter', inplace=True)


            def makeuphelper(x):
                formatlist = []
                for i,v in enumerate(x):
                    # print(x.iloc[0], x.iloc[1])
                    upper = x.iloc[0] + x.iloc[1]
                    lower = x.iloc[0] + x.iloc[2]
                    # print(upper.type())
                    if i >= 3:
                        if float(v) > float(upper):
                            formatlist.append("background-color: #db9d39")
                        elif float(v) < float(lower):
                            formatlist.append("background-color: #0083b3")
                        else:
                            formatlist.append("background-color: #f2f1f0")
                    else:
                        formatlist.append("background-color: #c9c8c5")
                return formatlist

            makeupdf = df_result.style.apply(makeuphelper)

            if datafr:
                st.dataframe(makeupdf)

            if extra:
                dfcopy = df_result.copy()
                datestring = makeupdf.index.astype(str).str[-10:]
                dfcopy.loc[:, 'DateTime'] = pd.to_datetime(datestring, format='%d%m%y%H%M', dayfirst=True)
                dfcopy.loc[:, 'OsNos'] = makeupdf.index.astype(str).str[:-10]

                ff = pd.MultiIndex.from_frame(dfcopy.loc[:, ['DateTime', 'OsNos']])
                # dfcopy = dfcopy.
                # st.write(datestring)
                # dfcopy = dfcopy.set_index(dfcopy.loc[:, 'DateTime'])
                dfcopy = dfcopy.set_index(ff).sort_index(ascending=True).reset_index(drop=True)
                dfcopy = dfcopy.drop('DateTime', axis=1)
                dfcopy = dfcopy.drop('OsNos', axis=1)
                dfcopy = dfcopy.iloc[3:, :]
                # st.write(dfcopy)
                # st.write(ff)


                selector = selector_slot.selectbox('kies boxplot', dfcopy.columns)

                with graph2_slot:
                # with graph_slot.form('dfdf'):
                    fig = px.box(
                    data_frame=dfcopy,
                    x = selector,
                    title='this is your keyence data',
                    points='all'
                    # markers='.'
                    # template='plotly_white'
                        )
                    st.plotly_chart(fig, use_container_width=True)
                    # st.form_submit_button('update this graph')

                st.write(dfcopy)
                with graph_slot:
                # with graph_slot.form('dfdf'):
                    # selector = st.selectbox('kies boxplot', dfcopy.columns)

            #     fig = px.line(
            #     data_frame=df_result.iloc[3:, :],
            #     y = selector,
            #     markers='.'
            #     # template='plotly_white'
            #         )
            #     st.plotly_chart(fig, use_container_width=True)
                    source = ColumnDataSource(data=dfcopy)
                    # st.write(source)

                    TOOLTIPS = [
                        ("index", "$index"),
                        ("(x,y)", "($x, $y)"),
                        ]

                    p = figure(
                        title='simple line example',
                        # x_axis_label='x',
                        y_axis_label='value',
                        tooltips=TOOLTIPS)
                    
                    p.line(x='index', y=selector, source=source, line_width=2)
                    # p.line(x='index', y='CT02', source=source, line_width=2)

                    st.bokeh_chart(p, use_container_width=True)

                    # st.form_submit_button('update this graph')

        except Exception as e:
            msgbox.write(e)
            msgbox.write('Dit is de laatste dataframe die wel werkte')
            msgbox.write(df_result)

if csv:
    @st.cache
    def to_excel(df):
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, index=True, sheet_name='Sheet1')
        writer.save()
        processed_data = output.getvalue()
        return processed_data

    # df_xlsx = to_excel(makeupdf)
    st.download_button(label='📥 Download Current Result as .xlsx',
                                    data=to_excel(makeupdf) ,
                                    file_name= f'{csv.name[:-4]}_colored.xlsx',
                                    mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
