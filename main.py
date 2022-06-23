import streamlit as st
import pandas as pd
import re
from io import BytesIO
# import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.transform import factor_cmap, factor_mark
import plotly.figure_factory as ffact

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
c1, c2, c3 = st.columns(3)

graph1_slot = c1.empty()
graph2_slot = c2.empty()
graph3_slot = c3.empty()

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
            df_result = df_result.loc[:, ~df_result.columns.isin(['Program name', 'Measurement time', 'Judgment', 'Name', 'Number '])]
            dfcopy = df_result.copy()
            df_result = df_result.loc[:, ~df_result.columns.isin(['Lot No.'])]
            df_result.set_index('Serial Counter', inplace=True)
            dfcopy.set_index('Serial Counter', inplace=True)


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
                datestring = makeupdf.index.astype(str).str[-10:]
                dfcopy.loc[:, 'DateTime'] = pd.to_datetime(datestring, format='%d%m%y%H%M', dayfirst=True)
                dfcopy.loc[:, 'OsNos'] = makeupdf.index.astype(str).str[:-10]

                ff = pd.MultiIndex.from_frame(dfcopy.loc[:, ['DateTime', 'OsNos', 'Lot No.']])
                # dfcopy = dfcopy.
                # st.write(dfcopy)
                # dfcopy = dfcopy.set_index(dfcopy.loc[:, 'DateTime'])
                dfcopy = dfcopy.set_index(ff).sort_index(ascending=True).reset_index(drop=True)
                # dfcopy = dfcopy.set_index(ff).sort_index(ascending=True)
                dfcopy = dfcopy.drop('DateTime', axis=1)
                dfcopy = dfcopy.drop('OsNos', axis=1)
                dfcopy = dfcopy.iloc[3:, :]
                # st.write(dfcopy)
                # st.write(ff)


                selector = selector_slot.selectbox('kies boxplot', dfcopy.columns[1:])

                mean = dfcopy.loc[:, selector].median()
                stdev = dfcopy.loc[:, selector].std()
                up = mean + 3 * stdev
                down = mean - 3 * stdev
                if down < 0:
                    down = 0

                with graph1_slot:
                    fig = px.box(
                    data_frame=dfcopy,
                    y = selector,
                    title=selector,
                    # facet_col='Lot No.',
                    color='Lot No.')
                    
                    fig.add_hline(y=mean, line_width=0.5, line_dash="dash", line_color="black", opacity=0.7)
                    fig.add_hline(y=up, line_width=1, line_dash="dash", line_color="red", opacity=0.7)
                    fig.add_hline(y=down, line_width=1, line_dash="dash", line_color="red", opacity=0.7)
                    st.plotly_chart(fig, use_container_width=True)

                with graph2_slot:
                    fig = px.line(
                        data_frame=dfcopy,
                        y = selector,
                        markers='.',
                        color='Lot No.',
                        title=selector)
                    fig.add_hline(y=mean, line_width=0.5, line_dash="dash", line_color="black", opacity=0.7)
                    fig.add_hline(y=up, line_width=1, line_dash="dash", line_color="red", opacity=0.7)
                    fig.add_hline(y=down, line_width=1, line_dash="dash", line_color="red", opacity=0.7)
                    st.plotly_chart(fig, use_container_width=True)

                # st.write(dfcopy)

                dfcopy = dfcopy.drop('Lot No.', axis=1)
                dfcopy = dfcopy.dropna()

                with graph3_slot:
                    fig = ffact.create_distplot([dfcopy[selector].to_list()], [selector], bin_size=0.1, curve_type='normal')
                    
                    # fig = ffact.create_distplot([dfcopy[c] for c in dfcopy.columns], dfcopy.columns, bin_size=.25)
                    fig.add_vline(x=mean, line_width=0.5, line_dash="dash", line_color="black", opacity=0.7)
                    fig.add_vline(x=up, line_width=1, line_dash="dash", line_color="red", opacity=0.7)
                    fig.add_vline(x=down, line_width=1, line_dash="dash", line_color="red", opacity=0.7)
                    st.plotly_chart(fig, use_container_width=True)

                # bokeh graph , maar de colormap is niet super goed vindk
                # with graph_slot:
                #     source = ColumnDataSource(data=dfcopy)
                #     # st.write(source)

                #     TOOLTIPS = [
                #         ("index", "$index"),
                #         ("(x,y)", "($x, $y)"),
                #         # ("Lot No", "($Lot No.)")
                #         ]

                #     p = figure(
                #         title=selector,
                #         # x_axis_label='x',
                #         y_axis_label='value',
                #         tooltips=TOOLTIPS)
                #     st.write(dfcopy.loc[:, 'Lot No.'])
                #     SPECIES = dfcopy.loc[:, 'Lot No.']
                #     p.line(x='index', y=selector, source=source, line_width=2)
                #     p.circle(x='index', y=selector, source=source, color=factor_cmap('Lot No.', 'Turbo256', SPECIES), size=10)
                #     # p.circle([1, 2, 3, 4, 5], [6, 7, 2, 4, 5], size=20, color="navy", alpha=0.5)
                #     # p.line(x='index', y='CT02', source=source, line_width=2)

                #     st.bokeh_chart(p, use_container_width=True)

                #     # st.form_submit_button('update this graph')

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
