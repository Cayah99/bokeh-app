
# ## Importeren packages 

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon
from bokeh.plotting import figure, show, output_file
import geopandas as gp
import shapely
import seaborn as sns
from bokeh.io import curdoc, output_notebook
from bokeh.layouts import layout, column, widgetbox, gridplot
from bokeh.models import (Button, CategoricalColorMapper, ColumnDataSource, Select, RadioButtonGroup,
                          HoverTool, Label, SingleIntervalTicker, Slider,LinearColorMapper, MultiSelect, CheckboxButtonGroup, CheckboxGroup, RangeSlider)
from bokeh.models import ColorBar
from bokeh.palettes import Spectral6, Viridis256
from bokeh.models.widgets import Panel, Tabs
import yaml
from bokeh.server.server import Server
from bokeh.driving import linear
output_notebook()

pd.set_option('chained_assignment', None)
pd.options.display.float_format = '{:.4f}'.format
import warnings
warnings.filterwarnings('ignore')
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
import fiona

# ## Importeren files

#File with the terrorist attacks
Terrorist_attacks = pd.read_excel('C:/Users/kyrajongman/Documents/Challenge/Terrorist attacks.xlsx')

#File with the geometry values of the world
world = gp.read_file(gp.datasets.get_path('naturalearth_lowres'))

#File with human development index wordt geopend
Human_Development_Index = pd.read_excel('C:/Users/kyrajongman/Documents/Challenge/HDI.xlsx')

# ## Cleanen data
#Using dissolve to group by the dataframe with geometry values
World = gp.GeoDataFrame(world.dissolve(by='name').reset_index())

#Using group by to group the dataframe on country and year
#Using reset_index to rest the index columns to normal columns
Terrorist_attacks_df = pd.DataFrame(Terrorist_attacks.groupby(['Country', 'Year']).sum().reset_index())

#Making cumulative values
Terrorist_attacks_df['no_cumulative'] = Terrorist_attacks_df.groupby(['Country'])['nkill'].apply(lambda x: x.cumsum())

#Changing the value names so that the columns can be merged
World.loc[World['name'] == 'United States of America', World.columns[0]] = 'United States'
World.loc[World['name'] == 'Congo', World.columns[0]] = 'Republic of the Congo'

#Convert the multipolygon values to polygon values
indf = World
outdf = gp.GeoDataFrame(columns=indf.columns)
for idx, row in indf.iterrows():
    if type(row.geometry) == Polygon:
        outdf = outdf.append(row,ignore_index=True)
    if type(row.geometry) == MultiPolygon:
        multdf = gp.GeoDataFrame(columns=indf.columns)
        recs = len(row.geometry)
        multdf = multdf.append([row]*recs,ignore_index=True)
        for geom in range(recs):
            multdf.loc[geom,'geometry'] = row.geometry[geom]
            outdf = outdf.append(multdf,ignore_index=True)

#Making a dataframe with the polygon values
GeoDataframe_outdf = gp.GeoDataFrame(outdf)
Countries_Polygon = gp.GeoDataFrame(GeoDataframe_outdf[GeoDataframe_outdf.geometry.type == 'Polygon'])

#Combining the two dataframes on the country names
Two_Dataframes = pd.merge(left=Terrorist_attacks_df, right=Countries_Polygon, left_on='Country', right_on='name')

#Making a new dataframe with the year, country, amount of kills and geometry columns
Amount_of_Terrorist_Attacks = gp.GeoDataFrame(Two_Dataframes, columns = ['Year', 'Country', 'no_cumulative', 'geometry'])

