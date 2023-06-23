import dash_bootstrap_components as dbc
from dash import html,Dash,dcc
import numpy as np

from dash.dependencies import Input, Output


from .app_utils import (load_metadata,connect_to_dataset,unixToDatetime,
                        get_center,get_zoom,get_domain_box,unixTimeMillis,getMarks)




import dash_deckgl
import pydeck

# create_contour
from pydeck_grid import PcolorLayer, PartmeshLayer

root='/home/anahon/schism/results/cova_gala/202010_v5.10/outputs/'
EPSG=3763
Lon,Lat,xrng,yrng,nlayers,variables,files,times,filen=load_metadata(root,EPSG)
center=get_center(xrng,yrng)
zoom=get_zoom(xrng,yrng)


INITIAL_VIEW_STATE = pydeck.ViewState(
    latitude=center['lat'], longitude=center['lon'], zoom=zoom, max_zoom=16, pitch=45, bearing=0
)

r = pydeck.Deck(
    layers=[],
    initial_view_state=INITIAL_VIEW_STATE,
)

### all variables to plot
label_parameters=[]
for i,var in enumerate(variables.keys()):
    label_parameters.append(
        {'label': [html.Span(var, style={'font-size': 20, 'padding-left': 10})], 'value': i+1,}
        )

### all levels
label_levels=[]
for i in nlayers:
    if i==0:
        name='Bottom'
    elif i==len(nlayers)-1:
        name='Surface'
    else:
        name=i
    label_levels.append(
        {'label': [html.Span(name, style={'font-size': 20, 'padding-left': 10})], 'value': i,}
        )

### Construct the layout
app = Dash(__name__,external_stylesheets=[dbc.themes.MINTY])
app.title = "Calypso datasets"
server = app.server


tooltip={
    "html": "<b>{name}</b><br />"
}


app.layout = dbc.Container(
    [
        html.Div(
            [
                html.H1('Calypso Science datasets',style= {"display": "inline-block",}),
                html.Img(src=app.get_asset_url("cs-logo.png"),style={"float": "right"},alt="CS Logo",height="50px")
                ],),

        dbc.Row(
            [dbc.Col([html.H5('Choose a variables:'),
                        dcc.Dropdown(
                                        options=label_parameters,
                                        maxHeight=700,
                                        id="var-dropdown",
                                    ),
                        html.Br(),
                        dcc.Dropdown(label_levels,
                                      0,
                                      id='lev-dropdown',),
                        html.Br(),
                        html.P('',
                            id='variable_description',
                            style={'width':'90%','textAlign':'justify','font-size': 20}),
                        html.Br(),
                      ],width=3),
            dbc.Col(
                    [ dcc.Loading(id = "loading-icon", children=
                        [
                        html.Div(
                            dash_deckgl.DashDeckgl(
                             spec=r.to_json(),
                             tooltip=tooltip,id="deck-gl", 
                             customLibraries=pydeck.settings.custom_libraries,
                             height= "80vh",
                            )
                            )
                        ]
                        ),
                    html.Br(),
                    html.Div(
                        [
                            html.P("Date:"),
                            dcc.Slider(
                                            id='time_slider',
                                            min = unixTimeMillis(times.min()),
                                            max = unixTimeMillis(times.max()),
                                            value = unixTimeMillis(times[0]),
                                            marks=getMarks(times,times.min(),
                                                        times.max())
                                        )
                        ]       
                       ),
                    ]                    
                    ),
            ]
        ),
    ],
    fluid=True,
)

@app.callback(
    [
            Output("deck-gl", 'spec'),
            Output('deck-gl','description'),
            Output('deck-gl','tooltip'),
            Output('variable_description','children'),
            ],
            [
            Input('lev-dropdown','value') ,
            Input('var-dropdown','value'),
            Input('time_slider','value'),
            Input('deck-gl','tooltip'),
            Input('deck-gl','description'),
            ]
           )
def update_graph(level,variable,time_value,tooltip,description):

    description={}
    parameter_desc=''
    all_datasets=[]
    tooltip={
            "html": "<b>{name}</b><br />"
    }


    if variable==None:

        center=get_center(xrng,yrng)
        zoom=get_zoom(xrng,yrng)
        dropdown=None
        all_datasets+=get_domain_box(xrng,yrng)
        
    else:


        idx=[unixTimeMillis(x) for x in times].index(time_value)

        ds=connect_to_dataset(files[filen[idx]])
        variable=list(variables.keys())[variable-1]
       
        data=ds[['SCHISM_hgrid_node_x',variable]]\
                        .sel(time=times[idx])

        if variables[variable]['i23d']==2:
            data=data.sel(nSCHISM_vgrid_layers=level)
        
        data['lon']=data['SCHISM_hgrid_node_x'].copy()
        data['lon'][:]=Lon
        data['lat']=data['SCHISM_hgrid_node_x'].copy()
        data['lat'][:]=Lat

        if variables[variable]['ivs']==2:
            
            data['u']=data['SCHISM_hgrid_node_x'].copy()
            data['u'][:]=data[variable][:,0]
            data['v']=data['SCHISM_hgrid_node_x'].copy()
            data['v'][:]=data[variable][:,1]
            spd=np.sqrt(data[variable][:,0]**2+data[variable][:,1]**2)
            datakeys = {
                    "x": "lon",
                    "y": "lat",
                    "u": "u",
                    "v": "v",
                }
            scale=1.94
            vmin=0#spd.min().values
            vmax=2#3spd.max().values
            opacity=0.0
            labels=[0,.25, .5, 1,1.5,2]
            units='kts'
        else:
            data['c']=data['SCHISM_hgrid_node_x'].copy()
            data['c'][:]=data[variable][:]

            datakeys = {
                    "x": "lon",
                    "y": "lat",
                    "c": "c",
                }
            scale=1
            vmin=-1#data[variable][:].min().values
            vmax=1#data[variable][:].max().values
            opacity=1.0
            units='m'
            labels=[-1,-.5,-.25,0,.25, .5, 1]

        layer1 = PcolorLayer(
            data,
            datakeys,
            id='data1',
            opacity=opacity,
            vmin=vmin,
            vmax=vmax,
            scale=scale,
            pickable=True,
            precision=2,
        )
        all_datasets=[layer1]
        if variables[variable]['ivs']==2:

            layer2 = PartmeshLayer(
                data,
                datakeys,
                id='data2',
                colormap="turbo",
                vmin=vmin,
                vmax=vmax,
                scale=1.94,
                precision=2,
            )
            all_datasets.append(layer2)
        colorbar = layer1.colorbar(units=units, labels=labels,width=400,)
        description={"top-right": colorbar}
        tooltip={
                "html": "<b>Current speed:</b> {value} kts",
                "style": {"backgroundColor": "steelblue", "color": "white"},
            }
        center=get_center(xrng,yrng)
        zoom=get_zoom(xrng,yrng)

        

    view_state = pydeck.ViewState(
        latitude=center['lat'], longitude=center['lon'], zoom=zoom, max_zoom=16, pitch=45, bearing=0
    )
    r = pydeck.Deck(
        layers=all_datasets,
        initial_view_state=view_state,
    )

    if variable:
        desc=variables[variable]['desc']
    else:
        desc=''
    return r.to_json(),description,tooltip,desc


@app.server.route("/ping")
def ping():
  return "{status: ok}"

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=False, use_reloader=False)
