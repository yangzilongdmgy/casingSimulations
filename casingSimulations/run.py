import time
import numpy as np
import scipy.sparse as sp
import os
import json
from scipy.constants import mu_0

import discretize
from discretize import utils
import properties
from SimPEG.EM import FDEM, TDEM
from SimPEG import Utils, Maps
from SimPEG.EM.Static import DC

try:
    from pymatsolver import Pardiso as Solver
except ImportError:
    import warnings
    warnings.warn(
        "Could not import Pardiso, falling back to LU. Will be slow."
    )
    from SimPEG import SolverLU as Solver

from .base import LoadableInstance, BaseCasing
from . import model
from .model import PhysicalProperties
from .mesh import BaseMeshGenerator, CylMeshGenerator, TensorMeshGenerator
from .sources import BaseCasingSrc
from .utils import writeSimulationPy
from . import sources
from .info import __version__


class BaseSimulation(BaseCasing):
    """
    Base class wrapper to run an EM Forward Simulation
    """

    fields_filename = properties.String(
        "filename for the fields",
        default="fields.npy"
    )

    filename = properties.String(
        "filename for the simulation parameters",
        default="simulationParameters.json"
    )

    num_threads = properties.Integer(
        "number of threads",
        default=1
    )

    modelParameters = LoadableInstance(
        "Model Parameters instance",
        model.Wholespace,
        required=True
    )

    meshGenerator = LoadableInstance(
        "mesh generator instance",
        BaseMeshGenerator,
        required=True
    )

    src = LoadableInstance(
        "Source Parameters instance",
        BaseCasingSrc,
        required=False
    )

    verbose = properties.Bool(
        "run the simulation in Verbose mode?",
        default = False
    )

    def __init__(self, **kwargs):
        # set keyword arguments
        Utils.setKwargs(self, **kwargs)

        # if the working directory does not exsist, create it
        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

        # hook up the properties classes
        self.meshGenerator.modelParameters = self.modelParameters

        if getattr(self, 'src', None) is not None:
            self.src.modelParameters = self.modelParameters
            self.src.meshGenerator = self.meshGenerator

    @property
    def physprops(self):
        if getattr(self, '_physprops', None) is None:
            self._physprops = PhysicalProperties(
                self.meshGenerator, self.modelParameters
            )
        return self._physprops

    @property
    def prob(self):
        return self._prob

    @property
    def survey(self):
        return self._survey

    def write_py(self, physics=None, includeDC=True, include2D=True):
        """
        Write a python script for running the simulation
        :param str physics: 'TDEM', 'FDEM'
        :param bool includeDC: include a DC simulation with the EM one (default is True)
        :param bool include2D: include a 2D simulation? (default is True)
        """

        # save the properties
        self.modelParameters.save()
        self.meshGenerator.save()
        self.src.save()

        # if physics is None:
        #     physics = self.src.physics

        # write the simulation.py
        writeSimulationPy(
            modelParameters=self.modelParameters.filename,
            meshGenerator=self.meshGenerator.filename,
            src=self.src.filename,
            directory=self.directory,
            physics=self.physics
        )

    def fields(self):
        """
        fields from the forward simulation
        """
        if getattr(self, '_fields', None) is None:
            self._fields = self.run()
        return self._fields

    def run(self):
        """
        Run the forward simulation
        """

        # ----------------- Validate Parameters ----------------- #

        print('Validating parameters...')
        self.validate()

        # grab the discretize mesh off of the mesh object
        sim_mesh = self.meshGenerator.mesh
        print('      max x: {}, min z: {}, max z: {}, nC: {}'.format(
            sim_mesh.vectorNx.max(),
            sim_mesh.vectorNz.min(),
            sim_mesh.vectorNz.max(),
            sim_mesh.nC
        ))

        # save simulation parameters
        self.save()

        # ----------------- Set up the simulation ----------------- #
        physprops = self.physprops
        prb = self.prob
        # survey = self.survey
        # prb.pair(survey)

        # ----------------- Run the the simulation ----------------- #
        print('Starting {}'.format(type(self).__name__))
        t = time.time()
        print('Using {} Solver'.format(prb.Solver))
        fields = prb.fields(physprops.model)
        np.save(
            '/'.join([self.directory, self.fields_filename]),
            fields[:, '{}Solution'.format(self.formulation)]
        )
        print('   ... Done. Elapsed time : {}'.format(time.time()-t))

        self._fields = fields
        return fields


