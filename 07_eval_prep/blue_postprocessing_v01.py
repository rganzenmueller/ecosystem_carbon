#!/usr/bin/env python
# -*-coding:utf-8 -*-
'''
@File    :   blue_postprocessing_v01.py
@Time    :   2025/03/28
@Author  :   Raphael Ganzenmüller
@Version :   1.00
@Contact :   r.ganzenmueller@lmu.de
@License :   (C)Copyright 2025, raphael ganzenmüller/lmu
@Desc    :   function to post-process blue output data. Based on scripts from
             Clemens Schwingshackl. Fluxes for shifting cultivation/no-shifting 
             cultivation not implemented
'''

##### File structure #####
#.
#├── _load_dataset
#├── _export_ds_eluc
#├── prep_ds_blue_components
#│   ├── _check_blue_data_exists
#│   ├── _prep_da_eluc
#│       ├── _prep_da_cpool_sources_sinks
#│       ├── _prep_da_cpool_deforestation_forest_other
#│       ├── _prep_da_cpool_net_harvest_crop_pasture
#│       ├── _prep_da_cpool_forestation
#│   ├── _prep_da_cell_area
#│   ├── _perform_checks
#├── prep_ds_eluc_pft
#│   ├── _check_blue_pft_data_exists
#│   ├── _prep_da_eluc_pft
#├── prep_ds_cveg_csoil
#│   ├── _check_blue_cveg_csoil_data_exists


###### Libraries ######

import os, sys
import xarray as xr
import numpy as np


##### LOAD AND EXPORT #####

def _load_dataset(dir_blue_data, input_file, chunks):
    """Loads datasets with chunking."""
    
    return xr.open_mfdataset(f'{dir_blue_data}{input_file}', chunks='auto') \
        .chunk(chunks)


def _export_ds_eluc(ds, blue_run, dir_out, file_out,
                    encoding=True, complevel=3):
    """Exports dataset with prepared eluc components as nc file"""

    print('Exporting')
    
    # Define encoding
    if encoding is True:
        encoding = dict((var, dict(zlib=True, complevel=complevel)) for
                        var in ds.data_vars)
    
    # Export
    ds.to_netcdf(f'{dir_out}{file_out}.nc', encoding=encoding, mode='w')


##### ELUC COMPONENTS #####

# net: Net carbon fluxes
# sources: All source fluxes combined (clearing + other transitions + degradation + decay (after harvest))
# sinks: All sink fluxes combined (abandonment + regrowth (after harvest) + recovery after degradation)
# deforestation: Carbon fluxes from deforestation (including permanent deforestation and deforestation in shifting cultivation cycles)
# forestation: Carbon fluxes from forest (re-)growth (including forest (re-)growth due to afforestation and reforestation and forest regrowth in shifting cultivation cycles)
# forest: Carbon fluxes from abandonment, regrowth (after harvest), recovery after degradation + degradation
# wood_harvest_sources: Carbon emissions from wood harvest and other forest management
# wood_harvest_sinks: Carbon removals from wood harvest and other forest management
# other_transitions: Carbon fluxes related to other transitions, e.g., from pasture to cropland
# crop: Carbon fluxes from cropland expansion
# pasture: Carbon fluxes pasture expansion


def prep_ds_eluc_components(dir_blue_runs, blue_run, components, dir_out=None, file_out=None, 
                            chunks_time=50, chunks_lat=-1, chunks_lon=-1, 
                            encoding=True, complevel=3):

    """Prepares dataset with BLUE components"""

    print('Preparing: eluc_components')
    
    # Define input folder
    dir_blue_data = f'{dir_blue_runs}{blue_run}/'
        
    # Define chunks
    chunks = dict(time=chunks_time, lat=chunks_lat, lon=chunks_lon)

    # Check if all needed BLUE output data exists
    _check_blue_data_exists(dir_blue_data, components)
    
    # Create empty datasets
    ds_eluc = xr.Dataset()

    # Add prepared eluc dataarrays
    for component in components:
        print(f'Preparing: {component}')     
        ds_eluc[f'eluc_{component}'] = _prep_da_eluc(component, dir_blue_data, chunks)   
       
    # Add cell_area datarray
    ds_eluc['cell_area'] = _prep_da_cell_area(dir_blue_data, chunks)

    # Rechunk and load to memory
    ds_eluc = ds_eluc.chunk(chunks).persist()

    # Perform checks
    _perform_checks(ds_eluc)

    # Return or Export
    if file_out is None:
        return ds_eluc
    else:
        _export_ds_eluc(ds_eluc, blue_run, dir_out, file_out,
                        encoding=encoding, complevel=complevel)
        print('Success')
    

