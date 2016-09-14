# coding: utf-8
# Copyright (c) Pymatgen Development Team.
# Distributed under the terms of the MIT License.

from __future__ import division, unicode_literals

"""
This module defines classes for parsing the FEFF output files.

Currently supports the xmu.dat, ldos.dat output files are for non-spin case.
"""

from collections import defaultdict, OrderedDict

import numpy as np

from monty.io import zopen
from monty.json import MSONable

from pymatgen import Orbital, Spin
from pymatgen.electronic_structure.dos import Dos, CompleteDos
from pymatgen.io.feff import Header, Potential, Tags

__author__ = "Alan Dozier"
__credits__ = "Anubhav Jain, Shyue Ping Ong"
__copyright__ = "Copyright 2011, The Materials Project"
__version__ = "1.0.3"
__maintainer__ = "Alan Dozier"
__email__ = "adozier@uky.edu"
__status__ = "Beta"
__date__ = "April 7, 2013"


class LDos(MSONable):
    """
    Parser for ldos files ldos01, ldos02, .....

    Args:
        complete_dos (CompleteDos): complete dos object
        charge_transfer (dict): computed charge transfer between atoms dictionary
    """
    def __init__(self, complete_dos, charge_transfer):
        self.complete_dos = complete_dos
        self.charge_transfer = charge_transfer

    @staticmethod
    def from_file(filename1='feff.inp', filename2='ldos'):
        """"
        Creates LDos object from raw Feff ldos files by
        by assuming they are numbered consecutively, i.e. ldos01.dat
        ldos02.dat...

        Args:
            filename1: input file of run to obtain structure
            filename2: output ldos file of run to obtain dos info, etc.
        """
        ldos_filename = filename2
        header_str = Header.header_string_from_file(filename1)
        header = Header.from_string(header_str)
        structure = header.struct
        nsites = structure.num_sites
        pot_string = Potential.pot_string_from_file(filename1)
        dicts = Potential.pot_dict_from_string(pot_string)
        pot_dict = dicts[0]

        with zopen(ldos_filename + "00.dat", "r") as fobject:
            f = fobject.readlines()
        efermi = float(f[0].split()[4])

        dos_energies = []
        ldos = {}

        for i in range(1, len(pot_dict) + 1):
            if len(str(i)) == 1:
                ldos[i] = np.loadtxt("{}0{}.dat".format(ldos_filename, i))
            else:
                ldos[i] = np.loadtxt("{}{}.dat".format(ldos_filename, i))

        for i in range(0, len(ldos[1])):
            dos_energies.append(ldos[1][i][0])

        all_pdos = []
        vorb = {"s": Orbital.s, "p": Orbital.py, "d": Orbital.dxy,
                "f": Orbital.f0}
        forb = {"s": 0, "p": 1, "d": 2, "f": 3}

        dlength = len(ldos[1])

        for i in range(nsites):
            pot_index = pot_dict[structure.species[i].symbol]
            all_pdos.append(defaultdict(dict))
            for k, v in vorb.items():
                density = [ldos[pot_index][j][forb[k] + 1]
                           for j in range(dlength)]
                updos = density
                downdos = None
                if downdos:
                    all_pdos[-1][v] = {Spin.up: updos, Spin.down: downdos}
                else:
                    all_pdos[-1][v] = {Spin.up: updos}

        pdos = all_pdos
        vorb2 = {0: Orbital.s, 1: Orbital.py, 2: Orbital.dxy, 3: Orbital.f0}
        pdoss = {structure[i]: {v: pdos[i][v]
                                for v in vorb2.values()}
                 for i in range(len(pdos))}

        forb = {"s": 0, "p": 1, "d": 2, "f": 3}

        tdos = [0] * dlength
        for i in range(nsites):
            pot_index = pot_dict[structure.species[i].symbol]
            for v in forb.values():
                density = [ldos[pot_index][j][v + 1] for j in range(dlength)]
                for j in range(dlength):
                    tdos[j] = tdos[j] + density[j]
        tdos = {Spin.up: tdos}

        dos = Dos(efermi, dos_energies, tdos)
        complete_dos = CompleteDos(structure, dos, pdoss)
        charge_transfer = LDos.charge_transfer_from_file(filename1,
                                                         filename2)
        return LDos(complete_dos, charge_transfer)

    @staticmethod
    def charge_transfer_from_file(filename1, filename2):
        """
        Get charge transfer from file.

        Args:
            filename1: name of feff.inp file for run
            filename2: ldos filename for run, assume consequetive order, .i.e.,
                ldos01.dat, ldos02.dat....

        Returns:
            dictionary of dictionaries in order of potential sites
            ({"p": 0.154, "s": 0.078, "d": 0.0, "tot": 0.232}, ...)
        """
        cht = OrderedDict()
        pot_string = Potential.pot_string_from_file(filename1)
        dicts = Potential.pot_dict_from_string(pot_string)
        pot_dict = dicts[1]

        for i in range(0, len(dicts[0]) + 1):
            if len(str(i)) == 1:
                with zopen("{}0{}.dat".format(filename2, i), "rt") \
                        as fobject:
                    f = fobject.readlines()
                    s = float(f[3].split()[2])
                    p = float(f[4].split()[2])
                    d = float(f[5].split()[2])
                    f1 = float(f[6].split()[2])
                    tot = float(f[1].split()[4])
                    cht[str(i)] = {pot_dict[i]: {'s': s, 'p': p, 'd': d,
                                                 'f': f1,
                                   'tot': tot}}
            else:
                with zopen(filename2 + str(i) + ".dat", "rt") as fid:
                    f = fid.readlines()
                    s = float(f[3].split()[2])
                    p = float(f[4].split()[2])
                    d = float(f[5].split()[2])
                    f1 = float(f[6].split()[2])
                    tot = float(f[1].split()[4])
                    cht[str(i)] = {pot_dict[i]: {'s': s, 'p': p, 'd': d,
                                                 'f': f1,
                                   'tot': tot}}

        return cht

    def charge_transfer_to_string(self):
        """returns shrage transfer as string"""
        ch = self.charge_transfer
        chts = ['\nCharge Transfer\n\nabsorbing atom']
        for i in range(len(ch)):
            for atom, v2 in ch[str(i)].items():
                a = ['\n', atom, '\n', 's   ', str(v2['s']), '\n',
                     'p   ', str(v2['p']), '\n',
                     'd   ', str(v2['d']), '\n',
                     'f   ', str(v2['f']), '\n',
                     'tot ', str(v2['tot']), '\n']
                chts.extend(a)
        return ''.join(chts)


