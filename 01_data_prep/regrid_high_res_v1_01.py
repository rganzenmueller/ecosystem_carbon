#!/usr/bin/env python
# -*-coding:utf-8 -*-
'''
@File    :   regrid_high_res.py
@Time    :   2022/10/27
@Author  :   raphael ganzenmüller
@Version :   1.01
@Contact :   r.ganzenmueller@lmu.de
@License :   (C)Copyright 2022, raphael ganzenmüller/lmu
@Desc    :   function to regrid large high-resolution datasets on a hpc system 
             with cdo and slurm configuration. Main function: regrid_high_res. 
             Functions to prepare arrays: prep_tiff, prep_zarr, prep_netcdf.
'''

# import required packages
import os, stat, time, itertools, shutil, subprocess, dask, rioxarray
import numpy as np
import xarray as xr
from datetime import datetime

# allow large chunks
dask.config.set(**{'array.slicing.split_large_chunks': True});

# inner fuctions for function regrid_high_res
def _make_intermediate_directories(dir_out): 
    """Creates intermediate folders, needed to temporarily store intermediate 
    files, in output directory. Folders get deleted after regridding.
    """ 
    
    # delete folder interm if exists
    if os.path.exists(dir_out + 'interm'):
        shutil.rmtree(dir_out + 'interm')

    # create needed folder and subfolders
    os.makedirs(dir_out + '/interm')
    os.makedirs(dir_out + '/interm/source')
    os.makedirs(dir_out + '/interm/target')
    os.makedirs(dir_out + '/interm/out')
    os.makedirs(dir_out + '/interm/bash')
    os.makedirs(dir_out + '/interm/bash/logs')
    
    
def _make_cases_list_global(size_tiles):
    """Creates a list with lat and lon coordinates of tiles depending on tile 
    size for the whole globe.
    
    Args:
        size_tiles (int): Size of tiles.
        
    Returns:
        list: List with lat and lon coordinates according to tile size defining. 
        tiles.
    """
    
    # define min lat and lon corner of tiles
    list_cases_global = list(itertools.product(*[
        [*range(-90, 90, size_tiles)], [*range(-180, 180, size_tiles)]]))

    # create list of coordinates of tiles
    list_cases_global2 = []
        
    for i in range(0, len(list_cases_global)):
        list_cases_global2.append([list_cases_global[i][0], 
                                   list_cases_global[i][0]+size_tiles,                    
                                   list_cases_global[i][1], 
                                   list_cases_global[i][1]+size_tiles])
                
    return list_cases_global2

    
def _make_cases_list_source(da_source, size_tiles):  
    """Selects tiles coordinates that are touched by extent of source data 
    array.
    
    Returns:
        list: List with lat and lon coordinates according to tile size defining. 
        tiles.
    """
    # select min and max coordinates of source data array
    lat_min = min(da_source.lat.data)
    lat_max = max(da_source.lat.data)
    lon_min = min(da_source.lon.data)
    lon_max = max(da_source.lon.data)
    
    # create list of global tiles coordinates
    list_cases_global = _make_cases_list_global(size_tiles)
    
    # select tiles coordinates touched by extent of source data array
    list_cases = []
    
    for i in list_cases_global:
        if ((i[1] >= lat_min) & (i[0] <= lat_max) &
            (i[3] >= lon_min) & (i[2] <= lon_max)):
            
            list_cases.append(i)
        
    return list_cases
     
    
