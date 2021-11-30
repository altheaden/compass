import numpy
import xarray

from mpas_tools.cime.constants import constants
from mpas_tools.io import write_netcdf

from compass.model import ModelSetupSubstep, ModelSubstep
from compass.step import Step
from compass.substep import Substep


class SshAdjustment(Step):
    """
    A step for iteratively adjusting the pressure from the weight of the ice
    shelf to match the sea-surface height

    ntasks : int
        the target number of tasks the model substep would ideally use.  If too
        few cores are available on the system to accommodate the number of
        tasks and the number of cores per task, the substep will run on
        fewer tasks as long as as this is not below ``min_tasks``

    min_tasks : int
        the number of tasks the model substep requires.  If the system has too
        few cores to accommodate the number of tasks and cores per task,
        the step will fail

    openmp_threads : int
        the number of OpenMP threads the model will use

    mem : str
        the amount of memory that the model substep is allowed to use

    """
    def __init__(self, test_case, init_filename, graph_filename):
        """
        Create the step

        Parameters
        ----------
        test_case : compass.TestCase
            The test case this step belongs to

        init_filename : str
            The path (typically relative) to the initial condition for the
            iteration process

        graph_filename : str
            The path (typically relative) to the graph file to use to partition
            the mesh across processors
        """
        super().__init__(test_case=test_case, name='ssh_adjustment',
                         add_default_substep=False)

        self.ntasks = 1
        self.min_tasks = 1
        self.openmp_threads = 1
        self.mem = '1GB'

        self.add_model_as_input()

        self.add_output_file(filename='adjusted_init.nc')

        self.add_input_file(filename='adjusting_init0.nc',
                            target=init_filename)

        self.add_input_file(filename='graph.info',
                            target=graph_filename)

        self.add_model_as_input()

        self.add_output_file(filename='adjusted_init.nc')

        options = dict(
            config_check_ssh_consistency='.false.',
            config_land_ice_flux_mode="'pressure_only'")

        self.add_namelist_options(options=options)

        replacements = dict(
            in_filename=f'adjusting_init0.nc',
            out_filename='output_ssh0.nc',
            run_duration='0000_01:00:00')

        self.add_streams_file(package='compass.ocean.iceshelf',
                              streams='streams.ssh_adjust',
                              template_replacements=replacements)

    def set_resources(self, ntasks=None, min_tasks=None, openmp_threads=None,
                      mem=None):
        """
        Update the resources for the model subtask.  This can be done within
        init, ``setup()`` or ``runtime_setup()`` for the step, or init,
        ``configure()`` or ``run()`` for the test case that this step belongs
        to.

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
        if ntasks is not None:
            self.ntasks = ntasks
        if min_tasks is not None:
            self.min_tasks = min_tasks
        if openmp_threads is not None:
            self.openmp_threads = openmp_threads
        if mem is not None:
            self.mem = mem

    def runtime_setup(self):
        """
        Get the iteration count and set up the substeps accordingly
        """

        config = self.config
        ntasks = self.ntasks
        min_tasks = self.min_tasks
        openmp_threads = self.openmp_threads
        mem = self.mem

        iter_count = config.getint('ssh_adjustment', 'iterations')

        for iter_index in range(iter_count):
            in_filename = f'adjusting_init{iter_index}.nc'
            ssh_filename = f'output_ssh{iter_index}.nc'
            if iter_index < iter_count-1:
                next_filename = f'adjusting_init{iter_index + 1}.nc'
            else:
                next_filename = 'adjusted_init.nc'
            substep_prefix = f'model_{iter_index:02d}'
            model_substep = ModelSubstep(self, substep_prefix,
                                         ntasks, min_tasks, openmp_threads,
                                         mem, namelist='namelist.ocean',
                                         streams='streams.ocean')

            model_setup_substep = PreModelSubstep(
                self, substep_prefix, model_substep, in_filename, ssh_filename)

            self.add_substep(model_setup_substep)

            # won't get called automatically since setup already happened
            model_substep.setup()
            self.add_substep(model_substep)

            self.add_substep(PostModelSubstep(
                self, iter_index, iter_count, in_filename, ssh_filename,
                next_filename))


class PreModelSubstep(ModelSetupSubstep):
    def __init__(self, step, prefix, model_substep, in_filename,
                 ssh_filename):
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

        in_filename : str
            The initial condition for this iteration

        ssh_filename : str
            The file name for SSH output
        """
        super().__init__(step=step, prefix=prefix, model_substep=model_substep,
                         update_pio=True, partition_graph=True,
                         graph_file='graph.info')
        self.in_filename = in_filename
        self.ssh_filename = ssh_filename

    def run(self):
        """ Run the substep """
        super().run()
        step = self.step
        config = step.config
        namelist = self.model_substep.namelist
        streams = self.model_substep.streams
        run_duration = config.get('ssh_adjustment', 'run_duration')

        options = dict(
            config_run_duration=f"'{run_duration}'",
            config_check_ssh_consistency='.false.',
            config_land_ice_flux_mode="'pressure_only'")

        step.update_namelist_at_runtime(options=options, out_name=namelist)

        replacements = dict(
            in_filename=self.in_filename,
            out_filename=self.ssh_filename,
            run_duration=run_duration)

        step.update_streams_at_runtime(package='compass.ocean.iceshelf',
                                       streams='streams.ssh_adjust',
                                       template_replacements=replacements,
                                       out_name=streams)


