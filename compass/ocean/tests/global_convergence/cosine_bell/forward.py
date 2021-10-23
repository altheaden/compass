import time

from compass.model import add_model_substeps
from compass.step import Step


class Forward(Step):
    """
    A step for performing forward MPAS-Ocean runs as part of the cosine bell
    test case

    Attributes
    ----------
    resolution : int
        The resolution of the (uniform) mesh in km
    """

    def __init__(self, test_case, resolution):
        """
        Create a new step

        Parameters
        ----------
        test_case : compass.ocean.tests.global_convergence.cosine_bell.CosineBell
            The test case this step belongs to

        resolution : int
            The resolution of the (uniform) mesh in km
        """
        super().__init__(test_case=test_case,
                         name=f'QU{resolution}_forward',
                         subdir=f'QU{resolution}/forward')

        self.resolution = resolution

        # make sure output is double precision
        self.add_streams_file('compass.ocean.streams', 'streams.output')

        self.add_namelist_file(
            'compass.ocean.tests.global_convergence.cosine_bell',
            'namelist.forward')
        self.add_streams_file(
            'compass.ocean.tests.global_convergence.cosine_bell',
            'streams.forward')

        self.add_input_file(filename='init.nc',
                            target='../init/initial_state.nc')
        self.add_input_file(filename='graph.info',
                            target='../mesh/graph.info')

        self.add_output_file(filename='output.nc')

        add_model_substeps(step=self)

    def setup(self):
        """
        Set namelist options base on config options
        """
        dt = self.get_dt()
        self.add_namelist_options({'config_dt': dt})

    def runtime_setup(self):
        """
        Set model resources based on config options
        """
        resolution = self.resolution
        config = self.config
        ntasks = config.getint('cosine_bell',
                               f'QU{resolution}_cores')
        min_tasks = config.getint('cosine_bell',
                                  f'QU{resolution}_min_cores')
        substep = self.substeps['model']
        substep.set_model_resources(ntasks=ntasks, min_tasks=min_tasks)

    def run(self):
        """
        Run this step of the testcase
        """

        # update dt in case the user has changed dt_per_km
        dt = self.get_dt()
        self.update_namelist_at_runtime(options={'config_dt': dt},
                                        out_name='namelist.ocean')

    def get_dt(self):
        """
        Get the time step

        Returns
        -------
        dt : str
            the time step in HH:MM:SS
        """
        config = self.config
        # dt is proportional to resolution: default 30 seconds per km
        dt_per_km = config.getint('cosine_bell', 'dt_per_km')

        dt = dt_per_km * self.resolution
        # https://stackoverflow.com/a/1384565/7728169
        dt = time.strftime('%H:%M:%S', time.gmtime(dt))

        return dt