def _make_tile(da_target, da_source, dir_out, olap, case):
    """Creates tile with overlap and export as netcdf.
    
    Args:
        da_target (xr.data.array): Target data array.
        da_source (xr.data.array): Source data array.
        dir_out (str): Path of output directory.
        olap (int/float): size of overlap (gets cropped after regridding).
        case: tile coordinates.
    """
    # define coordinates
    latmin, latmax, lonmin, lonmax = case[0], case[1], case[2], case[3]
    # create tile identifier
    case_str = (str(latmin) + '_' + str(latmax) + '_' + str(lonmin) + '_' + 
                str(lonmax))
    
    # crop target data array and export
    da_target \
        .sel(lat=slice(latmax+olap, latmin-olap), 
             lon=slice(lonmin-olap, lonmax+olap)) \
        .to_netcdf(dir_out + 'interm/target/da_target_' + case_str + '.nc', 
                   mode='w')
    # crop source data array and export
    da_source \
        .sel(lat=slice(latmax+olap, latmin-olap), 
            lon=slice(lonmin-olap, lonmax+olap)) \
        .to_netcdf(dir_out + 'interm/source/da_source_' + case_str + '.nc', 
                   mode='w')
    
    
def _make_tiles(da_target, da_source, dir_out, size_tiles, olap):
    """Creates and export tiles of target and source data arrays."""
    
    da_target = da_target \
        .chunk(dict(lat=-1, lon=-1)) \
        .persist()
    da_source = da_source \
        .chunk(dict(lat=-1, lon=-1)) \
        .persist()

    # create list of tiles coordinates touched by source data array
    list_cases = _make_cases_list_source(da_source, size_tiles)
    
    # create and export tiles
    for i in list_cases:
        _make_tile(da_target, da_source, dir_out, olap, i) 


def _prep_cmd_cdo(case):
    """ Defines CDO bash line for one tile.
    
    Args:
        case (list): List with coordinates defining tile.
        
    Return: 
        str: CDO command.
    """

    # define coordinates
    latmin, latmax, lonmin, lonmax = case[0], case[1], case[2], case[3]
    # create tile identifier
    case_str = (str(latmin) + '_' + str(latmax) + '_' + str(lonmin) + '_' + 
    str(lonmax))

    # define target, source and output files
    f_target = 'target/da_target_' + case_str + '.nc'
    f_source = 'source/da_source_' + case_str + '.nc'
    f_out = 'out/ds_out_' + case_str + '.nc'

    return 'cdo -P 12 remapycon,' + f_target + ' ' + f_source + ' ' + f_out
    
        
def _make_bash_scripts(da_source, dir_out, size_tiles, partition, account):
    
    """Creates bash script to regridd tiles."""
    # create list of tiles coordinates touched by source data array
    list_cases = _make_cases_list_source(da_source, size_tiles)
    
    # create list of tiles coordinates with five tiles in one group
    groups_cases = [list_cases[i:i+5] for i in range(0, len(list_cases), 5)]
    
    # create bash sub scripts defining slurm jobs for each group
    for i in range(0, len(groups_cases)):

        # create bash subscript
        script_sub = (dir_out + 'interm/bash/regridding_sub_' + str(i) + '.sh')

        # define bashsubscript
        with open(script_sub, 'w') as fp:
            fp.write('#!/bin/bash\n')
            fp.write('#SBATCH --job-name=regrid\n')
            fp.write('#SBATCH --partition=' + partition + '\n')
            fp.write('#SBATCH --ntasks=12\n')
            fp.write('#SBATCH --time=00:15:00\n')
            fp.write('#SBATCH --mail-type=FAIL\n')
            fp.write('#SBATCH --account=' + account + '\n')
            fp.write('#SBATCH --output=logs/regrid.o%j\n')
            fp.write('#SBATCH --error=logs/regrid.e%j\n')
            fp.write('\n')
            fp.write('cd ' + dir_out + 'interm/\n')
            fp.write('module load cdo\n')
            for ii in range(0, len(groups_cases[i])):
                fp.write(_prep_cmd_cdo(groups_cases[i][ii]) + '\n')
            pass

        # make subscript executable
        st = os.stat(script_sub)
        os.chmod(script_sub, st.st_mode | stat.S_IEXEC)
        
    # list of bash subscripts
    list_sub_files = sorted([i for i in 
                             os.listdir(dir_out + 'interm/bash/') if 
                             i.startswith('regridding_sub')])
    
    # create bash script to run subscripts in parallel
    script = dir_out + 'interm/bash/regridding.sh'
    
    #define bash script
    with open(script, 'w') as fp:
        fp.write('#!/bin/bash\n')
        fp.write('\n')
        for i in list_sub_files[:-1]:
            fp.write('sbatch -Q -W ' + dir_out + 'interm/bash/' + i + 
                     ' &\n')
        fp.write('sbatch -Q -W ' + dir_out + 'interm/bash/' + 
                 list_sub_files[-1] + '\n')
            
    # make bash script executable       
    st = os.stat(script)
    os.chmod(script, st.st_mode | stat.S_IEXEC)
    

