from compass.model import add_model_substeps
from compass.step import Step


class Forward(Step):
    """
    A step for performing forward MPAS-Ocean runs as part of baroclinic
    channel test cases.

    Attributes
    ----------
    resolution : str
        The resolution of the test case
    """
    def __init__(self, test_case, resolution, name='forward', subdir=None,
                 ntasks=1, min_tasks=None, openmp_threads=1, mem='1GB',
                 nu=None):
        """
        Create a new test case

        Parameters
        ----------
        test_case : compass.TestCase
            The test case this step belongs to

        resolution : str
            The resolution of the test case

        name : str
            the name of the test case

        subdir : str, optional
            the subdirectory for the step.  The default is ``name``

        ntasks : int, optional
            the target number of tasks to ideally use to run the model. If too
            few cores are available on the system to accommodate the number of
            tasks and the number of cores per task, the substep will run on
            fewer tasks as long as as this is not below ``min_tasks``

        min_tasks : int, optional
            the number of tasks required to run the model.  If the system has
            too few cores to accommodate the number of tasks and cores per
            task, the step will fail

        openmp_threads : int, optional
            the number of OpenMP threads to use

        mem : str, optional
            the amount of memory that the substep is allowed to use

        nu : float, optional
            the viscosity (if different from the default for the test group)
        """
        self.resolution = resolution
        if min_tasks is None:
            min_tasks = ntasks
        super().__init__(test_case=test_case, name=name, subdir=subdir,
                         add_default_substep=False)
        self.add_namelist_file('compass.ocean.tests.baroclinic_channel',
                               'namelist.forward')
        self.add_namelist_file('compass.ocean.tests.baroclinic_channel',
                               'namelist.{}.forward'.format(resolution))
        if nu is not None:
            # update the viscosity to the requested value
            options = {'config_mom_del2': '{}'.format(nu)}
            self.add_namelist_options(options)

        # make sure output is double precision
        self.add_streams_file('compass.ocean.streams', 'streams.output')

        self.add_streams_file('compass.ocean.tests.baroclinic_channel',
                              'streams.forward')

        self.add_input_file(filename='init.nc',
                            target='../initial_state/ocean.nc')
        self.add_input_file(filename='graph.info',
                            target='../initial_state/culled_graph.info')

        self.add_output_file(filename='output.nc')

        add_model_substeps(step=self, ntasks=ntasks, min_tasks=min_tasks,
                           openmp_threads=openmp_threads, mem=mem)

    # no setup() or run() is needed