class SimulationFDEM(BaseSimulation):
    """
    A wrapper to run an FDEM Forward Simulation
    :param CasingSimulations.model.WholeSpace modelParameters: casing parameters object
    :param CasingSimulations.mesh.BaseMeshGenerator mesh: a CasingSimulation mesh generator object
    """

    formulation = properties.StringChoice(
        "Formulation of the problem to solve [e, b, h, j]",
        default="h",
        choices=["e", "b", "h", "j"]
    )

    physics = "FDEM"

    def __init__(self, **kwargs):
        super(SimulationFDEM, self).__init__(**kwargs)

        self._prob = getattr(
                FDEM, 'Problem3D_{}'.format(self.formulation)
                )(
                self.meshGenerator.mesh,
                sigmaMap=self.physprops.wires.sigma,
                muMap=self.physprops.wires.mu,
                Solver=Solver,
                verbose=self.verbose
            )

        if getattr(self.src, "physics", None) is None:
            self.src.physics = "FDEM"

        self._survey = FDEM.Survey(self.src.srcList)

        self._prob.pair(self._survey)


class SimulationTDEM(BaseSimulation):
    """
    A wrapper to run a TDEM Forward Simulation
    :param CasingSimulations.model.WholeSpace modelParameters: casing parameters object
    :param CasingSimulations.mesh.BaseMeshGenerator mesh: a CasingSimulation mesh generator object
    """

    formulation = properties.StringChoice(
        "Formulation of the problem to solve [e, b, h, j]",
        default="j",
        choices=["e", "b", "h", "j"]
    )

    physics = "TDEM"

    def __init__(self, **kwargs):
        super(SimulationTDEM, self).__init__(**kwargs)

        self._prob = getattr(
                TDEM, 'Problem3D_{}'.format(self.formulation)
                )(
                self.meshGenerator.mesh,
                timeSteps=self.modelParameters.timeSteps,
                sigmaMap=self.physprops.wires.sigma,
                mu=self.physprops.mu, # right now the TDEM code doesn't support mu inversions
                Solver=Solver,
                verbose=self.verbose
            )

        if getattr(self.src, "physics", None) is None:
            self.src.physics = "TDEM"

        self._survey = TDEM.Survey(self.src.srcList)

        self._prob.pair(self._survey)


class SimulationDC(BaseSimulation):
    """
    A wrapper to run a DC Forward Simulation
    :param CasingSimulations.model.WholeSpace modelParameters: casing parameters object
    :param CasingSimulations.mesh.BaseMeshGenerator mesh: a CasingSimulation mesh generator object
    """
    src_a = properties.Vector3(
        "a electrode location", required=True
    )

    src_b = properties.Vector3(
        "return electrode location", required=True
    )

    fields_filename = properties.String(
        "filename for the fields",
        default="fieldsDC.npy"
    )

    formulation = properties.String(
        "field that we are solving for",
        default="phi"
    )

    physics = "DC"

    def __init__(self, **kwargs):
        super(SimulationDC, self).__init__(**kwargs)

        self._prob = DC.Problem3D_CC(
            self.meshGenerator.mesh,
            sigmaMap=self.physprops.wires.sigma,
            bc_type='Dirichlet',
            Solver=Solver
        )
        self._src = DC.Src.Dipole([], self.src_a, self.src_b)
        self._survey = DC.Survey([self._src])

        self._prob.pair(self._survey)
