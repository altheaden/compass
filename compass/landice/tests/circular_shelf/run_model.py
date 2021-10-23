from compass.model import add_model_substeps
from compass.step import Step


class RunModel(Step):
    """
    A step for performing forward MALI runs as part of circular_shelf
    test cases.

    Attributes
    ----------
    suffixes : list of str, optional
        a list of suffixes for namelist and streams files produced
        for this step.  Most steps most runs will just have a
        ``namelist.landice`` and a ``streams.landice`` (the default) but
        the ``restart_run`` step of the ``restart_test`` runs the model
        twice, the second time with ``namelist.landice.rst`` and
        ``streams.landice.rst``
    """
    def __init__(self, test_case, name='run_model', subdir=None, ntasks=1,
                 min_tasks=None, openmp_threads=1, mem='1GB', suffixes=None):
        """
        Create a new test case

        Parameters
        ----------
        test_case : compass.TestCase
            The test case this step belongs to

        name : str, optional
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

        suffixes : list of str, optional
            a list of suffixes for namelist and streams files produced
            for this step.  Most steps most runs will just have a
            ``namelist.landice`` and a ``streams.landice`` (the default) but
            the ``restart_run`` step of the ``restart_test`` runs the model
            twice, the second time with ``namelist.landice.rst`` and
            ``streams.landice.rst``
        """
        if suffixes is None:
            suffixes = ['landice']
        self.suffixes = suffixes
        if min_tasks is None:
            min_tasks = ntasks
        super().__init__(test_case=test_case, name=name, subdir=subdir,
                         add_default_substep=False)

        for suffix in suffixes:
            namelist = f'namelist.{suffix}'
            streams = f'streams.{suffix}'
            self.add_namelist_file(
                'compass.landice.tests.circular_shelf', 'namelist.landice',
                out_name=namelist)

            self.add_streams_file(
                'compass.landice.tests.circular_shelf', 'streams.landice',
                out_name=streams)

            add_model_substeps(step=self, substep_prefix=suffix, ntasks=ntasks,
                               min_tasks=min_tasks,
                               openmp_threads=openmp_threads, mem=mem,
                               namelist=namelist, streams=streams)

        self.add_input_file(filename='landice_grid.nc',
                            target='../setup_mesh/landice_grid.nc')
        self.add_input_file(filename='graph.info',
                            target='../setup_mesh/graph.info')
        self.add_input_file(filename='albany_input.yaml',
                            package='compass.landice.tests.circular_shelf',
                            copy=True)

        self.add_output_file(filename='output.nc')

    # no setup() or run() is needed
