# pylint: disable=C0103
"""
nchandy
~~~~~~~~~
Handy NetCDF tools

This package contains functions and tools to work with
 NetCDF files.

:github: https://github.com/isezen/nchandy
:docs: https://github.com/isezen/nchandy
:author: Ismail SEZEN (sezenismail@gmail.com)
"""

from math import log10 as _log10
from math import floor as _floor
import logging as _logging
import numpy as _np
import xarray as _xr

from nchandy import file
from nchandy.file import _log

__all__ = ['file', ]
__version__ = '0.0.1.dev'
__author__ = 'Ismail SEZEN'
__email__ = 'sezenismail@gmail.com'
__license__ = 'AGPL v3.0'
__year__ = '2022'

# fh = _logging.FileHandler(s.log.file)
# fh.setLevel(logging.INFO)
# fh.setFormatter(formatter)
# log.addHandler(fh)
_log_level_names_ = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
_log_levels_ = dict(zip(_log_level_names_, range(10, 60, 10)))
_log_formatter_ = _logging.Formatter(
    '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S')


def _update_is_required_compress(f, quantize=2, dlevel=5):
    """Check NetCDF file is compressed or not."""
    dp_str = 'precision'
    compression_changed = False
    with _xr.open_dataset(f, engine='netcdf4') as ds:
        for _, v in ds.variables.items():
            if v.encoding['complevel'] != dlevel:
                compression_changed = True
                break
        if dp_str in ds.attrs.keys():
            if ds.attrs[dp_str] is not None and quantize is not None:
                if quantize >= ds.attrs[dp_str]:
                    quantize = None
        if quantize is not None:
            compression_changed = True
    return compression_changed


def _update_is_required_regrid(f, lats, lons, dim_names=None):
    """Check NetCDF file is regridded previously."""
    with _xr.open_dataset(f, engine='netcdf4') as ds:
        latn, lonn = _find_dim_names(ds) if dim_names is None \
                     else tuple(dim_names)
        if 'regrid_method' in ds.attrs.keys():  # if contains attribute
            xlats, xlons = ds[latn].values, ds[lonn].values
            if all(xlats != lats):
                return True
            if all(xlons != lons):
                return True
        else:
            return True
    return False


def _set_logger_(name, verbose=False,
                 log_level='INFO', logfile=None) -> None:
    _log.name = name
    _log.setLevel(_log_levels_[log_level])
    if verbose:
        handler = _logging.StreamHandler()
        handler.setFormatter(_log_formatter_)
        _log.addHandler(handler)
    if logfile is not None:
        handler = _logging.FileHandler(logfile)
        handler.setFormatter(_log_formatter_)
        _log.addHandler(handler)
    return _log


def _check_ds(ds) -> None:
    ds_types = (_xr.core.dataset.Dataset,
                _xr.core.dataarray.DataArray,
                _xr.core.variable.Variable)
    if not isinstance(ds, ds_types):
        type_names = [str(i).split("'")[1] for i in ds_types]
        type_names = [f"'{i}'" for i in type_names]
        type_names = ' or '.join(type_names)
        raise TypeError(f'ds must be an instance of {type_names}.')


def _check_int(x, name) -> None:
    if x is not None:
        if not isinstance(x, int):
            raise TypeError(f'{name} must be integer')


def _check_dlevel(x) -> None:
    _check_int(x, 'dlevel')
    if x is not None:
        if not 0 <= x <= 9:
            raise ValueError('dlevel must be between (0,9)')


def _exp10(x):
    return max(10**(-_floor(_log10(x))) if x > 0 else 1, 1)


def _exp10_2(x):
    return 10**(-_np.floor(_np.log10(x)))


def is_netcdf(f):
    """
    Check file is a valid netcdf file.

    Args:
    f (FILENAME): A valid file name
    """
    try:
        _xr.open_dataset(f, engine='netcdf4')
    except OSError:
        return False
    return True