def _check_blue_data_exists(dir_blue_data, components):
    """Checks if required datasets are available."""
    
    # Check if the defined blue directory exists
    if not os.path.exists(dir_blue_data):
        raise FileNotFoundError(f'BLUE run does not exist: {dir_blue_data}')
    
    # Dictionarry with required files
    dict_req_fstrs = {
        'net': ['CurrentCPools_CD.nc'],
        'sources': ['CurrentCPools_CD_PerHistoryType.nc', 
                    'CurrentCPools_CD_PerCoverType.nc'],
        'sinks': ['CurrentCPools_CD_PerHistoryType.nc', 
                  'CurrentCPools_CD_PerCoverType.nc'],
        'deforestation': ['CurrentCPools_CD_A_all_PerHistoryAndPerPFT.nc'],
        'forestation': ['CurrentCPools_CD_A_all_PerHistoryAndPerPFT.nc',
                        'CurrentCPools_CD_PerHistoryType.nc'],
        'forest': ['CurrentCPools_CD_A_all_PerHistoryAndPerPFT.nc'],
        'wood_harvest_sources': ['CurrentCPools_CD_PerHistoryType.nc'],
        'wood_harvest_sinks': ['CurrentCPools_CD_PerHistoryType.nc'],
        'other_transitions': ['CurrentCPools_CD_A_all_PerHistoryAndPerPFT.nc'],
        'crop': ['CurrentCPools_CD_PerCoverType.nc'],
        'pasture': ['CurrentCPools_CD_PerCoverType.nc']
    }
    
    # Check if required files exist
    files_in_dir = os.listdir(dir_blue_data)
    for component in components:
        req_fstrs = dict_req_fstrs[component] if component in dict_req_fstrs else []

        missing_files = []
        for fstr in req_fstrs:
            if not any(file.endswith(fstr) for file in files_in_dir):
                missing_files.append(fstr)
    
        if missing_files:
            raise FileNotFoundError(f'Not all required data found. Missing files: {', '.join(missing_files)} for {component}')
    
    print('All required data found')


def _prep_da_eluc(component, dir_blue_data, chunks):
    """Calculates eluc flux from prepared component datarray"""

    # Assign cpool prep functions to components
    component_funcs = {
        'net': _prep_da_cpool_net_harvest_crop_pasture,
        'sources': _prep_da_cpool_sources_sinks,
        'sinks': _prep_da_cpool_sources_sinks,
        'deforestation': _prep_da_cpool_deforestation_forest_other,
        'forestation': _prep_da_cpool_forestation,
        'forest': _prep_da_cpool_deforestation_forest_other,
        'wood_harvest_sources': _prep_da_cpool_net_harvest_crop_pasture,
        'wood_harvest_sinks': _prep_da_cpool_net_harvest_crop_pasture,
        'other_transitions': _prep_da_cpool_deforestation_forest_other,
        'crop': _prep_da_cpool_net_harvest_crop_pasture,
        'pasture': _prep_da_cpool_net_harvest_crop_pasture,
    }

    # Create cpool dataarray of component
    da_cpool = component_funcs[component](dir_blue_data, component, chunks)
    
    # Create eluc dataarray from cpool dataarray
    da_eluc = da_cpool.diff('time')
    da_eluc['time'] = da_eluc['time'] - 1

    # Update attributes
    da_eluc.attrs.update(dict(
        standard_name=f'eluc_{component}',
        long_name=f'Carbon emissions from land use change: {component}',
        units='tC ha⁻¹'
    ))
    
    return da_eluc
    

