import xarray

from mpas_tools.planar_hex import make_planar_hex_mesh
from mpas_tools.io import write_netcdf
from mpas_tools.mesh.conversion import convert, cull
from mpas_tools.cime.constants import constants

from compass.ocean.vertical import generate_grid
from compass.ocean.iceshelf import compute_land_ice_pressure_and_draft
from compass.ocean.vertical.zstar import compute_layer_thickness_and_zmid
from compass.io import add_output_file


def collect(testcase, step):
    """
    Update the dictionary of step properties

    Parameters
    ----------
    testcase : dict
        A dictionary of properties of this test case, which should not be
        modified here

    step : dict
        A dictionary of properties of this step, which can be updated
    """
    defaults = dict(cores=1, min_cores=1, max_memory=8000, max_disk=8000,
                    threads=1)
    for key, value in defaults.items():
        step.setdefault(key, value)

    for file in ['base_mesh.nc', 'culled_mesh.nc', 'culled_graph.info',
                 'initial_state.nc']:
        add_output_file(step, filename=file)


# no setup function because there's nothing more to do


def run(step, test_suite, config, logger):
    """
    Run this step of the testcase

    Parameters
    ----------
    step : dict
        A dictionary of properties of this step

    test_suite : dict
        A dictionary of properties of the test suite

    config : configparser.ConfigParser
        Configuration options for this test case

    logger : logging.Logger
        A logger for output from the step
   """
    section = config['ice_shelf_2d']
    nx = section.getint('nx')
    ny = section.getint('ny')
    dc = section.getfloat('dc')

    dsMesh = make_planar_hex_mesh(nx=nx, ny=ny, dc=dc, nonperiodic_x=False,
                                  nonperiodic_y=True)
    write_netcdf(dsMesh, 'base_mesh.nc')

    dsMesh = cull(dsMesh, logger=logger)
    dsMesh = convert(dsMesh, graphInfoFileName='culled_graph.info',
                     logger=logger)
    write_netcdf(dsMesh, 'culled_mesh.nc')

    section = config['ice_shelf_2d']
    temperature = section.getfloat('temperature')
    surface_salinity = section.getfloat('surface_salinity')
    bottom_salinity = section.getfloat('bottom_salinity')

    interfaces = generate_grid(config=config)

    bottom_depth = interfaces[-1]
    vert_levels = len(interfaces) - 1

    # points 1 and 2 are where angles on ice shelf are located.
    # point 3 is at the surface.
    # d variables are total water-column thickness below ice shelf
    y1 = section.getfloat('y1')
    y2 = section.getfloat('y2')
    y3 = y2 + section.getfloat('edge_width')
    d1 = section.getfloat('cavity_thickness')
    d2 = d1 + section.getfloat('slope_height')
    d3 = bottom_depth

    ds = dsMesh.copy()

    ds['refBottomDepth'] = ('nVertLevels', interfaces[1:])
    ds['refZMid'] = ('nVertLevels', -0.5 * (interfaces[1:] + interfaces[0:-1]))
    ds['vertCoordMovementWeights'] = xarray.ones_like(ds.refBottomDepth)

    yCell = ds.yCell
    ds['bottomDepth'] = bottom_depth * xarray.ones_like(yCell)
    ds['maxLevelCell'] = vert_levels * xarray.ones_like(yCell, dtype=int)

    column_thickness = xarray.where(yCell < y1, d1,
                                    d1 + (d2 - d1) * (yCell - y1) / (y2 - y1))
    column_thickness = xarray.where(yCell < y2, column_thickness,
                                    d2 + (d3 - d2) * (yCell - y2) / (y3 - y2))
    column_thickness = xarray.where(yCell < y3, column_thickness, d3)

    ssh = -bottom_depth + column_thickness

    cellMask = xarray.ones_like(yCell)
    cellMask, _ = xarray.broadcast(cellMask, ds.refBottomDepth)
    cellMask = cellMask.transpose('nCells', 'nVertLevels')

    restingThickness, layerThickness, zMid = compute_layer_thickness_and_zmid(
        cellMask, ds.refBottomDepth, ds.bottomDepth, ds.maxLevelCell-1,
        ssh=ssh)

    layerThickness = layerThickness.expand_dims(dim='Time', axis=0)
    ssh = ssh.expand_dims(dim='Time', axis=0)
    modify_mask = xarray.where(yCell < y3, 1, 0).expand_dims(
        dim='Time', axis=0)
    landIceFraction = modify_mask.astype(float)
    landIceMask = modify_mask.copy()

    ref_density = constants['SHR_CONST_RHOSW']
    landIcePressure, landIceDraft = compute_land_ice_pressure_and_draft(
        ssh=ssh, modify_mask=modify_mask, ref_density=ref_density)

    salinity = surface_salinity + ((bottom_salinity - surface_salinity) *
                                   (zMid / (-bottom_depth)))
    salinity, _ = xarray.broadcast(salinity, layerThickness)
    salinity = salinity.transpose('Time', 'nCells', 'nVertLevels')

    normalVelocity = xarray.zeros_like(ds.xEdge)
    normalVelocity, _ = xarray.broadcast(normalVelocity, ds.refBottomDepth)
    normalVelocity = normalVelocity.transpose('nEdges', 'nVertLevels')
    normalVelocity = normalVelocity.expand_dims(dim='Time', axis=0)

    ds['temperature'] = temperature * xarray.ones_like(layerThickness)
    ds['salinity'] = salinity
    ds['normalVelocity'] = normalVelocity
    ds['layerThickness'] = layerThickness
    ds['ssh'] = ssh
    ds['restingThickness'] = restingThickness
    ds['fCell'] = xarray.zeros_like(ds.xCell)
    ds['fEdge'] = xarray.zeros_like(ds.xEdge)
    ds['fVertex'] = xarray.zeros_like(ds.xVertex)
    ds['modifyLandIcePressureMask'] = modify_mask
    ds['landIceFraction'] = landIceFraction
    ds['landIceMask'] = landIceMask
    ds['landIcePressure'] = landIcePressure
    ds['landIceDraft'] = landIceDraft

    write_netcdf(ds, 'initial_state.nc')
