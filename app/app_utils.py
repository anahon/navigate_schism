import pydeck as pdk
import pandas as pd
import os,glob
from scipy.io import loadmat
from matplotlib.dates import num2date
from dash import html
import numpy as np
from datetime import datetime
import xarray as xr
import re
from numpy.matlib import repmat
from pyproj import Proj, transform
import time

BAD_VARS=[
'time',
'SCHISM_hgrid',
'SCHISM_hgrid_face_nodes',
'SCHISM_hgrid_edge_nodes',
'SCHISM_hgrid_node_x',
'SCHISM_hgrid_node_y',
'node_bottom_index',
'SCHISM_hgrid_face_x',
'SCHISM_hgrid_face_y',
'ele_bottom_index',
'SCHISM_hgrid_edge_x',
'SCHISM_hgrid_edge_y',
'edge_bottom_index',
'depth',
'sigma',
'dry_value_flag',
'coordinate_system_flag',
'minimum_depth',
'sigma_h_c',
'sigma_theta_b',
'sigma_theta_f',
'sigma_maxdepth',
'Cs',
'wetdry_node',
'wetdry_elem',
'wetdry_side',
'zcor']


def get_domain_box(xrng,yrng):
    all_datasets=[]
    d1 = {"coordinates": [[
            [xrng[0],yrng[0]],
            [xrng[0],yrng[1]], 
            [xrng[1],yrng[1]],
            [xrng[1],yrng[0]],
            ]],'name':'domain',}

    df = pd.DataFrame(data=d1)

    all_datasets.append( pdk.Layer(
        "PolygonLayer",
        df,
        stroked=False,
        id='domain',
        #get_text='name',
        get_polygon="coordinates",
        # # processes the data as a flat longitude-latitude pair
        # get_polygon="-",
        get_fill_color=[189, 223, 236 , 150],
        auto_highlight=True,
        pickable=False,
    )   
    )

    return all_datasets

def unixTimeMillis(dt):
    ''' Convert datetime to unix timestamp '''
    return int(time.mktime(dt.timetuple()))

def unixToDatetime(unix):
    ''' Convert unix timestamp to datetime. '''
    return pd.to_datetime(unix,unit='s')

def getMarks(daterange,start, end, Nth=12):
    ''' Returns the marks for labeling. 
        Every Nth value will be used.
    '''

    result = {}
    for i, date in enumerate(daterange):
        if i==0:
            form='%d/%m/%Y %Hh'
        else:
            form='%Hh'
        if(i%Nth == 1):
            # Append value to dict
            result[unixTimeMillis(date)] = str(date.strftime(form))

    return result


def get_center(xrng,yrng):
    return {'lon':(xrng[0]+xrng[1])/2,
            'lat':(yrng[0]+yrng[1])/2}


def get_zoom(xrng,yrng):
    max_bound = max(
                abs(xrng[0]-xrng[1]),
                abs(yrng[0]-yrng[1])
                ) * 111
    return 14.5 - np.log(max_bound)


def connect_to_dataset(db_name):
    ds=xr.open_dataset(db_name)

    return ds

def load_metadata(root,EPSG):
    all_file=glob.glob(root+'*.nc')
    all_file.sort(key=lambda f: int(re.sub('\D', '', f)))
    nfiles=len(all_file)
    nc=xr.open_dataset(all_file[0])
    ts=nc['time'][0].values
    dt=(nc['time'][1]-nc['time'][0]).values
    nt=len(nc['time'])*nfiles
    times=pd.date_range(ts,ts+(nt*dt),freq='%iS'%(dt/1e9))[:-1]
    filen=repmat(np.arange(0,len(all_file)),len(nc['time']),1).T.ravel()
    variables={}
    for key in nc.variables.keys():
        if key not in BAD_VARS:
            variables[key]={}
            variables[key]={'ivs':nc[key].ivs,
                            'i23d':nc[key].i23d,
                            'desc':'elevation '}


    

    inProj = Proj(init='epsg:'+str(EPSG))
    outProj = Proj(init='epsg:'+str(4326))

    Lon,Lat=transform(inProj,outProj,nc['SCHISM_hgrid_node_x'][:].values,nc['SCHISM_hgrid_node_y'][:].values) 
    xrng=[Lon.min(),Lon.max()]
    yrng=[Lat.min(),Lat.max()]

    nlayers=nc.nSCHISM_vgrid_layers.values

    return Lon,Lat,xrng,yrng,nlayers,variables,all_file,times,filen


