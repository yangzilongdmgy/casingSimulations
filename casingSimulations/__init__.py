from . import model
from .mesh import (
    CylMeshGenerator, CasingMeshGenerator, TensorMeshGenerator
)
from .physics import (
    CasingCurrents, plotCurrentDensity, plot_currents_over_freq,
    plot_currents_over_mu, plot_j_over_mu_z, plot_j_over_freq_z,
    plot_j_over_mu_x
)
from .view import plotEdge2D, plotFace2D
from . import sources
from . import run
from .utils import (
    load_properties, edge3DthetaSlice, face3DthetaSlice, ccv3DthetaSlice
)

from .info import (
    __version__, __author__, __license__, __copyright__
)