class PostModelSubstep(Substep):
    def __init__(self, step, iter_index, iter_count, in_filename,
                 ssh_filename, next_filename):
        """
        Make a substep for setting up the model right before running

        Parameters
        ----------
        step : compass.Step
            A step that this substep belongs to

        iter_index : int
            The index of this substep in the iterative adjustment of SSH or
            landIcePressure

        iter_count : int
            The total number of iterations

        in_filename : str
            The initial condition for this iteration

        ssh_filename : str
            The file name for SSH output

        next_filename : str
            The initial condition for the next iteration or the final result
            of the iteration
        """
        super().__init__(step=step, name=f'adjust_ssh_{iter_index:02d}')
        self.iter_index = iter_index
        self.iter_count = iter_count
        self.in_filename = in_filename
        self.ssh_filename = ssh_filename
        self.next_filename = next_filename

    def run(self):
        """ Run the substep """
        config = self.step.config
        logger = self.step.logger
        iter_index = self.iter_index
        iter_count = self.iter_count

        variable = config.get('ssh_adjustment', 'variable')
        if variable not in ['ssh', 'landIcePressure']:
            raise ValueError(f'Unknown variable to modify: {variable}')

        logger.info(f' * Iteration {iter_index + 1}/{iter_count}')

        logger.info(f"   * Updating {variable}")

        with xarray.open_dataset(self.in_filename) as ds:

            # keep the data set with Time for output
            ds_out = ds

            ds = ds.isel(Time=0)

            on_a_sphere = ds.attrs['on_a_sphere'].lower() == 'yes'

            initSSH = ds.ssh
            if 'minLevelCell' in ds:
                minLevelCell = ds.minLevelCell-1
            else:
                minLevelCell = xarray.zeros_like(ds.maxLevelCell)

            with xarray.open_dataset(self.ssh_filename) as ds_ssh:
                # get the last time entry
                ds_ssh = ds_ssh.isel(Time=ds_ssh.sizes['Time'] - 1)
                finalSSH = ds_ssh.ssh
                topDensity = ds_ssh.density.isel(nVertLevels=minLevelCell)

            mask = numpy.logical_and(ds.maxLevelCell > 0,
                                     ds.modifyLandIcePressureMask == 1)

            deltaSSH = mask * (finalSSH - initSSH)

            # then, modify the SSH or land-ice pressure
            if variable == 'ssh':
                ssh = finalSSH.expand_dims(dim='Time', axis=0)
                ds_out['ssh'] = ssh
                # also update the landIceDraft variable, which will be used to
                # compensate for the SSH due to land-ice pressure when
                # computing sea-surface tilt
                ds_out['landIceDraft'] = ssh
                # we also need to stretch layerThickness to be compatible with
                # the new SSH
                stretch = ((finalSSH + ds.bottomDepth) /
                           (initSSH + ds.bottomDepth))
                ds_out['layerThickness'] = ds_out.layerThickness * stretch
                landIcePressure = ds.landIcePressure.values
            else:
                # Moving the SSH up or down by deltaSSH would change the
                # land-ice pressure by density(SSH)*g*deltaSSH. If deltaSSH is
                # positive (moving up), it means the land-ice pressure is too
                # small and if deltaSSH is negative (moving down), it means
                # land-ice pressure is too large, the sign of the second term
                # makes sense.
                gravity = constants['SHR_CONST_G']
                deltaLandIcePressure = topDensity * gravity * deltaSSH

                landIcePressure = numpy.maximum(
                    0.0, ds.landIcePressure + deltaLandIcePressure)

                ds_out['landIcePressure'] = \
                    landIcePressure.expand_dims(dim='Time', axis=0)

                finalSSH = initSSH

            write_netcdf(ds_out, self.next_filename)

            # Write the largest change in SSH and its lon/lat to a file
            with open(f'maxDeltaSSH_{iter_index:02d}.log', 'w') as \
                    log_file:

                mask = landIcePressure > 0.
                iCell = numpy.abs(deltaSSH.where(mask)).argmax().values

                ds_cell = ds.isel(nCells=iCell)

                if on_a_sphere:
                    lon = numpy.rad2deg(ds_cell.lonCell.values)
                    lat = numpy.rad2deg(ds_cell.latCell.values)
                    coords = f'lon/lat: {lon:f} {lat:f}'
                else:
                    x = 1e-3 * ds_cell.xCell.values
                    y = 1e-3 * ds_cell.yCell.values
                    coords = f'x/y: {x:f} {y:f}'
                max_delta_ssh = deltaSSH.isel(nCells=iCell).values
                string = f'max change in SSH: {max_delta_ssh:g}, {coords}'
                logger.info(f'     {string}')
                log_file.write(f'{string}\n')
                ssh_at_max = finalSSH.isel(nCells=iCell).values
                pres_at_max = landIcePressure.isel(nCells=iCell).values
                string = f'ssh: {ssh_at_max:g}, ' \
                         f'landIcePressure: {pres_at_max:g}'
                logger.info(f'     {string}')
                log_file.write(f'{string}\n')

        logger.info("   - Complete\n")
