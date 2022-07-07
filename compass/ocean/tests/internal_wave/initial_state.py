from compass.model import ModelStep


class InitialState(ModelStep):
    """
    A step for creating an initial condition for internal wave test cases
    """
    def __init__(self, test_case):
        """
        Create the step

        Parameters
        ----------
        test_case : compass.testcase.Testcase
            The test case this step belongs to
        """
        super().__init__(test_case=test_case, name='initial_state', ntasks=1,
                         min_tasks=1, openmp_threads=1)

        self.add_namelist_file('compass.ocean.tests.internal_wave',
                               'namelist.init', mode='init')

        self.add_streams_file('compass.ocean.tests.internal_wave',
                              'streams.init', mode='init')

        self.add_input_file(filename='culled_mesh.nc',
                            target=f'../mesh/culled_mesh.nc')

        self.add_input_file(filename='graph.info',
                            target=f'../mesh/culled_graph.info')

        self.add_output_file('ocean.nc')
        self.add_output_file('init_mode_forcing_data.nc')
