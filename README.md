# Code Repository for "Ecosystem carbon mapping reduces global land use change flux estimates"

## Overview
This repository contains the code used for the analysis published in "Ecosystem carbon mapping reduces global land use change flux estimates". 
For questions, please contact Raphael Ganzenmüller (r.ganzenmueller@lmu.de).

## Associated Publications
.

* **Data:** Ganzenmüller et al., Ecosystem carbon mapping reduces global land use change flux estimates [Data set], Zenodo (2026), https://doi.org/10.5281/zenodo.22113321

## Associated Input Data
The input data for this analysis are sourced from various publicly available datasets:
* [Copernicus Land Cover 100m v.3.0.1](https://zenodo.org/records/3939050)
* [Dinerstein2017](https://storage.googleapis.com/teow2016/Ecoregions2017.zip)
* [ESACCI-BIOMASS v6.0](https://data.ceda.ac.uk/neodc/esacci/biomass/data/agb/maps/v6.0/)
* [Geomorpho90m v1.0](https://doi.pangaea.de/10.1594/PANGAEA.899135)
* [GSOC v1.6.1](https://data.apps.fao.org/glosis/)
* [HILDA+ v2.0](https://doi.pangaea.de/10.1594/PANGAEA.974335)
* [Huang2021](https://doi.org/10.6084/m9.figshare.12199637.v1)
* [Iturbide2020](https://github.com/SantanderMetGroup/ATLAS/tree/v1.6)
* [LUH2](https://luh.umd.edu/data.shtml)
* [Mu2022](https://doi.org/10.6084/m9.figshare.16571064)
* [Natural Earth](https://www.naturalearthdata.com/downloads/)
* [Soilgrids2020](https://files.isric.org/soilgrids/latest/data/)
* [Soilgrids2017](https://files.isric.org/soilgrids/former/2017-03-10/data/)
* [Spawn2020](https://doi.org/10.3334/ORNLDAAC/1763)
* [WISE30sec](https://data.isric.org/geonetwork/srv/eng/catalog.search#/metadata/dc7b283a-8f19-45e1-aaed-e9bd515119bc)
* [WorldClim v2.1](https://www.worldclim.org/data/worldclim21.html)
* [TRENDY-v12](https://mdosullivan.github.io/GCB/)

## Requirements
* Python: Version 3.13
* Python packages: see `environment.yml`
* CDO version 2.0.5 (https://mpimet.mpg.de/cdo)
* SLURM workload manager
 
## Project structure
```
.
├── 01_data_prep                                   # Preparation input data
│   ├── regrid_high_res_v1_01.py                   # Function for regridding global high resolution data
│   ├── 01_01_prep_land_and_target.ipynb           # Preparation land-sea mask from copernicus luc data
│   ├── 01_02_prep_spawn.ipynb                     # Preparation Spawn et al. 2020 data
│   ├── 01_03_prep_esabio.ipynb                    # Preparation ESACCI aboveground biomass data
│   ├── 01_04_prep_huang.ipynb                     # Preparation Huang et al. 2021 data
│   ├── 01_05_prep_soilgrids.ipynb                 # Preparation soilgrids data
│   ├── 01_06_prep_gsoc.ipynb                      # Preparation GSOC soil data
│   ├── 01_07_prep_wise.ipynb                      # Preparation WISE soil data
│   ├── 01_08_prep_hilda.ipynb                     # Preparation HILDA+ data
│   ├── 01_09_prep_copernicusluc.ipynb             # Preparation Copernicus LUCC data
│   ├── 01_10_prep_dinerstein.ipynb                # Preparation Dinerstein et al. 2017 data
│   ├── 01_11_prep_mu.ipynb                        # Preparation Mu 2022 HFP data
│   ├── 01_12_prep_worldclim.ipynb                 # Preparation worldclim data
│   └── 01_13_prep_geomorpho90m.ipynb              # Preparation geom90m data
│
├── 02_database_prep                               # Preparation databases
│   ├── 02_01_prep_cveg_data.ipynb                 # Preparation biomass carbon data
│   ├── 02_02_prep_csoil_data.ipynb                # Preparation soil carbon data
│   ├── 02_03_prep_pot_train_occur_r001.ipynb      # Preparation potential training and occurrence of ecosystems (res. 0.01°)
│   ├── 02_04_prep_pot_occur_r025.ipynb            # Preparation occurrence of ecosystems (res. 0.25°)
│   ├── 02_05_prep_database_r001.ipynb             # Preparation database "res. 0.01°"
│   └── 02_06_prep_database_r025.ipynb             # Preparation database "res. 0.25°"
│
├── 03_rf_predict                                  # Application of random forest models
│   ├── 03_01_best_parameter_r001.ipynb            # Identification best performing random forest model parameters
│   ├── 03_02_predict_rf_r001.ipynb                # Prediction carbon densities with random forest models
│   └── 03_03_df2ds_r001.ipynb                     # Conversion dataframes to datasets
│
├── 04_dgvm_prep                                   # Preparation DGVM simulation data
│   ├── dgvm_data_overview.txt                     # DGVMS: Models and files
│   ├── 04_01_dgvm_regridd_dvgm.ipynb              # Regridding DGVM file
│   ├── 04_02_dgvm_translate.ipynb                 # Translation DGMV PFTs to ecosystem zones
│   ├── 04_03_dgvm_limit_range.ipynb               # Limitation DGVM value range to value range of training data
│   └── 04_04_dgvm_rf_fillnan.ipynb                # Fill nans using random forest models
│
├── 05_rf_constrain                                # Constraining random forest predictions
│   ├── 05_01_rf_regridding2r025.ipynb             # Regridding random forest predictions to 0.25° resolution
│   └── 05_02_rf_constrain.ipynb                   # Constraining random forest predictions with prepared DGVM data
│
├── 06_blue_prep                                   # Preparation BLUE data
│   ├── 06_01_prep_c4blue_20260515_cspatial.ipynb  # Preparation carbon data for blue run: 20260515_cspatial
│   └── 06_02_prep_c4blue_20260515_cdgvm.ipynb     # Preparation carbon data for blue run: 20260515_cdgvm
│
├── 07_eval_prep                                   # Preparation of evaluation data
│   ├── blue_postprocessing_v01.py                 # Functions to post-process BLUE output data
│   ├── xgrid_utils.py                             # Helper functions
│   ├── 07_01_blue_runs_postprocess.ipynb          # Post-processing BLUE output data
│   ├── 07_02_ds_trendy_ysum.ipynb                 # Preparation TRENDY data
│   ├── 07_03_prep_area_r001.ipynb                 # Preparation array with grid cell areas at res. 0.01°
│   ├── 07_04_prep_occur_etype_r025.ipynb          # Preparation occurrence of ecosystem types at res. 0.25°
│   ├── 07_05_prep_data_m01_m03_zenodo.ipynb       # Preparation carbon density data cSpatial and cDGVM (figure m01 and m03)
│   ├── 07_06_prep_data_m02_m04_zenodo.ipynb       # Preparation carbon density data (figure m02 and m04)
│   ├── 07_07_prep_data_m05_zenodo.ipynb           # Preparation fluc data (figure m05)
│   └── 07_08_prep_data_m06_zenodo.ipynb           # Preparation carbon stocks data (figure m06)
│
├── 08_eval                                        # Evaluation: plots, tables, ...
│   ├── 08_01_m01_m03_maps_carbon.ipynb            # Plots maps carbon densities (figure m01 and m03)
│   ├── 08_02_m02_m04_training_literature.ipynb    # Plots box training data and literature (figure m02 and m04)
│   ├── 08_03_m05_fluc.ipynb                       # Plot fluc blue (figure m05)
│   ├── 08_04_m06_cstocks.ipynb                    # Plot carbon stocks blue trendy literature (figure m06)
│   ├── 08_05_s01_training_data.ipynb              # Plot maps training data
│   ├── 08_06_s02_s04_cspatial_scatter.ipynb       # Plots scatter random forest performance
│   ├── 08_07_s03_s05_diffper_cspatial_cdgvm.ipynb # Plots maps carbon densities differences
│   ├── 08_08_s06_s07_fluc_maps.ipynb              # Plots maps fLUC differences
│   ├── 08_09_s08_ipcc_regions.ipynb               # Plot map IPCC regions
│   ├── 08_10_s10_carbon_underlying.ipynb          # Plot maps underlying carbon
│   ├── 08_11_ts01_ipcc_region_fluc.ipynb          # Table fLUC IPCC regions
│   ├── 08_12_ts04_params_best10rfmodels.ipynb     # Table parameters of 10 best random forest models
│   ├── 08_13_ts05_stats_best10rfmodels.ipynb      # Table performance of 10 best random forest models
│   ├── 08_14_ts06_effect_constrain.ipynb          # Table constraining effect
│   └── 08_15_values_publication.ipynb             # Values for publication
│
├── environment.yml                                # Conda environment with required dependencies
├── environment-full.yml                           # Complete conda environment used for the analysis
├── README.md
└── LICENSE.md
```

## Note
* SLURM settings (e.g., queue, account, interface, local_directory, and job_extra_directives) must be adapted to the local computing environment.
* BLUE code and BLUE runscript files are not published.

## Licensing
This code is licensed under the **MIT License**.

MIT License

Copyright (c) 2026 Raphael Ganzenmüller

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.