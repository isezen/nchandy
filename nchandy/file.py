# pylint: disable=C0103
"""
nchandy Files Module.

~~~~~~~~~
File module to interact with netCDF files directly
"""
import logging as _logging
from shutil import move as _mv
from shutil import copy2 as _copy2
from os import remove as _remove
from pathlib import Path as _Path
import subprocess as _subp
import xarray as _xr
import numpy as _np
import nchandy as _nch

_log = _logging.getLogger('nchandy')
_fmt_str = '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s'
_formatter = _logging.Formatter(_fmt_str, datefmt='%Y-%m-%dT%H:%M:%S')


_exclude_vars_ = ('TFLAG',)
_emis_vars_ = ['TFLAG', 'AACD', 'ACET', 'ALD2', 'ALDX', 'APIN', 'BENZ',
               'CH4', 'CO', 'ETH', 'ETHA', 'ETHY', 'ETOH', 'FACD', 'FORM',
               'IOLE', 'ISOP', 'IVOC', 'KET', 'MEOH', 'NAPH', 'NH3', 'NO',
               'NO2', 'NVOL', 'OLE', 'PAL', 'PAR', 'PCA', 'PCL', 'PEC',
               'PFE', 'PH2O', 'PK', 'PMC', 'PMG', 'PMN', 'PMOTHR', 'PNA',
               'PNCOM', 'PNH4', 'PNO3', 'POC', 'PRPA', 'PSI', 'PSO4',
               'PTI', 'SO2', 'SULF', 'TERP', 'TOL', 'UNR', 'XYLMN']


def scale_ncdf(from_file, factor, variables=None,
               exclude_variables=('TFLAG',), to_file=None) -> None:
    """
    Scale Emission File by netCDF4 library.

    Args:
        from_file (FILENAME)     : NetCDF file to scale.
        factor (FLOAT)           : Scale factor.
        variables (str|list)     : Name of variables to scale.
        exclude_vars (str| list) : Name of variables to exclude from scaling.
        to_file (FILENAME)       : New file name for scaled NetCDF data.
    Return:
        None
    """
    try:
        from netCDF4 import Dataset as _Dataset  # pylint: disable=E0611,C0415
    except ImportError:
        print('Install netCDF4 library to use this functionality')
        return

    if isinstance(from_file, str):
        from_file = _Path(from_file)

    if exclude_variables is None:
        exclude_variables = []

    if to_file is None:
        to_file = from_file

    modify = from_file == to_file
    if modify:
        to_file = _Path(str(to_file) + '.tmp')
    _copy2(from_file, to_file)

    nco = _Dataset(to_file, 'r+')
    nco = _nch.scale_ncdf(nco, factor, variables, exclude_variables)
    nco.close()

    if modify:
        _remove(from_file)
        _mv(to_file, from_file)
        _log.debug(f'tmp file renamed to {from_file}')
    _log.info(f'Scaled [netCDF4]: {from_file}')


def scale_xr(from_file, factor, variables=None,  # pylint: disable=R0913
             exclude_variables=('TFLAG',), dlevel=5,
             to_file=None) -> None:
    """
    Scale Emission File by xarray library.

    Args:
        from_file (FILENAME)     : NetCDF file to scale.
        factor (FLOAT)           : Scale factor.
        variables (str|list)     : Name of variables to scale.
        exclude_vars (str| list) : Name of variables to exclude from scaling.
        dlevel (INT)             : Compression/deflate level between [0-9].
                                   Default is 5.
        to_file (FILENAME)       : New file name for scaled NetCDF data.
    Return:
        None
    """
    if isinstance(from_file, str):
        from_file = _Path(from_file)

    if exclude_variables is None:
        exclude_variables = []

    if to_file is None:
        to_file = from_file

    modify = from_file == to_file
    if modify:
        to_file = _Path(str(to_file) + '.tmp')

    ds = _nch.scale_xr(_xr.open_dataset(from_file), factor, variables,
                       exclude_variables, dlevel)
    ds.to_netcdf(to_file)

    if modify:
        _remove(from_file)
        _mv(to_file, from_file)
        _log.debug(f'tmp file renamed to {from_file}')
    _log.info(f'Scaled: {from_file}')


def scale_emis(from_file, factor,
               dlevel=5, to_file=None) -> None:
    """
    Scale Emission File by xarray library.

    Args:
        from_file (FILENAME)     : NetCDF file to scale.
        factor (FLOAT)           : Scale factor.
        dlevel (INT)             : Compression/deflate level between [0-9].
                                   Default is 5.
        to_file (FILENAME)       : New file name for scaled NetCDF data.
    Return:
        None
    """
    scale_xr(from_file, factor, _emis_vars_, _exclude_vars_, dlevel, to_file)


