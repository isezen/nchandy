# pylint: disable=C0103
"""
nchandy CLI Module.

~~~~~~~~~
CLI module
"""
from os import getcwd as _getcwd
from os import makedirs as _makedirs
from os.path import isdir as _isdir
from os.path import isfile as _isfile
from os.path import split as _split
from pathlib import Path as _Path
from filecmp import cmp as _cmp
from shutil import copy2 as _copy2

import functools
# import logging as _logging
import click

from nchandy import __version__
from nchandy import _log_level_names_
from nchandy import _set_logger_
from nchandy import is_netcdf as _is_netcdf
from nchandy import _update_is_required_compress
from nchandy import _update_is_required_regrid
from nchandy import file as _file

_cli_log_levels_ = click.Choice(_log_level_names_)
_txt1_ = '%s is not a valid netcdf file. Copied to target.'


def _common_start(sa, sb):
    """Return the longest common substring from the beginning of sa and sb."""
    def _iter():
        for a, b in zip(sa, sb):
            if a == b:
                yield a
            else:
                return

    return ''.join(_iter())


def _get_source_dir(source):
    """Get source_dir from file names."""
    source_dir = ''
    if len(source) > 1:
        source_dir = source[0]
        for i in source[1:]:
            source_dir = _common_start(source_dir, i)
            if source_dir == '':
                break
        if not _isdir(source_dir):
            source_dir, _ = _split(source_dir)
    return source_dir


def _get_file_args(paths, recursive=True):
    """Get file/path arguments."""
    if isinstance(paths, str):
        paths = [paths]
    if isinstance(paths, tuple):
        paths = list(paths)
    if len(paths) == 1:
        source, target = paths[0], paths[0]
    elif len(paths) == 2:
        source, target = paths[0], paths[1]
    else:
        target = paths.pop() if _isdir(paths[-1]) else _getcwd()
        source = paths

    source_dir = None
    if not isinstance(source, (list, tuple)):
        if _isdir(source):
            source_dir = _Path(source)
            source = list(source_dir.rglob("*.*") if recursive
                          else source_dir.glob("*.*"))
        elif _isfile(source):
            source = [source]
        else:
            raise ValueError('Error in source files')

    source = [_Path(i) for i in source]
    if source_dir is None:
        source_dir = _get_source_dir([str(i) for i in source])

    if _isfile(target):
        if len(source) > 1:
            raise ValueError('Target must be a directory')

    return source, _Path(source_dir), _Path(target)