def scale_ncdf(nco, factor, variables=None, exclude_variables=('TFLAG',)):
    """
    Scale netCDF4.Dataset object.

    Args:
        nco (netCDF4.Dataset)     : NetCDF4.Dataset object
        factor (FLOAT)           : Scale factor.
        variables (str|list)     : Name of variables to scale.
        exclude_vars (str| list) : Name of variables to exclude from scaling.
                                   Default is 'TFLAG'.
    Return:
        netCDF4.Dataset object
    """
    try:
        from netCDF4 import Dataset as _Dataset  # pylint: disable=E0611,C0415
        if not isinstance(nco, _Dataset):
            raise TypeError("nco must be an instance of 'netCDF4.Dataset'")
    except ImportError:
        print('Install netCDF4 library to use this functionality')
        return None

    nco_vars = list(nco.variables.keys())
    if variables is None:
        variables = nco_vars
    for k in variables:
        if k not in nco_vars:
            _log.debug(f'Var:{k} was not found in dataset. Skipping!')
            continue
        if k not in exclude_variables:
            nco[k][:] *= factor
            _log.debug(f'{k} variable scaled by {factor}')
    return nco


def scale_xr(ds, factor, variables=None, exclude_variables=('TFLAG',),
             dlevel=5):
    """
    Scale NetCDF File by xarray library.

    Args:
        ds (xarray.Dataset)      : xarray.Dataset object.
        factor (FLOAT)           : Scale factor.
        variables (str|list)     : Name of variables to scale.
        exclude_vars (str| list) : Name of variables to exclude from scaling.
        dlevel (INT)             : Compression/deflate level between [0-9].
                                   Default is 5.
    Return:
        xarray.Dataset object.
    """
    _check_dlevel(dlevel)
    ds = ds.copy(deep=True)
    if variables is None:
        variables = list(ds.variables)
    # log.debug(f'Scaling {from_file}')
    for k in variables:
        if k not in ds.variables:
            _log.debug(f'Var:{k} was not found in dataset. Skipping!')
            continue
        if k not in exclude_variables:
            encoding, attrs = ds[k].encoding, ds[k].attrs
            ds[k] = ds[k].astype('float64') * factor
            ds[k].encoding, ds[k].attrs = encoding, attrs
            _log.debug(f'{k} variable scaled by {factor}')
            ds[k].attrs['scale_factor'] = factor
    if dlevel is not None:
        for k in ds.keys():
            ds[k].encoding.update(
                {'dtype': _np.dtype('float32'), 'zlib': True,
                 'complevel': dlevel})

    return ds


def scale_emis(ds, factor, dlevel=5):
    """
    Scale emission File by xarray library.

    Args:
        ds (xarray.Dataset)      : xarray.Dataset object.
        factor (FLOAT)           : Scale factor.
        dlevel (INT)             : Compression/deflate level between [0-9].
                                   Default is 5.
    Return:
        xarray.Dataset object.
    """
    return scale_xr(ds, factor,
                    file._emis_vars_,  # pylint: disable=W0212
                    file._exclude_vars_,  # pylint: disable=W0212
                    dlevel)