def _prep_da_cpool_sources_sinks(dir_blue_data, component, chunks):
    """ Prepares sources and sink component data from blue output files"""

    # Name of relevant blue output files
    input_file_hist = '*_CurrentCPools_CD_PerHistoryType.nc'
    input_file_covr = '*_CurrentCPools_CD_PerCoverType.nc'
            
    # Get relevant blue data
    ds_hist = _load_dataset(dir_blue_data, input_file_hist, chunks)
    ds_covr = _load_dataset(dir_blue_data, input_file_covr, chunks)
    
    # Merge relevant data tp Dataset
    ds_hc = xr.merge([ds_hist, ds_covr])
    
    # Variables to process for deforestation
    if component == 'sources':
        vars_process = ['CD_A_l', 'CD_A_g', 'CD_A_dec_h', 'CD_A_deg_d']
    if component == 'sinks':
        vars_process = ['CD_A_a', 'CD_A_reg_h', 'CD_A_deg_rec_d']      
        
    # Prepare component dataarray by summing all variables
    da_cpool = ds_hc[vars_process].to_array('a').sum('a')
    return da_cpool


def _prep_da_cpool_deforestation_forest_other(dir_blue_data, component, chunks):

    """Prepares deforestation, forest, other_transitions component data from 
    blue output files"""

    # Define all pfts (1-11)
    l_pfts_all = range(1, 12)
    # Define forest pfts (1-6)
    l_pfts_forest = range(1, 7)
    # Define non-forest pfts (7-11)
    l_pfts_nonforest = range(7, 12)
    
    # Name of relevant blue output file
    input_file = '*_CurrentCPools_CD_A_all_PerHistoryAndPerPFT.nc'
    
    # Get relevant blue data
    ds_in = _load_dataset(dir_blue_data, input_file, chunks)

    # Variables to process
    if component == 'deforestation':
        vars_process = [f'CD_A_l_{pft}' for pft in l_pfts_forest]
    if component == 'forest':
        l_temp = ['a', 'dec_h', 'deg_d', 'deg_rec_d', 'reg_h']
        vars_process = [f'CD_A_{i}_{pft}' for i in l_temp for pft in l_pfts_forest]
    if component == 'other_transitions':
        l_temp = ['a', 'dec_h', 'deg_d', 'deg_rec_d', 'reg_h', 'l']
        vars_process = [
            *[f'CD_A_{i}_{pft}' for i in  l_temp for pft in l_pfts_nonforest],
            *[f'CD_A_g_{pft}' for pft in l_pfts_all]
            ] 
        
    # Sum variables
    da_cpool = ds_in[vars_process].to_array('a').sum('a')
    return da_cpool


def _prep_da_cpool_net_harvest_crop_pasture(dir_blue_data, component, chunks):
    """ Prepares net, harvest, crop, and pasture component data from blue 
    output files"""

    # Define input file and variable
    file_vars = dict(
        net=('*CurrentCPools_CD.nc', 'CD_A'),
        wood_harvest_sources=('*_CurrentCPools_CD_PerHistoryType.nc', 'CD_A_dec_h'),
        wood_harvest_sinks=('*_CurrentCPools_CD_PerHistoryType.nc', 'CD_A_reg_h'),
        crop=('*_CurrentCPools_CD_PerCoverType.nc', 'CD_A_c'),
        pasture=('*_CurrentCPools_CD_PerCoverType.nc', 'CD_A_p')
    )
    
    input_file, variable = file_vars[component]

    # Get relevant blue data
    ds_in = _load_dataset(dir_blue_data, input_file, chunks)
    
    # Prepare component datarray 
    da_cpool = ds_in[variable]
    return da_cpool


def _prep_da_cpool_forestation(dir_blue_data, component, chunks):
    """ Prepares forestation component data from blue output files"""

    # Calculate relevant cpools
    da_cpool_forest = _prep_da_cpool_deforestation_forest_other(dir_blue_data, 'forest', chunks)
    da_cpool_hsource = _prep_da_cpool_net_harvest_crop_pasture(dir_blue_data, 'wood_harvest_sources', chunks)
    da_cpool_hsink = _prep_da_cpool_net_harvest_crop_pasture(dir_blue_data, 'wood_harvest_sinks', chunks)

    # Define forestation - fixed to properly use the harvest source and sink variables
    da_cpool = da_cpool_forest - da_cpool_hsource - da_cpool_hsink
    return da_cpool


def _prep_da_cell_area(dir_blue_data, chunks):
    """ Returns cell area dataarray """

    # Get relevant blue output data and return 
    input_file = '*_CurrentCPools_CD.nc'
    return _load_dataset(dir_blue_data, input_file, chunks).cell_area