def _run_bash_script(dir_out):
    """Runs bash script."""

    def _get_lastmod_diff(dir_files):
        """Get time difference between now and the last file modification
           
           Args:
               dir_files (str): directory of files to check last modification
            
           Return:
               datetime: last modification
           """
        # get list of file modifications
        list_lastmod = [os.stat(dir_files + i).st_mtime for i 
                    in os.listdir(dir_files)]
        # get last file modification
        d_lastmod = datetime.fromtimestamp(np.max(list_lastmod))
        # return difference between now and last file modification
        return (datetime.fromtimestamp(time.time()) - d_lastmod)
        
    # change directory to directory of bash scripts
    # directory needs to be changed, subprocess.run fails with exitcode 1
    os.chdir(dir_out + 'interm/bash/')
    # run bash script
    subprocess.run(['bash regridding.sh'], shell=True)
    
    # wait until all files are created 
    while (len(os.listdir(dir_out + 'interm/target/')) !=
           len(os.listdir(dir_out + 'interm/out/'))):
        time.sleep(5)

    # wait until last file modification was more than 120s ago
    while _get_lastmod_diff(dir_out + 'interm/out/').seconds < 120:
        time.sleep(2)


def _prep_tiles_regridded(file):
    """Crops overlap of regridded tiles.
    
    Args:
        file (str): regridded tile.        
        
    Return: 
        xr.dataset: regridded tile without overlap.
    """
    
    # min and max coordinates of file
    latmin = float(file.split('_')[-4])
    latmax = float(file.split('_')[-3])
    lonmin = float(file.split('_')[-2])
    lonmax = float(file.split('_')[-1].split('.')[0])

    # open and crop tile
    ds = xr.open_mfdataset(file) \
        .sel(lat=slice(latmax, latmin), lon = slice(lonmin, lonmax)) \
        .drop_vars('spatial_ref')
        
    return ds
            
            
def _combine_tiles_regridded(da_target, dir_out, f_str):
    """Opens tiles and combines them to one dataset.
    
    Returns: 
        xr.datases: Regridded dataset."""
    
    # list of regridded tiles
    list_f_out = sorted([i for i in os.listdir(dir_out + 'interm/out/') if 
                         i[:2] == 'ds'])

    # open tiles and crop overlap
    list_tiles_regridded = [_prep_tiles_regridded(dir_out + 'interm/out/' + i) 
                            for i in list_f_out]

    # combine tiles, if needed expand extent to extent of target source 
    # (if extent of source dataset is smaller than of target dataset), 
    # rename variable, rechunk
    ds_combine = xr.combine_by_coords(list_tiles_regridded, 
                                      compat='no_conflicts', 
                                      combine_attrs='drop') \
        .rename({f_str: 'regridded_' + f_str}) \
        .drop_duplicates(['lat', 'lon']) \
        .reindex_like(da_target) \
        .chunk(dict(lat=5000, lon=5000))

    return ds_combine

            