def compress(from_file, quantize=None, dlevel=5, to_file=None) -> None:
    """
    Compress a single NetCDF File.

    Args:
        from_file (FILENAME) : File to compress.
        quantize (INT)       : Decimal precision to truncate data.
        dlevel (INT)         : Compression/deflate level between [0-9].
        to_file (FILENAME)   : New name of compressed NetCDF file.
    Return:
        None
    """
    if to_file is None:
        to_file = from_file

    modify = from_file == to_file
    if modify:
        to_file = _Path(str(to_file) + '.tmp')

    ds = _xr.open_dataset(from_file)
    ds = _nch.compress(ds, quantize, dlevel)
    ds.to_netcdf(to_file)
    ds.close()

    if modify:
        _remove(from_file)
        _mv(to_file, from_file)
        _log.debug(f'tmp file renamed to {from_file}')
    _log.info(f'Compressed: {from_file}')


def _set_or_create_attr(var, attr_name, attr_value):
    if attr_name in var.ncattrs():
        var.setncattr(attr_name, attr_value)
        return
    var.UnusedNameAttribute = attr_value
    var.renameAttribute("UnusedNameAttribute", attr_name)
    return


def ncks(from_file, quantize=None, dlevel=5, to_file=None,
         append_stats=True) -> None:
    """
    Compress a single NetCDF File by ncks.

    Args:
        from_file (FILENAME) : File to compress.
        quantize (INT)       : Decimal precision to truncate data.
        dlevel (INT)         : Compression/deflate level between [0-9].
        to_file (FILENAME)   : New name of compressed NetCDF file.
    Return:
        None
    """
    if quantize is None and dlevel is None:
        raise ValueError('One of quantize or dlevel must be set.')

    if quantize is not None:
        q = float(quantize) if quantize.startswith('.') else int(quantize)
        if isinstance(q, int) and q == 0:
            raise ValueError('NSD quantize cannot be 0.')

    if to_file is None:
        to_file = from_file

    modify = from_file == to_file
    if modify:
        to_file = _Path(str(to_file) + '.tmp')

    dfl_lvl = ["-L", str(dlevel), "--baa=8"] if dlevel is not None else []
    ppc = ["--ppc", f"default={quantize}"] if quantize is not None else []
    cmd = ["ncks", "-O", "-7", "--no_abc"] + dfl_lvl + ppc + \
          [str(from_file), str(to_file)]
    _subp.run(cmd, check=True, capture_output=True)

    if append_stats:
        pm_str = 'precision_MAXE'
        str_rmse = 'precision_RMSE'
        str_range = 'range'
        from netCDF4 import Dataset as _Dataset  # pylint: disable=E0611,C0415
        # nco1, nco2 = _Dataset(from_file, 'r'), _Dataset(to_file, 'r+')
        with _Dataset(from_file, 'r') as nco1, _Dataset(to_file, 'r+') as nco2:
            glob = {'maxe': 0, 'rmse': 0}
            for k, v in nco2.variables.items():
                x = nco1.variables[k][:]
                y = v[:]
                x_range = [x.min(), x.max()]
                y_range = [y.min(), y.max()]
                dif = x - v
                _log.debug(f'x_range: {x_range}, y_range: {y_range}')
                maxe = _np.max(abs(dif))
                rmse = _np.sqrt((dif**2).mean())
                _log.debug(f'Processed {v.name}: MAE: {maxe} RMSE: {rmse}')
                var_attrs = {str_range: y_range, pm_str: maxe, str_rmse: rmse}
                glob['maxe'] = max(glob['maxe'], maxe)
                glob['rmse'] = max(glob['rmse'], rmse)
                for k1, v1 in var_attrs.items():
                    _set_or_create_attr(v, k1, v1)
                del x, y
            gmaxe, grmse = glob['maxe'], glob['rmse']
            _log.info(f'{pm_str}: {gmaxe}, {str_rmse}: {grmse}')
            nco2.precision = quantize
            nco2.precision_MAXE = gmaxe
            nco2.precision_RMSE = grmse

    if modify:
        _remove(from_file)
        _mv(to_file, from_file)
        _log.debug(f'tmp file renamed to {from_file}')
    _log.info(f'Compressed: {from_file}')


def regrid(from_file, lats, lons, dim_names=None,  # pylint: disable=R0913
           dlevel=5, method='bilinear', to_file=None) -> None:
    """
    Regrid NetCDF file.

    Args:
        from_file (FILENAME)   : Path to file to regrid.
        lats (list)            : list of latitude values to regrid.
        lons (list)            : list of longitude values to regrid.
        dim_names (list|tuple) : name of lat/lon dimensions.
        method (str)           : regridding method. (See xesmf.Regridder)
        to_file (FILENAME)     : New path for regridded NetCDF file.

    """
    if to_file is None:
        to_file = from_file

    modify = from_file == to_file
    if modify:
        to_file = _Path(str(to_file) + '.tmp')
    ds = _xr.open_dataset(from_file, cache=False)
    ds2 = _nch.regrid(ds, lats, lons, dim_names, dlevel, method)
    ds2.to_netcdf(to_file)
    if modify:
        _remove(from_file)
        _mv(to_file, from_file)
        _log.debug(f'tmp file renamed to {from_file}')
    _log.info(f'Regridded: {from_file}')