def _perform_checks(ds_eluc):

    """Performs basic checks to ensure values are in expected range"""
    
    # Create dataset with yearly carbon values
    ds_sum = (ds_eluc * ds_eluc.cell_area).sum(['lat', 'lon']) * 1e-9
    
    # Create component array
    components = ['deforestation', 'forestation', 'wood_harvest_sources', 
                  'wood_harvest_sinks', 'other_transitions']
    da_comp = ds_sum[[f'eluc_{comp}' for comp in components]].to_array('a').sum('a')
    
    # Values for checks
    v_check1 = ds_sum.eluc_net.mean().values.item()
    v_check2 = abs(ds_sum.eluc_net - da_comp).max().values.item()
    v_check3 = abs(ds_sum.eluc_net - (ds_sum.eluc_sources + ds_sum.eluc_sinks)).max().values.item()
    
    # Perform checks and print result
    checks_passed = True
    
    if not (0 < v_check1 < 10):
        print('Check 1 not passed: Mean net flux not between 0 and 10')
        checks_passed = False
    if v_check2 > 1e-03:
        print('Check 2 not passed: Difference between net flux and component fluxes larger than 1e-03')
        checks_passed = False
    if v_check3 > 1e-03:
        print('Check 3 not passed: Difference between net flux and sources+sinks fluxes larger than 1e-03')
        checks_passed = False
    
    if checks_passed:
        print('All checks passed')


##### ELUC PFTS #####

def prep_ds_eluc_pft(dir_blue_runs, blue_run, dir_out=None, file_out=None,
                     chunks_time=50, chunks_lat=-1, chunks_lon=-1,
                     encoding=True, complevel=3):
    """
    Prepares dataset with eluc of pfts
    """
    
    print('Preparing: pft')
    
    # Define input folder
    dir_blue_data = f'{dir_blue_runs}{blue_run}/'
    
    # Define basic chunks (don't include pft yet)
    chunks = dict(time=chunks_time, lat=chunks_lat, lon=chunks_lon)
    
    # Check if required PFT file exists
    _check_blue_pft_data_exists(dir_blue_data)
    
    # Create empty dataset
    ds_eluc = xr.Dataset()
    
    # Add prepared eluc_pft dataarray
    ds_eluc['eluc_pft'] = _prep_da_eluc_pft(dir_blue_data, chunks)
    
    # Add cell_area dataarray
    ds_eluc['cell_area'] = _prep_da_cell_area(dir_blue_data, chunks)
    
    # Now create proper chunks with pft dimension for the final dataset
    all_chunks = dict(chunks)
    if 'eluc_pft' in ds_eluc and 'pft' in ds_eluc.eluc_pft.dims:
        all_chunks['pft'] = 1
    
    # Rechunk and load to memory
    ds_eluc = ds_eluc.chunk(all_chunks).persist()
    
    # Return or Export
    if file_out is None:
        return ds_eluc
    else:
        _export_ds_eluc(ds_eluc, blue_run, dir_out, file_out,
                        encoding=encoding, complevel=complevel)
        print('Success')

def _check_blue_pft_data_exists(dir_blue_data):
    """Checks if required PFT datasets are available."""
    
    # Check if the defined blue directory exists
    if not os.path.exists(dir_blue_data):
        raise FileNotFoundError(f'BLUE run does not exist: {dir_blue_data}')
    
    # Required file pattern
    req_fstr = 'CurrentCPools_CD_A_all_PerHistoryAndPerPFT.nc'
    
    # Check if required file exists
    files_in_dir = os.listdir(dir_blue_data)
    if not any(file.endswith(req_fstr) for file in files_in_dir):
        raise FileNotFoundError(f'Not all required data found. Missing file: {req_fstr}')
    
    print('All required data found')


