cimport cython

cdef extern from "wmm/GeomagnetismHeader.h":
    # Data structure defined in GeomagnetismHeader.h used by the get_geomagnetics_elements function
    ctypedef struct MAGtype_GeoMagneticElements:
        double Decl
        double Incl
        double F
        double H
        double X
        double Y
        double Z
        double GV
        double Decldot
        double Incldot
        double Fdot
        double Hdot
        double Xdot
        double Ydot
        double Zdot
        double GVdot


cdef extern from "wmm_wrap.h":
    # Imports definitions from a c header file
    # Corresponding source file (cfunc.c) must be added to
    # the extension definition in setup.py for proper compiling & linking

    MAGtype_GeoMagneticElements _get_geomagnetics_elements "get_geomagnetics_elements"(
        double lat, double lon, double alt, char* alt_mode, double year, char* cof_file_name)


def get_geomagnetics_elements(lat, lon, alt, alt_mode="g", year=None, cof_file_path=None):
    """
    Get the geomagnetics elements for the given coordinates and WMM model.

    The resulting dictionary contains the following keys:
    - Decl: Geomagnetic Declination in deg (degrees)
    - Incl: Geomagnetic Inclination in deg (degrees)
    - F: Total Intensity of the geomagnetic field in nT (nanoTesla)
    - H: Horizontal Intensity of the geomagnetic field in nT (nanoTesla)
    - X: North Component of the geomagnetic field in nT (nanoTesla)
    - Y: East Component of the geomagnetic field in nT (nanoTesla)
    - Z: Vertical Component of the geomagnetic field in nT (nanoTesla)
    - GV: Grid Variation in deg (degrees)
    - Decldot: Secular variation of the Geomagnetic Declination in deg/year (degrees per year)
    - Incldot: Secular variation of the Geomagnetic Inclination in deg/year (degrees per year)
    - Fdot: Secular variation of the Total Intensity of the geomagnetic field in nT/year (nanoTesla per year)
    - Hdot: Secular variation of the Horizontal Intensity of the geomagnetic field in nT/year (nanoTesla per year)
    - Xdot: Secular variation of the North Component of the geomagnetic field in nT/year (nanoTesla per year)
    - Ydot: Secular variation of the East Component of the geomagnetic field in nT/year (nanoTesla per year)
    - Zdot: Secular variation of the Vertical Component of the geomagnetic field in nT/year (nanoTesla per year)
    - GV: Secular variation of the Grid Variation in deg/year (degrees per year)

    :param lat: geographic latitude en degrees
    :param lon: geographic longitude en degrees
    :param alt: altitude above mean sea level (geoid) or above ellipsoid
    :param year: year as a decimal number. Examples : 2015, 2017.5
    :param cof_file_path: path to the COF file to be used. By default, the 2015 COF file provided with the package
    :param alt_mode: "g" or "e". "e" is for altitude above ellipsoid. "g" is for altitude above mean sea level (geoid)
    :return: dictionnary containing the geomagnetics elements
    """

    # Exposes the get_geomagnetics_elements c function to python

    if year is None:
        from datetime import date
        year = date.today().year

    import os
    if cof_file_path is None:
        cof_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "WMM.COF")

    if not os.path.exists(cof_file_path):
        import errno
        raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), cof_file_path)

    cdef double dlat = lat
    cdef double dlon = lon
    cdef double dalt = alt
    cdef double dyear = year
    cdef char* scof_file_path = cof_file_path
    cdef char* salt_mod = alt_mode

    # alt is the height above MSL / above geoid (not above ellipsoid)!
    # unit for alt: kilometer
    result = _get_geomagnetics_elements(dlat, dlon, dalt, salt_mod, dyear, scof_file_path)

    return result