def _export_regridded(da_target, da_source, dir_out, f_str, fill_value, 
                      type_export):
    """ Combine tiles and export."""
        
    # combine tiles
    ds_combined = _combine_tiles_regridded(da_target, dir_out, f_str)
    
    # replace nan values with parameter fill_value
    # change dtype back to dtype of da_source
    ds_combined = xr.where(np.isnan(ds_combined), fill_value, ds_combined) \
        .astype(da_source.dtype)
    
    # add _FillValue attribute
    ds_combined['regridded_' + f_str].attrs['_FillValue'] = fill_value
    
    # export as zarr
    if type_export == 'zarr':
        ds_combined \
            .to_zarr(dir_out + 'ds_regridded_' + f_str + '.zarr', mode='w')

    # export as tif
    if type_export == 'tif':
        ds_combined \
            .rename(dict(lat='y', lon='x')) \
            .rio.to_raster(dir_out + 'ds_regridded_' + f_str + '.tif')

    # export as netcdf
    if type_export == 'netcdf':
        ds_combined \
            .to_netcdf(dir_out + 'ds_regridded_' + f_str + '.nc', mode='w')



# function for high resolution regridding
def regrid_high_res(da_target, da_source, dir_out, account, partition,
                    size_tiles, olap, fill_value, type_export, del_interm=True):
    """Regrids large high-resolution datasets on a hpc system with cdo and 
    slurm configuration
    
    Args:
        da_target (xarray.dataarray): Data array with target grid
        da_source (xarray.dataarray): Data array to be regridded
        dir_out (str): path to output directory
        account (str): hpc account/project
        partition (str): partition to use
        size_tiles (int): Size of tiles in degrees
        olap (int/float): Size of overlap in degrees
        fill_value (int/float): Fill value of output data array
        type_export (str): Export type, zarr and netcdf are implemented
        del_interm (bool): Delete intermediate files and directory
    """
    
    da_target = da_target#.chunk(dict(lat=5000, lon=5000))
    # ensure that extent of da_source is equal or smaller to da_target
    da_source = da_source.sel(lat=slice(max(da_target.lat.data), 
                                        min(da_target.lat.data)),
                              lon=slice(min(da_target.lon.data),
                                        max(da_target.lon.data)))# \
#        .chunk(dict(lat=5000, lon=5000))
    # name of variable (without dots if any)
    f_str = da_source.name.replace('.', '_')    
    
    # create intermediate directories
    _make_intermediate_directories(dir_out)
    # create netcdf files of tiles to regrid 
    _make_tiles(da_target, da_source, dir_out, size_tiles, olap)
    # create bash scripts to submit slurm jobs
    _make_bash_scripts(da_source, dir_out, size_tiles, partition, account)
    # run bash script to submit slurm jobs
    _run_bash_script(dir_out)
    # aggregate tiles and export regridded data
    _export_regridded(da_target, da_source, dir_out, f_str, fill_value, 
                      type_export)
    # remove intermediate directories if true
    if del_interm == True:
        shutil.rmtree(dir_out + 'interm')
    

# function to prepare tif files for regrid_high_res
def prep_tif(file, name):
    """Opens and prepares tiff file for regridding.
    
    Args:
        file (str): File location
        name (str): name of variable to regrid, if exists. Otherwise give new 
                    name  
    """
    
    # open tiff fill, replace dots in variable name (if any), rename lat and lon 
    # axis, remove and drop band dimension
    da = rioxarray.open_rasterio(file, chunks=dict(y = -1, x = -1)) \
        .rename(name.replace('.', '_')) \
        .rename({'y': 'lat', 'x': 'lon'}) \
        .squeeze('band') \
        .drop('band')
    
    # add spatial_ref attribute grid_mapping_name
    da.spatial_ref.attrs['grid_mapping_name'] = 'latitude_longitude'
    
    # adjust lat and lon attributes
    da.lat.attrs = dict(units = 'degrees_north', long_name = 'Latitude',
                        standard_name = 'latitude', axis = 'Y')
    da.lon.attrs = dict(units = 'degrees_east', long_name = 'Longitude',
                        standard_name = 'longitude', axis = 'X')
    
    return da