def _prep_da_eluc_pft(dir_blue_data, chunks):
    """Returns eluc of pfts as dataarray"""
    
    # Dictionary with pft names
    dict_pfts = {
        1: "Tropical evergreen forest",
        2: "Tropical deciduous forest",
        3: "Temperate evergreen broadleaf forest",
        4: "Temperate/boreal deciduous broadleaf forest",
        5: "Temperate/boreal evergreen conifers",
        6: "Temperate/boreal deciduous conifers",
        7: "Raingreen shrubs",
        8: "Summergreen shrubs",
        9: "C3 natural grasses",
        10: "C4 natural grasses",
        11: "Tundra"
    }
    
    # Input file pattern
    input_file = '*_CurrentCPools_CD_A_all_PerHistoryAndPerPFT.nc'
    
    # Load the PFT dataset
    ds_in = _load_dataset(dir_blue_data, input_file, chunks)
    
    # Prepare dataset with pft cpools
    ds_pft = xr.Dataset()
    for npft in dict_pfts.keys():
        # Variables to process - these are the common PFT variables
        vars_process = [f'CD_A_{l}_{npft}' for l in ['a', 'd', 'g', 'h', 'l']]
        # Get only variables that exist in the dataset
        available_vars = [var for var in vars_process if var in ds_in.variables]
        if available_vars:
            # Summarize relevant variables for each pft
            ds_pft[str(npft)] = ds_in[available_vars].to_array('v').sum('v')
    
    # Create a new dimension coordinate for PFTs
    pft_dim = xr.DataArray(
        list(dict_pfts.keys()),
        dims=['pft'],
        name='pft',
        attrs=dict(short_name = 'PFT', 
                   long_name = 'Plant Functional Type')
    )
    
    # Convert the dataset to array with proper coordinates
    da_cpool = ds_pft.to_array(dim='pft')
    # Assign the proper coordinates
    da_cpool = da_cpool.assign_coords(pft=pft_dim)
    
    # Calculate eluc for PFT
    da_eluc_pft = da_cpool.diff('time')
    da_eluc_pft['time'] = da_eluc_pft['time'] - 1
    
    # Update attributes
    da_eluc_pft.attrs.update(dict(
        standard_name='eluc_pft',
        long_name='Carbon emissions from land use change per Plant Functional Type',
        units='tC ha⁻¹',
        comment="; ".join(f"{key}: {value}" for key, value in dict_pfts.items())
    ))
    
    # Don't try to chunk with pft yet, just return the dataarray
    return da_eluc_pft


##### CVEG AND CSOIL #####

def prep_ds_cveg_csoil(dir_blue_runs, blue_run, dir_out=None, file_out=None,
                       chunks_time=50, chunks_lat=-1, chunks_lon=-1, 
                       encoding=True, complevel=3):
    """ Prepares dataset with variables cveg, csoil and cell_area."""

    print('Preparing: cveg_csoil')
    
    # Define input folder
    dir_blue_data = f'{dir_blue_runs}{blue_run}/'
        
    # Define chunks
    chunks = dict(time=chunks_time, lat=chunks_lat, lon=chunks_lon)

    # Check if all needed BLUE output data exists
    _check_blue_cveg_csoil_data_exists(dir_blue_data)
    
    # Name of relevant blue output file
    input_file = '*__CurrentCPools_CD.nc'
    
    # Get relevant blue data
    ds_in = _load_dataset(dir_blue_data, input_file, chunks)

    ds = xr.Dataset()
    ds['cveg'] = ds_in.CD_B
    ds['csoil'] = ds_in.CD_SR + ds_in.CD_SS
    ds['cell_area'] = ds_in.cell_area

    # Add attributes
    for var in ['cveg', 'csoil']:
        ds[var].attrs.clear()
        if var == 'cveg':
            long_name = f'Carbon stocks in Vegetation'
        if var == 'csoil':
            long_name = f'Carbon stocks in Soil'
        ds[var] = ds[var].assign_attrs(
            units='tons C per ha',
            short_name=var,
            long_name=long_name
        )
    
    # Return or Export
    if file_out is None:
        return ds
    else:
        _export_ds_eluc(ds, blue_run, dir_out, file_out,
                        encoding=encoding, complevel=complevel)
        print('Success')


def _check_blue_cveg_csoil_data_exists(dir_blue_data):
    """Checks if required PFT datasets are available."""
    
    # Check if the defined blue directory exists
    if not os.path.exists(dir_blue_data):
        raise FileNotFoundError(f'BLUE run does not exist: {dir_blue_data}')
    
    # Required file pattern
    req_fstr = '__CurrentCPools_CD.nc'
    
    # Check if required file exists
    files_in_dir = os.listdir(dir_blue_data)
    if not any(file.endswith(req_fstr) for file in files_in_dir):
        raise FileNotFoundError(f'Not all required data found. Missing file: {req_fstr}')
    
    print('All required data found')