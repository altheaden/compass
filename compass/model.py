import os
import xarray
import numpy

from mpas_tools.logging import check_call

from compass import Substep


def add_model_substeps(step, ntasks=1, min_tasks=1, openmp_threads=1,
                       mem='1GB', update_pio=True, partition_graph=True,
                       graph_file='graph.info', namelist=None, streams=None,
                       substep_prefix='model'):
    """
    Run the model after determining the number of cores

    Parameters
    ----------
    step : compass.Step
        a step

    ntasks : int, optional
        the target number of tasks the model substep would ideally use.  If too
        few cores are available on the system to accommodate the number of
        tasks and the number of cores per task, the substep will run on
        fewer tasks as long as as this is not below ``min_tasks``

    min_tasks : int, optional
        the number of tasks the model substep requires.  If the system has too
        few cores to accommodate the number of tasks and cores per task,
        the step will fail

    openmp_threads : int, optional
        the number of OpenMP threads the model will use

    mem : str, optional
        the amount of memory that the model substep is allowed to use

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

    substep_prefix : str, optional
        The prefix to use for the names of the substeps
    """

    step.add_model_as_input()

    model_substep = ModelSubstep(step, substep_prefix, ntasks, min_tasks,
                                 openmp_threads, mem, namelist, streams)
    model_setup_substep = ModelSetupSubstep(step, substep_prefix,
                                            model_substep,  update_pio,
                                            partition_graph, graph_file)
    step.add_substep(model_setup_substep)
    step.add_substep(model_substep)


class ModelSetupSubstep(Substep):
    def __init__(self, step, prefix, model_substep, update_pio,
                 partition_graph, graph_file):
        """
        Make a substep for setting up the model right before running

        Parameters
        ----------
        step : compass.Step
            A step that this substep belongs to

        prefix : str
            The prefix to use in the name of the substep

        model_substep : compass.model.ModelSubstep
            The substep for running the model

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
        """
        super().__init__(step=step, name=f'{prefix}_setup')
        self.model_substep = model_substep
        self.update_pio = update_pio
        self.partition_graph = partition_graph
        self.graph_file = graph_file

    def run(self):
        """ Run the substep """
        namelist = self.model_substep.namelist
        cores = self.model_substep.ntasks
        config = self.step.config
        logger = self.step.logger

        if self.update_pio:
            self.update_namelist_pio(namelist)

        if self.partition_graph:
            partition(cores, config, logger, graph_file=self.graph_file)

    def update_namelist_pio(self, out_name=None):
        """
        Modify the namelist so the number of PIO tasks and the stride between
        them consistent with the number of nodes and cores (one PIO task per
        node).

        Parameters
        ----------
        out_name : str, optional
            The name of the namelist file to write out, ``namelist.<core>`` by
            default
        """
        config = self.step.config
        cores = self.model_substep.cpus_per_task

        if out_name is None:
            out_name = 'namelist.{}'.format(self.step.mpas_core.name)

        cores_per_node = config.getint('parallel', 'cores_per_node')

        # update PIO tasks based on the machine settings and the available
        # number or cores
        pio_num_iotasks = int(numpy.ceil(cores / cores_per_node))
        pio_stride = cores // pio_num_iotasks
        if pio_stride > cores_per_node:
            raise ValueError('Not enough nodes for the number of cores.  '
                             'cores: {}, cores per node: {}'.format(
                cores, cores_per_node))

        replacements = {'config_pio_num_iotasks': '{}'.format(pio_num_iotasks),
                        'config_pio_stride': '{}'.format(pio_stride)}

        self.step.update_namelist_at_runtime(options=replacements,
                                             out_name=out_name)


class ModelSubstep(Substep):
    def __init__(self, step, name, ntasks, min_tasks, openmp_threads,
                 mem, namelist, streams):
        """
        Make a substep for running the model

        Parameters
        ----------
        step : compass.Step
            A step that this substep belongs to

        name : str
            The name of the substep

        ntasks : int
            the target number of tasks the substep would ideally use.  If too
            few cores are available on the system to accommodate the number of
            tasks and the number of cores per task, the substep will run on
            fewer tasks as long as as this is not below ``min_tasks``

        min_tasks : int
            the number of tasks the substep requires.  If the system has too
            few cores to accommodate the number of tasks and cores per task,
            the step will fail

        openmp_threads : int
            the number of OpenMP threads to use

        mem : str
            the amount of memory that the substep is allowed to use

        namelist : {str, None}
            The name of the namelist file

        streams : {str, None}
            The name of the streams file
        """
        super().__init__(step=step, name=name, cpus_per_task=openmp_threads,
                         min_cpus_per_task=openmp_threads, ntasks=ntasks,
                         min_tasks=min_tasks, openmp_threads=openmp_threads,
                         mem=mem)

        mpas_core = self.step.mpas_core.name
        if namelist is None:
            namelist = 'namelist.{}'.format(mpas_core)

        if streams is None:
            streams = 'streams.{}'.format(mpas_core)

        self.namelist = namelist
        self.streams = streams

    def set_model_resources(self, ntasks=None, min_tasks=None,
                            openmp_threads=None, mem=None):
        """
        Update the resources for the subtask.  This can be done within init,
        ``setup()`` or ``runtime_setup()`` for the step that this substep
        belongs to, or init, ``configure()`` or ``run()`` for the test case
        that this substep belongs to.

        Parameters
        ----------
        ntasks : int, optional
            the number of tasks the substep would ideally use.  If too few
            cores are available on the system to accommodate the number of
            tasks and the number of cores per task, the substep will run on
            fewer tasks as long as as this is not below ``min_tasks``

        min_tasks : int, optional
            the number of tasks the substep requires.  If the system has too
            few cores to accommodate the number of tasks and cores per task,
            the step will fail

        openmp_threads : int, optional
            the number of OpenMP threads to use

        mem : str, optional
            the amount of memory that the substep is allowed to use
        """
        self.set_resources(cpus_per_task=openmp_threads,
                           min_cpus_per_task=openmp_threads, ntasks=ntasks,
                           min_tasks=min_tasks, openmp_threads=openmp_threads,
                           mem=mem)

    def setup(self):
        """ Setup the command-line arguments """
        config = self.step.config
        model = config.get('executables', 'model')
        model_basename = os.path.basename(model)
        self.args = ['./{}'.format(model_basename), '-n', self.namelist,
                     '-s', self.streams]


def partition(cores, config, logger, graph_file='graph.info'):
    """
    Partition the domain for the requested number of cores

    Parameters
    ----------
    cores : int
        The number of cores that the model should be run on

    config : compass.config.CompassConfigParser
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
