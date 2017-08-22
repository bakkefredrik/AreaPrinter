#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>

#include "wmm/GeomagnetismHeader.h"
#include "wmm/EGM9615.h"

// This function merely comes from the wmm_point.c file of the WMM utilities available
// at https://www.ngdc.noaa.gov/geomag/WMM/DoDWMM.shtml
MAGtype_GeoMagneticElements get_geomagnetics_elements(
    double lat, double lon, double alt, char* alt_mode, double year, char* cof_file_name)
{
    MAGtype_MagneticModel * MagneticModels[1], *TimedMagneticModel;
    MAGtype_Ellipsoid Ellip;
    MAGtype_CoordSpherical CoordSpherical;
    MAGtype_CoordGeodetic CoordGeodetic;
    MAGtype_Date UserDate;
    MAGtype_GeoMagneticElements GeoMagneticElements, Errors;
    MAGtype_Geoid Geoid;

    char VersionDate_Large[] = "$Date: 2014-11-21 10:40:43 -0700 (Fri, 21 Nov 2014) $";
    char VersionDate[12];
    int NumTerms, nMax = 0;
    int epochs = 1;

    strncpy(VersionDate, VersionDate_Large + 39, 11);
    VersionDate[11] = '\0';

    if(!MAG_robustReadMagModels(cof_file_name, &MagneticModels, epochs)) {
        puts("\n COF file not found.");
    }

    if(nMax < MagneticModels[0]->nMax) nMax = MagneticModels[0]->nMax;
    NumTerms = ((nMax + 1) * (nMax + 2) / 2);
    TimedMagneticModel = MAG_AllocateModelMemory(NumTerms); /* For storing the time modified WMM Model parameters */
    if(MagneticModels[0] == NULL || TimedMagneticModel == NULL)
    {
        MAG_Error(2);
    }
    MAG_SetDefaults(&Ellip, &Geoid); /* Set default values and constants */

    // Geoid params
    /* Set EGM96 Geoid parameters */
    Geoid.GeoidHeightBuffer = GeoidHeightBuffer;
    Geoid.Geoid_Initialized = 1;

    // Coordinates
    CoordGeodetic.phi = lat;
    CoordGeodetic.lambda = lon;

    if(alt_mode[0] == 'e') /* User entered height above WGS-84 ellipsoid, copy it to CoordGeodetic->HeightAboveEllipsoid */
    {
        Geoid.UseGeoid = 0;
        CoordGeodetic.HeightAboveEllipsoid = alt;
    }
    else /* User entered height above MSL, convert it to the height above WGS-84 ellipsoid */
    {
        Geoid.UseGeoid = 1;
        CoordGeodetic.HeightAboveGeoid = alt;
        MAG_ConvertGeoidToEllipsoidHeight(&CoordGeodetic, &Geoid);
    }

    UserDate.DecimalYear = year;

    MAG_GeodeticToSpherical(Ellip, CoordGeodetic, &CoordSpherical); /*Convert from geodetic to Spherical Equations: 17-18, WMM Technical report*/
    MAG_TimelyModifyMagneticModel(UserDate, MagneticModels[0], TimedMagneticModel); /* Time adjust the coefficients, Equation 19, WMM Technical report */
    MAG_Geomag(Ellip, CoordSpherical, CoordGeodetic, TimedMagneticModel, &GeoMagneticElements); /* Computes the geoMagnetic field elements and their time change*/
    MAG_CalculateGridVariation(CoordGeodetic, &GeoMagneticElements);
    MAG_WMMErrorCalc(GeoMagneticElements.H, &Errors);
//    MAG_PrintUserDataWithUncertainty(GeoMagneticElements, Errors, CoordGeodetic, UserDate, TimedMagneticModel, &Geoid); /* Print the results */

    MAG_FreeMagneticModelMemory(TimedMagneticModel);
    MAG_FreeMagneticModelMemory(MagneticModels[0]);

    return GeoMagneticElements;
}