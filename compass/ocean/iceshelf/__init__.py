import numpy
import xarray

from mpas_tools.cime.constants import constants


def compute_land_ice_pressure_and_draft(ssh, modify_mask, ref_density):
    """
    Compute the pressure from and overlying ice shelf and the ice-shelf draft

    Parameters
    ----------
    ssh : xarray.DataArray
        The sea surface height (the ice draft)

    modify_mask : xarray.DataArray
        A mask that is 1 where ``landIcePressure`` can be deviate from 0

    ref_density : float
        A reference density for seawater displaced by the ice shelf

    Returns
    -------
    landIcePressure : xarray.DataArray
        The pressure from the overlying land ice on the ocean

    landIceDraft : xarray.DataArray
        The ice draft, equal to the initial ``ssh``
    """
    gravity = constants['SHR_CONST_G']
    landIcePressure = \
        modify_mask*numpy.maximum(-ref_density * gravity * ssh, 0.)
    landIceDraft = ssh
    return landIcePressure, landIceDraft
