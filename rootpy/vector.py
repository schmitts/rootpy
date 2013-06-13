# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
from __future__ import absolute_import

import ROOT

from copy import copy

from . import QROOT
from .base import isbasictype, Object
from .decorators import snake_case_methods

__all__ = [
    'Vector2',
    'Vector3',
    'LorentzVector',
    'Rotation',
    'LorentzRotation',
]


class _arithmetic_mixin:

    def __mul__(self, other):

        try:
            prod = self.__class__.__bases__[-1].__mul__(self, other)
            if isinstance(prod, self.__class__.__bases__[-1]):
                prod.__class__ = self.__class__
        except TypeError:
            raise TypeError(
                "unsupported operand type(s) for *: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        return prod

    def __imul__(self, other):

        if isinstance(other, self.__class__):
            raise TypeError("Attemping to set vector to scalar quantity")
        try:
            prod = self * other
        except TypeError:
            raise TypeError(
                "unsupported operand type(s) for *: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        self = prod
        return self

    def __rmul__(self, other):

        try:
            return self * other
        except TypeError:
            raise TypeError(
                "unsupported operand type(s) for *: '{0}' and '{1}'".format(
                    other.__class__.__name__, self.__class__.__name__))

    def __add__(self, other):

        if other == 0:
            return copy(self)
        try:
            clone = self.__class__.__bases__[-1].__add__(self, other)
            clone.__class__ = self.__class__
        except TypeError:
            raise TypeError(
                "unsupported operand type(s) for +: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        return clone

    def __radd__(self, other):

        if other == 0:
            return copy(self)
        raise TypeError(
            "unsupported operand type(s) for +: '{0}' and '{1}'".format(
                other.__class__.__name__, self.__class__.__name__))

    def __iadd__(self, other):

        try:
            _sum = self + other
        except TypeError:
            raise TypeError(
                "unsupported operand type(s) for +: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        self = _sum
        return self

    def __sub__(self, other):

        if other == 0:
            return copy(self)
        try:
            clone = self.__class__.__bases__[-1].__sub__(self, other)
            clone.__class__ = self.__class__
        except TypeError:
            raise TypeError(
                "unsupported operand type(s) for -: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        return clone

    def __rsub__(self, other):

        if other == 0:
            return copy(self)
        raise TypeError(
                "unsupported operand type(s) for -: '{0}' and '{1}'".format(
                    other.__class__.__name__, self.__class__.__name__))

    def __isub__(self, other):

        try:
            diff = self - other
        except TypeError:
            raise TypeError(
                "unsupported operand type(s) for -: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        self = diff
        return self

    def __copy__(self):

        _copy = self.__class__.__bases__[-1](self)
        _copy.__class__ = self.__class__
        return _copy


@snake_case_methods
class Vector2(_arithmetic_mixin, Object, QROOT.TVector2):

    _ROOT = QROOT.TVector2

    def __repr__(self):

        return '{0}({1:f}, {2:f})'.format(
            self.__class__.__name__, self.X(), self.Y())

    def __mul__(self, other):

        if isinstance(other, self.__class__):
            prod = self.X() * other.X() + \
                   self.Y() * other.Y()
        elif isbasictype(other):
            prod = Vector2(other * self.X(), other * self.Y())
        else:
            raise TypeError(
                "unsupported operand type(s) for *: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        return prod

    def __add__(self, other):

        if isinstance(other, ROOT.TVector2):
            _sum = Vector3(self.X() + other.X(),
                           self.Y() + other.Y())
        else:
            raise TypeError(
                "unsupported operand type(s) for *: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        return _sum


@snake_case_methods
class Vector3(_arithmetic_mixin, Object, QROOT.TVector3):

    _ROOT = QROOT.TVector3

    def __repr__(self):

        return '{0}({1:f}, {2:f}, {3:f})'.format(
            self.__class__.__name__, self.X(), self.Y(), self.Z())

    def Angle(self, other):

        if isinstance(other, LorentzVector):
            return other.Angle(self)
        return ROOT.TVector3.Angle(self, other)

    def __mul__(self, other):

        if isinstance(other, ROOT.TVector3):
            prod = self.X() * other.X() + \
                   self.Y() * other.Y() + \
                   self.Z() * other.Z()
        elif isbasictype(other):
            prod = Vector3(other * self.X(), other * self.Y(), other * self.Z())
        else:
            raise TypeError(
                "unsupported operand type(s) for *: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        return prod

    def __add__(self, other):

        if isinstance(other, ROOT.TVector3):
            _sum = Vector3(self.X() + other.X(),
                           self.Y() + other.Y(),
                           self.Z() + other.Z())
        else:
            raise TypeError(
                "unsupported operand type(s) for +: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        return _sum

    def __sub__(self, other):

        if isinstance(other, ROOT.TVector3):
            _dif = Vector3(self.X() - other.X(),
                           self.Y() - other.Y(),
                           self.Z() - other.Z())
        else:
            raise TypeError(
                "unsupported operand type(s) for -: '{0}' and '{1}'".format(
                    self.__class__.__name__, other.__class__.__name__))
        return _dif


@snake_case_methods
class LorentzVector(_arithmetic_mixin, Object, QROOT.TLorentzVector):

    _ROOT = QROOT.TLorentzVector

    def __repr__(self):

        return "{0}({1:f}, {2:f}, {3:f}, {4:f})".format(
            self.__class__.__name__,
            self.Px(), self.Py(), self.Pz(), self.E())

    def Angle(self, other):

        if isinstance(other, ROOT.TLorentzVector):
            return ROOT.TLorentzVector.Angle(self, other.Vect())
        return ROOT.TLorentzVector.Angle(self, other)

    def BoostVector(self):

        vector = ROOT.TLorentzVector.BoostVector(self)
        vector.__class__ = Vector3
        return vector


@snake_case_methods
class Rotation(_arithmetic_mixin, Object, QROOT.TRotation):

    _ROOT = QROOT.TRotation

    def __repr__(self):

        return ("[[{0:f}, {1:f}, {2:f}],\n"
                " [{3:f}, {4:f}, {5:f}],\n"
                " [{6:f}, {7:f}, {8:f}]]").format(
                    self.XX(), self.XY(), self.XZ(),
                    self.YX(), self.YY(), self.YZ(),
                    self.ZX(), self.ZY(), self.ZZ())


@snake_case_methods
class LorentzRotation(_arithmetic_mixin, Object, QROOT.TLorentzRotation):

    _ROOT = QROOT.TLorentzRotation

    def __repr__(self):

        return ("[[{0:f},  {1:f},  {2:f},  {3:f}],\n"
                " [{4:f},  {5:f},  {6:f},  {7:f}],\n"
                " [{8:f},  {9:f},  {10:f},  {11:f}],\n"
                " [{12:f},  {13:f},  {14:f},  {15:f}]]").format(
                    self.XX(), self.XY(), self.XZ(), self.XT(),
                    self.YX(), self.YY(), self.YZ(), self.YT(),
                    self.ZX(), self.ZY(), self.ZZ(), self.ZT(),
                    self.TX(), self.TY(), self.TZ(), self.TT())