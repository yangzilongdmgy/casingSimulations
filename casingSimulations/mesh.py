import numpy as np
import properties
import json
import os

import properties
from SimPEG import Utils

import discretize
from discretize import utils
from discretize.utils import mkvc

from .model import CasingParameters

# __all__ = [TensorMeshGenerator, CylMeshGenerator]


class BaseMeshGenerator(properties.HasProperties):
    """
    Base Mesh Generator Class
    """
    # # Z-direction of mesh
    # csz = properties.Float(
    #     "cell size in the z-direction", default=0.05
    # )
    # nca = properties.Integer(
    #     "number of fine cells above the air-earth interface", default=10
    # )

    # # padding factors


    # # number of padding cells
    # npadz = properties.Integer(
    #     "number of padding cells in z", default=38
    # )
    # npadx = properties.Integer(
    #     "number of padding cells required to get to infinity!", default=23
    # )

    # casing parameters
    cp = properties.Instance(
        "casing parameters instance",
        CasingParameters,
        required=True
    )

    def __init__(self, **kwargs):
        Utils.setKwargs(self, **kwargs)

    @property
    def mesh(self):
        if getattr(self, '_mesh', None) is None:
            self._mesh = self._discretizePair(
                [self.hx, self.hy, self.hz],
                x0=self.x0
            )
        return self._mesh

    def save(self, filename='MeshParameters.json', directory='.'):
        """
        Save the casing mesh parameters to json
        :param str file: filename for saving the casing mesh parameters
        """
        if not os.path.isdir(directory):  # check if the directory exists
            os.mkdir(directory)  # if not, create it
        f = '/'.join([directory, filename])
        with open(f, 'w') as outfile:
            cp = json.dump(self.serialize(), outfile)


class TensorMeshGenerator(BaseMeshGenerator):
    """
    Tensor mesh designed based on the source and formulation
    """
    # cell sizes in each of the dimensions
    csx = properties.Float(
        "cell size in the x-direction", default=25.
    )
    csy = properties.Float(
        "cell size in the y-direction", default=25.
    )
    csz = properties.Float(
        "cell size in the z-direction", default=25.
    )

    # padding factors in each direction
    pfx = properties.Float(
        "padding factor to pad to infinity", default=1.5
    )
    pfy = properties.Float(
        "padding factor to pad to infinity", default=1.5
    )
    pfz = properties.Float(
        "padding factor to pad to infinity", default=1.5
    )

    # number of extra cells horizontally, above the air-earth interface and
    # below the casing
    nch = properties.Integer(
        "number of cells to add on each side of the mesh horizontally",
        default=10.
    )
    nca = properties.Integer(
        "number of extra cells above the air-earth interface",
        default=5.
    )
    ncb = properties.Integer(
        "number of cells below the casing",
        default=5.
    )

    # number of padding cells in each direction
    npadx = properties.Integer(
        "number of x-padding cells", default=10
    )
    npady = properties.Integer(
        "number of y-padding cells", default=10
    )
    npadz = properties.Integer(
        "number of z-padding cells", default=10
    )

    # domain extent in the y-direction
    domain_y = properties.Float(
        "domain extent in the y-direction", default=1000.
    )

    _discretizePair = discretize.TensorMesh

    # Instantiate the class with casing parameters
    def __init__(self, **kwargs):
        super(TensorMeshGenerator, self).__init__(**kwargs)

    @property
    def x0(self):
        if getattr(self, '_x0', None) is None:
            self._x0 = np.r_[
                -self.hx[:self.npadx+self.ncx-self.nch].sum(),
                -self.hy[:self.npady+self.ncy-self.nch].sum(),
                -self.hz[:self.npadz+self.ncz-self.nca].sum()
            ]
        return self._x0

    @x0.setter
    def x0(self, value):
        assert len(value) == 3, (
            'length of x0 must be 3, not {}'.format(len(x0))
        )

        self._x0 = value

    # Domain extents in the x, z directions
    @property
    def domain_x(self):
        if getattr(self, '_domain_x', None) is None:
            self._domain_x = (self.cp.src_a[0] - self.cp.src_b[0])
        return self._domain_x

    @domain_x.setter
    def domain_x(self, value):
        self._domain_x = value

    @property
    def domain_z(self):
        if getattr(self, '_domain_z', None) is None:
            self._domain_z = (self.cp.src_a[0] - self.cp.src_b[0])
        return self._domain_z

    @domain_z.setter
    def domain_z(self, value):
        self._domain_z = value

    # number of cells in each direction
    @property
    def ncx(self):
        if getattr(self, '_ncx', None) is None:
            self._ncx = int(
                np.ceil(self.domain_x / self.csx) +
                2*self.nch
            )
        return self._ncx

    @property
    def ncy(self):
        if getattr(self, '_ncy', None) is None:
            self._ncy = int(
                np.ceil(self.domain_y / self.csy) + 2*self.nch
            )
        return self._ncy

    @property
    def ncz(self):
        if getattr(self, '_ncz', None) is None:
            self._ncz = int(
                np.ceil(self.domain_z / self.csz) + self.nca + self.ncb
            )
        return self._ncz

    # cell spacings in each direction
    @property
    def hx(self):
        if getattr(self, '_hx', None) is None:
            self._hx = utils.meshTensor([
                (self.csx, self.npadx, -self.pfx),
                (self.csx, self.ncx),
                (self.csx, self.npadx, self.pfx)
            ])
        return self._hx

    @property
    def hy(self):
        if getattr(self, '_hy', None) is None:
            self._hy = utils.meshTensor([
                (self.csy, self.npady, -self.pfy),
                (self.csy, self.ncy),
                (self.csy, self.npady, self.pfy)
            ])
        return self._hy

    @property
    def hz(self):
        if getattr(self, '_hz', None) is None:
            self._hz = utils.meshTensor([
                (self.csz, self.npadz, -self.pfz),
                (self.csz, self.ncz),
                (self.csz, self.npadz, self.pfz)
            ])
        return self._hz


