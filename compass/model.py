import os
import xarray

from mpas_tools.logging import check_call


def run_model(step, update_pio=True, partition_graph=True,
              graph_file='graph.info', namelist=None, streams=None):
    """
    Run the model after determining the number of cores

    Parameters
    ----------
    step : compass.Step
        a step

    update_pio : bool, optional
        Whether to modify the namelist so the number of PIO tasks and the
        stride between them is consistent with the number of nodes and cores
        (one PIO task per node).

    partition_graph : bool, optional
        Whether to partition the domain for the requested number of cores.  If
        so, the partitioning executable is taken from the ``partition`` option
        of the ``[executables]`` config section.

    graph_file : str, optional
        The name of the graph file to partition

    namelist : str, optional
        The name of the namelist file, default is ``namelist.<core>``

    streams : str, optional
        The name of the streams file, default is ``streams.<core>``
    """
    mpas_core = step.mpas_core.name
    cores = step.cores
    threads = step.threads
    config = step.config
    logger = step.logger

    if namelist is None:
        namelist = 'namelist.{}'.format(mpas_core)

    if streams is None:
        streams = 'streams.{}'.format(mpas_core)

    if update_pio:
        step.update_namelist_pio(namelist)

    if partition_graph:
        partition(cores, config, logger, graph_file=graph_file)

    os.environ['OMP_NUM_THREADS'] = '{}'.format(threads)

    parallel_executable = config.get('parallel', 'parallel_executable')
    model = config.get('executables', 'model')
    model_basename = os.path.basename(model)

    # split the parallel executable into constituents in case it includes flags
    args = parallel_executable.split(' ')
    args.extend(['-n', '{}'.format(cores),
                 './{}'.format(model_basename),
                 '-n', namelist,
                 '-s', streams])

    check_call(args, logger)


def partition(cores, config, logger, graph_file='graph.info'):
    """
    Partition the domain for the requested number of cores

    Parameters
    ----------
    cores : int
        The number of cores that the model should be run on

    config : configparser.ConfigParser
        Configuration options for the test case, used to get the partitioning
        executable

    logger : logging.Logger
        A logger for output from the step that is calling this function

    graph_file : str, optional
        The name of the graph file to partition

    """
    if cores > 1:
        executable = config.get('parallel', 'partition_executable')
        args = [executable, graph_file, '{}'.format(cores)]
        check_call(args, logger)


def make_graph_file(mesh_filename, graph_filename='graph.info',
                    weight_field=None):
    """
    Make a graph file from the MPAS mesh for use in the Metis graph
    partitioning software

    Parameters
    ----------
     mesh_filename : str
        The name of the input MPAS mesh file

    graph_filename : str, optional
        The name of the output graph file

    weight_field : str
        The name of a variable in the MPAS mesh file to use as a field of
        weights
    """

    with xarray.open_dataset(mesh_filename) as ds:

        nCells = ds.sizes['nCells']

        nEdgesOnCell = ds.nEdgesOnCell.values
        cellsOnCell = ds.cellsOnCell.values - 1
        if weight_field is not None:
            if weight_field in ds:
                raise ValueError('weight_field {} not found in {}'.format(
                    weight_field, mesh_filename))
            weights = ds[weight_field].values
        else:
            weights = None

    nEdges = 0
    for i in range(nCells):
        for j in range(nEdgesOnCell[i]):
            if cellsOnCell[i][j] != -1:
                nEdges = nEdges + 1

    nEdges = nEdges/2

    with open(graph_filename, 'w+') as graph:
        if weights is None:
            graph.write('{} {}\n'.format(nCells, nEdges))

            for i in range(nCells):
                for j in range(0, nEdgesOnCell[i]):
                    if cellsOnCell[i][j] >= 0:
                        graph.write('{} '.format(cellsOnCell[i][j]+1))
                graph.write('\n')
        else:
            graph.write('{} {} 010\n'.format(nCells, nEdges))

            for i in range(nCells):
                graph.write('{} '.format(int(weights[i])))
                for j in range(0, nEdgesOnCell[i]):
                    if cellsOnCell[i][j] >= 0:
                        graph.write('{} '.format(cellsOnCell[i][j] + 1))
                graph.write('\n')