def compress(ds, quantize=None, dlevel=5):  # pylint: disable=R0912
    """
    Compress a single NetCDF File.

    Args:
        ds (xarray.Dataset)  : xarray.Dataset object
        quantize (INT)       : Decimal precision to truncate data.
                               Default is no quantization.
        dlevel (INT)         : Compression/deflate level between [0-9].
                               Default is 5.
    Return:
        xarray.Dataset object.
    """
    _check_ds(ds)
    _check_int(quantize, 'quantize')
    _check_dlevel(dlevel)
    pm_str = 'precision_MAE'
    if isinstance(ds, _xr.core.variable.Variable):
        dt = ds.dtype
        old_enc = ds.encoding.copy()
        if str(ds.dtype).startswith('float') and quantize is not None:
            q = 0.0
            mx = ds.max().values.tolist()
            mn = ds.min().values.tolist()
            # if (ds != 0.0).all():
            #     m = ds.where(ds != 0.0)
            #     mx, mn = m.max().values.tolist(), m.min().values.tolist()
            #     q = m.quantile(q=0.90).values.tolist()
            #     q = m.mean().values.tolist()
            #     q = m.max().values.tolist()
            #     e = _exp10_2(abs(m))
            #     e = stats.mode(e)
            #     vals, counts = _np.unique(e, return_counts=True)
            #     index = _np.argmax(counts)
            #     e = vals[index]
            #     print(e)
            # e = _exp10(abs(q))
            e = 1
            _log.debug(f'Max: {mx}, Min: {mn}, exp: {e}, q: {q}')
            e = _np.array(e).astype('float64')
            r = (_np.round(ds.astype('float64') * e, quantize) / e).astype(dt)
            mae = _np.max(abs(ds - r)).astype(dt)
            r.attrs[pm_str] = mae.values.tolist()
            ds = r
        if dlevel is not None:
            old_enc.update({'zlib': True, 'shuffle': True,
                            'complevel': dlevel})
            ds.encoding = old_enc

    if isinstance(ds, _xr.core.dataarray.DataArray):
        v = compress(ds.variable, quantize, dlevel)
        ds = _xr.DataArray(v, name=ds.name, attrs=v.attrs)
        ds.encoding = v.encoding.copy()
        if pm_str in ds.attrs.keys():
            _log.debug(f'Processed {ds.name}: MAE: {ds.attrs[pm_str]}')

    if isinstance(ds, _xr.core.dataarray.Dataset):
        ds2 = ds.copy(deep=True)
        glob_mae = 0
        for k in list(ds2.keys()):
            ds2[k] = compress(ds2[k], quantize, dlevel)
            if pm_str in ds2[k].attrs.keys():
                glob_mae = max(glob_mae, ds2[k].attrs[pm_str])

        if quantize is not None:
            ds2.attrs.update({'decimal_precision': quantize,
                              pm_str: glob_mae})
            _log.info(f'{pm_str}: {glob_mae}')
        return ds2
    return ds


def _find_dim_names(ds, lat_name='lat', lon_name='lon'):
    """
    Find exact lat/lon dimension names in xarray dataset.

    Args:
        ds (xarray.Dataset) : xarray Dataset object
        lat_name (str)      : lat name to search in coords.
        lon_name (str)      : lon name to search in coords.
    Return:
        tuple of lat/lon names
    """
    dim_names = list(ds.dims.keys())
    coord = {}
    for j in [lat_name, lon_name]:
        dim_name = {j: i for i in dim_names if j in i}
        if len(dim_name) == 0:
            raise ValueError(f'dimension {j} name was not found')
        if len(dim_name) > 1:
            raise ValueError(f'Ambiguous dimension name for {j}')
        coord.update(dim_name)
    return coord[lat_name], coord[lon_name]


def regrid(ds, lats, lons, dim_names=None,  # pylint: disable=R0913
           dlevel=5, method='bilinear'):
    """
    Regrid xarray dataset.

    Args:
        ds (xarray.Dataset)    : xarray.Dataset object
        lats (list)            : list of latitude values to regrid.
        lons (list)            : list of longitude values to regrid.
        dim_names (list|tuple) : name of lat/lon dimensions.
        dlevel (INT)           : Compression/deflate level between [0-9].
                                 Default is 5.
        method (str)           : regridding method. (See xesmf.Regridder)
    Return:
        xarray.Dataset object
    """
    # try:
    import xesmf as xe  # pylint: disable=E0401,C0415
    # except ImportError:
    #     print('*** Install xesmf library to use this functionality ***')
    #     return None
    _check_dlevel(dlevel)
    latn, lonn = _find_dim_names(ds) if dim_names is None else tuple(dim_names)
    ds = ds.rename({latn: 'lat', lonn: 'lon'})
    ds2 = _xr.Dataset(
        {
            "lat": (["lat"], lats),
            "lon": (["lon"], lons),
        }
    )
    regridder = xe.Regridder(ds, ds2, method, periodic=True)
    ds2 = regridder(ds)
    if dlevel is not None:
        for k in ds2.keys():
            ds2[k].encoding.update(
                {'dtype': _np.dtype('float32'), 'zlib': True,
                 'complevel': dlevel})
    return ds2