class FilesDefaultToStdin(click.Argument):
    """Helper Class to get PATHS argument."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        kwargs['nargs'] = -1
        kwargs['type'] = click.Path()
        super().__init__(*args, **kwargs)

    def full_process_value(self, ctx, value):
        """Process value."""
        print('HELLO')
        return super().process_value(ctx, value or ('-', ))


class SpecialEpilog(click.Group):
    """Special Epilog Class."""

    def format_epilog(self, ctx, formatter):
        """Format epilog."""
        if self.epilog:
            formatter.write_paragraph()
            for line in self.epilog.split('\n'):
                formatter.write_text(line)


def _common_options(func):
    """Return common options for CLI functions."""
    @click.option('--recursive', '-r', default=True, is_flag=True,
                  help='Scan sub-folders recursively for nc files')
    @click.option('--copy-non-nc-files', '-c', default=True, is_flag=True,
                  help='Scan sub-folders recursively for nc files')
    @click.option('--dlevel', '-d', default=5,
                  help='Compression/deflate level between [0-9].')
    @click.option('--overwrite', '-o', default=False,
                  is_flag=True, help='Overwrite if file exist.')
    @click.option('--log', '-l', type=click.Path(), default=None,
                  required=False, help='Log file path.')
    @click.option('--log-level', '-ll', type=_cli_log_levels_, default='INFO',
                  required=False, help='Logging level.')
    @click.option('--verbose', '-v', default=False,
                  is_flag=True, help='Show verbose output.')
    @click.argument('paths', cls=FilesDefaultToStdin)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


@click.group()
def cli():
    """Nchandy CLI."""


@cli.command("version", short_help="Show version")
def version_cmd() -> None:
    """Get version."""
    print(__version__)


@cli.command("scale", short_help="Scale NetCDF File(s)",
             context_settings={'show_default': True})
@click.argument('factor', type=float, required=True)
@_common_options
def scale_cmd(paths, factor, recursive,  # pylint: disable=R0912,R0913,R0914
              copy_non_nc_files, dlevel, overwrite,
              log, log_level, verbose) -> None:
    r"""
    Scale NetCDF File(s) by factor of a floating number.

    \b
    Args:
        FACTOR (float)  : Scaling factor.
        PATHS  (str)    : Files/Paths to regrid from/to.
                          Default is current directory.
    ~~~~~~~~~~~~~
    \b
    Examples:
        $ nch scale -v 0.5 path/to/files/*.nc /target/dir
        $ nch scale -v 0.2 path/to/nc_files /target/dir
        $ nch scale -v 0.4 path/to/nc_files
    """
    _log = _set_logger_('scale', verbose, log_level, log)
    if len(paths) == 0:
        paths = tuple([_getcwd()])

    source, source_dir, target = _get_file_args(paths, recursive)

    for f1 in source:
        f2 = target if source_dir == '' else \
            _Path(str(f1).replace(str(source_dir), str(target)))
        _makedirs(f2.parent, exist_ok=True)
        scale = False
        if _isfile(f1):
            if not _is_netcdf(f1):
                if _isfile(f2):
                    if _cmp(f1, f2):
                        _log.debug(f'Comparing {f1} with {f2}')
                        msg = f"{f1} is identical to target."
                        _log.debug(msg)
                else:
                    if copy_non_nc_files:
                        _copy2(f1, f2)
                        _log.debug(_txt1_, f1)
                scale = False
                continue
        else:
            continue

        if _isfile(f2):
            if _is_netcdf(f2):
                if not overwrite:
                    raise FileExistsError('Use --overwrite to overwrite files')
            else:
                if copy_non_nc_files:
                    _copy2(f1, f2)
                    _log.debug(_txt1_, f1)
        else:
            scale = True

        if scale:
            _file.scale_xr(f1, factor, dlevel=dlevel, to_file=f2)


@cli.command("regrid", short_help="Regrid NetCDF File(s)",
             context_settings={'show_default': True})
@click.option('--lats', '-n', default=[-90, 90, 192],
              nargs=3, help='Latitude boundaries (LAT_MIN, LAT_MAX, NLATS).')
@click.option('--lons', '-m', default=[0, 358.75, 288],
              nargs=3, help='Longitude boundaries (LON_MIN, LON_MAX, NLONS).')
@click.option('--gridfile', '-g', default=None, required=False,
              help='Grid File to get lat/lon information.' +
                   ' If this arg is defined, overrides lats/lons args.')
@click.option('--dim_names', '-dn', default=None,
              required=False, nargs=2, help='latitude/longitude dim name.')
@_common_options
def regrid_cmd(paths, lats, lons,  # pylint: disable=R0912,R0913,R0914
               gridfile, dim_names, recursive, copy_non_nc_files, dlevel,
               overwrite, log, log_level, verbose) -> None:
    r"""
    Regrid NetCDF File(s).

    \b
    Args:
        PATHS (str): Files/Paths to regrid from/to.
                     Default is current directory.
    ~~~~~~~~~~~~~
    \b
    Examples:
        $ nch regrid -v -n -90, 90, 192 -m 0 358.75 288 path/to/files/*.nc\
 /target/dir
        $ nch regrid -v -g gridcro.nc -d 0 path/to/nc_files /target/dir
        $ nch regrid -v -dn dim1 dim2 path/to/nc_files
    """
    _log = _set_logger_('regrid', verbose, log_level, log)
    if len(paths) == 0:
        paths = tuple([_getcwd()])

    source, source_dir, target = _get_file_args(paths, recursive)

    if gridfile is not None:
        raise NotImplementedError('This feature is not implemented yet.')

    for f1 in source:
        f2 = target if source_dir == '' else \
             _Path(str(f1).replace(str(source_dir), str(target)))
        _makedirs(f2.parent, exist_ok=True)
        rg = False
        if _isfile(f1):
            if not _is_netcdf(f1):
                if _isfile(f2):
                    if _cmp(f1, f2):
                        msg = f"{f1} is identical to target."
                        _log.debug(msg)
                else:
                    if copy_non_nc_files:
                        _copy2(f1, f2)
                        _log.debug(_txt1_, f1)
                rg = False
                continue
        else:
            continue

        if _isfile(f2):
            if _is_netcdf(f2):
                rg = _update_is_required_regrid(f2, lats, lons, dim_names)
                if not rg:
                    _log.info(f"{f2} is already regridded.")
                elif not overwrite:
                    raise FileExistsError('Use --overwrite to overwrite files')
            else:
                if copy_non_nc_files:
                    _copy2(f1, f2)
                    _log.debug(_txt1_, f1)

        else:
            rg = True

        if rg:
            try:
                _file.regrid(f1, lats, lons, dim_names, dlevel, to_file=f2)
            except ImportError:
                msg = '*** Install xesmf library to use this functionality ***'
                print(msg)
                break


@cli.command("compress", short_help="Compress NetCDF file(s)",
             context_settings={'show_default': True})
@click.option('--quantize', '-q', default=2,
              help='Truncate data in variables to a given ' +
                   'decimal precision after significant digit, e.g. -q 2.')
@_common_options
def compress_cmd(paths, quantize,  # pylint: disable=R0912,R0913,R0914
                 recursive, copy_non_nc_files, dlevel, overwrite,
                 log, log_level, verbose) -> None:
    r"""
    Compress NetCDF File(s).

    \b
    Args:
        PATHS (str): Files/Paths to compress from/to.
                     Default is current directory.
    ~~~~~~~~~~~~~
    \b
    Examples:
        $ nch compress -v -q 4 -d 0 path/to/files/*.nc /target/dir
        $ nch compress -v -d 9 gridcro.nc -d 0 path/to/nc_files /target/dir
        $ nch compress -v -q 5 -d 9 path/to/nc_files
    """
    _log = _set_logger_('compress', verbose, log_level, log)
    if len(paths) == 0:
        paths = tuple([_getcwd()])

    source, source_dir, target = _get_file_args(paths, recursive)

    for f1 in source:
        f2 = target if source_dir == '' else \
            _Path(str(f1).replace(str(source_dir), str(target)))
        _makedirs(f2.parent, exist_ok=True)
        compress = False
        if _isfile(f1):
            if not _is_netcdf(f1):
                if _isfile(f2):
                    if _cmp(f1, f2):
                        _log.debug(f'Comparing {f1} with {f2}')
                        msg = f"{f1} is identical to target."
                        _log.debug(msg)
                else:
                    if copy_non_nc_files:
                        _copy2(f1, f2)
                        _log.debug(_txt1_, f1)
                compress = False
                continue
        else:
            continue

        if _isfile(f2):
            if _is_netcdf(f2):
                compress = _update_is_required_compress(f2, quantize, dlevel)
                if not compress:
                    _log.info(f"{f2} is already compressed.")
                elif not overwrite:
                    raise FileExistsError('Use --overwrite to overwrite files')
            else:
                if copy_non_nc_files:
                    _copy2(f1, f2)
                    _log.debug(_txt1_, f1)
        else:
            compress = True

        if compress:
            _file.compress(f1, quantize, dlevel, f2)


def main() -> None:  # noqa: D401
    """Main entry point."""
    cli()