class CylMeshGenerator(BaseMeshGenerator):
    """
    Mesh that makes sense for casing examples

    :param CasingSimulations.CasingParameters cp: casing parameters object
    """

    # X-direction of the mesh
    csx1 = properties.Float(
        "finest cells in the x-direction", default=2.5e-3
    )
    csx2 = properties.Float(
        "second uniform cell region in x-direction", default=25.
    )
    pfx1 = properties.Float(
        "padding factor to pad from csx1 to csx2", default=1.3
    )
    pfx2 = properties.Float(
        "padding factor to pad to infinity", default=1.5
    )
    domain_x2 = properties.Float(
        "domain extent for uniform cell region", default=1000.
    )

    # Theta direction of the mesh
    ncy = properties.Integer(
        "number of cells in the theta direction of the mesh. "
        "1 --> cyl symmetric", default=1
    )

    # z-direction of the mesh
    csz = properties.Float(
        "cell size in the z-direction", default=0.05
    )
    nca = properties.Integer(
        "number of fine cells above the air-earth interface", default=5
    )
    ncb = properties.Integer(
        "number of fine cells below the casing", default=5
    )
    pfz = properties.Float(
        "padding factor in the z-direction", default=1.5
    )

    # number of padding cells
    npadx = properties.Integer(
        "number of padding cells required to get to infinity!", default=23
    )
    npadz = properties.Integer(
        "number of padding cells in z", default=38
    )

    _discretizePair = discretize.CylMesh

    # Instantiate the class with casing parameters
    def __init__(self, **kwargs):
        super(CylMeshGenerator, self).__init__(**kwargs)

    @property
    def ncx1(self):
        """number of cells with size csx1"""
        return np.ceil(self.cp.casing_b/self.csx1+2)

    @property
    def npadx1(self):
        """number of padding cells to get from csx1 to csx2"""
        return np.floor(np.log(self.csx2/self.csx1) / np.log(self.pfx1))

    @property
    def hx(self):
        """
        cell spacings in the x-direction
        """
        if getattr(self, '_hx', None) is None:

            # finest uniform region
            hx1a = Utils.meshTensor([(self.csx1, self.ncx1)])

            # pad to second uniform region
            hx1b = Utils.meshTensor([(self.csx1, self.npadx1, self.pfx1)])

            # scale padding so it matches cell size properly
            dx1 = sum(hx1a)+sum(hx1b)
            dx1 = np.floor(dx1/self.csx2)
            hx1b *= (dx1*self.csx2 - sum(hx1a))/sum(hx1b)

            # second uniform chunk of mesh
            ncx2 = np.ceil((self.domain_x2 - dx1)/self.csx2)
            hx2a = Utils.meshTensor([(self.csx2, ncx2)])

            # pad to infinity
            hx2b = Utils.meshTensor([(self.csx2, self.npadx, self.pfx2)])

            self._hx = np.hstack([hx1a, hx1b, hx2a, hx2b])

        return self._hx

    @property
    def hy(self):
        """
        cell spacings in the y-direction
        """
        if getattr(self, '_hy', None) is None:
            if self.ncy == 1:
                self._hy = 1
            else:
                self._hy = 2*np.pi * np.ones(self.ncy) / self.ncy
        return self._hy

    @hy.setter
    def hy(self, val):
        H = val.sum()
        if H != 2*np.pi:
            val = val*2*np.pi/val.sum()
        self._hy = val

    @property
    def ncz(self):
        """
        number of core z-cells
        """
        if getattr(self, '_ncz', None) is None:
            # number of core z-cells (add 10 below the end of the casing)
            self._ncz = (
                np.int(np.ceil(-self.cp.casing_z[0]/self.csz)) +
                self.nca + self.ncb
            )
        return self._ncz

    @property
    def hz(self):
        if getattr(self, '_hz', None) is None:

            self._hz = Utils.meshTensor([
                (self.csz, self.npadz, -self.pfz),
                (self.csz, self.ncz),
                (self.csz, self.npadz, self.pfz)
            ])
        return self._hz

    @property
    def x0(self):
        if getattr(self, '_x0', None) is None:
            self._x0 = np.r_[
                0., 0., -np.sum(self.hz[:self.npadz+self.ncz-self.nca])
            ]
        return self._x0

    @x0.setter
    def x0(self, value):
        assert len(value) == 3, 'x0 must be length 3, not {}'.format(len(x0))

    # Plot the physical Property Models
    def plotModels(self, sigma, mu, xlim=[0., 1.], zlim=[-1200., 100.], ax=None):
        if ax is None:
            fig, ax = plt.subplots(1, 2, figsize=(10, 4))

        plt.colorbar(self.mesh.plotImage(np.log10(sigma), ax=ax[0])[0], ax=ax[0])
        plt.colorbar(self.mesh.plotImage(mu/mu_0, ax=ax[1])[0], ax=ax[1])

        ax[0].set_xlim(xlim)
        ax[1].set_xlim(xlim)

        ax[0].set_ylim(zlim)
        ax[1].set_ylim(zlim)

        ax[0].set_title('$\log_{10}\sigma$')
        ax[1].set_title('$\mu_r$')

        plt.tight_layout()

        return ax
