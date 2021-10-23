class Substep:
    """
    The base class for a substep of a step.  A substep is a part of a step
    with fixed resource requirements such as the number of cores per task,
    number of tasks, or amount of memory.  Making a mesh and running the MPAS
    model are examples of a substep.  When running on Slurm, any process that
    is called with ``srun`` must be a separate substep.

    Attributes
    ----------
    name : str
        the name of the test case

    step : compass.Step
        The step this substep belongs to

    cpus_per_task : int
        the number of cores per task the substep would ideally use.  If fewer
        cores per node are available on the system, the substep will run on all
        available cores as long as this is not below ``min_cpus_per_task``

    min_cpus_per_task : int
        the number of cores per task the substep requires.  If the system has
        fewer than this number of cores per node, the step will fail

    ntasks : int
        the number of tasks the substep would ideally use.  If too few cores
        are available on the system to accommodate the number of tasks and the
        number of cores per task, the substep will run on fewer tasks as long
        as as this is not below ``min_tasks``

    min_tasks : int
        the number of tasks the substep requires.  If the system has too few
        cores to accommodate the number of tasks and cores per task, the step
        will fail

    openmp_threads : int
        the number of OpenMP threads to use

    mem : str
        the amount of memory that the substep is allowed to use

    args : list of str or None
        A list of command-line arguments to call in parallel
   """

    def __init__(self, step, name, cpus_per_task=1, min_cpus_per_task=1,
                 ntasks=1, min_tasks=1, openmp_threads=1, mem='1G'):
        """
        Create a new test case

        Parameters
        ----------
        step : compass.Step
            The step this substep belongs to

        name : str
            the name of the test case

        cpus_per_task : int, optional
            the number of cores per task the substep would ideally use.  If
            fewer cores per node are available on the system, the substep will
            run on all available cores as long as this is not below
            ``min_cpus_per_task``

        min_cpus_per_task : int, optional
            the number of cores per task the substep requires.  If the system
            has fewer than this number of cores per node, the step will fail

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
        self.name = name
        self.step = step
        self.cpus_per_task = cpus_per_task
        self.min_cpus_per_task = min_cpus_per_task
        self.ntasks = ntasks
        self.min_tasks = min_tasks
        self.openmp_threads = openmp_threads
        self.mem = mem
        self.args = None

    def set_resources(self, cpus_per_task=None, min_cpus_per_task=None,
                      ntasks=None, min_tasks=None, openmp_threads=None,
                      mem=None):
        """
        Update the resources for the subtask.  This can be done within init,
        ``setup()`` or ``runtime_setup()`` for the step that this substep
        belongs to, or init, ``configure()`` or ``run()`` for the test case
        that this substep belongs to.

        Parameters
        ----------
        cpus_per_task : int, optional
            the number of cores per task the substep would ideally use.  If
            fewer cores per node are available on the system, the substep will
            run on all available cores as long as this is not below
            ``min_cpus_per_task``

        min_cpus_per_task : int, optional
            the number of cores per task the substep requires.  If the system
            has fewer than this number of cores per node, the step will fail

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
        if cpus_per_task is not None:
            self.cpus_per_task = cpus_per_task
        if min_cpus_per_task is not None:
            self.min_cpus_per_task = min_cpus_per_task
        if ntasks is not None:
            self.ntasks = ntasks
        if min_tasks is not None:
            self.min_tasks = min_tasks
        if openmp_threads is not None:
            self.openmp_threads = openmp_threads
        if mem is not None:
            self.mem = mem

    def setup(self):
        """
        Set up the substep in the work directory.  Typically, setup will be
        handled entirely at the step, rather than the substep, level but this
        method can be overridden to perform any tasks during setup that are
        specific to the substep.
        """
        pass

    def run(self):
        """
        Run the substep.  Every child class must override this method to perform
        the main work.
        """
        pass


class DefaultSubstep(Substep):
    """
    The default substep, which calls the step's ``run()`` method
    """

    def __init__(self, step, **kwargs):
        """
        Create a new test case

        Parameters
        ----------
        step : compass.Step
            The step this substep belongs to

        kwargs : dict
            Keyword arguments that get passed on to the Substep base class
        """
        super().__init__(step=step, name='default', **kwargs)

    def run(self):
        """
        Run the substep.  Every child class must override this method to perform
        the main work.
        """
        self.step.run()