# ## Making a map
def bkapp(doc):
    
    #Creating x and y instead of geometry
    def getPolyCoords(row, geom, coord_type):
            if coord_type == 'x':
                return list(row[geom].exterior.coords.xy[0])
            elif coord_type == 'y':
                return list(row[geom].exterior.coords.xy[1])

    gdf = Amount_of_Terrorist_Attacks
    gdf['x'] = gdf.apply(getPolyCoords, geom = 'geometry', coord_type = 'x', axis = 1)
    gdf['y'] = gdf.apply(getPolyCoords, geom = 'geometry', coord_type = 'y', axis = 1)
    
    #Delete the geometry column
    p_df = gdf.drop('geometry', axis = 1).copy()
    gefilterde_df_1970 = p_df[p_df['Year'] == 1970] 

    #Creating Column Data Source
    source = ColumnDataSource({
        'x': gefilterde_df_1970['x'], 
        'y': gefilterde_df_1970['y'], 
        'Country': gefilterde_df_1970['Country'], 
        'no_cumulative': gefilterde_df_1970['no_cumulative']
    })

    #Creating color palette for plot
    color_mapper = LinearColorMapper(palette= Viridis256,
                                     low = min(p_df['no_cumulative']),
                                     high = max(p_df['no_cumulative']))

    # Creating the figure
    p = figure(title = "Amount of kills over the years", height=700, width=950)
    p.xaxis.axis_label = "Longitude"
    p.yaxis.axis_label = "Latitude"
    p.patches(xs = 'x', ys = 'y', source = source, line_color = "white", line_width = 0.5, fill_color ={'field':'no_cumulative','transform':color_mapper})

    #Add text
    label = Label(x=-170, y=-50, text=str(min(Amount_of_Terrorist_Attacks['Year'])), text_font_size='70pt', text_color='#A9A9A9')
    p.add_layout(label)
    
    #Add colorbar
    bar = ColorBar(color_mapper=color_mapper,location=(0,0))
    p.add_layout(bar, 'right')

    def update_plot(attr, old, new):
        #Update glyph locations
        yr = slider.value
        Amount_nkills_df = p_df[p_df['Year']== yr]
        new_data = {
            'x': Amount_nkills_df['x'], 
            'y': Amount_nkills_df['y'], 
            'Country': Amount_nkills_df['Country'], 
            'no_cumulative': Amount_nkills_df['no_cumulative']
            }
        source.data = new_data
        label.text = str(yr)
        
        #Update colors
        color_mapper = LinearColorMapper(palette= Viridis256,
                                     low = min(new_data['no_cumulative']),
                                     high = max(new_data['no_cumulative']))

    #Creating Slider for Year
    start_yr = min(p_df['Year'])
    end_yr = max(p_df['Year'])
    slider = Slider(start=start_yr, end=end_yr, step=1, value=start_yr, title='Year', width=450)
    slider.on_change('value',update_plot)
    
    #Creating animate update function for slider
    def animate_update():
        year = slider.value + 1
        if year > end_yr:
            year = start_yr
        slider.value = year
    
    #Creating animate function for slider with button
    def animate():
        global callback_id
        if button.label == '► Play':
            button.label = '❚❚ Pause'
            callback_id = curdoc().add_periodic_callback(animate_update, 1000)
        else:
            button.label = '► Play'
            curdoc().remove_periodic_callback(callback_id)
    
    #Creating button for play and pause
    button = Button(label='► Play', width=450)
    button.on_click(animate)
    
    #Creating layout
    grid = gridplot([[p],[slider, button]])
    
    df_Terrorist = pd.DataFrame(Terrorist_attacks.groupby('Year').agg({'City':'size', 'nkill':'sum'}).reset_index())
    year = df_Terrorist['Year']
    city = df_Terrorist['City']
    nkill = df_Terrorist['nkill']
    
    p = figure(title = 'Development amount of attacks and kills', height = 400, width=800)
    p.xaxis.axis_label = "Year"
    p.yaxis.axis_label = "Amount"
    r1 = p.line([], [], color="lightgreen", line_width=3, legend="Attacks")
    r2 = p.line([], [], color="purple", line_width=3, legend="Kills")
    
    ds1 = r1.data_source
    ds2 = r2.data_source

    @linear(m=1, b=min(year))
    def update(step):
        ds1.data['x'].append(step)
        ds1.data['y'].append(city[step-1970])
        ds2.data['x'].append(step)
        ds2.data['y'].append(nkill[step-1970])  
        ds1.trigger('data', ds1.data, ds1.data)
        ds2.trigger('data', ds2.data, ds2.data)
        if step == 2017:
            doc.remove_periodic_callback(update)
            
    def animate():
        global callback_id
        if button.label == '► Play':
            button.label = '❚❚ Pause'
            callback_id = doc.add_periodic_callback(update, 600)
        else:
            button.label = '► Play'
            doc.remove_periodic_callback(callback_id)
    
    #Creating button for play and pause
    button = Button(label='► Play', width=800)
    button.on_click(animate) 
    
    Gefilterde_df_Afghanistan = Terrorist_attacks[Terrorist_attacks['Country']=='Afghanistan']
    success_Afghanistan = pd.DataFrame(Gefilterde_df_Afghanistan.groupby(['Year', 'Success', 'Country'])['City'].count().reset_index())
    success_Afghanistan_0 = success_Afghanistan[success_Afghanistan['Success'] == 0.0]
    success_Afghanistan_1 = success_Afghanistan[success_Afghanistan['Success']== 1.0]
    
    successdf = Terrorist_attacks[Terrorist_attacks['Success'].isnull() == False]
    success = pd.DataFrame(successdf.groupby(['Year','Success', 'Country'])['City'].count().reset_index())
    
    Human_Development_Index['HDI Score'] = [int('{:<03}'.format(score)) for score in Human_Development_Index['HDI Score']]
    HDI_Afghanistan = Human_Development_Index[Human_Development_Index['Country'] == 'Afghanistan']

    source1 = ColumnDataSource({
            'x': success_Afghanistan_0['Year'], 
            'y': success_Afghanistan_0['City'], 
            'Country': success_Afghanistan_0['Country'], 
            'Success': success_Afghanistan_0['Success']
        })
    source2 = ColumnDataSource({
            'x': success_Afghanistan_1['Year'], 
            'y': success_Afghanistan_1['City'], 
            'Country': success_Afghanistan_1['Country'], 
            'Success': success_Afghanistan_1['Success']
        })
    
    source3 = ColumnDataSource({
        'x': HDI_Afghanistan['Year'], 
        'y': HDI_Afghanistan['HDI Score']
    })
    
    k = figure(title = 'Development of the attacks with success and no success', height = 500, width=400)
    k.line('x', 'y', source = source1, color="lightgreen", line_width=3, legend="No success (0.0)")
    k.line('x', 'y', source = source2, color="purple", line_width=3, legend="Success (1.0)")
    k.xaxis.axis_label = "Year"
    k.yaxis.axis_label = "Amount of attacks"
    
    t = figure(title='Development of Human Development Index', height = 500, width=400)
    t.line('x', 'y', source=source3, color='purple', line_width=3)
    t.xaxis.axis_label = "Year"
    t.yaxis.axis_label = "HDI Score, 350(low)-1000(high)"

    def update_line(attr, old, new):
        country = select.value
        year_1 = slider_range.value[0]
        year_2 = slider_range.value[1]
        Success_Attacks = success[(success['Country'] == country) & (success['Year'] >= year_1) & (success['Year'] <= year_2)]
        HDI_Country = Human_Development_Index[(Human_Development_Index['Country'] == country) & (Human_Development_Index['Year'] >= year_1) & (Human_Development_Index['Year'] <= year_2)]
        Success_Attacks_0 = Success_Attacks[Success_Attacks['Success'] == 0.0]
        Success_Attacks_1 = Success_Attacks[Success_Attacks['Success'] == 1.0]
        New_Data_1 = {
            'x': Success_Attacks_0['Year'], 
            'y': Success_Attacks_0['City'], 
            'Country': Success_Attacks_0['Country'], 
            'Success': Success_Attacks_0['Success']
        }
        New_Data_2 = {
            'x': Success_Attacks_1['Year'],
            'y': Success_Attacks_1['City'],
            'Country': Success_Attacks_1['Country'],
            'Success': Success_Attacks_1['Success']
        } 
        New_Data_3 = {
            'x': HDI_Country['Year'], 
            'y': HDI_Country['HDI Score']
        }
        source1.data = New_Data_1
        source2.data = New_Data_2
        source3.data = New_Data_3

    Countries = Terrorist_attacks['Country'].dropna()
    Countries_list = sorted(Countries.unique())
    select = Select(title='Choose Country:', value='Afghanistan', options=Countries_list, width=380)
    select.on_change('value', update_line)
    
    str_year = min(success['Year'])
    end_year = max(success['Year'])
    slider_range = RangeSlider(title="Choose years", start=str_year, end=end_year, value=(str_year, end_year), step=5, width=400)
    slider_range.on_change('value', update_line)
    
    grid1 = gridplot([[None, button], [p], [select, None, slider_range], [k, t]])

    tab1 = Panel(child=grid, title='General',)
    tab2 = Panel(child=grid1,title="Development of terrorism attacks in the world")
    tabs = Tabs(tabs=[tab1, tab2])
    
    #Making the document
    doc.add_root(tabs)
