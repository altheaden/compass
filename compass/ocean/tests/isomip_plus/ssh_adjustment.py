from compass.ocean.iceshelf.ssh_adjustment import SshAdjustment
from compass.ocean.tests.isomip_plus.forward import get_time_steps


class IsomipPlusAdjustment(SshAdjustment):
    """
    A step for iteratively adjusting the pressure from the weight of the ice
    shelf to match the sea-surface height as part of ice-shelf 2D test cases
    """
    def __init__(self, test_case, resolution):
        """
        Create the step

        Parameters
        ----------
        test_case : compass.TestCase
            The test case this step belongs to

        resolution : float
            The horizontal resolution (km) of the test case
        """
        super().__init__(test_case=test_case,
                         init_filename='../initial_state/initial_state.nc',
                         graph_filename='../initial_state/culled_graph.info')

        # generate the namelist, replacing a few default options
        # start with the same namelist settings as the forward run
        self.add_namelist_file('compass.ocean.tests.isomip_plus',
                               'namelist.forward_and_ssh_adjust')

        # we don't want the global stats AM for this run
        options = get_time_steps(resolution)
        options['config_AM_globalStats_enable'] = '.false.'
        self.add_namelist_options(options)

    def runtime_setup(self):
        """
        Set model resources based on config options
        """
        config = self.config
        cores = config.getint('isomip_plus', 'forward_cores')
        min_cores = config.getint('isomip_plus', 'forward_min_cores')
        threads = config.getint('isomip_plus', 'forward_threads')
        self.set_resources(ntasks=cores, min_tasks=min_cores,
                           openmp_threads=threads)

        super().runtime_setup()