class Xmu(MSONable):
    """
    Parser for data in 'xmu.dat' file.
    The file 'xmu.dat' contains XANES, EXAFS or NRIXS data depending on the
    situation; \mu, \mu_0, and \chi = \chi * \mu_0/ \mu_0/(edge+50eV) as
    functions of absolute energy E, relative energy E − E_f and wave number k.

    Args:
        header: Header object
        parameters: Tags object
        absorbing_atom (str): absorbing atom symbol
        data (numpy.ndarray, Nx6): cross_sections

    Default attributes:
        xmu: Photon absorption cross section of absorbing atom in material
        Energies: Energies of data point
        relative_energies: E - E_fermi
        wavenumber: k=\sqrt(E −E_fermi)
        mu: The total absorption cross-section.
        mu0: The embedded atomic background absorption.
        chi: fine structure.
        Edge: Aborption Edge
        Absorbing atom: Species of absorbing atom
        Material: Formula of material
        Source: Source of structure
        Calculation: Type of Feff calculation performed
    """

    def __init__(self, header, parameters, absorbing_atom, data):
        self.header = header
        self.parameters = parameters
        self.absorbing_atom = absorbing_atom
        self.data = data

    @staticmethod
    def from_file(filename="xmu.dat", input_filename="feff.inp"):
        """
        Get Xmu from file.

        Args:
            filename: filename and path for xmu.dat
            input_filename: filename and path of feff.inp input file

        Returns:
             Xmu object
        """
        data = np.loadtxt(filename)
        header = Header.from_file(input_filename)
        parameters = Tags.from_file(input_filename)
        pots = Potential.pot_string_from_file(input_filename)
        absorbing_atom = pots.splitlines()[1].split()[2]
        return Xmu(header, parameters, absorbing_atom, data)

    @property
    def energies(self):
        """
        Returns energies for cross-section plots
        """
        return self.data[:, 0]

    @property
    def relative_energies(self):
        """
        Returns energy with respect to the fermi level.
        E - E_f
        """
        return self.data[:, 1]

    @property
    def wavenumber(self):
        """
        Returns The wave number in units of \AA^-1. k=\sqrt(E −E_f) where E is
        the energy and E_f is the Fermi level computed from electron gas theory
        at the average interstitial charge density.
        """
        return self.data[:, 2]

    @property
    def mu(self):
        """
        Returns the total absorption cross-section.
        """
        return self.data[:, 3]

    @property
    def mu0(self):
        """
        Returns the embedded atomic background absorption.
        """
        return self.data[:, 4]

    @property
    def chi(self):
        """
        Returns the normalized fine structure.
        """
        return self.data[:, 5]

    @property
    def source(self):
        """
        Returns source identification from Header file
        """
        return self.header.source

    @property
    def calc(self):
        """
        Returns type of Feff calculation, XANES or EXAFS
        """
        return "XANES" if "XANES" in self.parameters else "EXAFS"

    @property
    def material_formula(self):
        """
        Returns chemical formula of material from feff.inp file
        """
        try:
            form = self.header.formula
        except IndexError:
            form = 'No formula provided'
        return "".join(map(str, form))

    @property
    def edge(self):
        """
        Returns excitation edge.
        """
        return self.parameters["EDGE"]

    def as_dict(self):
        """
        Returns Dictionary of attributes and to reproduce object
        using from dictionary staticmethod.
        """
        return {'@module': self.__class__.__module__,
                '@class': self.__class__.__name__,
                'energies': self.energies,
                'mu': self.mu.tolist(),
                'mu0': self.mu0.tolist(),
                "chi": self.chi.tolist(),
                'atom': self.absorbing_atom,
                'edge': self.edge,
                'source': self.source,
                'calc': self.calc,
                'formula': self.material_formula,
                'HEADER': self.header.as_dict(),
                'TAGS': self.parameters,
                'c_atom': self.absorbing_atom,
                'xmu': self.data.tolist()}

    @classmethod
    def from_dict(cls, xdict):
        """
        Returns Xmu object from dictionary
        """
        header = Header.from_dict(xdict['HEADER'])
        return cls(header, xdict['TAGS'], xdict['c_atom'],
                   np.array(xdict['xmu']))